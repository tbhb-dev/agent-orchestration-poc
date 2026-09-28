"""Pure operation and journal decisions for the staged REST backfill."""

import json
from dataclasses import dataclass, replace
from typing import Any, cast

from agent_orchestration_poc.core.work_model_backfill import (
    Item,
    Snapshot,
    Step,
    Tables,
    _draft_body,
    _rest_project_fields,
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


@dataclass(frozen=True)
class ProjectMetadata:
    """REST identities and options needed to address GraphQL Project fields."""

    project: dict[str, Any]
    fields: list[dict[str, Any]]
    items: list[dict[str, Any]]


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


def membership_actions(cp1: Snapshot, plan: tuple[Step, ...]) -> tuple[Action, ...]:
    """Add only numbered issues absent from the new Project."""
    stage = next(step for step in plan if step.number == "6")
    items = {item.key: item for item in cp1.items}
    return tuple(
        Action(
            f"6:item:{number}",
            "6",
            "project_item",
            int(number),
            "POST",
            "orgs/tbhb-dev/projectsV2/1/items",
            {"type": "Issue", "id": int(items[f"#{number}"].issue_id)},
            (0, items[f"#{number}"].issue_id),
            (1, items[f"#{number}"].issue_id),
        )
        for number in stage.targets
        if number.isdigit() and not items[f"#{number}"].item_id
    )


def project_field_actions(
    tables: Tables,
    cp1: Snapshot,
    metadata: ProjectMetadata,
    reviewed_status: dict[str, str] | None = None,
) -> tuple[Action, ...]:
    """Batch changed Project fields per existing CP1 item with reviewed IDs."""
    definitions = {field["name"]: field for field in metadata.fields}
    items = {item.key: item for item in cp1.items if item.item_id}
    nodes = {str(item["id"]): item["node_id"] for item in metadata.items}
    actions = []
    for row in tables.assignments:
        key = f"#{row['number']}" if row["number"] else f"title:{row['title']}"
        if key not in items:
            continue
        item = items[key]
        targets = {"Status": (reviewed_status or {}).get(key, row["project status"])}
        if row["number"]:
            targets.update(
                Size=row["size"],
                Area=row["project area"],
                Harness=row["project harness"],
                Worker=row["project worker"],
            )
        before = dict(item.project)
        changed = {
            name: value
            for name, value in targets.items()
            if before.get(name, "") != value
        }
        if not changed:
            continue
        if item.item_id not in nodes or not metadata.project.get("node_id"):
            raise ValueError("Project item node identity is missing")
        query = _project_field_query(
            metadata.project["node_id"], nodes[item.item_id], changed, definitions
        )
        actions.append(
            Action(
                f"6:fields:{key}",
                "6",
                "project_fields",
                int(row["number"] or 0),
                "POST",
                "graphql",
                {
                    "query": query,
                    "key": key,
                    "item_id": item.item_id,
                    "node_id": nodes[item.item_id],
                    "mutation_count": len(changed),
                },
                tuple(sorted((name, before.get(name, "")) for name in targets)),
                tuple(sorted(targets.items())),
            )
        )
    return tuple(actions)


def project_fields_observation(
    raw_items: list[dict[str, Any]], action: Action
) -> tuple[tuple[str, str], ...]:
    """Read exactly the targeted fields from the same Project item identity."""
    payload = cast("dict[str, Any]", action.payload)
    matches = [item for item in raw_items if str(item["id"]) == payload["item_id"]]
    if len(matches) != 1:
        raise ValueError("Project item identity changed")
    item = matches[0]
    key = (
        f"#{item['content']['number']}"
        if item["content_type"] == "Issue"
        else f"title:{item['content']['title']}"
    )
    if key != payload["key"] or item["node_id"] != payload["node_id"]:
        raise ValueError("Project item content changed")
    actual = dict(_rest_project_fields(item))
    return tuple(
        (name, actual.get(name, ""))
        for name, _ in cast("tuple[tuple[str, str], ...]", action.after)
    )


def graphql_field_receipt(action: Action, response: object) -> None:
    """Require every aliased mutation to return the intended Project item."""
    payload = cast("dict[str, Any]", action.payload)
    if not isinstance(response, dict) or response.get("errors"):
        raise ValueError("GraphQL Project field batch failed")
    data = response.get("data")
    if not isinstance(data, dict) or set(data) != {
        f"f{index}" for index in range(payload["mutation_count"])
    }:
        raise ValueError("GraphQL Project field batch is incomplete")
    if any(
        not isinstance(result, dict)
        or (result.get("projectV2Item") or {}).get("id") != payload["node_id"]
        for result in data.values()
    ):
        raise ValueError("GraphQL Project item identity changed")


def _project_field_query(
    project_id: str,
    item_id: str,
    changes: dict[str, str],
    definitions: dict[str, dict[str, Any]],
) -> str:
    operations = []
    for index, (name, value) in enumerate(changes.items()):
        definition = definitions.get(name)
        if not definition or not definition.get("node_id"):
            raise ValueError(f"Project field definition is missing: {name}")
        args = (
            f"projectId:{json.dumps(project_id)},itemId:{json.dumps(item_id)},"
            f"fieldId:{json.dumps(definition['node_id'])}"
        )
        if not value:
            mutation = f"clearProjectV2ItemFieldValue(input:{{{args}}})"
        elif definition["data_type"] == "text":
            mutation = f"updateProjectV2ItemFieldValue(input:{{{args},value:{{text:{json.dumps(value)}}}}})"
        elif definition["data_type"] == "single_select":
            matches = [
                option["id"]
                for option in definition["options"]
                if option["name"]["raw"] == value
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"Project option is missing or ambiguous: {name}={value}"
                )
            mutation = f"updateProjectV2ItemFieldValue(input:{{{args},value:{{singleSelectOptionId:{json.dumps(matches[0])}}}}})"
        else:
            raise ValueError(f"unsupported Project field type: {name}")
        operations.append(f"f{index}:{mutation}{{projectV2Item{{id}}}}")
    return "mutation{" + " ".join(operations) + "}"


def stage_actions(
    stage: str,
    actions: tuple[Action, ...],
    records: tuple[Record, ...],
) -> tuple[Action, ...]:
    """Select actions admitted by the completed prior stage."""
    closures = tuple(action for action in actions if action.step == "0")
    memberships = tuple(action for action in actions if action.kind == "project_item")
    drafts = tuple(action for action in actions if action.kind == "draft")
    project_fields = tuple(
        action for action in actions if action.kind == "project_fields"
    )
    if stage == "0":
        return closures
    if stage not in {"6:items", "6:drafts", "6:fields"}:
        raise ValueError("unsupported backfill stage")
    verified = {record.action_id for record in records if record.phase == "verified"}
    if any(action.id not in verified for action in closures):
        raise ValueError("stage 0 must be verified before stage 6")
    if stage == "6:items":
        return memberships
    if any(action.id not in verified for action in memberships):
        raise ValueError("Project membership must be verified before draft creation")
    if stage == "6:drafts":
        return drafts
    if any(action.id not in verified for action in drafts):
        raise ValueError("draft creation must be verified before Project fields")
    return project_fields


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


def membership_observation(
    items: list[dict[str, Any]], number: int, issue_id: str
) -> tuple[int, str, str | None, tuple[tuple[str, str], ...]]:
    """Retain the item ID and fields only for one matching issue."""
    matches = [
        item
        for item in items
        if item["content_type"] == "Issue" and item["content"]["number"] == number
    ]
    if len(matches) != 1:
        return len(matches), issue_id, None, ()
    item = matches[0]
    if str(item["content"]["id"]) != issue_id:
        return 1, str(item["content"]["id"]), None, ()
    fields = _rest_project_fields(item)
    return 1, issue_id, str(item["id"]), fields


def observation_value(action: Action, observed: object) -> object:
    """Compare comment cardinality while retaining its numeric identity."""
    if isinstance(observed, tuple) and action.kind == "comment":
        return observed[0]
    if isinstance(observed, tuple) and action.kind == "draft":
        return observed[:2]
    if isinstance(observed, tuple) and action.kind == "project_item":
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
    if action.kind == "project_item":
        identity = cast(
            "tuple[int, str, str | None, tuple[tuple[str, str], ...]]", observed
        )
        detail["item_id"], detail["project_fields"] = identity[2:]
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
    if not _observed_identity_matches(action, records, observed):
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


def _observed_identity_matches(
    action: Action, records: tuple[Record, ...], observed: object
) -> bool:
    if not isinstance(observed, tuple):
        return True
    own = tuple(record for record in records if record.action_id == action.id)
    if action.kind == "draft":
        return _draft_identity_matches(own, observed[2], observed[3])
    if action.kind == "project_item":
        return (observed[0] != 1 or bool(observed[2])) and _item_identity_matches(
            own, observed[2]
        )
    return True


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


def _item_identity_matches(records: tuple[Record, ...], item_id: str | None) -> bool:
    return all(
        item_id == str(record.detail["id"])
        for record in records
        if record.phase == "response" and record.detail.get("id") is not None
    ) and all(
        item_id == str(record.detail["item_id"])
        for record in records
        if record.phase == "verified" and record.detail.get("item_id") is not None
    )


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
    planned = {action.id: action for action in actions}
    records = tuple(Record(**row) for row in rows[1:])
    last = -1
    for record in records:
        index = order.get(record.action_id, -1)
        if index < last or index < 0:
            raise ValueError("journal action order differs from plan")
        last = index
        if record.phase not in {"intent", "response", "verified"}:
            raise ValueError("invalid journal phase")
        if (
            record.phase == "intent"
            and "payload" in record.detail
            and record.detail["payload"] != planned[record.action_id].payload
        ):
            raise ValueError("journal write payload differs from plan")
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
    created_drafts = 0
    created_memberships = 0
    for action in actions:
        phases = [record.phase for record in records if record.action_id == action.id]
        if action.kind == "draft":
            created_drafts += _draft_progress(action, observed, records)
            continue
        if action.kind == "project_item":
            key = f"#{action.number}"
            expected[key] = _project_item_progress(
                action, expected[key], observed[key], records
            )
            created_memberships += bool(expected[key].item_id)
            continue
        key = f"#{action.number}"
        if action.kind == "project_fields":
            key = cast("dict[str, Any]", action.payload)["key"]
        if phases and key in expected:
            expected[key] = _progress_item(
                action, expected[key], observed.get(key), phases
            )
    if observed != expected:
        raise ValueError("checkpoint state drifted outside journal")
    _validate_progress_counts(cp1, current, created_drafts, created_memberships)


def _draft_progress(
    action: Action, observed: dict[str, Item], records: tuple[Record, ...]
) -> int:
    payload = cast("dict[str, Any]", action.payload)
    created = observed.pop(f"title:{payload['title']}", None)
    own = tuple(record for record in records if record.action_id == action.id)
    if (
        own
        and created is not None
        and (
            created.state != "draft"
            or created.title != payload["title"]
            or created.body != payload["body"]
            or not created.item_id
            or not created.draft_id
            or created.issue_id
            or not _draft_identity_matches(own, created.item_id, created.draft_id)
        )
    ):
        raise ValueError("created draft differs from journal")
    if created is not None and not own:
        raise ValueError("unrecorded draft appeared")
    if created is None and any(record.phase == "verified" for record in own):
        raise ValueError("verified draft disappeared")
    return int(created is not None)


def _project_item_progress(
    action: Action, original: Item, current: Item, records: tuple[Record, ...]
) -> Item:
    own = tuple(record for record in records if record.action_id == action.id)
    if not own:
        return original
    if not current.item_id and not any(row.phase == "verified" for row in own):
        return original
    if not current.item_id or not _item_identity_matches(own, current.item_id):
        raise ValueError("created Project item differs from journal")
    verified = next((row for row in own if row.phase == "verified"), None)
    if verified and current.project != tuple(
        tuple(pair) for pair in verified.detail["project_fields"]
    ):
        raise ValueError("created Project fields changed")
    return replace(original, item_id=current.item_id, project=current.project)


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
    cp1: Snapshot, current: Snapshot, created_drafts: int, created_memberships: int
) -> None:
    for collection in ("project", "drafts"):
        before = next(
            page.total_count for page in cp1.pages if page.collection == collection
        )
        after = next(
            page.total_count for page in current.pages if page.collection == collection
        )
        increase = created_drafts + (
            created_memberships if collection == "project" else 0
        )
        if after != before + increase:
            raise ValueError("checkpoint collection count drifted outside journal")


def _progress_item(
    action: Action, original: Item, current: object, phases: list[str]
) -> Item:
    if action.kind == "issue_state":
        changed = replace(original, state="closed", state_reason="not_planned")
    elif action.kind == "project_fields":
        fields = {
            **dict(original.project),
            **dict(cast("tuple[tuple[str, str], ...]", action.after)),
        }
        changed = replace(original, project=tuple(sorted(fields.items())))
    else:
        return original
    return changed if "verified" in phases or current == changed else original
