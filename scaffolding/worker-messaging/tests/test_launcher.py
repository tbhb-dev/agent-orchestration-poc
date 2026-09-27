"""Temporary #176 registry and command tests; #28 replaces this scaffold."""
# ruff: noqa: S101

import json
import subprocess
import sys
from pathlib import Path

import cli
import launcher
import pytest
import registry
from adapters import codex_launch


def test_registry_roundtrip(tmp_path: Path) -> None:
    """Versioned rows survive a restart without storing prompt text."""
    path = tmp_path / "registry.json"
    assert registry.read(path) == []
    registry.write(path, [{"run_id": "one", "state": "starting"}])
    assert registry.read(path) == [{"run_id": "one", "state": "starting"}]
    assert path.stat().st_mode & 0o777 == 0o600


def test_existing_worktree_needs_recorded_owner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A checkout left by another worker cannot be adopted."""
    monkeypatch.setattr(
        launcher,
        "_run",
        lambda _argv: f"worktree {tmp_path}\nbranch refs/heads/tooling/176-worker",
    )
    with pytest.raises(ValueError, match="not available"):
        launcher._worktree(tmp_path, "tooling/176-worker", owned=False)


def test_no_tmux_server_is_first_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    """The first launch reaches pane creation after a missing-server response."""
    calls: list[str] = []
    monkeypatch.setattr(launcher.registry, "read", lambda _path: [])
    monkeypatch.setattr(launcher.registry, "write", lambda _path, _rows: None)
    monkeypatch.setattr(Path, "read_text", lambda _self: "brief")
    monkeypatch.setattr(launcher, "_worktree", lambda _path, _branch, _owned: None)
    monkeypatch.setattr(
        launcher, "_new_pane", lambda _row, _brief: calls.append("pane") or {}
    )
    monkeypatch.setattr(launcher, "inspect", lambda row: (row, "blocked", "test"))
    monkeypatch.setattr(
        launcher.subprocess,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(
            args[0], 1, "", "no server running"
        ),
    )
    request = dict.fromkeys(("name", "branch", "worktree", "tmux_name"), "worker")
    request.update(harness="agy", model="m", effort="low", brief_file="/brief")
    launcher.launch(request)
    assert calls == ["pane"]


def test_first_pane_initializes_only_worker_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A clean tmux environment creates only the intended session."""
    commands: list[list[str]] = []

    def run(argv: list[str]) -> str:
        commands.append(argv)
        return "%1"

    monkeypatch.setattr(launcher, "_run", run)
    monkeypatch.setattr(launcher, "_pane", lambda _pane_id: {})
    monkeypatch.setattr(launcher, "_command", lambda _row, _brief: "exec worker")
    monkeypatch.setattr(
        launcher.subprocess,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(
            args[0], 1, "", "no server running"
        ),
    )
    launcher._new_pane({"name": "alice", "worktree": "/worker"}, "brief")
    assert commands[0] == [
        "tmux",
        "new-session",
        "-d",
        "-s",
        "worker-messaging",
        "-n",
        "control",
    ]
    assert commands[1][:7] == [
        "tmux",
        "new-window",
        "-d",
        "-P",
        "-F",
        "#{pane_id}",
        "-t",
    ]


@pytest.mark.parametrize(
    ("stderr", "stdout", "message"),
    [
        ("", "worker\n", "tmux window name already exists"),
        ("Operation not permitted", "", "tmux window observation failed"),
    ],
)
def test_launch_rejects_duplicate_or_failed_window_observation(
    monkeypatch: pytest.MonkeyPatch, stderr: str, stdout: str, message: str
) -> None:
    """Neither a duplicate nor an observation failure creates a checkout."""
    monkeypatch.setattr(launcher.registry, "read", lambda _path: [])
    monkeypatch.setattr(Path, "read_text", lambda _self: "brief")
    monkeypatch.setattr(
        launcher.subprocess,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(
            args[0], bool(stderr), stdout, stderr
        ),
    )
    request = dict.fromkeys(("name", "branch", "worktree", "tmux_name"), "worker")
    request.update(harness="agy", model="m", effort="low", brief_file="/brief")
    with pytest.raises(ValueError, match=message):
        launcher.launch(request)


@pytest.mark.parametrize("checkout", ["/repo", "/repo/.worktrees/worker"])
def test_command_from_main_or_linked_checkout(
    monkeypatch: pytest.MonkeyPatch, checkout: str
) -> None:
    """Git's common directory supplies the same shim and metadata path."""
    monkeypatch.setattr(launcher, "ROOT", Path(checkout))
    monkeypatch.setattr(launcher, "_run", lambda _argv: "/repo/.git")
    row = {"harness": "codex", "model": "m", "effort": "high", "worktree": "/new"}
    command = launcher._command(row, "brief")
    assert "--add-dir /repo/.git" in command
    assert "PATH=/repo/.holding/shim:" in command


class HandshakeConnection:
    """Supply only the WebSocket handshake to the adapter test."""

    def __init__(
        self, reply: bytes = b"HTTP/1.1 101 Switching Protocols\r\n\r\n"
    ) -> None:
        self.reply = bytearray(reply)

    def settimeout(self, _timeout: int) -> None:
        """Accept the adapter timeout."""

    def connect(self, _endpoint: str) -> None:
        """Accept the endpoint."""

    def sendall(self, _data: bytes) -> None:
        """Accept handshake and initialized frames."""

    def recv(self, count: int) -> bytes:
        """Return handshake bytes."""
        part = self.reply[:count]
        del self.reply[:count]
        return bytes(part)

    def close(self) -> None:
        """Close the fake connection."""


def test_loaded_inventory_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    """The adapter accepts string IDs across all loaded inventory pages."""
    calls: list[tuple[str, dict[str, object]]] = []

    def answer(
        _connection: object, _number: int, method: str, params: dict[str, object]
    ) -> dict[str, object]:
        calls.append((method, params))
        if method == "thread/loaded/list":
            if "cursor" in params:
                return {"data": ["thread-1"], "nextCursor": None}
            return {"data": ["other"], "nextCursor": "page-2"}
        if method == "thread/read":
            return {
                "thread": {
                    "id": "thread-1",
                    "cwd": "/worker",
                    "status": {"type": "active", "activeFlags": []},
                }
            }
        return {}

    monkeypatch.setattr(
        codex_launch.socket, "socket", lambda _family: HandshakeConnection()
    )
    monkeypatch.setattr(codex_launch, "_call", answer)
    loaded, thread = codex_launch.runtime_thread("/sock", "thread-1")
    assert loaded
    assert thread["status"]["type"] == "active"
    assert calls[2] == ("thread/loaded/list", {"limit": 100, "cursor": "page-2"})


@pytest.mark.parametrize("reply", [b"", b"HTTP/1.1 101 Switching Protocols\r\n\r\n"])
def test_socket_eof_persists_unknown_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    reply: bytes,
) -> None:
    """A closed handshake or frame produces a persisted machine-readable unknown."""
    store = tmp_path / "registry.json"
    row = {
        "run_id": "run-1",
        "state": "ready",
        "native_id": "thread-1",
        "worktree": "/worker",
        "branch": "tooling/176-worker",
    }
    registry.write(store, [row])
    monkeypatch.setattr(launcher, "STORE", store)
    monkeypatch.setattr(launcher, "_worktree", lambda *_args: None)
    monkeypatch.setattr(
        launcher,
        "_observe",
        lambda _row: codex_launch.runtime_thread("/sock", "thread-1"),
    )
    monkeypatch.setattr(
        codex_launch.socket, "socket", lambda _family: HandshakeConnection(reply)
    )
    monkeypatch.setattr(sys, "argv", ["worker", "status", "run-1"])
    assert cli.main() == 3
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "run_id": "run-1",
        "state": "unknown",
        "reason": "observation failed: EOFError",
    }
    assert registry.read(store)[0]["state"] == "unknown"
