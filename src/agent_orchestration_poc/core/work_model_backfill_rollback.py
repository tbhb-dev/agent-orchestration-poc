"""Pure reversal decisions for verified work model writes."""

import json
from dataclasses import asdict, replace
from typing import Any, cast
from urllib.parse import quote, unquote

from agent_orchestration_poc.core.work_model_backfill import Snapshot, complete
from agent_orchestration_poc.core.work_model_backfill_executor import (
    Action,
    ProjectMetadata,
    Record,
    _project_field_query,
    validate_progress,
)

PROJECT_ITEMS = "orgs/tbhb-dev/projectsV2/1/items"


def rollback_plan(
    cp1: Snapshot,
    current: Snapshot,
    actions: tuple[Action, ...],
    records: tuple[Record, ...],
    metadata: ProjectMetadata,
) -> tuple[Action, ...]:
    """Reverse only verified writes, retaining their saved identities."""
    if (
        not complete(cp1)
        or not complete(current)
        or cp1.version != current.version
        or cp1.branch_sha != current.branch_sha
    ):
        raise ValueError("rollback checkpoint or retained branch changed")
    by_id = {action.id: action for action in actions}
    if len(by_id) != len(actions):
        raise ValueError("duplicate forward action")
    phases: dict[str, list[str]] = {}
    details: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in records:
        if record.phase == "complete":
            continue
        if record.action_id not in by_id:
            raise ValueError("unknown forward operation")
        phases.setdefault(record.action_id, []).append(record.phase)
        if record.phase == "verified":
            details[record.action_id] = record.detail
            order.append(record.action_id)
    if any(values[-1] != "verified" for values in phases.values()):
        raise ValueError("forward write has no verified read-back")
    if len(order) != len(set(order)):
        raise ValueError("duplicate forward verification")
    return tuple(
        inverse_action(by_id[action_id], details[action_id], metadata)
        for action_id in reversed(order)
        if by_id[action_id].kind != "trial_remove"
        and not (by_id[action_id].kind == "trial_add" and "3:remove:149:96" in details)
    )


def inverse_action(
    action: Action, detail: dict[str, Any], metadata: ProjectMetadata
) -> Action:
    """Build the exact opposite write from a saved forward action."""
    result = replace(
        action,
        id=f"rollback:{action.id}",
        step="rollback",
        before=action.after,
        after=action.before,
    )
    value = action.payload or {}
    if action.kind in {
        "comment",
        "pr_state",
        "issue_state",
        "title",
        "body",
        "issue_type",
        "native",
        "issue_create",
    }:
        return _inverse_issue(action, result, detail, value)
    if action.kind in {
        "label_create",
        "label_delete",
        "trial_add",
        "trial_remove",
        "blocker",
        "parent",
    }:
        return _inverse_relation(action, result, value)
    return _inverse_project(action, result, detail, value, metadata)


def _inverse_issue(
    action: Action, result: Action, detail: dict[str, Any], value: dict[str, Any]
) -> Action:
    if action.kind == "comment":
        identity = detail.get("comment_id")
        if not identity:
            raise ValueError("comment identity is missing")
        return replace(
            result,
            method="DELETE",
            path=f"issues/comments/{identity}",
            payload={"body": value["body"]},
        )
    if action.kind == "pr_state":
        return replace(
            result,
            method="PATCH",
            payload={"state": cast("tuple[str, bool]", action.before)[0]},
        )
    if action.kind == "issue_state":
        state, reason = cast("tuple[str, str]", action.before)
        return replace(
            result,
            method="PATCH",
            payload={"state": state, **({"state_reason": reason} if reason else {})},
        )
    if action.kind in {"title", "body", "issue_type"}:
        return replace(
            result,
            method="PATCH",
            payload={
                "type" if action.kind == "issue_type" else action.kind: action.before
                if action.kind != "issue_type"
                else action.before or None
            },
        )
    if action.kind == "native":
        return replace(
            result,
            method="PUT",
            payload={
                "fields": dict(cast("tuple[tuple[str, str], ...]", action.before))
            },
        )
    if action.kind == "issue_create":
        created = detail.get("created_item")
        if not isinstance(created, dict) or not created.get("key", "").startswith("#"):
            raise ValueError("created issue identity is missing")
        number = int(created["key"][1:])
        return Action(
            result.id,
            "rollback",
            "issue_state",
            number,
            "PATCH",
            f"issues/{number}",
            {"state": "closed", "state_reason": "not_planned"},
            ("open", ""),
            ("closed", "not_planned"),
        )
    raise ValueError(f"unsupported rollback action: {action.kind}")


def _inverse_relation(action: Action, result: Action, value: dict[str, Any]) -> Action:
    if action.kind == "label_create":
        return replace(
            result,
            method="DELETE",
            path=f"labels/{quote(value['name'], safe='')}",
            payload=value,
            before=action.after,
            after=0,
        )
    if action.kind == "label_delete":
        label = unquote(action.path.rsplit("/", 1)[1])
        return replace(
            result,
            method="POST",
            path=f"issues/{action.number}/labels",
            payload={"labels": [label]},
        )
    if action.kind in {"trial_add", "trial_remove", "blocker"}:
        blocker_id = value.get("issue_id") or action.path.rsplit("/", 1)[1]
        prefix = f"issues/{action.number}/dependencies/blocked_by"
        method = "DELETE" if action.method == "POST" else "POST"
        return replace(
            result,
            kind="blocker"
            if action.kind == "trial_add" and method == "DELETE"
            else result.kind,
            method=method,
            path=f"{prefix}/{blocker_id}" if method == "DELETE" else prefix,
            payload=None if method == "DELETE" else {"issue_id": int(blocker_id)},
        )
    if action.kind == "parent":
        return replace(
            result,
            method="DELETE",
            path=f"issues/{action.number}/sub_issue",
            payload=value,
        )
    raise ValueError(f"unsupported rollback action: {action.kind}")


def _inverse_project(
    action: Action,
    result: Action,
    detail: dict[str, Any],
    value: dict[str, Any],
    metadata: ProjectMetadata,
) -> Action:
    if action.kind in {"draft", "project_item"}:
        identity = detail.get("item_id")
        if not identity:
            raise ValueError("created Project item identity is missing")
        return replace(result, method="DELETE", path=f"{PROJECT_ITEMS}/{identity}")
    if action.kind == "project_fields":
        definitions = {field["name"]: field for field in metadata.fields}
        before = cast("tuple[tuple[str, str], ...]", action.before)
        query = _project_field_query(
            metadata.project["node_id"],
            value["node_id"],
            dict(before),
            definitions,
        )
        return replace(
            result,
            payload={**value, "query": query, "mutation_count": len(before)},
        )
    if action.kind == "draft_body":
        query = (
            "mutation{updateProjectV2DraftIssue(input:{"
            f"draftIssueId:{json.dumps(value['draft_id'])},body:{json.dumps(action.before)}"
            "}){draftIssue{id body}}}"
        )
        return replace(result, payload={**value, "query": query})
    raise ValueError(f"unsupported rollback action: {action.kind}")


def validate_rollback_journal(
    rows: list[dict[str, Any]], run_id: str, actions: tuple[Action, ...]
) -> tuple[Record, ...]:
    """Require the saved inverse plan and ordered durable transitions."""
    if not rows or rows[0] != {"version": 1, "run_id": run_id}:
        raise ValueError("rollback journal header differs from CP1")
    positions = {action.id: index for index, action in enumerate(actions)}
    if len(positions) != len(actions):
        raise ValueError("duplicate rollback action")
    records = tuple(Record(**row) for row in rows[1:])
    index = -1
    phases: list[str] = []
    for record in records:
        current = positions.get(record.action_id, -1)
        if current < index or current < 0 or current > index + 1:
            raise ValueError("rollback journal order differs from plan")
        if current != index:
            if phases and phases[-1] != "verified":
                raise ValueError("rollback journal has an unfinished action")
            phases = []
            index = current
        allowed = (
            ("intent",)
            if not phases
            else ("intent", "response", "verified")
            if phases[-1] == "intent"
            else ("intent", "verified")
            if phases[-1] == "response"
            else ()
        )
        if record.phase not in allowed:
            raise ValueError("rollback journal transition is invalid")
        if record.phase == "intent" and record.detail.get("action") != json.loads(
            json.dumps(asdict(actions[index]))
        ):
            raise ValueError("rollback action changed")
        phases.append(record.phase)
    return records


def validate_rollback_progress(
    cp1: Snapshot,
    current: Snapshot,
    forward_journal: tuple[tuple[Action, ...], tuple[Record, ...]],
    rollback_journal: tuple[tuple[Action, ...], tuple[Record, ...]],
) -> None:
    """Check the full snapshot against forward writes minus saved inverses."""
    forward, forward_records = forward_journal
    inverse, rollback_records = rollback_journal
    verified = {row.action_id for row in rollback_records if row.phase == "verified"}
    pending = next(
        (row.action_id for row in rollback_records if row.action_id not in verified),
        None,
    )
    candidates = (verified, verified | {pending}) if pending else (verified,)
    for undone in candidates:
        removed = {
            action.id.removeprefix("rollback:")
            for action in inverse
            if action.id in undone
        }
        retained = {action.id for action in forward if action.kind == "issue_create"}
        selected = tuple(
            row
            for row in forward_records
            if row.action_id not in removed or row.action_id in retained
        )
        closures = tuple(
            action
            for action in inverse
            if action.id in undone
            and action.kind == "issue_state"
            and action.id.removeprefix("rollback:") in retained
        )
        try:
            validate_progress(
                cp1,
                current,
                (*forward, *closures),
                (
                    *selected,
                    *(Record(action.id, "verified", {}) for action in closures),
                ),
            )
        except ValueError:
            continue
        return
    raise ValueError("checkpoint state drifted outside rollback journals")
