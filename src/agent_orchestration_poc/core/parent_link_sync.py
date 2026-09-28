"""Pure decisions for native parent dependency synchronization."""

from dataclasses import dataclass

from agent_orchestration_poc.core.work_model_backfill import Tables


@dataclass(frozen=True)
class Parent:
    """A resolved native parent and its complete blocked-by read."""

    title: str
    number: int
    issue_id: int
    blockers: tuple[int, ...]


@dataclass(frozen=True)
class Issue:
    """A numbered issue's current membership and accepted blocker read."""

    number: str
    epic: str
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Comparison:
    """Desired and actual edges with changes owned by this synchronizer."""

    desired: frozenset[tuple[str, str]]
    actual: frozenset[tuple[str, str]]
    missing: tuple[tuple[str, str], ...]
    extra: tuple[tuple[str, str], ...]
    removable: tuple[tuple[str, str], ...]
    kahn_cycle: bool
    dfs_cycle: tuple[str, ...]


@dataclass(frozen=True)
class Operation:
    """One ordered native parent dependency mutation."""

    method: str
    edge: tuple[str, str]


def accepted(row: dict[str, str]) -> bool:
    """Recognize only immediately accepted native table edges."""
    return row["execution"] == "native" and row["action"].startswith(
        ("exists", "write")
    )


def parent_titles(tables: Tables) -> frozenset[str]:
    """Return the complete approved parent identity set."""
    return frozenset(row["proposed title"] for row in tables.parents)


def initial_edges(tables: Tables) -> frozenset[tuple[str, str]]:
    """Read the initial native target directly from approved edge rows."""
    parents = parent_titles(tables)
    return frozenset(
        (row["dependent"], row["blocker"])
        for row in tables.edges
        if accepted(row) and row["dependent"] in parents and row["blocker"] in parents
    )


def explicit_edges(tables: Tables) -> frozenset[tuple[str, str]]:
    """Keep operator gate and roadmap order independent of issue changes."""
    parents = parent_titles(tables)
    return frozenset(
        (row["dependent"], row["blocker"])
        for row in tables.edges
        if accepted(row)
        and row["dependent"] in parents
        and row["blocker"] in parents
        and row["evidence"] != "derived"
    )


def ongoing_edges(
    tables: Tables, issues: tuple[Issue, ...]
) -> frozenset[tuple[str, str]]:
    """Project current accepted issue links through current memberships."""
    parents = parent_titles(tables)
    initiatives = {row["proposed title"]: row["parent title"] for row in tables.parents}
    denied = {
        (row["dependent"], row["blocker"]) for row in tables.edges if not accepted(row)
    }
    by_number = {issue.number: issue for issue in issues}
    if len(by_number) != len(issues):
        raise ValueError("duplicate issue read")
    result = set(explicit_edges(tables))
    for dependent in issues:
        for blocker_number in dependent.blockers:
            blocker = by_number.get(blocker_number)
            if blocker is None:
                raise ValueError("incomplete blocker read")
            if (dependent.number, blocker_number) in denied:
                continue
            if not dependent.epic or not blocker.epic or dependent.epic == blocker.epic:
                continue
            if dependent.epic not in parents or blocker.epic not in parents:
                raise ValueError("unknown membership")
            edge = (dependent.epic, blocker.epic)
            if edge not in denied:
                result.add(edge)
            dependency_initiative = initiatives[dependent.epic]
            blocker_initiative = initiatives[blocker.epic]
            if (
                dependency_initiative
                and blocker_initiative
                and dependency_initiative != blocker_initiative
                and (dependency_initiative, blocker_initiative) not in denied
            ):
                result.add((dependency_initiative, blocker_initiative))
    return frozenset(result)


def actual_edges(
    parents: tuple[Parent, ...], expected_titles: frozenset[str]
) -> frozenset[tuple[str, str]]:
    """Resolve complete native blocker IDs to parent titles."""
    by_id = {parent.issue_id: parent.title for parent in parents}
    if len(by_id) != len(parents) or len({p.title for p in parents}) != len(parents):
        raise ValueError("duplicate parent read")
    if not {parent.title for parent in parents} <= expected_titles:
        raise ValueError("unexpected parent read")
    if len(parents) != len(expected_titles):
        if parents:
            raise ValueError("incomplete parent read")
        return frozenset()
    if any(blocker not in by_id for parent in parents for blocker in parent.blockers):
        raise ValueError("external parent blocker requires review")
    return frozenset(
        (parent.title, by_id[blocker])
        for parent in parents
        for blocker in parent.blockers
    )


def kahn_cycle(edges: frozenset[tuple[str, str]]) -> bool:
    """Detect a directed cycle by repeatedly removing zero-indegree nodes."""
    nodes = {node for edge in edges for node in edge}
    incoming = {node: 0 for node in nodes}
    outgoing: dict[str, set[str]] = {node: set() for node in nodes}
    for dependent, blocker in edges:
        outgoing[dependent].add(blocker)
        incoming[blocker] += 1
    ready = [node for node, degree in incoming.items() if degree == 0]
    visited = 0
    while ready:
        node = ready.pop()
        visited += 1
        for next_node in outgoing[node]:
            incoming[next_node] -= 1
            if incoming[next_node] == 0:
                ready.append(next_node)
    return visited != len(nodes)


def dfs_cycle(edges: frozenset[tuple[str, str]]) -> tuple[str, ...]:
    """Return one deterministic directed cycle by depth-first search."""
    graph: dict[str, set[str]] = {}
    for dependent, blocker in edges:
        graph.setdefault(dependent, set()).add(blocker)
    active: dict[str, int] = {}
    done: set[str] = set()

    def visit(node: str, path: tuple[str, ...]) -> tuple[str, ...]:
        if node in active:
            return (*path[active[node] :], node)
        if node in done:
            return ()
        active[node] = len(path)
        for next_node in sorted(graph.get(node, ())):
            if found := visit(next_node, (*path, node)):
                return found
        del active[node]
        done.add(node)
        return ()

    for node in sorted(graph):
        if found := visit(node, ()):
            return found
    return ()


def compare(
    tables: Tables,
    desired: frozenset[tuple[str, str]],
    parents: tuple[Parent, ...],
    issues: tuple[Issue, ...],
    managed: frozenset[tuple[str, str]],
) -> Comparison:
    """Compare parent links and check the combined issue and parent graph."""
    actual = actual_edges(parents, parent_titles(tables))
    issue_edges = frozenset(
        (issue.number, blocker) for issue in issues for blocker in issue.blockers
    )
    membership_edges = frozenset(
        (issue.number, issue.epic) for issue in issues if issue.epic
    )
    graph = desired | issue_edges | membership_edges
    extra = actual - desired
    return Comparison(
        desired,
        actual,
        tuple(sorted(desired - actual)),
        tuple(sorted(extra)),
        tuple(sorted(extra & managed - explicit_edges(tables))),
        kahn_cycle(graph),
        dfs_cycle(graph),
    )


def operation_plan(
    result: Comparison, apply_requested: bool, eligible: bool
) -> tuple[Operation, ...]:
    """Refuse unsafe apply and remove obsolete edges before additions."""
    if result.kahn_cycle or result.dfs_cycle:
        raise ValueError(f"cycle: Kahn={result.kahn_cycle}, DFS={result.dfs_cycle}")
    if not apply_requested:
        return ()
    if not eligible:
        raise ValueError("apply requires all parents and coordinator identity")
    if set(result.extra) != set(result.removable):
        raise ValueError("unowned extra parent link requires review")
    return (
        *(Operation("DELETE", edge) for edge in result.removable),
        *(Operation("POST", edge) for edge in result.missing),
    )


def owned_before(
    tables: Tables,
    recorded: tuple[tuple[str, str], ...] | None,
    *,
    applied: bool,
) -> frozenset[tuple[str, str]]:
    """Bootstrap from approved derived edges or accept a successful receipt."""
    base = initial_edges(tables) - explicit_edges(tables)
    if recorded is None:
        return base
    if not applied:
        raise ValueError("managed ledger requires successful apply receipt")
    return base | frozenset(recorded)


def owned_after(
    tables: Tables,
    managed: frozenset[tuple[str, str]],
    completed: tuple[Operation, ...],
) -> frozenset[tuple[str, str]]:
    """Advance ownership only for mutations with read-back receipts."""
    additions = {
        operation.edge for operation in completed if operation.method == "POST"
    }
    removals = {
        operation.edge for operation in completed if operation.method == "DELETE"
    }
    return frozenset((managed | additions) - removals - explicit_edges(tables))
