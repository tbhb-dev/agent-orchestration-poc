"""Disposable M-001 WebSocket queue and Claude NDJSON targets and clients."""

import argparse
import base64
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any

from m001_core import (  # pyrefly: ignore[missing-import] - sibling experiment module resolves when run by path.
    cc_frame,
    cc_result,
    classify,
    mcp_action,
    queue_request,
    queue_response,
    websocket_accept,
)


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
    first, second = exact(reader, 2)
    if first != 0x81 or bool(second & 0x80) != masked:
        raise ValueError("unexpected WebSocket frame")
    length = second & 0x7F
    if length == 126:
        length = int.from_bytes(exact(reader, 2))
    if length > 4096 or length == 127:
        raise ValueError("oversize WebSocket frame")
    key = exact(reader, 4) if masked else b""
    payload = exact(reader, length)
    return (
        bytes(value ^ key[index % 4] for index, value in enumerate(payload))
        if masked
        else payload
    )


def send_frame(writer: socket.socket, payload: bytes, masked: bool) -> None:
    """Write one final text frame."""
    if len(payload) > 4096:
        raise ValueError("oversize WebSocket frame")
    prefix = bytes([0x81, 0x7E | (0x80 if masked else 0)]) + len(payload).to_bytes(2)
    key = os.urandom(4) if masked else b""
    body = (
        bytes(value ^ key[index % 4] for index, value in enumerate(payload))
        if masked
        else payload
    )
    writer.sendall(prefix + key + body)


def queue_exchange(conn: socket.socket) -> str:
    """Complete a WebSocket upgrade and JSON-RPC queue add."""
    request = headers(conn).decode("ascii")
    lines = request.split("\r\n")
    fields = {
        name.lower(): value
        for line in lines[1:]
        if ": " in line
        for name, value in [line.split(": ", 1)]
    }
    if (
        lines[0] != "GET / HTTP/1.1"
        or fields.get("upgrade", "").lower() != "websocket"
        or fields.get("sec-websocket-version") != "13"
    ):
        raise ValueError("invalid WebSocket upgrade")
    accept = websocket_accept(fields["sec-websocket-key"])
    conn.sendall(
        (
            "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "
            + accept
            + "\r\n\r\n"
        ).encode()
    )
    try:
        rpc: Any = json.loads(frame(conn, masked=True))
    except UnicodeDecodeError, ValueError:
        rpc = None
    reply = queue_response(rpc)
    send_frame(conn, json.dumps(reply, separators=(",", ":")).encode(), masked=False)
    return "accepted" if "result" in reply else "invalid"


def cc_exchange(conn: socket.socket) -> str:
    """Read a single Claude peer NDJSON message without sending an ack."""
    data = bytearray()
    while len(data) < 4096:
        part = exact(conn, 1)
        if part == b"\n":
            return cc_result(bytes(data))
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
        conn.sendall(
            (
                "GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: "
                + nonce
                + "\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
        )
        reply = headers(conn).decode("ascii")
        if (
            not reply.startswith("HTTP/1.1 101 ")
            or f"Sec-WebSocket-Accept: {websocket_accept(nonce)}\r\n" not in reply
        ):
            return "invalid"
        send_frame(
            conn,
            json.dumps(queue_request(), separators=(",", ":")).encode(),
            masked=True,
        )
        response: Any = json.loads(frame(conn, masked=False))
        return "accepted" if response == queue_response(queue_request()) else "invalid"


def cc_client(path: Path) -> str:
    """Write one complete Claude peer frame, then leave acceptance to the target log."""
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(3)
        conn.connect(str(path))
        conn.sendall(json.dumps(cc_frame(), separators=(",", ":")).encode() + b"\n")
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
            response, kind = mcp_action(request)
        except TypeError, ValueError, AttributeError:
            continue
        if kind:
            outcome = attempt(kind, home / "B" / f"{kind}-m001.sock")
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "outcome": outcome,
                                    "classification": classify(outcome),
                                }
                            ),
                        }
                    ],
                    "isError": outcome not in ("accepted", "sent"),
                },
            }
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
                    "classification": classify(outcome),
                }
            )
        )
        if outcome not in ("accepted", "sent"):
            sys.exit(1)


if __name__ == "__main__":
    main()
