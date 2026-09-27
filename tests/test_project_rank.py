"""Plain-value tests for rank planning and safety decisions."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.project_rank import (
    Item,
    apply_mutations,
    eligible,
    plan_move,
    plan_order,
    plan_replace,
    safe_to_write,
    standard_issues,
    validate_items,
)


def _item(number: int, *, priority: str = "Standard", state: str = "OPEN") -> Item:
    return Item(f"I{number}", number, "ISSUE", priority, state, "Chore")


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        (_item(1), True),
        (_item(1, priority="Expedite"), False),
        (_item(1, state="CLOSED"), False),
        (Item("D1", None, "DRAFT_ISSUE", "Standard", "OPEN", ""), True),
        (Item("I1", 1, "ISSUE", "Standard", "OPEN", "Epic"), False),
    ],
)
def test_eligible(item: Item, expected: bool) -> None:
    assert eligible(item) is expected


def test_standard_issues_and_validation() -> None:
    items = (_item(1), _item(2, priority="Intangible"), _item(3))
    validate_items(items)
    assert standard_issues(items) == (1, 3)
    for broken in ((), (_item(1), _item(1)), (Item("", 1, "ISSUE", "", "OPEN", ""),)):
        with pytest.raises(ValueError, match="incomplete|duplicate"):
            validate_items(broken)


@pytest.mark.parametrize(
    ("issue", "relation", "anchor", "expected", "after"),
    [
        (3, "above", 1, (3, 1, 2), None),
        (1, "below", 3, (2, 3, 1), "I3"),
    ],
)
def test_plan_move(
    issue: int, relation: str, anchor: int, expected: tuple[int, ...], after: str | None
) -> None:
    items = (_item(1), _item(2), _item(3))
    mutations = plan_move(items, issue, relation, anchor)
    assert mutations[0].after_id == after
    assert standard_issues(apply_mutations(items, mutations)) == expected


def test_move_refusals() -> None:
    items = (_item(1), _item(2, priority="Expedite"), _item(3, state="CLOSED"))
    for issue, anchor, relation in (
        (99, 1, "above"),
        (2, 1, "above"),
        (1, 3, "below"),
        (1, 1, "above"),
        (1, 2, "sideways"),
    ):
        with pytest.raises(ValueError, match="missing|Standard|distinct"):
            plan_move(items, issue, relation, anchor)


def test_order_and_replace() -> None:
    draft = Item("D1", None, "DRAFT_ISSUE", "Standard", "OPEN", "")
    items = (_item(1), draft, _item(2), _item(3))
    ordered = plan_order(items, (3, 1, 2))
    assert standard_issues(apply_mutations(items, ordered)) == (3, 1, 2)
    assert plan_order(items, (1, 2, 3)) == ()
    replacement = plan_replace(items, "D1", 3)
    result = apply_mutations(items, replacement)
    assert result.index(_item(3)) + 1 == result.index(draft)
    with pytest.raises(ValueError, match="every open Standard"):
        plan_order(items, (1, 2))
    with pytest.raises(ValueError, match="draft item"):
        plan_replace(items, "missing", 3)
    with pytest.raises(ValueError, match="missing"):
        plan_replace(items, "D1", 99)


@pytest.mark.parametrize(
    ("remaining", "cost", "changed", "expected"),
    [
        (100, 10, False, True),
        (99, 10, False, False),
        (100, 0, False, False),
        (100, 10, True, False),
    ],
)
def test_safe_to_write(
    remaining: int, cost: int, changed: bool, expected: bool
) -> None:
    before = (_item(1), _item(2))
    after = tuple(reversed(before)) if changed else before
    assert safe_to_write(before, after, remaining, cost) is expected


@given(st.permutations((1, 2, 3, 4, 5)))
def test_every_complete_order_reaches_its_requested_order(order: list[int]) -> None:
    items = tuple(_item(number) for number in range(1, 6))
    mutations = plan_order(items, tuple(order))
    assert standard_issues(apply_mutations(items, mutations)) == tuple(order)
    assert all(
        mutation.item_id in {item.id for item in items} for mutation in mutations
    )


@given(st.sampled_from(("above", "below")), st.integers(1, 5), st.integers(1, 5))
def test_one_move_preserves_membership(relation: str, issue: int, anchor: int) -> None:
    items = tuple(_item(number) for number in range(1, 6))
    if issue == anchor:
        with pytest.raises(ValueError, match="distinct"):
            plan_move(items, issue, relation, anchor)
        return
    moved = standard_issues(
        apply_mutations(items, plan_move(items, issue, relation, anchor))
    )
    assert set(moved) == set(range(1, 6))
    assert (moved.index(issue) < moved.index(anchor)) is (relation == "above")
