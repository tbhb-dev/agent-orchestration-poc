"""Temporary #176 Codex observation adapter; #28 replaces this scaffold."""

import base64
import json
import os
import socket
import struct
import subprocess
from pathlib import Path
from typing import Any, cast

import identity


def open_rollouts(pid: int) -> list[str]:
    """Find rollout files held by the exact TUI process."""
    result = subprocess.run(
        ["lsof", "-Fn", "-p", str(pid)],
        capture_output=True,
        text=True,
        errors="replace",
        check=True,
    )
    return [
        line[1:]
        for line in result.stdout.splitlines()
        if line.startswith("n/") and "/sessions/" in line and "rollout-" in line
    ]


def rollout(path: str) -> dict[str, Any]:
    """Read only identity and first-prompt evidence from a persisted rollout."""
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line]
    return identity.codex_rollout(rows, path)


def _frame(payload: dict[str, Any]) -> bytes:
    data = json.dumps(payload).encode()
    mask = os.urandom(4)
    length = len(data)
    size = bytes([length]) if length < 126 else b"\x7e" + struct.pack("!H", length)
    return (
        b"\x81"
        + bytes([0x80 | size[0]])
        + size[1:]
        + mask
        + bytes(value ^ mask[index % 4] for index, value in enumerate(data))
    )


def _receive(connection: socket.socket) -> dict[str, Any]:
    header = connection.recv(2)
    if len(header) != 2:
        raise EOFError("short WebSocket frame")
    length = header[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", _exact(connection, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _exact(connection, 8))[0]
    if header[1] & 0x80:
        mask = _exact(connection, 4)
        data = _exact(connection, length)
        data = bytes(value ^ mask[index % 4] for index, value in enumerate(data))
    else:
        data = _exact(connection, length)
    if header[0] & 0x0F != 1:
        raise ValueError("unexpected WebSocket frame")
    return cast("dict[str, Any]", json.loads(data))


def _exact(connection: socket.socket, count: int) -> bytes:
    data = bytearray()
    while len(data) < count:
        part = connection.recv(count - len(data))
        if not part:
            raise EOFError("closed WebSocket")
        data.extend(part)
    return bytes(data)


def _call(
    connection: socket.socket, number: int, method: str, params: dict[str, Any]
) -> dict[str, Any]:
    connection.sendall(_frame({"id": number, "method": method, "params": params}))
    for _ in range(100):
        reply = _receive(connection)
        if reply.get("id") == number:
            if "error" in reply:
                raise ValueError(f"{method} returned an error")
            return cast("dict[str, Any]", reply["result"])
    raise TimeoutError("no matching app-server response")


def runtime_thread(endpoint: str, thread_id: str) -> tuple[bool, dict[str, Any]]:
    """Read the named thread from its runtime and check the loaded inventory."""
    connection = socket.socket(socket.AF_UNIX)
    connection.settimeout(5)
    try:
        connection.connect(endpoint)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            "GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        connection.sendall(request.encode())
        response = bytearray()
        while not response.endswith(b"\r\n\r\n") and len(response) < 4096:
            response.extend(_exact(connection, 1))
        if not response.startswith(b"HTTP/1.1 101"):
            raise ValueError("app-server WebSocket handshake failed")
        _call(
            connection,
            1,
            "initialize",
            {"clientInfo": {"name": "worker-launcher", "version": "1"}},
        )
        connection.sendall(_frame({"method": "initialized"}))
        ids: set[str] = set()
        cursor: str | None = None
        cursors: set[str] = set()
        number = 2
        while True:
            params: dict[str, Any] = {"limit": 100}
            if cursor is not None:
                params["cursor"] = cursor
            loaded = _call(connection, number, "thread/loaded/list", params)
            ids.update(identity.loaded_ids(loaded))
            cursor = loaded.get("nextCursor")
            if cursor is None:
                break
            if not isinstance(cursor, str) or cursor in cursors:
                raise ValueError("invalid loaded thread cursor")
            cursors.add(cursor)
            number += 1
        result = _call(
            connection,
            number + 1,
            "thread/read",
            {"threadId": thread_id, "includeTurns": False},
        )
        return thread_id in ids, result.get("thread", {})
    finally:
        connection.close()
