"""Value-only tests for the fixture's attribution decision."""

import http.client
import json
import os
import runpy
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import IO

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.host_socket_attribution import (
    Peer,
    Process,
    ResponderRequest,
    membership,
    peer_stable,
    request_record,
    responder_log,
    responder_reply,
)

REPOSITORY = Path(__file__).resolve().parents[1]
if REPOSITORY.name == "mutants":
    REPOSITORY = REPOSITORY.parent
RESPONDER_FIXTURES = (
    REPOSITORY / "experiments/02-host-socket-attribution/fixtures/responder"
)


@pytest.mark.parametrize(
    ("peer_pid", "observed", "root", "expected"),
    [
        (3, {3: Process(3, 2, 30), 2: Process(2, 1, 20)}, Process(2, 1, 20), "allowed"),
        (3, {3: Process(3, 4, 30), 4: Process(4, 1, 20)}, Process(2, 1, 20), "unknown"),
        (3, {3: Process(3, 2, 30), 2: Process(2, 1, 21)}, Process(2, 1, 20), "stale"),
        (
            3,
            {3: Process(3, 2, 101), 2: Process(2, 1, 20)},
            Process(2, 1, 20),
            "unknown",
        ),
        (3, {3: Process(3, 3, 30)}, Process(2, 1, 20), "unknown"),
        (3, {}, Process(2, 1, 20), "unknown"),
    ],
)
def test_membership_cases(
    peer_pid: int, observed: dict[int, Process], root: Process, expected: str
) -> None:
    assert membership(Peer(peer_pid, 7, 100), root, observed) == expected


def test_process_started_at_acceptance_is_allowed() -> None:
    root = Process(2, 1, 20)
    child = Process(3, 2, 30)
    assert membership(Peer(3, 7, 30), root, {2: root, 3: child}) == "allowed"


@given(
    st.integers(min_value=2, max_value=100_000), st.integers(min_value=1, max_value=99)
)
def test_membership_direct_child(pid: int, start: int) -> None:
    root = Process(pid, 1, start)
    child = Process(pid + 100_001, pid, start + 1)
    assert (
        membership(Peer(child.pid, 1, 100), root, {root.pid: root, child.pid: child})
        == "allowed"
    )


@given(
    st.integers(min_value=2, max_value=100_000), st.integers(min_value=1, max_value=99)
)
def test_membership_reused_root_rejected(pid: int, start: int) -> None:
    root = Process(pid, 1, start)
    child = Process(pid + 100_001, pid, start + 1)
    replacement = Process(pid, 1, start + 1)
    assert (
        membership(
            Peer(child.pid, 1, 100), root, {root.pid: replacement, child.pid: child}
        )
        == "stale"
    )


@pytest.mark.parametrize(
    ("initial", "later", "expected"),
    [
        (Peer(2, 7, 10), Peer(2, 7, 20), True),
        (Peer(2, 7, 10), Peer(3, 8, 20), False),
        (Peer(2, 7, 10), Peer(2, 8, 20), False),
    ],
)
def test_peer_stable(initial: Peer, later: Peer, expected: bool) -> None:
    assert peer_stable(initial, later) is expected


@given(st.integers(min_value=1), st.integers(min_value=1))
def test_peer_stable_rejects_new_version(pid: int, version: int) -> None:
    assert not peer_stable(Peer(pid, version, 1), Peer(pid, version + 1, 2))


@pytest.mark.parametrize(
    ("before", "after", "root", "observed", "expected"),
    [
        (
            Peer(3, 7, 100),
            Peer(3, 7, 101),
            Process(2, 1, 20),
            {3: Process(3, 2, 30), 2: Process(2, 1, 20)},
            "allowed",
        ),
        (
            Peer(3, 7, 100),
            Peer(3, 8, 101),
            Process(2, 1, 20),
            {3: Process(3, 2, 30), 2: Process(2, 1, 20)},
            "changed-peer",
        ),
        (
            Peer(3, 7, 100),
            Peer(3, 7, 101),
            Process(2, 1, 20),
            {3: Process(3, 4, 30)},
            "unknown",
        ),
    ],
)
def test_request_record(
    before: Peer,
    after: Peer,
    root: Process,
    observed: dict[int, Process],
    expected: str,
) -> None:
    result = request_record("listener:4", "case-A", (before, after), root, observed)
    assert result == {
        "connection_id": "listener:4",
        "case_tag": "case-A",
        "initial": {
            "pid": before.pid,
            "pidversion": before.pidversion,
            "accepted_us": before.accepted_us,
        },
        "peer": {
            "pid": after.pid,
            "pidversion": after.pidversion,
            "accepted_us": after.accepted_us,
        },
        "root": {"pid": root.pid, "ppid": root.ppid, "start_us": root.start_us},
        "observed": [
            {"pid": value.pid, "ppid": value.ppid, "start_us": value.start_us}
            for value in observed.values()
        ],
        "decision": expected,
    }


@given(st.integers(min_value=2), st.text(), st.integers(min_value=1))
def test_request_record_preserves_values(pid: int, tag: str, version: int) -> None:
    root = Process(pid, 1, 1)
    peer = Peer(pid, version, 2)
    record = request_record("one", tag, (peer, peer), root, {pid: root})
    assert record["decision"] == "allowed"
    assert record["case_tag"] == tag
    assert record["initial"] == record["peer"]


@pytest.mark.parametrize(
    ("req", "expected"),
    [
        (
            ResponderRequest(
                "POST", "/v1/responses", "127.0.0.1:1234", 1234, "codex-headless", 0
            ),
            (200, "codex-headless-tool.sse"),
        ),
        (
            ResponderRequest(
                "POST", "/v1/messages", "127.0.0.1:1234", 1234, "claude-interactive", 1
            ),
            (200, "claude-interactive-final.sse"),
        ),
        (
            ResponderRequest(
                "POST",
                "/v1/messages?beta=true",
                "127.0.0.1:1234",
                1234,
                "claude-headless",
                0,
            ),
            (200, "claude-headless-tool.sse"),
        ),
        (
            ResponderRequest(
                "HEAD", "/v1/messages", "127.0.0.1:1234", 1234, "claude-headless", 0
            ),
            (200, None),
        ),
        (
            ResponderRequest(
                "HEAD", "/api/hello", "127.0.0.1:1234", 1234, "claude-interactive", 0
            ),
            (200, None),
        ),
        (
            ResponderRequest("HEAD", "/", "127.0.0.1:1234", 1234, "claude-headless", 0),
            (403, None),
        ),
        (
            ResponderRequest(
                "HEAD", "/v1/messages", "elsewhere:1234", 1234, "claude-headless", 0
            ),
            (403, None),
        ),
        (
            ResponderRequest(
                "GET", "/v1/responses", "127.0.0.1:1234", 1234, "codex-headless", 0
            ),
            (403, None),
        ),
        (
            ResponderRequest(
                "POST", "/v1/responses?x=1", "127.0.0.1:1234", 1234, "codex-headless", 0
            ),
            (403, None),
        ),
        (
            ResponderRequest(
                "POST", "/v1/responses", "elsewhere:1234", 1234, "codex-headless", 0
            ),
            (403, None),
        ),
        (
            ResponderRequest(
                "POST", "/v1/responses", "127.0.0.1:1234", 1234, "codex-headless", 2
            ),
            (409, None),
        ),
        (
            ResponderRequest(
                "POST", "/v1/responses", "127.0.0.1:1234", 1234, "wrong", 0
            ),
            (400, None),
        ),
        (
            ResponderRequest(
                "POST",
                "/v1/responses",
                "127.0.0.1:1234",
                1234,
                "codex-headless",
                0,
                "-1",
            ),
            (403, None),
        ),
        (
            ResponderRequest(
                "POST",
                "/v1/responses",
                "127.0.0.1:1234",
                1234,
                "codex-headless",
                0,
                "1",
                "chunked",
            ),
            (403, None),
        ),
    ],
)
def test_responder_reply(
    req: ResponderRequest,
    expected: tuple[int, str | None],
) -> None:
    assert responder_reply(req) == expected


@given(st.integers(min_value=1, max_value=65535), st.integers(min_value=2))
def test_responder_reply_exhausted(port: int, completed: int) -> None:
    assert responder_reply(
        ResponderRequest(
            "POST",
            "/v1/messages",
            f"127.0.0.1:{port}",
            port,
            "claude-headless",
            completed,
        )
    ) == (409, None)


@given(st.text(), st.text(), st.integers(min_value=100, max_value=599))
def test_responder_log_preserves_request_line(
    method: str, path: str, status: int
) -> None:
    assert responder_log(method, path, status) == {
        "method": method,
        "path": path,
        "status": status,
    }


@pytest.mark.parametrize(
    "profile",
    ["codex-interactive", "codex-headless", "claude-interactive", "claude-headless"],
)
def test_committed_frames_request_one_profile_command(profile: str) -> None:
    fixture_dir = RESPONDER_FIXTURES
    tool = (fixture_dir / f"{profile}-tool.sse").read_bytes()
    final = (fixture_dir / f"{profile}-final.sse").read_bytes()
    assert tool.endswith(b"\n\n: end\n")
    assert final.endswith(b"\n\n: end\n")
    events = [
        json.loads(line[6:]) for line in tool.splitlines() if line.startswith(b"data: ")
    ]
    command = (
        f"python3 experiments/02-host-socket-attribution/probe.py client "
        f"/private/tmp/bv01-228-{profile}/gateway.sock {profile}"
    )
    if profile.startswith("codex-"):
        calls = [
            event["item"]
            for event in events
            if event["type"] == "response.output_item.done"
        ]
        assert len(calls) == 1
        assert calls[0]["name"] == "exec_command"
        assert json.loads(calls[0]["arguments"])["cmd"] == command
    else:
        deltas = [
            event["delta"] for event in events if event["type"] == "content_block_delta"
        ]
        assert len(deltas) == 1
        assert json.loads(deltas[0]["partial_json"])["command"] == command
    assert command.encode() not in final


@pytest.mark.integration
@pytest.mark.parametrize(
    "profile",
    ["codex-interactive", "codex-headless", "claude-interactive", "claude-headless"],
)
def test_disposable_connector_imports_copied_package(profile: str) -> None:
    with tempfile.TemporaryDirectory(prefix="bv01-", dir="/tmp") as directory:
        workspace = Path(directory) / "workspace"
        probe_dir = workspace / "experiments/02-host-socket-attribution"
        probe_dir.mkdir(parents=True)
        shutil.copyfile(
            REPOSITORY / "experiments/02-host-socket-attribution/probe.py",
            probe_dir / "probe.py",
        )
        package = workspace / "agent_orchestration_poc"
        (package / "core").mkdir(parents=True)
        for relative in (
            "__init__.py",
            "core/__init__.py",
            "core/host_socket_attribution.py",
        ):
            shutil.copyfile(
                REPOSITORY / "src/agent_orchestration_poc" / relative,
                package / relative,
            )
        socket_path = Path(directory) / "gateway.sock"
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(socket_path))
            listener.listen(1)
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-S",
                    "experiments/02-host-socket-attribution/probe.py",
                    "client",
                    str(socket_path),
                    profile,
                ],
                cwd=workspace,
                env={
                    "PATH": os.environ["PATH"],
                    "PYTHONSAFEPATH": "1",
                    "PYTHONPATH": str(workspace),
                },
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                empty: list[socket.socket] = []
                ready, _, _ = select.select([listener], empty, empty, 5)
                if not ready:
                    _output, errors = process.communicate(timeout=5)
                    pytest.fail(
                        f"disposable connector did not reach the socket: {errors}"
                    )
                conn, _ = listener.accept()
                with conn:
                    assert conn.recv(512).decode() == profile
                    conn.sendall(b"allowed")
                output, errors = process.communicate(timeout=5)
                assert process.returncode == 0, errors
                assert output.strip() == "allowed"
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                if process.stdout is not None:
                    process.stdout.close()
                if process.stderr is not None:
                    process.stderr.close()


@pytest.fixture
def responder_process(
    request: pytest.FixtureRequest,
) -> Iterator[tuple[subprocess.Popen[str], Path, int]]:
    with tempfile.TemporaryDirectory(prefix="bv01-", dir="/tmp") as directory:
        log = Path(directory) / "model.jsonl"
        process = subprocess.Popen(
            [
                sys.executable,
                "experiments/02-host-socket-attribution/model_responder.py",
                "--host",
                "127.0.0.1",
                "--port",
                "0",
                "--profile",
                getattr(request, "param", "codex-headless"),
                "--log",
                str(log),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONSAFEPATH": "1"},
        )
        try:
            assert process.stdout is not None
            empty: list[IO[str]] = []
            ready, _, _ = select.select([process.stdout], empty, empty, 5)
            assert ready, "responder did not announce its port"
            announcement = json.loads(process.stdout.readline())
            assert announcement["host"] == "127.0.0.1"
            yield process, log, announcement["port"]
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()


@pytest.mark.integration
def test_responder_loopback_and_fixed_frames(
    responder_process: tuple[subprocess.Popen[str], Path, int],
) -> None:
    _process, log, port = responder_process
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    fixture_dir = RESPONDER_FIXTURES
    cases: list[tuple[str, dict[str, str], int, bytes]] = [
        ("/v1/responses?query-marker", {}, 403, b""),
        ("/v1/responses", {"Host": "outside.example"}, 403, b""),
        (
            "/v1/responses",
            {},
            200,
            (fixture_dir / "codex-headless-tool.sse").read_bytes(),
        ),
        (
            "/v1/responses",
            {},
            200,
            (fixture_dir / "codex-headless-final.sse").read_bytes(),
        ),
        ("/v1/responses", {}, 409, b""),
    ]
    try:
        for path, headers, expected_status, expected_body in cases:
            connection.request("POST", path, body=b"body-marker", headers=headers)
            response = connection.getresponse()
            assert response.status == expected_status
            assert response.read() == expected_body
        rows = [json.loads(line) for line in log.read_text().splitlines()]
        assert [row["status"] for row in rows] == [403, 403, 200, 200, 409]
        assert rows[0]["path"] == "/v1/responses?query-marker"
        assert all(set(row) == {"method", "path", "status"} for row in rows)
        assert all(row["method"] == "POST" for row in rows)
        assert "body-marker" not in log.read_text()
        connection.request("PUT", "/v1/responses", body=b"body-marker")
        rejected = connection.getresponse()
        assert rejected.status == 501
        rejected.read()
        assert json.loads(log.read_text().splitlines()[-1]) == {
            "method": "PUT",
            "path": "/v1/responses",
            "status": 501,
        }
    finally:
        connection.close()


@pytest.mark.integration
@pytest.mark.parametrize("responder_process", ["claude-headless"], indirect=True)
def test_responder_claude_startup_requests(
    responder_process: tuple[subprocess.Popen[str], Path, int],
) -> None:
    handler = runpy.run_path(
        str(REPOSITORY / "experiments/02-host-socket-attribution/model_responder.py")
    )["RequestHandler"]
    assert callable(handler.do_HEAD)
    _process, log, port = responder_process
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        for method, path, host, expected_status in (
            ("HEAD", "/api/hello", None, 200),
            ("HEAD", "/v1/messages", None, 200),
            ("HEAD", "/", None, 403),
            ("HEAD", "/v1/messages", "outside.example", 403),
            ("POST", "/v1/messages?beta=true", None, 200),
        ):
            headers = {"Host": host} if host else {}
            connection.request(method, path, body=b"body-marker", headers=headers)
            response = connection.getresponse()
            assert response.status == expected_status
            body = response.read()
            assert body == (
                (RESPONDER_FIXTURES / "claude-headless-tool.sse").read_bytes()
                if method == "POST"
                else b""
            )
        rows = [json.loads(line) for line in log.read_text().splitlines()]
        assert [(row["method"], row["path"], row["status"]) for row in rows] == [
            ("HEAD", "/api/hello", 200),
            ("HEAD", "/v1/messages", 200),
            ("HEAD", "/", 403),
            ("HEAD", "/v1/messages", 403),
            ("POST", "/v1/messages?beta=true", 200),
        ]
        assert "body-marker" not in log.read_text()
        assert "outside.example" not in log.read_text()
    finally:
        connection.close()


@pytest.mark.socket
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS LOCAL_PEERTOKEN only")
def test_listener_records_peer_and_root() -> None:
    with tempfile.TemporaryDirectory(prefix="bv01-", dir="/tmp") as directory:
        path = Path(directory) / "gateway.sock"
        probe = "experiments/02-host-socket-attribution/probe.py"
        server = subprocess.Popen(
            [sys.executable, probe, "server", str(path), str(os.getpid()), "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONSAFEPATH": "1"},
        )
        try:
            deadline = time.monotonic() + 5
            while not path.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert path.exists(), "listener did not bind its temporary socket"
            client = subprocess.run(
                [sys.executable, probe, "client", str(path), "listener-case"],
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, "PYTHONSAFEPATH": "1"},
            )
            assert client.stdout.strip() == "allowed"
            output, errors = server.communicate(timeout=5)
            assert server.returncode == 0, errors
            record = json.loads(output)
            assert record["connection_id"].endswith(":1")
            assert record["case_tag"] == "listener-case"
            assert record["root"]["pid"] == os.getpid()
            assert record["root"]["start_us"] > 0
            assert record["initial"]["pidversion"] == record["peer"]["pidversion"]
            assert record["peer"]["pid"] == record["observed"][0]["pid"]
            assert not path.exists()
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
            if server.stdout is not None:
                server.stdout.close()
            if server.stderr is not None:
                server.stderr.close()
