"""Loopback REST collection tests for the backfill checkpoint shell."""

import argparse
import hashlib
import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast, override

import pytest

FIXTURES = Path(__file__).parent / "fixtures/work_model_backfill"


@contextmanager
def server(
    responses: dict[str, tuple[list[Any] | dict[str, Any], bool]],
) -> Generator[str]:
    """Serve fixed JSON pages on loopback only."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = self.path
            if path not in responses:
                path = path.partition("?")[0]
            if path not in responses:
                self.send_error(404)
                return
            value, has_next = responses[path]
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-RateLimit-Remaining", "4999")
            if has_next:
                self.send_header(
                    "Link",
                    f'<http://127.0.0.1:{cast("ThreadingHTTPServer", self.server).server_port}/items?page=2>; rel="next"',
                )
            self.end_headers()
            self.wfile.write(body)

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    assert all(map(callable, (Handler.do_GET, Handler.log_message)))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


@pytest.mark.integration
def test_collects_every_linked_page_and_records_headers() -> None:
    """Both pages are returned with exact per-page receipts and safe ledger."""
    # Mutmut copies only the core package before collecting tests.
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
    )

    responses: dict[str, tuple[list[Any] | dict[str, Any], bool]] = {
        "/items?page=1": ([{"id": 1}], True),
        "/items?page=2": ([{"id": 2}], False),
    }
    with server(responses) as base:
        api = Api(base, "")
        items, pages = api.pages("items?page=1", "items")
    assert items == [{"id": 1}, {"id": 2}]
    assert [(page.index, page.count, page.total_pages) for page in pages] == [
        (1, 1, 2),
        (2, 1, 2),
    ]
    assert all(entry["status"] == 200 for entry in api.ledger)


@pytest.mark.integration
def test_refuses_unlinked_full_page() -> None:
    """A possible missing next page cannot be treated as complete."""
    # Mutmut copies only the core package before collecting tests.
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
    )

    with (
        server({"/items": ([{"id": index} for index in range(100)], False)}) as base,
        pytest.raises(ValueError, match="full page has no next link"),
    ):
        Api(base, "").pages("items", "items")


@pytest.mark.integration
def test_initial_checkpoint_uses_rest_gets_only(tmp_path: Path) -> None:
    """A complete loopback CP1 yields the reviewed plan and a safe ledger."""
    # Mutmut copies only the core package before collecting tests.
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        run,
    )

    fixture = json.loads((FIXTURES / "runner/initial.json").read_text())
    responses = {path: (value, False) for path, value in fixture.items()}
    plan = FIXTURES / "plan"
    paths = {name: plan / f"{name}.tsv" for name in ("assignments", "parents", "edges")}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                **{
                    f"{name}_sha256": hashlib.sha256(path.read_bytes()).hexdigest()
                    for name, path in paths.items()
                },
            }
        )
    )
    output = tmp_path / "checkpoint.json"
    with server(responses) as base:
        args = argparse.Namespace(
            checkpoint="initial",
            manifest=manifest,
            api_base=base,
            output=output,
            cp1=None,
            inputs=None,
            reference=None,
            **paths,
        )
        assert run(args) == 0
    data = json.loads(output.read_text())
    assert data["snapshot"]["branch_sha"] == "sha"
    assert data["plan"][0]["number"] == "1"
    assert all(
        entry["method"] == "GET" and entry["status"] == 200 for entry in data["ledger"]
    )
