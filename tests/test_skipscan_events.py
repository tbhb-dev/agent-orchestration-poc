"""Event routing and current-head reporting for skipscan."""

from pathlib import Path
from typing import Any

import pytest
import yaml  # pyrefly: ignore[untyped-import]  PyYAML is available for #300's workflow test.

from agent_orchestration_poc.core import skipscan
from agent_orchestration_poc.core.skipscan import (
    check_run_result,
    event_pr_number,
    head_result,
    scan_outcome,
)


def test_workflow_rescans_all_comment_and_review_changes() -> None:
    root = Path(__file__).resolve().parents[1]
    if root.name == "mutants":
        root = root.parent
    workflow = yaml.safe_load(
        (root / ".github/workflows/skipscan-comments.yml").read_text()
    )
    triggers = yaml.safe_load((root / ".github/workflows/skipscan.yml").read_text())[
        "on"
    ]
    assert workflow["on"]["workflow_run"] == {
        "workflows": ["skipscan"],
        "types": ["completed"],
    }
    assert "pull_request_review" not in workflow["on"]
    triggers["issue_comment"] = workflow["on"]["issue_comment"]
    assert set(triggers["issue_comment"]["types"]) == {"created", "edited", "deleted"}
    assert set(triggers["pull_request_review_comment"]["types"]) == {
        "created",
        "edited",
        "deleted",
    }
    assert set(triggers["pull_request_review"]["types"]) == {
        "submitted",
        "edited",
        "dismissed",
    }
    assert workflow["permissions"]["checks"] == "write"
    assert workflow["jobs"]["rescan"]["steps"][0]["with"]["ref"] == (
        "${{ github.event.repository.default_branch }}"
    )
    pr_workflow = yaml.safe_load((root / ".github/workflows/skipscan.yml").read_text())
    assert "checks" not in pr_workflow["permissions"]


@pytest.mark.parametrize(
    ("event_name", "payload", "number"),
    [
        ("pull_request", {"pull_request": {"number": 12}}, 12),
        ("pull_request_review", {"pull_request": {"number": 13}}, 13),
        ("pull_request_review_comment", {"pull_request": {"number": 14}}, 14),
        ("issue_comment", {"issue": {"number": 15, "pull_request": {"url": "pr"}}}, 15),
        ("issue_comment", {"issue": {"number": 16}}, None),
    ],
)
def test_event_pr_number(
    event_name: str, payload: dict[str, object], number: int | None
) -> None:
    assert event_pr_number(event_name, payload) == number


def test_unsupported_event_names_the_event() -> None:
    with pytest.raises(ValueError, match="^Unsupported skipscan event: push$"):
        event_pr_number("push", {})


@pytest.mark.parametrize(
    ("result", "conclusion"), [(0, "success"), (1, "failure"), (2, "failure")]
)
def test_check_run_result(result: int, conclusion: str) -> None:
    assert check_run_result(result) == {
        "status": "completed",
        "conclusion": conclusion,
    }


def test_scan_outcome_uses_only_untracked_hits() -> None:
    tracked = {"tracked": True, "phrase": "skipped"}
    untracked = {"tracked": False, "phrase": "deferred"}
    assert scan_outcome([]) == ([], 0)
    assert scan_outcome([tracked]) == ([], 0)
    assert scan_outcome([tracked, untracked]) == ([untracked], 1)


def test_head_result_fails_stale_scan() -> None:
    assert head_result(0, "original", "original") == 0
    assert head_result(1, "original", "original") == 1
    assert head_result(0, "original", "new") == 2


@pytest.mark.parametrize(("expected", "collected"), [(251, 250), (1, 0), (0, 1)])
def test_incomplete_commit_count(expected: int, collected: int) -> None:
    with pytest.raises(ValueError, match="Incomplete commit scan"):
        skipscan.validate_commit_count(expected, collected)


@pytest.mark.parametrize("count", [0, 1, 250])
def test_complete_commit_count(count: int) -> None:
    assert skipscan.validate_commit_count(count, count) is None


def test_review_run_matches_repository_and_branch() -> None:
    payload: dict[str, Any] = {
        "workflow_run": {
            "head_repository": {"full_name": "fork/repo"},
            "head_branch": "topic",
            "pull_requests": [],
        }
    }
    prs = [
        {"number": 1, "head": {"repo": {"full_name": "fork/repo"}, "ref": "topic"}},
        {"number": 2, "head": {"repo": {"full_name": "other/repo"}, "ref": "topic"}},
        {"number": 3, "head": {"repo": {"full_name": "fork/repo"}, "ref": "other"}},
        {"number": 4, "head": {"repo": None, "ref": "topic"}},
    ]
    assert skipscan.review_pr_numbers(payload, prs) == [1]
    assert skipscan.review_pr_numbers(payload, []) == []


@pytest.mark.parametrize(
    ("results", "expected"), [([], 0), ([0], 0), ([1, 0], 1), ([0, 2, 1], 2)]
)
def test_rescan_result(results: list[int], expected: int) -> None:
    assert skipscan.rescan_result(results) == expected
