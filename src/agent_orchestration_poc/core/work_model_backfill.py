"""Pure versioned work-model table and initial snapshot contract."""

import csv
import io
import json
from dataclasses import dataclass, replace
from typing import Any

from agent_orchestration_poc.core.workflow_forms import TITLE, Reference, validate_title

VERSION = 1
ISSUE_TYPES = frozenset(
    {"Feature", "Defect", "Chore", "Spike", "Incident", "Epic", "Initiative"}
)
NATIVE_OPTIONS = {
    "Priority": frozenset({"", "Expedite", "Standard", "Intangible"}),
    "Severity": frozenset({"", "SEV1", "SEV2", "SEV3"}),
    "Work type": frozenset({"Planned", "Unplanned"}),
}
VALIDATOR_FIELDS = frozenset({"Validation", "Validation detail"})
SOURCE_PROJECT_FIELDS = (
    "Status",
    "Size",
    "Area",
    "Harness",
    "Worker",
    "Phase",
    "Priority",
)
ASSIGNMENT_COLUMNS = (
    "number",
    "state",
    "title",
    "class",
    "epic",
    "initiative",
    "priority",
    "severity",
    "work type",
    "confidence",
    "note",
    "plan reference",
    "origin",
    "work type v1",
    "issue type",
    "live state",
    "state reason",
    "program",
    "backfill mode",
    "old project item",
    "old project fields",
    "project status",
    "size",
    "project area",
    "project harness",
    "project worker",
    "source",
    "claim status",
    "old type labels",
    "body revision",
    "request snapshot",
    "fold into",
    "proposed title",
    "target project item",
    "target content id",
    "target content node",
    "snapshot disposition",
    "refinement verdict",
)
PARENT_COLUMNS = (
    "kind",
    "proposed title",
    "parent title",
    "goal",
    "finish line",
    "state",
    "issue type",
    "work type",
)
EDGE_COLUMNS = ("dependent", "blocker", "action", "execution")


@dataclass(frozen=True)
class Tables:
    """Parsed approved rows, preserving every column and audit disposition."""

    version: int
    assignments: tuple[dict[str, str], ...]
    parents: tuple[dict[str, str], ...]
    edges: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class Page:
    """A shell-collected collection's pagination receipt."""

    collection: str
    index: int
    count: int
    total_pages: int
    total_count: int


@dataclass(frozen=True)
class Item:
    """Full read-back value for an issue, parent, or Project draft."""

    key: str
    title: str
    state: str
    state_reason: str = ""
    issue_type: str = ""
    native: tuple[tuple[str, str], ...] = ()
    project: tuple[tuple[str, str], ...] = ()
    source_project: tuple[tuple[str, str], ...] = ()
    parent: str = ""
    blockers: tuple[str, ...] = ()
    body: str = ""
    labels: tuple[str, ...] = ()
    issue_id: str = ""
    item_id: str = ""
    draft_id: str = ""


@dataclass(frozen=True)
class Snapshot:
    """CP1 or CP13 values captured by the separate runner shell."""

    version: int
    items: tuple[Item, ...]
    pages: tuple[Page, ...]
    branch_sha: str
    run_state: str = "initial"


@dataclass(frozen=True)
class RestValues:
    """Complete raw REST collections passed across the shell boundary."""

    issues: list[dict[str, Any]]
    issue_pages: tuple[Page, ...]
    old: list[dict[str, Any]]
    project: list[dict[str, Any]]
    project_pages: tuple[Page, ...]
    nested: dict[str, tuple[list[Any], list[Any], list[Any]]]
    nested_pages: tuple[Page, ...]
    branch_sha: str
    run_state: str


@dataclass(frozen=True)
class Step:
    """One ordered runner stage and its reversible checkpoint contract."""

    number: str
    targets: tuple[str, ...]
    calls: tuple[str, ...]
    saved_inputs: tuple[str, ...]
    check: str
    reversal: tuple[str, ...]
    native_writes: tuple[NativeWrite, ...] = ()


@dataclass(frozen=True)
class NativeWrite:
    """Type and only the native fields pinned to that type."""

    key: str
    issue_type: str
    fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Difference:
    """A complete CP13 value that differs from the approved target."""

    key: str
    field: str
    expected: object
    actual: object


@dataclass(frozen=True)
class Rollback:
    """Prewrite values and created identities needed for reviewed reversal."""

    prior: tuple[Item, ...]
    created: tuple[Item, ...]
    order: tuple[str, ...]
    pr_state: str
    branch_sha: str
    exemptions: tuple[str, ...]
    added_items: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class RollbackExtras:
    """Saved exemption and added Project membership records."""

    exemptions: tuple[str, ...] = ()
    added_items: dict[str, str] | None = None


@dataclass(frozen=True)
class TargetInputs:
    """Reviewed post-CP1 identities, bodies, closure proof, and title policy."""

    created: dict[str, Item]
    bodies: dict[str, str]
    closed_at_cp0: frozenset[str]
    revoked: frozenset[str]
    reference: Reference
    added_items: dict[str, str] | None = None
    reviewed_status: dict[str, str] | None = None


@dataclass(frozen=True)
class _TargetContext:
    created: dict[str, Item]
    bodies: dict[str, str]
    links: dict[str, set[str]]
    exemptions: set[str]
    reference: Reference


def project_field_ids(fields: list[dict[str, Any]]) -> tuple[int, ...]:
    """Select the old and new Project fields needed by the snapshot."""
    names = {
        "Status",
        "Size",
        "Area",
        "Harness",
        "Worker",
        "Phase",
        "Priority",
        "Validation",
        "Validation detail",
    }
    return tuple(field["id"] for field in fields if field["name"] in names)


def verify_table_digests(
    digests: dict[str, str], manifest_text: str, *, markdown: bool
) -> None:
    """Require supplied table bytes to match a reviewed manifest."""
    names = ("assignments", "parents", "edges")
    if markdown:
        suffixes = {
            "assignments": ".tsv",
            "parents": "-parents.tsv",
            "edges": "-edges.tsv",
        }
        rows = {}
        for line in manifest_text.splitlines():
            parts = [part.strip().strip("`") for part in line.split("|")]
            if len(parts) >= 5 and parts[1] in suffixes.values():
                rows[parts[1]] = parts[3]
        approved = {name: rows.get(suffix) for name, suffix in suffixes.items()}
    else:
        manifest = json.loads(manifest_text)
        if manifest.get("version") != VERSION:
            raise ValueError("table digest manifest version differs")
        approved = {name: manifest.get(f"{name}_sha256") for name in names}
    if set(digests) != set(names) or any(
        approved[name] != digest for name, digest in digests.items()
    ):
        raise ValueError("table digest manifest differs")


def _rest_field_value(field: dict[str, Any]) -> str:
    value = field.get("value")
    if value is None:
        return ""
    if isinstance(value, dict):
        named = value.get("name") or value.get("raw")
        return str(named.get("raw", "") if isinstance(named, dict) else named or "")
    return str(value)


def _rest_project_fields(item: dict[str, Any] | None) -> tuple[tuple[str, str], ...]:
    if item is None:
        return ()
    names = set(SOURCE_PROJECT_FIELDS) | {"Validation", "Validation detail"}
    return tuple(
        sorted(
            (field["name"], _rest_field_value(field))
            for field in item["fields"]
            if field["name"] in names
        )
    )


def _rest_project_map(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in items:
        content = item.get("content") or {}
        key = (
            f"#{content['number']}"
            if item["content_type"] == "Issue"
            else f"title:{content['title']}"
        )
        if key in result:
            raise ValueError("duplicate Project content")
        result[key] = item
    return result


def snapshot_from_rest(source: RestValues) -> Snapshot:
    """Turn complete REST values into a plain CP1 or CP13 snapshot."""
    issues = [issue for issue in source.issues if "pull_request" not in issue]
    offset = 0
    filtered_pages = []
    for page in source.issue_pages:
        count = sum(
            "pull_request" not in issue
            for issue in source.issues[offset : offset + page.count]
        )
        filtered_pages.append(replace(page, count=count))
        offset += page.count
    if offset != len(source.issues):
        raise ValueError("issue page receipts differ from returned rows")
    if set(source.nested) != {f"#{issue['number']}" for issue in issues}:
        raise ValueError("nested issue reads are incomplete or unexpected")
    filtered_pages = [replace(page, total_count=len(issues)) for page in filtered_pages]
    old_map = _rest_project_map(source.old)
    project_map = _rest_project_map(source.project)
    parents: dict[str, str] = {}
    for key, (_, children, _) in source.nested.items():
        for child in children:
            child_key = f"#{child['number']}"
            if child_key in parents:
                raise ValueError("issue has multiple parents")
            parents[child_key] = key
    items = []
    for issue in issues:
        key = f"#{issue['number']}"
        field_values, _, blockers = source.nested[key]
        returned = {
            entry["issue_field_name"]: (entry.get("single_select_option") or {}).get(
                "name", ""
            )
            for entry in field_values
        }
        native = _pairs({**dict.fromkeys(NATIVE_OPTIONS, ""), **returned})
        new_item = project_map.get(key)
        items.append(
            Item(
                key,
                issue["title"],
                issue["state"],
                issue.get("state_reason") or "",
                issue_type=(issue.get("type") or {}).get("name", ""),
                native=native,
                project=_rest_project_fields(new_item),
                source_project=_rest_project_fields(old_map.get(key)),
                parent=parents.get(key, ""),
                blockers=tuple(sorted(f"#{row['number']}" for row in blockers)),
                body=issue.get("body") or "",
                labels=tuple(sorted(label["name"] for label in issue["labels"])),
                issue_id=str(issue["id"]),
                item_id=str(new_item["id"]) if new_item else "",
            )
        )
    drafts = [item for item in source.project if item["content_type"] == "DraftIssue"]
    for draft in drafts:
        content = draft["content"]
        items.append(
            Item(
                f"title:{content['title']}",
                content["title"],
                "draft",
                project=_rest_project_fields(draft),
                body=content.get("body") or "",
                draft_id=str(content["id"]),
                item_id=str(draft["id"]),
            )
        )
    count = len(issues)
    pages = (
        *filtered_pages,
        *source.project_pages,
        Page("drafts", 1, len(drafts), 1, len(drafts)),
        *(Page(name, 1, count, 1, count) for name in ("native", "parents", "blockers")),
        *source.nested_pages,
    )
    return Snapshot(VERSION, tuple(items), pages, source.branch_sha, source.run_state)


def _rows(
    text: str, required: tuple[str, ...], *, exact: bool = False
) -> tuple[dict[str, str], ...]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t", strict=True)
    if reader.fieldnames is None or (
        tuple(reader.fieldnames) != required
        if exact
        else not set(required) <= set(reader.fieldnames)
    ):
        raise ValueError("table header is incomplete")
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("duplicate table column")
    rows = tuple(dict(row) for row in reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("table row has wrong column count")
    return rows


def parse_tables(assignments: str, parents: str, edges: str) -> Tables:
    """Parse all three supplied TSV values without dropping audit rows."""
    a = _rows(assignments, ASSIGNMENT_COLUMNS, exact=True)
    p = _rows(parents, PARENT_COLUMNS)
    e = _rows(edges, EDGE_COLUMNS)
    numbers = [row["number"] for row in a if row["number"]]
    titles = [row["proposed title"] for row in p]
    draft_titles = [row["title"] for row in a if not row["number"]]
    if len(numbers) != len(set(numbers)) or any(not n.isdecimal() for n in numbers):
        raise ValueError("duplicate or invalid issue number")
    if len(titles) != len(set(titles)) or any(not title for title in titles):
        raise ValueError("duplicate or missing parent title")
    if len(draft_titles) != len(set(draft_titles)):
        raise ValueError("duplicate draft title")
    keys = set(numbers) | set(draft_titles) | set(titles)
    if len(keys) != len(numbers) + len(draft_titles) + len(titles):
        raise ValueError("duplicate edge key")
    if any(row["issue type"] not in ISSUE_TYPES for row in (*a, *p)):
        raise ValueError("unknown native issue type")
    if any(
        row[column] not in options
        for row in (*a, *p)
        for column, options in (
            ("priority", NATIVE_OPTIONS["Priority"]),
            ("severity", NATIVE_OPTIONS["Severity"]),
            ("work type", NATIVE_OPTIONS["Work type"]),
        )
        if column in row
    ):
        raise ValueError("unknown native field option")
    if any(
        row["parent title"] and row["parent title"] not in titles for row in p
    ) or any(row["epic"] and row["epic"] not in titles for row in a):
        raise ValueError("unresolved parent title")
    if any(
        value not in keys
        for row in e
        if _accepted(row)
        for value in (row["dependent"], row["blocker"])
    ):
        raise ValueError("unresolved accepted edge")
    return Tables(VERSION, a, p, e)


def complete(snapshot: Snapshot) -> bool:
    """Require contiguous complete pages for every declared collection."""
    if snapshot.version != VERSION or not snapshot.branch_sha or not snapshot.pages:
        return False
    groups: dict[str, list[Page]] = {}
    for page in snapshot.pages:
        groups.setdefault(page.collection, []).append(page)
    required = {"issues", "project", "drafts", "native", "parents", "blockers"}
    if not required.issubset(groups):
        return False
    pages_complete = all(
        [page.index for page in sorted(pages, key=lambda p: p.index)]
        == list(range(1, pages[0].total_pages + 1))
        and all(
            page.total_pages == pages[0].total_pages
            and page.total_count == pages[0].total_count
            and page.count >= 0
            for page in pages
        )
        and sum(page.count for page in pages) == pages[0].total_count
        for pages in groups.values()
    )
    counts = {name: pages[0].total_count for name, pages in groups.items()}
    issues = sum(bool(item.issue_id) for item in snapshot.items)
    drafts = sum(bool(item.draft_id) for item in snapshot.items)
    project = sum(bool(item.item_id) for item in snapshot.items)
    nested = all(
        counts.get(f"{kind}:{item.key}") == value
        for item in snapshot.items
        if item.issue_id
        for kind, value in (
            ("native", sum(bool(value) for _, value in item.native)),
            ("blockers", len(item.blockers)),
            ("sub_issues", sum(child.parent == item.key for child in snapshot.items)),
        )
    )
    return (
        pages_complete
        and nested
        and counts["issues"] == issues
        and counts["drafts"] == drafts
        and counts["project"] == project
        and all(counts[name] >= issues for name in ("native", "parents", "blockers"))
    )


def _key(row: dict[str, str]) -> str:
    return f"#{row['number']}" if row.get("number") else f"title:{row['title']}"


def _pairs(values: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(values.items()))


def _body_value(body: str, name: str) -> str:
    prefix = f"- {name}: "
    return next(
        (
            line[len(prefix) :].strip()
            for line in body.splitlines()
            if line.startswith(prefix)
        ),
        "",
    )


def _draft_body(row: dict[str, str], prior: str) -> str:
    values = {
        "Class": row["issue type"].lower(),
        "Priority": row["priority"],
        "Work type": row["work type"],
        "Severity": row["severity"] or "none",
        "Size": row["size"],
    }
    lines = [
        line
        for line in prior.splitlines()
        if not any(line.startswith(f"- {name}: ") for name in values)
    ]
    return "\n".join(
        (*lines, *(f"- {name}: {value}" for name, value in values.items()))
    )


def _parent_body(row: dict[str, str]) -> str:
    return f"## Goal\n\n{row['goal']}\n\n## Finish line\n\n{row['finish line']}"


def _incident_body(row: dict[str, str]) -> str:
    return f"## Incident\n\n{row['title']}\n\n## Record\n\n{row['note']}"


def _accepted(edge: dict[str, str]) -> bool:
    return edge["action"].startswith(("exists", "write")) and edge["execution"] in {
        "native",
        "deferred until conversion",
    }


def cycle_nodes(tables: Tables) -> tuple[str, ...]:
    """Return a cycle across native blockers and hierarchy, if one exists."""
    graph = _dependency_graph(tables)
    active: set[str] = set()
    done: set[str] = set()
    for node in sorted(graph):
        if found := _cycle_from(node, (), graph, active, done):
            return found
    return ()


def _dependency_graph(tables: Tables) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for row in tables.edges:
        if _accepted(row):
            graph.setdefault(row["dependent"], set()).add(row["blocker"])
    for row in tables.assignments:
        if row["epic"] and row["number"]:
            graph.setdefault(row["number"], set()).add(row["epic"])
    for row in tables.parents:
        if row["parent title"]:
            graph.setdefault(row["proposed title"], set()).add(row["parent title"])
    return graph


def _cycle_from(
    node: str,
    path: tuple[str, ...],
    graph: dict[str, set[str]],
    active: set[str],
    done: set[str],
) -> tuple[str, ...]:
    if node in active:
        return (*path[path.index(node) :], node)
    if node in done:
        return ()
    active.add(node)
    for next_node in sorted(graph.get(node, ())):
        if found := _cycle_from(next_node, (*path, node), graph, active, done):
            return found
    active.remove(node)
    done.add(node)
    return ()


def validate_cp1(
    tables: Tables, snapshot: Snapshot, reviewed_status: dict[str, str] | None = None
) -> None:
    """Refuse stale, incomplete, duplicate, or already-parented initial reads."""
    if any(
        item.draft_id and item.key != f"title:{item.title}" for item in snapshot.items
    ):
        raise ValueError("draft key and title differ")
    if (
        tables.version != VERSION
        or snapshot.run_state != "initial"
        or not complete(snapshot)
    ):
        raise ValueError("incomplete or incompatible CP1")
    items = {item.key: item for item in snapshot.items}
    if len(items) != len(snapshot.items):
        raise ValueError("duplicate snapshot identity")
    numbers = {_key(row) for row in tables.assignments if row["number"]}
    if {key for key in items if key.startswith("#")} != numbers:
        raise ValueError("unexpected or missing source issue")
    for row in tables.assignments:
        if not row["number"]:
            continue
        _validate_source_issue(
            row, items[_key(row)], (reviewed_status or {}).get(_key(row))
        )
    _validate_drafts(tables, snapshot)
    if cycle := cycle_nodes(tables):
        raise ValueError(f"accepted graph contains a cycle: {cycle}")


def _validate_drafts(tables: Tables, snapshot: Snapshot) -> None:
    drafts = [item for item in snapshot.items if item.draft_id]
    draft_titles = [item.title for item in drafts]
    if len(draft_titles) != len(set(draft_titles)):
        raise ValueError("duplicate existing draft title")
    for row in tables.assignments:
        if row["number"]:
            continue
        present = row["title"] in draft_titles
        if row["backfill mode"] == "existing draft" and not present:
            raise ValueError("unresolved existing draft")
        if present and row["backfill mode"] == "existing draft":
            draft = next(item for item in drafts if item.title == row["title"])
            if _body_value(draft.body, "Class") != row["issue type"].lower() or (
                _body_value(draft.body, "Size") != row["size"]
            ):
                raise ValueError("changed existing draft class or Size")
        if present and (
            (
                row["target project item"]
                and next(item.item_id for item in drafts if item.title == row["title"])
                != row["target project item"]
            )
            or (
                row["target content id"]
                and next(item.draft_id for item in drafts if item.title == row["title"])
                != row["target content id"]
            )
        ):
            raise ValueError("changed existing draft identity")


def _validate_source_issue(
    row: dict[str, str], item: Item, reviewed_status: str | None = None
) -> None:
    if not item.issue_id:
        raise ValueError("unresolved source issue id")
    if item.title not in {row["title"], row["proposed title"]}:
        raise ValueError("missing or changed source issue title")
    if item.state != row["live state"] or item.state_reason != row["state reason"]:
        raise ValueError("changed source issue state")
    if item.parent:
        raise ValueError("initial child already has a parent")
    old_fields: dict[str, str | None] = (
        json.loads(row["old project fields"]) if row["old project fields"] else {}
    )
    expected = (
        _pairs({field: old_fields.get(field) or "" for field in SOURCE_PROJECT_FIELDS})
        if old_fields
        else ()
    )
    if item.source_project != expected:
        raise ValueError("changed source Project values")
    _validate_copied_project(item, old_fields, reviewed_status)
    if row.get("target project item") and item.item_id != row["target project item"]:
        raise ValueError("changed target Project identity")
    if row.get("target content id") and item.issue_id != row["target content id"]:
        raise ValueError("changed target issue identity")


def _validate_copied_project(
    item: Item, old_fields: dict[str, str | None], reviewed_status: str | None
) -> None:
    if not item.item_id or not old_fields:
        return
    copied = {
        name: old_fields.get(name) or ""
        for name in ("Status", "Size", "Area", "Harness", "Worker")
    }
    if reviewed_status is not None:
        copied["Status"] = reviewed_status
    if any(dict(item.project).get(name) != value for name, value in copied.items()):
        raise ValueError("changed copied Project values")


def title_exemptions(  # noqa: PLR0913 - preserve the public manifest inputs.
    tables: Tables,
    cp1: Snapshot,
    closed_at_cp0: frozenset[str],
    revoked: frozenset[str],
    reference: Reference,
    *,
    reviewed_status: dict[str, str] | None = None,
) -> tuple[str, ...]:
    """Derive numbered legacy exemptions only after every planned closure succeeds."""
    validate_cp1(tables, cp1, reviewed_status)
    return _derive_exemptions(tables, cp1, closed_at_cp0, revoked, reference)


def _derive_exemptions(
    tables: Tables,
    cp1: Snapshot,
    closed_at_cp0: frozenset[str],
    revoked: frozenset[str],
    reference: Reference,
) -> tuple[str, ...]:
    planned = {
        row["number"]
        for row in tables.assignments
        if row["number"] and row["live state"] == "open" and row["state"] == "closed"
    }
    if not planned <= closed_at_cp0:
        raise ValueError("planned closure is not confirmed")
    by_key = {item.key: item for item in cp1.items}
    return tuple(
        row["number"]
        for row in tables.assignments
        if row["number"]
        and row["state"] == "closed"
        and row["number"] not in revoked
        and (
            len(by_key[_key(row)].title) > 72
            or validate_title(by_key[_key(row)].title, reference, issue=True)
        )
    )


def title_repairs(tables: Tables, reference: Reference) -> tuple[tuple[str, bool], ...]:
    """Validate every replacement and flag only scope changes for a new verdict."""
    repairs = []
    for row in tables.assignments:
        title = row["proposed title"]
        if not title:
            continue
        if row["state"] != "open" or not row["number"]:
            raise ValueError("replacement is not a numbered open issue")
        if len(title) > 72 or validate_title(title, reference, issue=True):
            raise ValueError("invalid replacement title")
        old_scope = TITLE.fullmatch(row["title"])
        new_scope = TITLE.fullmatch(title)
        changed = bool(
            old_scope and new_scope and old_scope.group(2) != new_scope.group(2)
        )
        if changed != (row["refinement verdict"] == "new verdict required"):
            raise ValueError("scope-change verdict disposition differs")
        repairs.append((row["number"], changed))
    return tuple(repairs)


PLAN_CONTRACT = """1|GET paginated R/issues and R/labels; GET OLD/fields and OLD/items; GET P/fields and P/items; GET org issue types and issue fields; GET R/issues/{n}/issue-field-values, parent, blocked_by; GET R/pulls/97 and retained branch ref; GraphQL query P POSITION|complete CP1, source digests, IDs, bodies, fields, order, PR and branch|CP1 complete and matches assignments before any closure|retain immutable CP1
0|POST R/issues/{n}/comments; PATCH R/issues/{n} closed/not_planned; POST R/issues/97/comments; PATCH R/pulls/97 closed; GET changed issues, comments, PR and retained branch ref|original states, reasons, comment IDs, PR state, branch SHA|only selected closures and PR closed unmerged; branch retained|PATCH saved states and PR state; DELETE only created comments; GET branch
2||reviewed and prior workflow commits|external implementation and enforcement prerequisites checked|restore prior commit through review
3|POST R/issues/149/dependencies/blocked_by with issue_id=id(96); GET R/issues/149/dependencies/blocked_by; DELETE only trial link; GET blockers again|original #149 blocker set and trial result|exact original blocker set restored|DELETE only newly added trial link; GET blockers
4|GET R/labels; POST R/labels only for missing reviewed definitions; GET R/labels|definition IDs, values and previous absence|created definitions match and old definitions unchanged|DELETE only created unused definitions after attachments reverse
5|GET orgs/tbhb-dev/issue-types; GET orgs/tbhb-dev/issue-fields; GET P/fields|definition IDs/options and delegated view export|seven types, native options and retained fields match|owner restores prior view settings
6|GET P/items before writes; POST P/items for absent issue items; POST P/drafts for unmatched drafts; PATCH P/items/{item-id} supported fields; PATCH R/issues/{n} native type; POST R/issues/{n}/issue-field-values pinned fields; GraphQL updateProjectV2DraftIssue for copied D2 body; GET P/items, R/issues and issue-field-values|per-row existing/created IDs, full native fields, P values, draft bodies|CP6 native and P values, draft identities and bodies match|restore saved native fields; restore saved type; restore saved P values and D2 body; delete only created P items after exporting drafts
6T|PATCH R/issues/{n} title only; GET each changed issue; GET scope-change refinement verdict comments|original titles, bodies, verdict records, CP0 closure proof|replacements and verdicts match; exemptions unchanged|with enforcement held, restore only changed titles; GET titles
7|GraphQL query P POSITION; GraphQL updateProjectV2ItemPosition trial move; GraphQL query POSITION; GET P/items REST order; GraphQL restore predecessor; GraphQL query POSITION; GET P/items REST order and rate budget|trial item, predecessor, full order, positions and cost|changed and restored order exact|restore saved predecessor and verify order
8|GraphQL query P POSITION; GraphQL sequential updateProjectV2ItemPosition by approved afterId; GraphQL query P POSITION|operator-approved seed and complete prior order|exact approved relative Standard order|restore complete saved sequence and compare
9|POST R/issues initiatives then epics with type=approved native type; POST R/issues/{n}/issue-field-values Work type; POST P/items; PATCH P/items/{item-id} Status; PATCH completed parents closed/completed; GET issues, issue-field-values and P/items|created issue and item IDs, bodies, closure results|all parents unique with target state, type, Work type and Status|reverse downstream links; close created issues not_planned; remove only created P items
10|POST R/issues/{parent}/sub_issues with resolved sub_issue_id; GET R/issues/{parent}/sub_issues for every parent|original parent or absence and successful attachments|exact numbered hierarchy; no draft native memberships|DELETE only new memberships; restore saved old parent links
11|DELETE R/issues/{dependent}/dependencies/blocked_by/{blocker-id} for reviewed removals; POST R/issues/{dependent}/dependencies/blocked_by for accepted writes; PATCH seven reviewed R/issues/{n} bodies; GET affected blockers and revised issues|original blocker sets, bodies and each operation result|exact accepted links, no cycle, seven body digests|remove only added links; restore only removed old links and saved bodies
12|POST R/issues for incidents with type=Incident; POST R/issues/{n}/issue-field-values pinned fields; POST P/items; PATCH P/items/{item-id} supported fields; GET issues, issue-field-values and P/items|created issue and item IDs, bodies and fields|incident identity, SEV2, type, Work type and P values|close only created incidents not_planned; remove only created P items
13|GET complete R/issues and P/items; GET R/issues/{n}/issue-field-values, sub_issues and blocked_by for every numbered issue|CP13, CP1-CP12, title manifest and operator decision|complete target equality and explicit operator confirmation|withdraw confirmation; pause dispatch; use prior checkpoint inverses
14||prior workflow commit, exemptions, revocations and scheduled-run IDs|external activation after two clean runs and procedure review|restore prior activation through review; retain revocations
15|DELETE R/issues/{n}/labels/{encoded-type-label} only for saved issue labels; GET complete R/issues labels|removed label IDs and remaining labels|no issue duplicate type labels; unrelated and PR labels retained|POST only saved removed issue labels"""


def operation_plan(
    tables: Tables, cp1: Snapshot, reviewed_status: dict[str, str] | None = None
) -> tuple[Step, ...]:
    """Describe each section-10 stage for a journaled runner without making calls."""
    validate_cp1(tables, cp1, reviewed_status)
    numbered = tuple(row["number"] for row in tables.assignments if row["number"])
    closures = tuple(
        row["number"]
        for row in tables.assignments
        if row["number"] and row["live state"] == "open" and row["state"] == "closed"
    )
    drafts = tuple(
        _key(row)
        for row in tables.assignments
        if row["backfill mode"] in {"draft", "existing draft"}
    )
    parents = tuple(
        row["proposed title"]
        for kind in ("initiative", "epic")
        for row in tables.parents
        if row["kind"] == kind
    )
    if len(parents) != len(tables.parents):
        raise ValueError("unknown parent kind")
    incidents = tuple(
        _key(row) for row in tables.assignments if row["backfill mode"] == "issue"
    )
    hierarchy = tuple(
        _key(row) for row in tables.assignments if row["number"] and row["epic"]
    ) + tuple(row["proposed title"] for row in tables.parents if row["parent title"])
    links = tuple(
        f"{row['dependent']} <- {row['blocker']}"
        for row in tables.edges
        if (row["action"].startswith("write") and row["execution"] == "native")
        or row["execution"] == "delete"
    )
    retitles = tuple(
        row["number"] for row in tables.assignments if row["proposed title"]
    )
    rank = tuple(
        _key(row)
        for row in tables.assignments
        if row["priority"] == "Standard" and row["state"] != "closed"
    )
    labels = tuple(
        row["number"]
        for row in tables.assignments
        if row["number"] and row["old type labels"]
    )
    targets = {
        "1": numbered,
        "0": closures,
        "2": (),
        "3": ("149 <- 96",),
        "4": (),
        "5": (),
        "6": (*numbered, *drafts),
        "6T": retitles,
        "7": (),
        "8": rank,
        "9": parents,
        "10": hierarchy,
        "11": links,
        "12": incidents,
        "13": (*numbered, *parents, *incidents, *drafts),
        "14": retitles,
        "15": labels,
    }
    native_writes = {
        "6": tuple(
            _native_write(_key(row), row) for row in tables.assignments if row["number"]
        ),
        "9": tuple(_native_write(row["proposed title"], row) for row in tables.parents),
        "12": tuple(
            _native_write(_key(row), row)
            for row in tables.assignments
            if row["backfill mode"] == "issue"
        ),
    }
    return tuple(
        Step(
            number,
            targets[number],
            tuple(calls.split("; ")) if calls else (),
            (saved,),
            check,
            tuple(reverse.split("; ")),
            native_writes.get(number, ()),
        )
        for number, calls, saved, check, reverse in (
            line.split("|") for line in PLAN_CONTRACT.splitlines()
        )
    )


def _native_write(key: str, row: dict[str, str]) -> NativeWrite:
    issue_type = row["issue type"]
    fields = {}
    if issue_type in {"Feature", "Chore", "Spike"}:
        fields["Priority"] = row["priority"]
    if issue_type in {"Defect", "Incident"}:
        fields["Severity"] = row["severity"]
    fields["Work type"] = row["work type"]
    return NativeWrite(key, issue_type, _pairs(fields))


def rollback_values(  # noqa: PLR0913 - plan tables are required for safe rollback identities
    tables: Tables,
    cp1: Snapshot,
    created: dict[str, Item],
    order: tuple[str, ...],
    pr_state: str,
    *,
    extras: RollbackExtras | None = None,
) -> Rollback:
    """Retain exact old values and creation IDs, never inferred replacement values."""
    extras = extras or RollbackExtras()
    if cp1.run_state != "initial" or not complete(cp1):
        raise ValueError("rollback requires complete initial CP1")
    if len(order) != len(set(order)) or set(order) != {
        item.item_id for item in cp1.items if item.item_id
    }:
        raise ValueError("incomplete saved Project order")
    if any(not (item.issue_id or item.draft_id) for item in created.values()):
        raise ValueError("created identity is incomplete")
    old = {item.key: item for item in cp1.items}
    issue_ids = {item.issue_id for item in cp1.items if item.issue_id}
    draft_ids = {item.draft_id for item in cp1.items if item.draft_id}
    item_ids = {item.item_id for item in cp1.items if item.item_id}
    keys = set(old)
    for item in created.values():
        if (
            item.key in keys
            or (item.issue_id and item.issue_id in issue_ids)
            or (item.draft_id and item.draft_id in draft_ids)
            or (item.item_id and item.item_id in item_ids)
        ):
            raise ValueError("created identity collides with CP1 or creation")
        keys.add(item.key)
        issue_ids.add(item.issue_id)
        draft_ids.add(item.draft_id)
        item_ids.add(item.item_id)
    planned_drafts = {
        _key(row)
        for row in tables.assignments
        if row["backfill mode"] == "draft" and _key(row) not in old
    }
    planned_issues = {
        _key(row)
        for row in tables.assignments
        if row["backfill mode"] == "issue" and _key(row) not in old
    } | {f"title:{row['proposed title']}" for row in tables.parents}
    if any(
        (
            key in planned_drafts
            and (item.key != key or not item.draft_id or item.issue_id)
        )
        or (
            key in planned_issues
            and (
                not item.key.startswith("#")
                or not item.key[1:].isdecimal()
                or not item.issue_id
                or item.draft_id
            )
        )
        or key not in planned_drafts | planned_issues
        for key, item in created.items()
    ):
        raise ValueError("creation resource kind differs from plan")
    added_items = extras.added_items or {}
    if any(
        key not in old or old[key].item_id or not item_id
        for key, item_id in added_items.items()
    ):
        raise ValueError("added Project membership is invalid")
    return Rollback(
        cp1.items,
        tuple(created.values()),
        order,
        pr_state,
        cp1.branch_sha,
        extras.exemptions,
        tuple(sorted(added_items.items())),
    )


def _target_key(value: str, created: dict[str, Item]) -> str:
    if value.startswith("#"):
        return value
    if value.isdecimal():
        return f"#{value}"
    key = value if value.startswith("title:") else f"title:{value}"
    return created[key].key if key in created else key


def _project_target(
    base: Item, fields: dict[str, str], *, draft: bool
) -> tuple[tuple[str, str], ...]:
    project = dict(base.project)
    project.update(fields)
    project["Type"] = "" if draft else base.issue_type
    for name in NATIVE_OPTIONS:
        project[name] = "" if draft else dict(base.native).get(name, "")
    return _pairs(project)


def expected_cp13(
    tables: Tables,
    cp1: Snapshot,
    inputs: TargetInputs,
) -> tuple[Item, ...]:
    """Build the complete numbered and draft target from CP1 and saved creation inputs."""
    created = inputs.created
    validate_cp1(tables, cp1, inputs.reviewed_status)
    exemptions = set(
        _derive_exemptions(
            tables, cp1, inputs.closed_at_cp0, inputs.revoked, inputs.reference
        )
    )
    title_repairs(tables, inputs.reference)
    expected = _created_target_items(tables, cp1, inputs)
    links: dict[str, set[str]] = {key: set() for key in expected}
    for row in tables.edges:
        if _accepted(row) and row["execution"] == "native":
            dependent = _target_key(row["dependent"], created)
            blocker = _target_key(row["blocker"], created)
            if dependent not in expected or blocker not in expected:
                raise ValueError("unresolved native dependency")
            links[dependent].add(blocker)
    context = _TargetContext(
        created, inputs.bodies, links, exemptions, inputs.reference
    )
    for row in tables.assignments:
        key = _target_key(_key(row), created)
        expected[key] = _assignment_target(row, expected[key], key, context)
    for row in tables.parents:
        key = _target_key(row["proposed title"], created)
        item = expected[key]
        item = replace(
            item,
            title=row["proposed title"],
            body=_parent_body(row),
            state=row["state"],
            state_reason="completed" if row["state"] == "closed" else "",
            issue_type=row["issue type"],
            native=_pairs(
                {"Priority": "", "Severity": "", "Work type": row["work type"]}
            ),
            parent=_target_key(row["parent title"], created)
            if row["parent title"]
            else "",
            blockers=tuple(sorted(links[key])),
        )
        expected[key] = replace(
            item,
            project=_project_target(
                item,
                {"Status": "Done" if row["state"] == "closed" else "Backlog"},
                draft=False,
            ),
        )
    return tuple(expected.values())


def _created_target_items(
    tables: Tables, cp1: Snapshot, inputs: TargetInputs
) -> dict[str, Item]:
    created = inputs.created
    expected = {item.key: item for item in cp1.items}
    required_created = {
        _key(row)
        for row in tables.assignments
        if row["backfill mode"] in {"draft", "issue"} and _key(row) not in expected
    } | {f"title:{row['proposed title']}" for row in tables.parents}
    draft_keys = {
        _key(row)
        for row in tables.assignments
        if row["backfill mode"] == "draft" and _key(row) in required_created
    }
    added_items = inputs.added_items or {}
    required_added = {
        _key(row)
        for row in tables.assignments
        if row["number"] and _key(row) in expected and not expected[_key(row)].item_id
    }
    if set(added_items) != required_added:
        raise ValueError("added Project membership is incomplete or unexpected")
    if any(
        key not in expected or expected[key].item_id or not item_id
        for key, item_id in added_items.items()
    ):
        raise ValueError("added Project membership is invalid")
    if set(created) != required_created or any(
        not item.item_id or not (item.issue_id or item.draft_id)
        for item in created.values()
    ):
        raise ValueError("creation map is incomplete or unexpected")
    if any(
        (key in draft_keys and (item.key != key or not item.draft_id or item.issue_id))
        or (
            key not in draft_keys
            and (
                not item.key.startswith("#")
                or not item.key[1:].isdecimal()
                or not item.issue_id
                or item.draft_id
            )
        )
        for key, item in created.items()
    ):
        raise ValueError("creation resource kind differs from plan")
    issue_ids = {item.issue_id for item in cp1.items if item.issue_id}
    item_ids = {item.item_id for item in cp1.items if item.item_id}
    draft_ids = {item.draft_id for item in cp1.items if item.draft_id}
    if (
        len(set(added_items.values())) != len(added_items)
        or set(added_items.values()) & item_ids
    ):
        raise ValueError("created Project item identity collides with CP1")
    for key, item in created.items():
        if (
            item.key in expected
            or (
                item.issue_id
                and (
                    not item.key.startswith("#")
                    or not item.key[1:].isdecimal()
                    or item.issue_id in issue_ids
                )
            )
            or (item.draft_id and (item.key != key or item.draft_id in draft_ids))
            or item.item_id in item_ids
        ):
            raise ValueError("created identity collides with CP1")
        expected[item.key] = item
        issue_ids.add(item.issue_id)
        item_ids.add(item.item_id)
        draft_ids.add(item.draft_id)
    if set(added_items.values()) & item_ids:
        raise ValueError("created Project item identity collides with creation")
    for key, item_id in added_items.items():
        expected[key] = replace(expected[key], item_id=item_id)
    return expected


def _assignment_target(
    row: dict[str, str],
    item: Item,
    key: str,
    context: _TargetContext,
) -> Item:
    draft = not bool(row["number"]) and row["backfill mode"] != "issue"
    title = (
        row["title"]
        if row["number"] in context.exemptions
        else row["proposed title"] or row["title"]
    )
    if (
        row["body revision"] == "required" or row["backfill mode"] == "existing draft"
    ) and key not in context.bodies:
        raise ValueError(f"reviewed body is missing: {key}")
    if (
        row["number"] not in context.exemptions
        and (len(title) > 72 or validate_title(title, context.reference, issue=True))
        and row["number"]
    ):
        raise ValueError(f"invalid non-exempt title: {key} {title}")
    native = (
        ()
        if draft
        else _pairs(
            {
                "Priority": row["priority"],
                "Severity": row["severity"],
                "Work type": row["work type"],
            }
        )
    )
    item = replace(
        item,
        title=title,
        state="draft"
        if draft
        else "open"
        if row["backfill mode"] == "issue"
        else row["state"],
        state_reason=(
            "not_planned"
            if row["live state"] == "open" and row["state"] == "closed"
            else item.state_reason
        ),
        issue_type="" if draft else row["issue type"],
        native=native,
        parent=_target_key(row["epic"], context.created)
        if row["epic"] and not draft
        else "",
        blockers=tuple(sorted(context.links[key])) if not draft else (),
        body=(
            context.bodies[key]
            if row["backfill mode"] == "existing draft"
            else _draft_body(row, context.bodies.get(key, item.body))
            if draft
            else _incident_body(row)
            if row["backfill mode"] == "issue"
            else context.bodies.get(key, item.body)
        ),
        labels=item.labels,
    )
    fields = {"Status": row["project status"]}
    if not draft:
        fields.update(
            {
                "Size": row["size"],
                "Area": row["project area"],
                "Harness": row["project harness"],
                "Worker": row["project worker"],
            }
        )
    return replace(item, project=_project_target(item, fields, draft=draft))


def compare_cp13(
    expected: tuple[Item, ...], actual: Snapshot, retained_branch_sha: str
) -> tuple[Difference, ...]:
    """Reject incomplete read-back and report every identity or value difference."""
    wanted = {item.key: item for item in expected}
    found = {item.key: item for item in actual.items}
    if len(wanted) != len(expected) or len(found) != len(actual.items):
        raise ValueError("duplicate CP13 identity")
    if not complete(actual) or actual.run_state != "final":
        raise ValueError("incomplete or incompatible CP13")
    differences = []
    if actual.branch_sha != retained_branch_sha:
        differences.append(
            Difference("branch", "sha", retained_branch_sha, actual.branch_sha)
        )
    for key in sorted(wanted.keys() | found.keys()):
        if key not in wanted or key not in found:
            differences.append(Difference(key, "presence", key in wanted, key in found))
            continue
        for field in (
            "title",
            "state",
            "state_reason",
            "issue_type",
            "native",
            "project",
            "parent",
            "blockers",
            "body",
            "labels",
            "issue_id",
            "item_id",
            "draft_id",
        ):
            left = getattr(wanted[key], field)
            right = getattr(found[key], field)
            if field == "project":
                left = tuple(pair for pair in left if pair[0] not in VALIDATOR_FIELDS)
                right = tuple(pair for pair in right if pair[0] not in VALIDATOR_FIELDS)
            if left != right:
                differences.append(Difference(key, field, left, right))
    return tuple(differences)
