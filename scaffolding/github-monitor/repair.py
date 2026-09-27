"""Pure decisions for temporary #179 REST repair."""
# ruff: noqa: INP001

import hashlib
import json
from dataclasses import dataclass

REPOSITORY = "tbhb/agent-orchestration-poc"
MAX_REQUESTS = 20
MAX_PAGES = 10
RESERVE = 100


@dataclass(frozen=True)
class Endpoint:
    """A current-state source and its projection component."""

    name: str
    component: str
    path: str
    paginated: bool = False


def endpoints(kind: str, number: int, head: str | None = None) -> tuple[Endpoint, ...]:
    """Select only allowlisted, tracked-object REST sources."""
    issue = f"/repos/{REPOSITORY}/issues/{number}"
    common = (
        Endpoint("issue", "identity", issue),
        Endpoint("issue_comments", "comments", f"{issue}/comments?per_page=100", True),
    )
    if kind == "issue":
        return (
            *common,
            Endpoint("labels", "labels", f"{issue}/labels?per_page=100", True),
        )
    if kind != "pr" or not head:
        raise ValueError("PR repair requires an authoritative head")
    pr = f"/repos/{REPOSITORY}/pulls/{number}"
    commit = f"/repos/{REPOSITORY}/commits/{head}"
    return (
        *common,
        Endpoint("pull", "identity", pr),
        Endpoint("labels", "labels", f"{issue}/labels?per_page=100", True),
        Endpoint("reviews", "reviews", f"{pr}/reviews?per_page=100", True),
        Endpoint("review_comments", "comments", f"{pr}/comments?per_page=100", True),
        Endpoint("check_runs", "checks", f"{commit}/check-runs?per_page=100", True),
        Endpoint("statuses", "checks", f"{commit}/status"),
    )


def capacity(headers: dict[str, str], spent: int, pages: int) -> str | None:
    """Refuse unknown or inconsistent REST capacity and per-object ceilings."""
    if spent >= MAX_REQUESTS or pages >= MAX_PAGES:
        return "request_or_page_cap"
    try:
        limit = int(headers["x-ratelimit-limit"])
        remaining = int(headers["x-ratelimit-remaining"])
        resource = headers["x-ratelimit-resource"]
    except KeyError, ValueError:
        return "unknown_headers"
    if resource != "core" or limit <= 0 or remaining < 0 or remaining > limit:
        return "contradictory_headers"
    if remaining <= RESERVE:
        return "reserve"
    return None


def body_for_response(
    status: int, body: bytes, saved: tuple[str, bytes] | None, etag: str | None
) -> bytes | None:
    """Reuse 304 bytes only when the exact page validator matches."""
    if status == 200:
        return body
    if status == 304 and saved is not None and etag == saved[0]:
        return saved[1]
    return None


def digest(value: object) -> str:
    """Hash a canonical value without retaining its prose in evidence."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def authoritative(name: str, pages: tuple[object, ...]) -> str:
    """Select fields that can change the claimed current observation."""
    if name == "issue":
        item = pages[0]
        if not isinstance(item, dict):
            raise ValueError("invalid issue body")
        return digest(
            (
                item.get("id"),
                item.get("body"),
                item.get("state"),
                item.get("labels"),
                item.get("updated_at"),
            )
        )
    if name == "pull":
        item = pages[0]
        if not isinstance(item, dict):
            raise ValueError("invalid pull body")
        head, base = item.get("head"), item.get("base")
        if not isinstance(head, dict) or not isinstance(base, dict):
            raise ValueError("invalid pull head or base")
        return digest(
            (
                head.get("sha"),
                base.get("sha"),
                item.get("state"),
                item.get("updated_at"),
            )
        )
    return digest(pages)


def complete(
    initial: dict[str, str], final: dict[str, str], captured: int, current: int
) -> str | None:
    """Accept a component only after final rereads and generation fencing."""
    if captured != current:
        return "invalidation_during_collection"
    for name, value in initial.items():
        if name not in final or final[name] != value:
            return f"changed_{name}"
    return None


def component_reason(
    kind: str, component: str, change: str | None, captured: int, current: int
) -> str | None:
    """Keep unsupported PR evidence visibly unknown."""
    reason = change or complete({}, {}, captured, current)
    if component == "reviews":
        return reason or "review_thread_resolution_unsupported"
    if component == "checks":
        return reason or "latest_attempt_selection_unsupported"
    if kind == "pr" and component == "comments":
        return reason or "review_comments_not_rechecked"
    return reason


def next_page(link: str | None) -> str | None:
    """Read the next-page relation without guessing a page count."""
    if not link:
        return None
    for part in link.split(","):
        url, _, relation = part.strip().partition(";")
        if 'rel="next"' in relation and url.startswith("<") and url.endswith(">"):
            return url[1:-1]
    return None


def budget_handoff(
    principal: str, headers: dict[str, str], requests: int, pages: int
) -> dict[str, str | int | None]:
    """Expose observed REST admission facts to the later atomic scheduler."""
    return {
        "principal": principal,
        "resource": headers.get("x-ratelimit-resource"),
        "limit": headers.get("x-ratelimit-limit"),
        "remaining": headers.get("x-ratelimit-remaining"),
        "reset": headers.get("x-ratelimit-reset"),
        "retry_after": headers.get("retry-after"),
        "requests": requests,
        "pages": pages,
    }
