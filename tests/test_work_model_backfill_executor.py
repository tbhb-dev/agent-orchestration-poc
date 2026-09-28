"""Pure journal and resume decisions for the staged backfill."""

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.work_model_backfill import (
    Item,
    Page,
    Snapshot,
    Tables,
    operation_plan,
    parse_tables,
    validate_cp1,
)
from agent_orchestration_poc.core.work_model_backfill_executor import (
    Action,
    ProjectMetadata,
    Record,
    _project_field_query,
    closure_actions,
    comment_observation,
    draft_actions,
    draft_observation,
    graphql_field_receipt,
    journal_state,
    membership_actions,
    membership_observation,
    observation_value,
    project_field_actions,
    project_fields_observation,
    stage_actions,
    validate_journal,
    validate_progress,
    verified_detail,
    write_wait_seconds,
)

FIXTURES = Path(__file__).parent / "fixtures/work_model_backfill"


def fixture_snapshot(name: str) -> Snapshot:
    """Restore a complete JSON checkpoint for pure resume tests."""
    saved = json.loads((FIXTURES / f"runner/{name}.json").read_text())
    items = []
    for value in saved["items"]:
        for field in ("native", "project", "source_project"):
            value[field] = tuple(tuple(pair) for pair in value[field])
        for field in ("blockers", "labels"):
            value[field] = tuple(value[field])
        items.append(Item(**value))
    return Snapshot(
        saved["version"],
        tuple(items),
        tuple(Page(**page) for page in saved["pages"]),
        saved["branch_sha"],
        saved["run_state"],
    )


def contract() -> tuple[tuple[Action, ...], Snapshot]:
    """Use the same complete CP1 and approved synthetic tables as slice A."""
    rows = FIXTURES / "plan"
    texts = [
        (rows / f"{name}.tsv").read_text()
        for name in ("assignments", "parents", "edges")
    ]
    tables = parse_tables(*texts)
    cp1 = fixture_snapshot("executor-cp1")
    validate_cp1(tables, cp1)
    plan = operation_plan(tables, cp1)
    return closure_actions(tables, cp1, plan, "digest"), cp1


def draft_action(cp1: Snapshot) -> Action:
    """Build the planned synthetic draft action."""
    rows = FIXTURES / "plan"
    tables = parse_tables(
        *(
            (rows / f"{name}.tsv").read_text()
            for name in ("assignments", "parents", "edges")
        )
    )
    return draft_actions(tables, cp1, operation_plan(tables, cp1))[0]


def with_added_draft(cp1: Snapshot, item: Item, *, prepend: bool = False) -> Snapshot:
    """Represent one complete additional Project draft page entry."""
    pages = tuple(
        replace(page, count=page.count + 1, total_count=page.total_count + 1)
        if page.collection in {"project", "drafts"}
        else page
        for page in cp1.pages
    )
    items = (item, *cp1.items) if prepend else (*cp1.items, item)
    return replace(cp1, items=items, pages=pages)


def without_membership(cp1: Snapshot) -> Snapshot:
    """Copy the fixture with issue one absent from the new Project."""
    return replace(
        cp1,
        items=tuple(
            replace(item, item_id="") if item.key == "#1" else item
            for item in cp1.items
        ),
        pages=tuple(
            replace(page, count=page.count - 1, total_count=page.total_count - 1)
            if page.collection == "project"
            else page
            for page in cp1.pages
        ),
    )


def field_contract() -> tuple[Tables, Snapshot, ProjectMetadata]:
    """Load the synthetic tables and REST Project field metadata."""
    rows = FIXTURES / "plan"
    tables = parse_tables(
        *(
            (rows / f"{name}.tsv").read_text()
            for name in ("assignments", "parents", "edges")
        )
    )
    cp1 = fixture_snapshot("executor-cp1")
    data = json.loads((FIXTURES / "runner/project-fields.json").read_text())
    return tables, cp1, ProjectMetadata(data["project"], data["fields"], data["items"])


def test_membership_plan_readback_and_resume() -> None:
    rows = FIXTURES / "plan"
    tables = parse_tables(
        *(
            (rows / f"{name}.tsv").read_text()
            for name in ("assignments", "parents", "edges")
        )
    )
    cp1 = without_membership(fixture_snapshot("executor-cp1"))
    validate_cp1(tables, cp1)
    actions = membership_actions(cp1, operation_plan(tables, cp1))
    assert actions == (
        Action(
            "6:item:1",
            "6",
            "project_item",
            1,
            "POST",
            "orgs/tbhb-dev/projectsV2/1/items",
            {"type": "Issue", "id": 1},
            (0, "1"),
            (1, "1"),
        ),
    )
    action = actions[0]
    assert membership_observation([], 1, "1") == (0, "1", None, ())
    raw: dict[str, Any] = {
        "content_type": "Issue",
        "content": {"number": 1, "id": 1},
        "id": 13,
        "fields": [],
    }
    observed = membership_observation([raw], 1, "1")
    assert observed == (1, "1", "13", ())
    assert membership_observation([raw, raw], 1, "1") == (2, "1", None, ())
    assert membership_observation(
        [{**raw, "content": {"number": 1, "id": 9}}], 1, "1"
    ) == (
        1,
        "9",
        None,
        (),
    )
    assert observation_value(action, observed) == action.after
    assert (
        journal_state(action, (Record(action.id, "intent", {}),), observed) == "verify"
    )
    assert journal_state(action, (), observed) == "halt"
    assert (
        journal_state(
            action,
            (
                Record(action.id, "intent", {}),
                Record(action.id, "response", {"id": 99}),
            ),
            observed,
        )
        == "halt"
    )
    receipt = Record(action.id, "verified", verified_detail(action, observed, {}))
    assert receipt.detail["item_id"] == "13"
    current = replace(
        cp1,
        items=tuple(
            replace(item, item_id="13") if item.key == "#1" else item
            for item in cp1.items
        ),
        pages=tuple(
            replace(page, count=page.count + 1, total_count=page.total_count + 1)
            if page.collection == "project"
            else page
            for page in cp1.pages
        ),
    )
    records = (Record(action.id, "intent", {}), receipt)
    validate_progress(cp1, current, actions, records)
    validate_progress(cp1, cp1, actions, records[:1])
    with pytest.raises(ValueError, match="journal"):
        validate_progress(cp1, cp1, actions, records)
    changed_fields = replace(
        current,
        items=tuple(
            replace(item, project=(("Status", "Ready"),)) if item.key == "#1" else item
            for item in current.items
        ),
    )
    with pytest.raises(ValueError, match="fields"):
        validate_progress(cp1, changed_fields, actions, records)
    with pytest.raises(ValueError, match="journal"):
        validate_progress(
            cp1,
            replace(
                current,
                items=tuple(
                    replace(item, item_id="other") if item.key == "#1" else item
                    for item in current.items
                ),
            ),
            actions,
            records,
        )
    with pytest.raises(ValueError, match="drifted"):
        validate_progress(cp1, current, actions, ())


def test_project_field_batch_uses_option_ids_and_readback() -> None:
    tables, cp1, metadata = field_contract()
    raw = metadata.items
    actions = project_field_actions(tables, cp1, metadata)
    assert {action.id for action in actions} == {
        "6:fields:#1",
        "6:fields:#2",
        "6:fields:title:Draft B",
    }
    first = next(action for action in actions if action.id == "6:fields:#1")
    assert first.after == (
        ("Area", "tooling"),
        ("Harness", "codex"),
        ("Size", "M"),
        ("Status", "Ready"),
        ("Worker", "worker"),
    )
    assert first.payload is not None
    query = first.payload["query"]
    assert 'projectId:"project-id",itemId:"node-item-1",fieldId:"field-Status"' in query
    assert 'value:{singleSelectOptionId:"option-Ready"}' in query
    assert 'value:{text:"worker"}' in query
    good = {
        f"f{index}": {"projectV2Item": {"id": first.payload["node_id"]}}
        for index in range(5)
    }
    graphql_field_receipt(first, {"data": good})
    with pytest.raises(ValueError, match="GraphQL"):
        graphql_field_receipt(first, None)
    for bad in (
        {"errors": [{"message": "rejected"}]},
        {"data": {"f0": good["f0"]}},
        {"data": {**good, "f0": {"projectV2Item": {"id": "other"}}}},
    ):
        with pytest.raises(ValueError, match="GraphQL"):
            graphql_field_receipt(first, bad)
    filled = {
        **raw[0],
        "fields": [
            {"name": name, "value": value if name == "Worker" else {"name": value}}
            for name, value in cast("tuple[tuple[str, str], ...]", first.after)
        ],
    }
    assert project_fields_observation([filled], first) == first.after
    with pytest.raises(ValueError, match="identity"):
        project_fields_observation([], first)
    with pytest.raises(ValueError, match="content"):
        project_fields_observation([{**filled, "node_id": "replacement"}], first)
    assert (
        journal_state(first, (Record(first.id, "intent", {}),), first.after) == "verify"
    )
    changed = replace(
        cp1,
        items=tuple(
            replace(item, project=cast("tuple[tuple[str, str], ...]", first.after))
            if item.key == "#1"
            else item
            for item in cp1.items
        ),
    )
    receipt = (Record(first.id, "intent", {}), Record(first.id, "verified", {}))
    validate_progress(cp1, changed, (first,), receipt)
    with pytest.raises(ValueError, match="drifted"):
        validate_progress(cp1, cp1, (first,), receipt)


@pytest.mark.parametrize("phase", ["intent", "verified"])
def test_existing_draft_field_write_progress(phase: str) -> None:
    tables, cp1, metadata = field_contract()
    action = next(
        action
        for action in project_field_actions(tables, cp1, metadata)
        if action.id == "6:fields:title:Draft B"
    )
    current = replace(
        cp1,
        items=tuple(
            replace(item, project=cast("tuple[tuple[str, str], ...]", action.after))
            if item.key == "title:Draft B"
            else item
            for item in cp1.items
        ),
    )
    records = (Record(action.id, "intent", {}),)
    if phase == "verified":
        records += (Record(action.id, "verified", {}),)
    validate_progress(cp1, current, (action,), records)
    if phase == "verified":
        with pytest.raises(ValueError, match="drifted"):
            validate_progress(cp1, cp1, (action,), records)
    else:
        validate_progress(cp1, cp1, (action,), records)
    with pytest.raises(ValueError, match="drifted"):
        validate_progress(cp1, current, (action,), ())


def test_project_field_metadata_and_draft_identity() -> None:
    tables, cp1, metadata = field_contract()
    definitions = metadata.fields
    raw = metadata.items
    actions = project_field_actions(tables, cp1, metadata)
    first = actions[0]
    with pytest.raises(ValueError, match="definition"):
        project_field_actions(tables, cp1, replace(metadata, fields=definitions[:1]))
    with pytest.raises(ValueError, match="node identity"):
        project_field_actions(tables, cp1, replace(metadata, project={}))
    blank_worker = replace(
        tables,
        assignments=tuple(
            {**row, "project worker": ""} if row["number"] == "1" else row
            for row in tables.assignments
        ),
    )
    blank_first = project_field_actions(blank_worker, cp1, metadata)[0]
    assert blank_first.payload is not None
    assert blank_first.payload["mutation_count"] == 4
    revised = replace(
        cp1,
        items=tuple(
            replace(item, project=cast("tuple[tuple[str, str], ...]", first.after))
            if item.key == "#1"
            else item
            for item in cp1.items
        ),
    )
    revised_ids = {
        action.id for action in project_field_actions(tables, revised, metadata)
    }
    assert "6:fields:#1" not in revised_ids
    assert "6:fields:#2" in revised_ids
    definitions[0]["options"].append(
        {"id": "option-Refinement", "name": {"raw": "Refinement"}}
    )
    overridden = project_field_actions(tables, cp1, metadata, {"#1": "Refinement"})
    after = next(action for action in overridden if action.id == first.id).after
    assert cast("tuple[tuple[str, str], ...]", after)[3] == (
        "Status",
        "Refinement",
    )
    assert "clearProjectV2ItemFieldValue" in _project_field_query(
        "project-id",
        "node-item-1",
        {"Worker": ""},
        {"Worker": definitions[-1]},
    )
    with pytest.raises(ValueError, match="content"):
        project_fields_observation([{**raw[0], "content": {"number": 9}}], first)
    draft = next(action for action in actions if action.id == "6:fields:title:Draft B")
    assert project_fields_observation([raw[2]], draft) == draft.before


def test_closure_actions_follow_plan() -> None:
    actions, _ = contract()
    expected = json.loads((FIXTURES / "runner/executor-actions.json").read_text())
    assert (
        json.loads(json.dumps([asdict(action) for action in actions]))
        == expected["closure"]
    )


def test_draft_actions_follow_plan_and_recover_identity() -> None:
    rows = FIXTURES / "plan"
    tables = parse_tables(
        *(
            (rows / f"{name}.tsv").read_text()
            for name in ("assignments", "parents", "edges")
        )
    )
    cp1 = fixture_snapshot("executor-cp1")
    actions = draft_actions(tables, cp1, operation_plan(tables, cp1))
    body = "- Class: chore\n- Priority: Standard\n- Work type: Unplanned\n- Severity: none\n- Size: "
    assert actions == (
        Action(
            "6:draft:title:Draft A",
            "6",
            "draft",
            0,
            "POST",
            "orgs/tbhb-dev/projectsV2/1/drafts",
            {"title": "Draft A", "body": body},
            (0, ""),
            (1, body),
        ),
    )
    action = actions[0]
    assert action.payload is not None
    assert draft_observation([], "Draft A") == (0, "", None, None)
    item = {
        "content_type": "DraftIssue",
        "id": 13,
        "content": {
            "id": "draft-a",
            "title": "Draft A",
            "body": action.payload["body"],
        },
    }
    observed = draft_observation([item], "Draft A")
    assert observed == (1, body, "13", "draft-a")
    assert observation_value(action, observed) == action.after
    assert verified_detail(action, observed, {"status": 200}) == {
        "observed": (1, body),
        "read": {"status": 200},
        "item_id": "13",
        "draft_id": "draft-a",
    }
    assert draft_observation([item, item], "Draft A") == (2, "", None, None)
    assert (
        journal_state(action, (Record(action.id, "intent", {}),), observed) == "verify"
    )
    assert journal_state(action, (), observed) == "halt"


def test_draft_progress_requires_recorded_creation() -> None:
    cp1 = fixture_snapshot("executor-cp1")
    action = draft_action(cp1)
    assert action.payload is not None
    created = Item(
        "title:Draft A",
        "Draft A",
        "draft",
        body=action.payload["body"],
        item_id="13",
        draft_id="draft-a",
    )
    current = with_added_draft(cp1, created)
    record = (Record(action.id, "intent", {}),)
    validate_progress(cp1, current, (action,), record)
    for changed in (
        replace(created, title="Other"),
        replace(created, body="changed"),
        replace(created, state="open"),
        replace(created, item_id=""),
        replace(created, draft_id=""),
        replace(created, issue_id="unexpected"),
    ):
        with pytest.raises(ValueError, match="differs|changed"):
            validate_progress(
                cp1, replace(current, items=(*cp1.items, changed)), (action,), record
            )
    with pytest.raises(ValueError, match="unrecorded"):
        validate_progress(cp1, current, (action,), ())
    with pytest.raises(ValueError, match="disappeared"):
        validate_progress(
            cp1, cp1, (action,), (*record, Record(action.id, "verified", {}))
        )


def test_draft_resume_rejects_replacement_after_identity_is_known() -> None:
    cp1 = fixture_snapshot("executor-cp1")
    action = draft_action(cp1)
    assert action.payload is not None
    created = Item(
        "title:Draft A",
        "Draft A",
        "draft",
        body=action.payload["body"],
        item_id="999",
        draft_id="unrelated-draft",
    )
    records = (
        Record(action.id, "intent", {}),
        Record(action.id, "response", {"id": 13, "draft_id": "draft-a"}),
        Record(action.id, "verified", {"item_id": "13", "draft_id": "draft-a"}),
    )
    with pytest.raises(ValueError, match="identity|differs"):
        validate_progress(
            cp1,
            with_added_draft(cp1, created),
            (action,),
            records,
        )
    original = replace(created, item_id="13", draft_id="draft-a")
    validate_progress(cp1, with_added_draft(cp1, original), (action,), records)
    assert (
        journal_state(action, records, (1, action.payload["body"], "13", "draft-a"))
        == "skip"
    )
    assert (
        journal_state(
            action, records[:1], (1, action.payload["body"], "999", "unrelated-draft")
        )
        == "verify"
    )
    assert (
        journal_state(
            action, records, (1, action.payload["body"], "999", "unrelated-draft")
        )
        == "halt"
    )
    assert (
        journal_state(
            action, records[:2], (1, action.payload["body"], "999", "draft-a")
        )
        == "halt"
    )
    assert (
        journal_state(
            action, records[:2], (1, action.payload["body"], "13", "unrelated-draft")
        )
        == "halt"
    )
    verified_without_response = (records[0], records[2])
    for changed in (
        replace(original, item_id="replacement-item"),
        replace(original, draft_id="replacement-draft"),
    ):
        with pytest.raises(ValueError, match="differs"):
            validate_progress(
                cp1,
                with_added_draft(cp1, changed),
                (action,),
                verified_without_response,
            )
        assert (
            journal_state(
                action,
                verified_without_response,
                (1, action.payload["body"], changed.item_id, changed.draft_id),
            )
            == "halt"
        )


def test_progress_rejects_duplicate_existing_draft_key() -> None:
    actions, cp1 = contract()
    original = next(item for item in cp1.items if item.key == "title:Draft B")
    duplicate = replace(original, item_id="extra-item", draft_id="extra-draft")
    current = with_added_draft(cp1, duplicate, prepend=True)
    with pytest.raises(ValueError, match="duplicate|drifted"):
        validate_progress(cp1, current, actions, ())


def test_stage_actions_require_verified_closures() -> None:
    closures = (
        Action("a", "0", "comment", 1, "POST", "", {}, 0, 1),
        Action("b", "0", "issue_state", 1, "PATCH", "", {}, 0, 1),
    )
    drafts = (Action("c", "6", "draft", 0, "POST", "", {}, 0, 1),)
    assert stage_actions("0", (*closures, *drafts), ()) == closures
    for records in ((), (Record("a", "intent", {}),), (Record("a", "verified", {}),)):
        with pytest.raises(ValueError, match="stage 0"):
            stage_actions("6:drafts", (*closures, *drafts), records)
    complete = (Record("a", "verified", {}), Record("b", "verified", {}))
    assert stage_actions("6:drafts", (*closures, *drafts), complete) == drafts
    membership = Action("m", "6", "project_item", 1, "POST", "", {}, 0, 1)
    field = Action("f", "6", "project_fields", 1, "POST", "", {}, 0, 1)
    all_actions = (*closures, membership, *drafts, field)
    assert stage_actions("6:items", all_actions, complete) == (membership,)
    with pytest.raises(ValueError, match="membership"):
        stage_actions("6:drafts", all_actions, complete)
    with_membership = (*complete, Record("m", "verified", {}))
    assert stage_actions("6:drafts", all_actions, with_membership) == drafts
    with pytest.raises(ValueError, match="draft creation"):
        stage_actions("6:fields", all_actions, with_membership)
    assert stage_actions(
        "6:fields", all_actions, (*with_membership, Record("c", "verified", {}))
    ) == (field,)
    with pytest.raises(ValueError, match="unsupported"):
        stage_actions("unknown", all_actions, ())


@pytest.mark.parametrize(
    ("kind", "phases", "observed", "decision"),
    [
        ("issue_state", (), "before", "send"),
        ("issue_state", ("intent",), "after", "verify"),
        ("issue_state", ("intent", "response", "verified"), "after", "skip"),
        ("issue_state", ("intent", "response", "verified"), "before", "halt"),
        ("comment", ("intent",), "after", "verify"),
        ("comment", (), "after", "halt"),
    ],
)
def test_journal_resume_table(
    kind: str, phases: tuple[str, ...], observed: str, decision: str
) -> None:
    action = Action("a", "0", kind, 1, "PATCH", "issues/1", {}, "before", "after")
    records = tuple(Record("a", phase, {}) for phase in phases)
    assert journal_state(action, records, observed) == decision


def test_comment_recovery_preserves_only_unique_numeric_identity() -> None:
    action = Action(
        "a", "0", "comment", 2, "POST", "issues/2/comments", {"body": "marked"}, 0, 1
    )
    assert comment_observation([], "marked") == (0, None)
    assert comment_observation([{"id": 10, "body": "other"}], "marked") == (0, None)
    comments = [{"id": 10, "body": "marked"}, {"id": 11, "body": "other"}]
    observed = comment_observation(comments, "marked")
    assert observed == (1, 10)
    assert observation_value(action, observed) == 1
    assert verified_detail(action, observed, {"status": 200}) == {
        "observed": 1,
        "read": {"status": 200},
        "comment_id": 10,
    }
    assert comment_observation([*comments, {"id": 12, "body": "marked"}], "marked") == (
        2,
        None,
    )
    state = Action(
        "b", "0", "issue_state", 2, "PATCH", "issues/2", {}, "open", "closed"
    )
    assert observation_value(state, "closed") == "closed"
    assert verified_detail(state, "closed", {"status": 200}) == {
        "observed": "closed",
        "read": {"status": 200},
    }


@given(st.lists(st.sampled_from(["intent", "response", "verified"]), max_size=5))
def test_verified_action_never_replays(phases: list[str]) -> None:
    action = Action("a", "0", "issue_state", 1, "PATCH", "", {}, "before", "after")
    records = tuple(Record("a", phase, {}) for phase in ("intent", *phases, "verified"))
    assert journal_state(action, records, "before") == "halt"


def test_journal_header_and_order() -> None:
    actions, _ = contract()
    rows: list[dict[str, Any]] = [
        {"version": 1, "run_id": "digest"},
        {"action_id": actions[0].id, "phase": "intent", "detail": {}},
    ]
    assert validate_journal(rows, "digest", actions) == (
        Record(actions[0].id, "intent", {}),
    )
    with pytest.raises(ValueError, match="header"):
        validate_journal(rows, "other", actions)
    with pytest.raises(ValueError, match="order"):
        validate_journal(
            [*rows, {"action_id": "unknown", "phase": "intent", "detail": {}}],
            "digest",
            actions,
        )
    with pytest.raises(ValueError, match="phase"):
        validate_journal([rows[0], {**rows[1], "phase": "other"}], "digest", actions)
    with pytest.raises(ValueError, match="payload"):
        validate_journal(
            [rows[0], {**rows[1], "detail": {"payload": {"changed": True}}}],
            "digest",
            actions,
        )
    with pytest.raises(ValueError, match="order"):
        validate_journal(
            [rows[0], {**rows[1], "action_id": actions[1].id}, rows[1]],
            "digest",
            actions,
        )


@given(st.text(min_size=1, max_size=12))
def test_journal_record_round_trip(run_id: str) -> None:
    action = Action(
        "a", "0", "comment", 1, "POST", "issues/1/comments", {"body": "x"}, 0, 1
    )
    record = Record(action.id, "intent", {"payload": action.payload})
    rows = [{"version": 1, "run_id": run_id}, json.loads(json.dumps(record.__dict__))]
    assert validate_journal(rows, run_id, (action,)) == (record,)


def test_resume_refuses_unexpected_observation_and_invalid_history() -> None:
    action = Action("a", "0", "issue_state", 1, "PATCH", "issues/1", {}, "old", "new")
    assert journal_state(action, (), "changed") == "halt"
    with pytest.raises(ValueError, match="unknown"):
        journal_state(action, (Record("a", "bad", {}),), "old")
    with pytest.raises(ValueError, match="lacks intent"):
        journal_state(action, (Record("a", "response", {}),), "old")
    with pytest.raises(ValueError, match="after verification"):
        journal_state(
            action,
            (
                Record("a", "intent", {}),
                Record("a", "verified", {}),
                Record("a", "intent", {}),
            ),
            "old",
        )


def test_progress_refuses_unrelated_drift() -> None:
    actions, cp1 = contract()
    first = next(item for item in cp1.items if item.key == "#2")
    changed = replace(first, state="closed", state_reason="not_planned")
    current = replace(
        cp1, items=tuple(changed if item.key == "#2" else item for item in cp1.items)
    )
    records = (Record("0:close:2", "intent", {}),)
    validate_progress(cp1, current, actions, records)
    drifted = replace(
        current,
        items=tuple(
            replace(item, title="drift") if item.key == "#1" else item
            for item in current.items
        ),
    )
    with pytest.raises(ValueError, match="drifted"):
        validate_progress(cp1, drifted, actions, records)


def test_progress_rejects_changed_receipts_and_verified_reversal() -> None:
    actions, cp1 = contract()
    verified = (Record("0:close:2", "verified", {}),)
    with pytest.raises(ValueError, match="drifted"):
        validate_progress(cp1, cp1, actions, verified)
    for current in (
        replace(cp1, version=2),
        replace(cp1, branch_sha="other"),
        replace(cp1, pages=cp1.pages[:-1]),
        replace(cp1, items=cp1.items[:-1]),
    ):
        with pytest.raises(ValueError, match="changed|drifted"):
            validate_progress(cp1, current, actions, ())


@pytest.mark.parametrize(
    ("now", "last", "remaining", "wait"),
    [
        (10.0, None, 5000, 0.0),
        (10.0, 5.0, 5000, 3.0),
        (20.0, 5.0, 5000, 0.0),
        (8.0, 0.0, 50, 0.0),
        (5.0, 0.0, 50, 3.0),
        (10.0, None, 50, 0.0),
    ],
)
def test_write_spacing(
    now: float, last: float | None, remaining: int, wait: float
) -> None:
    assert write_wait_seconds(now, last, remaining) == wait
    with pytest.raises(ValueError, match="budget"):
        write_wait_seconds(now, last, 49)
