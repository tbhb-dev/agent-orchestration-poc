"""Pure webhook decision tests and loopback receiver tests."""
# ruff: noqa: INP001, S101, D103

import hashlib
import hmac
import http.client
import json
import socket
import threading
import uuid
from datetime import UTC, datetime, timedelta
from http.server import HTTPServer
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from receiver import Handler
from state import (
    REPOSITORY_ID,
    classify_delivery,
    expiry,
    freshness,
    invalidate_component,
    signature_result,
)
from store import Store

ROOT = Path(__file__).resolve().parents[1]
BODY = (ROOT / "tests/fixtures/receiver/pull_request.json").read_bytes().strip()
SECRET = b"synthetic-test-secret"


@pytest.mark.parametrize(
    ("header", "result"),
    [
        (None, "missing"),
        ("sha256=bad", "malformed"),
        ("sha256=" + "g" * 64, "malformed"),
        ("sha256=" + "0" * 64, "invalid"),
    ],
)
def test_signature_table(header: str | None, result: str) -> None:
    assert signature_result(header, BODY, SECRET) == result


@given(st.binary(max_size=1000), st.binary(min_size=1, max_size=40))
def test_signature_property(body: bytes, secret: bytes) -> None:
    signature = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    assert signature_result(signature, body, secret) == "valid"
    assert signature_result(signature, body + b"x", secret) == "invalid"


@pytest.mark.parametrize(
    ("event", "kind", "names"),
    [
        ("pull_request", "pr", ("identity", "checks", "reviews", "comments", "labels")),
        ("issues", "issue", ("identity", "comments", "labels")),
        ("unsupported", None, ()),
    ],
)
def test_classify_table(event: str, kind: str | None, names: tuple[str, ...]) -> None:
    payload = json.loads(BODY)
    payload["issue"] = {"number": 7}
    if event == "issues":
        payload["action"] = "opened"
    result = classify_delivery(event, json.dumps(payload).encode(), 42)
    assert (
        (result[0].kind, result[0].components) == (kind, names)
        if kind
        else result == ()
    )


@given(st.integers(min_value=1, max_value=100000))
def test_classify_property(number: int) -> None:
    payload = json.loads(BODY)
    payload["pull_request"]["number"] = number
    assert (
        classify_delivery("pull_request", json.dumps(payload).encode(), 42)[0].number
        == number
    )
    payload["repository"]["id"] = REPOSITORY_ID + 1
    with pytest.raises(ValueError, match="repository"):
        classify_delivery("pull_request", json.dumps(payload).encode(), 42)
    payload["repository"]["id"] = REPOSITORY_ID
    payload["action"] = "instruction_from_comment"
    assert classify_delivery("pull_request", json.dumps(payload).encode(), 42) == ()
    payload["installation"]["id"] = 0
    with pytest.raises(ValueError, match="number"):
        classify_delivery("pull_request", json.dumps(payload).encode(), 42)
    payload["installation"]["id"] = 43
    with pytest.raises(ValueError, match="installation"):
        classify_delivery("pull_request", json.dumps(payload).encode(), 42)


@pytest.mark.parametrize(
    ("complete", "reason", "expires", "expected"),
    [
        (False, None, None, "unknown"),
        (True, "dirty", None, "dirty"),
        (True, None, -1, "expired"),
        (True, None, 1, "fresh"),
    ],
)
def test_freshness_table(
    complete: bool, reason: str | None, expires: int | None, expected: str
) -> None:
    now = datetime.now(tz=UTC)
    end = (
        (now + timedelta(seconds=expires)).isoformat() if expires is not None else None
    )
    assert freshness(complete, reason, end, now) == expected


@given(st.integers(min_value=-100000, max_value=100000))
def test_expiry_and_freshness_property(seconds: int) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=seconds)
    assert expiry(now) == (now + timedelta(minutes=5)).isoformat()
    assert freshness(True, None, expiry(now), now) == "fresh"


def test_expiry_table() -> None:
    assert expiry(datetime(2026, 1, 1, tzinfo=UTC)) == "2026-01-01T00:05:00+00:00"


@pytest.mark.parametrize(
    ("current", "expected"), [((), (1, ("new",))), (("old",), (1, ("old", "new")))]
)
def test_invalidation_table(
    current: tuple[str, ...], expected: tuple[int, tuple[str, ...]]
) -> None:
    assert invalidate_component(0, current, "new") == expected


@given(st.integers(min_value=0), st.lists(st.text(min_size=1), max_size=100))
def test_invalidation_property(generation: int, current: list[str]) -> None:
    advanced, sources = invalidate_component(generation, tuple(current), "new")
    assert advanced == generation + 1
    assert sources[-1] == "new"
    assert len(sources) <= 32


@pytest.mark.integration
def test_loopback_receiver(tmp_path: Path) -> None:
    store = Store(tmp_path / "state.sqlite3")
    handler = type(
        "TestHandler",
        (Handler,),
        {"store": store, "secret": SECRET, "installation_id": 42},
    )
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        guid = str(uuid.uuid4())
        good = "sha256=" + hmac.new(SECRET, BODY, hashlib.sha256).hexdigest()

        def send(
            body: bytes, signature: str | None, path: str = "/hooks/github"
        ) -> int:
            conn = http.client.HTTPConnection(
                "127.0.0.1", server.server_port, timeout=3
            )
            headers = {
                "X-GitHub-Delivery": guid,
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            }
            if signature is not None:
                headers["X-Hub-Signature-256"] = signature
            conn.request("POST", path, body, headers)
            response = conn.getresponse()
            response.read()
            conn.close()
            return response.status

        assert send(BODY, None) == 401
        assert send(BODY, "sha256=bad") == 401
        assert send(BODY, "sha256=" + "0" * 64) == 401
        assert send(BODY, good, "/elsewhere") == 404
        probe = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        probe.request("GET", "/hooks/github")
        health = probe.getresponse()
        assert health.status == 405
        assert health.getheader("X-Local-Monitor-Schema") == "1"
        health.read()
        probe.close()
        assert send(BODY, good) == 202
        assert send(BODY, good) == 202
        changed = BODY + b" "
        changed_sig = "sha256=" + hmac.new(SECRET, changed, hashlib.sha256).hexdigest()
        assert send(changed, changed_sig) == 409
        assert store.status()["receipts"] == 1
        assert store.status()["signature_failures"] == {
            "missing": 1,
            "malformed": 1,
            "invalid": 1,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.integration
def test_incomplete_headers_release_single_receiver(tmp_path: Path) -> None:
    store = Store(tmp_path / "state.sqlite3")
    handler = type(
        "DeadlineHandler",
        (Handler,),
        {
            "store": store,
            "secret": SECRET,
            "installation_id": 42,
            "request_timeout": 0.25,
        },
    )
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    stalled = socket.create_connection(("127.0.0.1", server.server_port), timeout=2)
    try:
        stalled.sendall(b"POST /hooks/github HTTP/1.1\r\nHost: localhost\r\nX-Test: ")
        while stalled.recv(4096):
            pass
        probe = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        try:
            probe.request("GET", "/hooks/github")
            response = probe.getresponse()
            assert response.status == 405
            response.read()
        finally:
            probe.close()
    finally:
        stalled.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
