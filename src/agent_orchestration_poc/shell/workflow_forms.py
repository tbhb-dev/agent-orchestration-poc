"""GitHub and file operations for workflow form checks."""

import argparse
import json
import logging
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any, cast

from agent_orchestration_poc.core.workflow_forms import (
    Reference,
    blocking_findings,
    changed_forms,
    generated_files,
    issue_records,
    label_names,
    open_reference_numbers,
    page_items,
    refs,
    remote_mode,
    validate_issue,
    validate_pr,
)

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY = "tbhb/agent-orchestration-poc"
LOGGER = logging.getLogger(__name__)


def _reference() -> Reference:
    return tomllib.loads((ROOT / "config/workflow-reference.toml").read_text())


def _run_gh(*args: str) -> str:
    """Run a REST request, retrying rate limits without printing response data."""
    command = ("gh", "api", *args)
    for attempt in range(4):
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return result.stdout
        if "rate limit" not in result.stderr.lower() or attempt == 3:
            raise RuntimeError(f"GitHub REST request failed (exit {result.returncode})")
        time.sleep(120)
    raise RuntimeError("unreachable GitHub retry state")


def _api(path: str, *args: str) -> dict[str, Any]:
    output = _run_gh(f"repos/{REPOSITORY}/{path}", *args)
    return cast("dict[str, Any]", json.loads(output)) if output else {}


def _pages(path: str) -> list[dict[str, Any]]:
    output = _run_gh(f"repos/{REPOSITORY}/{path}", "--paginate", "--slurp")
    pages = cast("list[list[dict[str, Any]]]", json.loads(output))
    return list(page_items(tuple(tuple(page) for page in pages)))


def _names(raw: dict[str, Any]) -> tuple[str, ...]:
    return label_names(tuple(raw["labels"]))


def _report(number: int, findings: tuple[str, ...], mode: str = "enforce") -> int:
    for finding in findings:
        LOGGER.error("#%s [%s] %s", number, mode, finding)
    if not findings:
        LOGGER.info("#%s [%s] valid", number, mode)
    return int(blocking_findings(findings, mode))


def audit_issue(number: int, reference: Reference) -> int:
    """Read and validate one issue without changing it."""
    raw = _api(f"issues/{number}")
    if not issue_records((raw,)):
        raise ValueError(f"#{number} is a pull request")
    return _report(
        number,
        validate_issue(raw["title"], raw["body"] or "", _names(raw), reference),
    )


def audit_issues(reference: Reference) -> int:
    """Read and validate every open issue, reporting all findings."""
    issues = _pages("issues?state=open&per_page=100")
    status = 0
    for issue in issue_records(tuple(issues)):
        status |= _report(
            issue["number"],
            validate_issue(
                issue["title"], issue["body"] or "", _names(issue), reference
            ),
        )
    return status


def audit_pr(number: int, reference: Reference) -> int:
    """Read a PR and its referenced issues, applying the merge cutoff."""
    raw = _api(f"pulls/{number}")
    activation = reference["migration"]["validator_pr"]
    if not activation:
        raise ValueError("validator PR number is not recorded")
    validator = _api(f"pulls/{activation}")
    cutoff = validator.get("merged_at")
    mode = remote_mode(raw.get("created_at"), cutoff, validator["state"])
    if mode == "invalid":
        return _report(number, ("missing or invalid PR creation or cutoff metadata",))
    body = raw["body"] or ""
    issue_states = {
        issue_number: _api(f"issues/{issue_number}") for issue_number in refs(body)
    }
    open_issues = open_reference_numbers(issue_states)
    return _report(
        number,
        validate_pr(raw["title"], body, _names(raw), open_issues, reference),
        mode,
    )


def check_forms(reference: Reference, *, write: bool) -> int:
    """Write or compare generated issue forms and the reference page."""
    directory = ROOT / ".github/ISSUE_TEMPLATE"
    if write:
        directory.mkdir(parents=True, exist_ok=True)
    expected = generated_files(reference)
    if write:
        for relative_path, content in expected.items():
            (ROOT / relative_path).write_text(content)
        return 0
    actual = {}
    for relative_path in expected:
        path = ROOT / relative_path
        actual[relative_path] = path.read_text() if path.is_file() else None
    findings = changed_forms(expected, actual)
    for path in findings:
        LOGGER.error("form differs from reference: %s", path)
    return int(bool(findings))


def main() -> int:
    """Dispatch one workflow audit or form action."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "issue",
            "issues",
            "pr",
            "forms",
            "write-forms",
        ),
    )
    parser.add_argument("number", type=int, nargs="?")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    reference = _reference()
    try:
        match args.command:
            case "issue" if args.number:
                result = audit_issue(args.number, reference)
            case "issues":
                result = audit_issues(reference)
            case "pr" if args.number:
                result = audit_pr(args.number, reference)
            case "forms":
                result = check_forms(reference, write=False)
            case "write-forms":
                result = check_forms(reference, write=True)
            case _:
                parser.error("number required for issue or pr")
    except RuntimeError, ValueError, subprocess.CalledProcessError:
        LOGGER.exception("workflow audit failed")
        return 2
    return result


if __name__ == "__main__":
    sys.exit(main())
