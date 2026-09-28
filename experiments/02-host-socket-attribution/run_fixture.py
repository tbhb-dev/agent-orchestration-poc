"""Run the two-workload disposable Unix-socket fixture."""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import cast

PROBE = Path(__file__).with_name("probe.py")


def launch(*args: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(PROBE), *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def command(
    root: subprocess.Popen[str], path: Path, claim: str, mode: str = "direct"
) -> dict[str, object]:
    if root.stdin is None or root.stdout is None:
        raise RuntimeError("root pipe absent")
    root.stdin.write(json.dumps([str(path), claim, mode]) + "\n")
    root.stdin.flush()
    if mode == "exit-parent":
        return {"exit": 0, "reply": "parent exited after spawn"}
    return cast("dict[str, object]", json.loads(root.stdout.readline()))


def wait_socket(path: Path) -> None:
    for _ in range(100):
        if path.exists():
            return
        time.sleep(0.01)
    raise RuntimeError("socket did not appear")


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="bv01-", dir="/tmp") as directory:
        base = Path(directory)
        a, b = launch("root"), launch("root")
        servers: list[subprocess.Popen[str]] = []
        try:
            if a.stdout is None or b.stdout is None:
                raise RuntimeError("root output absent")
            a_pid, b_pid = int(a.stdout.readline()), int(b.stdout.readline())
            a_path, b_path = base / "a.sock", base / "b.sock"
            a_server = launch("server", str(a_path), str(a_pid), "6")
            b_server = launch("server", str(b_path), str(b_pid), "1")
            servers.extend([a_server, b_server])
            wait_socket(a_path)
            wait_socket(b_path)
            replies = [
                {"case": "A to A", "result": command(a, a_path, "A")},
                {"case": "B forges A at A", "result": command(b, a_path, "A pid=1")},
                {"case": "A forges B at A", "result": command(a, a_path, "B pid=1")},
                {"case": "A nested at A", "result": command(a, a_path, "A", "nested")},
                {
                    "case": "A detached at A",
                    "result": command(a, a_path, "A", "detached"),
                },
                {"case": "B to B", "result": command(b, b_path, "B")},
                {
                    "case": "A parent exit at A",
                    "result": command(a, a_path, "A", "exit-parent"),
                },
            ]
            for server in servers:
                output, error = server.communicate(timeout=10)
                print(
                    json.dumps(
                        {
                            "server_exit": server.returncode,
                            "traces": [
                                json.loads(line) for line in output.splitlines()
                            ],
                            "error": error.strip(),
                        }
                    )
                )
            for reply in replies:
                print(json.dumps(reply))
        finally:
            for process in [*servers, a, b]:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()


if __name__ == "__main__":
    run()
