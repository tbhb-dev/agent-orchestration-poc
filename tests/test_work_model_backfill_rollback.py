"""Plain-value rollback plan and journal tests."""

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.work_model_backfill import Item, Page, Snapshot
from agent_orchestration_poc.core.work_model_backfill_executor import (
    Action,
    ProjectMetadata,
    Record,
    _tuplify,
    recorded_actions,
    validate_journal,
)
from agent_orchestration_poc.core.work_model_backfill_rollback import (
    inverse_action,
    rollback_plan,
    validate_rollback_journal,
    validate_rollback_progress,
)

METADATA = ProjectMetadata({"node_id": "project"}, [], [])


def title_inverse() -> Action:
    """Build the saved title inverse shared by journal cases."""
    forward = Action(
        "title",
        "6T",
        "title",
        1,
        "PATCH",
        "issues/1",
        {"title": "new"},
        "old",
        "new",
    )
    return inverse_action(forward, {}, METADATA)


def fixture_snapshot() -> Snapshot:
    """Read the complete runner checkpoint as immutable plain values."""
    path = (
        Path(__file__).parent / "fixtures/work_model_backfill/runner/executor-cp1.json"
    )
    data = json.loads(path.read_text())
    items = []
    for value in data["items"]:
        for name in ("native", "project", "source_project"):
            value[name] = tuple(tuple(pair) for pair in value[name])
        for name in ("blockers", "labels"):
            value[name] = tuple(value[name])
        items.append(Item(**value))
    return Snapshot(
        data["version"],
        tuple(items),
        tuple(Page(**page) for page in data["pages"]),
        data["branch_sha"],
        data["run_state"],
    )


@pytest.mark.parametrize(
    "case",
    json.loads(
        (
            Path(__file__).parent
            / "fixtures/work_model_backfill/runner/rollback-actions.json"
        ).read_text()
    ),
)
def test_inverse_action_table(case: dict[str, Any]) -> None:
    value = case["action"]
    action = Action(
        value["id"],
        value["step"],
        value["kind"],
        value["number"],
        value["method"],
        value["path"],
        value["payload"],
        _tuplify(value["before"]),
        _tuplify(value["after"]),
    )
    inverse = inverse_action(action, case["detail"], METADATA)
    assert inverse.id == f"rollback:{action.id}"
    assert (inverse.method, inverse.path, inverse.after) == (
        case["method"],
        case["path"],
        _tuplify(case["after"]),
    )
    assert inverse.payload == case["payload"]


def test_project_fields_restore_reviewed_option_and_clear_blank() -> None:
    metadata = ProjectMetadata(
        {"node_id": "project"},
        [
            {
                "name": "Status",
                "node_id": "field",
                "data_type": "single_select",
                "options": [{"id": "old-id", "name": {"raw": "Ready"}}],
            },
            {"name": "Worker", "node_id": "worker", "data_type": "text"},
        ],
        [],
    )
    action = Action(
        "fields",
        "6",
        "project_fields",
        1,
        "POST",
        "graphql",
        {
            "query": "forward",
            "key": "#1",
            "item_id": "13",
            "node_id": "item",
            "mutation_count": 2,
        },
        (("Status", "Ready"), ("Worker", "")),
        (("Status", "Done"), ("Worker", "new")),
    )
    inverse = inverse_action(action, {}, metadata)
    assert inverse.after == action.before
    assert inverse.payload is not None
    assert inverse.payload["mutation_count"] == 2
    assert 'singleSelectOptionId:"old-id"' in inverse.payload["query"]
    assert "clearProjectV2ItemFieldValue" in inverse.payload["query"]
    with pytest.raises(ValueError, match="option"):
        inverse_action(
            action,
            {},
            replace(
                metadata,
                fields=[{**metadata.fields[0], "options": []}, metadata.fields[1]],
            ),
        )


def test_plan_uses_only_verified_actions_in_reverse_order() -> None:
    cp1 = fixture_snapshot()
    first = Action(
        "first", "6T", "title", 1, "PATCH", "issues/1", {"title": "new"}, "old", "new"
    )
    second = Action(
        "second",
        "11:bodies",
        "body",
        1,
        "PATCH",
        "issues/1",
        {"body": "new"},
        "old",
        "new",
    )
    records = tuple(
        Record(
            action.id, phase, {"action": asdict(action)} if phase == "intent" else {}
        )
        for action in (first, second)
        for phase in ("intent", "response", "verified")
    )
    records = (
        *records[:3],
        Record("stage:6T", "complete", {"stage": "6T"}),
        *records[3:],
    )
    plan = rollback_plan(cp1, cp1, (first, second), records, METADATA)
    assert tuple(action.id for action in plan) == ("rollback:second", "rollback:first")
    with pytest.raises(ValueError, match="no verified") as error:
        rollback_plan(cp1, cp1, (first, second), records[:-1], METADATA)
    assert str(error.value) == "forward write has no verified read-back"
    with pytest.raises(ValueError, match="branch") as error:
        rollback_plan(
            cp1, replace(cp1, branch_sha="changed"), (first, second), records, METADATA
        )
    assert str(error.value) == "rollback checkpoint or retained branch changed"
    for changed in (replace(cp1, version=cp1.version + 1), replace(cp1, pages=())):
        with pytest.raises(ValueError, match="checkpoint"):
            rollback_plan(cp1, changed, (first, second), records, METADATA)


def test_forward_retry_reconstructs_one_rollback_action() -> None:
    cp1 = fixture_snapshot()
    action = Action(
        "retry", "6T", "title", 1, "PATCH", "issues/1", {"title": "new"}, "old", "new"
    )
    rows: list[dict[str, Any]] = [{"version": 1, "run_id": "cp1"}]
    rows.extend(
        asdict(
            Record(
                action.id,
                phase,
                {"action": asdict(action), "payload": action.payload}
                if phase == "intent"
                else {},
            )
        )
        for phase in ("intent", "intent", "response", "verified")
    )
    saved = recorded_actions(json.loads(json.dumps(rows)))
    records = validate_journal(rows, "cp1", saved)
    assert tuple(
        item.id for item in rollback_plan(cp1, cp1, saved, records, METADATA)
    ) == ("rollback:retry",)
    changed = replace(action, payload={"title": "different"})
    rows[2] = asdict(
        Record(
            action.id, "intent", {"action": asdict(changed), "payload": action.payload}
        )
    )
    with pytest.raises(ValueError, match="changed"):
        recorded_actions(rows)


def test_rollback_journal_rejects_plan_and_order_changes() -> None:
    action = title_inverse()
    rows = [
        {"version": 1, "run_id": "cp1"},
        asdict(Record(action.id, "intent", {"action": asdict(action)})),
        asdict(Record(action.id, "verified", {"observed": "old"})),
    ]
    rows = json.loads(json.dumps(rows))
    assert len(validate_rollback_journal(rows, "cp1", (action,))) == 2
    with pytest.raises(ValueError, match="changed"):
        validate_rollback_journal(rows, "cp1", (replace(action, path="issues/2"),))
    with pytest.raises(ValueError, match="transition"):
        validate_rollback_journal([*rows, rows[-1]], "cp1", (action,))


def test_rollback_retry_journal_reloads_after_second_intent() -> None:
    action = title_inverse()
    rows: list[dict[str, Any]] = [{"version": 1, "run_id": "cp1"}]
    rows.extend(
        asdict(
            Record(
                action.id,
                phase,
                {"action": asdict(action)} if phase == "intent" else {},
            )
        )
        for phase in ("intent", "intent", "response", "verified")
    )
    assert (
        len(validate_rollback_journal(json.loads(json.dumps(rows)), "cp1", (action,)))
        == 4
    )
    after_response = [rows[0], rows[1], rows[3], rows[2], rows[3], rows[4]]
    assert len(validate_rollback_journal(after_response, "cp1", (action,))) == 5
    changed_retry = [*after_response]
    changed_retry[3] = {
        **rows[2],
        "detail": {"action": {**asdict(action), "path": "issues/9"}},
    }
    with pytest.raises(ValueError, match="rollback action changed"):
        validate_rollback_journal(changed_retry, "cp1", (action,))


def test_rollback_progress_rejects_header_and_partial_resume_drift() -> None:
    cp1 = fixture_snapshot()
    item = cp1.items[0]
    first = Action(
        "title",
        "6T",
        "title",
        int(item.key[1:]),
        "PATCH",
        f"issues/{item.key[1:]}",
        {"title": "new"},
        item.title,
        "new",
    )
    second = Action(
        "body",
        "11:bodies",
        "body",
        int(item.key[1:]),
        "PATCH",
        f"issues/{item.key[1:]}",
        {"body": "new body"},
        item.body,
        "new body",
    )
    forward = (first, second)
    records = tuple(Record(action.id, "verified", {}) for action in forward)
    inverse = tuple(
        inverse_action(action, {}, METADATA) for action in reversed(forward)
    )
    current = replace(
        cp1, items=(replace(item, title="new", body="new body"), *cp1.items[1:])
    )
    validate_rollback_progress(cp1, current, (forward, records), (inverse, ()))
    drift = replace(
        current,
        items=(replace(current.items[0], labels=("unrelated",)), *current.items[1:]),
    )
    with pytest.raises(ValueError, match="drifted"):
        validate_rollback_progress(cp1, drift, (forward, records), (inverse, ()))
    undone = (Record(inverse[0].id, "verified", {}),)
    partial = replace(
        current, items=(replace(current.items[0], body=item.body), *current.items[1:])
    )
    validate_rollback_progress(cp1, partial, (forward, records), (inverse, undone))
    with pytest.raises(ValueError, match="drifted"):
        validate_rollback_progress(cp1, current, (forward, records), (inverse, undone))
    pending = (*undone, Record(inverse[1].id, "intent", {}))
    validate_rollback_progress(cp1, partial, (forward, records), (inverse, pending))
    validate_rollback_progress(
        cp1,
        replace(
            partial,
            items=(replace(partial.items[0], title=item.title), *partial.items[1:]),
        ),
        (forward, records),
        (inverse, pending),
    )


def test_rollback_progress_retains_created_issue_as_closed_record() -> None:
    cp1 = fixture_snapshot()
    created = Item("#99", "new issue", "open", issue_id="99", body="body")
    action = Action(
        "9:create:99",
        "9:create",
        "issue_create",
        0,
        "POST",
        "issues",
        {"title": "new issue", "body": "body", "type": ""},
        0,
        1,
    )
    record = Record(action.id, "verified", {"created_item": asdict(created)})
    inverse = inverse_action(action, record.detail, METADATA)
    closed = replace(created, state="closed", state_reason="not_planned")
    pages = tuple(
        replace(page, count=3, total_count=3)
        if page.collection in {"issues", "native", "parents", "blockers"}
        else page
        for page in cp1.pages
    ) + tuple(
        Page(f"{kind}:#99", 1, 0, 1, 0) for kind in ("native", "blockers", "sub_issues")
    )
    current = replace(cp1, items=(*cp1.items, closed), pages=pages)
    validate_rollback_progress(
        cp1,
        current,
        ((action,), (record,)),
        ((inverse,), (Record(inverse.id, "verified", {}),)),
    )
    with pytest.raises(ValueError, match="drifted"):
        validate_rollback_progress(
            cp1,
            replace(current, items=(*cp1.items, created)),
            ((action,), (record,)),
            ((inverse,), (Record(inverse.id, "verified", {}),)),
        )


def test_rollback_journal_requires_ordered_saved_intents() -> None:
    first = inverse_action(
        Action(
            "first",
            "6T",
            "title",
            1,
            "PATCH",
            "issues/1",
            {"title": "new"},
            "old",
            "new",
        ),
        {},
        METADATA,
    )
    second = replace(first, id="rollback:second", number=2, path="issues/2")
    header = {"version": 1, "run_id": "cp1"}
    intent = asdict(Record(first.id, "intent", {"action": asdict(first)}))
    verified = asdict(Record(first.id, "verified", {}))
    next_intent = asdict(Record(second.id, "intent", {"action": asdict(second)}))

    def encode(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return cast("list[dict[str, Any]]", json.loads(json.dumps(rows)))

    assert (
        len(
            validate_rollback_journal(
                encode([header, intent, verified, next_intent]), "cp1", (first, second)
            )
        )
        == 3
    )
    for rows, message in (
        ([{**header, "run_id": "other"}], "rollback journal header differs from CP1"),
        ([header, verified], "rollback journal transition is invalid"),
        ([header, next_intent], "rollback journal order differs from plan"),
        ([header, intent, next_intent], "rollback journal has an unfinished action"),
        (
            [header, intent, verified, next_intent, intent],
            "rollback journal order differs from plan",
        ),
        (
            [
                header,
                {**intent, "detail": {"action": {**asdict(first), "path": "issues/9"}}},
            ],
            "rollback action changed",
        ),
    ):
        with pytest.raises(ValueError, match=message) as error:
            validate_rollback_journal(encode(rows), "cp1", (first, second))
        assert str(error.value) == message


def test_missing_created_identity_refuses_inverse() -> None:
    comment = Action(
        "comment", "0", "comment", 1, "POST", "issues/1/comments", {"body": "B"}, 0, 1
    )
    item = Action(
        "item",
        "6",
        "project_item",
        1,
        "POST",
        "orgs/tbhb-dev/projectsV2/1/items",
        {"id": 1},
        (0, "1"),
        (1, "1"),
    )
    created = Action(
        "created", "9:create", "issue_create", 0, "POST", "issues", {"title": "P"}, 0, 1
    )
    cases: tuple[tuple[Action, dict[str, Any], str], ...] = (
        (comment, {}, "comment identity is missing"),
        (item, {}, "created Project item identity is missing"),
        (created, {}, "created issue identity is missing"),
        (
            created,
            {"created_item": {"key": "title:P"}},
            "created issue identity is missing",
        ),
    )
    for action, detail, message in cases:
        with pytest.raises(ValueError, match="identity") as error:
            inverse_action(action, detail, METADATA)
        assert str(error.value) == message


def test_completed_trial_has_no_net_rollback() -> None:
    cp1 = fixture_snapshot()
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
    remove = replace(
        add,
        id="3:remove:149:96",
        kind="trial_remove",
        method="DELETE",
        path="issues/149/dependencies/blocked_by/96",
        payload=None,
        before=add.after,
        after=add.before,
    )
    records = tuple(Record(action.id, "verified", {}) for action in (add, remove))
    assert rollback_plan(cp1, cp1, (add, remove), records, METADATA) == ()
    with pytest.raises(ValueError, match="duplicate") as error:
        rollback_plan(cp1, cp1, (add, add), records, METADATA)
    assert str(error.value) == "duplicate forward action"
    with pytest.raises(ValueError, match="unknown") as error:
        rollback_plan(cp1, cp1, (add,), records, METADATA)
    assert str(error.value) == "unknown forward operation"


def test_plan_uses_verified_comment_identity_once() -> None:
    cp1 = fixture_snapshot()
    comment = Action(
        "0:comment:1",
        "0",
        "comment",
        1,
        "POST",
        "issues/1/comments",
        {"body": "saved"},
        0,
        1,
    )
    records = (
        Record(comment.id, "intent", {}),
        Record(comment.id, "verified", {"comment_id": 42}),
    )
    assert (
        rollback_plan(cp1, cp1, (comment,), records, METADATA)[0].path
        == "issues/comments/42"
    )
    with pytest.raises(ValueError, match="duplicate forward verification") as error:
        rollback_plan(cp1, cp1, (comment,), (*records, records[-1]), METADATA)
    assert str(error.value) == "duplicate forward verification"


@given(st.text(max_size=40))
def test_reversal_preserves_saved_title(title: str) -> None:
    action = Action(
        "title", "6T", "title", 1, "PATCH", "issues/1", {"title": "new"}, title, "new"
    )
    inverse = inverse_action(action, {}, METADATA)
    assert inverse.before == "new"
    assert inverse.after == title
    assert inverse.payload == {"title": title}
