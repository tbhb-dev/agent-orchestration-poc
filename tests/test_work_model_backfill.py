"""Synthetic table and initial snapshot tests for the work model."""

import hashlib
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
    RestValues,
    RollbackExtras,
    Snapshot,
    Tables,
    TargetInputs,
    compare_cp13,
    complete,
    cycle_nodes,
    expected_cp13,
    operation_plan,
    parse_tables,
    project_field_ids,
    rollback_values,
    snapshot_from_rest,
    title_exemptions,
    title_repairs,
    validate_cp1,
    verify_table_digests,
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
        Item(
            "title:Draft B",
            "Draft B",
            "draft",
            body="- Class: chore\n- Size: ",
            draft_id="draft-b",
            item_id="item-b",
        ),
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
    return _with_nested(Snapshot(1, (*issues, *drafts), pages, "sha"))


def _with_nested(value: Snapshot) -> Snapshot:
    """Supply one complete nested receipt for each numbered issue and endpoint."""
    nested = tuple(
        Page(f"{kind}:{item.key}", 1, count, 1, count)
        for item in value.items
        if item.issue_id
        for kind, count in (
            ("native", sum(bool(value) for _, value in item.native)),
            ("blockers", len(item.blockers)),
            ("sub_issues", sum(child.parent == item.key for child in value.items)),
        )
    )
    return replace(value, pages=(*value.pages, *nested))


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
        {"title:Draft B": ""},
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
    return _with_nested(Snapshot(1, items, pages, "after", "final"))


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


def test_approved_manifest_matches_committed_table_bytes() -> None:
    """The committed manifest pins all three approved inputs."""
    inputs = next(
        path / "reports/inputs/work-model-tables"
        for path in Path(__file__).resolve().parents
        if (path / "reports/inputs/work-model-tables").is_dir()
    )
    digests = {
        name: hashlib.sha256((inputs / filename).read_bytes()).hexdigest()
        for name, filename in (
            ("assignments", "2026-09-27-work-model-v3-final.tsv"),
            ("parents", "2026-09-27-work-model-v3-final-parents.tsv"),
            ("edges", "2026-09-27-work-model-v3-final-edges.tsv"),
        )
    }
    manifest = (inputs / "manifest.md").read_text()
    verify_table_digests(digests, manifest, markdown=True)
    with pytest.raises(ValueError, match="digest manifest differs"):
        verify_table_digests({**digests, "edges": "changed"}, manifest, markdown=True)


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
                    project=tuple(
                        sorted(
                            (name, old.get(name) or "")
                            for name in ("Status", "Size", "Area", "Harness", "Worker")
                        )
                    )
                    if old
                    else (),
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
                    body=f"- Class: {row['issue type'].lower()}\n- Size: {row['size']}",
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


def approved_creation_inputs(approved: Tables, cp1: Snapshot) -> TargetInputs:
    """Supply synthetic returned IDs and reviewed issue bodies for the final table."""
    present = {item.key for item in cp1.items}
    created = {}
    next_issue = 20000
    for row in approved.assignments:
        key = f"#{row['number']}" if row["number"] else f"title:{row['title']}"
        if row["backfill mode"] in {"draft", "issue"} and key not in present:
            issue = row["backfill mode"] == "issue"
            created[key] = Item(
                f"#{next_issue}" if issue else key,
                row["title"],
                "open" if issue else "draft",
                draft_id=f"new-draft-{key}" if not issue else "",
                issue_id=str(next_issue) if issue else "",
                item_id=f"new-item-{key}",
            )
            if issue:
                next_issue += 1
    for index, row in enumerate(approved.parents, 10000):
        created[f"title:{row['proposed title']}"] = Item(
            f"#{index}",
            row["proposed title"],
            "open",
            issue_id=str(index),
            item_id=f"new-item-{index}",
        )
    bodies = {
        f"#{row['number']}": "reviewed"
        for row in approved.assignments
        if row["body revision"] == "required"
    }
    bodies.update(
        (item.key, item.body)
        for item in cp1.items
        if item.draft_id and item.key not in bodies
    )
    closed = frozenset(
        row["number"]
        for row in approved.assignments
        if row["number"] and row["live state"] == "open" and row["state"] == "closed"
    )
    return TargetInputs(created, bodies, closed, frozenset(), REFERENCE)


def test_approved_incidents_are_open_numbered_issues_at_cp13() -> None:
    """A real issue read-back must match the planned incident creations."""
    approved, cp1 = approved_cp1_and_tables()
    inputs = approved_creation_inputs(approved, cp1)
    target = expected_cp13(approved, cp1, inputs)
    incidents = {}
    for row in approved.assignments:
        if row["backfill mode"] != "issue":
            continue
        identity = inputs.created[f"title:{row['title']}"]
        native = (("Priority", ""), ("Severity", "SEV2"), ("Work type", "Unplanned"))
        project = tuple(
            sorted(
                {
                    "Status": row["project status"],
                    "Size": row["size"],
                    "Area": row["project area"],
                    "Harness": row["project harness"],
                    "Worker": row["project worker"],
                    "Type": "Incident",
                    **dict(native),
                }.items()
            )
        )
        incidents[identity.key] = Item(
            identity.key,
            row["title"],
            "open",
            issue_type="Incident",
            native=native,
            project=project,
            issue_id=identity.issue_id,
            item_id=identity.item_id,
            body=f"## Incident\n\n{row['title']}\n\n## Record\n\n{row['note']}",
        )
    assert len(incidents) == 2
    actual = final_snapshot(tuple(incidents.get(item.key, item) for item in target))
    assert compare_cp13(target, actual, "after") == ()


@pytest.mark.parametrize("kind", ["draft", "incident", "parent"])
def test_cp13_rejects_wrong_creation_kind(kind: str) -> None:
    """Creation identities must have the resource kind the row requested."""
    approved, cp1 = approved_cp1_and_tables()
    inputs = approved_creation_inputs(approved, cp1)
    if kind == "parent":
        key = f"title:{approved.parents[0]['proposed title']}"
        wrong = replace(
            inputs.created[key], key="title:wrong", issue_id="", draft_id="wrong"
        )
    elif kind == "incident":
        row = next(
            row for row in approved.assignments if row["backfill mode"] == "issue"
        )
        key = f"title:{row['title']}"
        wrong = replace(
            inputs.created[key], key="title:wrong", issue_id="", draft_id="wrong"
        )
    else:
        row = next(
            row for row in approved.assignments if row["backfill mode"] == "draft"
        )
        key = f"title:{row['title']}"
        wrong = replace(
            inputs.created[key], key="#20002", issue_id="20002", draft_id=""
        )
    with pytest.raises(ValueError, match="creation resource kind"):
        expected_cp13(
            approved,
            cp1,
            replace(inputs, created={**inputs.created, key: wrong}),
        )


def test_cp1_rejects_changed_existing_draft_content_id() -> None:
    """The approved draft content ID is part of the preclosure identity."""
    approved, cp1 = approved_cp1_and_tables()
    d2 = next(item for item in cp1.items if item.draft_id)
    changed = replace(
        cp1,
        items=tuple(
            replace(item, draft_id="wrong-id") if item == d2 else item
            for item in cp1.items
        ),
    )
    with pytest.raises(ValueError, match="changed existing draft identity"):
        operation_plan(approved, changed)


@pytest.mark.parametrize("change", ["key", "class", "size"])
def test_cp1_rejects_draft_identity_or_classification(change: str) -> None:
    """A copied draft is checked before closures, including its body Size."""
    approved, cp1 = approved_cp1_and_tables()
    draft = next(item for item in cp1.items if item.draft_id)
    changed = {
        "key": replace(draft, key="title:wrong"),
        "class": replace(
            draft, body=draft.body.replace("Class: chore", "Class: spike")
        ),
        "size": replace(draft, body=draft.body.replace("Size: L", "Size: S")),
    }[change]
    cp1 = replace(
        cp1,
        items=tuple(changed if item == draft else item for item in cp1.items),
    )
    with pytest.raises(ValueError, match="draft key and title|draft class or Size"):
        operation_plan(approved, cp1)


def test_created_bodies_come_from_tables() -> None:
    """Returned creation bodies cannot define the reviewed CP13 target."""
    approved, cp1 = approved_cp1_and_tables()
    inputs = approved_creation_inputs(approved, cp1)
    target = expected_cp13(approved, cp1, inputs)
    parent = approved.parents[0]
    parent_item = next(
        item for item in target if item.title == parent["proposed title"]
    )
    assert parent["goal"] in parent_item.body
    assert parent["finish line"] in parent_item.body
    assert parent_item.body != inputs.created[f"title:{parent['proposed title']}"].body
    incident = next(item for item in target if item.issue_type == "Incident")
    assert "## Incident" in incident.body
    draft = next(
        item
        for item in target
        if item.draft_id and item.key not in {old.key for old in cp1.items}
    )
    for name in ("Class", "Priority", "Work type", "Severity", "Size"):
        assert f"- {name}: " in draft.body


@given(st.integers(min_value=2, max_value=5))
def test_nested_pages_require_all_receipts(page_count: int) -> None:
    """Any missing later nested page makes the snapshot incomplete."""
    cp1 = snapshot()
    selected = next(page for page in cp1.pages if page.collection == "blockers:#1")
    extra = tuple(
        replace(selected, index=index, count=0, total_pages=page_count)
        for index in range(1, page_count)
    )
    changed = replace(
        cp1,
        pages=tuple(page for page in cp1.pages if page != selected) + extra,
    )
    assert not complete(changed)


def test_rest_snapshot_filters_pr_and_counts_nested_pages() -> None:
    """REST values produce the reviewed complete issue and draft snapshot."""
    payload = json.loads((FIXTURES.parent / "runner/rest-snapshot.json").read_text())
    values = payload["raw"]
    raw = RestValues(
        values["issues"],
        tuple(Page(**page) for page in values["issue_pages"]),
        values["old"],
        values["project"],
        tuple(Page(**page) for page in values["project_pages"]),
        {key: tuple(groups) for key, groups in values["nested"].items()},
        tuple(Page(**page) for page in values["nested_pages"]),
        values["branch_sha"],
        values["run_state"],
    )
    assert (
        json.loads(json.dumps(asdict(snapshot_from_rest(raw)))) == payload["expected"]
    )
    assert complete(snapshot_from_rest(raw))
    assert not complete(
        snapshot_from_rest(replace(raw, nested_pages=raw.nested_pages[:-1]))
    )


def test_rest_snapshot_rejects_unreviewed_or_incomplete_identity() -> None:
    """A CP1 must not silently drop issue reads or duplicate Project items."""
    issue: dict[str, Any] = {
        "number": 1,
        "id": 101,
        "title": "Title",
        "state": "open",
        "labels": [],
    }
    project: dict[str, Any] = {
        "content_type": "Issue",
        "content": {"number": 1},
        "id": 201,
        "fields": [],
    }
    raw = RestValues(
        [issue],
        (Page("issues", 1, 1, 1, 1),),
        [],
        [project],
        (Page("project", 1, 1, 1, 1),),
        {"#1": ([], [], [])},
        (),
        "sha",
        "initial",
    )
    with pytest.raises(ValueError, match="page receipts"):
        snapshot_from_rest(replace(raw, issue_pages=(Page("issues", 1, 0, 1, 0),)))
    with pytest.raises(ValueError, match="nested issue reads"):
        snapshot_from_rest(replace(raw, nested={}))
    with pytest.raises(ValueError, match="duplicate Project content"):
        snapshot_from_rest(replace(raw, project=[project, project]))


def test_project_field_selection_requires_named_fields() -> None:
    """Unknown definitions cannot alter the requested Project field set."""
    names = (
        "Status",
        "Size",
        "Area",
        "Harness",
        "Worker",
        "Phase",
        "Priority",
        "Validation",
        "Validation detail",
    )
    fields = [{"id": index, "name": name} for index, name in enumerate(names, 1)]
    fields.append({"id": 99, "name": "Secret"})
    assert project_field_ids(fields) == tuple(range(1, 10))


def test_validator_owned_fields_do_not_define_cp13_target() -> None:
    """The Actions validator owns its two Project fields after backfill."""
    target = expected_cp13(tables(), snapshot(), creation_inputs())
    changed = replace(
        target[0],
        project=(
            *target[0].project,
            ("Validation", "Valid"),
            ("Validation detail", "ok"),
        ),
    )
    actual = final_snapshot((changed, *target[1:]))
    assert compare_cp13(target, actual, "after") == ()


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
        "3",
        "4",
        "5",
        "6",
        "8",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
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
        "84",
        "87",
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


def test_cp1_rejects_copied_drift_and_accepts_reviewed_status() -> None:
    """A copied Project value must match OLD unless its Status override was reviewed."""
    approved, cp1 = approved_cp1_and_tables()
    first = cp1.items[0]
    drift = replace(first, project=(("Status", "wrong-copy"),))
    changed = replace(cp1, items=(drift, *cp1.items[1:]))
    with pytest.raises(ValueError, match="changed copied Project values"):
        operation_plan(approved, changed)
    reviewed = replace(
        first, project=tuple(sorted({**dict(first.project), "Status": "Done"}.items()))
    )
    changed = replace(cp1, items=(reviewed, *cp1.items[1:]))
    operation_plan(approved, changed, {first.key: "Done"})
    closures = frozenset(
        row["number"]
        for row in approved.assignments
        if row["number"] and row["live state"] == "open" and row["state"] == "closed"
    )
    title_exemptions(
        approved,
        changed,
        closures,
        frozenset(),
        REFERENCE,
        reviewed_status={first.key: "Done"},
    )
    inputs = replace(
        approved_creation_inputs(approved, changed),
        reviewed_status={first.key: "Done"},
    )
    expected_cp13(approved, changed, inputs)
    with pytest.raises(ValueError, match="changed copied Project values"):
        operation_plan(approved, changed, {first.key: "In progress"})


def test_native_write_pinning_and_ordered_inverse() -> None:
    """Payloads omit unpinned fields and restore fields before the saved type."""
    steps = {step.number: step for step in operation_plan(tables(), snapshot())}
    assert steps["6"].native_writes[0].fields == (
        ("Priority", "Standard"),
        ("Work type", "Planned"),
    )
    assert steps["9"].native_writes[0].issue_type == "Epic"
    assert steps["9"].native_writes[0].fields == (("Work type", "Planned"),)
    assert "type=" in steps["9"].calls[0]
    assert "type=" in steps["12"].calls[0]
    assert steps["6"].reversal.index("restore saved native fields") < steps[
        "6"
    ].reversal.index("restore saved type")


@pytest.mark.parametrize(
    ("issue_type", "expected_fields"),
    [
        ("Feature", {"Priority", "Work type"}),
        ("Defect", {"Severity", "Work type"}),
        ("Chore", {"Priority", "Work type"}),
        ("Spike", {"Priority", "Work type"}),
        ("Incident", {"Severity", "Work type"}),
        ("Epic", {"Work type"}),
        ("Initiative", {"Work type"}),
    ],
)
def test_native_write_fields_follow_type_pins(
    issue_type: str, expected_fields: set[str]
) -> None:
    """Each type's write payload contains only fields pinned to that type."""
    parsed = tables()
    row = dict(parsed.assignments[0])
    row["issue type"] = issue_type
    row["severity"] = "SEV2"
    changed = replace(parsed, assignments=(row, *parsed.assignments[1:]))
    write = {step.number: step for step in operation_plan(changed, snapshot())}[
        "6"
    ].native_writes[0]
    assert write.issue_type == issue_type
    assert {name for name, _ in write.fields} == expected_fields


def test_added_membership_uses_existing_issue_identity() -> None:
    """Adding an existing issue to the Project changes only its item identity."""
    parsed, cp1 = tables(), snapshot()
    first = replace(cp1.items[0], item_id="")
    cp1 = replace(
        cp1,
        items=(first, *cp1.items[1:]),
        pages=tuple(
            replace(page, count=page.count - 1, total_count=page.total_count - 1)
            if page.collection == "project"
            else page
            for page in cp1.pages
        ),
    )
    operation_plan(parsed, cp1)
    with pytest.raises(ValueError, match="added Project membership is incomplete"):
        expected_cp13(parsed, cp1, creation_inputs())
    inputs = replace(creation_inputs(), added_items={"#1": "new-item-1"})
    target = expected_cp13(parsed, cp1, inputs)
    assert target[0].issue_id == first.issue_id
    assert target[0].item_id == "new-item-1"
    assert compare_cp13(target, final_snapshot(target), "after") == ()
    rollback = rollback_values(
        tables(),
        cp1,
        {},
        tuple(item.item_id for item in cp1.items if item.item_id),
        "open",
        extras=RollbackExtras(added_items=inputs.added_items),
    )
    assert rollback.added_items == (("#1", "new-item-1"),)


def test_existing_d2_draft_requires_corrected_body() -> None:
    """The approved D2 correction is required even with an empty revision cell."""
    approved, cp1 = approved_cp1_and_tables()
    d2 = next(
        item
        for item in cp1.items
        if item.title == "tooling(docs): move diagrams from Mermaid to D2"
    )
    cp1 = replace(
        cp1,
        items=tuple(
            replace(item, body=f"{item.body}\nold planned") if item == d2 else item
            for item in cp1.items
        ),
    )
    incomplete = approved_creation_inputs(approved, cp1)
    with pytest.raises(ValueError, match="reviewed body is missing"):
        expected_cp13(
            approved,
            cp1,
            replace(
                incomplete,
                bodies={
                    key: body
                    for key, body in incomplete.bodies.items()
                    if key != d2.key
                },
            ),
        )
    inputs = approved_creation_inputs(approved, cp1)
    inputs = replace(inputs, bodies={**inputs.bodies, d2.key: "corrected unplanned"})
    target = expected_cp13(approved, cp1, inputs)
    corrected = next(item for item in target if item.key == d2.key)
    assert (corrected.item_id, corrected.draft_id) == (d2.item_id, d2.draft_id)
    assert any(
        d.field == "body"
        for d in compare_cp13(
            target,
            final_snapshot(
                tuple(
                    replace(item, body="old planned") if item.key == d2.key else item
                    for item in target
                )
            ),
            "after",
        )
    )
    already_correct = replace(
        cp1,
        items=tuple(
            replace(item, body=f"{item.body}\ncorrected unplanned")
            if item.key == d2.key
            else item
            for item in cp1.items
        ),
    )
    target = expected_cp13(approved, already_correct, inputs)
    assert (
        "corrected unplanned"
        in next(item for item in target if item.key == d2.key).body
    )


def test_existing_draft_body_is_preserved_after_classification() -> None:
    """An existing draft's reviewed body survives CP13 byte-for-byte."""
    approved, cp1 = approved_cp1_and_tables()
    title = "tooling(workers): report worker completion without process exit"
    row = next(row for row in approved.assignments if row["title"] == title)
    draft = next(item for item in cp1.items if item.title == title)
    body = (
        f"- Class: {row['issue type'].lower()}\n"
        f"- Priority: {row['priority']}\n"
        f"- Work type: {row['work type']}\n"
        f"- Severity: {row['severity'] or 'none'}\n"
        f"- Size: {row['size']}\n\n"
        "## Context\n\nKeep the worker session available.\n"
    )
    cp1 = replace(
        cp1,
        items=tuple(
            replace(item, body=body) if item == draft else item for item in cp1.items
        ),
    )
    validate_cp1(approved, cp1)
    inputs = approved_creation_inputs(approved, cp1)
    target = expected_cp13(approved, cp1, inputs)
    assert next(item for item in target if item.key == draft.key).body == body
    unchanged = tuple(
        replace(item, body=body) if item.key == draft.key else item for item in target
    )
    assert compare_cp13(target, final_snapshot(unchanged), "after") == ()


def test_revoked_closed_title_needs_valid_replacement() -> None:
    """Reclosing after revocation cannot bless the old invalid title."""
    inputs = replace(creation_inputs(), revoked=frozenset({"2"}))
    with pytest.raises(ValueError, match="invalid non-exempt title"):
        expected_cp13(tables(), snapshot(), inputs)


def test_partial_created_issue_is_rollback_input() -> None:
    """An issue creation remains reversible before its Project item exists."""
    cp1 = snapshot()
    partial = Item("#3", "epic: migration", "open", issue_id="3")
    rollback = rollback_values(
        tables(),
        cp1,
        {"title:epic: migration": partial},
        tuple(item.item_id for item in cp1.items),
        "open",
    )
    assert rollback.created == (partial,)


@pytest.mark.parametrize("native", [(), (("Work type", "Planned"),)])
def test_partial_issue_before_project_addition_keeps_number(
    native: tuple[tuple[str, str], ...],
) -> None:
    """Failure before or after field write leaves a closable created issue."""
    cp1 = snapshot()
    created = Item("#3", "epic: migration", "open", issue_id="3", native=native)
    result = rollback_values(
        tables(),
        cp1,
        {"title:epic: migration": created},
        tuple(item.item_id for item in cp1.items),
        "open",
    )
    assert result.created[0].issue_id == "3"
    assert result.created[0].item_id == ""


@pytest.mark.parametrize(
    ("key", "field", "value"),
    [
        ("title:epic: migration", "key", "#1"),
        ("title:epic: migration", "issue_id", "1"),
        ("title:epic: migration", "item_id", "item-1"),
        ("title:Draft A", "draft_id", "draft-b"),
    ],
)
def test_rollback_rejects_created_identity_colliding_with_cp1(
    key: str, field: str, value: str
) -> None:
    """An inverse must never delete or close a resource saved at CP1."""
    cp1 = snapshot()
    created = creation_inputs().created
    changed = {**created, key: replace(created[key], **cast("Any", {field: value}))}
    with pytest.raises(ValueError, match="created identity collides with CP1"):
        rollback_values(
            tables(), cp1, changed, tuple(item.item_id for item in cp1.items), "open"
        )


@pytest.mark.parametrize("field", ["key", "issue_id", "item_id", "draft_id"])
def test_rollback_rejects_created_identity_colliding_with_creation(field: str) -> None:
    """Two creation results cannot claim the same returned resource."""
    approved, cp1 = approved_cp1_and_tables()
    created = approved_creation_inputs(approved, cp1).created
    if field == "draft_id":
        keys = [key for key, item in created.items() if item.draft_id]
    else:
        keys = [f"title:{row['proposed title']}" for row in approved.parents]
    first, second = keys[:2]
    created[second] = replace(
        created[second], **cast("Any", {field: getattr(created[first], field)})
    )
    with pytest.raises(ValueError, match="created identity"):
        rollback_values(
            approved, cp1, created, tuple(item.item_id for item in cp1.items), "open"
        )


@pytest.mark.parametrize("kind", ["draft", "parent", "incident"])
def test_rollback_rejects_wrong_creation_kind(kind: str) -> None:
    """Rollback must follow the planned draft or numbered issue operation."""
    if kind == "incident":
        planned, cp1 = approved_cp1_and_tables()
        created = approved_creation_inputs(planned, cp1).created
        row = next(
            row for row in planned.assignments if row["backfill mode"] == "issue"
        )
        key = f"title:{row['title']}"
    else:
        planned, cp1 = tables(), snapshot()
        created = creation_inputs().created
        key = "title:Draft A" if kind == "draft" else "title:epic: migration"
    item = created[key]
    wrong = (
        replace(item, key="#9", draft_id="", issue_id="9")
        if kind == "draft"
        else replace(item, key="title:wrong", draft_id="wrong", issue_id="")
    )
    with pytest.raises(ValueError, match="creation resource kind differs from plan"):
        rollback_values(
            planned,
            cp1,
            {key: wrong},
            tuple(item.item_id for item in cp1.items),
            "open",
        )


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
    for item in (*actual, *saved):
        item.pop("body")
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
            field: value + (("unexpected", "value"),)
            if field == "native"
            else value + ("unexpected",)
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
        changed, snapshot(), replace(inputs, bodies={**inputs.bodies, "#1": "reviewed"})
    )
    assert supplied[0].body == "reviewed"


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("issue_id", "1", "created identity collides with CP1"),
        ("item_id", "item-1", "created identity collides with CP1"),
        ("key", "#1", "created identity collides with CP1"),
        ("key", "wrong", "creation resource kind differs from plan"),
    ],
)
def test_created_parent_identity_must_be_new(
    field: str, value: str, error: str
) -> None:
    """Returned parent IDs cannot alias CP1 or lose their numbered identity."""
    inputs = creation_inputs()
    parent = inputs.created["title:epic: migration"]
    changed = replace(parent, **cast("Any", {field: value}))
    created = {**inputs.created, "title:epic: migration": changed}
    with pytest.raises(ValueError, match=error):
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
    cp1 = _with_nested(replace(cp1, items=(old, *cp1.items[1:]), pages=cp1.pages[:6]))
    created = creation_inputs().created
    order = tuple(item.item_id for item in cp1.items)
    rollback = rollback_values(
        tables(), cp1, created, order, "open", extras=RollbackExtras(("2",))
    )
    assert rollback.prior[0] == old
    assert set(rollback.created) == set(created.values())
    assert rollback.order == order
    assert rollback.pr_state == "open"
    assert rollback.branch_sha == "sha"
    assert rollback.exemptions == ("2",)
    with pytest.raises(ValueError, match="incomplete saved Project order"):
        rollback_values(tables(), cp1, created, order[:-1], "open")
    with pytest.raises(ValueError, match="created identity is incomplete"):
        rollback_values(
            tables(),
            cp1,
            {"parent": replace(next(iter(created.values())), item_id="", draft_id="")},
            order,
            "open",
        )


@given(st.permutations(["item-1", "item-2", "item-b", "item-held"]))
def test_rollback_preserves_any_complete_order(order: list[str]) -> None:
    """A reviewed reversal can restore the exact original sequence."""
    assert rollback_values(
        tables(), snapshot(), {}, tuple(order), "open"
    ).order == tuple(order)


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
    cp1 = _with_nested(Snapshot(1, (item,), pages, "sha"))
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


@given(st.permutations(tuple(range(12))))
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
