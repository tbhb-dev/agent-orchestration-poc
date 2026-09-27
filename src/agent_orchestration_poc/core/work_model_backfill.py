"""Pure versioned work-model table and initial snapshot contract."""

import csv
import io
from dataclasses import dataclass

VERSION = 1
ISSUE_TYPES = frozenset(
    {"Feature", "Defect", "Chore", "Spike", "Incident", "Epic", "Initiative"}
)
NATIVE_OPTIONS = {
    "Priority": frozenset({"", "Expedite", "Standard", "Intangible"}),
    "Severity": frozenset({"", "SEV1", "SEV2", "SEV3"}),
    "Work type": frozenset({"Planned", "Unplanned"}),
}
PROJECT_FIELDS = (
    "Status",
    "Size",
    "Phase",
    "Area",
    "Harness",
    "Worker",
    "Validation",
    "Validation detail",
)
ASSIGNMENT_COLUMNS = (
    "number",
    "state",
    "title",
    "epic",
    "initiative",
    "priority",
    "severity",
    "work type",
    "issue type",
    "live state",
    "state reason",
    "backfill mode",
    "project status",
    "project size",
    "project phase",
    "project area",
    "project harness",
    "project worker",
    "proposed title",
    "fold into",
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


def _rows(text: str, required: tuple[str, ...]) -> tuple[dict[str, str], ...]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t", strict=True)
    if reader.fieldnames is None or not set(required) <= set(reader.fieldnames):
        raise ValueError("table header is incomplete")
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("duplicate table column")
    rows = tuple(dict(row) for row in reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("table row has wrong column count")
    return rows


def parse_tables(assignments: str, parents: str, edges: str) -> Tables:
    """Parse all three supplied TSV values without dropping audit rows."""
    a = _rows(assignments, ASSIGNMENT_COLUMNS)
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
    return (
        pages_complete
        and counts["issues"] == issues
        and counts["drafts"] == drafts
        and counts["project"] == project
        and all(counts[name] >= issues for name in ("native", "parents", "blockers"))
    )


def _key(row: dict[str, str]) -> str:
    return f"#{row['number']}" if row.get("number") else f"title:{row['title']}"


def _pairs(values: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(values.items()))


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


def validate_cp1(tables: Tables, snapshot: Snapshot) -> None:
    """Refuse stale, incomplete, duplicate, or already-parented initial reads."""
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
        _validate_source_issue(row, items[_key(row)])
    _validate_drafts(tables, snapshot)
    if cycle := cycle_nodes(tables):
        raise ValueError(f"accepted graph contains a cycle: {cycle}")


def _validate_drafts(tables: Tables, snapshot: Snapshot) -> None:
    draft_titles = [item.title for item in snapshot.items if item.draft_id]
    if len(draft_titles) != len(set(draft_titles)):
        raise ValueError("duplicate existing draft title")
    for row in tables.assignments:
        if row["number"]:
            continue
        present = row["title"] in draft_titles
        if row["backfill mode"] == "existing draft" and not present:
            raise ValueError("unresolved existing draft")
        if row["backfill mode"] != "existing draft" and present:
            raise ValueError("proposed new draft already exists")


def _validate_source_issue(row: dict[str, str], item: Item) -> None:
    if not item.issue_id:
        raise ValueError("unresolved source issue id")
    if item.title != row["title"]:
        raise ValueError("missing or changed source issue title")
    if item.state != row["live state"] or item.state_reason != row["state reason"]:
        raise ValueError("changed source issue state")
    if item.parent:
        raise ValueError("initial child already has a parent")
    expected = _pairs(
        {field: row.get("project " + field.lower(), "") for field in PROJECT_FIELDS}
    )
    if item.source_project != expected:
        raise ValueError("changed source Project values")
    if row.get("target project item") and item.item_id != row["target project item"]:
        raise ValueError("changed target Project identity")
    if row.get("target content id") and item.issue_id != row["target content id"]:
        raise ValueError("changed target issue identity")
