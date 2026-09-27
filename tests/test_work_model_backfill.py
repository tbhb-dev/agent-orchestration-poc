"""Synthetic table and initial snapshot tests for the work model."""

from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.work_model_backfill import (
    PROJECT_FIELDS,
    Item,
    Page,
    Snapshot,
    Tables,
    complete,
    cycle_nodes,
    parse_tables,
    validate_cp1,
)

FIXTURES = Path(__file__).parent / "fixtures/work_model_backfill/plan"


def texts() -> tuple[str, str, str]:
    """Read three synthetic TSV values."""
    return (
        (FIXTURES / "assignments.tsv").read_text(),
        (FIXTURES / "parents.tsv").read_text(),
        (FIXTURES / "edges.tsv").read_text(),
    )


def tables() -> Tables:
    """Parse the synthetic work model."""
    return parse_tables(*texts())


def snapshot() -> Snapshot:
    """Make a complete CP1 with a matched draft and an unrelated held draft."""
    issues = tuple(
        Item(
            key=f"#{row['number']}",
            title=row["title"],
            state=row["live state"],
            state_reason=row["state reason"],
            issue_id=row["number"],
            item_id="item-" + row["number"],
            source_project=tuple(
                sorted(
                    (field, row.get("project " + field.lower(), ""))
                    for field in PROJECT_FIELDS
                )
            ),
        )
        for row in tables().assignments
        if row["number"]
    )
    drafts = (
        Item("title:Draft B", "Draft B", "draft", draft_id="draft-b", item_id="item-b"),
        Item("title:Held", "Held", "draft", draft_id="draft-held", item_id="item-held"),
    )
    pages = tuple(
        Page(name, 1, count, 1, count)
        for name, count in (
            ("issues", 2),
            ("project", 4),
            ("drafts", 2),
            ("native", 2),
            ("parents", 2),
            ("blockers", 2),
        )
    )
    return Snapshot(1, (*issues, *drafts), pages, "sha")


def test_parse_preserves_dispositions() -> None:
    """Retain the rejected and pending rows beside accepted links."""
    parsed = tables()
    assert [row["action"] for row in parsed.edges] == [
        "write",
        "no link",
        "judgment: inferred",
        "cut: not native, remove from the body",
    ]
    assert parsed.assignments[0]["issue type"] == "Chore"
    assert parsed.parents[0]["issue type"] == "Epic"
    assert cycle_nodes(parsed) == ()


@pytest.mark.parametrize(
    ("index", "change", "message"),
    [
        (0, "duplicate number", "duplicate or invalid issue number"),
        (0, "duplicate draft", "duplicate draft title"),
        (0, "experiment", "unknown native issue type"),
        (0, "priority", "unknown native field option"),
        (0, "severity", "unknown native field option"),
        (0, "parent", "unresolved parent title"),
        (1, "duplicate parent", "duplicate or missing parent title"),
        (2, "edge", "unresolved accepted edge"),
        (2, "header", "table header is incomplete"),
        (2, "short row", "table row has wrong column count"),
    ],
)
def test_invalid_tables_fail(index: int, change: str, message: str) -> None:
    """Reject ambiguous keys, invalid options, and malformed TSV."""
    values = list(texts())
    lines = values[index].splitlines()
    match change:
        case "duplicate number" | "duplicate draft":
            lines.append(lines[1 if change == "duplicate number" else 4])
        case "duplicate parent":
            lines.append(lines[1])
        case "experiment":
            lines[1] = lines[1].replace("Chore", "Experiment")
        case "priority":
            lines[1] = lines[1].replace("Standard", "Urgent")
        case "severity":
            cells = lines[1].split("\t")
            cells[lines[0].split("\t").index("severity")] = "SEV4"
            lines[1] = "\t".join(cells)
        case "parent":
            lines[1] = lines[1].replace("epic: migration", "epic: missing")
        case "edge":
            lines[1] = lines[1].replace("\t2\t", "\t999\t")
        case "header":
            lines[0] = lines[0].replace("execution", "unused")
        case "short row":
            lines[1] = lines[1].rsplit("\t", 1)[0]
    values[index] = "\n".join(lines) + "\n"
    with pytest.raises(ValueError, match=f"^{message}$"):
        parse_tables(*values)


@pytest.mark.parametrize(
    ("table", "old", "new"),
    [
        (0, "Draft A", "epic: migration"),
        (0, "Draft A", "1"),
        (1, "epic: migration", "1"),
    ],
)
def test_shared_edge_keys_must_be_unique(table: int, old: str, new: str) -> None:
    """A draft, parent, and numbered issue cannot share an edge key."""
    values = list(texts())
    values[table] = values[table].replace(old, new)
    with pytest.raises(ValueError, match="^duplicate edge key$"):
        parse_tables(*values)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("title", "drift", "missing or changed source issue title"),
        ("state", "closed", "changed source issue state"),
        ("parent", "other", "initial child already has a parent"),
        ("source_project", (), "changed source Project values"),
        ("issue_id", "", "unresolved source issue id"),
    ],
)
def test_stale_issue_fails(field: str, value: str | tuple[()], message: str) -> None:
    """Reject changed source issue values before any closure."""
    cp1 = snapshot()
    match field:
        case "title":
            changed = replace(cp1.items[0], title=str(value))
        case "state":
            changed = replace(cp1.items[0], state=str(value))
        case "parent":
            changed = replace(cp1.items[0], parent=str(value))
        case "source_project":
            changed = replace(cp1.items[0], source_project=())
        case _:
            changed = replace(cp1.items[0], issue_id="")
    cp1 = replace(cp1, items=(changed, *cp1.items[1:]))
    if field == "issue_id":
        cp1 = replace(
            cp1,
            pages=tuple(
                replace(page, count=1, total_count=1)
                if page.collection in {"issues", "native", "parents", "blockers"}
                else page
                for page in cp1.pages
            ),
        )
    with pytest.raises(ValueError, match=f"^{message}$"):
        validate_cp1(tables(), cp1)


def test_complete_and_draft_guards() -> None:
    """Refuse missing pages, a missing existing draft, and a partial-run snapshot."""
    cp1 = snapshot()
    assert complete(cp1)
    validate_cp1(tables(), cp1)
    assert not complete(replace(cp1, pages=cp1.pages[:-1]))
    assert not complete(replace(cp1, pages=(*cp1.pages, cp1.pages[0])))
    split = (Page("issues", 1, 1, 2, 2), Page("issues", 2, 1, 2, 2))
    assert not complete(
        replace(cp1, pages=(*split, *cp1.pages[1:]), items=cp1.items[:1])
    )
    assert not complete(
        replace(cp1, pages=(replace(split[0], count=2), *cp1.pages[1:]))
    )
    assert not complete(
        replace(cp1, pages=(split[0], replace(split[1], index=3), *cp1.pages[1:]))
    )
    assert not complete(
        replace(cp1, pages=(split[0], replace(split[1], total_pages=3), *cp1.pages[1:]))
    )
    assert not complete(
        replace(cp1, pages=(split[0], replace(split[1], total_count=3), *cp1.pages[1:]))
    )
    assert not complete(replace(cp1, branch_sha=""))
    assert not complete(replace(cp1, version=2))
    with pytest.raises(ValueError, match="^incomplete or incompatible CP1$"):
        validate_cp1(tables(), replace(cp1, run_state="partial"))
    missing = replace(cp1, items=cp1.items[:2] + cp1.items[3:])
    missing = replace(
        missing,
        pages=tuple(
            replace(page, count=1, total_count=1)
            if page.collection == "drafts"
            else replace(page, count=3, total_count=3)
            if page.collection == "project"
            else page
            for page in missing.pages
        ),
    )
    with pytest.raises(ValueError, match="^unresolved existing draft$"):
        validate_cp1(tables(), missing)
    assert cp1.items[-1].draft_id == "draft-held"
    assert cp1.items[0].issue_type == ""
    assert cp1.items[0].native == ()
    assert cp1.items[0].project == ()
    assert cp1.items[0].blockers == ()
    assert cp1.items[0].body == ""
    assert cp1.items[0].labels == ()


def test_new_draft_already_in_cp1_fails() -> None:
    """Reject creation intent when a held draft now has the proposed title."""
    cp1 = snapshot()
    found = replace(cp1.items[-1], key="title:Draft A", title="Draft A")
    cp1 = replace(cp1, items=(*cp1.items[:-1], found))
    with pytest.raises(ValueError, match="^proposed new draft already exists$"):
        validate_cp1(tables(), cp1)


@given(st.integers(min_value=1, max_value=50))
def test_cycle_property(length: int) -> None:
    """A chain becomes cyclic when the tail links to the head."""
    parsed = tables()
    chain = tuple(
        {
            "dependent": str(i),
            "blocker": str(i + 1),
            "action": "write",
            "execution": "native",
        }
        for i in range(1, length + 1)
    )
    acyclic = replace(parsed, assignments=(), parents=(), edges=chain)
    assert cycle_nodes(acyclic) == ()
    reverse = {
        "dependent": str(length + 1),
        "blocker": "1",
        "action": "write",
        "execution": "native",
    }
    assert cycle_nodes(replace(acyclic, edges=(*chain, reverse)))
    deferred = {**reverse, "dependent": "1", "execution": "deferred until conversion"}
    assert cycle_nodes(replace(acyclic, edges=(*chain, deferred)))
    parent = {**parsed.parents[0], "parent title": parsed.parents[0]["proposed title"]}
    assert cycle_nodes(replace(parsed, parents=(parent,)))


@given(st.permutations(tuple(range(6))))
def test_complete_page_order_property(order: list[int]) -> None:
    """Collection order cannot change a complete snapshot verdict."""
    cp1 = snapshot()
    assert complete(replace(cp1, pages=tuple(cp1.pages[index] for index in order)))


@given(st.permutations(tuple(range(4))))
def test_cp1_item_order_property(order: list[int]) -> None:
    """Source identity joins cannot depend on item presentation order."""
    cp1 = snapshot()
    validate_cp1(
        tables(), replace(cp1, items=tuple(cp1.items[index] for index in order))
    )


@given(st.text(alphabet="abc", min_size=1, max_size=12))
def test_audit_row_property(note: str) -> None:
    """Audit-only rows preserve text without changing accepted links."""
    values = list(texts())
    values[2] += f"1\t2\tjudgment: {note}\taudit only\n"
    parsed = parse_tables(*values)
    assert parsed.edges[-1]["action"] == "judgment: " + note
    assert cycle_nodes(parsed) == ()
