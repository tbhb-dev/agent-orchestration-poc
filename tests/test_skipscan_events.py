"""Event routing and current-head reporting for skipscan."""

from pathlib import Path

import pytest
import yaml  # pyrefly: ignore[untyped-import]  PyYAML is available for #300's workflow test.

from agent_orchestration_poc.core.skipscan import check_run_result, event_pr_number


def test_workflow_rescans_all_comment_and_review_changes() -> None:
    root = Path(__file__).resolve().parents[1]
    if root.name == "mutants":
        root = root.parent
    workflow = yaml.safe_load(
        (root / ".github/workflows/skipscan-comments.yml").read_text()
    )
    triggers = workflow["on"]
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


@pytest.mark.parametrize(
    ("result", "conclusion"), [(0, "success"), (1, "failure"), (2, "failure")]
)
def test_check_run_result(result: int, conclusion: str) -> None:
    assert check_run_result(result) == {
        "status": "completed",
        "conclusion": conclusion,
    }
