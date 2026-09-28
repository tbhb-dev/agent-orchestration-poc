"""Pure journal and resume decisions for the staged backfill."""

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.work_model_backfill import (
    Item,
    Page,
    Snapshot,
    operation_plan,
    parse_tables,
    validate_cp1,
)
from agent_orchestration_poc.core.work_model_backfill_executor import (
    Action,
    Record,
    closure_actions,
    comment_observation,
    draft_actions,
    draft_observation,
    journal_state,
    observation_value,
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
    rows = FIXTURES / "plan"
    tables = parse_tables(
        *(
            (rows / f"{name}.tsv").read_text()
            for name in ("assignments", "parents", "edges")
        )
    )
    cp1 = fixture_snapshot("executor-cp1")
    action = draft_actions(tables, cp1, operation_plan(tables, cp1))[0]
    assert action.payload is not None
    created = Item(
        "title:Draft A",
        "Draft A",
        "draft",
        body=action.payload["body"],
        item_id="13",
        draft_id="draft-a",
    )
    pages = tuple(
        replace(page, count=page.count + 1, total_count=page.total_count + 1)
        if page.collection in {"project", "drafts"}
        else page
        for page in cp1.pages
    )
    current = replace(cp1, items=(*cp1.items, created), pages=pages)
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
