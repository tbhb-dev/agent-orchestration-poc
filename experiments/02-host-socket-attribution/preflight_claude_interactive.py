"""Exercise Claude's interactive title and Bash requests without a gateway."""

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from agent_orchestration_poc.core.host_socket_attribution import (
    claude_settings,
    claude_theme_choice,
    claude_trust,
    empty_input_prompt,
    launch_command,
)

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = Path(__file__).resolve().parent
PYTHON = Path("/Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3")
CLAUDE = Path("/Users/tony/.local/share/claude/versions/2.1.284")
TMUX = Path("/opt/homebrew/bin/tmux")
PROFILE = "claude-interactive"
HOME = Path("/private/tmp/bv01-228-claude-interactive")
RUNS = Path("/private/tmp/bv01-228-preflight")
PROMPT = (
    "Run python3 experiments/02-host-socket-attribution/probe.py client "
    "/private/tmp/bv01-228-claude-interactive/gateway.sock claude-interactive and then stop."
)


def checked(*args: str) -> str:
    """Run a bounded local tmux command."""
    return subprocess.run(
        args, check=True, capture_output=True, text=True, timeout=10
    ).stdout


def wait_for(
    predicate: Callable[[], bool],
    label: str,
    on_timeout: Callable[[], None] | None = None,
) -> None:
    """Wait for a short interactive preflight condition."""
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.2)
    if on_timeout is not None:
        on_timeout()
    raise TimeoutError(label)


def prepare_home(home: Path) -> None:
    """Create only a disposable Claude profile, with no gateway or probe client."""
    workspace = home / "workspace"
    config = home / "claude"
    for path in (workspace, config, home / "tmp", home / "xdg"):
        path.mkdir(parents=True, exist_ok=True)
    (config / ".claude.json").write_text(json.dumps(claude_trust(workspace)))
    (home / "settings.json").write_text(json.dumps(claude_settings(home)))


def save_claude_artifacts(home: Path, run: Path, started_ns: int) -> None:
    """Copy this invocation's Claude debug and transcript files for inspection."""
    config = home / "claude"
    for directory in ("debug", "projects"):
        source = config / directory
        if not source.is_dir():
            continue
        for path in source.rglob("*"):
            if path.is_file() and path.stat().st_mtime_ns >= started_ns:
                target = run / "claude" / path.relative_to(config)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)


def save_pane(socket: Path, run: Path, name: str) -> None:
    """Retain the dedicated pane while its tmux server is alive."""
    try:
        pane = checked(
            str(TMUX),
            "-S",
            str(socket),
            "capture-pane",
            "-p",
            "-S",
            "-2000",
            "-t",
            "preflight",
        )
    except (OSError, subprocess.SubprocessError) as error:
        pane = f"capture failed: {error}\n"
    (run / name).write_text(pane)


def wait_for_input(socket: Path, run: Path) -> None:
    """Handle the same first-run screens and composer as the relay cell."""
    theme_answered = False

    def ready() -> bool:
        nonlocal theme_answered
        pane = checked(
            str(TMUX), "-S", str(socket), "capture-pane", "-p", "-t", "preflight"
        )
        if "Accessing workspace:" in pane or "Quick safety check:" in pane:
            (run / "pane-trust-prompt.txt").write_text(pane)
            raise RuntimeError("workspace trust prompt appeared")
        if "Sign in" in pane or "Enter your API key" in pane:
            (run / "pane-credential-prompt.txt").write_text(pane)
            raise RuntimeError("credential prompt appeared")
        if "Pane is dead" in pane:
            (run / "pane-dead.txt").write_text(pane)
            raise RuntimeError("harness pane exited before its input prompt")
        if claude_theme_choice(pane):
            if not theme_answered:
                (run / "pane-theme-choice.txt").write_text(pane)
                checked(
                    str(TMUX),
                    "-S",
                    str(socket),
                    "send-keys",
                    "-t",
                    "preflight",
                    "Enter",
                )
                theme_answered = True
            return False
        if empty_input_prompt(pane, "❯"):
            (run / "pane-before-prompt.txt").write_text(pane)
            return True
        return False

    wait_for(
        ready,
        "Claude interactive input",
        lambda: save_pane(socket, run, "pane-prompt-timeout.txt"),
    )


def verify_frames(model_log: Path) -> None:
    """Require one title side request and Bash tool before the final frame."""
    rows = [json.loads(line) for line in model_log.read_text().splitlines()]
    title = [
        row
        for row in rows
        if row.get("tool_count") == 0
        and row.get("has_output_format") is True
        and row.get("classification") in {"side-request", "follow-up"}
    ]
    tool = [row for row in rows if row.get("classification") == "tool"]
    final = [row for row in rows if row.get("classification") == "final"]
    if len(title) != 1 or len(tool) != 1 or len(final) != 1:
        raise RuntimeError("expected one title, Bash tool, and final frame")
    if title[0].get("has_bash") or not tool[0].get("has_bash"):
        raise RuntimeError("Bash frame was not served to the Bash request")
    if rows.index(final[0]) < rows.index(tool[0]):
        raise RuntimeError("final frame preceded Bash tool frame")


def run_interactive(home: Path, run: Path, port: int, model_log: Path) -> None:
    """Start pinned Claude on one dedicated tmux socket and submit the probe."""
    socket = run / "tmux.sock"
    argv, env = launch_command(PROFILE, port, home, (CLAUDE, CLAUDE, PYTHON))
    (run / "launch-argv.json").write_text(json.dumps(argv) + "\n")
    assignments = [f"{key}={shlex.quote(value)}" for key, value in env.items()]
    command = (
        f"cd {shlex.quote(str(home / 'workspace'))} && exec /usr/bin/env -i "
        + " ".join(assignments + [shlex.quote(arg) for arg in argv])
    )
    try:
        checked(
            str(TMUX),
            "-S",
            str(socket),
            "-f",
            "/dev/null",
            "new-session",
            "-x",
            "200",
            "-y",
            "50",
            "-d",
            "-s",
            "preflight",
            command,
        )

        wait_for_input(socket, run)
        checked(
            str(TMUX), "-S", str(socket), "send-keys", "-t", "preflight", "-l", PROMPT
        )
        time.sleep(0.5)
        checked(str(TMUX), "-S", str(socket), "send-keys", "-t", "preflight", "Enter")

        def completed() -> bool:
            if not model_log.is_file():
                return False
            rows = [json.loads(line) for line in model_log.read_text().splitlines()]
            return any(row.get("classification") == "final" for row in rows)

        wait_for(
            completed,
            "Claude final frame",
            lambda: save_pane(socket, run, "pane-final-timeout.txt"),
        )
        verify_frames(model_log)
    finally:
        if socket.exists():
            save_pane(socket, run, "pane-at-teardown.txt")
            subprocess.run(
                [str(TMUX), "-S", str(socket), "kill-server"],
                check=False,
                capture_output=True,
                timeout=10,
            )


def main() -> None:
    """Start the loopback responder and clean up every disposable process."""
    os.umask(0o077)
    if not CLAUDE.is_file() or not TMUX.is_file() or not PYTHON.is_file():
        raise RuntimeError("pinned preflight binary is absent")
    RUNS.mkdir(mode=0o700, exist_ok=True)
    run = RUNS / f"run-{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
    run.mkdir(mode=0o700)
    print(f"BV-01 Claude interactive preflight artifacts: {run}")
    prepare_home(HOME)
    (run / "claude.json.raw.txt").write_text((HOME / "claude/.claude.json").read_text())
    (run / "settings.json.raw.txt").write_text((HOME / "settings.json").read_text())
    model_log = run / "model.jsonl"
    model_log.touch()
    start = run / "model-start.json"
    with start.open("w") as output, (run / "model.err").open("w") as stderr:
        model = subprocess.Popen(
            [
                str(PYTHON),
                str(EXPERIMENT / "model_responder.py"),
                "--host",
                "127.0.0.1",
                "--port",
                "0",
                "--profile",
                PROFILE,
                "--log",
                str(model_log),
            ],
            env={
                "PATH": "/usr/bin:/bin",
                "PYTHONPATH": str(ROOT / "src"),
                "PYTHONSAFEPATH": "1",
                "HOME": str(HOME),
            },
            stdout=output,
            stderr=stderr,
        )
    try:
        wait_for(
            lambda: start.stat().st_size > 0 or model.poll() is not None,
            "loopback responder start",
            lambda: save_pane(run / "tmux.sock", run, "pane-model-start-timeout.txt"),
        )
        if model.poll() is not None:
            raise RuntimeError("loopback responder exited")
        started_ns = time.time_ns()
        try:
            run_interactive(
                HOME, run, int(json.loads(start.read_text())["port"]), model_log
            )
        finally:
            save_claude_artifacts(HOME, run, started_ns)
        print("BV-01 Claude interactive preflight: passed; title, Bash tool, final")
    finally:
        model.terminate()
        try:
            model.wait(timeout=5)
        except subprocess.TimeoutExpired:
            model.kill()
            model.wait(timeout=5)


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        ValueError,
        RuntimeError,
        TimeoutError,
        subprocess.SubprocessError,
    ) as error:
        print(f"BV-01 Claude interactive preflight: failed; {error}", file=sys.stderr)
        raise SystemExit(1) from error
