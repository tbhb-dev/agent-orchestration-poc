"""Fetch and acknowledge fixture operator commands through the GitHub REST API."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from agent_orchestration_poc.core.operator_commands import Decision, decide

LOGGER = logging.getLogger(__name__)
REPOSITORY = "tbhb-dev/agent-orchestration-poc"
API = "https://api.github.com"
# Replaced only by a reviewed change that records two disposable item IDs.
FIXTURE_ISSUE = 0
FIXTURE_PR = 0


def request_json(
    base: str,
    token: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> tuple[Any, str | None]:
    """Make one authenticated REST request, returning JSON and pagination link."""
    url = f"{base}{path}"
    parsed = urlparse(url)
    if not (
        (parsed.scheme == "https" and parsed.hostname == "api.github.com")
        or (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"})
    ):
        raise ValueError("untrusted API host")
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "agent-orchestration-operator-commands",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    target = Request(url, data=data, headers=headers, method=method)  # noqa: S310 validated host and scheme
    with urlopen(target, timeout=20) as response:  # noqa: S310 validated host and scheme
        raw = response.read()
        return (json.loads(raw) if raw else None), response.headers.get("Link")


def all_pages(base: str, token: str, path: str) -> tuple[dict[str, Any], ...]:
    """Read every page of one REST collection, refusing repeated or foreign links."""
    prefix = path.split("?", 1)[0]
    seen: set[str] = set()
    comments: list[dict[str, Any]] = []
    while path:
        if path in seen:
            raise ValueError("repeated comment page")
        seen.add(path)
        page, link = request_json(base, token, path)
        if not isinstance(page, list):
            raise TypeError("invalid comment page")
        comments.extend(page)
        next_url = next(
            (
                part.split(";", 1)[0].strip(" <>")
                for part in (link or "").split(",")
                if 'rel="next"' in part
            ),
            None,
        )
        if next_url:
            if not next_url.startswith(f"{base}{prefix}?"):
                raise ValueError("foreign comment page")
            path = next_url[len(base) :]
        else:
            path = ""
    return tuple(comments)


def all_comments(base: str, token: str, number: int) -> tuple[dict[str, Any], ...]:
    """Read all issue timeline comment pages."""
    return all_pages(
        base, token, f"/repos/{REPOSITORY}/issues/{number}/comments?per_page=100"
    )


def process(event: dict[str, Any], token: str, base: str = API) -> Decision:
    """Fetch source data, apply a pure decision, and acknowledge once."""
    if event.get("action") != "created" or event.get("actor") != "tbhb":
        return Decision(None)
    number = event.get("issue", {}).get("number")
    is_pr = bool(event.get("issue", {}).get("pull_request"))
    if not isinstance(number, int) or number != (
        FIXTURE_PR if is_pr else FIXTURE_ISSUE
    ):
        return Decision(None)
    comment_id = event.get("comment", {}).get("id")
    if not isinstance(comment_id, int) or comment_id <= 0:
        return Decision(None)
    root = f"/repos/{REPOSITORY}"
    comment, _ = request_json(base, token, f"{root}/issues/comments/{comment_id}")
    item, _ = request_json(base, token, f"{root}/issues/{number}")
    comments = all_comments(base, token, number)
    facts = {
        "action": event["action"],
        "actor": event["actor"],
        "number": number,
        "is_pr": is_pr,
        "comment_id": comment_id,
        "issue_url": f"{API}{root}/issues/{number}",
    }
    decision = decide(facts, comment, item, comments)
    if decision.reaction is None:
        return decision
    reactions = all_pages(
        base, token, f"{root}/issues/comments/{comment_id}/reactions?per_page=100"
    )
    if not any(
        reaction.get("content") == decision.reaction
        and reaction.get("user", {}).get("login") == "github-actions[bot]"
        for reaction in reactions
    ):
        request_json(
            base,
            token,
            f"{root}/issues/comments/{comment_id}/reactions",
            "POST",
            {"content": decision.reaction},
        )
    if decision.add_label and not any(
        label.get("name") == "operator/replied" for label in item["labels"]
    ):
        request_json(
            base,
            token,
            f"{root}/issues/{number}/labels",
            "POST",
            {"labels": ["operator/replied"]},
        )
    return decision


def main() -> int:
    """Process one Actions event without exposing the token or comment body."""
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    if os.environ["GITHUB_REPOSITORY"] != REPOSITORY:
        return 1
    decision = process(
        event | {"actor": os.environ["GITHUB_ACTOR"]}, os.environ["GITHUB_TOKEN"]
    )
    LOGGER.info("operator command reaction: %s", decision.reaction or "none")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
