"""Single-process sender/listener for CODEX_HANDOFF.md; JSON commands on stdin."""

import datetime
import json
import os
from pathlib import Path
import socket
import sys
import threading


ROOT = Path(__file__).resolve().parent
TARGET_NAME = "agent-peering-tests-3d"


def target():
    matches = []
    for path in Path.home().joinpath(".claude/sessions").glob("*.json"):
        try:
            entry = json.loads(path.read_text())
        except (OSError, ValueError):
            continue  # Registry files can disappear or change during discovery.
        if entry.get("name") == TARGET_NAME:
            matches.append(entry)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one target, found {len(matches)}")
    return matches[0]


def receive(listener, log, stop):
    while not stop.is_set():
        try:
            conn, _ = listener.accept()
        except socket.timeout:
            continue
        with conn, conn.makefile("rb") as stream:
            for line in stream:
                timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                log.write(timestamp.encode() + b" " + line)
                log.flush()
                print("INBOUND", timestamp, repr(line), flush=True)


def send(frame, auth_token=None):
    entry = target()
    payload = b""
    if auth_token is not None:
        payload += (json.dumps({"type": "auth", "token": auth_token}) + "\n").encode()
    payload += (json.dumps(frame, separators=(",", ":")) + "\n").encode()
    send_bytes(entry, payload)


def send_bytes(entry, payload):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.connect(entry["messagingSocketPath"])
        conn.sendall(payload)
    print("SENT", repr(payload), flush=True)


def main():
    path = Path(f"/tmp/cc-socks/{os.getpid()}.sock")
    bound = False
    stop = threading.Event()
    receiver = None
    with (ROOT / "codex-peering-inbound.log").open("ab") as log:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            try:
                listener.bind(str(path))
                bound = True
                path.chmod(0o600)
                listener.listen()
                listener.settimeout(0.2)
                entry = target()
                receiver = threading.Thread(target=receive, args=(listener, log, stop), daemon=True)
                receiver.start()
                print(json.dumps({"ready": True, "from": f"uds:{path}", "target": entry}), flush=True)
                for line in sys.stdin:
                    command = json.loads(line)
                    if command.get("quit"):
                        break
                    if "raw" in command:
                        send_bytes(target(), command["raw"].encode())
                    else:
                        send(command["frame"])
            finally:
                # Stop accepting before closing the socket to avoid the observed shutdown race.
                stop.set()
                if receiver is not None:
                    receiver.join(timeout=1)
                if bound:
                    path.unlink()


if __name__ == "__main__":
    main()
