"""Fixture checks for the coordinator's pure decisions."""

import json
from pathlib import Path
from typing import Any

import pytest

from agent_orchestration_poc.core.coordinator_preflight import (
    CheckOutcome,
    CheckState,
    IssueState,
    MergedPullRequest,
    check_outcome,
    linked_merged_prs,
    needs_closure_review,
    outdated_workflows,
)

FIXTURES = Path(__file__).parent / "fixtures" / "coordinator_preflight"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.parametrize("case", ["outdated", "current"])
def test_workflow_revision(case: str) -> None:
    fixture = _load("workflows.json")[case]
    assert (
        list(outdated_workflows(fixture["base"], fixture["main"], fixture["head"]))
        == fixture["expected"]
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
