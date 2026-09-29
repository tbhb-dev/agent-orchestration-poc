"""Run one BV-01 harness cell after the operator's capture control passes."""

import argparse
import hashlib
import json
import os
import shlex
import shutil
import signal
import subprocess
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = Path(__file__).resolve().parent
CODEX = Path(
    "/Users/tony/.codex/packages/standalone/releases/0.157.1-aarch64-apple-darwin/bin/codex"
)
PYTHON = Path("/Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3")
TMUX_SOCKET = Path("/private/tmp/bv01-228-probe.tmux")
CAPTURE_HOME = Path("/private/tmp/bv01-228-codex-headless")
PROFILES = (
    "codex-headless",
    "codex-interactive",
    "claude-headless",
    "claude-interactive",
)


def codex_config(profile: str, port: int) -> str:
    """Build the one disposable Codex profile and its exact read grants."""
    home = Path(f"/private/tmp/bv01-228-{profile}")
    workspace = home / "workspace"
    return f'''model_provider = "bv01"
default_permissions = "bv01"
check_for_update_on_startup = false
[features]
plugins = false
[projects."{workspace}"]
trust_level = "trusted"
[model_providers.bv01]
name = "bv01"
base_url = "http://127.0.0.1:{port}/v1"
wire_api = "responses"
env_key = "BV01_FAKE_OPENAI_KEY"
[permissions.bv01.filesystem]
"{workspace}" = "read"
"{PYTHON.parent.parent}" = "read"
[permissions.bv01.network]
enabled = true
[permissions.bv01.network.unix_sockets]
"{home}/gateway.sock" = "allow"
'''


def claude_trust(workspace: Path) -> dict[str, object]:
    """Seed only first-run and workspace-trust state in a disposable home."""
    return {
        "hasCompletedOnboarding": True,
        "theme": "dark",
        "projects": {str(workspace): {"hasTrustDialogAccepted": True}},
    }


def wait_for(predicate: Callable[[], bool], deadline: float, label: str) -> None:
    """Wait for a bounded setup or run condition."""
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise TimeoutError(label)


def checked(*args: str) -> str:
    """Return output from a required, read-only check."""
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def capture_gate() -> None:
    """Require the live, new capture and its positive control."""
    capture = CAPTURE_HOME / "file-opens-relay.json"
    pid_file = CAPTURE_HOME / "file-opens-relay.pid"
    error = CAPTURE_HOME / "file-opens-relay.err"
    if not capture.is_file() or not pid_file.is_file() or not error.is_file():
        raise RuntimeError("capture files are absent")
    if error.stat().st_size or b"audit-positive-relay" not in capture.read_bytes():
        raise RuntimeError("capture positive control or error gate failed")
    pid = int(pid_file.read_text().strip())
    if checked("/usr/bin/pgrep", "-x", "eslogger").strip() != str(pid):
        raise RuntimeError("recorded eslogger is not running")


def prepare(profile: str, run: Path, port: int) -> dict[str, str]:
    """Write only into the selected disposable home."""
    home = run.parent
    workspace = home / "workspace"
    source_files = (
        (
            EXPERIMENT / "probe.py",
            workspace / "experiments/02-host-socket-attribution/probe.py",
        ),
        (
            ROOT / "src/agent_orchestration_poc/__init__.py",
            workspace / "agent_orchestration_poc/__init__.py",
        ),
        (
            ROOT / "src/agent_orchestration_poc/core/__init__.py",
            workspace / "agent_orchestration_poc/core/__init__.py",
        ),
        (
            ROOT / "src/agent_orchestration_poc/core/host_socket_attribution.py",
            workspace / "agent_orchestration_poc/core/host_socket_attribution.py",
        ),
    )
    hashes: dict[str, str] = {}
    for source, destination in source_files:
        if not destination.parent.is_dir():
            raise RuntimeError(
                f"workspace fixture directory is absent: {destination.parent}"
            )
        shutil.copyfile(source, destination)
        hashes[str(destination.relative_to(workspace))] = hashlib.sha256(
            destination.read_bytes()
        ).hexdigest()
    if profile.startswith("codex-"):
        config = home / "codex/config.toml"
        config.write_text(codex_config(profile, port))
        if tomllib.loads(config.read_text())["default_permissions"] != "bv01":
            raise RuntimeError("Codex profile was not written")
        (run / "config.toml.raw.txt").write_text(config.read_text())
    else:
        (home / "claude/.claude.json").write_text(json.dumps(claude_trust(workspace)))
        (home / "settings.json").write_text(
            json.dumps(
                {
                    "sandbox": {
                        "enabled": True,
                        "network": {
                            "allowUnixSockets": [str(home / "gateway.sock")],
                            "allowAllUnixSockets": False,
                            "allowLocalBinding": False,
                        },
                        "allowUnsandboxedCommands": False,
                    }
                }
            )
        )
        (run / "claude.json.raw.txt").write_text(
            (home / "claude/.claude.json").read_text()
        )
        (run / "settings.json.raw.txt").write_text((home / "settings.json").read_text())
    (run / "source-sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    return hashes


def launch_command(profile: str, port: int) -> tuple[list[str], dict[str, str]]:
    """Return the pinned harness argv and empty-home environment."""
    home = Path(f"/private/tmp/bv01-228-{profile}")
    workspace = home / "workspace"
    env = {
        "HOME": str(home),
        "TMPDIR": str(home / "tmp"),
        "XDG_CONFIG_HOME": str(home / "xdg"),
        "PYTHONPATH": str(workspace),
        "PATH": f"/Users/tony/.local/bin:{PYTHON.parent}:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "TERM": "xterm-256color",
        "LANG": "C.UTF-8",
        "NO_COLOR": "1",
        "PYTHONUNBUFFERED": "1",
    }
    prompt = (
        "Run python3 experiments/02-host-socket-attribution/probe.py client "
        f"{home}/gateway.sock {profile} and then stop."
    )
    if profile.startswith("codex-"):
        env.update(
            CODEX_HOME=str(home / "codex"), BV01_FAKE_OPENAI_KEY="not-a-real-key"
        )
        argv = [str(CODEX)]
        if profile.endswith("headless"):
            argv += ["exec", "--ephemeral", "--skip-git-repo-check"]
        argv += ["-C", str(workspace), "-c", "approval_policy=never"]
        if profile.endswith("headless"):
            argv.append(prompt)
    else:
        env.update(
            CLAUDE_CONFIG_DIR=str(home / "claude"),
            ANTHROPIC_API_KEY="not-a-real-key",
            ANTHROPIC_BASE_URL=f"http://127.0.0.1:{port}",
        )
        argv = [
            "claude",
            "--bare",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--settings",
            str(home / "settings.json"),
        ]
        if profile.endswith("headless"):
            argv += [
                "--print",
                "--no-session-persistence",
                "--permission-prompts",
                "none",
                prompt,
            ]
    return argv, env


def launcher(run: Path, workspace: Path, argv: list[str], env: dict[str, str]) -> Path:
    """Write a barrier wrapper so the listener can bind against its root PID."""
    script = run / "launch.sh"
    assignments = [f"{key}={shlex.quote(value)}" for key, value in env.items()]
    script.write_text(
        "#!/bin/sh\nset -eu\n"
        f"printf '%s\\n' \"$$\" > {shlex.quote(str(run / 'root.pid'))}\n"
        f"while test ! -e {shlex.quote(str(run / 'go'))}; do sleep 0.05; done\n"
        f"cd {shlex.quote(str(workspace))}\n"
        f"exec env -i {' '.join(assignments)} {' '.join(map(shlex.quote, argv))}\n"
    )
    return script


def descendants(root: int) -> list[int]:
    """Find current descendants of this one recorded launch root."""
    rows = checked("/bin/ps", "-eo", "pid=,ppid=").splitlines()
    pairs = [tuple(map(int, row.split())) for row in rows if len(row.split()) == 2]
    found = {root}
    while True:
        newer = found | {pid for pid, parent in pairs if parent in found}
        if newer == found:
            return sorted(found, reverse=True)
        found = newer


def terminate(process: subprocess.Popen[bytes] | None, root: int | None) -> None:
    """Stop only recorded cell descendants and reap the direct child."""
    pids = descendants(root) if root else []
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if process is not None:
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
    for pid in pids:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


@dataclass
class Cell:
    """Own one profile's disposable processes and evidence paths."""

    profile: str
    model: subprocess.Popen[bytes] | None = None
    listener: subprocess.Popen[bytes] | None = None
    harness: subprocess.Popen[bytes] | None = None
    root: int | None = None
    tmux_started: bool = False

    @property
    def home(self) -> Path:
        """Return the approved disposable home."""
        return Path(f"/private/tmp/bv01-228-{self.profile}")

    @property
    def run(self) -> Path:
        """Return this attempt's private files."""
        return self.home / "relay-run"

    @property
    def evidence(self) -> Path:
        """Return this attempt's commit-ready evidence path."""
        return EXPERIMENT / "evidence/relay-run" / self.profile

    @property
    def python_env(self) -> dict[str, str]:
        """Give the responder and listener only the fixture's Python path."""
        return {
            "PATH": f"{PYTHON.parent}:/usr/bin:/bin:/usr/sbin:/sbin",
            "PYTHONPATH": str(ROOT / "src"),
            "HOME": str(self.home),
            "TMPDIR": str(self.home / "tmp"),
            "PYTHONSAFEPATH": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "NO_COLOR": "1",
        }

    def preflight(self) -> None:
        """Require the capture, pinned tools, and unused cell paths."""
        capture_gate()
        if not self.home.is_dir() or not (self.home / "workspace").is_dir():
            raise RuntimeError("disposable home or workspace is absent")
        if (
            self.run.exists()
            or self.evidence.exists()
            or (self.home / "gateway.sock").exists()
        ):
            raise RuntimeError("cell output or gateway path already exists")
        if self.profile.endswith("interactive") and TMUX_SOCKET.exists():
            raise RuntimeError("dedicated tmux socket already exists")
        if checked(str(CODEX), "--version").strip() != "codex-cli 0.157.1":
            raise RuntimeError("Codex version gate failed")
        if checked("claude", "--version").strip() != "2.1.284 (Claude Code)":
            raise RuntimeError("Claude version gate failed")
        if not PYTHON.is_file():
            raise RuntimeError("pinned Python is absent")
        self.run.mkdir(mode=0o700)
        (self.run / "versions.txt").write_text(
            checked("date", "+%Y-%m-%d %H:%M:%S %Z")
            + checked("sw_vers")
            + checked("uname", "-m")
            + checked(str(CODEX), "--version")
            + checked("claude", "--version")
            + checked(str(PYTHON), "--version")
            + checked("tmux", "-V")
        )

    def start_model(self, deadline: float) -> int:
        """Start the fresh loopback responder and verify its listener."""
        with (
            (self.run / "model-start.json").open("wb") as output,
            (self.run / "model.err").open("wb") as error,
        ):
            self.model = subprocess.Popen(
                [
                    str(PYTHON),
                    str(EXPERIMENT / "model_responder.py"),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "0",
                    "--profile",
                    self.profile,
                    "--log",
                    str(self.run / "model.jsonl"),
                ],
                env=self.python_env,
                stdout=output,
                stderr=error,
            )
        model = self.model
        wait_for(
            lambda: (
                (self.run / "model-start.json").stat().st_size > 0
                or model.poll() is not None
            ),
            min(deadline, time.monotonic() + 10),
            "responder readiness",
        )
        if model.poll() is not None:
            raise RuntimeError("responder exited before readiness")
        port = int(json.loads((self.run / "model-start.json").read_text())["port"])
        listen = checked("lsof", "-nP", "-a", "-p", str(model.pid), "-iTCP")
        (self.run / "model-listen.txt").write_text(listen)
        if f"127.0.0.1:{port} (LISTEN)" not in listen:
            raise RuntimeError("responder is not loopback-only")
        return port

    def start_harness(self, port: int, deadline: float) -> None:
        """Launch behind a root-PID barrier in a shell or dedicated tmux."""
        prepare(self.profile, self.run, port)
        argv, env = launch_command(self.profile, port)
        (self.run / "launch-argv.json").write_text(json.dumps(argv) + "\n")
        script = launcher(self.run, self.home / "workspace", argv, env)
        if self.profile.endswith("interactive"):
            checked(
                "tmux",
                "-S",
                str(TMUX_SOCKET),
                "-f",
                "/dev/null",
                "new-session",
                "-d",
                "-s",
                "bv01",
                "-n",
                "anchor",
                "sleep 600",
            )
            self.tmux_started = True
            checked(
                "tmux",
                "-S",
                str(TMUX_SOCKET),
                "set-option",
                "-g",
                "remain-on-exit",
                "on",
            )
            checked(
                "tmux",
                "-S",
                str(TMUX_SOCKET),
                "new-window",
                "-t",
                "bv01",
                "-n",
                self.profile,
                f"sh {shlex.quote(str(script))}",
            )
        else:
            with (
                (self.run / "harness.out").open("wb") as output,
                (self.run / "harness.err").open("wb") as error,
            ):
                self.harness = subprocess.Popen(
                    ["/bin/sh", str(script)], stdout=output, stderr=error
                )
        wait_for(
            lambda: (self.run / "root.pid").is_file(),
            min(deadline, time.monotonic() + 10),
            "launch root",
        )
        self.root = int((self.run / "root.pid").read_text())

    def start_listener(self, deadline: float) -> None:
        """Bind the exact per-workload socket before releasing the root."""
        with (
            (self.run / "listener.jsonl").open("wb") as output,
            (self.run / "listener.err").open("wb") as error,
        ):
            self.listener = subprocess.Popen(
                [
                    str(PYTHON),
                    str(EXPERIMENT / "probe.py"),
                    "server",
                    str(self.home / "gateway.sock"),
                    str(self.root),
                    "1",
                ],
                env=self.python_env,
                stdout=output,
                stderr=error,
            )
        listener = self.listener
        wait_for(
            lambda: (
                (self.home / "gateway.sock").is_socket() or listener.poll() is not None
            ),
            min(deadline, time.monotonic() + 10),
            "listener readiness",
        )
        if listener.poll() is not None:
            raise RuntimeError("listener exited before readiness")
        opened = checked("lsof", "-nP", "-a", "-p", str(listener.pid), "-U")
        (self.run / "listener-open.txt").write_text(opened)
        if str(self.home / "gateway.sock") not in opened:
            raise RuntimeError("listener does not own gateway socket")
        (self.run / "go").touch()

    def prompt_interactive(self, deadline: float) -> None:
        """Send the fixed prompt only after the TUI input appears."""
        if not self.tmux_started:
            return
        marker = "›" if self.profile.startswith("codex-") else "❯"
        ready_by = min(deadline, time.monotonic() + 30)
        while time.monotonic() < ready_by:
            pane = checked(
                "tmux",
                "-S",
                str(TMUX_SOCKET),
                "capture-pane",
                "-p",
                "-t",
                f"bv01:{self.profile}",
            )
            if "Accessing workspace:" in pane or "Quick safety check:" in pane:
                raise RuntimeError("workspace trust prompt appeared")
            if "Sign in" in pane or "Enter your API key" in pane:
                raise RuntimeError("credential prompt appeared")
            if "Pane is dead" in pane:
                raise RuntimeError("harness pane exited before its input prompt")
            if marker in pane:
                (self.run / "pane-before-prompt.txt").write_text(pane)
                break
            time.sleep(0.2)
        else:
            raise TimeoutError("interactive input prompt did not appear")
        prompt = (
            "Run python3 experiments/02-host-socket-attribution/probe.py client "
            f"{self.home}/gateway.sock {self.profile} and then stop."
        )
        checked(
            "tmux",
            "-S",
            str(TMUX_SOCKET),
            "send-keys",
            "-t",
            f"bv01:{self.profile}",
            "-l",
            prompt,
        )
        checked(
            "tmux",
            "-S",
            str(TMUX_SOCKET),
            "send-keys",
            "-t",
            f"bv01:{self.profile}",
            "Enter",
        )

    def observe(self, deadline: float) -> str:
        """Wait for a connector request and retain only cell process evidence."""
        listener = self.listener
        harness = self.harness
        if listener is None:
            raise RuntimeError("listener absent")
        wait_for(
            lambda: (
                listener.poll() is not None
                or (harness is not None and harness.poll() is not None)
            ),
            deadline,
            "cell completion before 540 seconds",
        )
        if harness is not None:
            harness.wait(timeout=max(1, deadline - time.monotonic()))
        time.sleep(1)
        if self.tmux_started:
            (self.run / "harness-pane.txt").write_text(
                checked(
                    "tmux",
                    "-S",
                    str(TMUX_SOCKET),
                    "capture-pane",
                    "-p",
                    "-S",
                    "-2000",
                    "-t",
                    f"bv01:{self.profile}",
                )
            )
            exit_status = checked(
                "tmux",
                "-S",
                str(TMUX_SOCKET),
                "display-message",
                "-p",
                "-t",
                f"bv01:{self.profile}",
                "#{pane_dead} #{pane_dead_status}",
            ).strip()
        else:
            exit_status = str(harness.returncode if harness else "absent")
        (self.run / "harness-exit.txt").write_text(exit_status + "\n")
        pids = sorted(
            set(
                descendants(self.root or 0)
                + [listener.pid, self.model.pid if self.model else 0]
            )
        )
        (self.run / "process-tree.txt").write_text(
            checked(
                "/bin/ps",
                "-p",
                ",".join(map(str, pids)),
                "-o",
                "pid,ppid,lstart,command",
            )
        )
        rows = [
            json.loads(line)
            for line in (self.run / "model.jsonl").read_text().splitlines()
        ]
        requests = [
            json.loads(line)
            for line in (self.run / "listener.jsonl").read_text().splitlines()
        ]
        if any(row["status"] != 200 for row in rows):
            raise RuntimeError("responder refused a request")
        if len(requests) != 1:
            raise RuntimeError("listener did not handle exactly one connector request")
        if harness is not None and harness.returncode != 0:
            raise RuntimeError(f"headless harness exited {harness.returncode}")
        return f"peer={requests[0]['peer']['pid']} decision={requests[0]['decision']} requests={len(rows)}"

    def cleanup(self, status: str, detail: str) -> None:
        """Stop owned processes, preserve evidence, and print one result."""
        terminate(
            self.harness, self.root or (self.harness.pid if self.harness else None)
        )
        if self.tmux_started:
            checked("tmux", "-S", str(TMUX_SOCKET), "kill-server")
            if TMUX_SOCKET.exists():
                TMUX_SOCKET.unlink()
        terminate(self.listener, self.listener.pid if self.listener else None)
        terminate(self.model, self.model.pid if self.model else None)
        socket = self.home / "gateway.sock"
        if socket.is_socket():
            socket.unlink()
        if self.run.exists():
            (self.run / "summary.json").write_text(
                json.dumps(
                    {"profile": self.profile, "status": status, "detail": detail}
                )
                + "\n"
            )
            self.evidence.mkdir(parents=True, mode=0o700, exist_ok=True)
            for item in self.run.iterdir():
                if item.is_file() and item.name not in {"go", "launch.sh"}:
                    shutil.copyfile(item, self.evidence / item.name)
        print(f"BV-01 {self.profile}: {status}; {detail}", flush=True)


def run_cell(profile: str) -> None:
    """Run one cell with a 540-second deadline and unconditional teardown."""
    os.umask(0o077)
    cell = Cell(profile)
    status = "failed"
    detail = "unknown"
    deadline = time.monotonic() + 540
    try:
        cell.preflight()
        port = cell.start_model(deadline)
        cell.start_harness(port, deadline)
        cell.start_listener(deadline)
        cell.prompt_interactive(deadline)
        detail = cell.observe(deadline)
        status = "passed"
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        TimeoutError,
        subprocess.CalledProcessError,
    ) as error:
        detail = str(error).replace("\n", " ")[:300]
    finally:
        try:
            cell.cleanup(status, detail)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
            status = "failed"
            print(f"BV-01 {profile}: failed; cleanup: {error}", flush=True)
    if status != "passed":
        raise SystemExit(1)


def main() -> None:
    """Run exactly one named cell."""
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", choices=PROFILES)
    args = parser.parse_args()
    run_cell(args.profile)


if __name__ == "__main__":
    main()
