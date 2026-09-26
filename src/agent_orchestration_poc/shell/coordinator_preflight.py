"""Read GitHub and git state for coordinator preflight commands."""

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

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


@dataclass(frozen=True)
class PullRequest:
    """Fields read from a pull request status rollup."""

    head_ref_oid: str
    status_check_rollup: tuple[dict[str, str | None], ...]


def _run(*argv: str) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def _pull_request(number: int) -> PullRequest:
    raw = cast(
        "dict[str, object]",
        json.loads(
            _run(
                "gh",
                "pr",
                "view",
                str(number),
                "--json",
                "headRefOid,statusCheckRollup",
            )
        ),
    )
    return PullRequest(
        head_ref_oid=cast("str", raw["headRefOid"]),
        status_check_rollup=tuple(
            cast("list[dict[str, str | None]]", raw["statusCheckRollup"])
        ),
    )


def _workflow_tree(revision: str) -> dict[str, str]:
    entries = _run("git", "ls-tree", "-r", revision, ".github/workflows/")
    return {
        path: metadata.split()[2]
        for entry in entries.splitlines()
        for metadata, path in [entry.split("\t", 1)]
    }


def _review_preflight(number: int) -> int:
    head = _pull_request(number).head_ref_oid
    _run("git", "fetch", "origin", "main")
    _run("git", "fetch", "origin", f"refs/pull/{number}/head")
    fetched_head = _run("git", "rev-parse", "FETCH_HEAD").strip()
    if fetched_head != head:
        sys.stderr.write(f"PR #{number} head changed during fetch; retry\n")
        return 1
    main = _run("git", "rev-parse", "origin/main").strip()
    base = _run("git", "merge-base", main, head).strip()
    head_tree = _workflow_tree(head)
    stale = outdated_workflows(_workflow_tree(base), _workflow_tree(main), head_tree)
    for path in stale:
        reason = "missing" if path not in head_tree else "outdated"
        sys.stderr.write(f"PR #{number}: {path} {reason} relative to origin/main\n")
    if stale:
        return 1
    sys.stdout.write(f"PR #{number}: workflows include current origin/main revisions\n")
    return 0


def _check_states(raw: PullRequest) -> tuple[CheckState, ...]:
    return tuple(
        CheckState(
            name=str(check.get("name") or check.get("context")),
            status=str(check.get("status") or check.get("state")),
            conclusion=check.get("conclusion") or check.get("state"),
            started_at=check.get("startedAt") or check.get("createdAt") or "",
        )
        for check in raw.status_check_rollup
    )


def _wait_check(number: int, name: str, timeout: int) -> int:
    if timeout < 0:
        sys.stderr.write("timeout must be nonnegative seconds\n")
        return 2
    expected = _pull_request(number).head_ref_oid
    deadline = time.monotonic() + timeout
    while True:
        current = _pull_request(number)
        outcome = check_outcome(
            expected, current.head_ref_oid, name, _check_states(current)
        )
        if outcome == CheckOutcome.SUCCESS:
            sys.stdout.write(f"PR #{number}: {name} succeeded on {expected}\n")
            return 0
        if outcome in (CheckOutcome.FAIL, CheckOutcome.CHANGED_HEAD):
            sys.stderr.write(f"PR #{number}: {name} {outcome.value} on {expected}\n")
            return 1
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            sys.stderr.write(
                f"PR #{number}: {name} did not succeed on {expected} within {timeout}s\n"
            )
            return 1
        time.sleep(min(5, remaining))


def _closure_audit() -> int:
    raw_issues = cast(
        "list[dict[str, object]]",
        json.loads(
            _run(
                "gh",
                "issue",
                "list",
                "--state",
                "closed",
                "--limit",
                "10000",
                "--json",
                "number,state,body,labels",
            )
        ),
    )
    raw_prs = cast(
        "list[dict[str, object]]",
        json.loads(
            _run(
                "gh",
                "pr",
                "list",
                "--state",
                "merged",
                "--limit",
                "10000",
                "--json",
                "number,body,closingIssuesReferences",
            )
        ),
    )
    if len(raw_issues) == 10000 or len(raw_prs) == 10000:
        sys.stderr.write("closure audit reached the 10000-item query limit\n")
        return 2
    pull_requests = tuple(
        MergedPullRequest(
            number=cast("int", raw["number"]),
            body=cast("str", raw["body"] or ""),
            closing_issues=tuple(
                cast("int", issue["number"])
                for issue in cast(
                    "list[dict[str, object]]", raw["closingIssuesReferences"]
                )
            ),
        )
        for raw in raw_prs
    )
    flagged: list[int] = []
    checked = 0
    for raw in raw_issues:
        labels = tuple(
            cast("str", label["name"])
            for label in cast("list[dict[str, object]]", raw["labels"])
        )
        if not any(label.startswith("type/") for label in labels):
            continue
        number = cast("int", raw["number"])
        issue = IssueState(
            number=number,
            state=cast("str", raw["state"]).lower(),
            body=cast("str", raw["body"] or ""),
            labels=labels,
            merged_prs=linked_merged_prs(number, pull_requests),
        )
        checked += 1
        if needs_closure_review(issue):
            flagged.append(number)
    for number in flagged:
        sys.stderr.write(
            f"issue #{number}: closed without a linked merged PR or recorded non-code closure\n"
        )
    sys.stdout.write(
        f"Audited {checked} closed work-item issues; {len(flagged)} need review\n"
    )
    return 1 if flagged else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run one coordinator preflight command."""
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    review = commands.add_parser("review")
    review.add_argument("pr", type=int)
    waiter = commands.add_parser("wait-check")
    waiter.add_argument("pr", type=int)
    waiter.add_argument("name")
    waiter.add_argument("timeout", type=int)
    commands.add_parser("closure-audit")
    args = parser.parse_args(argv)
    try:
        if args.command == "review":
            return _review_preflight(args.pr)
        if args.command == "wait-check":
            return _wait_check(args.pr, args.name, args.timeout)
        return _closure_audit()
    except (subprocess.CalledProcessError, KeyError, ValueError) as error:
        sys.stderr.write(f"coordinator preflight failed: {error}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
