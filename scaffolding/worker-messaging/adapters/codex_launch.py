"""Temporary #176 Codex observation adapter; #28 replaces this scaffold."""

import base64
import json
import os
import socket
import struct
from collections.abc import Callable
from typing import Any, cast

import identity


class TrustPreflightError(ValueError):
    """No trust write was sent to the endpoint."""


class TrustConflictError(TrustPreflightError):
    """The endpoint already has an entry for this exact worktree."""


def change_trust(
    endpoint: str,
    worktree: str,
    value: str | None,
    before_write: Callable[[], None] | None = None,
) -> None:
    """Write one server user-config trust key and read it back on that endpoint."""
    try:
        connection = _connect(endpoint)
    except (OSError, ValueError, EOFError) as error:
        if value is not None:
            raise TrustPreflightError("folder trust endpoint unavailable") from error
        raise
    try:
        number = 2
        if value is not None:
            try:
                before = _call(
                    connection,
                    number,
                    "config/read",
                    {"cwd": worktree, "includeLayers": True},
                )
            except (OSError, ValueError, EOFError) as error:
                raise TrustPreflightError(
                    "folder trust preflight read failed"
                ) from error
            if not identity.trust_readback(before, worktree, None):
                raise TrustConflictError("exact worktree already has a trust entry")
            number += 1
        if before_write is not None:
            before_write()
        written = _call(
            connection,
            number,
            "config/batchWrite",
            identity.trust_write_params(worktree, value),
        )
        if not identity.trust_write_confirmed(written):
            raise ValueError("config/batchWrite did not confirm an unoverridden write")
        read = _call(
            connection,
            number + 1,
            "config/read",
            {"cwd": worktree, "includeLayers": True},
        )
        if not identity.trust_readback(read, worktree, value):
            raise ValueError("config/read did not confirm exact worktree trust")
    finally:
        connection.close()


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
    connection = _connect(endpoint)
    try:
        return _runtime_thread(connection, thread_id, 2)
    finally:
        connection.close()


def discover_thread(
    endpoint: str, row: dict[str, Any]
) -> tuple[str | None, bool, dict[str, Any]]:
    """Find the launched thread through the owning endpoint, then verify it."""
    connection = _connect(endpoint)
    try:
        threads: list[dict[str, Any]] = []
        cursor: str | None = None
        cursors: set[str] = set()
        number = 2
        while True:
            params: dict[str, Any] = {"limit": 100, "cwd": row["worktree"]}
            if cursor is not None:
                params["cursor"] = cursor
            page = _call(connection, number, "thread/list", params)
            data = page.get("data")
            if not isinstance(data, list) or not all(
                isinstance(item, dict) for item in data
            ):
                raise ValueError("invalid thread list")
            threads.extend(data)
            cursor = page.get("nextCursor")
            if cursor is None:
                break
            if not isinstance(cursor, str) or cursor in cursors:
                raise ValueError("invalid thread list cursor")
            cursors.add(cursor)
            number += 1
        found = identity.codex_candidate(threads, row)
        if found is None:
            return None, False, {}
        loaded, thread = _runtime_thread(connection, found, number + 1)
        if loaded and thread.get("id") == found:
            resumed = _call(
                connection,
                number + 3,
                "thread/resume",
                {"threadId": found, "excludeTurns": True},
            )
            if resumed.get("thread", {}).get("id") != found:
                raise ValueError("resumed thread identity mismatch")
            roots = resumed.get("runtimeWorkspaceRoots")
            if not isinstance(roots, list) or not all(
                isinstance(root, str) for root in roots
            ):
                raise ValueError("thread workspace roots unavailable")
            thread["runtimeWorkspaceRoots"] = roots
        return found, loaded, thread
    finally:
        connection.close()


def _connect(endpoint: str) -> socket.socket:
    """Open and initialize one WebSocket client on the selected Unix endpoint."""
    socket_path = identity.codex_endpoint(endpoint)
    connection = socket.socket(socket.AF_UNIX)
    connection.settimeout(5)
    try:
        connection.connect(socket_path)
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
            {
                "clientInfo": {"name": "worker-launcher", "version": "1"},
                "capabilities": {"experimentalApi": True},
            },
        )
        connection.sendall(_frame({"method": "initialized"}))
        return connection
    except Exception:
        connection.close()
        raise


def _runtime_thread(
    connection: socket.socket, thread_id: str, number: int
) -> tuple[bool, dict[str, Any]]:
    """Match a discovered ID in loaded inventory and read it back."""
    ids: set[str] = set()
    cursor: str | None = None
    cursors: set[str] = set()
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
