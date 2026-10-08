"""Read pull request artifacts and report untracked skip indicators."""

import json
import logging
import os
from collections.abc import Mapping
from typing import Any, cast
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from agent_orchestration_poc.core.skipscan import scan_diff, scan_text

LOGGER = logging.getLogger(__name__)


def _get(url: str, token: str, accept: str = "application/vnd.github+json") -> str:
    request = Request(  # noqa: S310  #300
        url,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
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


def main() -> int:
    """Run the scanner in a pull request job."""
    repo = os.environ["GITHUB_REPOSITORY"]
    number = int(os.environ["PR_NUMBER"])
    token = os.environ["GH_TOKEN"]
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        return run("https://api.github.com", token, repo, number)
    except (OSError, ValueError, TypeError, KeyError) as error:
        LOGGER.exception("skipscan: API error: %s", type(error).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
