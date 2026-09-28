"""Disposable host process and tmux lifecycle probe for issue 243."""

import argparse
import json
import os
import pty
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def worker(root: Path, name: str, delay: float) -> None:
    """Run a deterministic stand-in for a host wrapper and harness."""
    private = root / "private" / name
    shared = root / "workspace"
    (private / "marker").write_text(name)
    (shared / f"{name}.txt").write_text(f"written by {name}\n")
    (root / f"{name}.ready").write_text(str(os.getpid()))
    print(f"{name}: ready", flush=True)
    time.sleep(delay)
    print(f"{name}: complete", flush=True)
    (root / f"{name}.exit").write_text("0")


def tmux(socket: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Address only the dedicated socket."""
    return subprocess.run(
        ["tmux", "-S", str(socket), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def wait_for(path: Path, timeout: float = 5) -> bool:
    """Wait for a fixture marker without inspecting operator state."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def cancel_process(process: subprocess.Popen[str]) -> str:
    """Signal a live stand-in once and accept repeated cancellation."""
    if process.poll() is None:
        process.terminate()
        return "signaled"
    return "already exited"


def attach_once(socket: Path) -> int:
    """Attach through a disposable PTY and disconnect its client."""
    master, slave = pty.openpty()
    try:
        child_env = os.environ.copy()
        child_env.pop("TMUX", None)
        child_env.pop("TMUX_PANE", None)
        client = subprocess.Popen(
            ["tmux", "-S", str(socket), "attach-session", "-t", "bv08"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env=child_env,
        )
        os.close(slave)
        time.sleep(0.3)
        if client.poll() is not None:
            raise RuntimeError(
                f"tmux attach exited before disconnect: {client.returncode}"
            )
        client.terminate()
        client.wait(timeout=5)
        return client.returncode
    finally:
        os.close(master)


def run() -> None:  # noqa: PLR0915 - fixed probe stages belong in one teardown scope
    """Execute the fixed case sequence and emit a credential-free case record."""
    cases: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="bv08-243-", dir="/private/tmp") as temp:
        root = Path(temp)
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "unrelated.txt").write_text("retain me\n")
        (root / "private").mkdir(mode=0o700)
        for name in ("A", "B"):
            (root / "private" / name).mkdir(mode=0o700)
        cases.append(
            {
                "case": "prepare",
                "actual": "shared and private paths created",
                "A_mode": oct((root / "private" / "A").stat().st_mode & 0o777),
                "B_mode": oct((root / "private" / "B").stat().st_mode & 0o777),
            }
        )

        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "worker",
            str(root),
            "A",
            "0.2",
        ]
        direct = subprocess.run(command, capture_output=True, text=True, check=False)
        cases.append(
            {
                "case": "direct-headless",
                "exit": direct.returncode,
                "ready": (root / "A.ready").exists(),
                "outcome": (root / "A.exit").read_text(),
                "stdout": direct.stdout.strip().splitlines(),
            }
        )

        long_command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "worker",
            str(root),
            "B",
            "30",
        ]
        running = subprocess.Popen(
            long_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        ready = wait_for(root / "B.ready")
        first_cancel = cancel_process(running)
        cancelled_stdout, _ = running.communicate(timeout=5)
        second_cancel = cancel_process(running)
        cases.append(
            {
                "case": "direct-cancel-twice",
                "ready": ready,
                "exit": running.returncode,
                "first_cancel": first_cancel,
                "second_cancel": second_cancel,
                "stdout": cancelled_stdout.strip().splitlines(),
                "outcome_marker": (root / "B.exit").exists(),
            }
        )

        (root / "B.ready").unlink()
        socket = root / "tmux.sock"
        tmux_command = shlex.join(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "worker",
                str(root),
                "B",
                "5",
            ]
        )
        created = tmux(
            socket,
            "-f",
            "/dev/null",
            "new-session",
            "-d",
            "-s",
            "bv08",
            "-c",
            str(workspace),
            tmux_command,
        )
        tmux_ready = wait_for(root / "B.ready")
        pane = tmux(socket, "display-message", "-p", "-t", "bv08", "#{pane_pid}")
        try:
            first_attach = attach_once(socket) if created.returncode == 0 else None
            after_first = tmux(socket, "has-session", "-t", "bv08").returncode
            second_attach = attach_once(socket) if after_first == 0 else None
            after_second = tmux(socket, "has-session", "-t", "bv08").returncode
            pane_output = tmux(
                socket, "capture-pane", "-p", "-t", "bv08"
            ).stdout.strip()
        finally:
            stopped = tmux(socket, "kill-server")
        cases.append(
            {
                "case": "tmux-interactive-reconnect",
                "create_exit": created.returncode,
                "ready": tmux_ready,
                "pane_pid": pane.stdout.strip(),
                "first_attach_exit": first_attach,
                "after_first_has_session": after_first,
                "second_attach_exit": second_attach,
                "after_second_has_session": after_second,
                "pane_output": pane_output,
            }
        )
        cases.append(
            {
                "case": "tmux-server-stop",
                "exit": stopped.returncode,
                "socket_retained": socket.exists(),
                "outcome_marker": (root / "B.exit").exists(),
            }
        )

        try:
            (root / "private" / "A").mkdir()
        except FileExistsError:
            collision = "rejected"
        else:
            collision = "accepted"
        contested = root / "private" / "contested"
        racers = [
            subprocess.Popen(["mkdir", str(contested)], stderr=subprocess.DEVNULL)
            for _ in range(2)
        ]
        race_exits = sorted(racer.wait(timeout=5) for racer in racers)
        interrupted = root / "private" / "interrupted"
        interrupted.mkdir()
        interrupted.rmdir()
        try:
            interrupted.rmdir()
        except FileNotFoundError:
            second_cleanup = "already absent"
        else:
            second_cleanup = "unexpected success"
        cases.append(
            {
                "case": "collision-and-interrupted-create",
                "collision": collision,
                "concurrent_create_exits": race_exits,
                "interrupted_retained": interrupted.exists(),
                "second_cleanup": second_cleanup,
                "unrelated_retained": (workspace / "unrelated.txt").exists(),
            }
        )
        cases.append(
            {
                "case": "storage",
                "shared_A": (workspace / "A.txt").read_text().strip(),
                "shared_B": (workspace / "B.txt").read_text().strip(),
                "A_private": (root / "private" / "A" / "marker").read_text(),
                "B_reads_A_private": (root / "private" / "A" / "marker").read_text(),
            }
        )
    cases.append({"case": "cleanup", "fixture_retained": root.exists()})
    print(json.dumps(cases, indent=2))


def main() -> None:
    """Select the fixed probe or stand-in worker entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("run", "worker"))
    parser.add_argument("root", nargs="?", type=Path)
    parser.add_argument("name", nargs="?")
    parser.add_argument("delay", nargs="?", type=float)
    args = parser.parse_args()
    if args.mode == "worker":
        if args.root is None or args.name is None or args.delay is None:
            parser.error("worker requires root, name, and delay")
        worker(args.root, args.name, args.delay)
    else:
        run()


if __name__ == "__main__":
    main()
