"""Pure journal and resume decisions for the staged backfill."""

import hashlib
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
    WriteContext,
    _apply_progress_action,
    _draft_progress,
    _issue_progress,
    _progress_item,
    _project_field_query,
    candidate_actions,
    closure_actions,
    comment_observation,
    confirmed_cp13,
    created_membership_actions,
    created_native_actions,
    created_project_field_actions,
    creation_actions,
    creation_observation,
    dependency_actions,
    draft_actions,
    draft_body_actions,
    draft_observation,
    graphql_field_receipt,
    hierarchy_actions,
    journal_state,
    label_definition_actions,
    label_observation,
    label_retirement_actions,
    membership_actions,
    membership_observation,
    merge_planned_actions,
    native_actions,
    native_field_payload,
    new_project_field_actions,
    observation_value,
    ordered_actions,
    parent_close_actions,
    pr_closure_actions,
    project_field_actions,
    project_fields_observation,
    recorded_actions,
    retitle_actions,
    reviewed_body_actions,
    stage_actions,
    trial_actions,
    validate_journal,
    validate_progress,
    validate_resume_admission,
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


def project_issue_item(number: int, issue_id: int, item_id: str) -> dict[str, Any]:
    """Represent one new issue membership in the Project REST response."""
    return {
        "id": item_id,
        "node_id": f"node-{item_id}",
        "content_type": "Issue",
        "content": {"id": issue_id, "number": number},
        "fields": [],
    }


def with_project_fields(cp1: Snapshot, key: str, fields: object) -> Snapshot:
    """Change one fixture item's Project fields."""
    return replace(
        cp1,
        items=tuple(
            replace(item, project=cast("tuple[tuple[str, str], ...]", fields))
            if item.key == key
            else item
            for item in cp1.items
        ),
    )


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
    changed_fields = with_project_fields(current, "#1", (("Status", "Ready"),))
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
    draft = next(action for action in actions if action.id == "6:fields:title:Draft B")
    for action in (first, draft):
        key = cast("dict[str, Any]", action.payload)["key"]
        changed = with_project_fields(cp1, key, action.after)
        intent = (Record(action.id, "intent", {}),)
        receipt = (*intent, Record(action.id, "verified", {}))
        validate_progress(cp1, changed, (action,), intent)
        validate_progress(cp1, changed, (action,), receipt)
        validate_progress(cp1, cp1, (action,), intent)
        with pytest.raises(ValueError, match="drifted"):
            validate_progress(cp1, cp1, (action,), receipt)
        with pytest.raises(ValueError, match="drifted"):
            validate_progress(cp1, changed, (action,), ())


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
    revised = with_project_fields(cp1, "#1", first.after)
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
    assert draft_observation([], "Draft A") == (0, "", None, None, ())
    item: dict[str, Any] = {
        "content_type": "DraftIssue",
        "id": 13,
        "fields": [],
        "content": {
            "id": "draft-a",
            "title": "Draft A",
            "body": action.payload["body"],
        },
    }
    observed = draft_observation([item], "Draft A")
    assert observed == (1, body, "13", "draft-a", ())
    assert observation_value(action, observed) == action.after
    detail = verified_detail(action, observed, {"status": 200})
    assert detail["item_id"] == "13"
    assert detail["draft_id"] == "draft-a"
    assert detail["created_item"]["body"] == body
    assert draft_observation([item, item], "Draft A") == (2, "", None, None, ())
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
    ready = (
        Record("a", "verified", {}),
        Record("b", "verified", {}),
        Record("stage:0", "complete", {"stage": "0"}),
        Record("stage:3:trial", "complete", {"stage": "3:trial"}),
        Record("stage:4:labels", "complete", {"stage": "4:labels"}),
    )
    complete = (*ready, Record("stage:6:items", "complete", {"stage": "6:items"}))
    assert stage_actions("6:drafts", (*closures, *drafts), complete) == drafts
    membership = Action("m", "6", "project_item", 1, "POST", "", {}, 0, 1)
    field = Action("f", "6", "project_fields", 1, "POST", "", {}, 0, 1)
    all_actions = (*closures, membership, *drafts, field)
    assert stage_actions("6:items", all_actions, ready) == (membership,)
    with pytest.raises(ValueError, match="membership"):
        stage_actions("6:drafts", all_actions, ready)
    with_membership = (*ready, Record("m", "verified", {}))
    with pytest.raises(ValueError, match="membership"):
        stage_actions("6:drafts", all_actions, with_membership)
    completed_membership = (
        *with_membership,
        Record("stage:6:items", "complete", {"stage": "6:items"}),
    )
    assert stage_actions("6:drafts", all_actions, completed_membership) == drafts
    with pytest.raises(ValueError, match="draft creation"):
        stage_actions("6:fields", all_actions, completed_membership)
    assert stage_actions(
        "6:fields",
        all_actions,
        (
            *completed_membership,
            Record("c", "verified", {}),
            Record("stage:6:drafts", "complete", {"stage": "6:drafts"}),
        ),
    ) == (field,)
    with pytest.raises(ValueError, match="unsupported"):
        stage_actions("unknown", all_actions, ())


def test_stage_actions_refuse_interrupted_trial_before_cleanup_intent() -> None:
    add = Action(
        "3:add:149:96", "3:trial", "trial_add", 149, "POST", "", {}, (), ("#96",)
    )
    records = (
        Record("stage:0", "complete", {"stage": "0"}),
        Record(add.id, "verified", {}),
    )
    with pytest.raises(ValueError, match="stage 3:trial"):
        stage_actions("4:labels", (add,), records)


def test_checkpoint_and_resume_admission_use_plain_values() -> None:
    current = fixture_snapshot("executor-cp1")
    digests = {"assignments": "abc"}
    checkpoint: dict[str, Any] = {
        "snapshot": asdict(current),
        "differences": [],
        "digests": digests,
    }
    data = json.dumps(checkpoint).encode()
    token = f"CP13:{hashlib.sha256(data).hexdigest()}"
    assert confirmed_cp13("0", None, None, digests) is None
    assert confirmed_cp13("15", data, token, digests) == json.loads(data)
    for raw, confirmation, expected in (
        (None, token, "requires confirmed"),
        (data, "CP13:wrong", "confirmation differs"),
        (
            json.dumps({**checkpoint, "differences": ["drift"]}).encode(),
            token,
            "confirmation differs",
        ),
    ):
        with pytest.raises(ValueError, match=expected):
            confirmed_cp13("15", raw, confirmation, digests)
    bad_data = json.dumps({**checkpoint, "differences": ["drift"]}).encode()
    with pytest.raises(ValueError, match="clean comparison"):
        confirmed_cp13(
            "15", bad_data, f"CP13:{hashlib.sha256(bad_data).hexdigest()}", digests
        )
    assert validate_resume_admission("0", None, current, (), None) is None
    assert (
        validate_resume_admission("15", current, current, (), ("closed", False)) is None
    )
    with pytest.raises(ValueError, match="confirmed CP13"):
        validate_resume_admission(
            "15", replace(current, branch_sha="other"), current, (), ("closed", False)
        )
    assert (
        validate_resume_admission(
            "15",
            replace(current, branch_sha="other"),
            current,
            (Record("15:label", "intent", {}),),
            ("closed", False),
        )
        is None
    )
    with pytest.raises(ValueError, match="PR 97"):
        validate_resume_admission("3:trial", None, current, (), ("open", False))


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


def test_b4_native_write_order_and_definition_resolution() -> None:
    tables, cp1, _ = field_contract()
    plan = operation_plan(tables, cp1)
    actions = native_actions(cp1, plan)
    first = actions[:2]
    assert [action.kind for action in first] == ["issue_type", "native"]
    assert first[0].payload == {"type": "Chore"}
    assert first[1].after == (
        ("Priority", "Standard"),
        ("Severity", ""),
        ("Work type", "Planned"),
    )
    definitions = [
        {
            "id": 11,
            "name": "Priority",
            "data_type": "single_select",
            "options": [{"name": "Standard"}],
        },
        {
            "id": 12,
            "name": "Work type",
            "data_type": "single_select",
            "options": [{"name": "Planned"}],
        },
    ]
    assert native_field_payload(first[1], definitions) == {
        "issue_field_values": [
            {"field_id": 11, "value": "Standard"},
            {"field_id": 12, "value": "Planned"},
        ]
    }
    with pytest.raises(ValueError, match="option"):
        native_field_payload(
            first[1], [{**definitions[0], "options": []}, definitions[1]]
        )
    with pytest.raises(ValueError, match="definition"):
        native_field_payload(first[1], definitions[:1])


def test_b4_exact_rest_write_contracts() -> None:
    tables, cp1, _ = field_contract()
    plan = operation_plan(tables, cp1)
    assert pr_closure_actions("digest", "reviewed") == (
        Action(
            "0:pr-comment:97",
            "0",
            "comment",
            97,
            "POST",
            "issues/97/comments",
            {"body": "reviewed\n\n<!-- work-model-backfill:digest:0:pr-comment:97 -->"},
            0,
            1,
        ),
        Action(
            "0:pr-close:97",
            "0",
            "pr_state",
            97,
            "PATCH",
            "pulls/97",
            {"state": "closed"},
            ("open", False),
            ("closed", False),
        ),
    )
    assert label_definition_actions(
        ({"name": "type/chore", "color": "ABCDEF", "description": "Chore"},), ()
    ) == (
        Action(
            "4:label:type/chore",
            "4:labels",
            "label_create",
            0,
            "POST",
            "labels",
            {"name": "type/chore", "color": "ABCDEF", "description": "Chore"},
            0,
            ("type/chore", "abcdef", "Chore"),
        ),
    )
    trial_cp1 = replace(
        cp1,
        items=(
            *cp1.items,
            Item("#149", "dependent", "open", issue_id="149"),
            Item("#96", "blocker", "closed", issue_id="96"),
        ),
    )
    assert trial_actions(trial_cp1, plan) == (
        Action(
            "3:add:149:96",
            "3:trial",
            "trial_add",
            149,
            "POST",
            "issues/149/dependencies/blocked_by",
            {"issue_id": 96},
            (),
            ("#96",),
        ),
        Action(
            "3:remove:149:96",
            "3:trial",
            "trial_remove",
            149,
            "DELETE",
            "issues/149/dependencies/blocked_by/96",
            None,
            ("#96",),
            (),
        ),
    )
    assert native_actions(cp1, plan)[:2] == (
        Action(
            "6:native:type:#1",
            "6:native",
            "issue_type",
            1,
            "PATCH",
            "issues/1",
            {"type": "Chore"},
            "",
            "Chore",
        ),
        Action(
            "6:native:native:#1",
            "6:native",
            "native",
            1,
            "POST",
            "issues/1/issue-field-values",
            {"fields": {"Priority": "Standard", "Work type": "Planned"}},
            (("Priority", ""), ("Severity", ""), ("Work type", "")),
            (("Priority", "Standard"), ("Severity", ""), ("Work type", "Planned")),
        ),
    )
    assert retitle_actions(cp1, plan, tables) == (
        Action(
            "6T:title:1",
            "6T",
            "title",
            1,
            "PATCH",
            "issues/1",
            {"title": "tooling(project): build a model"},
            "tooling(project): old title",
            "tooling(project): build a model",
        ),
    )
    assert creation_actions(tables, cp1, plan, "9:create") == (
        Action(
            "9:create:000:epic: migration",
            "9:create",
            "issue_create",
            0,
            "POST",
            "issues",
            {
                "title": "epic: migration",
                "body": "## Goal\n\nMigrate records.\n\n## Finish line\n\nAll records migrated.",
                "type": "Epic",
            },
            0,
            1,
        ),
    )
    parent = Item("#3", "epic: migration", "open", issue_type="Epic", issue_id="103")
    current = replace(cp1, items=(*cp1.items, parent))
    assert created_native_actions(current, plan, "9:native") == (
        Action(
            "9:native:000:epic: migration",
            "9:native",
            "native",
            3,
            "POST",
            "issues/3/issue-field-values",
            {"fields": {"Work type": "Planned"}},
            (("Priority", ""), ("Severity", ""), ("Work type", "")),
            (("Priority", ""), ("Severity", ""), ("Work type", "Planned")),
        ),
    )
    assert created_membership_actions(current, plan, "9:items") == (
        Action(
            "9:item:000:epic: migration",
            "9:items",
            "project_item",
            3,
            "POST",
            "orgs/tbhb-dev/projectsV2/1/items",
            {"type": "Issue", "id": 103},
            (0, "103"),
            (1, "103"),
        ),
    )
    assert hierarchy_actions(tables, current, plan) == (
        Action(
            "10:parent:000:#1",
            "10",
            "parent",
            3,
            "POST",
            "issues/3/sub_issues",
            {"sub_issue_id": 1, "child": "#1"},
            "",
            "#3",
        ),
        Action(
            "10:parent:001:#2",
            "10",
            "parent",
            3,
            "POST",
            "issues/3/sub_issues",
            {"sub_issue_id": 2, "child": "#2"},
            "",
            "#3",
        ),
    )
    assert dependency_actions(tables, current, plan) == (
        Action(
            "11:edge:000:1 <- 2",
            "11:links",
            "blocker",
            1,
            "POST",
            "issues/1/dependencies/blocked_by",
            {"issue_id": 2},
            (),
            ("#2",),
        ),
    )


def test_b4_native_replace_clears_reviewed_empty_values() -> None:
    tables, cp1, _ = field_contract()
    plan = operation_plan(tables, cp1)
    cp1 = replace(
        cp1,
        items=tuple(
            replace(item, native=(("Priority", "Intangible"), ("Work type", "Planned")))
            if item.key == "#1"
            else item
            for item in cp1.items
        ),
    )
    assert native_actions(cp1, plan)[1].method == "POST"
    cleared = replace(
        cp1,
        items=tuple(
            replace(
                item,
                native=(
                    ("Priority", "Intangible"),
                    ("Severity", "SEV2"),
                    ("Work type", "Planned"),
                ),
            )
            if item.key == "#1"
            else item
            for item in cp1.items
        ),
    )
    assert native_actions(cleared, plan)[1].method == "PUT"
    pinned = tuple(
        replace(
            step,
            native_writes=tuple(
                replace(write, fields=(*write.fields, ("Severity", "")))
                if write.key == "#1"
                else write
                for write in step.native_writes
            ),
        )
        if step.number == "6"
        else step
        for step in plan
    )
    clear = native_actions(cleared, pinned)[1]
    assert clear.method == "PUT"
    assert clear.after == (
        ("Priority", "Standard"),
        ("Severity", ""),
        ("Work type", "Planned"),
    )


def test_b4_fields_for_added_item_and_journal_recovery() -> None:
    tables, original, metadata = field_contract()
    cp1 = without_membership(original)
    current = replace(
        cp1,
        items=tuple(
            replace(item, item_id="item-1") if item.key == "#1" else item
            for item in cp1.items
        ),
        pages=original.pages,
    )
    actions = new_project_field_actions(tables, cp1, current, metadata)
    assert len(actions) == 1
    action = actions[0]
    assert action.payload is not None
    assert action.step == "6:new-fields"
    assert action.payload["key"] == "#1"
    assert "singleSelectOptionId" in action.payload["query"]
    saved = recorded_actions(
        [
            {"version": 1, "run_id": "digest"},
            asdict(
                Record(
                    action.id,
                    "intent",
                    {"action": asdict(action), "payload": action.payload},
                )
            ),
        ]
    )
    assert saved == actions
    assert (
        ordered_actions((action, Action("c", "0", "comment", 1, "POST", "", {}, 0, 1)))[
            0
        ].step
        == "0"
    )


def test_b4_creation_identity_and_progress() -> None:
    tables, cp1, _ = field_contract()
    plan = operation_plan(tables, cp1)
    action = creation_actions(tables, cp1, plan, "9:create")[0]
    assert action.payload is not None
    assert action.payload == {
        "title": "epic: migration",
        "body": "## Goal\n\nMigrate records.\n\n## Finish line\n\nAll records migrated.",
        "type": "Epic",
    }
    raw: dict[str, Any] = {
        "number": 3,
        "id": 103,
        "title": action.payload["title"],
        "body": action.payload["body"],
        "state": "open",
        "type": {"name": "Epic"},
        "labels": [],
    }
    observed = creation_observation([raw], action.payload)
    assert observed[1] == Item(
        "#3",
        "epic: migration",
        "open",
        issue_type="Epic",
        native=(("Priority", ""), ("Severity", ""), ("Work type", "")),
        body=action.payload["body"],
        issue_id="103",
    )
    assert creation_observation([{**raw, "body": "conflict"}], action.payload) == (
        1,
        None,
    )
    assert creation_observation(
        [{**raw, "type": {"name": "Chore"}}], action.payload
    ) == (1, None)
    assert creation_observation([raw, {**raw, "number": 4}], action.payload) == (
        2,
        None,
    )
    assert observation_value(action, observed) == 1
    assert (
        journal_state(action, (Record(action.id, "intent", {}),), observed) == "verify"
    )
    created = observed[1]
    assert created is not None
    pages = tuple(
        replace(page, count=page.count + 1, total_count=page.total_count + 1)
        if page.collection in {"issues", "native", "parents", "blockers"}
        else page
        for page in cp1.pages
    ) + tuple(
        Page(f"{kind}:#3", 1, 0, 1, 0) for kind in ("native", "blockers", "sub_issues")
    )
    current = replace(cp1, items=(*cp1.items, created), pages=pages)
    intent = Record(action.id, "intent", {"action": asdict(action)})
    verified = Record(action.id, "verified", verified_detail(action, observed, {}))
    validate_progress(cp1, current, (action,), (intent,))
    validate_progress(cp1, current, (action,), (intent, verified))
    assert created_membership_actions(current, plan, "9:items")[0].payload == {
        "type": "Issue",
        "id": 103,
    }
    assert created_native_actions(current, plan, "9:native")[0].payload == {
        "fields": {"Work type": "Planned"},
    }
    changed = replace(current, items=(*cp1.items, replace(created, issue_id="999")))
    with pytest.raises(ValueError, match="identity"):
        validate_progress(cp1, changed, (action,), (intent, verified))


def test_b4_hierarchy_dependency_and_reviewed_bodies() -> None:
    tables, cp1, _ = field_contract()
    plan = operation_plan(tables, cp1)
    parent = Item("#3", "epic: migration", "open", issue_type="Epic", issue_id="103")
    current = replace(cp1, items=(*cp1.items, parent))
    hierarchy = hierarchy_actions(tables, current, plan)
    assert [
        (cast("dict[str, Any]", action.payload)["sub_issue_id"], action.number)
        for action in hierarchy
    ] == [(1, 3), (2, 3)]
    assert hierarchy[0].after == "#3"
    links = dependency_actions(tables, current, plan)
    assert len(links) == 1
    assert links[0].payload == {"issue_id": 2}
    assert links[0].before == ()
    assert links[0].after == ("#2",)
    edited = replace(
        tables,
        assignments=tuple(
            {**row, "body revision": "required"} if row["number"] == "1" else row
            for row in tables.assignments
        ),
    )
    with pytest.raises(ValueError, match="reviewed body"):
        reviewed_body_actions(edited, current, {})
    assert reviewed_body_actions(edited, current, {"#1": "reviewed"}) == (
        Action(
            "11:body:1",
            "11:bodies",
            "body",
            1,
            "PATCH",
            "issues/1",
            {"body": "reviewed"},
            next(item.body for item in cp1.items if item.key == "#1"),
            "reviewed",
        ),
    )


def test_b4_trial_pr_labels_and_retitle_preconditions() -> None:
    tables, cp1, _ = field_contract()
    plan = operation_plan(tables, cp1)
    trial_cp1 = replace(
        cp1,
        items=(
            *cp1.items,
            Item("#149", "dependent", "open", issue_id="149"),
            Item("#96", "blocker", "closed", issue_id="96"),
        ),
    )
    assert [action.kind for action in trial_actions(trial_cp1, plan)] == [
        "trial_add",
        "trial_remove",
    ]
    assert pr_closure_actions("digest", "reviewed decision")[1].after == (
        "closed",
        False,
    )
    with pytest.raises(ValueError, match="missing"):
        pr_closure_actions("digest", "")
    labels = label_definition_actions(
        ({"name": "type/chore", "color": "ABCDEF", "description": "Chore"},), ()
    )
    assert labels[0].payload is not None
    assert labels[0].payload["color"] == "ABCDEF"
    assert label_observation([], "type/chore") == 0
    assert (
        observation_value(
            labels[0],
            label_observation(
                [
                    {
                        "id": 4,
                        "name": "type/chore",
                        "color": "abcdef",
                        "description": "Chore",
                    }
                ],
                "type/chore",
            ),
        )
        == labels[0].after
    )
    with pytest.raises(ValueError, match="differs"):
        label_definition_actions(
            ({"name": "type/chore", "color": "ABCDEF", "description": "Chore"},),
            (
                {
                    "id": 4,
                    "name": "type/chore",
                    "color": "123456",
                    "description": "Chore",
                },
            ),
        )
    assert (
        retitle_actions(cp1, plan, tables)[0].after == "tooling(project): build a model"
    )
    labelled = replace(
        cp1,
        items=tuple(
            replace(item, labels=("type/chore",)) if item.key == "#1" else item
            for item in cp1.items
        ),
    )
    rows = tuple(
        {**row, "old type labels": "type/chore"} if row["number"] == "1" else row
        for row in tables.assignments
    )
    retired = label_retirement_actions(replace(tables, assignments=rows), labelled)
    assert retired == (
        Action(
            "15:label:1:type/chore",
            "15",
            "label_delete",
            1,
            "DELETE",
            "issues/1/labels/type%2Fchore",
            None,
            ("type/chore",),
            (),
        ),
    )


def test_b4_parent_and_incident_project_fields_and_closure() -> None:
    tables, cp1, metadata = field_contract()
    parent = Item(
        "#3",
        "epic: migration",
        "open",
        issue_type="Epic",
        issue_id="103",
        item_id="item-3",
    )
    parent_raw = project_issue_item(3, 103, "item-3")
    current = replace(cp1, items=(*cp1.items, parent))
    metadata = replace(metadata, items=[*metadata.items, parent_raw])
    parent_fields = created_project_field_actions(tables, current, metadata, "9:fields")
    assert parent_fields == (
        Action(
            "9:fields:000:epic: migration",
            "9:fields",
            "project_fields",
            3,
            "POST",
            "graphql",
            {
                "query": 'mutation{f0:updateProjectV2ItemFieldValue(input:{projectId:"project-id",itemId:"node-item-3",fieldId:"field-Status",value:{singleSelectOptionId:"option-Backlog"}}){projectV2Item{id}}}',
                "key": "#3",
                "item_id": "item-3",
                "node_id": "node-item-3",
                "mutation_count": 1,
            },
            (("Status", ""),),
            (("Status", "Backlog"),),
        ),
    )
    with pytest.raises(ValueError, match="missing"):
        created_project_field_actions(
            tables, current, replace(metadata, items=metadata.items[:-1]), "9:fields"
        )
    closed_table = replace(tables, parents=({**tables.parents[0], "state": "closed"},))
    assert parent_close_actions(closed_table, current) == (
        Action(
            "9:close:000:epic: migration",
            "9:close",
            "issue_state",
            3,
            "PATCH",
            "issues/3",
            {"state": "closed", "state_reason": "completed"},
            ("open", ""),
            ("closed", "completed"),
        ),
    )
    assert (
        parent_close_actions(
            closed_table,
            replace(
                current,
                items=(
                    *cp1.items,
                    replace(parent, state="closed", state_reason="completed"),
                ),
            ),
        )
        == ()
    )

    incident_row = {
        **next(row for row in tables.assignments if row["title"] == "Draft A"),
        "title": "inc(github): synthetic outage",
        "backfill mode": "issue",
        "issue type": "Incident",
        "severity": "SEV2",
        "size": "M",
    }
    incident = Item(
        "#4",
        incident_row["title"],
        "open",
        issue_type="Incident",
        issue_id="104",
        item_id="item-4",
    )
    incident_raw = project_issue_item(4, 104, "item-4")
    incident_tables = replace(tables, assignments=(*tables.assignments, incident_row))
    incident_plan = operation_plan(incident_tables, cp1)
    assert creation_actions(incident_tables, cp1, incident_plan, "12:create") == (
        Action(
            "12:create:000:inc(github): synthetic outage",
            "12:create",
            "issue_create",
            0,
            "POST",
            "issues",
            {
                "title": "inc(github): synthetic outage",
                "body": "## Incident\n\ninc(github): synthetic outage\n\n## Record\n\n",
                "type": "Incident",
            },
            0,
            1,
        ),
    )
    incident_current = replace(current, items=(*current.items, incident))
    incident_meta = replace(metadata, items=[*metadata.items, incident_raw])
    incident_fields = created_project_field_actions(
        incident_tables, incident_current, incident_meta, "12:fields"
    )
    assert len(incident_fields) == 1
    assert incident_fields[0].id == "12:fields:000:inc(github): synthetic outage"
    payload = incident_fields[0].payload
    assert payload is not None
    assert payload["mutation_count"] == 4
    assert incident_fields[0].after == (
        ("Area", "tooling"),
        ("Harness", "codex"),
        ("Size", "M"),
        ("Status", "Backlog"),
        ("Worker", ""),
    )


def test_b4_copied_draft_body_and_scope_verdict() -> None:
    tables, cp1, metadata = field_contract()
    raw = [
        {**item, "content": {**item["content"], "node_id": "node-draft-b"}}
        if item["id"] == "item-b"
        else item
        for item in metadata.items
    ]
    metadata = replace(metadata, items=raw)
    body = draft_body_actions(tables, cp1, metadata)
    assert body == (
        Action(
            "6:body:title:Draft B",
            "6:body",
            "draft_body",
            0,
            "POST",
            "graphql",
            {
                "query": 'mutation{updateProjectV2DraftIssue(input:{draftIssueId:"node-draft-b",body:"- Class: chore\\n- Priority: Standard\\n- Work type: Unplanned\\n- Severity: none\\n- Size: "}){draftIssue{id body}}}',
                "key": "title:Draft B",
                "draft_id": "node-draft-b",
            },
            "- Class: chore\n- Size: ",
            "- Class: chore\n- Priority: Standard\n- Work type: Unplanned\n- Severity: none\n- Size: ",
        ),
    )
    with pytest.raises(ValueError, match="node identity"):
        draft_body_actions(tables, cp1, replace(metadata, items=metadata.items[:2]))
    updated = replace(
        cp1,
        items=tuple(
            replace(item, body=cast("str", body[0].after))
            if item.key == "title:Draft B"
            else item
            for item in cp1.items
        ),
    )
    assert draft_body_actions(tables, updated, metadata) == ()

    rows = tuple(
        {**row, "refinement verdict": "new verdict required"}
        if row["number"] == "1"
        else row
        for row in tables.assignments
    )
    reviewed = replace(tables, assignments=rows)
    plan = operation_plan(reviewed, cp1)
    item = next(item for item in cp1.items if item.key == "#1")
    digest = hashlib.sha256(item.body.encode()).hexdigest()
    verdict = {
        "#1": {
            "title": "tooling(project): build a model",
            "body_sha256": digest,
            "comment_id": 42,
        }
    }
    comment = {
        "id": 42,
        "user": {"login": "tbhb-agent-reviewer"},
        "body": f"Issue review: ready\nBody-SHA256: {digest}",
    }
    comments = {"#1": [comment]}
    assert retitle_actions(cp1, plan, reviewed, verdict, comments)[0].number == 1
    with pytest.raises(ValueError, match="verdict"):
        retitle_actions(cp1, plan, reviewed, verdict, {"#1": []})
    for bad in (
        {**comment, "user": {"login": "tbhb-agent"}},
        {
            **comment,
            "body": f"Do not use this old verdict:\n> Issue review: ready\n> Body-SHA256: {digest}",
        },
        {
            **comment,
            "body": f"Issue review: changes-requested\nBody-SHA256: {digest}\nIssue review: ready",
        },
        {**comment, "body": f"Issue review: ready\nBody-SHA256: {digest} withdrawn"},
    ):
        with pytest.raises(ValueError, match="verdict"):
            retitle_actions(cp1, plan, reviewed, verdict, {"#1": [bad]})


def test_b4_resume_refuses_changed_reviewed_input() -> None:
    action = Action(
        "9:create:000:epic",
        "9:create",
        "issue_create",
        0,
        "POST",
        "issues",
        {"body": "reviewed"},
        0,
        1,
    )
    assert merge_planned_actions((action,), (action,)) == (action,)
    with pytest.raises(ValueError, match="changed after journal intent"):
        merge_planned_actions(
            (action,), (replace(action, payload={"body": "changed"}),)
        )


def test_b4_verified_receipts_preserve_creation_and_project_identities() -> None:
    read = {"status": 200}
    draft = Action(
        "6:draft:title:Draft A",
        "6",
        "draft",
        0,
        "POST",
        "drafts",
        {"title": "Draft A", "body": "reviewed"},
        (0, ""),
        (1, "reviewed"),
    )
    draft_observed = (
        1,
        "reviewed",
        "project-item-4",
        "draft-4",
        (("Status", "Backlog"),),
    )
    expected_draft = Item(
        "title:Draft A",
        "Draft A",
        "draft",
        body="reviewed",
        project=(("Status", "Backlog"),),
        item_id="project-item-4",
        draft_id="draft-4",
    )
    assert verified_detail(draft, draft_observed, read) == {
        "observed": (1, "reviewed"),
        "read": read,
        "item_id": "project-item-4",
        "draft_id": "draft-4",
        "created_item": asdict(expected_draft),
    }
    created = Item(
        "#3",
        "epic: migration",
        "open",
        issue_type="Epic",
        issue_id="103",
        body="reviewed",
    )
    issue = Action(
        "9:create",
        "9:create",
        "issue_create",
        0,
        "POST",
        "issues",
        {"title": created.title},
        0,
        1,
    )
    assert verified_detail(issue, (1, created), read) == {
        "observed": 1,
        "read": read,
        "created_item": asdict(created),
        "issue_id": "103",
    }
    with pytest.raises(ValueError, match="identity is missing"):
        verified_detail(issue, (1, None), read)
    label = Action(
        "4:label",
        "4:labels",
        "label_create",
        0,
        "POST",
        "labels",
        {},
        0,
        ("type/chore", "abcdef", "Chore"),
    )
    assert verified_detail(label, ("type/chore", "abcdef", "Chore", "55"), read) == {
        "observed": ("type/chore", "abcdef", "Chore"),
        "read": read,
        "label_id": "55",
    }
    member = Action(
        "6:item",
        "6",
        "project_item",
        3,
        "POST",
        "items",
        {"id": 103},
        (0, "103"),
        (1, "103"),
    )
    assert verified_detail(
        member, (1, "103", "project-item-4", (("Status", "Backlog"),)), read
    ) == {
        "observed": (1, "103"),
        "read": read,
        "item_id": "project-item-4",
        "project_fields": (("Status", "Backlog"),),
    }


def test_b4_journal_resume_requires_same_created_identity() -> None:
    item = Item("#3", "epic: migration", "open", issue_id="103")
    issue = Action(
        "9:create", "9:create", "issue_create", 0, "POST", "issues", {}, 0, 1
    )
    own = (Record(issue.id, "intent", {}), Record(issue.id, "response", {"id": 103}))
    assert journal_state(issue, own, (1, item)) == "verify"
    assert journal_state(issue, own, (1, replace(item, issue_id="104"))) == "halt"
    assert journal_state(issue, own, (2, None)) == "halt"
    assert journal_state(issue, own, (0, None)) == "send"

    label = Action(
        "4:label",
        "4:labels",
        "label_create",
        0,
        "POST",
        "labels",
        {},
        0,
        ("type/chore", "abcdef", "Chore"),
    )
    labelled = (
        Record(label.id, "intent", {}),
        Record(label.id, "response", {"id": 55}),
    )
    assert (
        journal_state(label, labelled, ("type/chore", "abcdef", "Chore", "55"))
        == "verify"
    )
    assert (
        journal_state(label, labelled, ("type/chore", "abcdef", "Chore", "56"))
        == "halt"
    )
    assert journal_state(label, labelled, 0) == "send"
    verified_label = (
        Record(label.id, "intent", {}),
        Record(label.id, "verified", {"label_id": "55"}),
    )
    assert (
        journal_state(label, verified_label, ("type/chore", "abcdef", "Chore", "55"))
        == "skip"
    )
    assert (
        journal_state(label, verified_label, ("type/chore", "abcdef", "Chore", "56"))
        == "halt"
    )

    member = Action(
        "9:item",
        "9:items",
        "project_item",
        3,
        "POST",
        "items",
        {"id": 103},
        (0, "103"),
        (1, "103"),
    )
    joined = (
        Record(member.id, "intent", {}),
        Record(member.id, "response", {"id": 14}),
    )
    assert journal_state(member, joined, (1, "103", "14", ())) == "verify"
    assert journal_state(member, joined, (1, "103", "15", ())) == "halt"
    assert journal_state(member, joined, (1, "103", None, ())) == "halt"
    assert journal_state(member, joined, (0, "103", None, ())) == "halt"


def test_b4_progress_rejects_changed_new_issue_and_draft() -> None:
    issue_action = Action(
        "9:create",
        "9:create",
        "issue_create",
        0,
        "POST",
        "issues",
        {"title": "epic: migration", "body": "reviewed", "type": "Epic"},
        0,
        1,
    )
    issue = Item(
        "#3",
        "epic: migration",
        "open",
        issue_type="Epic",
        issue_id="103",
        body="reviewed",
    )
    intent = Record(issue_action.id, "intent", {})
    assert _issue_progress(issue_action, {issue.key: issue}, (intent,)) == issue
    with pytest.raises(ValueError, match="unrecorded"):
        _issue_progress(issue_action, {issue.key: issue}, ())
    with pytest.raises(ValueError, match="ambiguous"):
        _issue_progress(
            issue_action, {issue.key: issue, "#4": replace(issue, key="#4")}, (intent,)
        )
    for changed in (replace(issue, body="changed"), replace(issue, issue_type="Chore")):
        with pytest.raises(ValueError, match="differs"):
            _issue_progress(issue_action, {changed.key: changed}, (intent,))
    response = Record(issue_action.id, "response", {"id": 103})
    with pytest.raises(ValueError, match="identity"):
        _issue_progress(
            issue_action,
            {issue.key: replace(issue, issue_id="104")},
            (intent, response),
        )
    verified = Record(issue_action.id, "verified", {"created_item": asdict(issue)})
    assert (
        _issue_progress(issue_action, {issue.key: issue}, (intent, verified)) == issue
    )
    with pytest.raises(ValueError, match="disappeared"):
        _issue_progress(issue_action, {}, (intent, verified))

    draft_action = Action(
        "6:draft",
        "6",
        "draft",
        0,
        "POST",
        "drafts",
        {"title": "Draft A", "body": "reviewed"},
        (0, ""),
        (1, "reviewed"),
    )
    draft = Item(
        "title:Draft A",
        "Draft A",
        "draft",
        body="reviewed",
        item_id="item-1",
        draft_id="draft-1",
    )
    draft_intent = Record(draft_action.id, "intent", {})
    assert _draft_progress(draft_action, {draft.key: draft}, (draft_intent,)) == draft
    with pytest.raises(ValueError, match="unrecorded"):
        _draft_progress(draft_action, {draft.key: draft}, ())
    for changed in (
        replace(draft, state="open"),
        replace(draft, title="changed"),
        replace(draft, body="changed"),
        replace(draft, item_id=""),
        replace(draft, draft_id=""),
        replace(draft, issue_id="103"),
    ):
        with pytest.raises(ValueError, match="differs"):
            _draft_progress(draft_action, {draft.key: changed}, (draft_intent,))
    draft_receipt = Record(
        draft_action.id, "response", {"id": "item-1", "draft_id": "draft-1"}
    )
    with pytest.raises(ValueError, match="differs"):
        _draft_progress(
            draft_action,
            {draft.key: replace(draft, item_id="other")},
            (draft_intent, draft_receipt),
        )
    draft_verified = Record(
        draft_action.id, "verified", {"created_item": asdict(draft)}
    )
    assert (
        _draft_progress(
            draft_action, {draft.key: draft}, (draft_intent, draft_verified)
        )
        == draft
    )
    with pytest.raises(ValueError, match="disappeared"):
        _draft_progress(draft_action, {}, (draft_intent, draft_verified))


def test_b4_progress_routes_field_body_parent_and_membership_effects() -> None:
    issue = Item("#1", "old", "open", issue_id="101")
    draft = Item(
        "title:Draft B",
        "Draft B",
        "draft",
        body="old",
        item_id="item-b",
        draft_id="draft-b",
    )
    expected = {issue.key: issue, draft.key: draft}
    fields = Action(
        "6:fields:#1",
        "6",
        "project_fields",
        1,
        "POST",
        "graphql",
        {"key": "#1"},
        (("Status", ""),),
        (("Status", "Ready"),),
    )
    body = Action(
        "6:body:title:Draft B",
        "6:body",
        "draft_body",
        0,
        "POST",
        "graphql",
        {"key": "title:Draft B"},
        "old",
        "new",
    )
    parent = Action(
        "10:parent:#1",
        "10",
        "parent",
        3,
        "POST",
        "issues/3/sub_issues",
        {"child": "#1"},
        "",
        "#3",
    )
    observed = {
        "#1": replace(issue, project=(("Status", "Ready"),), parent="#3"),
        "title:Draft B": replace(draft, body="new"),
    }
    actions = (fields, body, parent)
    records = tuple(Record(action.id, "verified", {}) for action in actions)
    for action in actions:
        _apply_progress_action(action, expected, observed, actions, records)
    assert expected == observed

    original = replace(issue, item_id="")
    joined = replace(original, item_id="new-item", project=(("Status", "Ready"),))
    member = Action(
        "6:item:1",
        "6",
        "project_item",
        1,
        "POST",
        "items",
        {"id": 101},
        (0, "101"),
        (1, "101"),
    )
    saved = (
        Record(member.id, "intent", {}),
        Record(member.id, "verified", {"item_id": "new-item", "project_fields": []}),
    )
    with pytest.raises(ValueError, match="fields changed"):
        _apply_progress_action(
            member, {"#1": original}, {"#1": joined}, (member,), saved
        )
    fields_for_new = replace(fields, id="6:new-fields:#1", step="6:new-fields")
    new_records = (*saved, Record(fields_for_new.id, "intent", {}))
    projection = {"#1": original}
    _apply_progress_action(
        member, projection, {"#1": joined}, (member, fields_for_new), new_records
    )
    assert projection["#1"] == replace(original, item_id="new-item")


def test_b4_stage_sorting_uses_all_stage_six_write_kinds() -> None:
    def action(key: str, step: str, kind: str) -> Action:
        return Action(key, step, kind, 1, "POST", "", None, 0, 1)

    drafts = action("draft", "6", "draft")
    member = action("member", "6", "project_item")
    fields = action("fields", "6", "project_fields")
    later = action("parent", "10", "parent")
    earlier = action("closure", "0", "comment")
    assert ordered_actions((later, fields, drafts, member, earlier)) == (
        earlier,
        member,
        drafts,
        fields,
        later,
    )


def test_b4_trial_resume_needs_add_receipt_and_verified_cleanup_predecessor() -> None:
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
    remove = Action(
        "3:remove:149:96",
        "3:trial",
        "trial_remove",
        149,
        "DELETE",
        "issues/149/dependencies/blocked_by/96",
        None,
        ("#96",),
        (),
    )
    add_intent = Record(add.id, "intent", {})
    assert journal_state(add, (add_intent,), ("#96",)) == "halt"
    assert (
        journal_state(add, (add_intent, Record(add.id, "response", {})), ("#96",))
        == "verify"
    )
    assert journal_state(add, (add_intent,), ()) == "send"
    remove_intent = Record(remove.id, "intent", {})
    assert journal_state(remove, (remove_intent,), ("#96",)) == "halt"
    add_verified = Record(add.id, "verified", {})
    assert journal_state(remove, (add_verified, remove_intent), ("#96",)) == "send"
    assert journal_state(remove, (add_verified, remove_intent), ()) == "verify"
    assert (
        journal_state(
            remove, (add_verified, remove_intent, Record(remove.id, "verified", {})), ()
        )
        == "skip"
    )


def test_b4_journal_and_definition_failures_name_the_failed_guard() -> None:
    action = Action(
        "0:comment:1",
        "0",
        "comment",
        1,
        "POST",
        "issues/1/comments",
        {"body": "reviewed"},
        0,
        1,
    )
    header = {"version": 1, "run_id": "digest"}
    intent = asdict(Record(action.id, "intent", {"payload": action.payload}))
    cases = (
        ([{**header, "run_id": "other"}], "journal header differs from CP1"),
        (
            [header, {**intent, "action_id": "foreign"}],
            "journal action order differs from plan",
        ),
        ([header, {**intent, "phase": "other"}], "invalid journal phase"),
        (
            [header, {**intent, "detail": {"payload": {"body": "changed"}}}],
            "journal write payload differs from plan",
        ),
    )
    for rows, message in cases:
        with pytest.raises(ValueError, match=message) as failure:
            validate_journal(rows, "digest", (action,))
        assert str(failure.value) == message

    reviewed = {"name": "type/chore", "color": "ABCDEF", "description": "Chore"}
    with pytest.raises(
        ValueError, match="duplicate reviewed label definition"
    ) as duplicate:
        label_definition_actions((reviewed, reviewed), ())
    assert str(duplicate.value) == "duplicate reviewed label definition"
    with pytest.raises(
        ValueError, match="existing label definition differs"
    ) as conflict:
        label_definition_actions(
            (reviewed,),
            (
                {
                    "id": 1,
                    "name": "type/chore",
                    "color": "123456",
                    "description": "Chore",
                },
            ),
        )
    assert str(conflict.value) == "existing label definition differs: type/chore"


def test_b4_native_definition_rejects_ambiguous_or_wrong_field_type() -> None:
    action = Action(
        "6:native:#1",
        "6:native",
        "native",
        1,
        "POST",
        "issues/1/issue-field-values",
        {"fields": {"Priority": "Standard", "Severity": ""}},
        (),
        (),
    )
    definition = {
        "id": 5,
        "name": "Priority",
        "data_type": "single_select",
        "options": [{"name": "Standard"}],
    }
    assert native_field_payload(action, [definition]) == {
        "issue_field_values": [{"field_id": 5, "value": "Standard"}],
    }
    with pytest.raises(ValueError, match="definition is missing: Priority"):
        native_field_payload(action, [{**definition, "data_type": "text"}])
    with pytest.raises(ValueError, match="option is missing: Priority=Standard"):
        native_field_payload(
            action,
            [{**definition, "options": [{"name": "Standard"}, {"name": "Standard"}]}],
        )


def test_b4_candidate_dispatches_incident_creation_fields_and_membership() -> None:
    tables, cp1, metadata = field_contract()
    row = {
        **next(value for value in tables.assignments if value["title"] == "Draft A"),
        "title": "inc(github): synthetic outage",
        "backfill mode": "issue",
        "issue type": "Incident",
        "severity": "SEV2",
        "size": "M",
    }
    tables = replace(tables, assignments=(*tables.assignments, row))
    plan = operation_plan(tables, cp1)
    context = WriteContext(tables, cp1, cp1, plan, metadata, None, {})
    assert candidate_actions("12:create", context) == creation_actions(
        tables, cp1, plan, "12:create"
    )
    incident = Item("#4", row["title"], "open", issue_type="Incident", issue_id="104")
    created = replace(context, current=replace(cp1, items=(*cp1.items, incident)))
    assert candidate_actions("12:native", created) == created_native_actions(
        created.current, plan, "12:native"
    )
    assert candidate_actions("12:items", created) == created_membership_actions(
        created.current, plan, "12:items"
    )
    joined = replace(incident, item_id="item-4")
    raw = project_issue_item(4, 104, "item-4")
    added = replace(
        created,
        current=replace(cp1, items=(*cp1.items, joined)),
        metadata=replace(metadata, items=[*metadata.items, raw]),
    )
    assert candidate_actions("12:fields", added) == created_project_field_actions(
        tables, added.current, added.metadata, "12:fields"
    )


def test_b4_projected_resume_values_and_stage_markers() -> None:
    original = Item(
        "#1",
        "old",
        "open",
        issue_id="101",
        body="old body",
        native=(("Priority", ""),),
        labels=("type/chore",),
    )
    cases: tuple[tuple[str, object, dict[str, Any]], ...] = (
        ("issue_type", "Chore", {"issue_type": "Chore"}),
        (
            "native",
            (("Priority", "Standard"),),
            {"native": (("Priority", "Standard"),)},
        ),
        ("title", "new", {"title": "new"}),
        ("body", "new body", {"body": "new body"}),
        ("draft_body", "new body", {"body": "new body"}),
        (
            "issue_state",
            ("closed", "completed"),
            {"state": "closed", "state_reason": "completed"},
        ),
        ("project_fields", (("Status", "Done"),), {"project": (("Status", "Done"),)}),
        ("parent", "#3", {"parent": "#3"}),
        ("blocker", ("#2",), {"blockers": ("#2",)}),
        ("trial_add", ("#2",), {"blockers": ("#2",)}),
        ("trial_remove", ("#2",), {"blockers": ("#2",)}),
        ("label_delete", (), {"labels": ()}),
    )
    for kind, after, changes in cases:
        action = Action("a", "15", kind, 1, "PATCH", "", {"child": "#1"}, None, after)
        changed = replace(original, **changes)
        assert _progress_item(action, original, changed, ["verified"]) == changed
        assert _progress_item(action, original, changed, ["intent"]) == changed
        assert _progress_item(action, original, original, ["verified"]) == changed
        assert _progress_item(action, original, original, ["intent"]) == original
    unknown = Action("unknown", "15", "other", 1, "PATCH", "", None, None, "new")
    assert _progress_item(unknown, original, original, ["verified"]) == original

    empty = [
        {"version": 1, "run_id": "digest"},
        asdict(Record("stage:3:trial", "complete", {"stage": "3:trial"})),
    ]
    assert validate_journal(empty, "digest", ())[-1].phase == "complete"
    with pytest.raises(ValueError, match="completion"):
        validate_journal([*empty, empty[1]], "digest", ())
    with pytest.raises(ValueError, match="order"):
        validate_journal(
            [
                empty[0],
                asdict(Record("stage:4:labels", "complete", {"stage": "4:labels"})),
                empty[1],
            ],
            "digest",
            (),
        )


def test_b4_candidate_dispatch_uses_completed_stage_values() -> None:
    tables, cp1, metadata = field_contract()
    plan = operation_plan(tables, cp1)
    draft_items = [
        {**item, "content": {**item["content"], "node_id": "node-draft-b"}}
        if item["id"] == "item-b"
        else item
        for item in metadata.items
    ]
    metadata = replace(metadata, items=draft_items)
    context = WriteContext(
        tables,
        cp1,
        cp1,
        plan,
        metadata,
        None,
        {},
        ({"name": "type/chore", "color": "abcdef", "description": "Chore"},),
        (),
    )
    assert candidate_actions("4:labels", context)[0].kind == "label_create"
    assert candidate_actions("6:new-fields", context) == ()
    assert candidate_actions("6:body", context)[0].kind == "draft_body"
    assert candidate_actions("6:native", context)[0].kind == "issue_type"
    assert candidate_actions("6T", context)[0].kind == "title"
    assert candidate_actions("9:create", context)[0].kind == "issue_create"
    assert candidate_actions("12:create", context) == ()
    assert candidate_actions("unknown", context) == ()
    trial_cp1 = replace(
        cp1,
        items=(
            *cp1.items,
            Item("#149", "dependent", "open", issue_id="149"),
            Item("#96", "blocker", "closed", issue_id="96"),
        ),
    )
    assert (
        candidate_actions("3:trial", replace(context, cp1=trial_cp1))[0].kind
        == "trial_add"
    )

    parent = Item(
        "#3",
        "epic: migration",
        "open",
        issue_type="Epic",
        issue_id="103",
        item_id="item-3",
    )
    parent_raw = project_issue_item(3, 103, "item-3")
    with_parent = replace(
        context,
        current=replace(cp1, items=(*cp1.items, parent)),
        metadata=replace(metadata, items=[*metadata.items, parent_raw]),
    )
    assert candidate_actions("9:native", with_parent)[0].kind == "native"
    assert (
        candidate_actions(
            "9:items",
            replace(
                with_parent,
                current=replace(cp1, items=(*cp1.items, replace(parent, item_id=""))),
            ),
        )[0].kind
        == "project_item"
    )
    assert candidate_actions("9:fields", with_parent)[0].kind == "project_fields"
    assert candidate_actions("10", with_parent)[0].kind == "parent"
    assert candidate_actions("11:links", with_parent)[0].kind == "blocker"
    assert candidate_actions("12:native", with_parent) == ()
    assert candidate_actions("12:items", with_parent) == ()
    assert candidate_actions("12:fields", with_parent) == ()
    closed = replace(tables, parents=({**tables.parents[0], "state": "closed"},))
    assert (
        candidate_actions("9:close", replace(with_parent, tables=closed))[0].kind
        == "issue_state"
    )
    revised = replace(
        tables,
        assignments=tuple(
            {**row, "body revision": "required"} if row["number"] == "1" else row
            for row in tables.assignments
        ),
    )
    assert (
        candidate_actions(
            "11:bodies",
            replace(with_parent, tables=revised, reviewed_bodies={"#1": "reviewed"}),
        )[0].kind
        == "body"
    )
    labelled = replace(
        with_parent.current,
        items=tuple(
            replace(item, labels=("type/chore",)) if item.key == "#1" else item
            for item in with_parent.current.items
        ),
    )
    labels = replace(
        tables,
        assignments=tuple(
            {**row, "old type labels": "type/chore"} if row["number"] == "1" else row
            for row in tables.assignments
        ),
    )
    assert (
        candidate_actions("15", replace(with_parent, current=labelled, tables=labels))[
            0
        ].kind
        == "label_delete"
    )
