"""Run one BV-01 harness cell after the operator's capture control passes."""

import argparse
import hashlib
import json
import os
import shlex
import shutil
import signal
import socket
import subprocess
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agent_orchestration_poc.core.host_socket_attribution import (
    claude_settings,
    claude_trust,
    codex_config,
    empty_input_prompt,
    launch_command,
    relay_result,
)

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = Path(__file__).resolve().parent
CODEX = Path(
    "/Users/tony/.codex/packages/standalone/releases/0.157.1-aarch64-apple-darwin/bin/codex"
)
CLAUDE = Path("/Users/tony/.local/share/claude/versions/2.1.284")
PYTHON = Path("/Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3")
TMUX_SOCKET = Path("/private/tmp/bv01-228-probe.tmux")
CAPTURE_HOME = Path("/private/tmp/bv01-228-codex-headless")
PROFILES = (
    "codex-headless",
    "codex-interactive",
    "claude-headless",
    "claude-interactive",
)


def wait_for(predicate: Callable[[], bool], deadline: float, label: str) -> None:
    """Wait for a bounded setup or run condition."""
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise TimeoutError(label)


def checked(*args: str) -> str:
    """Return output from a required, read-only check."""
    return subprocess.run(
        args, check=True, capture_output=True, text=True, timeout=30
    ).stdout


def version(binary: Path, home: Path, *args: str) -> str:
    """Check the launched binary without the operator's environment."""
    return checked(
        "/usr/bin/env",
        "-i",
        f"HOME={home}",
        f"CODEX_HOME={home / 'codex'}",
        f"CLAUDE_CONFIG_DIR={home / 'claude'}",
        "PATH=/usr/bin:/bin",
        str(binary),
        *args,
    )


def clear_stale_gateway(path: Path) -> None:
    """Remove only an unheld socket in this cell's disposable home."""
    if not path.exists():
        return
    if not path.is_socket():
        raise RuntimeError("gateway path is not a socket")
    result = subprocess.run(
        ["/usr/sbin/lsof", "-nP", str(path)],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode == 0:
        raise RuntimeError("gateway socket is held by a process")
    if result.returncode != 1:
        raise RuntimeError(f"gateway lsof failed: {result.returncode}")
    path.unlink()


def process_start(pid: int) -> str | None:
    """Read the launch root's start time before signalling its process tree."""
    try:
        return checked("/bin/ps", "-p", str(pid), "-o", "lstart=").strip()
    except subprocess.CalledProcessError:
        return None


def capture_gate() -> None:
    """Require the live, new capture and its positive control."""
    capture = CAPTURE_HOME / "file-opens-relay.json"
    pid_file = CAPTURE_HOME / "file-opens-relay.pid"
    error = CAPTURE_HOME / "file-opens-relay.err"
    marker = CAPTURE_HOME / "audit-positive-relay"
    if not all(path.is_file() for path in (capture, pid_file, error, marker)):
        raise RuntimeError("capture files are absent")
    marker.read_bytes()  # Make a fresh open event for this cell's bounded tail check.

    def marker_in_tail() -> bool:
        with capture.open("rb") as stream:
            stream.seek(max(0, capture.stat().st_size - 1_048_576))
            return b"audit-positive-relay" in stream.read()

    if error.stat().st_size:
        raise RuntimeError("capture positive control or error gate failed")
    wait_for(marker_in_tail, time.monotonic() + 5, "capture positive control")
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
        config.write_text(codex_config(home, PYTHON, port))
        if tomllib.loads(config.read_text())["default_permissions"] != "bv01":
            raise RuntimeError("Codex profile was not written")
        (run / "config.toml.raw.txt").write_text(config.read_text())
    else:
        (home / "claude/.claude.json").write_text(json.dumps(claude_trust(workspace)))
        (home / "settings.json").write_text(json.dumps(claude_settings(home)))
        (run / "claude.json.raw.txt").write_text(
            (home / "claude/.claude.json").read_text()
        )
        (run / "settings.json.raw.txt").write_text((home / "settings.json").read_text())
    (run / "source-sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    return hashes


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


def terminate(
    process: subprocess.Popen[bytes] | None, root: int | None, start: str | None = None
) -> None:
    """Stop only recorded cell descendants and reap the direct child."""
    alive_child = process is not None and process.poll() is None
    same_root = start is not None and root is not None and process_start(root) == start
    pids = descendants(root) if root and (alive_child or same_root) else []
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
    root_start: str | None = None
    tmux_started: bool = False
    run_owned: bool = False
    socket_inode: int | None = None

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
        if self.run.exists() or self.evidence.exists():
            raise RuntimeError("cell output already exists")
        clear_stale_gateway(self.home / "gateway.sock")
        if self.profile.endswith("interactive") and TMUX_SOCKET.exists():
            raise RuntimeError("dedicated tmux socket already exists")
        if not CODEX.is_file() or not CLAUDE.is_file() or not PYTHON.is_file():
            raise RuntimeError("pinned harness or Python is absent")
        try:
            with socket.create_connection(("127.0.0.1", 9), timeout=1):
                raise RuntimeError("dead loopback proxy port is in use")
        except ConnectionRefusedError:
            pass
        if version(CODEX, self.home, "--version").strip() != "codex-cli 0.157.1":
            raise RuntimeError("Codex version gate failed")
        if version(CLAUDE, self.home, "--version").strip() != "2.1.284 (Claude Code)":
            raise RuntimeError("Claude version gate failed")
        self.run.mkdir(mode=0o700)
        self.run_owned = True
        (self.run / "versions.txt").write_text(
            checked("date", "+%Y-%m-%d %H:%M:%S %Z")
            + checked("sw_vers")
            + checked("uname", "-m")
            + version(CODEX, self.home, "--version")
            + version(CLAUDE, self.home, "--version")
            + version(PYTHON, self.home, "--version")
            + version(Path("/opt/homebrew/bin/tmux"), self.home, "-V")
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
        argv, env = launch_command(
            self.profile, port, self.home, (CODEX, CLAUDE, PYTHON)
        )
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
        self.root_start = process_start(self.root)
        if self.root_start is None:
            raise RuntimeError("launch root exited before start-time check")

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
        self.socket_inode = (self.home / "gateway.sock").stat().st_ino
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
            if empty_input_prompt(pane, marker):
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
        return relay_result(rows, requests, harness.returncode if harness else None)

    def cleanup(self, status: str, detail: str) -> bool:  # noqa: C901 - independent teardown steps
        """Stop owned processes, preserve evidence, and print one result."""
        errors: list[str] = []

        def attempt(action: Callable[[], object]) -> None:
            try:
                action()
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                errors.append(str(error))

        attempt(
            lambda: terminate(
                self.harness,
                self.root or (self.harness.pid if self.harness else None),
                self.root_start,
            )
        )
        if self.tmux_started:
            prior_errors = len(errors)
            attempt(lambda: checked("tmux", "-S", str(TMUX_SOCKET), "kill-server"))
            if len(errors) == prior_errors and TMUX_SOCKET.exists():
                attempt(TMUX_SOCKET.unlink)
        attempt(
            lambda: terminate(
                self.listener, self.listener.pid if self.listener else None
            )
        )
        attempt(lambda: terminate(self.model, self.model.pid if self.model else None))
        socket = self.home / "gateway.sock"
        if socket.is_socket() and self.socket_inode == socket.stat().st_ino:
            attempt(socket.unlink)
        if errors:
            status = "failed"
            detail = f"{detail}; cleanup: {'; '.join(errors)}"[:300]
        if self.run_owned:
            try:
                (self.run / "summary.json").write_text(
                    json.dumps(
                        {"profile": self.profile, "status": status, "detail": detail}
                    )
                    + "\n"
                )
                self.evidence.mkdir(parents=True, mode=0o700, exist_ok=False)
                for item in self.run.iterdir():
                    if item.is_file() and item.name not in {"go", "launch.sh"}:
                        shutil.copyfile(item, self.evidence / item.name)
            except (OSError, RuntimeError) as error:
                status = "failed"
                detail = f"{detail}; evidence: {error}"[:300]
        print(f"BV-01 {self.profile}: {status}; {detail}", flush=True)
        return status == "passed"


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
        subprocess.TimeoutExpired,
    ) as error:
        detail = str(error).replace("\n", " ")[:300]
    finally:
        try:
            if not cell.cleanup(status, detail):
                status = "failed"
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
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
