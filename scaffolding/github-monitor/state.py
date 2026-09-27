"""Temporary #167 decisions, replaced by permanent #189 and #190."""
# ruff: noqa: INP001, C901, PLR0912

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

SCHEMA_VERSION = 1
REPOSITORY_ID = 1389534135
REPOSITORY_NAME = "tbhb/agent-orchestration-poc"
COMPONENTS = {
    "pr": ("identity", "checks", "reviews", "comments", "labels"),
    "issue": ("identity", "comments", "labels"),
}
EVENT_COMPONENTS = {
    "pull_request": ("identity", "checks", "reviews", "comments", "labels"),
    "pull_request_review": ("reviews",),
    "pull_request_review_comment": ("comments", "reviews"),
    "pull_request_review_thread": ("comments", "reviews"),
    "issues": ("identity", "comments", "labels"),
    "issue_comment": ("comments",),
    "check_run": ("checks",),
    "check_suite": ("checks",),
    "status": ("checks",),
    "workflow_run": ("checks",),
}
EVENT_ACTIONS = {
    "pull_request": "opened reopened synchronize edited closed labeled unlabeled "
    "ready_for_review converted_to_draft review_requested review_request_removed",
    "pull_request_review": "submitted edited dismissed",
    "pull_request_review_comment": "created edited deleted",
    "pull_request_review_thread": "resolved unresolved",
    "issues": "opened edited closed reopened labeled unlabeled deleted transferred",
    "issue_comment": "created edited deleted",
    "check_run": "created completed rerequested requested_action",
    "check_suite": "requested rerequested completed",
    "workflow_run": "requested in_progress completed",
}


@dataclass(frozen=True)
class Invalidation:
    """One named object's components to invalidate."""

    kind: str
    number: int
    components: tuple[str, ...]
    head_sha: str | None = None


def signature_result(header: str | None, body: bytes, secret: bytes) -> str:
    """Classify a signature over the exact bytes without parsing the body."""
    if header is None:
        return "missing"
    if len(header) != 71 or not header.startswith("sha256="):
        return "malformed"
    digest = header[7:]
    if any(char not in "0123456789abcdefABCDEF" for char in digest):
        return "malformed"
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return "valid" if hmac.compare_digest(digest.lower(), expected) else "invalid"


def _number(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("invalid object number")
    return value


def _object_number(value: object) -> int:
    if not isinstance(value, dict):
        raise TypeError("missing object")
    return _number(value.get("number"))


def classify_delivery(
    event: str, body: bytes, installation_id: int
) -> tuple[Invalidation, ...]:
    """Validate identity and turn a verified payload into invalidations."""
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise TypeError("invalid payload")
    repo = payload.get("repository")
    install = payload.get("installation")
    if not isinstance(repo, dict) or not isinstance(install, dict):
        raise TypeError("missing identity")
    if repo.get("id") != REPOSITORY_ID or repo.get("full_name") != REPOSITORY_NAME:
        raise ValueError("repository not allowed")
    if _number(install.get("id")) != installation_id:
        raise ValueError("installation not allowed")
    if event not in EVENT_COMPONENTS:
        return ()
    if event != "status" and not isinstance(payload.get("action"), str):
        raise ValueError("missing action")
    if event != "status" and not payload["action"]:
        raise ValueError("empty action")
    if event != "status" and payload["action"] not in EVENT_ACTIONS[event].split():
        return ()
    components = EVENT_COMPONENTS[event]
    if event == "issues":
        return (
            Invalidation("issue", _object_number(payload.get("issue")), components),
        )
    if event == "issue_comment":
        issue = payload.get("issue")
        kind = "pr" if isinstance(issue, dict) and "pull_request" in issue else "issue"
        return (Invalidation(kind, _object_number(issue), components),)
    if event.startswith("pull_request"):
        pr = payload.get("pull_request")
        head = pr.get("head") if isinstance(pr, dict) else None
        sha = head.get("sha") if isinstance(head, dict) else None
        return (Invalidation("pr", _object_number(pr), components, sha),)
    prs = payload.get("pull_requests")
    if not isinstance(prs, list):
        nested = payload.get(event)
        prs = (
            nested.get("pull_requests", [])
            if isinstance(nested, dict)
            else list[object]()
        )
    if not isinstance(prs, list):
        raise TypeError("invalid pull requests")
    return tuple(Invalidation("pr", _object_number(pr), components) for pr in prs[:100])


def freshness(
    complete: bool, stale_reason: str | None, expires_at: str | None, now: datetime
) -> str:
    """Derive current freshness from stored observation metadata."""
    if stale_reason:
        return stale_reason
    if not complete or expires_at is None:
        return "unknown"
    return "fresh" if now < datetime.fromisoformat(expires_at) else "expired"


def expiry(observed_at: datetime) -> str:
    """Give a complete temporary observation a five-minute lifetime."""
    return (observed_at.astimezone(UTC) + timedelta(minutes=5)).isoformat()


def can_complete(captured_generation: int, current_generation: int) -> bool:
    """Fence a repair against an intervening invalidation."""
    return captured_generation == current_generation


def invalidate_component(
    generation: int, sources: tuple[str, ...], delivery_id: str
) -> tuple[int, tuple[str, ...]]:
    """Advance a component and retain bounded provenance."""
    return generation + 1, (*sources[-31:], delivery_id)
