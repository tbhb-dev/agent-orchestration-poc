"""Exercise Claude's interactive title and Bash requests without a gateway."""

import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from agent_orchestration_poc.core.host_socket_attribution import (
    claude_settings,
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
PROMPT = (
    "Run python3 experiments/02-host-socket-attribution/probe.py client "
    "/private/tmp/bv01-228-claude-interactive/gateway.sock claude-interactive and then stop."
)


def checked(*args: str) -> str:
    """Run a bounded local tmux command."""
    return subprocess.run(
        args, check=True, capture_output=True, text=True, timeout=10
    ).stdout


def wait_for(predicate: Callable[[], bool], label: str) -> None:
    """Wait for a short interactive preflight condition."""
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.2)
    raise TimeoutError(label)


def prepare_home(home: Path) -> None:
    """Create only a disposable Claude profile, with no gateway or probe client."""
    workspace = home / "workspace"
    config = home / "claude"
    for path in (workspace, config, home / "tmp", home / "xdg"):
        path.mkdir()
    (config / ".claude.json").write_text(json.dumps(claude_trust(workspace)))
    settings = claude_settings(home)
    sandbox = settings["sandbox"]
    if isinstance(sandbox, dict):
        network = sandbox.get("network")
        if isinstance(network, dict):
            network["allowUnixSockets"] = list[str]()
    (home / "settings.json").write_text(json.dumps(settings))


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


def run_interactive(home: Path, port: int, model_log: Path) -> None:
    """Start pinned Claude on one dedicated tmux socket and submit the probe."""
    socket = home / "tmux.sock"
    argv, env = launch_command(PROFILE, port, home, (CLAUDE, CLAUDE, PYTHON))
    argv[-1] = "bypassPermissions"
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

        def ready() -> bool:
            pane = checked(
                str(TMUX), "-S", str(socket), "capture-pane", "-p", "-t", "preflight"
            )
            if "Accessing workspace:" in pane or "Sign in" in pane:
                raise RuntimeError("unexpected Claude setup prompt")
            return empty_input_prompt(pane, "❯")

        wait_for(ready, "Claude interactive input")
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

        wait_for(completed, "Claude final frame")
        verify_frames(model_log)
    finally:
        if socket.exists():
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
    with tempfile.TemporaryDirectory(
        prefix="bv01-r6-preflight-", dir="/private/tmp"
    ) as directory:
        home = Path(directory)
        prepare_home(home)
        model_log = home / "model.jsonl"
        start = home / "model-start.json"
        with start.open("w") as output, (home / "model.err").open("w") as stderr:
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
                    "HOME": str(home),
                },
                stdout=output,
                stderr=stderr,
            )
        try:
            wait_for(
                lambda: start.stat().st_size > 0 or model.poll() is not None,
                "loopback responder start",
            )
            if model.poll() is not None:
                raise RuntimeError("loopback responder exited")
            run_interactive(home, int(json.loads(start.read_text())["port"]), model_log)
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
