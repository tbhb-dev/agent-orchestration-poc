"""Pure operation and journal decisions for the staged REST backfill."""

from dataclasses import dataclass, replace
from typing import Any, cast

from agent_orchestration_poc.core.work_model_backfill import (
    Item,
    Snapshot,
    Step,
    Tables,
    _draft_body,
    complete,
)

JOURNAL_VERSION = 1
MIN_WRITE_INTERVAL = 8.0


@dataclass(frozen=True)
class Action:
    """One write with exact before and after read-back values."""

    id: str
    step: str
    kind: str
    number: int
    method: str
    path: str
    payload: dict[str, Any] | None
    before: object
    after: object


@dataclass(frozen=True)
class Record:
    """One durable journal transition for an operation."""

    action_id: str
    phase: str
    detail: dict[str, Any]


def closure_actions(
    tables: Tables, cp1: Snapshot, plan: tuple[Step, ...], run_id: str
) -> tuple[Action, ...]:
    """Derive issue closure writes from the validated pure plan."""
    stage = next(step for step in plan if step.number == "0")
    rows = {row["number"]: row for row in tables.assignments if row["number"]}
    items = {item.key: item for item in cp1.items}
    actions = []
    for number in stage.targets:
        row = rows[number]
        issue = items[f"#{number}"]
        comment_id = f"0:comment:{number}"
        marker = f"<!-- work-model-backfill:{run_id}:{comment_id} -->"
        body = f"Folded into {row['fold into']}.\n\n{marker}"
        actions.extend(
            (
                Action(
                    comment_id,
                    "0",
                    "comment",
                    int(number),
                    "POST",
                    f"issues/{number}/comments",
                    {"body": body},
                    0,
                    1,
                ),
                Action(
                    f"0:close:{number}",
                    "0",
                    "issue_state",
                    int(number),
                    "PATCH",
                    f"issues/{number}",
                    {"state": "closed", "state_reason": "not_planned"},
                    (issue.state, issue.state_reason),
                    ("closed", "not_planned"),
                ),
            )
        )
    return tuple(actions)


def draft_actions(
    tables: Tables, cp1: Snapshot, plan: tuple[Step, ...]
) -> tuple[Action, ...]:
    """Create only unmatched planned drafts, in the stage-six plan order."""
    stage = next(step for step in plan if step.number == "6")
    existing = {item.key for item in cp1.items}
    rows = {
        f"title:{row['title']}": row for row in tables.assignments if not row["number"]
    }
    return tuple(
        Action(
            f"6:draft:{key}",
            "6",
            "draft",
            0,
            "POST",
            "orgs/tbhb-dev/projectsV2/1/drafts",
            {"title": rows[key]["title"], "body": _draft_body(rows[key], "")},
            (0, ""),
            (1, _draft_body(rows[key], "")),
        )
        for key in stage.targets
        if key.startswith("title:") and key not in existing
    )


def stage_actions(
    stage: str,
    closures: tuple[Action, ...],
    drafts: tuple[Action, ...],
    records: tuple[Record, ...],
) -> tuple[Action, ...]:
    """Select actions admitted by the completed prior stage."""
    if stage == "0":
        return closures
    if stage != "6:drafts":
        raise ValueError("unsupported backfill stage")
    verified = {record.action_id for record in records if record.phase == "verified"}
    if any(action.id not in verified for action in closures):
        raise ValueError("stage 0 must be verified before draft creation")
    return drafts


def comment_observation(
    comments: list[dict[str, Any]], body: str
) -> tuple[int, int | None]:
    """Retain the identity only when the marked comment is unique."""
    matches = [comment for comment in comments if comment["body"] == body]
    return len(matches), matches[0]["id"] if len(matches) == 1 else None


def draft_observation(
    items: list[dict[str, Any]], title: str
) -> tuple[int, str, str | None, str | None]:
    """Count matching drafts and retain both returned identities."""
    matches = [
        item
        for item in items
        if item["content_type"] == "DraftIssue" and item["content"]["title"] == title
    ]
    if len(matches) != 1:
        return len(matches), "", None, None
    item = matches[0]
    return (
        1,
        item["content"].get("body") or "",
        str(item["id"]),
        str(item["content"]["id"]),
    )


def observation_value(action: Action, observed: object) -> object:
    """Compare comment cardinality while retaining its numeric identity."""
    if isinstance(observed, tuple) and action.kind == "comment":
        return observed[0]
    if isinstance(observed, tuple) and action.kind == "draft":
        return observed[:2]
    return observed


def verified_detail(
    action: Action, observed: object, read: dict[str, Any]
) -> dict[str, Any]:
    """Persist a uniquely recovered comment ID with the read-back receipt."""
    detail = {"observed": observation_value(action, observed), "read": read}
    if action.kind == "comment":
        detail["comment_id"] = cast("tuple[int, int | None]", observed)[1]
    if action.kind == "draft":
        identity = cast("tuple[int, str, str | None, str | None]", observed)
        detail["item_id"], detail["draft_id"] = identity[2:]
    return detail


def journal_state(action: Action, records: tuple[Record, ...], observed: object) -> str:
    """Classify a fresh read without replaying an uncertain write."""
    phases = [record.phase for record in records if record.action_id == action.id]
    if any(phase not in {"intent", "response", "verified"} for phase in phases):
        raise ValueError("unknown journal phase")
    if phases and phases[0] != "intent":
        raise ValueError("journal response lacks intent")
    if "verified" in phases and phases[-1] != "verified":
        raise ValueError("journal action changed after verification")
    if (
        action.kind == "draft"
        and isinstance(observed, tuple)
        and not _draft_identity_matches(
            tuple(record for record in records if record.action_id == action.id),
            observed[2],
            observed[3],
        )
    ):
        return "halt"
    observed = observation_value(action, observed)
    if observed == action.after:
        if "verified" in phases:
            return "skip"
        if "intent" in phases:
            return "verify"
        return "halt"
    if observed != action.before or "verified" in phases:
        return "halt"
    return "send"


def _draft_identity_matches(
    records: tuple[Record, ...], item_id: str | None, draft_id: str | None
) -> bool:
    for record in records:
        if (
            record.phase == "response"
            and record.detail.get("id") is not None
            and item_id != str(record.detail["id"])
        ):
            return False
        if (
            record.phase == "response"
            and record.detail.get("draft_id") is not None
            and draft_id != str(record.detail["draft_id"])
        ):
            return False
        if record.phase == "verified":
            for name, actual in (("item_id", item_id), ("draft_id", draft_id)):
                if record.detail.get(name) is not None and actual != str(
                    record.detail[name]
                ):
                    return False
    return True


def write_wait_seconds(now: float, last: float | None, remaining: int | None) -> float:
    """Limit local writes below the documented hourly creation ceiling."""
    if remaining is not None and remaining < 50:
        raise ValueError("primary REST budget is too low for another write")
    return max(0.0, MIN_WRITE_INTERVAL - (now - last)) if last is not None else 0.0


def validate_journal(
    rows: list[dict[str, Any]], run_id: str, actions: tuple[Action, ...]
) -> tuple[Record, ...]:
    """Reject foreign, malformed, or reordered append-only records."""
    if not rows or rows[0] != {"version": JOURNAL_VERSION, "run_id": run_id}:
        raise ValueError("journal header differs from CP1")
    order = {action.id: index for index, action in enumerate(actions)}
    records = tuple(Record(**row) for row in rows[1:])
    last = -1
    for record in records:
        index = order.get(record.action_id, -1)
        if index < last or index < 0:
            raise ValueError("journal action order differs from plan")
        last = index
        if record.phase not in {"intent", "response", "verified"}:
            raise ValueError("invalid journal phase")
    return records


def validate_progress(
    cp1: Snapshot,
    current: Snapshot,
    actions: tuple[Action, ...],
    records: tuple[Record, ...],
) -> None:
    """Refuse drift outside effects of recorded or interrupted operations."""
    if (
        cp1.version != current.version
        or cp1.branch_sha != current.branch_sha
        or not complete(current)
    ):
        raise ValueError("checkpoint collection or retained branch changed")
    _validate_progress_receipts(cp1, current)
    observed = {item.key: item for item in current.items}
    expected = {item.key: item for item in cp1.items}
    created_count = 0
    for action in actions:
        phases = [record.phase for record in records if record.action_id == action.id]
        if action.kind == "draft":
            key = f"title:{cast('dict[str, Any]', action.payload)['title']}"
            created = observed.pop(key, None)
            if (
                phases
                and created is not None
                and (
                    created.state != "draft"
                    or created.title != cast("dict[str, Any]", action.payload)["title"]
                    or created.body != cast("dict[str, Any]", action.payload)["body"]
                    or not created.item_id
                    or not created.draft_id
                    or created.issue_id
                    or not _draft_identity_matches(
                        tuple(
                            record
                            for record in records
                            if record.action_id == action.id
                        ),
                        created.item_id,
                        created.draft_id,
                    )
                )
            ):
                raise ValueError("created draft differs from journal")
            if created is not None and not phases:
                raise ValueError("unrecorded draft appeared")
            if created is None and "verified" in phases:
                raise ValueError("verified draft disappeared")
            if created is not None:
                created_count += 1
            continue
        key = f"#{action.number}"
        if phases and key in expected:
            expected[key] = _progress_item(
                action, expected[key], observed.get(key), phases
            )
    if observed != expected:
        raise ValueError("checkpoint state drifted outside journal")
    _validate_progress_counts(cp1, current, created_count)


def _validate_progress_receipts(cp1: Snapshot, current: Snapshot) -> None:
    if tuple(
        page for page in cp1.pages if page.collection not in {"project", "drafts"}
    ) != tuple(
        page for page in current.pages if page.collection not in {"project", "drafts"}
    ):
        raise ValueError("checkpoint collection or retained branch changed")
    if len({item.key for item in cp1.items}) != len(cp1.items) or len(
        {item.key for item in current.items}
    ) != len(current.items):
        raise ValueError("duplicate checkpoint item key")


def _validate_progress_counts(
    cp1: Snapshot, current: Snapshot, created_count: int
) -> None:
    for collection in ("project", "drafts"):
        before = next(
            page.total_count for page in cp1.pages if page.collection == collection
        )
        after = next(
            page.total_count for page in current.pages if page.collection == collection
        )
        if after != before + created_count:
            raise ValueError("checkpoint collection count drifted outside journal")


def _progress_item(
    action: Action, original: Item, current: object, phases: list[str]
) -> Item:
    if action.kind != "issue_state":
        return original
    changed = replace(original, state="closed", state_reason="not_planned")
    return changed if "verified" in phases or current == changed else original
