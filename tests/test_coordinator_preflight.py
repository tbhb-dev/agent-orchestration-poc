"""Fixture checks for the coordinator's pure decisions."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from agent_orchestration_poc.core.coordinator_preflight import (
    CheckOutcome,
    CheckState,
    IssueState,
    MergedPullRequest,
    audit_closures,
    check_outcome,
    linked_merged_prs,
    needs_closure_review,
    normalize_checks,
    outdated_workflows,
)

FIXTURES = Path(__file__).parent / "fixtures" / "coordinator_preflight"


def _load(name: str) -> dict[str, Any] | list[dict[str, Any]]:
    return cast(
        "dict[str, Any] | list[dict[str, Any]]",
        json.loads((FIXTURES / name).read_text()),
    )


@pytest.mark.parametrize("case", ["outdated", "current"])
def test_workflow_revision(case: str) -> None:
    fixture = cast("dict[str, dict[str, Any]]", _load("workflows.json"))[case]
    assert (
        list(outdated_workflows(fixture["base"], fixture["main"], fixture["head"]))
        == fixture["expected"]
    )


def test_workflow_revision_with_missing_head_path() -> None:
    assert outdated_workflows({"check.yml": "old"}, {"check.yml": "new"}, {}) == (
        "check.yml",
    )


def test_workflow_revision_with_updated_head_path() -> None:
    assert (
        outdated_workflows(
            {"check.yml": "old"}, {"check.yml": "new"}, {"check.yml": "new"}
        )
        == ()
    )


@pytest.mark.parametrize("fixture", _load("checks.json"), ids=lambda item: item["case"])
def test_check_outcome(fixture: dict[str, Any]) -> None:
    checks = tuple(CheckState(**check) for check in fixture["checks"])
    assert check_outcome("abc", fixture["head"], "check", checks) == CheckOutcome(
        fixture["expected"]
    )


@pytest.mark.parametrize(
    "fixture", _load("closures.json"), ids=lambda item: item["case"]
)
def test_closure_audit(fixture: dict[str, Any]) -> None:
    pull_requests = tuple(
        MergedPullRequest(pr["number"], f"Refs: #{fixture['number']}", ())
        for pr in fixture["linked_prs"]
        if pr["merged"]
    )
    issue = IssueState(
        number=fixture["number"],
        state=fixture["state"],
        body=fixture["body"],
        labels=tuple(fixture["labels"]),
        merged_prs=linked_merged_prs(fixture["number"], pull_requests),
    )
    assert needs_closure_review(issue) is fixture["expected"]


def test_github_closing_reference_links_merged_pr() -> None:
    pr = MergedPullRequest(12, "No trailer", (5,))
    assert linked_merged_prs(5, (pr,)) == (12,)


def test_duplicate_check_with_queued_run_waits() -> None:
    checks = (
        CheckState("check", "COMPLETED", "SUCCESS", "2026-09-26T20:00:00Z"),
        CheckState("check", "QUEUED", None, ""),
    )
    assert check_outcome("abc", "abc", "check", checks) == CheckOutcome.WAIT


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("SUCCESS", CheckOutcome.SUCCESS),
        ("FAILURE", CheckOutcome.FAIL),
        ("ERROR", CheckOutcome.FAIL),
    ],
)
def test_completed_status_without_conclusion(
    status: str, expected: CheckOutcome
) -> None:
    checks = (CheckState("check", status, None, ""),)
    assert check_outcome("abc", "abc", "check", checks) == expected


def test_duplicate_check_with_tied_start_waits() -> None:
    checks = (
        CheckState("check", "COMPLETED", "SUCCESS", "1"),
        CheckState("check", "IN_PROGRESS", None, "1"),
    )
    assert check_outcome("abc", "abc", "check", checks) == CheckOutcome.WAIT


def test_duplicate_completed_checks_choose_later_start() -> None:
    checks = (
        CheckState("check", "COMPLETED", "FAILURE", "1"),
        CheckState("check", "COMPLETED", "SUCCESS", "2"),
    )
    assert check_outcome("abc", "abc", "check", checks) == CheckOutcome.SUCCESS


def test_duplicate_completed_checks_with_tied_start_wait() -> None:
    checks = (
        CheckState("check", "COMPLETED", "SUCCESS", "1"),
        CheckState("check", "COMPLETED", "FAILURE", "1"),
    )
    assert check_outcome("abc", "abc", "check", checks) == CheckOutcome.WAIT


def test_check_normalization_preserves_missing_start() -> None:
    raw: tuple[dict[str, str | None], ...] = (
        {
            "name": "check",
            "status": "COMPLETED",
            "conclusion": "SUCCESS",
            "startedAt": "1",
        },
        {"name": "check", "status": "QUEUED", "conclusion": None},
    )
    assert normalize_checks(raw) == (
        CheckState("check", "COMPLETED", "SUCCESS", "1"),
        CheckState("check", "QUEUED", None, ""),
    )


def test_check_normalization_uses_status_context_and_creation_time() -> None:
    raw: tuple[dict[str, str | None], ...] = (
        {"context": "check", "state": "SUCCESS", "createdAt": "1"},
    )
    assert normalize_checks(raw) == (CheckState("check", "SUCCESS", "SUCCESS", "1"),)


def test_decision_closure_requires_decision_label() -> None:
    issue = IssueState(1, "closed", "Closed by the decision record", ("type/bug",), ())
    assert needs_closure_review(issue)


def test_decision_closure_accepts_case_insensitive_note() -> None:
    issue = IssueState(
        1, "closed", "closed by a decision record", ("type/decision",), ()
    )
    assert not needs_closure_review(issue)


def test_non_code_closure_requires_explanation() -> None:
    issue = IssueState(1, "closed", "Non-code closure:  ", ("type/bug",), ())
    assert needs_closure_review(issue)


def test_closure_audit_selects_and_counts_work_items() -> None:
    issues = (
        IssueState(1, "closed", "", ("type/bug",), ()),
        IssueState(2, "closed", "", ("area/tooling",), ()),
        IssueState(3, "closed", "Non-code closure: duplicate", ("type/process",), ()),
    )
    assert audit_closures(issues) == (2, (1,))
