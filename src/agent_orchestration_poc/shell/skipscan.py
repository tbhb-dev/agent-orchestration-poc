"""Read pull request artifacts and report untracked skip indicators."""

import json
import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from agent_orchestration_poc.core.skipscan import (
    check_run_result,
    event_pr_number,
    scan_diff,
    scan_text,
)

LOGGER = logging.getLogger(__name__)


def _get(
    url: str,
    token: str,
    accept: str = "application/vnd.github+json",
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> str:
    request = Request(  # noqa: S310  #300
        url,
        data=json.dumps(data).encode() if data is not None else None,
        method=method,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310  #300
        return cast("str", response.read().decode("utf-8"))


def _pages(api: str, token: str, path: str) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for page in range(1, 1000):
        query = urlencode({"per_page": 100, "page": page})
        batch = json.loads(_get(f"{api}/{path}?{query}", token))
        if not isinstance(batch, list):
            raise TypeError("GitHub returned a non-list page")
        rows.extend(batch)
        if len(batch) < 100:
            return rows
    raise ValueError("GitHub pagination exceeded 999 pages")


def run(api: str, token: str, repo: str, number: int) -> int:
    """Collect PR artifacts and emit only redacted, untracked findings."""
    prefix = f"repos/{repo}/pulls/{number}"
    pr = json.loads(_get(f"{api}/{prefix}", token))
    hits = scan_text(pr.get("body") or "", "pr-body", f"PR #{number} body")
    for path in (f"{prefix}/comments", f"repos/{repo}/issues/{number}/comments"):
        for row in _pages(api, token, path):
            hits.extend(
                scan_text(row.get("body") or "", "review-comment", row["html_url"])
            )
    for row in _pages(api, token, f"{prefix}/reviews"):
        if row.get("body"):
            hits.extend(scan_text(row["body"], "review-verdict", row["html_url"]))
    for row in _pages(api, token, f"{prefix}/commits"):
        hits.extend(
            scan_text(
                row["commit"]["message"], "commit-message", f"commit {row['sha']}"
            )
        )
    diff = _get(f"{api}/{prefix}", token, "application/vnd.github.v3.diff")
    hits.extend(scan_diff(diff, f"PR #{number}"))
    untracked = [hit for hit in hits if not hit["tracked"]]
    for hit in untracked:
        LOGGER.error("%s:%s: %s", hit["source"], hit["line"], hit["phrase"])
    LOGGER.info("skipscan: %d untracked indicator(s)", len(untracked))
    return int(bool(untracked))


def run_event(
    api: str, token: str, repo: str, event_name: str, payload: dict[str, Any]
) -> int:
    """Scan an event's PR and attach comment-triggered results to its head."""
    number = event_pr_number(event_name, payload)
    if number is None:
        return 0
    if event_name == "pull_request":
        return run(api, token, repo, number)

    pr_url = f"{api}/repos/{repo}/pulls/{number}"
    head = json.loads(_get(pr_url, token))["head"]["sha"]
    checks_url = f"{api}/repos/{repo}/check-runs"
    created = json.loads(
        _get(
            checks_url,
            token,
            method="POST",
            data={"name": "skipscan", "head_sha": head, "status": "in_progress"},
        )
    )
    update_url = f"{checks_url}/{created['id']}"
    try:
        result = run(api, token, repo, number)
        if json.loads(_get(pr_url, token))["head"]["sha"] != head:
            result = 2
    except OSError, ValueError, TypeError, KeyError:
        _get(update_url, token, method="PATCH", data=check_run_result(2))
        raise
    _get(update_url, token, method="PATCH", data=check_run_result(result))
    return result


def main() -> int:
    """Run the scanner in a pull request job."""
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    event_name = os.environ["GITHUB_EVENT_NAME"]
    payload = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        return run_event("https://api.github.com", token, repo, event_name, payload)
    except (OSError, ValueError, TypeError, KeyError) as error:
        LOGGER.exception("skipscan: API error: %s", type(error).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
