"""Probe a disposable stdio app server without printing model text or credentials."""

import json
import os
import select
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast


def send(process: subprocess.Popen[bytes], message: dict[str, Any]) -> None:
    """Send one JSON-RPC message to the owned runtime."""
    if process.stdin is None:
        raise RuntimeError("app-server stdin unavailable")
    process.stdin.write((json.dumps(message) + "\n").encode())
    process.stdin.flush()


def receive(process: subprocess.Popen[bytes], deadline: float) -> dict[str, Any]:
    """Read one bounded response or notification."""
    if process.stdout is None:
        raise RuntimeError("app-server stdout unavailable")
    line = bytearray()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
            raise TimeoutError("app-server response deadline")
        byte = os.read(process.stdout.fileno(), 1)
        if not byte:
            raise EOFError("app-server closed stdout")
        if byte == b"\n":
            return cast("dict[str, Any]", json.loads(line))
        line.extend(byte)


def request(
    process: subprocess.Popen[bytes],
    number: int,
    method: str,
    params: dict[str, Any],
    deadline: float,
) -> tuple[dict[str, Any], bool]:
    """Send one request and retain selected lifecycle notifications."""
    send(process, {"id": number, "method": method, "params": params})
    completed = False
    while True:
        message = receive(process, deadline)
        completed = record_notification(message) or completed
        if message.get("id") == number:
            return message, completed


def record(event: str, value: dict[str, Any]) -> None:
    """Write only lifecycle metadata to the capture."""
    selected: dict[str, Any] = {"at": datetime.now(tz=UTC).isoformat(), "event": event}
    if event == "status-notification":
        selected.update(
            {"threadId": value.get("threadId"), "status": value.get("status")}
        )
    else:
        selected.update(value)
    print(json.dumps(selected), flush=True)


def record_notification(message: dict[str, Any]) -> bool:
    """Capture a lifecycle notification and flag a completed turn."""
    method = message.get("method")
    params = message.get("params", {})
    if method == "thread/status/changed":
        record("status-notification", params)
    if method == "turn/completed":
        record(
            "turn-completed",
            {
                "threadId": params.get("threadId"),
                "turnId": params.get("turn", {}).get("id"),
            },
        )
        return True
    return False


def start() -> subprocess.Popen[bytes]:
    """Start an experiment-owned app server with no configuration writes."""
    return subprocess.Popen(
        ["codex", "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )


def stop(process: subprocess.Popen[bytes]) -> None:
    """Stop only the child started by this probe."""
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    record("runtime-exit", {"pid": process.pid, "returncode": process.returncode})


def main() -> None:
    """Sample a loaded turn, then a stored thread on a fresh owned runtime."""
    worktree = str(Path.cwd())
    process = start()
    thread_id = ""
    try:
        deadline = time.monotonic() + 120
        record("runtime-start", {"pid": process.pid, "cwd": worktree})
        initialized, _ = request(
            process,
            1,
            "initialize",
            {
                "clientInfo": {"name": "exp214", "version": "1"},
                "capabilities": {"experimentalApi": True},
            },
            deadline,
        )
        record(
            "initialize",
            {"ok": "result" in initialized, "error": initialized.get("error")},
        )
        send(process, {"method": "initialized"})
        started, _ = request(
            process,
            2,
            "thread/start",
            {
                "cwd": worktree,
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "ephemeral": False,
            },
            deadline,
        )
        if "result" not in started:
            record("thread-start-error", {"error": started.get("error")})
            return
        thread = started["result"]["thread"]
        thread_id = thread["id"]
        record(
            "thread-start",
            {
                "id": thread_id,
                "cwd": started["result"].get("cwd"),
                "status": thread.get("status"),
            },
        )
        loaded, _ = request(process, 3, "thread/loaded/list", {}, deadline)
        record(
            "loaded-list",
            {"containsThread": thread_id in loaded.get("result", {}).get("data", [])},
        )
        turn, completed = request(
            process,
            4,
            "turn/start",
            {
                "threadId": thread_id,
                "input": [{"type": "text", "text": "Reply with exactly EXP214-DONE."}],
            },
            deadline,
        )
        record("turn-start", {"ok": "result" in turn, "error": turn.get("error")})
        if "result" not in turn:
            return
        read, during_completed = request(
            process,
            5,
            "thread/read",
            {"threadId": thread_id, "includeTurns": False},
            deadline,
        )
        record(
            "during-turn-read",
            {"status": read.get("result", {}).get("thread", {}).get("status")},
        )
        while not (completed or during_completed) and time.monotonic() < deadline:
            message = receive(process, deadline)
            if record_notification(message):
                break
        read, _ = request(
            process,
            6,
            "thread/read",
            {"threadId": thread_id, "includeTurns": False},
            deadline,
        )
        record(
            "after-turn-read",
            {"status": read.get("result", {}).get("thread", {}).get("status")},
        )
    finally:
        stop(process)
    if thread_id:
        restarted = start()
        try:
            deadline = time.monotonic() + 15
            record("replacement-start", {"pid": restarted.pid})
            request(
                restarted,
                7,
                "initialize",
                {"clientInfo": {"name": "exp214", "version": "1"}},
                deadline,
            )
            send(restarted, {"method": "initialized"})
            read, _ = request(
                restarted,
                8,
                "thread/read",
                {"threadId": thread_id, "includeTurns": False},
                deadline,
            )
            record(
                "replacement-read",
                {
                    "status": read.get("result", {}).get("thread", {}).get("status"),
                    "error": read.get("error"),
                },
            )
            loaded, _ = request(restarted, 9, "thread/loaded/list", {}, deadline)
            record(
                "replacement-loaded-list",
                {
                    "containsThread": thread_id
                    in loaded.get("result", {}).get("data", [])
                },
            )
        finally:
            stop(restarted)


if __name__ == "__main__":
    main()
