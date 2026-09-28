"""Disposable M-001 WebSocket queue and Claude NDJSON targets and clients."""

import argparse
import base64
import json
import os
import socket
import sys
from pathlib import Path
from runpy import run_path
from types import SimpleNamespace
from typing import cast

core = SimpleNamespace(**run_path(str(Path(__file__).with_name("m001_core.py"))))


def exact(reader: socket.socket, length: int) -> bytes:
    """Read exactly one bounded frame component."""
    data = bytearray()
    while len(data) < length:
        part = reader.recv(length - len(data))
        if not part:
            raise EOFError("short frame")
        data.extend(part)
    return bytes(data)


def headers(reader: socket.socket) -> bytes:
    """Read a small HTTP upgrade response or request."""
    data = bytearray()
    while not data.endswith(b"\r\n\r\n") and len(data) < 4096:
        data.extend(exact(reader, 1))
    if not data.endswith(b"\r\n\r\n"):
        raise ValueError("oversize HTTP headers")
    return bytes(data)


def frame(reader: socket.socket, masked: bool) -> bytes:
    """Read one final text frame with RFC 6455 mask direction enforced."""
    first_two = exact(reader, 2)
    extension = core.frame_extension_size(first_two, masked)
    length = core.frame_length(first_two + exact(reader, extension), masked)
    key = exact(reader, 4) if masked else b""
    payload = exact(reader, length)
    return cast("bytes", core.decode_frame(payload, key, masked))


def send_frame(writer: socket.socket, payload: bytes, masked: bool) -> None:
    """Write one final text frame."""
    key = os.urandom(4) if masked else b""
    writer.sendall(core.encode_frame(payload, key))


def queue_exchange(conn: socket.socket) -> str:
    """Complete a WebSocket upgrade and JSON-RPC queue add."""
    conn.sendall(core.upgrade_response(headers(conn)))
    reply, outcome = core.queue_reply(frame(conn, masked=True))
    send_frame(conn, reply, masked=False)
    return cast("str", outcome)


def cc_exchange(conn: socket.socket) -> str:
    """Read a single Claude peer NDJSON message without sending an ack."""
    data = bytearray()
    while len(data) < 4096:
        part = exact(conn, 1)
        if part == b"\n":
            return cast("str", core.cc_result(bytes(data)))
        data.extend(part)
    return "invalid"


def serve(path: Path, kind: str, count: int, log: Path) -> None:
    """Bind one disposable Unix target and log only protocol outcomes."""
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(str(path))
        path.chmod(0o600)
        listener.listen(count)
        for _ in range(count):
            conn, _ = listener.accept()
            with conn:
                conn.settimeout(3)
                try:
                    outcome = (
                        queue_exchange(conn) if kind == "queue" else cc_exchange(conn)
                    )
                except OSError, EOFError, ValueError, KeyError:
                    outcome = "invalid"
            with log.open("a", encoding="utf-8") as output:
                output.write(json.dumps({"kind": kind, "outcome": outcome}) + "\n")
    path.unlink()


def queue_client(path: Path) -> str:
    """Send a masked JSON-RPC request over WebSocket-over-Unix."""
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(3)
        conn.connect(str(path))
        nonce = base64.b64encode(os.urandom(16)).decode()
        conn.sendall(core.upgrade_request(nonce))
        if not core.valid_upgrade_response(headers(conn), nonce):
            return "invalid"
        send_frame(
            conn,
            core.queue_request_bytes(),
            masked=True,
        )
        return cast("str", core.queue_client_result(frame(conn, masked=False)))


def cc_client(path: Path) -> str:
    """Write one complete Claude peer frame, then leave acceptance to the target log."""
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(3)
        conn.connect(str(path))
        conn.sendall(core.cc_line())
    return "sent"


def attempt(kind: str, path: Path) -> str:
    """Keep one client failure as a classified probe result."""
    try:
        return queue_client(path) if kind == "queue" else cc_client(path)
    except (OSError, EOFError, ValueError) as error:
        return type(error).__name__


def mcp(home: Path) -> None:
    """Serve stdio MCP so a harness can exercise the same clients as children."""
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response, kind = core.mcp_action(request)
        except TypeError, ValueError, AttributeError:
            continue
        if kind:
            outcome = attempt(kind, home / "B" / f"{kind}-m001.sock")
            response = core.mcp_probe_response(request["id"], outcome)
        if response is not None:
            print(json.dumps(response), flush=True)


def hook(home: Path) -> None:
    """Run the two probes in a command hook without altering hook decisions."""
    sys.stdin.read()
    outcomes = {
        kind: attempt(kind, home / "B" / f"{kind}-m001.sock")
        for kind in ("queue", "cc-socks")
    }
    print(json.dumps({"outcomes": outcomes}), file=sys.stderr)
    print("{}")


def main() -> None:
    """Expose server and client commands to the later approved harness cells."""
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("serve", "send", "mcp", "hook"))
    parser.add_argument("kind", choices=("queue", "cc-socks", "none"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--log", type=Path)
    args = parser.parse_args()
    if (args.action in ("serve", "send")) == (args.kind == "none"):
        parser.error("serve/send require a protocol kind, mcp/hook require none")
    if args.action == "mcp":
        mcp(args.path)
    elif args.action == "hook":
        hook(args.path)
    elif args.action == "serve":
        if args.log is None or args.count < 1:
            parser.error("serve needs --log and positive --count")
        serve(args.path, args.kind, args.count, args.log)
    else:
        outcome = attempt(args.kind, args.path)
        print(
            json.dumps(
                {
                    "kind": args.kind,
                    "outcome": outcome,
                    "classification": core.classify(outcome),
                }
            )
        )
        if outcome not in ("accepted", "sent"):
            sys.exit(1)


if __name__ == "__main__":
    main()
