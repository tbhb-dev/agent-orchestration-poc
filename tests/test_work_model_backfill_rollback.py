"""Plain-value rollback plan and journal tests."""

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.work_model_backfill import Item, Page, Snapshot
from agent_orchestration_poc.core.work_model_backfill_executor import (
    Action,
    ProjectMetadata,
    Record,
)
from agent_orchestration_poc.core.work_model_backfill_rollback import (
    inverse_action,
    rollback_plan,
    validate_rollback_journal,
)

METADATA = ProjectMetadata({"node_id": "project"}, [], [])


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
    ("action", "detail", "method", "path", "after"),
    [
        (
            Action(
                "comment",
                "0",
                "comment",
                1,
                "POST",
                "issues/1/comments",
                {"body": "saved"},
                0,
                1,
            ),
            {"comment_id": 42},
            "DELETE",
            "issues/1/comments/42",
            0,
        ),
        (
            Action(
                "state",
                "0",
                "issue_state",
                1,
                "PATCH",
                "issues/1",
                {"state": "closed"},
                ("open", ""),
                ("closed", "not_planned"),
            ),
            {},
            "PATCH",
            "issues/1",
            ("open", ""),
        ),
        (
            Action(
                "type",
                "6:native",
                "issue_type",
                1,
                "PATCH",
                "issues/1",
                {"type": "Chore"},
                "",
                "Chore",
            ),
            {},
            "PATCH",
            "issues/1",
            "",
        ),
        (
            Action(
                "native",
                "6:native",
                "native",
                1,
                "POST",
                "issues/1/issue-field-values",
                {"fields": {"Work type": "Planned"}},
                (("Work type", ""),),
                (("Work type", "Planned"),),
            ),
            {},
            "PUT",
            "issues/1/issue-field-values",
            (("Work type", ""),),
        ),
        (
            Action(
                "item",
                "6",
                "project_item",
                1,
                "POST",
                "orgs/tbhb-dev/projectsV2/1/items",
                {"id": 1},
                (0, "1"),
                (1, "1"),
            ),
            {"item_id": "13"},
            "DELETE",
            "orgs/tbhb-dev/projectsV2/1/items/13",
            (0, "1"),
        ),
        (
            Action(
                "label",
                "15",
                "label_delete",
                1,
                "DELETE",
                "issues/1/labels/type%2Fold",
                None,
                ("type/old",),
                (),
            ),
            {},
            "POST",
            "issues/1/labels",
            ("type/old",),
        ),
        (
            Action(
                "parent",
                "10",
                "parent",
                1,
                "POST",
                "issues/1/sub_issues",
                {"sub_issue_id": 2, "child": "#2"},
                "",
                "#1",
            ),
            {},
            "DELETE",
            "issues/1/sub_issues/2",
            "",
        ),
        (
            Action(
                "created",
                "9:create",
                "issue_create",
                0,
                "POST",
                "issues",
                {"title": "P", "body": "B", "type": "Epic"},
                0,
                1,
            ),
            {"created_item": {"key": "#29"}},
            "PATCH",
            "issues/29",
            ("closed", "not_planned"),
        ),
    ],
)
def test_inverse_action_table(
    action: Action, detail: dict[str, Any], method: str, path: str, after: object
) -> None:
    inverse = inverse_action(action, detail, METADATA)
    assert inverse.id == f"rollback:{action.id}"
    assert (inverse.method, inverse.path, inverse.after) == (method, path, after)


def test_relation_and_project_inverse_payloads() -> None:
    """Keep only saved identities and restore exact prior field values."""
    actions = (
        Action(
            "label",
            "4:labels",
            "label_create",
            0,
            "POST",
            "labels",
            {"name": "phase/2", "color": "abc", "description": "d"},
            0,
            ("phase/2", "abc", "d"),
        ),
        Action(
            "blocker",
            "11:links",
            "blocker",
            1,
            "POST",
            "issues/1/dependencies/blocked_by",
            {"issue_id": 2},
            (),
            ("#2",),
        ),
        Action(
            "draft",
            "6",
            "draft",
            0,
            "POST",
            "orgs/tbhb-dev/projectsV2/1/drafts",
            {"title": "D", "body": "B"},
            (0, ""),
            (1, "B"),
        ),
        Action(
            "draft-body",
            "6:body",
            "draft_body",
            0,
            "POST",
            "graphql",
            {"query": "old", "key": "title:D", "draft_id": "D-node"},
            "before",
            "after",
        ),
    )
    details: tuple[dict[str, Any], ...] = ({}, {}, {"item_id": "34"}, {})
    inverses = tuple(
        inverse_action(action, detail, METADATA)
        for action, detail in zip(actions, details, strict=True)
    )
    assert (inverses[0].method, inverses[0].path, inverses[0].after) == (
        "DELETE",
        "labels/phase%2F2",
        0,
    )
    assert (inverses[1].method, inverses[1].path, inverses[1].payload) == (
        "DELETE",
        "issues/1/dependencies/blocked_by/2",
        None,
    )
    assert (inverses[2].method, inverses[2].path) == (
        "DELETE",
        "orgs/tbhb-dev/projectsV2/1/items/34",
    )
    assert inverses[3].payload is not None
    assert 'body:"before"' in inverses[3].payload["query"]
    with pytest.raises(ValueError, match="identity"):
        inverse_action(actions[2], {}, METADATA)


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
    plan = rollback_plan(cp1, cp1, (first, second), records, METADATA)
    assert tuple(action.id for action in plan) == ("rollback:second", "rollback:first")
    with pytest.raises(ValueError, match="no verified"):
        rollback_plan(cp1, cp1, (first, second), records[:-1], METADATA)
    with pytest.raises(ValueError, match="branch"):
        rollback_plan(
            cp1, replace(cp1, branch_sha="changed"), (first, second), records, METADATA
        )


def test_rollback_journal_rejects_plan_and_order_changes() -> None:
    action = inverse_action(
        Action(
            "title",
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
    with pytest.raises(ValueError, match="duplicate"):
        rollback_plan(cp1, cp1, (add, add), records, METADATA)
    with pytest.raises(ValueError, match="unknown"):
        rollback_plan(cp1, cp1, (add,), records, METADATA)


@given(st.text(max_size=40))
def test_reversal_preserves_saved_title(title: str) -> None:
    action = Action(
        "title", "6T", "title", 1, "PATCH", "issues/1", {"title": "new"}, title, "new"
    )
    inverse = inverse_action(action, {}, METADATA)
    assert inverse.before == "new"
    assert inverse.after == title
    assert inverse.payload == {"title": title}
