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
    Step,
    operation_plan,
    parse_tables,
    validate_cp1,
)
from agent_orchestration_poc.core.work_model_backfill_executor import (
    Action,
    Record,
    closure_actions,
    comment_observation,
    journal_state,
    observation_value,
    require_stage_ready,
    require_trial_pr,
    trial_actions,
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


def test_closure_and_trial_follow_plan() -> None:
    actions, _ = contract()
    expected = json.loads((FIXTURES / "runner/executor-actions.json").read_text())
    assert (
        json.loads(json.dumps([asdict(action) for action in actions]))
        == expected["closure"]
    )


def test_trial_uses_saved_numeric_id_and_refuses_existing_link() -> None:
    cp1 = Snapshot(
        1,
        (
            Item("#96", "closed", "closed", issue_id="960"),
            Item("#149", "dependent", "open", blockers=("#1",), issue_id="1490"),
        ),
        (),
        "sha",
    )
    plan = (Step("3", ("149 <- 96",), (), (), "", ()),)
    actions = trial_actions(cp1, plan)
    expected = json.loads((FIXTURES / "runner/executor-actions.json").read_text())
    assert (
        json.loads(json.dumps([asdict(action) for action in actions]))
        == expected["trial"]
    )
    with pytest.raises(ValueError, match="already exists"):
        trial_actions(
            replace(
                cp1, items=(cp1.items[0], replace(cp1.items[1], blockers=("#1", "#96")))
            ),
            plan,
        )


def test_trial_refuses_changed_plan_or_missing_blocker_id() -> None:
    cp1 = Snapshot(
        1,
        (
            Item("#96", "closed", "closed", issue_id="96"),
            Item("#149", "open", "open", issue_id="149"),
        ),
        (),
        "sha",
    )
    stage = Step("3", ("149 <- 96",), (), (), "", ())
    with pytest.raises(ValueError, match="unreviewed"):
        trial_actions(cp1, (replace(stage, targets=("149 <- 97",)),))
    with pytest.raises(ValueError, match="no ID"):
        trial_actions(
            replace(cp1, items=(replace(cp1.items[0], issue_id=""), cp1.items[1])),
            (stage,),
        )


@pytest.mark.parametrize(
    "pr",
    [
        {"state": "open", "merged": False},
        {"state": "closed", "merged": True},
        {"state": "closed"},
    ],
)
def test_trial_requires_closed_unmerged_pr(pr: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="closed and unmerged"):
        require_trial_pr(pr)
    require_trial_pr({"state": "closed", "merged": False})


@pytest.mark.parametrize(
    ("kind", "phases", "observed", "decision"),
    [
        ("issue_state", (), "before", "send"),
        ("issue_state", ("intent",), "after", "verify"),
        ("issue_state", ("intent", "response", "verified"), "after", "skip"),
        ("issue_state", ("intent", "response", "verified"), "before", "halt"),
        ("trial_add", ("intent",), "after", "halt"),
        ("trial_add", ("intent", "response"), "after", "verify"),
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


def test_trial_cleanup_needs_verified_ownership() -> None:
    action = Action(
        "3:remove:149:96", "3", "trial_remove", 149, "DELETE", "", None, ("#96",), ()
    )
    assert journal_state(action, (), ("#96",)) == "halt"
    assert (
        journal_state(action, (Record("3:add:149:96", "verified", {}),), ("#96",))
        == "send"
    )


def test_trial_add_is_superseded_only_by_recorded_cleanup() -> None:
    add = Action("3:add:149:96", "3", "trial_add", 149, "POST", "", {}, (), ("#96",))
    verified = (Record(add.id, "intent", {}), Record(add.id, "verified", {}))
    assert journal_state(add, verified, ()) == "halt"
    for phase in ("intent", "verified"):
        records = (*verified, Record("3:remove:149:96", "intent", {}))
        if phase == "verified":
            records = (*records, Record("3:remove:149:96", "verified", {}))
        assert journal_state(add, records, ()) == "skip"


def test_trial_page_delta_requires_complete_authorized_receipts() -> None:
    cp1 = fixture_snapshot("trial-cp1")
    dependent, blocker = cp1.items
    pages = tuple(
        replace(page, count=page.count + 1, total_count=page.total_count + 1)
        if page.collection == "blockers:#149"
        else page
        for page in cp1.pages
    )
    current = replace(
        cp1, items=(replace(dependent, blockers=("#96",)), blocker), pages=pages
    )
    add = Action("3:add:149:96", "3", "trial_add", 149, "POST", "", {}, (), ("#96",))
    records = (
        Record(add.id, "intent", {}),
        Record(add.id, "response", {}),
        Record(add.id, "verified", {}),
    )
    validate_progress(cp1, current, (add,), records)
    with pytest.raises(ValueError, match="collection"):
        validate_progress(cp1, replace(current, pages=cp1.pages), (add,), records)


def test_trial_readiness_requires_every_closure_verified() -> None:
    actions, _ = contract()
    with pytest.raises(ValueError, match="every closure"):
        require_stage_ready("3", actions, ())
    partial = (Record(actions[0].id, "verified", {}),)
    with pytest.raises(ValueError, match="every closure"):
        require_stage_ready("3", actions, partial)
    complete = tuple(Record(action.id, "verified", {}) for action in actions)
    require_stage_ready("3", actions, complete)


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
