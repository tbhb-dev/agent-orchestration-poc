"""Loopback REST integration for fixture-only operator acknowledgement."""

import json
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, cast, override

import pytest

FIXTURES = Path(__file__).parent / "fixtures/operator-commands"
REPOSITORY = "tbhb-dev/agent-orchestration-poc"


class Handler(BaseHTTPRequestHandler):
    """Serve fixed GitHub-shaped responses and record side effects."""

    payload: dict[str, Any]
    posts: list[tuple[str, dict[str, Any]]]
    reactions: list[dict[str, Any]]

    @override
    def log_message(self, format: str, *args: object) -> None:
        """Keep fixture requests out of test output."""

    def do_GET(self) -> None:
        """Return source comment, item, paginated asks, or reactions."""
        base = f"/repos/{REPOSITORY}"
        number = self.payload["item"]["number"]
        comment_id = self.payload["comment"]["id"]
        if self.path == f"{base}/issues/comments/{comment_id}":
            result = self.payload["comment"]
        elif self.path == f"{base}/issues/{number}":
            result = self.payload["item"]
        elif self.path == f"{base}/issues/{number}/comments?per_page=100":
            result = [{"id": 1, "body": "older comment"}]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header(
                "Link",
                f'<http://127.0.0.1:{self.server.server_port}{base}/issues/{number}/comments?page=2>; rel="next"',  # type: ignore[attr-defined] HTTPServer port
            )
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return
        elif self.path == f"{base}/issues/{number}/comments?page=2":
            result = [self.payload["ask"]]
        elif self.path == f"{base}/issues/comments/{comment_id}/reactions?per_page=100":
            result = self.reactions
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_POST(self) -> None:
        """Record additive label and reaction requests."""
        length = int(self.headers["Content-Length"])
        payload = cast("dict[str, Any]", json.loads(self.rfile.read(length)))
        self.posts.append((self.path, payload))
        if self.path.endswith("/reactions"):
            self.reactions.append(
                {
                    "content": payload["content"],
                    "user": {"login": "github-actions[bot]"},
                }
            )
        elif self.path.endswith("/labels"):
            self.payload["item"]["labels"].append({"name": "operator/replied"})
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")


@pytest.fixture
def api() -> Iterator[tuple[str, type[Handler]]]:
    """Start a GitHub-shaped HTTP server on loopback only."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", Handler
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()


@pytest.mark.integration
@pytest.mark.parametrize("item_type", ["issue", "pr"])
def test_valid_repeated_delivery(
    api: tuple[str, type[Handler]], monkeypatch: pytest.MonkeyPatch, item_type: str
) -> None:
    from agent_orchestration_poc.shell import (  # noqa: PLC0415 mutmut copies core only
        operator_commands as shell,
    )

    base, handler = api
    handler.payload = cast(
        "dict[str, Any]", json.loads((FIXTURES / f"{item_type}.json").read_text())
    )
    handler.posts = []
    handler.reactions = []
    number = handler.payload["item"]["number"]
    monkeypatch.setattr(
        shell, "FIXTURE_PR" if item_type == "pr" else "FIXTURE_ISSUE", number
    )
    event = handler.payload["event"] | {
        "issue": handler.payload["item"],
        "comment": {"id": 100},
    }
    assert shell.process(event, "fixture-token", base).reaction == "+1"
    assert shell.process(event, "fixture-token", base).reaction == "+1"
    handler.payload["ask"]["updated_at"] = "2026-09-28T12:02:00Z"
    assert shell.process(event, "fixture-token", base).reaction == "confused"
    assert handler.posts == [
        (
            f"/repos/{REPOSITORY}/issues/comments/100/reactions",
            {"content": "+1"},
        ),
        (
            f"/repos/{REPOSITORY}/issues/{number}/labels",
            {"labels": ["operator/replied"]},
        ),
    ]


@pytest.mark.integration
def test_invalid_and_outside_gate(
    api: tuple[str, type[Handler]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from agent_orchestration_poc.shell import (  # noqa: PLC0415 mutmut copies core only
        operator_commands as shell,
    )

    base, handler = api
    handler.payload = cast(
        "dict[str, Any]", json.loads((FIXTURES / "issue.json").read_text())
    )
    handler.posts = []
    handler.reactions = []
    monkeypatch.setattr(shell, "FIXTURE_ISSUE", 11)
    event = handler.payload["event"] | {
        "issue": handler.payload["item"],
        "comment": {"id": 100},
    }
    assert (
        shell.process(
            event | {"issue": {"number": 999}}, "fixture-token", base
        ).reaction
        is None
    )
    handler.payload["comment"]["body"] = "/approve lines=8"
    assert shell.process(event, "fixture-token", base).reaction == "confused"
    assert shell.process(event, "fixture-token", base).reaction == "confused"
    assert len(handler.posts) == 1
    assert handler.posts[0][1] == {"content": "confused"}
