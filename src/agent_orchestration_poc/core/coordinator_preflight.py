"""Pure decisions for coordinator review and checkpoint checks."""

import re
from dataclasses import dataclass
from enum import StrEnum


class CheckOutcome(StrEnum):
    """The result of one named check observation."""

    WAIT = "wait"
    SUCCESS = "success"
    FAIL = "fail"
    CHANGED_HEAD = "changed-head"


@dataclass(frozen=True)
class CheckState:
    """A check reported in the PR head's status rollup."""

    name: str
    status: str
    conclusion: str | None
    started_at: str


@dataclass(frozen=True)
class IssueState:
    """The facts needed to audit one work-item issue."""

    number: int
    state: str
    body: str
    labels: tuple[str, ...]
    merged_prs: tuple[int, ...]


@dataclass(frozen=True)
class MergedPullRequest:
    """A merged PR and its recorded issue references."""

    number: int
    body: str
    closing_issues: tuple[int, ...]


def outdated_workflows(
    base: dict[str, str], main: dict[str, str], head: dict[str, str]
) -> tuple[str, ...]:
    """Find main workflow revisions absent from a PR branch."""
    return tuple(
        path
        for path in sorted(base.keys() | main.keys())
        if base.get(path) != main.get(path) and head.get(path) != main.get(path)
    )


def check_outcome(
    expected_head: str,
    current_head: str,
    check_name: str,
    checks: tuple[CheckState, ...],
) -> CheckOutcome:
    """Decide whether the named check succeeded on the expected head."""
    if current_head != expected_head:
        return CheckOutcome.CHANGED_HEAD
    matches = [check for check in checks if check.name == check_name]
    if not matches:
        return CheckOutcome.WAIT
    if any(
        check.status not in ("COMPLETED", "SUCCESS", "FAILURE", "ERROR")
        for check in matches
    ):
        return CheckOutcome.WAIT
    if len(matches) > 1 and (
        any(not check.started_at for check in matches)
        or len({check.started_at for check in matches}) != len(matches)
    ):
        outcomes = {check.conclusion or check.status for check in matches}
        if len(outcomes) != 1:
            return CheckOutcome.WAIT
    latest = max(matches, key=lambda check: check.started_at)
    if latest.status == "SUCCESS" or (
        latest.status == "COMPLETED" and latest.conclusion == "SUCCESS"
    ):
        return CheckOutcome.SUCCESS
    return CheckOutcome.FAIL


def normalize_checks(
    raw_checks: tuple[dict[str, str | None], ...],
) -> tuple[CheckState, ...]:
    """Convert GitHub rollup values into check observations."""
    return tuple(
        CheckState(
            name=str(check.get("name") or check.get("context")),
            status=str(check.get("status") or check.get("state")),
            conclusion=check.get("conclusion") or check.get("state"),
            started_at=check.get("startedAt") or check.get("createdAt") or "",
        )
        for check in raw_checks
    )


def needs_closure_review(issue: IssueState) -> bool:
    """Flag a closed work item without a merged PR or recorded exception."""
    if issue.state != "closed" or not any(
        label.startswith("type/") for label in issue.labels
    ):
        return False
    if issue.merged_prs:
        return False
    if "type/decision" in issue.labels and re.search(
        r"\bClosed by (?:the|a) decision record\b", issue.body, re.IGNORECASE
    ):
        return False
    return not any(
        line.startswith("Non-code closure: ")
        and line.removeprefix("Non-code closure: ").strip()
        for line in issue.body.splitlines()
    )


def linked_merged_prs(
    issue_number: int, pull_requests: tuple[MergedPullRequest, ...]
) -> tuple[int, ...]:
    """Find merged PRs linked by a trailer or GitHub closing reference."""
    return tuple(
        pr.number
        for pr in pull_requests
        if issue_number in pr.closing_issues
        or any(
            int(match) == issue_number
            for match in re.findall(r"(?m)^Refs: #(\d+)\s*$", pr.body)
        )
    )


def audit_closures(issues: tuple[IssueState, ...]) -> tuple[int, tuple[int, ...]]:
    """Count closed work items and identify those needing review."""
    selected = tuple(
        issue
        for issue in issues
        if issue.state == "closed"
        and any(label.startswith("type/") for label in issue.labels)
    )
    return len(selected), tuple(
        issue.number for issue in selected if needs_closure_review(issue)
    )
