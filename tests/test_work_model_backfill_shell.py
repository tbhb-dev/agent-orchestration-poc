"""Loopback REST collection tests for the backfill checkpoint shell."""

import argparse
import csv
import hashlib
import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast, override
from urllib.request import Request

import pytest

FIXTURES = Path(__file__).parent / "fixtures/work_model_backfill"


def send_json(handler: BaseHTTPRequestHandler, status: int, value: object) -> None:
    """Respond with one JSON value from a loopback fake."""
    body = json.dumps(value).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def send_project_items(
    handler: BaseHTTPRequestHandler, items: list[dict[str, Any]]
) -> None:
    """Serve the REST field definition and Project item reads for loopback tests."""
    if handler.path.endswith("/fields?per_page=100"):
        send_json(handler, 200, [{"id": 1, "name": "Status"}])
    elif "/items?" in handler.path:
        send_json(handler, 200, items)
    else:
        handler.send_error(404)


class ProjectItemsHandler(BaseHTTPRequestHandler):
    """Serve Project items for write and read-back loopback cases."""

    project_items: list[dict[str, Any]]

    def do_GET(self) -> None:
        send_project_items(self, self.project_items)

    @override
    def log_message(self, format: str, *args: object) -> None:
        pass


@contextmanager
def live_server(handler: type[BaseHTTPRequestHandler]) -> Generator[str]:
    """Run a mutable REST fake on loopback for an executor test."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def new_journal(tmp_path: Path, actions: tuple[Any, ...]) -> tuple[Path, list[Any]]:
    """Start a loopback write test with a durable empty operation journal."""
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        _journal,
    )

    path = tmp_path / "journal.jsonl"
    return path, list(_journal(path, "digest", actions, create=True))


@pytest.mark.integration
def test_apply_refuses_next_stage_after_trial_add_without_cleanup_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recovery cannot advance after only the first verified trial write."""
    from agent_orchestration_poc.core.work_model_backfill import (  # noqa: PLC0415
        Item,
        Snapshot,
        Tables,
    )
    from agent_orchestration_poc.core.work_model_backfill_executor import (  # noqa: PLC0415
        Action,
        ProjectMetadata,
        Record,
    )
    from agent_orchestration_poc.shell import (  # noqa: PLC0415
        work_model_backfill as shell,
    )

    add = Action(
        "3:add:149:96",
        "3:trial",
        "trial_add",
        149,
        "POST",
        "issues/149/dependencies/blocked_by",
        {"issue_id": 96},
        (),
        ("#96",),
    )
    journal = tmp_path / "journal.jsonl"
    rows = [
        {"version": 1, "run_id": "digest"},
        asdict(Record("stage:0", "complete", {"stage": "0"})),
        asdict(Record(add.id, "intent", {"action": asdict(add)})),
        asdict(Record(add.id, "verified", {})),
    ]
    journal.write_text("".join(json.dumps(row) + "\n" for row in rows))
    current = Snapshot(
        1, (Item("#149", "trial", "open", blockers=("#96",)),), (), "sha"
    )

    def collect_snapshot(_api: object, _name: str) -> Snapshot:
        return current

    def accept_progress(*_args: object) -> None:
        pass

    def closed_pr(*_args: object) -> tuple[str, bool]:
        return "closed", False

    def no_candidate(*_args: object) -> tuple[Action, ...]:
        return ()

    monkeypatch.setattr(shell, "collect", collect_snapshot)
    monkeypatch.setattr(shell, "validate_progress", accept_progress)
    monkeypatch.setattr(shell, "_observe", closed_pr)
    monkeypatch.setattr(shell, "candidate_actions", no_candidate)
    prepared = shell.ApplyInputs(
        Tables(1, (), (), ()),
        current,
        (),
        "digest",
        None,
        {"pr97_comment": "reviewed"},
        None,
        (),
    )
    with pytest.raises(ValueError, match="stage 3:trial"):
        shell._apply_locked(
            argparse.Namespace(stage="4:labels", journal=journal),
            cast("Any", object()),
            prepared,
            ProjectMetadata({}, [], []),
            [],
        )
    assert journal.read_text().splitlines() == [json.dumps(row) for row in rows]


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
    from agent_orchestration_poc.shell.work_model_backfill import run  # noqa: PLC0415

    fixture = json.loads((FIXTURES / "runner/initial.json").read_text())
    responses = {path: (value, False) for path, value in fixture.items()}
    manifest, paths = checkpoint_paths(tmp_path)
    cp1 = tmp_path / "cp1.json"
    output = tmp_path / "cp13.json"
    output.write_text("stale")
    inputs = tmp_path / "inputs.json"
    inputs.write_bytes((FIXTURES / "runner/final-inputs.json").read_bytes())
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
def test_reviewed_copied_status_reaches_initial_and_final_cp1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reviewed copied Status differs from the unchanged source value."""
    from agent_orchestration_poc.shell.work_model_backfill import run  # noqa: PLC0415

    fixture = json.loads((FIXTURES / "runner/initial.json").read_text())
    old = {
        "Status": "Backlog",
        "Size": "",
        "Area": "",
        "Harness": "",
        "Worker": "",
        "Phase": "",
        "Priority": "",
    }
    old_item = {
        "content_type": "Issue",
        "content": {"number": 1},
        "id": 9,
        "fields": [{"name": key, "value": value} for key, value in old.items()],
    }
    fixture["/users/tbhb/projectsV2/9/items"] = [old_item]
    project = fixture["/orgs/tbhb-dev/projectsV2/1/items"][0]
    project["fields"] = [
        {"name": key, "value": "Refinement" if key == "Status" else value}
        for key, value in old.items()
        if key in {"Status", "Size", "Area", "Harness", "Worker"}
    ]
    manifest, paths = checkpoint_paths(tmp_path)
    with paths["assignments"].open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        rows = list(reader)
        fields = reader.fieldnames
    assert fields is not None
    rows[0]["old project fields"] = json.dumps(old)
    assignment = tmp_path / "assignments.tsv"
    with assignment.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    paths["assignments"] = assignment
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
    cp1 = tmp_path / "cp1.json"
    inputs = tmp_path / "inputs.json"
    inputs_data = json.loads((FIXTURES / "runner/final-inputs.json").read_text())
    inputs_data["reviewed_status"] = {"#1": "Refinement"}
    inputs.write_text(json.dumps(inputs_data))
    with server({path: (value, False) for path, value in fixture.items()}) as base:
        args = argparse.Namespace(
            checkpoint="initial",
            manifest=manifest,
            api_base=base,
            output=cp1,
            cp1=None,
            inputs=None,
            reference=None,
            reviewed_status=None,
            **paths,
        )
        with pytest.raises(ValueError, match="copied Project"):
            run(args)
        args.reviewed_status = '{"#1": "Refinement"}'
        assert run(args) == 0
        capsys.readouterr()
        assert json.loads(cp1.read_text())["reviewed_status"] == {"#1": "Refinement"}
        args.checkpoint = "final"
        args.cp1 = cp1
        args.inputs = inputs
        args.reference = (
            Path(__file__).resolve().parents[1] / "config/workflow-reference.toml"
        )
        assert run(args) == 2


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


def test_cp13_differences_keep_both_values_for_the_failure_envelope() -> None:
    """The saved failure envelope needs precise before and after values."""
    from agent_orchestration_poc.core.work_model_backfill import (  # noqa: PLC0415
        Difference,
        Item,
        Page,
        Snapshot,
        compare_cp13,
    )

    expected = Item(
        "title:Draft",
        "Reviewed",
        "draft",
        project=(("Status", "Backlog"),),
        body="Reviewed body",
        item_id="item-1",
        draft_id="draft-1",
    )
    actual = replace(
        expected,
        title="Drifted",
        project=(("Status", "Ready"),),
        body="Drifted body",
    )
    pages = tuple(
        Page(name, 1, count, 1, count)
        for name, count in (
            ("issues", 0),
            ("project", 1),
            ("drafts", 1),
            ("native", 0),
            ("parents", 0),
            ("blockers", 0),
        )
    )
    snapshot = Snapshot(1, (actual,), pages, "new-sha", "final")
    assert compare_cp13((expected,), snapshot, "old-sha") == (
        Difference("branch", "sha", "old-sha", "new-sha"),
        Difference("title:Draft", "title", "Reviewed", "Drifted"),
        Difference(
            "title:Draft",
            "project",
            (("Status", "Backlog"),),
            (("Status", "Ready"),),
        ),
        Difference("title:Draft", "body", "Reviewed body", "Drifted body"),
    )
    missing_pages = tuple(Page(page.collection, 1, 0, 1, 0) for page in pages)
    missing = Snapshot(1, (), missing_pages, "new-sha", "final")
    assert compare_cp13((expected,), missing, "new-sha") == (
        Difference("title:Draft", "presence", True, False),
    )
    assert compare_cp13((), snapshot, "new-sha") == (
        Difference("title:Draft", "presence", False, True),
    )


@pytest.mark.integration
def test_journaled_write_resumes_without_duplicate_comment(
    tmp_path: Path,
) -> None:
    """A lost comment response is recovered by read-back without replay."""
    from agent_orchestration_poc.core.work_model_backfill_executor import (  # noqa: PLC0415
        Action,
    )
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
        _execute,
        _journal,
    )

    comments: list[dict[str, Any]] = []
    state = {"state": "open", "state_reason": "not_planned"}
    writes: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.endswith("/comments?per_page=100"):
                send_json(self, 200, comments)
            elif self.path.endswith("/issues/2"):
                send_json(self, 200, state)
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            writes.append(self.path)
            if self.path.endswith("/comments"):
                comments.append({"id": 10, "body": payload["body"]})
                send_json(self, 503, {})

        def do_PATCH(self) -> None:
            writes.append(self.path)
            state.update(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            send_json(self, 200, state)

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    assert all(
        map(
            callable,
            (Handler.do_GET, Handler.do_POST, Handler.do_PATCH),
        )
    )
    comment = Action(
        "0:comment:2",
        "0",
        "comment",
        2,
        "POST",
        "issues/2/comments",
        {"body": "Folded into 1.\n\n<!-- marker -->"},
        0,
        1,
    )
    close = Action(
        "0:close:2",
        "0",
        "issue_state",
        2,
        "PATCH",
        "issues/2",
        {"state": "closed", "state_reason": "not_planned"},
        ("open", "not_planned"),
        ("closed", "not_planned"),
    )
    actions = (comment, close)
    journal, records = new_journal(tmp_path, actions)
    with live_server(Handler) as base:
        api = Api(base, "")
        with pytest.raises(ValueError, match="HTTP 503"):
            _execute(api, journal, comment, records)
        records = list(_journal(journal, "digest", actions, create=False))
        _execute(api, journal, comment, records)
        _execute(api, journal, close, records)
        _execute(api, journal, comment, records)
    assert len(comments) == 1
    assert len(writes) == 2
    assert [record.phase for record in records if record.action_id == comment.id] == [
        "intent",
        "verified",
    ]
    reloaded = _journal(journal, "digest", actions, create=False)
    assert (
        next(
            record.detail["comment_id"]
            for record in reloaded
            if record.action_id == comment.id and record.phase == "verified"
        )
        == 10
    )
    assert {record.action_id for record in records if record.phase == "verified"} == {
        action.id for action in actions
    }


@pytest.mark.integration
def test_rollback_comment_delete_recovers_lost_response(tmp_path: Path) -> None:
    """A completed deletion is read back without sending a second DELETE."""
    from agent_orchestration_poc.core.work_model_backfill_executor import (  # noqa: PLC0415
        Action,
        ProjectMetadata,
    )
    from agent_orchestration_poc.core.work_model_backfill_rollback import (  # noqa: PLC0415
        inverse_action,
        validate_rollback_journal,
    )
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
        _execute,
    )

    comments = [{"id": 10, "body": "saved"}]
    deletes: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            send_json(self, 200, comments)

        def do_DELETE(self) -> None:
            deletes.append(self.path)
            comments.clear()
            send_json(self, 503, {})

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    assert callable(Handler.do_DELETE)
    forward = Action(
        "0:comment:2",
        "0",
        "comment",
        2,
        "POST",
        "issues/2/comments",
        {"body": "saved"},
        0,
        1,
    )
    inverse = inverse_action(forward, {"comment_id": 10}, ProjectMetadata({}, [], []))
    path = tmp_path / "rollback.jsonl"
    path.write_text(json.dumps({"version": 1, "run_id": "cp1"}) + "\n")
    records: list[Any] = []
    with live_server(Handler) as base:
        api = Api(base, "")
        with pytest.raises(ValueError, match="HTTP 503"):
            _execute(api, path, inverse, records)
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        records = list(validate_rollback_journal(rows, "cp1", (inverse,)))
        _execute(api, path, inverse, records)
    assert deletes == ["/repos/tbhb-dev/agent-orchestration-poc/issues/comments/10"]
    assert [row.phase for row in records] == ["intent", "verified"]


@pytest.mark.integration
def test_rollback_parent_removal_sends_required_body(tmp_path: Path) -> None:
    """The inverse parent write uses GitHub's singular endpoint and body."""
    from agent_orchestration_poc.core.work_model_backfill_executor import (  # noqa: PLC0415
        Action,
        ProjectMetadata,
    )
    from agent_orchestration_poc.core.work_model_backfill_rollback import (  # noqa: PLC0415
        inverse_action,
    )
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
        _execute,
    )

    children = [{"number": 2}]
    writes: list[tuple[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            send_json(self, 200, children)

        def do_DELETE(self) -> None:
            writes.append(
                (
                    self.path,
                    json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
                )
            )
            children.clear()
            send_json(self, 200, {})

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    assert callable(Handler.do_DELETE)
    forward = Action(
        "10:parent:2",
        "10",
        "parent",
        1,
        "POST",
        "issues/1/sub_issues",
        {"sub_issue_id": 22, "child": "#2"},
        "",
        "#1",
    )
    inverse = inverse_action(forward, {}, ProjectMetadata({}, [], []))
    path = tmp_path / "rollback.jsonl"
    path.write_text(json.dumps({"version": 1, "run_id": "cp1"}) + "\n")
    with live_server(Handler) as base:
        _execute(Api(base, ""), path, inverse, [])
    assert writes == [
        (
            "/repos/tbhb-dev/agent-orchestration-poc/issues/1/sub_issue",
            {"sub_issue_id": 22},
        )
    ]


@pytest.mark.integration
@pytest.mark.parametrize("status", [201, 503])
def test_draft_creation_recovers_after_response(tmp_path: Path, status: int) -> None:
    """Read-back resumes a successful receipt or a lost response without replay."""
    from agent_orchestration_poc.core.work_model_backfill_executor import (  # noqa: PLC0415
        Action,
    )
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
        _execute,
        _journal,
    )

    drafts: list[dict[str, Any]] = []
    writes: list[dict[str, Any]] = []

    class Handler(ProjectItemsHandler):
        project_items = drafts

        def do_POST(self) -> None:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            writes.append(payload)
            drafts.append(
                {
                    "content_type": "DraftIssue",
                    "id": 13,
                    "content": {"id": "draft-a", **payload},
                    "fields": [],
                }
            )
            send_json(self, status, drafts[-1] if status == 201 else {})

    action = Action(
        "6:draft:title:Draft A",
        "6",
        "draft",
        0,
        "POST",
        "orgs/tbhb-dev/projectsV2/1/drafts",
        {"title": "Draft A", "body": "- Class: chore"},
        (0, ""),
        (1, "- Class: chore"),
    )
    journal, records = new_journal(tmp_path, (action,))
    with live_server(Handler) as base:
        api = Api(base, "")
        if status == 503:
            with pytest.raises(ValueError, match="HTTP 503"):
                _execute(api, journal, action, records)
        else:
            _execute(api, journal, action, records)
            assert (
                next(
                    record.detail["draft_id"]
                    for record in records
                    if record.phase == "response"
                )
                == "draft-a"
            )
            journal.write_text("\n".join(journal.read_text().splitlines()[:-1]) + "\n")
        records = list(_journal(journal, "digest", (action,), create=False))
        _execute(api, journal, action, records)
        _execute(api, journal, action, records)
    assert len(writes) == 1
    assert (
        next(
            record.detail["draft_id"]
            for record in records
            if record.phase == "verified"
        )
        == "draft-a"
    )


@pytest.mark.integration
def test_project_membership_recovers_lost_response(tmp_path: Path) -> None:
    """A recorded intent and matching REST item prevent a second add."""
    from agent_orchestration_poc.core.work_model_backfill_executor import (  # noqa: PLC0415
        Action,
    )
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
        _execute,
        _journal,
    )

    items: list[dict[str, Any]] = []
    writes: list[dict[str, Any]] = []

    class Handler(ProjectItemsHandler):
        project_items = items

        def do_POST(self) -> None:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            writes.append(payload)
            items.append(
                {
                    "content_type": "Issue",
                    "content": {"number": 1, "id": payload["id"]},
                    "id": 13,
                    "fields": [],
                }
            )
            send_json(self, 503, {})

    action = Action(
        "6:item:1",
        "6",
        "project_item",
        1,
        "POST",
        "orgs/tbhb-dev/projectsV2/1/items",
        {"type": "Issue", "id": 101},
        (0, "101"),
        (1, "101"),
    )
    journal, records = new_journal(tmp_path, (action,))
    with live_server(Handler) as base:
        api = Api(base, "")
        with pytest.raises(ValueError, match="HTTP 503"):
            _execute(api, journal, action, records)
        records = list(_journal(journal, "digest", (action,), create=False))
        _execute(api, journal, action, records)
        _execute(api, journal, action, records)
    assert writes == [{"type": "Issue", "id": 101}]
    assert [row.phase for row in records] == ["intent", "verified"]
    assert records[-1].detail["item_id"] == "13"


@pytest.mark.integration
def test_project_field_graphql_batch_reads_back_rest(tmp_path: Path) -> None:
    """One GraphQL write records a REST verified field value."""
    from agent_orchestration_poc.core.work_model_backfill_executor import (  # noqa: PLC0415
        Action,
    )
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
        _execute,
    )

    items: list[dict[str, Any]] = [
        {
            "id": 13,
            "node_id": "node-13",
            "content_type": "Issue",
            "content": {"id": 101, "number": 1},
            "fields": [],
        }
    ]
    queries: list[str] = []

    class Handler(ProjectItemsHandler):
        project_items = items

        def do_POST(self) -> None:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert self.path == "/graphql"
            assert set(payload) == {"query"}
            queries.append(payload["query"])
            items[0]["fields"] = [{"name": "Status", "value": {"name": "Ready"}}]
            send_json(self, 200, {"data": {"f0": {"projectV2Item": {"id": "node-13"}}}})

    data = json.loads((FIXTURES / "runner/project-field-action.json").read_text())
    action = Action(
        data["id"],
        data["step"],
        data["kind"],
        data["number"],
        data["method"],
        data["path"],
        data["payload"],
        tuple(map(tuple, data["before"])),
        tuple(map(tuple, data["after"])),
    )
    journal, records = new_journal(tmp_path, (action,))
    with live_server(Handler) as base:
        api = Api(base, "")
        _execute(api, journal, action, records)
        _execute(api, journal, action, records)
    assert len(queries) == 1
    assert records[-1].phase == "verified"
    assert records[-1].detail["observed"] == (("Status", "Ready"),)


@pytest.mark.integration
def test_b4_issue_creation_recovers_lost_response(tmp_path: Path) -> None:
    """An uncertain POST is recovered by exact issue read-back without replay."""
    from agent_orchestration_poc.core.work_model_backfill_executor import (  # noqa: PLC0415
        Action,
    )
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
        _execute,
    )

    issues: list[dict[str, Any]] = []
    posts: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            assert (
                self.path
                == "/repos/tbhb-dev/agent-orchestration-poc/issues?state=all&per_page=100"
            )
            send_json(self, 200, issues)

        def do_POST(self) -> None:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert self.path == "/repos/tbhb-dev/agent-orchestration-poc/issues"
            posts.append(payload)
            issues.append(
                {
                    "id": 103,
                    "number": 3,
                    "title": payload["title"],
                    "body": payload["body"],
                    "state": "open",
                    "type": {"name": payload["type"]},
                    "labels": [],
                }
            )
            send_json(self, 503, {})

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    action = Action(
        "9:create:000:epic: migration",
        "9:create",
        "issue_create",
        0,
        "POST",
        "issues",
        {"title": "epic: migration", "body": "reviewed", "type": "Epic"},
        0,
        1,
    )
    journal, records = new_journal(tmp_path, (action,))
    with live_server(Handler) as base:
        api = Api(base, "")
        with pytest.raises(ValueError, match="503"):
            _execute(api, journal, action, records)
        assert [record.phase for record in records] == ["intent"]
        _execute(api, journal, action, records)
    assert len(posts) == 1
    assert records[-1].phase == "verified"
    assert records[-1].detail["created_item"]["issue_id"] == "103"


@pytest.mark.integration
def test_b4_native_parent_and_dependency_writes(tmp_path: Path) -> None:  # noqa: C901 - one loopback fake covers three REST writes.
    """Native values and links use REST, then read back each targeted value."""
    from agent_orchestration_poc.core.work_model_backfill_executor import (  # noqa: PLC0415
        Action,
    )
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
        _execute,
    )

    values: list[dict[str, Any]] = []
    children: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    writes: list[tuple[str, dict[str, Any]]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.startswith("/orgs/tbhb-dev/issue-fields"):
                send_json(
                    self,
                    200,
                    [
                        {
                            "id": field_id,
                            "name": name,
                            "data_type": "single_select",
                            "options": [{"name": option}],
                        }
                        for field_id, name, option in (
                            (11, "Priority", "Standard"),
                            (12, "Work type", "Planned"),
                        )
                    ],
                )
            elif "/issue-field-values?" in self.path:
                send_json(self, 200, values)
            elif "/sub_issues?" in self.path:
                send_json(self, 200, children)
            elif "/blocked_by?" in self.path:
                send_json(self, 200, blockers)
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            writes.append((self.path, payload))
            if self.path.endswith("/issue-field-values"):
                values.extend(
                    {
                        "issue_field_name": "Priority"
                        if entry["field_id"] == 11
                        else "Work type",
                        "single_select_option": {"name": entry["value"]},
                    }
                    for entry in payload["issue_field_values"]
                )
            elif self.path.endswith("/sub_issues"):
                children.append({"number": 1})
            elif self.path.endswith("/blocked_by"):
                blockers.append({"number": 2})
            else:
                self.send_error(404)
                return
            send_json(self, 201, {})

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    empty_native = (("Priority", ""), ("Severity", ""), ("Work type", ""))
    actions = (
        Action(
            "6:native:1",
            "6:native",
            "native",
            1,
            "POST",
            "issues/1/issue-field-values",
            {"fields": {"Priority": "Standard", "Work type": "Planned"}},
            empty_native,
            (("Priority", "Standard"), ("Severity", ""), ("Work type", "Planned")),
        ),
        Action(
            "10:parent:1",
            "10",
            "parent",
            3,
            "POST",
            "issues/3/sub_issues",
            {"sub_issue_id": 101, "child": "#1"},
            "",
            "#3",
        ),
        Action(
            "11:edge:1",
            "11:links",
            "blocker",
            1,
            "POST",
            "issues/1/dependencies/blocked_by",
            {"issue_id": 102},
            (),
            ("#2",),
        ),
    )
    journal, records = new_journal(tmp_path, actions)
    with live_server(Handler) as base:
        api = Api(base, "")
        for action in actions:
            _execute(api, journal, action, records)
    assert len(writes) == 3
    assert writes[0][1] == {
        "issue_field_values": [
            {"field_id": 11, "value": "Standard"},
            {"field_id": 12, "value": "Planned"},
        ]
    }
    assert [row.phase for row in records].count("verified") == 3


@pytest.mark.integration
def test_b4_existing_draft_body_graphql_readback(tmp_path: Path) -> None:
    """The copied draft body uses its content node and REST read-back."""
    from agent_orchestration_poc.core.work_model_backfill_executor import (  # noqa: PLC0415
        Action,
    )
    from agent_orchestration_poc.shell.work_model_backfill import (  # noqa: PLC0415
        Api,
        _execute,
    )

    item: dict[str, Any] = {
        "id": "item-b",
        "node_id": "node-item-b",
        "content_type": "DraftIssue",
        "content": {
            "id": 13,
            "node_id": "node-draft",
            "title": "Draft B",
            "body": "old",
        },
        "fields": [],
    }
    queries: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.endswith("/fields?per_page=100"):
                send_json(self, 200, [{"id": 1, "name": "Status"}])
            elif "/items?" in self.path:
                send_json(self, 200, [item])
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            assert self.path == "/graphql"
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            queries.append(payload["query"])
            item["content"]["body"] = "reviewed"
            send_json(
                self,
                200,
                {
                    "data": {
                        "updateProjectV2DraftIssue": {
                            "draftIssue": {"id": "node-draft", "body": "reviewed"},
                        }
                    }
                },
            )

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    action = Action(
        "6:body:title:Draft B",
        "6:body",
        "draft_body",
        0,
        "POST",
        "graphql",
        {
            "query": 'mutation{updateProjectV2DraftIssue(input:{draftIssueId:"node-draft",body:"reviewed"}){draftIssue{id body}}}',
            "key": "title:Draft B",
            "draft_id": "node-draft",
        },
        "old",
        "reviewed",
    )
    journal, records = new_journal(tmp_path, (action,))
    with live_server(Handler) as base:
        api = Api(base, "")
        _execute(api, journal, action, records)
    assert len(queries) == 1
    assert records[-1].detail["observed"] == "reviewed"
