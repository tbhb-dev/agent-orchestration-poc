"""Loopback REST collection tests for the backfill checkpoint shell."""

import argparse
import hashlib
import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast, override
from urllib.request import Request

import pytest

FIXTURES = Path(__file__).parent / "fixtures/work_model_backfill"


def checkpoint_paths(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    """Build a digest manifest for the synthetic table files."""
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
    return manifest, paths


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
def test_initial_checkpoint_uses_rest_gets_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A complete loopback CP1 yields the reviewed plan and a safe ledger."""
    # Mutmut copies only the core package before collecting tests.
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        run,
    )

    fixture = json.loads((FIXTURES / "runner/initial.json").read_text())
    responses = {path: (value, False) for path, value in fixture.items()}
    manifest, paths = checkpoint_paths(tmp_path)
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
    assert json.loads(capsys.readouterr().out) == data["plan"]
    assert data["snapshot"]["branch_sha"] == "sha"
    assert data["plan"][0]["number"] == "1"
    assert all(
        entry["method"] == "GET" and entry["status"] == 200 for entry in data["ledger"]
    )


@pytest.mark.integration
def test_initial_output_can_be_loaded_by_final_and_saves_differences(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The saved CP1 survives JSON and a mismatched CP13 retains its evidence."""
    from agent_orchestration_poc.core.work_model_backfill import Item  # noqa: PLC0415
    from agent_orchestration_poc.shell.work_model_backfill import run  # noqa: PLC0415

    fixture = json.loads((FIXTURES / "runner/initial.json").read_text())
    responses = {path: (value, False) for path, value in fixture.items()}
    manifest, paths = checkpoint_paths(tmp_path)
    cp1 = tmp_path / "cp1.json"
    output = tmp_path / "cp13.json"
    output.write_text("stale")
    inputs = tmp_path / "inputs.json"
    inputs.write_text(
        json.dumps(
            {
                "created": {
                    "title:Draft A": asdict(
                        Item(
                            "title:Draft A",
                            "Draft A",
                            "draft",
                            draft_id="draft-a",
                            item_id="item-a",
                        )
                    ),
                    "title:epic: migration": asdict(
                        Item(
                            "#3",
                            "epic: migration",
                            "open",
                            issue_id="3",
                            item_id="item-3",
                        )
                    ),
                },
                "bodies": {"title:Draft B": ""},
                "closed_at_cp0": ["2"],
                "revoked": [],
            }
        )
    )
    reference = Path(__file__).resolve().parents[1] / "config/workflow-reference.toml"
    with server(responses) as base:
        args = argparse.Namespace(
            checkpoint="initial",
            manifest=manifest,
            api_base=base,
            output=cp1,
            cp1=None,
            inputs=None,
            reference=None,
            **paths,
        )
        assert run(args) == 0
        capsys.readouterr()
        args.checkpoint = "final"
        args.output = output
        args.cp1 = cp1
        args.inputs = inputs
        args.reference = reference
        assert run(args) != 0
    data = json.loads(output.read_text())
    assert data["differences"]
    assert any(item["field"] == "title" for item in data["differences"])
    assert data["ledger"][-1]["status"] == 200
    assert data["snapshot"]["run_state"] == "final"


@pytest.mark.integration
def test_redirect_cannot_forward_authorization_to_another_origin() -> None:
    """A redirect to another port cannot receive the bearer token."""
    from agent_orchestration_poc.shell.work_model_backfill import Api  # noqa: PLC0415

    seen: list[str | None] = []

    class Target(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            seen.append(self.headers.get("Authorization"))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    class Source(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{target.server_port}/other")
            self.end_headers()

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    target = ThreadingHTTPServer(("127.0.0.1", 0), Target)
    source = ThreadingHTTPServer(("127.0.0.1", 0), Source)
    threads = [
        threading.Thread(target=httpd.serve_forever) for httpd in (target, source)
    ]
    for thread in threads:
        thread.start()
    try:
        with pytest.raises(ValueError, match="redirect"):
            Api(
                f"http://127.0.0.1:{source.server_port}", "probe-token-not-a-secret"
            ).get("start")
        assert not seen
    finally:
        for httpd in (source, target):
            httpd.shutdown()
            httpd.server_close()
        for thread in threads:
            thread.join(timeout=5)


@pytest.mark.integration
def test_https_to_http_redirect_is_refused() -> None:
    """The redirect policy refuses HTTPS downgrade before another request."""
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        _NoRedirect,
    )

    with pytest.raises(ValueError, match="redirect"):
        _NoRedirect().redirect_request(
            Request(
                "https://api.github.com/start",
                headers={"Authorization": "Bearer dummy"},
            ),
            None,
            302,
            "Found",
            {},
            "http://api.github.com/other",
        )


@pytest.mark.integration
def test_created_item_decoder_restores_all_tuple_fields() -> None:
    """Created identities use the same JSON decoder as saved CP1 items."""
    from agent_orchestration_poc.core.work_model_backfill import Item  # noqa: PLC0415
    from agent_orchestration_poc.shell.work_model_backfill import _item  # noqa: PLC0415

    original = Item(
        "#3",
        "created",
        "open",
        native=(("Priority", "Standard"),),
        project=(("Status", "Ready"),),
        source_project=(("Status", "Backlog"),),
        blockers=("#2",),
        labels=("area/project",),
        issue_id="3",
        item_id="30",
    )
    assert _item(json.loads(json.dumps(asdict(original)))) == original
