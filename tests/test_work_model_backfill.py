"""Synthetic table and initial snapshot tests for the work model."""

import json
import tomllib
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.work_model_backfill import (
    SOURCE_PROJECT_FIELDS,
    Difference,
    Item,
    Page,
    Snapshot,
    Tables,
    TargetInputs,
    compare_cp13,
    complete,
    cycle_nodes,
    expected_cp13,
    operation_plan,
    parse_tables,
    rollback_values,
    title_exemptions,
    title_repairs,
    validate_cp1,
)

FIXTURES = Path(__file__).parent / "fixtures/work_model_backfill/plan"
ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = (
    ROOT if (ROOT / "config/workflow-reference.toml").is_file() else ROOT.parent
)
REFERENCE = tomllib.loads((CONFIG_ROOT / "config/workflow-reference.toml").read_text())


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


def creation_inputs() -> TargetInputs:
    """Represent only returned identities and saved content from creation calls."""
    return TargetInputs(
        {
            "title:Draft A": Item(
                "title:Draft A",
                "Draft A",
                "draft",
                draft_id="draft-a",
                item_id="item-a",
            ),
            "title:epic: migration": Item(
                "#3",
                "epic: migration",
                "open",
                issue_id="3",
                item_id="item-3",
                body="Goal and finish line",
            ),
        },
        {},
        frozenset({"2"}),
        frozenset(),
        REFERENCE,
    )


def final_snapshot(items: tuple[Item, ...]) -> Snapshot:
    """Build independently counted complete CP13 pagination receipts."""
    issues = sum(bool(item.issue_id) for item in items)
    drafts = sum(bool(item.draft_id) for item in items)
    project = sum(bool(item.item_id) for item in items)
    pages = tuple(
        Page(name, 1, count, 1, count)
        for name, count in (
            ("issues", issues),
            ("project", project),
            ("drafts", drafts),
            ("native", issues),
            ("parents", issues),
            ("blockers", issues),
        )
    )
    return Snapshot(1, items, pages, "after", "final")


def approved_tables() -> Tables:
    """Read the committed final revision by supplied paths."""
    inputs = next(
        path / "reports/inputs/work-model-tables"
        for path in Path(__file__).resolve().parents
        if (path / "reports/inputs/work-model-tables").is_dir()
    )
    return parse_tables(
        (inputs / "2026-09-27-work-model-v3-final.tsv").read_text(),
        (inputs / "2026-09-27-work-model-v3-final-parents.tsv").read_text(),
        (inputs / "2026-09-27-work-model-v3-final-edges.tsv").read_text(),
    )


def approved_cp1_and_tables() -> tuple[Tables, Snapshot]:
    """Construct a complete plain-value CP1 from approved saved row values."""
    approved = approved_tables()
    items = []
    for row in approved.assignments:
        if row["number"]:
            old: dict[str, str | None] = (
                json.loads(row["old project fields"])
                if row["old project fields"]
                else {}
            )
            source = (
                tuple(
                    sorted(
                        (name, old.get(name) or "") for name in SOURCE_PROJECT_FIELDS
                    )
                )
                if old
                else ()
            )
            items.append(
                Item(
                    f"#{row['number']}",
                    row["title"],
                    row["live state"],
                    row["state reason"],
                    source_project=source,
                    issue_id=row["target content id"] or row["number"],
                    item_id=row["target project item"] or f"copied-{row['number']}",
                )
            )
        elif row["backfill mode"] == "existing draft":
            items.append(
                Item(
                    f"title:{row['title']}",
                    row["title"],
                    "draft",
                    draft_id=row["target content id"],
                    item_id=row["target project item"],
                )
            )
    cp1 = replace(
        final_snapshot(tuple(items)),
        branch_sha="approved-input-cp1",
        run_state="initial",
    )
    return approved, cp1


def test_approved_table_counts_and_numbered_exemptions() -> None:
    """Derive the final revision's counts and manifest from its supplied rows."""
    approved, cp1 = approved_cp1_and_tables()
    assert (len(approved.assignments), len(approved.parents), len(approved.edges)) == (
        191,
        22,
        387,
    )
    validate_cp1(approved, cp1)
    closures = frozenset(
        row["number"]
        for row in approved.assignments
        if row["number"] and row["live state"] == "open" and row["state"] == "closed"
    )
    exemptions = title_exemptions(approved, cp1, closures, frozenset(), REFERENCE)
    assert exemptions == (
        "4",
        "5",
        "6",
        "8",
        "11",
        "12",
        "13",
        "14",
        "15",
        "26",
        "30",
        "58",
        "59",
        "60",
        "61",
        "62",
        "63",
        "69",
        "71",
        "72",
        "77",
        "78",
        "83",
        "96",
        "104",
        "110",
        "114",
        "125",
        "132",
        "154",
        "161",
        "167",
        "168",
        "169",
        "173",
        "177",
        "178",
        "184",
        "185",
        "187",
    )
    repairs = title_repairs(approved, REFERENCE)
    assert len(repairs) == 70
    assert sum(changed for _, changed in repairs) == 18
    plan = {step.number: step for step in operation_plan(approved, cp1)}
    assert len(plan["0"].targets) == 13
    assert len(plan["6T"].targets) == 70
    assert len(plan["9"].targets) == 22
    assert all(title.startswith("initiative:") for title in plan["9"].targets[:5])
    assert len(plan["12"].targets) == 2


def test_ordered_plan_covers_every_stage_and_saved_reversal() -> None:
    """Keep every approved step, target disposition, checkpoint, and reversal."""
    steps = operation_plan(tables(), snapshot())
    assert tuple(step.number for step in steps) == (
        "1",
        "0",
        "2",
        "3",
        "4",
        "5",
        "6",
        "6T",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
    )
    assert all(step.saved_inputs and step.check and step.reversal for step in steps)
    assert {step.number for step in steps if not step.calls} == {"2", "14"}
    by_number = {step.number: step for step in steps}
    assert by_number["0"].targets == ("2",)
    assert by_number["6"].targets == ("1", "2", "title:Draft A", "title:Draft B")
    assert by_number["6T"].targets == ("1",)
    assert by_number["9"].targets == ("epic: migration",)
    assert by_number["10"].targets == ("#1", "#2")
    assert by_number["11"].targets == ("1 <- 2",)
    assert "no link" not in repr(by_number["11"].targets)
    assert "judgment" not in repr(by_number["11"].targets)
    assert by_number["13"].calls
    assert "operator confirmation" in by_number["13"].check


def test_operation_contract_matches_reviewed_fixture() -> None:
    """Freeze every stage's calls, saved values, check, and reversal."""
    saved = json.loads((FIXTURES / "operations.json").read_text())
    actual = [asdict(step) for step in operation_plan(tables(), snapshot())]
    assert json.loads(json.dumps(actual)) == saved


def test_exemptions_require_closure_and_reopen_revokes_permanently() -> None:
    """A target-closed invalid title is keyed by number only after CP0."""
    with pytest.raises(ValueError, match="planned closure is not confirmed"):
        title_exemptions(tables(), snapshot(), frozenset(), frozenset(), REFERENCE)
    assert title_exemptions(
        tables(), snapshot(), frozenset({"2"}), frozenset(), REFERENCE
    ) == ("2",)
    assert (
        title_exemptions(
            tables(), snapshot(), frozenset({"2"}), frozenset({"2"}), REFERENCE
        )
        == ()
    )
    assert title_repairs(tables(), REFERENCE) == (("1", False),)


@given(st.sets(st.sampled_from(["1", "2", "999"])))
def test_exemption_revocation_never_adds_a_number(revoked: set[str]) -> None:
    """Any persisted reopen history only removes eligible exemptions."""
    result = title_exemptions(
        tables(), snapshot(), frozenset({"2"}), frozenset(revoked), REFERENCE
    )
    assert set(result) <= {"2"} - revoked


def test_scope_change_requires_new_verdict_and_replacement_validity() -> None:
    """Only a changed scope token needs a new refinement verdict."""
    parsed = tables()
    first = dict(parsed.assignments[0])
    first["proposed title"] = "tooling(workflow): build a model"
    first["refinement verdict"] = "new verdict required"
    changed = replace(parsed, assignments=(first, *parsed.assignments[1:]))
    assert title_repairs(changed, REFERENCE) == (("1", True),)
    first["refinement verdict"] = "preserve prior verdict if body unchanged"
    with pytest.raises(ValueError, match="scope-change verdict disposition differs"):
        title_repairs(changed, REFERENCE)
    first["proposed title"] = "invalid"
    with pytest.raises(ValueError, match="invalid replacement title"):
        title_repairs(changed, REFERENCE)


def test_cp13_uses_created_ids_and_compares_every_saved_value() -> None:
    """Build from table and CP1 values, then detect read-back drift by identity."""
    target = expected_cp13(tables(), snapshot(), creation_inputs())
    by_key = {item.key: item for item in target}
    assert by_key["#2"].title == "legacy title"
    assert by_key["#2"].state_reason == "not_planned"
    assert by_key["#1"].parent == "#3"
    assert by_key["#1"].blockers == ("#2",)
    assert by_key["#3"].issue_type == "Epic"
    assert dict(by_key["#1"].native)["Priority"] == "Standard"
    assert dict(by_key["#1"].project)["Type"] == "Chore"
    assert dict(by_key["title:Draft A"].project)["Priority"] == ""
    assert by_key["title:Held"].draft_id == "draft-held"
    assert compare_cp13(target, final_snapshot(target), "after") == ()
    assert compare_cp13(target, final_snapshot(target), "before") == (
        Difference("branch", "sha", "before", "after"),
    )
    changed = replace(by_key["#1"], native=(("Priority", "Intangible"),), parent="")
    after = final_snapshot(
        tuple(changed if item.key == "#1" else item for item in target)
    )
    assert {
        difference.field for difference in compare_cp13(target, after, "after")
    } == {
        "native",
        "parent",
    }


def test_target_matches_reviewed_snapshot_fixture() -> None:
    """Freeze every expected synthetic value, including held draft identity."""
    saved = json.loads((FIXTURES / "expected-cp13.json").read_text())
    actual = [
        asdict(item) for item in expected_cp13(tables(), snapshot(), creation_inputs())
    ]
    assert json.loads(json.dumps(actual)) == saved


@pytest.mark.parametrize(
    "field",
    [
        "title",
        "state",
        "issue_type",
        "native",
        "project",
        "parent",
        "blockers",
        "body",
        "labels",
        "issue_id",
        "item_id",
    ],
)
def test_cp13_reports_each_changed_field(field: str) -> None:
    """No expected issue read-back value is silently omitted."""
    target = expected_cp13(tables(), snapshot(), creation_inputs())
    before = target[0]
    value = getattr(before, field)
    changed = cast("Any", replace)(
        before,
        **{
            field: value + ("unexpected",)
            if isinstance(value, tuple)
            else str(value) + "unexpected"
        },
    )
    actual = final_snapshot((changed, *target[1:]))
    assert any(
        difference.key == before.key and difference.field == field
        for difference in compare_cp13(target, actual, "after")
    )


def test_cp13_refuses_missing_page_or_item() -> None:
    """A partial collection cannot compare equal to a full target."""
    target = expected_cp13(tables(), snapshot(), creation_inputs())
    actual = final_snapshot(target)
    with pytest.raises(ValueError, match="incomplete or incompatible CP13"):
        compare_cp13(target, replace(actual, pages=actual.pages[:-1]), "after")
    missing = target[:-1]
    assert compare_cp13(target, final_snapshot(missing), "after")[0].field == "presence"


def test_cp13_refuses_missing_creation_or_reviewed_body() -> None:
    """Do not infer returned IDs or revised body text from a title."""
    inputs = creation_inputs()
    with pytest.raises(ValueError, match="creation map is incomplete or unexpected"):
        expected_cp13(tables(), snapshot(), replace(inputs, created={}))
    first = dict(tables().assignments[0])
    first["body revision"] = "required"
    changed = replace(tables(), assignments=(first, *tables().assignments[1:]))
    with pytest.raises(ValueError, match="reviewed body is missing"):
        expected_cp13(changed, snapshot(), inputs)
    supplied = expected_cp13(
        changed, snapshot(), replace(inputs, bodies={"#1": "reviewed"})
    )
    assert supplied[0].body == "reviewed"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("issue_id", "1"),
        ("item_id", "item-1"),
        ("key", "#1"),
        ("key", "wrong"),
    ],
)
def test_created_parent_identity_must_be_new(field: str, value: str) -> None:
    """Returned parent IDs cannot alias CP1 or lose their numbered identity."""
    inputs = creation_inputs()
    parent = inputs.created["title:epic: migration"]
    changed = replace(parent, **cast("Any", {field: value}))
    created = {**inputs.created, "title:epic: migration": changed}
    with pytest.raises(ValueError, match="created identity collides with CP1"):
        expected_cp13(tables(), snapshot(), replace(inputs, created=created))


def test_comparison_refuses_duplicate_returned_identity() -> None:
    """Two CP13 records with the same key are ambiguous even with full pages."""
    target = expected_cp13(tables(), snapshot(), creation_inputs())
    duplicated = final_snapshot((target[0], *target[:-1]))
    with pytest.raises(ValueError, match="duplicate CP13 identity"):
        compare_cp13(target, duplicated, "after")


def test_rollback_uses_exact_saved_values_and_created_ids() -> None:
    """Retain prior fields, labels, links, body, state, title, and order."""
    cp1 = snapshot()
    old = replace(
        cp1.items[0],
        body="prior",
        labels=("type/tooling", "keep"),
        blockers=("#2",),
        native=(("Priority", "Standard"),),
        project=(("Status", "Ready"),),
    )
    cp1 = replace(cp1, items=(old, *cp1.items[1:]))
    created = creation_inputs().created
    order = tuple(item.item_id for item in cp1.items)
    rollback = rollback_values(cp1, created, order, "open", ("2",))
    assert rollback.prior[0] == old
    assert set(rollback.created) == set(created.values())
    assert rollback.order == order
    assert rollback.pr_state == "open"
    assert rollback.branch_sha == "sha"
    assert rollback.exemptions == ("2",)
    with pytest.raises(ValueError, match="incomplete saved Project order"):
        rollback_values(cp1, created, order[:-1], "open")
    with pytest.raises(ValueError, match="created identity is incomplete"):
        rollback_values(
            cp1,
            {"parent": replace(next(iter(created.values())), item_id="")},
            order,
            "open",
        )


@given(st.permutations(["item-1", "item-2", "item-b", "item-held"]))
def test_rollback_preserves_any_complete_order(order: list[str]) -> None:
    """A reviewed reversal can restore the exact original sequence."""
    assert rollback_values(snapshot(), {}, tuple(order), "open").order == tuple(order)


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
        ("source_project", (("Status", "drift"),), "changed source Project values"),
        ("issue_id", "", "unresolved source issue id"),
    ],
)
def test_stale_issue_fails(
    field: str, value: str | tuple[tuple[str, str], ...], message: str
) -> None:
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
            changed = replace(cp1.items[0], source_project=(("Status", "drift"),))
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


def test_approved_closure_uses_source_project_values() -> None:
    """Accept #168 before closure, then reject drift from its saved old Project values."""
    approved = approved_tables()
    row = next(row for row in approved.assignments if row["number"] == "168")
    source = tuple(
        sorted(
            (
                ("Status", "Refinement"),
                ("Phase", "2"),
                ("Priority", "P0"),
                ("Size", ""),
                ("Area", ""),
                ("Harness", ""),
                ("Worker", ""),
            )
        )
    )
    item = Item(
        key="#168",
        title=row["title"],
        state="open",
        state_reason="not_planned",
        issue_id="168",
        source_project=source,
    )
    pages = tuple(
        Page(name, 1, count, 1, count)
        for name, count in (
            ("issues", 1),
            ("project", 0),
            ("drafts", 0),
            ("native", 1),
            ("parents", 1),
            ("blockers", 1),
        )
    )
    cp1 = Snapshot(1, (item,), pages, "sha")
    selected = Tables(approved.version, (row,), (), ())
    validate_cp1(selected, cp1)
    drift = replace(
        item,
        source_project=tuple(
            sorted(
                ("Status", "Done") if field == "Status" else (field, value)
                for field, value in source
            )
        ),
    )
    with pytest.raises(ValueError, match="^changed source Project values$"):
        validate_cp1(selected, replace(cp1, items=(drift,)))


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


def test_new_draft_already_in_cp1_is_reused() -> None:
    """Match an early created draft by unique title without a second creation."""
    cp1 = snapshot()
    found = replace(cp1.items[-1], key="title:Draft A", title="Draft A")
    cp1 = replace(cp1, items=(*cp1.items[:-1], found))
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


def test_final_header_rejects_phase() -> None:
    """Reject the deleted Phase field and the earlier project size name."""
    values = list(texts())
    for old, new in (("size", "project phase"), ("size", "project size")):
        changed = values.copy()
        changed[0] = changed[0].replace(f"\t{old}\t", f"\t{new}\t", 1)
        with pytest.raises(ValueError, match="^table header is incomplete$"):
            parse_tables(*changed)


def test_preapplied_title_and_existing_draft_id() -> None:
    """Accept an already applied title and reject a changed draft item ID."""
    cp1 = snapshot()
    cp1 = replace(
        cp1,
        items=(
            replace(cp1.items[0], title="tooling(project): build a model"),
            *cp1.items[1:],
        ),
    )
    validate_cp1(tables(), cp1)
    values = list(texts())
    lines = values[0].splitlines()
    header = lines[0].split("\t")
    cells = lines[-1].split("\t")
    cells[header.index("target project item")] = "different"
    lines[-1] = "\t".join(cells)
    values[0] = "\n".join(lines) + "\n"
    with pytest.raises(ValueError, match="^changed existing draft identity$"):
        validate_cp1(parse_tables(*values), snapshot())
