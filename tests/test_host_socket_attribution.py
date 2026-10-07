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
    preflight_frames_error,
    request_record,
    responder_log,
    responder_reply,
)


@pytest.mark.parametrize(
    ("rows", "error"),
    [
        (
            [
                {"classification": "tool", "has_bash": True},
                {"classification": "final", "has_bash": True},
            ],
            None,
        ),
        (
            [
                {"classification": "side-request", "has_bash": False},
                {"classification": "tool", "has_bash": True},
                {"classification": "follow-up", "has_bash": False},
                {"classification": "final", "has_bash": True},
            ],
            None,
        ),
        (
            [{"classification": "tool", "has_bash": True}],
            "expected one Bash tool and final frame",
        ),
        (
            [
                {"classification": "tool", "has_bash": True},
                {"classification": "tool", "has_bash": True},
                {"classification": "final", "has_bash": True},
            ],
            "expected one Bash tool and final frame",
        ),
        (
            [
                {"classification": "tool", "has_bash": False},
                {"classification": "final", "has_bash": True},
            ],
            "Bash frame was not served to the Bash request",
        ),
        (
            [
                {"classification": "final", "has_bash": True},
                {"classification": "tool", "has_bash": True},
            ],
            "final frame preceded Bash tool frame",
        ),
        (
            [
                {"classification": "tool", "has_bash": True},
                {"classification": "side-request", "has_bash": True},
                {"classification": "final", "has_bash": True},
            ],
            "unexpected request or Bash side request",
        ),
        (
            [
                {"classification": "tool", "has_bash": True},
                {"classification": "retry", "has_bash": False},
                {"classification": "final", "has_bash": True},
            ],
            "unexpected request or Bash side request",
        ),
    ],
)
def test_preflight_frames_error(
    rows: list[dict[str, object]], error: str | None
) -> None:
    assert preflight_frames_error(rows) == error


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


def model_body(profile: str, phase: str) -> dict[str, object]:
    python = (
        "/Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3"
        if profile.startswith("codex-")
        else "python3"
    )
    prompt = (
        f"Run {python} experiments/02-host-socket-attribution/probe.py client "
        f"/private/tmp/bv01-228-{profile}/gateway.sock {profile} and then stop."
    )
    if profile.startswith("codex-"):
        item = (
            {
                "type": "function_call_output",
                "call_id": "call-bv01",
                "output": "allowed",
            }
            if phase == "result"
            else {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt if phase == "prompt" else "Session title",
                    }
                ],
            }
        )
        return {"input": [item]}
    item = (
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_bv01",
                    "content": "allowed",
                }
            ],
        }
        if phase == "result"
        else {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                    if phase == "prompt"
                    else f"<session>\n{prompt}\n</session>\nWrite the title",
                }
            ],
        }
    )
    return {
        "messages": [item],
        "tools": [{"name": "Bash"}] if phase != "side" else [],
        "model": "claude-sonnet-4-5",
        **({"outputFormat": {"type": "json_schema"}} if phase == "side" else {}),
    }


@pytest.mark.parametrize(
    "profile",
    ["codex-interactive", "codex-headless", "claude-interactive", "claude-headless"],
)
def test_responder_routes_side_retry_and_follow_up(profile: str) -> None:
    path = "/v1/responses" if profile.startswith("codex-") else "/v1/messages"

    def reply(
        phase: str, tool: bool = False, final: bool = False
    ) -> tuple[int, str | None, str]:
        return responder_reply(
            ResponderRequest(
                "POST",
                path,
                "127.0.0.1:1234",
                1234,
                profile,
                model_body(profile, phase),
                tool,
                final,
            )
        )

    side = f"{'codex' if profile.startswith('codex-') else 'claude'}-side.sse"
    assert reply("side") == (200, side, "side-request")
    assert reply("prompt") == (200, f"{profile}-tool.sse", "tool")
    assert reply("prompt", tool=True) == (200, side, "retry")
    assert reply("result", tool=True) == (200, f"{profile}-final.sse", "final")
    assert reply("result") == (200, side, "follow-up")
    assert reply("result", tool=True, final=True) == (200, side, "follow-up")
    assert reply("side", tool=True, final=True) == (200, side, "follow-up")


@pytest.mark.parametrize("order", [("side", "prompt"), ("prompt", "side")])
def test_claude_title_request_never_consumes_tool_frame(
    order: tuple[str, str],
) -> None:
    tool_served = False
    routes = []
    for phase in order:
        status, _fixture, route = responder_reply(
            ResponderRequest(
                "POST",
                "/v1/messages",
                "127.0.0.1:1234",
                1234,
                "claude-interactive",
                model_body("claude-interactive", phase),
                tool_served,
            )
        )
        assert status == 200
        routes.append(route)
        tool_served |= route == "tool"
    assert routes == (
        ["side-request", "tool"] if order[0] == "side" else ["tool", "follow-up"]
    )
    assert responder_reply(
        ResponderRequest(
            "POST",
            "/v1/messages",
            "127.0.0.1:1234",
            1234,
            "claude-interactive",
            model_body("claude-interactive", "result"),
            True,
        )
    ) == (200, "claude-interactive-final.sse", "final")


@given(st.lists(st.text().filter(lambda name: name != "Bash"), max_size=5))
def test_claude_without_bash_never_routes_tool(tool_names: list[str]) -> None:
    body = model_body("claude-interactive", "prompt")
    body["tools"] = [{"name": name} for name in tool_names]
    assert (
        responder_reply(
            ResponderRequest(
                "POST",
                "/v1/messages",
                "127.0.0.1:1234",
                1234,
                "claude-interactive",
                body,
            )
        )[2]
        != "tool"
    )


@pytest.mark.parametrize(
    "body",
    [
        None,
        {},
        {"input": [None, {"role": "assistant", "content": "probe.py client"}]},
        {"input": [{"role": "user", "content": None}]},
        {"input": [{"role": "user", "content": [None]}]},
    ],
)
def test_responder_does_not_route_unstructured_or_spoofed_input_to_tool(
    body: object,
) -> None:
    status, fixture, classification = responder_reply(
        ResponderRequest(
            "POST", "/v1/responses", "127.0.0.1:1234", 1234, "codex-headless", body
        )
    )
    assert (status, fixture, classification) == (
        200,
        "codex-side.sse",
        "side-request",
    )


def test_responder_accepts_string_input_prompt() -> None:
    prompt = (
        "Run /Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3 "
        "experiments/02-host-socket-attribution/probe.py client "
        "/private/tmp/bv01-228-codex-headless/gateway.sock codex-headless and then stop."
    )
    assert responder_reply(
        ResponderRequest(
            "POST",
            "/v1/responses",
            "127.0.0.1:1234",
            1234,
            "codex-headless",
            {"input": prompt},
        )
    ) == (200, "codex-headless-tool.sse", "tool")


def test_codex_ignores_claude_tool_result_shape() -> None:
    body = {
        "input": [
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "toolu_bv01"}],
            }
        ]
    }
    assert responder_reply(
        ResponderRequest(
            "POST",
            "/v1/responses",
            "127.0.0.1:1234",
            1234,
            "codex-headless",
            body,
            True,
        )
    ) == (200, "codex-side.sse", "follow-up")


@pytest.mark.parametrize(
    ("profile", "path"),
    [("claude-headless", "/v1/messages"), ("claude-interactive", "/api/hello")],
)
def test_claude_head_probe(profile: str, path: str) -> None:
    assert responder_reply(
        ResponderRequest("HEAD", path, "127.0.0.1:1234", 1234, profile)
    ) == (200, None, "probe")


@pytest.mark.parametrize(
    ("case", "status"),
    [
        (ResponderRequest("HEAD", "/", "127.0.0.1:1234", 1234, "claude-headless"), 403),
        (
            ResponderRequest(
                "GET", "/v1/responses", "127.0.0.1:1234", 1234, "codex-headless"
            ),
            403,
        ),
        (
            ResponderRequest(
                "POST", "/v1/responses?x=1", "127.0.0.1:1234", 1234, "codex-headless"
            ),
            403,
        ),
        (
            ResponderRequest(
                "POST", "/v1/responses", "elsewhere:1234", 1234, "codex-headless"
            ),
            403,
        ),
        (
            ResponderRequest("POST", "/v1/responses", "127.0.0.1:1234", 1234, "wrong"),
            400,
        ),
        (
            ResponderRequest(
                "POST",
                "/v1/responses",
                "127.0.0.1:1234",
                1234,
                "codex-headless",
                content_length="-1",
            ),
            403,
        ),
        (
            ResponderRequest(
                "POST",
                "/v1/responses",
                "127.0.0.1:1234",
                1234,
                "codex-headless",
                content_length="1",
                transfer_encoding="chunked",
            ),
            403,
        ),
    ],
)
def test_responder_rejects_invalid_request(case: ResponderRequest, status: int) -> None:
    assert responder_reply(case) == (status, None, "invalid")


@given(st.text(), st.text(), st.integers(min_value=100, max_value=599))
def test_responder_log_redacts_unknown_path(
    method: str, path: str, status: int
) -> None:
    row = responder_log(method, path, status)
    assert row == {
        "method": method if method in {"POST", "HEAD", "GET", "PUT"} else "<rejected>",
        "path": path
        if path
        in {"/v1/responses", "/v1/messages", "/v1/messages?beta=true", "/api/hello"}
        else "<rejected>",
        "status": status,
        "classification": "invalid",
    }
    assert (
        responder_log(method, path, status, "tool.sse", "tool")["fixture"] == "tool.sse"
    )


def test_responder_log_records_only_bounded_shape() -> None:
    prompt = "private prompt marker"
    body = {
        "model": "claude-sonnet-4-5",
        "tools": [{"name": "Bash"}],
        "outputFormat": {"schema": {"description": prompt}},
        "messages": [{"content": prompt}],
    }
    row = responder_log("POST", "/v1/messages", 200, "tool.sse", "tool", body=body)
    assert row["tool_count"] == 1
    assert row["has_bash"] is True
    assert row["model"] == "claude-sonnet-4-5"
    assert row["has_output_format"] is True
    assert prompt not in json.dumps(row)
    assert (
        responder_log("POST", "/v1/messages", 200, body={"model": prompt})["model"]
        == "<rejected>"
    )


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
    python = (
        "/Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3"
        if profile.startswith("codex-")
        else "python3"
    )
    command = (
        f"{python} experiments/02-host-socket-attribution/probe.py client "
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


@pytest.mark.parametrize("harness", ["codex", "claude"])
def test_side_frame_contains_text_and_no_tool_call(harness: str) -> None:
    frame = (RESPONDER_FIXTURES / f"{harness}-side.sse").read_bytes()
    events = [
        json.loads(line[6:])
        for line in frame.splitlines()
        if line.startswith(b"data: ")
    ]
    assert frame.endswith(b"\n\n: end\n")
    assert b"OK." in frame
    if harness == "codex":
        items = [
            event["item"]
            for event in events
            if event["type"] == "response.output_item.done"
        ]
        assert [item["type"] for item in items] == ["message"]
    else:
        blocks = [
            event["content_block"]
            for event in events
            if event["type"] == "content_block_start"
        ]
        assert [block["type"] for block in blocks] == ["text"]


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
@pytest.mark.parametrize(
    ("profile", "responder_process"),
    [
        (profile, profile)
        for profile in (
            "codex-interactive",
            "codex-headless",
            "claude-interactive",
            "claude-headless",
        )
    ],
    indirect=["responder_process"],
)
def test_responder_routes_full_conversation(
    profile: str,
    responder_process: tuple[subprocess.Popen[str], Path, int],
) -> None:
    _process, log, port = responder_process
    path = "/v1/responses" if profile.startswith("codex-") else "/v1/messages?beta=true"
    side = f"{'codex' if profile.startswith('codex-') else 'claude'}-side.sse"
    cases = [
        ("side", side, "side-request"),
        ("prompt", f"{profile}-tool.sse", "tool"),
        ("prompt", side, "retry"),
        ("result", f"{profile}-final.sse", "final"),
        ("result", side, "follow-up"),
        ("side", side, "follow-up"),
    ]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("POST", f"{path}?secret-marker", body=b"{}")
        response = connection.getresponse()
        assert response.status == 403
        assert response.read() == b""
        connection.request(
            "POST", path, body=b"{}", headers={"Host": "outside.example"}
        )
        response = connection.getresponse()
        assert response.status == 403
        assert response.read() == b""
        for phase, fixture, _classification in cases:
            body = json.dumps(model_body(profile, phase))
            connection.request("POST", path, body=body)
            response = connection.getresponse()
            assert response.status == 200
            assert response.read() == (RESPONDER_FIXTURES / fixture).read_bytes()
        connection.request("PUT", path, body=b"body-marker")
        response = connection.getresponse()
        assert response.status == 501
        response.read()
    finally:
        connection.close()
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert [row["classification"] for row in rows] == [
        "invalid",
        "invalid",
        *(item[2] for item in cases),
        "invalid",
    ]
    assert [row.get("fixture") for row in rows] == [
        None,
        None,
        *(item[1] for item in cases),
        None,
    ]
    assert rows[0]["path"] == "<rejected>"
    assert all(
        set(row)
        <= {
            "method",
            "path",
            "status",
            "fixture",
            "classification",
            "tool_count",
            "has_bash",
            "model",
            "has_output_format",
        }
        for row in rows
    )
    assert "secret-marker" not in log.read_text()
    assert "body-marker" not in log.read_text()
    assert "<session>" not in log.read_text()


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
            body = (
                json.dumps(model_body("claude-headless", "prompt"))
                if method == "POST"
                else b"body-marker"
            )
            connection.request(method, path, body=body, headers=headers)
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
            ("HEAD", "<rejected>", 403),
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
