"""Temporary #176 registry and command tests; #28 replaces this scaffold."""
# ruff: noqa: S101

import json
import socket
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path

import cli
import identity
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


def test_launch_syncs_vale_before_codex_trust_and_pane(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A new worktree gets pinned prose styles before its sandboxed TUI starts."""
    calls: list[str] = []
    monkeypatch.setattr(launcher, "STORE", tmp_path / "registry.json")
    monkeypatch.setattr(launcher, "_worktree", lambda *_args: True)
    monkeypatch.setattr(launcher, "_run", lambda _argv: "/repo/.git")
    brief = tmp_path / "brief.md"
    brief.write_text("brief")

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if argv[:2] == ["mise", "run"]:
            assert kwargs["cwd"] == Path("/repo/.worktrees/worker")
            calls.append("vale")
        return subprocess.CompletedProcess(argv, 1, "", "no server running")

    monkeypatch.setattr(launcher.subprocess, "run", run)
    monkeypatch.setattr(
        launcher,
        "_change_trust",
        lambda *_args, **_kwargs: calls.append("trust") or True,
    )
    monkeypatch.setattr(
        launcher, "_new_pane", lambda *_args: calls.append("pane") or {}
    )
    monkeypatch.setattr(launcher, "inspect", lambda row: (row, "ready", "test"))
    request = {
        "name": "worker",
        "issue": 176,
        "harness": "codex",
        "model": "gpt-6-sol",
        "effort": "high",
        "branch": "tooling/176-worker",
        "worktree": "/repo/.worktrees/worker",
        "tmux_name": "worker",
        "brief_file": str(brief),
        "endpoint": "unix:///private/tmp/fake.sock",
    }
    launcher.launch(request)
    assert calls == ["vale", "trust", "pane"]


def test_codex_launch_requires_endpoint_before_side_effects() -> None:
    """An omitted remote endpoint cannot create a worktree or tmux pane."""
    with pytest.raises(ValueError, match="explicit absolute"):
        launcher.launch({"harness": "codex", "brief_file": "/missing"})


def test_status_snapshot_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The shell reads a local status file, then pure code classifies it."""
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher, "_now", lambda: "2026-09-27T00:00:10+00:00")
    row = {"run_id": "one", "pane_generation": "generation"}
    path = tmp_path / ".local-cache/worker-messaging/status/one.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "run_id": "one",
                "generation": "generation",
                "last_seen_utc": "2026-09-27T00:00:00+00:00",
            }
        )
    )
    status = launcher.status_record(row)
    assert status["availability"] == "fresh"
    assert status["source"] == ".local-cache/worker-messaging/status/one.json"


def test_new_worktree_fetches_before_branching_from_origin_main(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A stale local main cannot become the new worker branch point."""
    commands: list[list[str]] = []

    def run(argv: list[str]) -> str:
        commands.append(argv)
        return "" if argv[1:3] == ["branch", "--list"] else "worktree /repo"

    monkeypatch.setattr(launcher, "_run", run)
    launcher._worktree(tmp_path / "worker", "tooling/176-worker", owned=False)
    assert commands[-2] == ["git", "fetch", "origin", "main"]
    assert commands[-1][-1] == "origin/main"


def test_missing_tmux_target_with_empty_success_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tmux 3.7b may return a successful reply with four empty fields."""
    monkeypatch.setattr(
        launcher.subprocess,
        "run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, "|||\n", ""),
    )
    assert launcher._pane("%missing") == {"tmux_missing": True}


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
    row = {
        "harness": "codex",
        "model": "m",
        "effort": "high",
        "worktree": "/new",
        "endpoint": "unix:///private/tmp/worker.sock",
    }
    command = launcher._command(row, "brief")
    assert "--remote unix:///private/tmp/worker.sock" in command
    assert "--add-dir" not in command
    assert "PATH=/repo/.holding/shim:" in command


class HandshakeConnection:
    """Supply only the WebSocket handshake to the adapter test."""

    def __init__(
        self, reply: bytes = b"HTTP/1.1 101 Switching Protocols\r\n\r\n"
    ) -> None:
        self.reply = bytearray(reply)
        self.timeout: int | None = None

    def settimeout(self, timeout: int) -> None:
        """Accept the adapter timeout."""
        self.timeout = timeout

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


def test_remote_socket_timeout_allows_slow_thread_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The observed 1.5 to 3 second list leaves room for server variance."""
    connection = HandshakeConnection()
    monkeypatch.setattr(codex_launch.socket, "socket", lambda _family: connection)
    monkeypatch.setattr(codex_launch, "_call", lambda *_args: {})
    assert codex_launch._connect("unix:///sock") is connection
    assert connection.timeout == 15


def test_remote_timeout_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A slow endpoint cannot leave a prior ready result eligible for sends."""
    row = {"harness": "codex", "native_id": "thread-1", "state": "ready"}

    def timed_out(_row: dict[str, object]) -> dict[str, object]:
        raise TimeoutError("slow endpoint")

    monkeypatch.setattr(launcher, "_observe", timed_out)
    _, state, reason = launcher.inspect(row)
    assert state == "unknown"
    assert reason == "observation failed: TimeoutError"


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
    loaded, thread = codex_launch.runtime_thread("unix:///sock", "thread-1")
    assert loaded
    assert thread["status"]["type"] == "active"
    assert calls[2] == ("thread/loaded/list", {"limit": 100, "cursor": "page-2"})


@pytest.mark.parametrize("loaded", [True, False])
def test_remote_inventory_on_temporary_unix_socket(loaded: bool) -> None:
    """The adapter queries the selected endpoint using the real socket protocol."""
    with tempfile.TemporaryDirectory(prefix="worker176-", dir="/private/tmp") as folder:
        path = f"{folder}/app.sock"
        server = socket.socket(socket.AF_UNIX)
        server.bind(path)
        server.listen(1)
        errors: list[Exception] = []
        methods: list[str] = []

        def serve() -> None:
            try:
                conn, _ = server.accept()
                with conn:
                    handshake = bytearray()
                    while not handshake.endswith(b"\r\n\r\n"):
                        handshake.extend(conn.recv(1))
                    conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\n\r\n")
                    while len(methods) < 4:
                        request = codex_launch._receive(conn)
                        method = request["method"]
                        methods.append(method)
                        if "id" not in request:
                            continue
                        result: dict[str, object] = {}
                        if method == "thread/loaded/list":
                            result = {
                                "data": ["thread-1"] if loaded else [],
                                "nextCursor": None,
                            }
                        if method == "thread/read":
                            result = {
                                "thread": {
                                    "id": "thread-1",
                                    "cwd": "/worker",
                                    "model": "gpt-6-sol",
                                    "reasoningEffort": "high",
                                    "status": {"type": "idle"},
                                }
                            }
                        conn.sendall(
                            codex_launch._frame({"id": request["id"], "result": result})
                        )
            except (OSError, EOFError, ValueError, KeyError) as error:
                errors.append(error)

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            actual, readback = codex_launch.runtime_thread(f"unix://{path}", "thread-1")
        finally:
            server.close()
            thread.join(timeout=5)
        assert not thread.is_alive()
        assert not errors
        assert actual is loaded
        assert readback["cwd"] == "/worker"
        assert methods == [
            "initialize",
            "initialized",
            "thread/loaded/list",
            "thread/read",
        ]


def _serve_fake_endpoint(
    server: socket.socket,
    replies: dict[str, dict[str, object]],
    methods: list[str],
    errors: list[Exception],
) -> None:
    """Answer requests on a disposable Unix socket with fixed results."""
    try:
        conn, _ = server.accept()
        with conn:
            handshake = bytearray()
            while not handshake.endswith(b"\r\n\r\n"):
                handshake.extend(conn.recv(1))
            conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\n\r\n")
            while True:
                try:
                    request = codex_launch._receive(conn)
                except EOFError:
                    break
                method = request["method"]
                methods.append(method)
                if "id" in request:
                    conn.sendall(
                        codex_launch._frame(
                            {"id": request["id"], "result": replies[method]}
                        )
                    )
    except (OSError, ValueError, KeyError) as error:
        errors.append(error)


@pytest.mark.parametrize(
    ("value", "failure"),
    [
        ("trusted", None),
        (None, None),
        ("trusted", "write_error"),
        ("trusted", "write_status"),
        ("trusted", "read_error"),
        ("trusted", "read_mismatch"),
        ("trusted", "preexisting"),
        ("trusted", "preflight_error"),
        (None, "read_mismatch"),
        (None, "read_error"),
    ],
)
def test_trust_write_and_readback_on_fake_endpoint(  # noqa: C901, PLR0915
    value: str | None, failure: str | None
) -> None:
    """Only the fake Unix endpoint receives exact trust edits and read-backs."""
    with tempfile.TemporaryDirectory(
        prefix="worker176-trust-", dir="/private/tmp"
    ) as folder:
        path = f"{folder}/app.sock"
        server = socket.socket(socket.AF_UNIX)
        server.bind(path)
        server.listen(1)
        server.settimeout(2)
        requests: list[dict[str, object]] = []
        errors: list[Exception] = []
        worktree = "/repo/.worktrees/worker"
        reads = 0
        pending: list[str] = []

        def serve() -> None:  # noqa: C901, PLR0912
            nonlocal reads
            try:
                conn, _ = server.accept()
                with conn:
                    handshake = bytearray()
                    while not handshake.endswith(b"\r\n\r\n"):
                        handshake.extend(conn.recv(1))
                    conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\n\r\n")
                    while True:
                        try:
                            request = codex_launch._receive(conn)
                        except EOFError:
                            break
                        requests.append(request)
                        if "id" not in request:
                            continue
                        method = request["method"]
                        if method == "config/batchWrite":
                            if pending != ["writing"]:
                                raise ValueError(
                                    "write reached server before registry phase"
                                )
                            response: dict[str, object] = {"status": "ok"}
                            if failure == "write_status":
                                response = {"status": "okOverridden"}
                        elif method == "config/read":
                            reads += 1
                            actual = (
                                "trusted"
                                if failure == "preexisting"
                                else None
                                if value is not None and reads == 1
                                else "untrusted"
                                if failure == "read_mismatch"
                                else value
                            )
                            projects = (
                                {worktree: {"trust_level": actual}}
                                if actual is not None or value is None
                                else {}
                            )
                            response = {"config": {"projects": projects}, "layers": []}
                        else:
                            response = {}
                        reply = {"id": request["id"], "result": response}
                        if failure == "write_error" and method == "config/batchWrite":
                            reply = {
                                "id": request["id"],
                                "error": {"message": "denied"},
                            }
                        if (
                            failure == "read_error"
                            and method == "config/read"
                            and reads == (2 if value is not None else 1)
                        ):
                            reply = {
                                "id": request["id"],
                                "error": {"message": "denied"},
                            }
                        if failure == "preflight_error" and method == "config/read":
                            reply = {
                                "id": request["id"],
                                "error": {"message": "denied"},
                            }
                        conn.sendall(codex_launch._frame(reply))
            except (OSError, ValueError, KeyError) as error:
                errors.append(error)

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            if failure:
                with pytest.raises(ValueError, match="config/|trust entry|preflight"):
                    codex_launch.change_trust(
                        f"unix://{path}",
                        worktree,
                        value,
                        lambda: pending.append("writing"),
                    )
            else:
                codex_launch.change_trust(
                    f"unix://{path}", worktree, value, lambda: pending.append("writing")
                )
        finally:
            server.close()
            thread.join(timeout=5)
        assert not thread.is_alive()
        assert not errors
        writes = [item for item in requests if item["method"] == "config/batchWrite"]
        if failure in {"preexisting", "preflight_error"}:
            assert writes == []
            assert pending == []
        else:
            assert writes[0]["params"] == identity.trust_write_params(worktree, value)
            assert pending == ["writing"]
        read_requests = [item for item in requests if item["method"] == "config/read"]
        assert all(
            item["params"] == {"cwd": worktree, "includeLayers": True}
            for item in read_requests
        )
        assert len(read_requests) == (
            (1 if value is not None else 0)
            + (
                0
                if failure
                in {"write_error", "write_status", "preexisting", "preflight_error"}
                else 1
            )
        )


@pytest.mark.parametrize("failure", [False, True])
def test_launch_trust_gate_precedes_pane(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: bool
) -> None:
    """A failed registration persists blocked state without starting a TUI."""
    store = tmp_path / "registry.json"
    calls: list[str] = []
    monkeypatch.setattr(launcher, "STORE", store)
    monkeypatch.setattr(launcher, "_worktree", lambda *_args: True)
    monkeypatch.setattr(launcher, "_run", lambda _argv: "/repo/.git")
    brief = tmp_path / "brief.md"
    brief.write_text("brief")
    monkeypatch.setattr(
        launcher.subprocess,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(
            args[0], 1, "", "no server running"
        ),
    )

    def change_trust(
        _endpoint: str,
        _worktree: str,
        _value: str | None,
        before_write: Callable[[], None],
    ) -> None:
        before_write()
        calls.append("trust")
        if failure:
            raise ValueError("write denied")

    monkeypatch.setattr(codex_launch, "change_trust", change_trust)
    monkeypatch.setattr(
        launcher, "_new_pane", lambda *_args: calls.append("pane") or {}
    )
    monkeypatch.setattr(launcher, "inspect", lambda row: (row, "ready", "test"))
    request = {
        "name": "worker",
        "issue": 176,
        "harness": "codex",
        "model": "gpt-6-sol",
        "effort": "high",
        "branch": "tooling/176-worker",
        "worktree": "/repo/.worktrees/worker",
        "tmux_name": "worker",
        "brief_file": str(brief),
        "endpoint": "unix:///private/tmp/fake.sock",
    }
    row, state, _ = launcher.launch(request)
    assert calls == (["trust"] if failure else ["trust", "pane"])
    assert state == ("blocked" if failure else "ready")
    assert row["trust_events"][0]["result"] == ("failed" if failure else "confirmed")
    assert registry.read(store)[0]["trust_events"] == row["trust_events"]


@pytest.mark.parametrize("path", ["/repo", "/repo/.worktrees", "/elsewhere/worker"])
def test_launch_rejects_non_worktree_trust_before_side_effects(path: str) -> None:
    """A main checkout, parent, or unrelated path cannot reach the endpoint."""
    request = {
        "harness": "codex",
        "endpoint": "unix:///private/tmp/fake.sock",
        "worktree": path,
    }
    with pytest.raises(ValueError, match="launcher-created"):
        launcher.launch(request)


@pytest.mark.parametrize("failure", [False, True])
def test_cleanup_removes_only_recorded_trust(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: bool
) -> None:
    """Cleanup records an exact removal attempt and blocks on readback failure."""
    path = "/repo/.worktrees/worker"
    row = {
        "run_id": "run-1",
        "harness": "codex",
        "worktree": path,
        "endpoint": "unix:///private/tmp/fake.sock",
        "trust_created": True,
        "trust_write_attempted": True,
        "git_common_dir": "/repo/.git",
        "trust_registered": True,
        "trust_events": [{"action": "register", "result": "confirmed"}],
    }
    store = tmp_path / "registry.json"
    registry.write(store, [row])
    monkeypatch.setattr(launcher, "STORE", store)
    calls: list[tuple[str, str, str | None]] = []

    def change(
        endpoint: str,
        worktree: str,
        value: str | None,
        before_write: Callable[[], None],
    ) -> None:
        before_write()
        calls.append((endpoint, worktree, value))
        if failure:
            raise ValueError("readback failed")

    monkeypatch.setattr(codex_launch, "change_trust", change)
    saved, state, _ = launcher.cleanup("run-1")
    assert calls == [(row["endpoint"], path, None)]
    assert state == ("blocked" if failure else "removed")
    assert saved["trust_events"][-1]["result"] == ("failed" if failure else "confirmed")
    assert registry.read(store)[0]["trust_events"][-1] == saved["trust_events"][-1]
    assert launcher.inspect(saved)[1] == "blocked"


@pytest.mark.parametrize(
    "error",
    [
        codex_launch.TrustConflictError("existing"),
        codex_launch.TrustPreflightError("unavailable"),
    ],
)
def test_prewrite_failure_is_never_removed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, error: ValueError
) -> None:
    """An existing entry or failed preflight grants no removal ownership."""
    row = {
        "run_id": "run-1",
        "harness": "codex",
        "worktree": "/repo/.worktrees/worker",
        "endpoint": "unix:///private/tmp/fake.sock",
        "trust_created": True,
        "git_common_dir": "/repo/.git",
    }
    store = tmp_path / "registry.json"
    monkeypatch.setattr(launcher, "STORE", store)
    monkeypatch.setattr(
        codex_launch,
        "change_trust",
        lambda *_args: (_ for _ in ()).throw(error),
    )
    assert not launcher._change_trust(row, [row], remove=False)
    assert not registry.read(store)[0].get("trust_write_attempted")
    with pytest.raises(ValueError, match="no launcher-owned"):
        launcher.cleanup("run-1")


@pytest.mark.parametrize("stage", ["preflight", "pending", "applied", "readback"])
def test_interrupted_trust_write_recovery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stage: str
) -> None:
    """Only a persisted pending edit can be cleaned up after interruption."""
    row = {
        "run_id": "run-1",
        "harness": "codex",
        "worktree": "/repo/.worktrees/worker",
        "endpoint": "unix:///private/tmp/fake.sock",
        "trust_created": True,
        "git_common_dir": "/repo/.git",
    }
    store = tmp_path / "registry.json"
    monkeypatch.setattr(launcher, "STORE", store)
    applied: list[str | None] = []

    def change(
        _endpoint: str,
        _worktree: str,
        value: str | None,
        before_write: Callable[[], None] | None = None,
    ) -> None:
        if value is None:
            applied.append(None)
            return
        if stage == "preflight":
            raise KeyboardInterrupt
        if before_write is not None:
            before_write()
        if stage == "pending":
            raise KeyboardInterrupt
        applied.append(value)
        if stage in {"applied", "readback"}:
            raise KeyboardInterrupt

    monkeypatch.setattr(codex_launch, "change_trust", change)
    with pytest.raises(KeyboardInterrupt):
        launcher._change_trust(row, [row], remove=False)
    saved = registry.read(store)[0]
    if stage == "preflight":
        assert not saved.get("trust_write_attempted")
        with pytest.raises(ValueError, match="no launcher-owned"):
            launcher.cleanup("run-1")
    else:
        assert saved["trust_write_attempted"] is True
        assert saved["trust_events"][-1]["result"] == "writing"
        assert launcher.cleanup("run-1")[1] == "removed"
        assert applied[-1] is None


@pytest.mark.parametrize(
    ("change", "state"),
    [
        ("matching", "ready"),
        ("wrong_id", "unknown"),
        ("wrong_cwd", "unknown"),
        ("wrong_read_cwd", "unknown"),
        ("unloaded", "unknown"),
        ("wrong_brief", "unknown"),
        ("newline_brief", "ready"),
        ("prefixed_brief", "ready"),
        ("missing_git_root", "unknown"),
    ],
)
def test_remote_discovery_without_tui_rollout(
    monkeypatch: pytest.MonkeyPatch, change: str, state: str
) -> None:
    """Readiness discovers the remote startup thread through its owning endpoint."""
    with tempfile.TemporaryDirectory(prefix="worker176-", dir="/private/tmp") as folder:
        path = f"{folder}/app.sock"
        server = socket.socket(socket.AF_UNIX)
        server.bind(path)
        server.listen(1)
        server.settimeout(2)
        methods: list[str] = []
        errors: list[Exception] = []
        brief = (
            "context\n## My request for Codex:\nfirst brief\n"
            if change == "prefixed_brief"
            else "first brief\n"
            if change == "newline_brief"
            else "first brief"
        )
        listed_id = "other" if change == "wrong_id" else "thread-1"
        cwd = "/other" if change == "wrong_cwd" else "/worker"
        read_cwd = "/other" if change == "wrong_read_cwd" else cwd
        preview = "other brief" if change == "wrong_brief" else "first brief"

        replies: dict[str, dict[str, object]] = {
            "initialize": {},
            "thread/list": {
                "data": [
                    {
                        "id": listed_id,
                        "cwd": cwd,
                        "createdAt": 1790470800,
                        "preview": preview,
                    }
                ],
                "nextCursor": None,
            },
            "thread/loaded/list": {
                "data": [] if change == "unloaded" else ["thread-1"],
                "nextCursor": None,
            },
            "thread/read": {
                "thread": {
                    "id": "thread-1",
                    "cwd": read_cwd,
                    "preview": preview,
                    "model": "gpt-6-sol",
                    "reasoningEffort": "high",
                    "status": {"type": "idle"},
                }
            },
            "thread/resume": {
                "thread": {"id": "thread-1"},
                "runtimeWorkspaceRoots": (
                    ["/other"] if change == "missing_git_root" else ["/repo/.git"]
                ),
            },
        }

        row = {
            "harness": "codex",
            "run_id": "run-1",
            "worktree": "/worker",
            "git_common_dir": "/repo/.git",
            "model": "gpt-6-sol",
            "effort": "high",
            "native_id": None,
            "brief_digest": identity.codex_brief_digest(brief),
            "launch_time": "2026-09-27T01:00:00+00:00",
            "endpoint": f"unix://{path}",
            "tmux_session": "worker-messaging",
            "tmux_window": "@7",
            "tmux_pane": "%13",
            "pane_generation": "%13:100:start",
            "pid": 100,
            "process_start": "start",
        }
        monkeypatch.setattr(
            launcher,
            "_pane",
            lambda _pane: {
                key: row[key]
                for key in (
                    "tmux_session",
                    "tmux_window",
                    "tmux_pane",
                    "pane_generation",
                    "pid",
                    "process_start",
                )
            },
        )
        monkeypatch.setattr(launcher, "_run", lambda _argv: "")
        thread = threading.Thread(
            target=_serve_fake_endpoint, args=(server, replies, methods, errors)
        )
        thread.start()
        try:
            _, actual, _ = launcher.inspect(row)
        finally:
            server.close()
            thread.join(timeout=5)
        assert not thread.is_alive()
        assert not errors
        assert actual == state
        assert "thread/list" in methods
        if state == "ready":
            assert row["native_id"] == "thread-1"
            assert methods[-3:] == [
                "thread/loaded/list",
                "thread/read",
                "thread/resume",
            ]
            assert row["runtime_workspace_roots"] == ["/repo/.git"]


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
        lambda _row: codex_launch.runtime_thread("unix:///sock", "thread-1"),
    )
    monkeypatch.setattr(
        codex_launch.socket, "socket", lambda _family: HandshakeConnection(reply)
    )
    monkeypatch.setattr(sys, "argv", ["worker", "status", "run-1"])
    assert cli.main() == 3
    output = json.loads(capsys.readouterr().out)
    assert {key: output[key] for key in ("run_id", "state", "reason")} == {
        "run_id": "run-1",
        "state": "unknown",
        "reason": "observation failed: EOFError",
    }
    assert output["endpoint"] is None
    assert output["observed_at"]
    assert registry.read(store)[0]["state"] == "unknown"


@pytest.mark.parametrize(
    ("raw", "decoded"),
    [("b'plain'", "plain"), ("bytes([0xff, 0xfe])", "\ufffd\ufffd")],
)
def test_subprocess_output_replaces_invalid_bytes(raw: str, decoded: str) -> None:
    """Non-UTF-8 process output remains an observation rather than an exception."""
    assert (
        launcher._run(
            [sys.executable, "-c", f"import sys; sys.stdout.buffer.write({raw})"]
        )
        == decoded
    )


@pytest.mark.parametrize(
    "stderr",
    [
        "can't find pane: %50",
        "can't find window: @2",
        "can't find session: worker-messaging",
        "no server running on /private/tmp/tmux-501/default",
        "error connecting to /private/tmp/tmux-501/default (No such file or directory)",
    ],
)
def test_missing_tmux_target_precedes_process_observation(
    monkeypatch: pytest.MonkeyPatch, stderr: str
) -> None:
    """A stopped target gets a specific reason without asking ps for a reused PID."""
    calls: list[list[str]] = []

    def run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 1, "", stderr)

    monkeypatch.setattr(launcher.subprocess, "run", run)
    row = {"tmux_pane": "%50", "endpoint": "/sock", "native_id": "thread-1"}
    _, state, reason = launcher.inspect(row)
    assert (state, reason) == ("unknown", "missing tmux target")
    assert [call[0] for call in calls] == ["tmux"]
