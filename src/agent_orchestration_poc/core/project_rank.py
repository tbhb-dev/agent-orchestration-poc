"""Pure Project item rank planning and write safety decisions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    """One item from a complete position-ordered Project read."""

    id: str
    issue: int | None
    kind: str
    priority: str
    state: str
    work_type: str


@dataclass(frozen=True)
class Mutation:
    """Position an item immediately after another item, or at the top."""

    item_id: str
    after_id: str | None


def eligible(item: Item) -> bool:
    """Limit rank changes to open Standard nonparent items."""
    return (
        item.priority == "Standard"
        and item.state == "OPEN"
        and item.work_type not in {"Initiative", "Epic"}
        and item.kind in {"ISSUE", "DRAFT_ISSUE"}
    )


def standard_issues(items: tuple[Item, ...]) -> tuple[int, ...]:
    """Return eligible issue numbers in native order."""
    return tuple(
        item.issue for item in items if eligible(item) and item.issue is not None
    )


def validate_items(items: tuple[Item, ...]) -> None:
    """Refuse incomplete or ambiguous Project snapshots."""
    ids = [item.id for item in items]
    issues = [item.issue for item in items if item.issue is not None]
    if not items or len(ids) != len(set(ids)) or len(issues) != len(set(issues)):
        raise ValueError("incomplete or duplicate Project items")
    if any(
        not item.id
        or not item.kind
        or not item.state
        or (item.state == "OPEN" and not item.priority)
        for item in items
    ):
        raise ValueError("item field read is incomplete")
    if any(
        item.kind == "ISSUE"
        and item.state == "OPEN"
        and item.priority == "Standard"
        and not item.work_type
        for item in items
    ):
        raise ValueError("Standard issue type is missing")


def _issue(items: tuple[Item, ...], number: int) -> Item:
    matches = [item for item in items if item.issue == number]
    if len(matches) != 1:
        raise ValueError(f"issue #{number} is missing or ambiguous")
    item = matches[0]
    if not eligible(item):
        raise ValueError(f"issue #{number} is not open Standard nonparent work")
    return item


def _position(items: tuple[Item, ...], mutation: Mutation) -> tuple[Item, ...]:
    moving = next(item for item in items if item.id == mutation.item_id)
    remaining = [item for item in items if item.id != mutation.item_id]
    index = (
        0
        if mutation.after_id is None
        else next(
            i + 1 for i, item in enumerate(remaining) if item.id == mutation.after_id
        )
    )
    remaining.insert(index, moving)
    return tuple(remaining)


def plan_move(
    items: tuple[Item, ...], issue: int, relation: str, anchor: int
) -> tuple[Mutation, ...]:
    """Plan one issue move relative to another eligible issue."""
    validate_items(items)
    moving = _issue(items, issue)
    target = _issue(items, anchor)
    if moving == target or relation not in {"above", "below"}:
        raise ValueError("move requires distinct issues and above or below")
    remaining = [item for item in items if item != moving]
    target_index = remaining.index(target)
    insertion = target_index if relation == "above" else target_index + 1
    after_id = remaining[insertion - 1].id if insertion else None
    mutation = Mutation(moving.id, after_id)
    return () if _position(items, mutation) == items else (mutation,)


def plan_order(
    items: tuple[Item, ...], issues: tuple[int, ...]
) -> tuple[Mutation, ...]:
    """Plan a complete Standard issue order from top to bottom."""
    validate_items(items)
    current = standard_issues(items)
    if len(issues) != len(current) or set(issues) != set(current):
        raise ValueError("order must contain every open Standard issue exactly once")
    if current == issues:
        return ()
    working = items
    mutations: list[Mutation] = []
    for index, number in enumerate(issues):
        if standard_issues(working)[index] == number:
            continue
        item = _issue(working, number)
        predecessor = _issue(working, issues[index - 1]).id if index else None
        mutation = Mutation(item.id, predecessor)
        working = _position(working, mutation)
        mutations.append(mutation)
    return tuple(mutations)


def plan_replace(
    items: tuple[Item, ...], draft_id: str, issue: int
) -> tuple[Mutation, ...]:
    """Put a replacement issue at an open Standard draft's position."""
    validate_items(items)
    draft = next((item for item in items if item.id == draft_id), None)
    if draft is None or draft.kind != "DRAFT_ISSUE" or not eligible(draft):
        raise ValueError("draft item is missing or not open Standard")
    replacement = _issue(items, issue)
    before = [item for item in items[: items.index(draft)] if item != replacement]
    return (Mutation(replacement.id, before[-1].id if before else None),)


def safe_to_write(
    before: tuple[Item, ...], after: tuple[Item, ...], remaining: int, cost: int
) -> bool:
    """Require unchanged state and ten times the planned point cost."""
    return before == after and cost > 0 and remaining >= 10 * cost


def apply_mutations(
    items: tuple[Item, ...], mutations: tuple[Mutation, ...]
) -> tuple[Item, ...]:
    """Predict the complete native order after planned mutations."""
    for mutation in mutations:
        items = _position(items, mutation)
    return items
