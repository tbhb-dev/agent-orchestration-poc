"""Pure operation and journal decisions for the staged REST backfill."""

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Any, cast
from urllib.parse import quote

from agent_orchestration_poc.core.work_model_backfill import (
    NATIVE_OPTIONS,
    Item,
    Snapshot,
    Step,
    Tables,
    _draft_body,
    _incident_body,
    _parent_body,
    _rest_project_fields,
    complete,
)

JOURNAL_VERSION = 1
MIN_WRITE_INTERVAL = 8.0
STAGES = (
    "0",
    "3:trial",
    "4:labels",
    "6:items",
    "6:drafts",
    "6:fields",
    "6:new-fields",
    "6:body",
    "6:native",
    "6T",
    "9:create",
    "9:native",
    "9:items",
    "9:fields",
    "9:close",
    "10",
    "11:links",
    "11:bodies",
    "12:create",
    "12:native",
    "12:items",
    "12:fields",
    "15",
)


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


@dataclass(frozen=True)
class WriteContext:
    """Plain inputs for one materialized plan stage."""

    tables: Tables
    cp1: Snapshot
    current: Snapshot
    plan: tuple[Step, ...]
    metadata: ProjectMetadata
    reviewed_status: dict[str, str] | None
    reviewed_bodies: dict[str, str]
    reviewed_labels: tuple[dict[str, str], ...] = ()
    existing_labels: tuple[dict[str, Any], ...] = ()
    verdicts: dict[str, dict[str, Any]] | None = None
    verdict_comments: dict[str, list[dict[str, Any]]] | None = None


def confirmed_cp13(
    stage: str,
    data: bytes | None,
    confirmation: str | None,
    digests: dict[str, str],
) -> dict[str, Any] | None:
    """Validate the operator's clean CP13 confirmation for retirement."""
    if stage != "15":
        return None
    if data is None or not confirmation:
        raise ValueError("stage 15 requires confirmed CP13")
    if confirmation != f"CP13:{hashlib.sha256(data).hexdigest()}":
        raise ValueError("operator CP13 confirmation differs from checkpoint")
    checkpoint = json.loads(data)
    if checkpoint.get("differences") != [] or checkpoint.get("digests") != digests:
        raise ValueError("CP13 is not a clean comparison for these tables")
    return cast("dict[str, Any]", checkpoint)


def validate_resume_admission(
    stage: str,
    cp13: Snapshot | None,
    current: Snapshot,
    records: tuple[Record, ...],
    pr_state: tuple[str, bool] | None,
) -> None:
    """Require the confirmed checkpoint and closed PR before later writes."""
    if (
        cp13 is not None
        and not any(row.action_id.startswith("15:") for row in records)
        and replace(cp13, run_state="initial") != current
    ):
        raise ValueError("current state differs from confirmed CP13")
    if stage != "0" and pr_state != ("closed", False):
        raise ValueError("PR 97 is not closed and unmerged")


def recorded_actions(rows: list[dict[str, Any]]) -> tuple[Action, ...]:
    """Recover stable action values after dynamic identities have been written."""
    actions: dict[str, Action] = {}
    for row in rows[1:]:
        if row.get("phase") != "intent" or "action" not in row.get("detail", {}):
            continue
        value = row["detail"]["action"]
        action = Action(
            str(value["id"]),
            str(value["step"]),
            str(value["kind"]),
            int(value["number"]),
            str(value["method"]),
            str(value["path"]),
            cast("dict[str, Any] | None", value["payload"]),
            _tuplify(value["before"]),
            _tuplify(value["after"]),
        )
        if row["action_id"] != action.id:
            raise ValueError("journal action identity changed")
        if action.id in actions and actions[action.id] != action:
            raise ValueError("journal action changed across retry")
        actions[action.id] = action
    return tuple(actions.values())


def _tuplify(value: object) -> object:
    if isinstance(value, list):
        return tuple(_tuplify(item) for item in value)
    return value


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


def pr_closure_actions(run_id: str, reviewed_comment: str) -> tuple[Action, ...]:
    """Save the reviewed size decision before closing PR 97 unmerged."""
    if not reviewed_comment.strip():
        raise ValueError("reviewed PR 97 closure comment is missing")
    marker = f"<!-- work-model-backfill:{run_id}:0:pr-comment:97 -->"
    return (
        Action(
            "0:pr-comment:97",
            "0",
            "comment",
            97,
            "POST",
            "issues/97/comments",
            {"body": f"{reviewed_comment}\n\n{marker}"},
            0,
            1,
        ),
        Action(
            "0:pr-close:97",
            "0",
            "pr_state",
            97,
            "PATCH",
            "pulls/97",
            {"state": "closed"},
            ("open", False),
            ("closed", False),
        ),
    )


def label_definition_actions(
    reviewed: tuple[dict[str, str], ...], existing: tuple[dict[str, Any], ...]
) -> tuple[Action, ...]:
    """Create only missing reviewed label definitions."""
    names = [row["name"] for row in reviewed]
    if len(names) != len(set(names)):
        raise ValueError("duplicate reviewed label definition")
    found = {row["name"]: row for row in existing}
    actions = []
    for row in reviewed:
        name, color, description = row["name"], row["color"], row["description"]
        if name in found:
            if (found[name]["color"].lower(), found[name].get("description") or "") != (
                color.lower(),
                description,
            ):
                raise ValueError(f"existing label definition differs: {name}")
            continue
        actions.append(
            Action(
                f"4:label:{name}",
                "4:labels",
                "label_create",
                0,
                "POST",
                "labels",
                {"name": name, "color": color, "description": description},
                0,
                (name, color.lower(), description),
            )
        )
    return tuple(actions)


def trial_actions(cp1: Snapshot, plan: tuple[Step, ...]) -> tuple[Action, ...]:
    """Add and remove only the absent blocker selected by the plan."""
    trial = next(step for step in plan if step.number == "3")
    if trial.targets != ("149 <- 96",):
        raise ValueError("unreviewed closed-blocker trial")
    items = {item.key: item for item in cp1.items}
    dependent, blocker = items["#149"], items["#96"]
    if "#96" in dependent.blockers or not blocker.issue_id:
        raise ValueError("trial blocker already exists or has no ID")
    before = tuple(sorted(dependent.blockers))
    after = tuple(sorted((*before, "#96")))
    return (
        Action(
            "3:add:149:96",
            "3:trial",
            "trial_add",
            149,
            "POST",
            "issues/149/dependencies/blocked_by",
            {"issue_id": int(blocker.issue_id)},
            before,
            after,
        ),
        Action(
            "3:remove:149:96",
            "3:trial",
            "trial_remove",
            149,
            "DELETE",
            f"issues/149/dependencies/blocked_by/{blocker.issue_id}",
            None,
            after,
            before,
        ),
    )


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


def native_actions(
    cp1: Snapshot, plan: tuple[Step, ...], stage: str = "6:native"
) -> tuple[Action, ...]:
    """Set an issue type before adding fields pinned to that type."""
    writes = next(
        step.native_writes for step in plan if step.number == stage.split(":")[0]
    )
    items = {item.key: item for item in cp1.items}
    actions = []
    for write in writes:
        if write.key not in items or not items[write.key].issue_id:
            continue
        item = items[write.key]
        number = int(write.key.removeprefix("#"))
        if item.issue_type != write.issue_type:
            actions.append(
                Action(
                    f"{stage}:type:{write.key}",
                    stage,
                    "issue_type",
                    number,
                    "PATCH",
                    f"issues/{number}",
                    {"type": write.issue_type},
                    item.issue_type,
                    write.issue_type,
                )
            )
        before = {**dict.fromkeys(NATIVE_OPTIONS, ""), **dict(item.native)}
        after = {**dict.fromkeys(before, ""), **dict(write.fields)}
        if before != after:
            method = (
                "PUT"
                if any(value and not after[name] for name, value in before.items())
                else "POST"
            )
            actions.append(
                Action(
                    f"{stage}:native:{write.key}",
                    stage,
                    "native",
                    number,
                    method,
                    f"issues/{number}/issue-field-values",
                    {"fields": dict(write.fields)},
                    tuple(sorted(before.items())),
                    tuple(sorted(after.items())),
                )
            )
    return tuple(actions)


def native_field_payload(
    action: Action, definitions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Resolve reviewed native field names to current organization IDs."""
    fields = {field["name"]: field for field in definitions}
    requested = cast("dict[str, str]", cast("dict[str, Any]", action.payload)["fields"])
    entries = []
    for name, value in requested.items():
        if not value:
            continue
        definition = fields.get(name)
        if not definition or definition.get("data_type") != "single_select":
            raise ValueError(f"native issue field definition is missing: {name}")
        if sum(option["name"] == value for option in definition["options"]) != 1:
            raise ValueError(f"native issue field option is missing: {name}={value}")
        entries.append({"field_id": definition["id"], "value": value})
    return {"issue_field_values": entries}


def _issue_for_title(current: Snapshot, title: str) -> Item | None:
    matches = [item for item in current.items if item.issue_id and item.title == title]
    if len(matches) > 1:
        raise ValueError(f"duplicate issue title: {title}")
    return matches[0] if matches else None


def _resolved_issue(current: Snapshot, value: str) -> Item:
    if value.isdigit():
        matches = [item for item in current.items if item.key == f"#{value}"]
        if len(matches) != 1:
            raise ValueError(f"unresolved issue number: {value}")
        return matches[0]
    match = _issue_for_title(current, value)
    if match is None:
        raise ValueError(f"unresolved issue title: {value}")
    return match


def creation_actions(
    tables: Tables, current: Snapshot, plan: tuple[Step, ...], stage: str
) -> tuple[Action, ...]:
    """Plan unique parent or incident creation using reviewed table bodies."""
    number = stage.split(":")[0]
    targets = next(step.targets for step in plan if step.number == number)
    parent_rows = {row["proposed title"]: row for row in tables.parents}
    incident_rows = {
        f"title:{row['title']}": row
        for row in tables.assignments
        if row["backfill mode"] == "issue"
    }
    actions = []
    for index, target in enumerate(targets):
        row = parent_rows[target] if number == "9" else incident_rows[target]
        title = target if number == "9" else row["title"]
        body = _parent_body(row) if number == "9" else _incident_body(row)
        existing = _issue_for_title(current, title)
        if existing is not None:
            if existing.body != body or existing.issue_type != row["issue type"]:
                raise ValueError(f"created issue title conflicts: {title}")
            continue
        actions.append(
            Action(
                f"{number}:create:{index:03}:{title}",
                stage,
                "issue_create",
                0,
                "POST",
                "issues",
                {"title": title, "body": body, "type": row["issue type"]},
                0,
                1,
            )
        )
    return tuple(actions)


def created_native_actions(
    current: Snapshot, plan: tuple[Step, ...], stage: str
) -> tuple[Action, ...]:
    """Add pinned native values to created issues after identity read-back."""
    number = stage.split(":")[0]
    writes = next(step.native_writes for step in plan if step.number == number)
    actions = []
    for index, write in enumerate(writes):
        title = write.key.removeprefix("title:")
        issue = _issue_for_title(current, title)
        if issue is None:
            raise ValueError(f"created issue is missing: {title}")
        before = {**dict.fromkeys(NATIVE_OPTIONS, ""), **dict(issue.native)}
        after = {**dict.fromkeys(before, ""), **dict(write.fields)}
        if before == after:
            continue
        method = (
            "PUT"
            if any(value and not after[name] for name, value in before.items())
            else "POST"
        )
        actions.append(
            Action(
                f"{number}:native:{index:03}:{title}",
                stage,
                "native",
                int(issue.key[1:]),
                method,
                f"issues/{issue.key[1:]}/issue-field-values",
                {"fields": dict(write.fields)},
                tuple(sorted(before.items())),
                tuple(sorted(after.items())),
            )
        )
    return tuple(actions)


def created_membership_actions(
    current: Snapshot, plan: tuple[Step, ...], stage: str
) -> tuple[Action, ...]:
    """Add each newly created issue to the Project at most once."""
    number = stage.split(":")[0]
    targets = next(step.targets for step in plan if step.number == number)
    actions = []
    for index, target in enumerate(targets):
        title = target.removeprefix("title:")
        issue = _resolved_issue(current, title)
        if issue.item_id:
            continue
        actions.append(
            Action(
                f"{number}:item:{index:03}:{title}",
                stage,
                "project_item",
                int(issue.key[1:]),
                "POST",
                "orgs/tbhb-dev/projectsV2/1/items",
                {"type": "Issue", "id": int(issue.issue_id)},
                (0, issue.issue_id),
                (1, issue.issue_id),
            )
        )
    return tuple(actions)


def created_project_field_actions(
    tables: Tables, current: Snapshot, metadata: ProjectMetadata, stage: str
) -> tuple[Action, ...]:
    """Set Project values for newly created parents and incidents."""
    number = stage.split(":")[0]
    rows = (
        [
            (
                row["proposed title"],
                {"Status": "Done" if row["state"] == "closed" else "Backlog"},
            )
            for row in tables.parents
        ]
        if number == "9"
        else [
            (
                row["title"],
                {
                    "Status": row["project status"],
                    "Size": row["size"],
                    "Area": row["project area"],
                    "Harness": row["project harness"],
                    "Worker": row["project worker"],
                },
            )
            for row in tables.assignments
            if row["backfill mode"] == "issue"
        ]
    )
    definitions = {field["name"]: field for field in metadata.fields}
    nodes = {str(item["id"]): item["node_id"] for item in metadata.items}
    actions = []
    for index, (title, targets) in enumerate(rows):
        issue = _resolved_issue(current, title)
        if not issue.item_id or issue.item_id not in nodes:
            raise ValueError(f"created Project item is missing: {title}")
        before = dict(issue.project)
        changes = {
            name: value
            for name, value in targets.items()
            if before.get(name, "") != value
        }
        if not changes:
            continue
        query = _project_field_query(
            metadata.project["node_id"], nodes[issue.item_id], changes, definitions
        )
        actions.append(
            Action(
                f"{number}:fields:{index:03}:{title}",
                stage,
                "project_fields",
                int(issue.key[1:]),
                "POST",
                "graphql",
                {
                    "query": query,
                    "key": issue.key,
                    "item_id": issue.item_id,
                    "node_id": nodes[issue.item_id],
                    "mutation_count": len(changes),
                },
                tuple(sorted((name, before.get(name, "")) for name in targets)),
                tuple(sorted(targets.items())),
            )
        )
    return tuple(actions)


def parent_close_actions(tables: Tables, current: Snapshot) -> tuple[Action, ...]:
    """Close only planned completed parents after their fields are read back."""
    actions = []
    for index, row in enumerate(tables.parents):
        if row["state"] != "closed":
            continue
        issue = _resolved_issue(current, row["proposed title"])
        if (issue.state, issue.state_reason) == ("closed", "completed"):
            continue
        actions.append(
            Action(
                f"9:close:{index:03}:{row['proposed title']}",
                "9:close",
                "issue_state",
                int(issue.key[1:]),
                "PATCH",
                f"issues/{issue.key[1:]}",
                {"state": "closed", "state_reason": "completed"},
                (issue.state, issue.state_reason),
                ("closed", "completed"),
            )
        )
    return tuple(actions)


def hierarchy_actions(
    tables: Tables, current: Snapshot, plan: tuple[Step, ...]
) -> tuple[Action, ...]:
    """Attach numbered issues and epics to their reviewed native parents."""
    targets = next(step.targets for step in plan if step.number == "10")
    rows = {
        f"#{row['number']}": row["epic"]
        for row in tables.assignments
        if row["number"] and row["epic"]
    }
    rows.update(
        (row["proposed title"], row["parent title"])
        for row in tables.parents
        if row["parent title"]
    )
    actions = []
    for index, target in enumerate(targets):
        child = _resolved_issue(current, target.removeprefix("#"))
        parent = _resolved_issue(current, rows[target])
        if child.parent == parent.key:
            continue
        if child.parent:
            raise ValueError(f"child already has another native parent: {target}")
        actions.append(
            Action(
                f"10:parent:{index:03}:{target}",
                "10",
                "parent",
                int(parent.key[1:]),
                "POST",
                f"issues/{parent.key[1:]}/sub_issues",
                {"sub_issue_id": int(child.issue_id), "child": child.key},
                "",
                parent.key,
            )
        )
    return tuple(actions)


def dependency_actions(
    tables: Tables, current: Snapshot, plan: tuple[Step, ...]
) -> tuple[Action, ...]:
    """Apply reviewed native edge writes and deletions in plan order."""
    targets = set(next(step.targets for step in plan if step.number == "11"))
    actions = []
    planned_blockers: dict[str, set[str]] = {}
    for index, row in enumerate(tables.edges):
        edge = f"{row['dependent']} <- {row['blocker']}"
        if edge not in targets:
            continue
        dependent = _resolved_issue(current, row["dependent"])
        blocker = _resolved_issue(current, row["blocker"])
        values = planned_blockers.setdefault(dependent.key, set(dependent.blockers))
        exists = blocker.key in values
        remove = row["execution"] == "delete"
        if exists == (not remove):
            continue
        before = tuple(sorted(values))
        if remove:
            values.remove(blocker.key)
        else:
            values.add(blocker.key)
        actions.append(
            Action(
                f"11:edge:{index:03}:{edge}",
                "11:links",
                "blocker",
                int(dependent.key[1:]),
                "DELETE" if remove else "POST",
                f"issues/{dependent.key[1:]}/dependencies/blocked_by"
                + (f"/{blocker.issue_id}" if remove else ""),
                None if remove else {"issue_id": int(blocker.issue_id)},
                before,
                tuple(sorted(values)),
            )
        )
    return tuple(actions)


def reviewed_body_actions(
    tables: Tables, current: Snapshot, bodies: dict[str, str]
) -> tuple[Action, ...]:
    """Require reviewed exact replacements for every marked issue body."""
    actions = []
    for row in tables.assignments:
        if row["body revision"] != "required":
            continue
        key = f"#{row['number']}"
        if key not in bodies:
            raise ValueError(f"reviewed body is missing: {key}")
        issue = _resolved_issue(current, row["number"])
        if issue.body == bodies[key]:
            continue
        actions.append(
            Action(
                f"11:body:{row['number']}",
                "11:bodies",
                "body",
                int(row["number"]),
                "PATCH",
                f"issues/{row['number']}",
                {"body": bodies[key]},
                issue.body,
                bodies[key],
            )
        )
    return tuple(actions)


def label_retirement_actions(tables: Tables, current: Snapshot) -> tuple[Action, ...]:
    """Remove saved issue-only class labels one at a time."""
    items = {item.key: item for item in current.items}
    actions = []
    for row in tables.assignments:
        if not row["number"] or not row["old type labels"]:
            continue
        issue = items[f"#{row['number']}"]
        label = row["old type labels"]
        if label not in issue.labels:
            continue
        actions.append(
            Action(
                f"15:label:{row['number']}:{label}",
                "15",
                "label_delete",
                int(row["number"]),
                "DELETE",
                f"issues/{row['number']}/labels/{quote(label, safe='')}",
                None,
                issue.labels,
                tuple(value for value in issue.labels if value != label),
            )
        )
    return tuple(actions)


def retitle_actions(
    cp1: Snapshot,
    plan: tuple[Step, ...],
    tables: Tables,
    verdicts: dict[str, dict[str, Any]] | None = None,
    comments: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[Action, ...]:
    """Retitle only reviewed, nonempty proposal rows."""
    targets = next(step.targets for step in plan if step.number == "6T")
    rows = {row["number"]: row for row in tables.assignments if row["number"]}
    items = {item.key: item for item in cp1.items}
    for number in targets:
        row = rows[number]
        if row["refinement verdict"] != "new verdict required":
            continue
        key = f"#{number}"
        verdict = (verdicts or {}).get(key)
        body_hash = hashlib.sha256(items[key].body.encode()).hexdigest()
        if (
            not verdict
            or verdict.get("title") != row["proposed title"]
            or verdict.get("body_sha256") != body_hash
            or not any(
                comment["id"] == verdict.get("comment_id")
                and (comment.get("user") or {}).get("login") == "tbhb-agent-reviewer"
                and _ready_verdict(comment["body"], body_hash)
                for comment in (comments or {}).get(key, [])
            )
        ):
            raise ValueError(f"new refinement verdict is missing: {key}")
    return tuple(
        Action(
            f"6T:title:{number}",
            "6T",
            "title",
            int(number),
            "PATCH",
            f"issues/{number}",
            {"title": rows[number]["proposed title"]},
            items[f"#{number}"].title,
            rows[number]["proposed title"],
        )
        for number in targets
        if items[f"#{number}"].title != rows[number]["proposed title"]
    )


def _ready_verdict(body: str, digest: str) -> bool:
    lines = body.splitlines()
    return (
        len(lines) >= 2
        and lines[0] == "Issue review: ready"
        and lines[1] == f"Body-SHA256: {digest}"
    )


def draft_body_actions(
    tables: Tables, cp1: Snapshot, metadata: ProjectMetadata
) -> tuple[Action, ...]:
    """Correct an existing copied draft body while preserving its identity."""
    items = {item.key: item for item in cp1.items}
    actions = []
    for row in tables.assignments:
        if row["backfill mode"] != "existing draft":
            continue
        key = f"title:{row['title']}"
        item = items[key]
        body = _draft_body(row, item.body)
        if body == item.body:
            continue
        if not item.draft_id or not item.item_id:
            raise ValueError("existing draft identity is missing")
        matches = [
            raw["content"].get("node_id")
            for raw in metadata.items
            if str(raw["id"]) == item.item_id
            and str(raw["content"]["id"]) == item.draft_id
        ]
        if len(matches) != 1 or not matches[0]:
            raise ValueError("existing draft node identity is missing")
        query = (
            "mutation{updateProjectV2DraftIssue(input:{"
            f"draftIssueId:{json.dumps(matches[0])},body:{json.dumps(body)}"
            "}){draftIssue{id body}}}"
        )
        actions.append(
            Action(
                f"6:body:{key}",
                "6:body",
                "draft_body",
                0,
                "POST",
                "graphql",
                {"query": query, "key": key, "draft_id": matches[0]},
                item.body,
                body,
            )
        )
    return tuple(actions)


def project_field_actions(
    tables: Tables,
    cp1: Snapshot,
    metadata: ProjectMetadata,
    reviewed_status: dict[str, str] | None = None,
    current: Snapshot | None = None,
) -> tuple[Action, ...]:
    """Batch changed Project fields after each planned item has an identity."""
    definitions = {field["name"]: field for field in metadata.fields}
    items = {item.key: item for item in cp1.items if item.item_id}
    if current is not None:
        items.update(
            (item.key, item)
            for item in current.items
            if item.item_id and item.key not in items
        )
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


def new_project_field_actions(
    tables: Tables,
    cp1: Snapshot,
    current: Snapshot,
    metadata: ProjectMetadata,
    reviewed_status: dict[str, str] | None = None,
) -> tuple[Action, ...]:
    """Address fields on stage-six items absent from the initial checkpoint."""
    old = {item.key: item.item_id for item in cp1.items}
    actions = project_field_actions(tables, cp1, metadata, reviewed_status, current)
    return tuple(
        replace(
            action,
            id=action.id.replace("6:fields:", "6:new-fields:"),
            step="6:new-fields",
        )
        for action in actions
        if not old.get(cast("dict[str, Any]", action.payload)["key"])
    )


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
    if stage not in STAGES:
        raise ValueError("unsupported backfill stage")
    selected = tuple(action for action in actions if _matches_stage(action, stage))
    if stage == "0":
        return selected
    verified = {record.action_id for record in records if record.phase == "verified"}
    completed = {
        record.detail["stage"] for record in records if record.phase == "complete"
    }
    for prior in STAGES[: STAGES.index(stage)]:
        prior_actions = tuple(
            action for action in actions if _matches_stage(action, prior)
        )
        if prior not in completed or any(
            action.id not in verified for action in prior_actions
        ):
            description = {
                "6:items": "Project membership",
                "6:drafts": "draft creation",
            }.get(prior, f"stage {prior}")
            raise ValueError(f"{description} must be verified before {stage}")
    if stage in completed and any(action.id not in verified for action in selected):
        raise ValueError("completed stage plan changed")
    return selected


def _matches_stage(action: Action, stage: str) -> bool:
    if stage == "0":
        return action.step == "0"
    if stage == "6:items":
        return action.step == "6" and action.kind == "project_item"
    if stage == "6:drafts":
        return action.step == "6" and action.kind == "draft"
    if stage == "6:fields":
        return action.step == "6" and action.kind == "project_fields"
    return action.step == stage


def ordered_actions(actions: tuple[Action, ...]) -> tuple[Action, ...]:
    """Retain plan order while placing recovered dynamic stages chronologically."""
    return tuple(
        sorted(actions, key=lambda action: STAGES.index(_action_stage(action)))
    )


def merge_planned_actions(
    known: tuple[Action, ...], candidate: tuple[Action, ...]
) -> tuple[Action, ...]:
    """Reject a changed reviewed input for an action already in the journal."""
    saved = {action.id: action for action in known}
    for action in candidate:
        if action.id in saved and saved[action.id] != action:
            raise ValueError(
                f"planned action changed after journal intent: {action.id}"
            )
    return ordered_actions(
        (*known, *(action for action in candidate if action.id not in saved))
    )


def _action_stage(action: Action) -> str:
    if action.step == "6":
        return {
            "project_item": "6:items",
            "draft": "6:drafts",
            "project_fields": "6:fields",
        }[action.kind]
    return action.step


def candidate_actions(stage: str, context: WriteContext) -> tuple[Action, ...]:
    """Materialize the next reviewed stage after prior identities exist."""
    match stage:
        case "3:trial":
            actions = trial_actions(context.cp1, context.plan)
        case "4:labels":
            actions = label_definition_actions(
                context.reviewed_labels, context.existing_labels
            )
        case "6:new-fields":
            actions = new_project_field_actions(
                context.tables,
                context.cp1,
                context.current,
                context.metadata,
                context.reviewed_status,
            )
        case "6:body":
            actions = draft_body_actions(context.tables, context.cp1, context.metadata)
        case "6:native":
            actions = native_actions(context.cp1, context.plan)
        case "6T":
            actions = retitle_actions(
                context.cp1,
                context.plan,
                context.tables,
                context.verdicts,
                context.verdict_comments,
            )
        case "9:create" | "12:create":
            actions = creation_actions(
                context.tables, context.current, context.plan, stage
            )
        case "9:native" | "12:native":
            actions = created_native_actions(context.current, context.plan, stage)
        case "9:items" | "12:items":
            actions = created_membership_actions(context.current, context.plan, stage)
        case _:
            actions = _later_candidate_actions(stage, context)
    return actions


def _later_candidate_actions(stage: str, context: WriteContext) -> tuple[Action, ...]:
    match stage:
        case "9:fields" | "12:fields":
            actions = created_project_field_actions(
                context.tables, context.current, context.metadata, stage
            )
        case "9:close":
            actions = parent_close_actions(context.tables, context.current)
        case "10":
            actions = hierarchy_actions(context.tables, context.current, context.plan)
        case "11:links":
            actions = dependency_actions(context.tables, context.current, context.plan)
        case "11:bodies":
            actions = reviewed_body_actions(
                context.tables, context.current, context.reviewed_bodies
            )
        case "15":
            actions = label_retirement_actions(context.tables, context.current)
        case _:
            actions = ()
    return actions


def comment_observation(
    comments: list[dict[str, Any]], body: str
) -> tuple[int, int | None]:
    """Retain the identity only when the marked comment is unique."""
    matches = [comment for comment in comments if comment["body"] == body]
    return len(matches), matches[0]["id"] if len(matches) == 1 else None


def label_observation(
    labels: list[dict[str, Any]], name: str
) -> tuple[str, str, str, str] | int:
    """Read one exact label definition and its identity."""
    matches = [label for label in labels if label["name"] == name]
    if len(matches) != 1:
        return len(matches)
    label = matches[0]
    return (
        name,
        label["color"].lower(),
        label.get("description") or "",
        str(label["id"]),
    )


def draft_observation(
    items: list[dict[str, Any]], title: str
) -> tuple[int, str, str | None, str | None, tuple[tuple[str, str], ...]]:
    """Count matching drafts and retain both returned identities."""
    matches = [
        item
        for item in items
        if item["content_type"] == "DraftIssue" and item["content"]["title"] == title
    ]
    if len(matches) != 1:
        return len(matches), "", None, None, ()
    item = matches[0]
    return (
        1,
        item["content"].get("body") or "",
        str(item["id"]),
        str(item["content"]["id"]),
        _rest_project_fields(item),
    )


def creation_observation(
    issues: list[dict[str, Any]], payload: dict[str, Any]
) -> tuple[int, Item | None]:
    """Find one issue by title and refuse conflicting content after an uncertain POST."""
    matches = [
        issue
        for issue in issues
        if "pull_request" not in issue and issue["title"] == payload["title"]
    ]
    if len(matches) != 1:
        return len(matches), None
    issue = matches[0]
    if (issue.get("body") or "") != payload["body"] or (issue.get("type") or {}).get(
        "name"
    ) != payload["type"]:
        return 1, None
    return 1, Item(
        f"#{issue['number']}",
        issue["title"],
        issue["state"],
        issue.get("state_reason") or "",
        issue_type=(issue.get("type") or {}).get("name", ""),
        native=tuple(sorted((("Priority", ""), ("Severity", ""), ("Work type", "")))),
        body=issue.get("body") or "",
        labels=tuple(sorted(label["name"] for label in issue["labels"])),
        issue_id=str(issue["id"]),
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
    if isinstance(observed, tuple) and action.kind == "issue_create":
        return observed[0]
    if isinstance(observed, tuple) and action.kind == "label_create":
        return observed[:3]
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
        identity = cast(
            "tuple[int, str, str | None, str | None, tuple[tuple[str, str], ...]]",
            observed,
        )
        detail["item_id"], detail["draft_id"] = identity[2:4]
        payload = cast("dict[str, Any]", action.payload)
        detail["created_item"] = {
            **asdict(
                Item(
                    f"title:{payload['title']}",
                    payload["title"],
                    "draft",
                    project=identity[4],
                    body=payload["body"],
                    item_id=identity[2] or "",
                    draft_id=identity[3] or "",
                )
            ),
        }
    if action.kind == "issue_create":
        created = cast("tuple[int, Item | None]", observed)[1]
        if created is None:
            raise ValueError("created issue identity is missing")
        detail["created_item"] = asdict(created)
        detail["issue_id"] = created.issue_id
    if action.kind == "label_create":
        detail["label_id"] = cast("tuple[str, str, str, str]", observed)[3]
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
    return _journal_transition(
        action, records, phases, observation_value(action, observed)
    )


def _journal_transition(
    action: Action, records: tuple[Record, ...], phases: list[str], observed: object
) -> str:
    if observed == action.after:
        if "verified" in phases:
            return "skip"
        if action.kind == "trial_add" and "response" not in phases:
            return "halt"
        return "verify" if "intent" in phases else "halt"
    if observed != action.before or "verified" in phases:
        return "halt"
    if action.kind == "trial_remove" and not any(
        row.action_id == "3:add:149:96" and row.phase == "verified" for row in records
    ):
        return "halt"
    return "send"


def _observed_identity_matches(
    action: Action, records: tuple[Record, ...], observed: object
) -> bool:
    if not isinstance(observed, tuple):
        return True
    own = tuple(record for record in records if record.action_id == action.id)
    if action.kind == "draft":
        matches = _draft_identity_matches(own, observed[2], observed[3])
    elif action.kind == "issue_create":
        created = cast("tuple[int, Item | None]", observed)[1]
        matches = created is None or _item_identity_matches(own, created.issue_id)
    elif action.kind == "label_create":
        matches = all(
            str(value) == observed[3]
            for record in own
            for value in (
                record.detail.get("id")
                if record.phase == "response"
                else record.detail.get("label_id")
                if record.phase == "verified"
                else None,
            )
            if value is not None
        )
    elif action.kind == "project_item":
        matches = (observed[0] != 1 or bool(observed[2])) and _item_identity_matches(
            own, observed[2]
        )
    else:
        matches = True
    return matches


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
    last_stage = -1
    completed: set[str] = set()
    verified: set[str] = set()
    for record in records:
        if record.phase == "complete":
            stage_index = _completion_stage(record, completed, verified, actions)
            if stage_index < last_stage:
                raise ValueError("journal stage order differs from plan")
            last_stage = stage_index
            completed.add(record.detail["stage"])
            continue
        index = order.get(record.action_id, -1)
        if index < last or index < 0:
            raise ValueError("journal action order differs from plan")
        last = index
        stage_index = STAGES.index(_action_stage(planned[record.action_id]))
        if stage_index < last_stage:
            raise ValueError("journal stage order differs from plan")
        last_stage = stage_index
        if record.phase not in {"intent", "response", "verified"}:
            raise ValueError("invalid journal phase")
        if (
            record.phase == "intent"
            and "payload" in record.detail
            and record.detail["payload"] != planned[record.action_id].payload
        ):
            raise ValueError("journal write payload differs from plan")
        if record.phase == "verified":
            verified.add(record.action_id)
    return records


def _completion_stage(
    record: Record, completed: set[str], verified: set[str], actions: tuple[Action, ...]
) -> int:
    stage = record.detail.get("stage")
    if (
        record.action_id != f"stage:{stage}"
        or stage not in STAGES
        or stage in completed
        or any(
            action.id not in verified
            for action in actions
            if _action_stage(action) == stage
        )
    ):
        raise ValueError("invalid journal stage completion")
    return STAGES.index(stage)


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
    observed = {item.key: item for item in current.items}
    expected = {item.key: item for item in cp1.items}
    if len(observed) != len(current.items) or len(expected) != len(cp1.items):
        raise ValueError("duplicate checkpoint item key")
    for action in actions:
        _apply_progress_action(action, expected, observed, actions, records)
    if observed != expected:
        raise ValueError("checkpoint state drifted outside journal")


def _apply_progress_action(
    action: Action,
    expected: dict[str, Item],
    observed: dict[str, Item],
    actions: tuple[Action, ...],
    records: tuple[Record, ...],
) -> None:
    phases = [record.phase for record in records if record.action_id == action.id]
    if action.kind in {"draft", "issue_create"}:
        created = (
            _draft_progress(action, observed, records)
            if action.kind == "draft"
            else _issue_progress(action, observed, records)
        )
        if created is not None:
            expected[created.key] = created
        return
    key = f"#{action.number}"
    if action.kind == "project_item":
        expected[key] = _project_item_progress(
            action,
            expected[key],
            observed[key],
            records,
            allow_fields=any(
                other.kind == "project_fields"
                and cast("dict[str, Any]", other.payload)["key"] == key
                and any(row.action_id == other.id for row in records)
                for other in actions
            ),
        )
        return
    if action.kind in {"project_fields", "draft_body"}:
        key = cast("dict[str, Any]", action.payload)["key"]
    if action.kind == "parent":
        key = cast("dict[str, Any]", action.payload)["child"]
    if phases and key in expected:
        expected[key] = _progress_item(action, expected[key], observed.get(key), phases)


def _draft_progress(
    action: Action, observed: dict[str, Item], records: tuple[Record, ...]
) -> Item | None:
    payload = cast("dict[str, Any]", action.payload)
    created = observed.get(f"title:{payload['title']}")
    own = tuple(record for record in records if record.action_id == action.id)
    if (
        own
        and created is not None
        and (
            created.state != "draft"
            or created.title != payload["title"]
            or (
                not any(record.phase == "verified" for record in own)
                and created.body != payload["body"]
            )
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
    if created is None:
        return None
    saved = next(
        (
            record.detail.get("created_item")
            for record in own
            if record.phase == "verified"
        ),
        None,
    )
    return _saved_item(saved) if saved else created


def _issue_progress(
    action: Action, observed: dict[str, Item], records: tuple[Record, ...]
) -> Item | None:
    payload = cast("dict[str, Any]", action.payload)
    matches = [
        item
        for item in observed.values()
        if item.issue_id and item.title == payload["title"]
    ]
    if len(matches) > 1:
        raise ValueError("created issue title is ambiguous")
    created = matches[0] if matches else None
    own = tuple(record for record in records if record.action_id == action.id)
    if created is not None and not own:
        raise ValueError("unrecorded issue appeared")
    if created is None and any(record.phase == "verified" for record in own):
        raise ValueError("verified issue disappeared")
    if created is None:
        return None
    if created.body != payload["body"] or created.issue_type != payload["type"]:
        raise ValueError("created issue differs from journal")
    if not _item_identity_matches(own, created.issue_id):
        raise ValueError("created issue identity changed")
    saved = next(
        (
            record.detail.get("created_item")
            for record in own
            if record.phase == "verified"
        ),
        None,
    )
    if saved and created.issue_id != str(saved["issue_id"]):
        raise ValueError("created issue identity changed")
    return _saved_item(saved) if saved else created


def _saved_item(value: dict[str, Any]) -> Item:
    value = value.copy()
    for name in ("native", "project", "source_project"):
        value[name] = tuple(tuple(pair) for pair in value[name])
    for name in ("blockers", "labels"):
        value[name] = tuple(value[name])
    return Item(**value)


def _project_item_progress(
    action: Action,
    original: Item,
    current: Item,
    records: tuple[Record, ...],
    *,
    allow_fields: bool = False,
) -> Item:
    own = tuple(record for record in records if record.action_id == action.id)
    if not own:
        return original
    if not current.item_id and not any(row.phase == "verified" for row in own):
        return original
    if not current.item_id or not _item_identity_matches(own, current.item_id):
        raise ValueError("created Project item differs from journal")
    verified = next((row for row in own if row.phase == "verified"), None)
    fields = (
        tuple(tuple(pair) for pair in verified.detail["project_fields"])
        if verified and "project_fields" in verified.detail
        else current.project
    )
    if verified and current.project != fields and not allow_fields:
        raise ValueError("created Project fields changed")
    return replace(original, item_id=current.item_id, project=fields)


def _progress_item(
    action: Action, original: Item, current: object, phases: list[str]
) -> Item:
    if action.kind == "issue_state":
        state, reason = cast("tuple[str, str]", action.after)
        changed = replace(original, state=state, state_reason=reason)
    elif action.kind == "project_fields":
        fields = {
            **dict(original.project),
            **dict(cast("tuple[tuple[str, str], ...]", action.after)),
        }
        changed = replace(original, project=tuple(sorted(fields.items())))
    elif action.kind == "issue_type":
        changed = replace(original, issue_type=cast("str", action.after))
    elif action.kind == "native":
        changed = replace(
            original, native=cast("tuple[tuple[str, str], ...]", action.after)
        )
    elif action.kind == "title":
        changed = replace(original, title=cast("str", action.after))
    elif action.kind in {"body", "draft_body"}:
        changed = replace(original, body=cast("str", action.after))
    elif action.kind == "parent":
        changed = replace(original, parent=cast("str", action.after))
    elif action.kind in {"blocker", "trial_add", "trial_remove"}:
        changed = replace(original, blockers=cast("tuple[str, ...]", action.after))
    elif action.kind == "label_delete":
        changed = replace(original, labels=cast("tuple[str, ...]", action.after))
    else:
        return original
    return changed if "verified" in phases or current == changed else original
