"""Fixture-backed repair decisions and loopback REST collection."""
# ruff: noqa: INP001, S101, D103

import json
import threading
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import override

import pytest
from hypothesis import given
from hypothesis import strategies as st
from repair import (
    authoritative,
    body_for_response,
    budget_handoff,
    capacity,
    complete,
    component_reason,
    digest,
    endpoints,
    next_page,
)
from rest_client import Client, principal_lock, repair_object
from state import Invalidation
from store import Store


@pytest.mark.parametrize(
    ("kind", "names"),
    [
        ("issue", {"issue", "issue_comments", "labels"}),
        (
            "pr",
            {
                "issue",
                "issue_comments",
                "pull",
                "labels",
                "reviews",
                "review_comments",
                "check_runs",
                "statuses",
            },
        ),
    ],
)
def test_endpoints(kind: str, names: set[str]) -> None:
    result = endpoints(kind, 7, "a" * 40 if kind == "pr" else None)
    assert {item.name for item in result} == names
    assert all("/7" in item.path or "a" * 40 in item.path for item in result)


@given(st.integers(min_value=1), st.integers(min_value=0))
def test_endpoint_scope(number: int, extra: int) -> None:
    result = endpoints("issue", number)
    assert len(result) == 3
    assert all("tbhb/agent-orchestration-poc" in item.path for item in result)
    assert extra >= 0


@pytest.mark.parametrize(
    ("headers", "spent", "pages", "reason"),
    [
        ({}, 0, 0, "unknown_headers"),
        (
            {
                "x-ratelimit-limit": "5000",
                "x-ratelimit-remaining": "101",
                "x-ratelimit-resource": "core",
            },
            0,
            0,
            None,
        ),
        (
            {
                "x-ratelimit-limit": "5000",
                "x-ratelimit-remaining": "100",
                "x-ratelimit-resource": "core",
            },
            0,
            0,
            "reserve",
        ),
        (
            {
                "x-ratelimit-limit": "5000",
                "x-ratelimit-remaining": "6000",
                "x-ratelimit-resource": "core",
            },
            0,
            0,
            "contradictory_headers",
        ),
        ({}, 20, 0, "request_or_page_cap"),
        ({}, 0, 10, "request_or_page_cap"),
    ],
)
def test_capacity(
    headers: dict[str, str], spent: int, pages: int, reason: str | None
) -> None:
    assert capacity(headers, spent, pages) == reason


@given(
    st.integers(min_value=101, max_value=5000), st.integers(min_value=0, max_value=19)
)
def test_capacity_property(remaining: int, spent: int) -> None:
    headers = {
        "x-ratelimit-limit": "5000",
        "x-ratelimit-remaining": str(remaining),
        "x-ratelimit-resource": "core",
    }
    assert capacity(headers, spent, 0) is None


def test_budget_handoff() -> None:
    record = budget_handoff(
        "installation:165297562:core",
        {
            "x-ratelimit-resource": "core",
            "x-ratelimit-limit": "5000",
            "x-ratelimit-remaining": "4000",
        },
        6,
        6,
    )
    assert record["principal"] == "installation:165297562:core"
    assert record["remaining"] == "4000"
    assert record["requests"] == record["pages"] == 6


@given(st.integers(min_value=0), st.integers(min_value=0))
def test_budget_handoff_property(requests: int, pages: int) -> None:
    result = budget_handoff("installation:1:core", {}, requests, pages)
    assert (result["requests"], result["pages"]) == (requests, pages)
    assert result["resource"] is None


@pytest.mark.parametrize(
    ("status", "saved", "etag", "expected"),
    [
        (200, None, None, b"new"),
        (304, ('"a"', b"old"), '"a"', b"old"),
        (304, ('"a"', b"old"), '"b"', None),
        (304, None, '"a"', None),
    ],
)
def test_body_for_response(
    status: int,
    saved: tuple[str, bytes] | None,
    etag: str | None,
    expected: bytes | None,
) -> None:
    assert body_for_response(status, b"new", saved, etag) == expected


@given(st.binary(), st.text())
def test_304_property(body: bytes, etag: str) -> None:
    assert body_for_response(304, b"", (etag, body), etag) == body


def test_digests_and_authority() -> None:
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})
    assert authoritative(
        "issue", ({"id": 1, "body": "a", "state": "open"},)
    ) != authoritative("issue", ({"id": 1, "body": "b", "state": "open"},))
    pull = {"head": {"sha": "a"}, "base": {"sha": "b"}, "state": "open"}
    assert authoritative("pull", (pull,)) != authoritative(
        "pull", ({**pull, "head": {"sha": "c"}},)
    )
    assert (
        complete(
            {"pull": authoritative("pull", (pull,))},
            {"pull": authoritative("pull", ({**pull, "head": {"sha": "c"}},))},
            1,
            1,
        )
        == "changed_pull"
    )
    assert authoritative("issue_comments", ([{"body": "a"}],)) != authoritative(
        "issue_comments", ([{"body": "b"}],)
    )


@given(st.integers(), st.integers())
def test_generation_property(captured: int, current: int) -> None:
    assert (complete({}, {}, captured, current) is None) == (captured == current)


@pytest.mark.parametrize(
    ("initial", "final", "captured", "current", "reason"),
    [
        ({"issue": "a"}, {"issue": "a"}, 1, 1, None),
        ({"issue": "a"}, {"issue": "b"}, 1, 1, "changed_issue"),
        ({"issue_comments": "a"}, {}, 1, 1, "changed_issue_comments"),
        ({}, {}, 1, 2, "invalidation_during_collection"),
    ],
)
def test_complete(
    initial: dict[str, str],
    final: dict[str, str],
    captured: int,
    current: int,
    reason: str | None,
) -> None:
    assert complete(initial, final, captured, current) == reason


@pytest.mark.parametrize(
    ("component", "reason"),
    [
        ("identity", None),
        ("checks", "latest_attempt_selection_unsupported"),
        ("reviews", "review_thread_resolution_unsupported"),
    ],
)
def test_component_reason(component: str, reason: str | None) -> None:
    assert component_reason(component, None, 1, 1) == reason


@given(st.integers(), st.integers())
def test_component_reason_property(captured: int, current: int) -> None:
    assert (component_reason("identity", None, captured, current) is None) == (
        captured == current
    )


@given(st.text())
def test_digest_property(value: str) -> None:
    assert digest(value) == digest(value)
    assert len(digest(value)) == 64


@given(st.text(), st.text())
def test_authoritative_issue_property(first: str, second: str) -> None:
    one = authoritative("issue", ({"id": 1, "body": first},))
    two = authoritative("issue", ({"id": 1, "body": second},))
    assert (one == two) == (first == second)


def test_next_page() -> None:
    assert (
        next_page('<https://api.github.com/x?page=2>; rel="next"')
        == "https://api.github.com/x?page=2"
    )
    assert next_page('<https://api.github.com/x?page=1>; rel="prev"') is None


@given(st.text())
def test_next_page_property(text: str) -> None:
    result = next_page(text)
    assert result is None or result in text


@pytest.mark.integration
def test_principal_lock_serializes_bootstrap(tmp_path: Path) -> None:
    entered = threading.Event()
    release = threading.Event()
    second = threading.Event()
    path = tmp_path / "principal.lock"

    def first() -> None:
        with principal_lock(path):
            entered.set()
            release.wait(timeout=3)

    def later() -> None:
        entered.wait(timeout=3)
        with principal_lock(path):
            second.set()

    one = threading.Thread(target=first)
    two = threading.Thread(target=later)
    one.start()
    two.start()
    assert entered.wait(timeout=3)
    assert not second.wait(timeout=0.05)
    release.set()
    one.join(timeout=3)
    two.join(timeout=3)
    assert second.is_set()


@pytest.mark.integration
def test_conditional_pages_and_missing_page(tmp_path: Path) -> None:
    counts: defaultdict[str, int] = defaultdict(int)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            counts[self.path] += 1
            status = 304 if self.headers.get("If-None-Match") == '"v1"' else 200
            if "page=2" in self.path and counts[self.path] == 2:
                status = 404
            body = json.dumps([{"id": 1}]).encode() if status == 200 else b""
            self.send_response(status)
            self.send_header("ETag", '"v1"')
            self.send_header("x-ratelimit-limit", "5000")
            self.send_header("x-ratelimit-remaining", "4000")
            self.send_header("x-ratelimit-resource", "core")
            if self.path == "/x":
                self.send_header(
                    "Link",
                    f'<http://127.0.0.1:{server.server_port}/x?page=2>; rel="next"',
                )
            self.end_headers()
            self.wfile.write(body)

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        client = Client(
            f"http://127.0.0.1:{server.server_port}",
            "fixture",
            tmp_path / "cache.json",
            0,
        )
        client.headers = {
            "x-ratelimit-limit": "5000",
            "x-ratelimit-remaining": "4000",
            "x-ratelimit-resource": "core",
        }
        assert len(client.get("/x")) == 2
        with pytest.raises(RuntimeError, match="incomplete_http_404"):
            client.get("/x")
        assert counts["/x"] == 2
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("changed", "reason"),
    [
        ("issue", "changed_issue"),
        ("comments", "changed_issue_comments"),
        ("invalidation", "invalidation_during_collection"),
    ],
)
def test_issue_change_without_webhook_and_restart(
    tmp_path: Path, changed: str, reason: str
) -> None:
    calls: defaultdict[str, int] = defaultdict(int)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            calls[self.path] += 1
            value: object = []
            if self.path.endswith("/issues/7"):
                value = {
                    "id": 7,
                    "body": "changed"
                    if changed == "issue" and calls[self.path] > 1
                    else "first",
                    "state": "open",
                }
            if "/issues/7/comments" in self.path:
                if changed == "invalidation" and calls[self.path] == 1:
                    store.receive(
                        "race-guid",
                        "issues",
                        b"fixture",
                        (Invalidation("issue", 7, ("identity",)),),
                    )
                value = [
                    {
                        "id": 8,
                        "body": "changed"
                        if changed == "comments" and calls[self.path] > 1
                        else "first",
                    }
                ]
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("ETag", f'"{calls[self.path]}"')
            self.send_header("x-ratelimit-limit", "5000")
            self.send_header("x-ratelimit-remaining", "4000")
            self.send_header("x-ratelimit-resource", "core")
            self.end_headers()
            self.wfile.write(body)

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        store = Store(tmp_path / "store.sqlite3")
        store.track("issue", 7)
        store.restart()
        client = Client(
            f"http://127.0.0.1:{server.server_port}",
            "fixture",
            tmp_path / "cache.json",
            0,
        )
        client.headers = {
            "x-ratelimit-limit": "5000",
            "x-ratelimit-remaining": "4000",
            "x-ratelimit-resource": "core",
        }
        item = store.snapshot()["objects"][0]
        report = repair_object(client, store, item)
        assert report["requests"] == 5
        assert report["pages"] == 5
        assert report["components"]["identity"]["unknown_reason"] == reason
        assert store.snapshot()["objects"][0]["components"][1]["stale_reason"] == (
            "dirty" if changed == "invalidation" else "restart"
        )
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()
