"""Plain-value and local Unix-socket tests for disposable M-001 targets."""

import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from runpy import run_path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
core = run_path(str(ROOT / "m001_core.py"))
m001 = run_path(str(ROOT / "m001.py"))


def test_safe_path_standalone_launch() -> None:
    result = subprocess.run(
        [
            "mise",
            "exec",
            "--",
            "uv",
            "run",
            "python",
            str(ROOT / "m001.py"),
            "--help",
        ],
        cwd=ROOT.parent.parent,
        env={**os.environ, "PYTHONSAFEPATH": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr  # noqa: S101 - documented launch.


@pytest.mark.parametrize("size", [125, 126, 127])
def test_wire_frame_lengths(size: int) -> None:
    source, target = socket.socketpair()
    with source, target:
        m001["send_frame"](source, b"a" * size, masked=False)
        expected = bytes([0x81, size]) if size < 126 else b"\x81\x7e" + size.to_bytes(2)
        assert target.recv(4)[: len(expected)] == expected  # noqa: S101 - RFC wire bytes.


def test_wire_error_response_uses_short_length() -> None:
    source, target = socket.socketpair()
    payload = json.dumps(core["queue_response"](None), separators=(",", ":")).encode()
    with source, target:
        m001["send_frame"](source, payload, masked=False)
        assert target.recv(2) == bytes([0x81, len(payload)])  # noqa: S101 - RFC wire bytes.


def test_independent_127_byte_frame_decodes() -> None:
    source, target = socket.socketpair()
    with source, target:
        source.sendall(b"\x81\x7e\x00\x7f" + b"a" * 127)
        assert m001["frame"](target, masked=False) == b"a" * 127  # noqa: S101 - independent frame.


@pytest.mark.parametrize("size", [0, 1, 125, 126, 127, 4096])
def test_core_frame_round_trip(size: int) -> None:
    payload = b"z" * size
    key = b"abcd"
    wire = core["encode_frame"](payload, key)
    extension = core["frame_extension_size"](wire[:2], True)
    header = wire[: 2 + extension]
    assert core["frame_length"](header, True) == size  # noqa: S101 - plain frame length.
    assert core["decode_frame"](wire[2 + extension + 4 :], key, True) == payload  # noqa: S101 - mask rule.


@pytest.mark.parametrize("wire", [b"\x81\x7e\x00\x7d", b"\x81\x7f" + (126).to_bytes(8)])
def test_core_rejects_nonminimal_frame_length(wire: bytes) -> None:
    with pytest.raises(ValueError, match="nonminimal"):
        core["frame_length"](wire, False)


def test_core_upgrade_and_reply() -> None:
    nonce = "dGhlIHNhbXBsZSBub25jZQ=="
    response = core["upgrade_response"](core["upgrade_request"](nonce))
    assert core["valid_upgrade_response"](response, nonce)  # noqa: S101 - nonce binding.
    assert not core["valid_upgrade_response"](  # noqa: S101 - wrong nonce.
        response, base64.b64encode(b"0" * 16).decode()
    )
    with pytest.raises(ValueError, match="invalid WebSocket upgrade"):
        core["upgrade_response"](b"GET /wrong HTTP/1.1\r\n\r\n")
    payload, outcome = core["queue_reply"](b"invalid json")
    assert outcome == "invalid"  # noqa: S101 - invalid request decision.
    assert json.loads(payload)["error"]["code"] == -32600  # noqa: S101 - response bytes.


def test_core_client_bytes_and_mcp_result() -> None:
    assert json.loads(core["queue_request_bytes"]()) == core["queue_request"]()  # noqa: S101 - request bytes.
    assert core["cc_line"]().endswith(b"\n")  # noqa: S101 - NDJSON delimiter.
    assert json.loads(core["cc_line"]()) == core["cc_frame"]()  # noqa: S101 - peer bytes.
    result = core["mcp_probe_response"](7, "PermissionError")
    assert result["id"] == 7  # noqa: S101 - call correlation.
    assert result["result"]["isError"]  # noqa: S101 - blocked result.
    assert (  # noqa: S101 - outcome classification.
        json.loads(result["result"]["content"][0]["text"])["classification"]
        == "blocked"
    )


def test_websocket_accept_rfc_example() -> None:
    assert (  # noqa: S101 - RFC 6455 known answer.
        core["websocket_accept"]("dGhlIHNhbXBsZSBub25jZQ==")
        == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
    )


@given(st.binary().filter(lambda value: len(value) != 16))
def test_websocket_accept_rejects_bad_nonce(value: bytes) -> None:
    with pytest.raises(ValueError, match="invalid WebSocket key"):
        core["websocket_accept"](base64.b64encode(value).decode())


def test_queue_exact_request_and_response() -> None:
    request = cast("dict[str, Any]", core["queue_request"]())
    assert request["method"] == "thread/queue/add"  # noqa: S101 - protocol assertion.
    assert (  # noqa: S101 - protocol assertion.
        core["queue_response"](request)["result"]["queuedSubmission"][
            "clientUserMessageId"
        ]
        == request["params"]["clientUserMessageId"]
    )
    assert (  # noqa: S101 - protocol assertion.
        core["queue_response"]({"method": "thread/queue/add"})["error"]["code"]
        == -32600
    )


@given(st.dictionaries(st.text(), st.text()))
def test_queue_never_accepts_arbitrary_request(value: dict[str, str]) -> None:
    assert "result" not in core["queue_response"](value)  # noqa: S101 - exact fixture request.


@pytest.mark.parametrize(
    ("line", "expected"), [(b"{}", "invalid"), (b"not-json", "invalid")]
)
def test_cc_rejects_invalid_frame(line: bytes, expected: str) -> None:
    assert core["cc_result"](line) == expected  # noqa: S101 - protocol assertion.


def test_cc_accepts_exact_frame() -> None:
    frame = core["cc_frame"]()
    assert frame["type"] == "user"  # noqa: S101 - protocol assertion.
    assert core["cc_result"](json.dumps(frame).encode()) == "accepted"  # noqa: S101 - protocol assertion.


@given(st.binary())
def test_cc_acceptance_is_exact(value: bytes) -> None:
    if core["cc_result"](value) == "accepted":
        assert json.loads(value) == core["cc_frame"]()  # noqa: S101 - protocol assertion.


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        ("accepted", "allowed"),
        ("EPERM", "blocked"),
        ("EACCES", "blocked"),
        ("PermissionError", "blocked"),
        ("sent", "inconclusive"),
        ("invalid", "inconclusive"),
    ],
)
def test_classify(outcome: str, expected: str) -> None:
    assert core["classify"](outcome) == expected  # noqa: S101 - result boundary.


@given(
    st.text().filter(
        lambda value: value not in {"accepted", "EPERM", "EACCES", "PermissionError"}
    )
)
def test_classify_unknown_is_inconclusive(value: str) -> None:
    assert core["classify"](value) == "inconclusive"  # noqa: S101 - result boundary.


@pytest.mark.parametrize(
    ("message", "kind"),
    [
        ({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, None),
        ({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, None),
        (
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "probe_queue"},
            },
            "queue",
        ),
        (
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "probe_cc_socks"},
            },
            "cc-socks",
        ),
        ({"jsonrpc": "2.0", "id": 5, "method": "bogus"}, None),
        ({"jsonrpc": "2.0", "method": "notifications/initialized"}, None),
    ],
)
def test_mcp_action(message: dict[str, Any], kind: str | None) -> None:
    response, selected = core["mcp_action"](message)
    assert selected == kind  # noqa: S101 - pure MCP decision.
    if "id" in message and kind is None:
        assert response is not None  # noqa: S101 - protocol correlation.
        assert response["id"] == message["id"]  # noqa: S101 - protocol correlation.
    else:
        assert response is None  # noqa: S101 - notification or deferred tool call.


@given(st.text().filter(lambda value: value not in {"probe_queue", "probe_cc_socks"}))
def test_mcp_unknown_tool_never_probes(name: str) -> None:
    response, kind = core["mcp_action"](
        {"id": 7, "method": "tools/call", "params": {"name": name}}
    )
    assert kind is None  # noqa: S101 - no probe for unknown tool.
    assert response["error"]["code"] == -32601  # noqa: S101 - no probe for unknown tool.


@pytest.mark.parametrize("kind", ["queue", "cc-socks"])
def test_disposable_target_protocol(kind: str) -> None:
    with tempfile.TemporaryDirectory(
        prefix="m001-test-", dir="/private/tmp"
    ) as temporary:
        root = Path(temporary)
        path = root / "B.sock"
        log = root / "target.jsonl"
        worker = threading.Thread(target=m001["serve"], args=(path, kind, 1, log))
        worker.start()
        for _ in range(100):
            if path.exists():
                break
            time.sleep(0.01)
        assert path.exists()  # noqa: S101 - socket readiness.
        for _ in range(100):
            try:
                outcome = (
                    m001["queue_client"](path)
                    if kind == "queue"
                    else m001["cc_client"](path)
                )
                break
            except ConnectionRefusedError:
                time.sleep(0.01)
        else:
            pytest.fail("target did not start listening")
        worker.join(timeout=5)
        assert not worker.is_alive()  # noqa: S101 - server ended after one exchange.
        assert outcome == ("accepted" if kind == "queue" else "sent")  # noqa: S101 - client result.
        assert json.loads(log.read_text()) == {"kind": kind, "outcome": "accepted"}  # noqa: S101 - target parsed protocol.


@pytest.mark.parametrize(
    "profile",
    ["codex-interactive", "codex-headless", "claude-interactive", "claude-headless"],
)
def test_responder_tool_frame_targets_own_home(profile: str) -> None:
    content = (ROOT / "fixtures" / "responder" / f"{profile}-tool.sse").read_text()
    messages = [
        json.loads(line.removeprefix("data: "))
        for line in content.splitlines()
        if line.startswith("data: ")
    ]
    if profile.startswith("codex-"):
        item = next(
            message["item"]
            for message in messages
            if message["type"] == "response.output_item.done"
        )
        command = json.loads(item["arguments"])["cmd"]
    else:
        delta = next(
            message["delta"]
            for message in messages
            if message["type"] == "content_block_delta"
        )
        command = json.loads(delta["partial_json"])["command"]
    home = f"/private/tmp/bv01-228-{profile}"
    assert command.count(f"{home}/B/") == 2  # noqa: S101 - exact target scope.
    assert "send queue" in command  # noqa: S101 - queue write.
    assert "send cc-socks" in command  # noqa: S101 - peer write.


@pytest.mark.parametrize("surface", ["mcp", "hook"])
def test_child_surface_sends_both_protocols(surface: str) -> None:
    with tempfile.TemporaryDirectory(
        prefix="m001-child-", dir="/private/tmp"
    ) as temporary:
        home = Path(temporary)
        (home / "B").mkdir()
        servers = []
        for kind in ("queue", "cc-socks"):
            path = home / "B" / f"{kind}-m001.sock"
            log = home / f"{kind}.jsonl"
            server = threading.Thread(target=m001["serve"], args=(path, kind, 1, log))
            server.start()
            servers.append(server)
        for _ in range(100):
            if all(
                (home / "B" / f"{kind}-m001.sock").exists()
                for kind in ("queue", "cc-socks")
            ):
                break
            time.sleep(0.01)
        calls = [
            {
                "jsonrpc": "2.0",
                "id": index,
                "method": "tools/call",
                "params": {"name": name},
            }
            for index, name in enumerate(("probe_queue", "probe_cc_socks"), 1)
        ]
        input_text = (
            "{}\n"
            if surface == "hook"
            else "".join(json.dumps(call) + "\n" for call in calls)
        )
        child = subprocess.run(
            [sys.executable, str(ROOT / "m001.py"), surface, "none", str(home)],
            input=input_text,
            capture_output=True,
            text=True,
            check=True,
        )
        for server in servers:
            server.join(timeout=5)
            assert not server.is_alive()  # noqa: S101 - child reached both targets.
        for kind in ("queue", "cc-socks"):
            assert (  # noqa: S101 - target parsed full protocol.
                json.loads((home / f"{kind}.jsonl").read_text())["outcome"]
                == "accepted"
            )
        if surface == "mcp":
            assert len(child.stdout.splitlines()) == 2  # noqa: S101 - MCP replied to both tool calls.
        else:
            assert child.stdout.strip() == "{}"  # noqa: S101 - hook left decision unchanged.
