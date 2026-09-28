"""Exercise disposable descriptor lifetime and socket path replacement."""

import json
import runpy
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

module = runpy.run_path(str(Path(__file__).with_name("probe.py")))
peer_info = module["peer_info"]
process_info = module["process_info"]


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="bv01-edge-", dir="/tmp") as directory:
        base = Path(directory)
        path = base / "held.sock"
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(path))
            listener.listen(1)
            sender = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).with_name("probe.py")),
                    "transfer",
                    str(path),
                ],
                stdout=subprocess.PIPE,
                text=True,
            )
            conn, _ = listener.accept()
            with conn:
                original = peer_info(conn, time.time_ns() // 1_000)
                output, _ = sender.communicate(timeout=5)
                successor_pid = int(output.strip())
                data = conn.recv(16).decode()
                still_original = peer_info(conn, time.time_ns() // 1_000)
                print(
                    json.dumps(
                        {
                            "case": "descriptor inherited after connector exit",
                            "connector_exit": sender.returncode,
                            "connector": asdict(original),
                            "successor_pid": successor_pid,
                            "received": data,
                            "peer_after_exit": asdict(still_original),
                            "connector_live": process_info(original.pid) is not None,
                        }
                    )
                )
        first = base / "first.sock"
        moved = base / "moved.sock"
        with (
            socket.socket(socket.AF_UNIX) as old,
            socket.socket(socket.AF_UNIX) as replacement,
        ):
            old.bind(str(first))
            old.listen(1)
            first.rename(moved)
            replacement.bind(str(first))
            replacement.listen(1)
            with socket.socket(socket.AF_UNIX) as client:
                client.connect(str(first))
                accepted, _ = replacement.accept()
                with accepted:
                    print(
                        json.dumps(
                            {
                                "case": "path replacement",
                                "old_endpoint_exists": moved.exists(),
                                "new_path_is_old_endpoint": first.stat().st_ino
                                == moved.stat().st_ino,
                                "new_listener_accepted": accepted.fileno() >= 0,
                            }
                        )
                    )


if __name__ == "__main__":
    run()
