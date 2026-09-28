"""Plain-value tests for the parent link decisions."""

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.parent_link_sync import (
    Issue,
    Operation,
    Parent,
    accepted,
    actual_edges,
    compare,
    dfs_cycle,
    explicit_edges,
    initial_edges,
    kahn_cycle,
    ongoing_edges,
    operation_plan,
    owned_after,
    owned_before,
    parent_titles,
)
from agent_orchestration_poc.core.work_model_backfill import Tables


def model() -> Tables:
    parents = (
        {"proposed title": "initiative: one", "parent title": ""},
        {"proposed title": "epic: a", "parent title": "initiative: one"},
        {"proposed title": "epic: b", "parent title": "initiative: one"},
    )
    edges = (
        {
            "dependent": "epic: b",
            "blocker": "epic: a",
            "execution": "native",
            "action": "write",
            "evidence": "derived",
        },
        {
            "dependent": "epic: a",
            "blocker": "initiative: one",
            "execution": "native",
            "action": "write",
            "evidence": "stated",
        },
        {
            "dependent": "2",
            "blocker": "1",
            "execution": "native",
            "action": "exists",
            "evidence": "stated",
        },
        {
            "dependent": "3",
            "blocker": "1",
            "execution": "audit only",
            "action": "no link",
            "evidence": "ambiguous",
        },
        {
            "dependent": "epic: a",
            "blocker": "epic: b",
            "execution": "audit only",
            "action": "do not write",
            "evidence": "stated",
        },
    )
    return Tables(1, (), parents, edges)


def issue_values(*, linked: bool = True) -> tuple[Issue, ...]:
    return (
        Issue("1", "epic: a", ()),
        Issue("2", "epic: b", ("1",) if linked else ()),
        Issue("3", "epic: a", ("1",)),
    )


def parent_values(*, linked: bool = True) -> tuple[Parent, ...]:
    return (
        Parent("initiative: one", 10, 110, ()),
        Parent("epic: a", 11, 111, (110,)),
        Parent("epic: b", 12, 112, (111,) if linked else ()),
    )


def test_table_filters_and_projection() -> None:
    tables = model()
    assert accepted(tables.edges[0])
    assert accepted(tables.edges[2])
    assert not accepted(tables.edges[3])
    assert not accepted({"execution": "audit only", "action": "exists"})
    assert parent_titles(tables) == {"initiative: one", "epic: a", "epic: b"}
    assert initial_edges(tables) == {
        ("epic: b", "epic: a"),
        ("epic: a", "initiative: one"),
    }
    assert explicit_edges(tables) == {("epic: a", "initiative: one")}
    assert ongoing_edges(tables, issue_values()) == initial_edges(tables)
    assert ongoing_edges(tables, issue_values(linked=False)) == explicit_edges(tables)


def test_changed_and_obsolete_link_with_ownership() -> None:
    tables = model()
    desired = ongoing_edges(tables, issue_values(linked=False))
    result = compare(
        tables,
        desired,
        parent_values(),
        issue_values(linked=False),
        initial_edges(tables),
    )
    assert result.extra == (("epic: b", "epic: a"),)
    assert result.removable == result.extra
    assert not result.missing
    assert not result.kahn_cycle
    assert not result.dfs_cycle


def test_new_accepted_edge_changes_parent_without_dispatch_decision() -> None:
    tables = replace(model(), edges=model().edges[:-1])
    issues = (Issue("1", "epic: a", ("2",)), Issue("2", "epic: b", ()))
    desired = ongoing_edges(tables, issues)
    assert ("epic: a", "epic: b") in desired
    assert ("epic: a", "epic: b") not in initial_edges(tables)
    assert ("1", "2") == (issues[0].number, issues[0].blockers[0])


def test_excluded_issue_pair_cannot_project_across_epics() -> None:
    tables = model()
    issues = (Issue("1", "epic: a", ()), Issue("3", "epic: b", ("1",)))
    assert ("epic: b", "epic: a") not in ongoing_edges(tables, issues)


def test_plan_orders_replacement_and_rejects_unowned_extras() -> None:
    tables = replace(model(), edges=model().edges[:-1])
    parents = (
        Parent("initiative: one", 10, 110, ()),
        Parent("epic: a", 11, 111, (112,)),
        Parent("epic: b", 12, 112, ()),
    )
    desired = frozenset({("epic: b", "epic: a")})
    result = compare(tables, desired, parents, (), frozenset({("epic: a", "epic: b")}))
    assert [(op.method, op.edge) for op in operation_plan(result, True, True)] == [
        ("DELETE", ("epic: a", "epic: b")),
        ("POST", ("epic: b", "epic: a")),
    ]
    with pytest.raises(ValueError, match="unowned extra"):
        operation_plan(compare(tables, desired, parents, (), frozenset()), True, True)


def test_dry_run_does_not_acquire_ownership() -> None:
    tables = model()
    edge = ("epic: b", "epic: a")
    assert owned_before(tables, None, applied=False) == frozenset({edge})
    assert owned_before(tables, (("epic: a", "epic: b"),), applied=True) == frozenset(
        {edge, ("epic: a", "epic: b")}
    )
    assert owned_after(tables, frozenset(), ()) == frozenset()
    assert owned_after(
        tables,
        frozenset({edge}),
        (Operation("DELETE", edge), Operation("POST", ("epic: a", "epic: b"))),
    ) == frozenset({("epic: a", "epic: b")})
    assert (
        owned_after(
            tables,
            frozenset(),
            (Operation("POST", ("epic: a", "initiative: one")),),
        )
        == frozenset()
    )
    with pytest.raises(ValueError, match="successful apply"):
        owned_before(tables, (edge,), applied=False)


def test_operation_plan_guards_apply_and_cycles() -> None:
    tables = model()
    result = compare(
        tables, initial_edges(tables), parent_values(linked=False), (), frozenset()
    )
    assert operation_plan(result, False, False) == ()
    with pytest.raises(ValueError, match="coordinator identity"):
        operation_plan(result, True, False)
    cyclic = replace(result, kahn_cycle=True)
    with pytest.raises(ValueError, match="cycle"):
        operation_plan(cyclic, False, False)
    cyclic = replace(result, dfs_cycle=("a", "b", "a"))
    with pytest.raises(ValueError, match="cycle"):
        operation_plan(cyclic, True, True)


def test_missing_and_unowned_link() -> None:
    tables = model()
    result = compare(
        tables,
        initial_edges(tables),
        parent_values(linked=False),
        issue_values(),
        frozenset(),
    )
    assert result.missing == (("epic: b", "epic: a"),)
    assert not result.removable
    with pytest.raises(ValueError, match="external parent blocker"):
        actual_edges(
            (replace(parent_values()[0], blockers=(999,)), *parent_values()[1:]),
            parent_titles(tables),
        )


def test_incomplete_and_duplicate_reads_fail() -> None:
    tables = model()
    with pytest.raises(ValueError, match="incomplete parent"):
        actual_edges(parent_values()[:1], parent_titles(tables))
    with pytest.raises(ValueError, match="duplicate parent"):
        actual_edges((*parent_values(), parent_values()[0]), parent_titles(tables))
    with pytest.raises(ValueError, match="duplicate parent"):
        actual_edges(
            (replace(parent_values()[0], issue_id=111), *parent_values()[1:]),
            parent_titles(tables),
        )
    with pytest.raises(ValueError, match="incomplete blocker"):
        ongoing_edges(tables, (Issue("2", "epic: b", ("1",)),))
    with pytest.raises(ValueError, match="duplicate issue"):
        ongoing_edges(tables, (*issue_values(), issue_values()[0]))


def test_rejected_reverse_issue_link_fails_both_cycle_checks() -> None:
    edges = frozenset({("27", "160"), ("160", "27")})
    assert kahn_cycle(edges)
    assert len(dfs_cycle(edges)) == 3
    result = compare(
        model(),
        initial_edges(model()),
        parent_values(),
        (Issue("27", "epic: a", ("160",)), Issue("160", "epic: b", ("27",))),
        frozenset(),
    )
    assert result.kahn_cycle
    assert result.dfs_cycle


@given(st.integers(min_value=1, max_value=40))
def test_acyclic_chain_and_reverse_property(length: int) -> None:
    edges = frozenset((str(i), str(i - 1)) for i in range(1, length))
    assert not kahn_cycle(edges)
    assert not dfs_cycle(edges)
    if length > 1:
        cyclic = edges | {(str(0), str(length - 1))}
        assert kahn_cycle(cyclic)
        assert dfs_cycle(cyclic)
