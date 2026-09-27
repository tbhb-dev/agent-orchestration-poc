"""Plain-value fixture and property checks for workflow forms."""

import json
import tomllib
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.workflow_forms import (
    Reference,
    blocking_findings,
    changed_forms,
    enforcement_mode,
    expected_labels,
    generated_files,
    issue_records,
    label_names,
    open_reference_numbers,
    page_items,
    refs,
    remote_mode,
    render_issue_form,
    render_reference_page,
    sections,
    valid_allowed_path,
    validate_issue,
    validate_labels,
    validate_pr,
    validate_title,
    validate_type_label,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/workflow_forms"
CONFIG_ROOT = (
    ROOT if (ROOT / "config/workflow-reference.toml").is_file() else ROOT.parent
)
REFERENCE: Reference = tomllib.loads(
    (CONFIG_ROOT / "config/workflow-reference.toml").read_text()
)


def _cases(name: str) -> list[dict[str, Any]]:
    return cast("list[dict[str, Any]]", json.loads((FIXTURES / name).read_text()))


@pytest.mark.parametrize(
    "case", _cases("issue_cases.json"), ids=lambda case: case["case"]
)
def test_issue_cases(case: dict[str, Any]) -> None:
    assert (
        list(
            validate_issue(
                case["title"], case["body"], tuple(case["labels"]), REFERENCE
            )
        )
        == case["expected"]
    )


def test_issue_with_separate_allowed_paths_field() -> None:
    case = _cases("issue_cases.json")[0]
    body = case["body"].replace(
        "Allowed paths: `config/workflow-reference.toml`, `.github/ISSUE_TEMPLATE/**`.",
        "\n## Allowed paths\nconfig/workflow-reference.toml\n.github/ISSUE_TEMPLATE/**",
    )
    assert validate_issue(case["title"], body, tuple(case["labels"]), REFERENCE) == ()
    assert (
        validate_issue(
            case["title"], body.replace("## ", "### "), tuple(case["labels"]), REFERENCE
        )
        == ()
    )


@pytest.mark.parametrize(
    ("checklist", "expected"),
    [
        ("- [x] Forms exist.", ()),
        ("- [x] Forms exist.\n- [ ] Tests pass.", ()),
        ("Forms exist.", ("Acceptance criteria needs a checkbox",)),
    ],
)
def test_issue_acceptance_checklist(checklist: str, expected: tuple[str, ...]) -> None:
    case = _cases("issue_cases.json")[0]
    body = case["body"].replace("- [ ] Forms exist.", checklist)
    assert (
        validate_issue(case["title"], body, tuple(case["labels"]), REFERENCE)
        == expected
    )


@pytest.mark.parametrize(
    ("dependency", "expected"),
    [
        ("After https://github.com/tbhb/agent-orchestration-poc/pull/81.", ()),
        ("After the template lands.", ("dependencies need an issue or PR reference",)),
    ],
)
def test_issue_dependency_url(dependency: str, expected: tuple[str, ...]) -> None:
    case = _cases("issue_cases.json")[0]
    body = case["body"].replace("After PR #81.", dependency)
    assert (
        validate_issue(case["title"], body, tuple(case["labels"]), REFERENCE)
        == expected
    )


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("gh query repos/tbhb/agent-orchestration-poc/issues/84", ()),
        ("check the issue", ("evidence needs a named path and exact command",)),
    ],
)
def test_issue_evidence_command(command: str, expected: tuple[str, ...]) -> None:
    case = _cases("issue_cases.json")[0]
    body = case["body"].replace("mise run check:workflow-forms", command)
    assert (
        validate_issue(case["title"], body, tuple(case["labels"]), REFERENCE)
        == expected
    )


@pytest.mark.parametrize("case", _cases("pr_cases.json"), ids=lambda case: case["case"])
def test_pr_cases(case: dict[str, Any]) -> None:
    assert (
        list(
            validate_pr(
                case["title"],
                case["body"],
                tuple(case["labels"]),
                frozenset(case["open"]),
                REFERENCE,
            )
        )
        == case["expected"]
    )


@pytest.mark.parametrize(
    ("path", "valid"),
    [
        ("src/**", True),
        ("AGENTS.md", True),
        ("/absolute/x", False),
        ("a/../b", False),
        ("!x", False),
        ("a/*.py", False),
    ],
)
def test_allowed_path(path: str, valid: bool) -> None:
    assert valid_allowed_path(path) is valid


@pytest.mark.parametrize(
    ("created", "cutoff", "expected"),
    [
        ("2026-09-26T00:00:00Z", "2026-09-27T00:00:00Z", "report"),
        ("2026-09-27T00:00:00Z", "2026-09-27T00:00:00Z", "enforce"),
        (None, "2026-09-27T00:00:00Z", "invalid"),
        ("2026-09-27T00:00:00Z", None, "invalid"),
    ],
)
def test_enforcement_mode(
    created: str | None, cutoff: str | None, expected: str
) -> None:
    assert enforcement_mode(created, cutoff) == expected


def test_remote_mode_requires_creation_time_during_bootstrap() -> None:
    assert remote_mode(None, None, "open") == "invalid"
    assert remote_mode("2026-09-26T00:00:00Z", None, "open") == "report"
    assert remote_mode("2026-09-26T00:00:00Z", None, "closed") == "invalid"
    assert blocking_findings(("bad",), "report") is False
    assert blocking_findings(("bad",), "enforce") is True


@pytest.mark.parametrize(
    "case", _cases("migration_cases.json"), ids=lambda case: case["case"]
)
def test_migration_cases(case: dict[str, Any]) -> None:
    assert (
        remote_mode(case["pr_created"], case["cutoff"], case["validator_state"])
        == case["expected"]
    )


@given(st.sampled_from(REFERENCE["titles"]["types"]))
def test_render_form_has_every_field(kind: str) -> None:
    form = render_issue_form(kind, REFERENCE)
    assert form == (CONFIG_ROOT / ".github/ISSUE_TEMPLATE" / f"{kind}.yml").read_text()
    assert "# do not edit" in form.splitlines()[1]
    assert all(
        f'label: "{field}"' in form for field in REFERENCE["forms"]["issue_fields"]
    )
    assert 'label: "Allowed paths"' in form


def test_generated_file_mapping_comes_from_core() -> None:
    expected = generated_files(REFERENCE)
    assert set(expected) == {
        *(
            f".github/ISSUE_TEMPLATE/{kind}.yml"
            for kind in REFERENCE["titles"]["types"]
        ),
        "docs/src/content/docs/guides/workflow-reference.md",
    }
    assert expected[".github/ISSUE_TEMPLATE/tooling.yml"] == render_issue_form(
        "tooling", REFERENCE
    )
    assert expected["docs/src/content/docs/guides/workflow-reference.md"] == (
        render_reference_page(REFERENCE)
    )
    assert (
        "## Agent provenance"
        in expected["docs/src/content/docs/guides/workflow-reference.md"]
    )


@pytest.mark.parametrize(
    ("title", "finding"),
    [
        ("unknown(workflow): add form", "unknown type: unknown"),
        ("tooling(unknown): add form", "unknown scope: unknown"),
        (
            "tooling(workflow): added form",
            "subject needs a listed imperative verb and an object",
        ),
        ("tooling(workflow): add form.", "subject ends in a period"),
    ],
)
def test_title_rejects_individual_rule_violations(title: str, finding: str) -> None:
    assert finding in validate_title(title, REFERENCE)


def test_issue_reports_missing_paths_and_evidence() -> None:
    case = _cases("issue_cases.json")[0]
    body = case["body"].replace(
        "Allowed paths: `config/workflow-reference.toml`, `.github/ISSUE_TEMPLATE/**`.",
        "",
    )
    body = body.replace("`reports/inputs/workflow-forms-evidence.md`", "evidence")
    findings = validate_issue(case["title"], body, tuple(case["labels"]), REFERENCE)
    assert "issue needs an Allowed paths list" in findings
    assert "evidence needs a named path and exact command" in findings


def test_pr_rejects_duplicate_trailers() -> None:
    case = _cases("pr_cases.json")[0]
    body = case["body"] + "\nRefs: #84"
    assert "duplicate Refs trailer" in validate_pr(
        case["title"], body, tuple(case["labels"]), frozenset({84}), REFERENCE
    )


@pytest.mark.parametrize(
    ("created", "cutoff"),
    [
        ("not-a-date", "2026-09-27T00:00:00Z"),
        ("2026-09-27T00:00:00", "2026-09-27T00:00:00Z"),
        ("2026-09-27T00:00:00Z", "2026-09-27T00:00:00"),
    ],
)
def test_enforcement_rejects_invalid_timestamps(created: str, cutoff: str) -> None:
    assert enforcement_mode(created, cutoff) == "invalid"


@given(
    st.sampled_from(REFERENCE["titles"]["types"]),
    st.text(alphabet="abc", min_size=1, max_size=8),
    st.integers(min_value=1),
)
def test_core_properties_across_reference(kind: str, word: str, number: int) -> None:
    title = f"{kind}(workflow): add {word}"
    labels = ("area/workflow", REFERENCE["types"][kind], "phase/1", "harness/codex")
    issue_body = _cases("issue_cases.json")[0]["body"]
    pr_body = _cases("pr_cases.json")[0]["body"]
    assert validate_title(title, REFERENCE) == ()
    assert sections(f"## Goal\n{word}")["Goal"] == word
    assert valid_allowed_path(f"docs/{word}")
    assert REFERENCE["types"][kind] in expected_labels(REFERENCE)
    assert validate_labels(labels, REFERENCE) == ()
    assert validate_type_label(title, labels, REFERENCE) == ()
    wrong_type = "type/bug" if kind == "feat" else "type/feature"
    wrong = ("area/workflow", wrong_type, "phase/1", "harness/codex")
    assert "title type does not match type/ label" in validate_issue(
        title, issue_body, wrong, REFERENCE
    )
    assert validate_issue(title, issue_body, labels, REFERENCE) == ()
    assert refs(f"Refs: #{number}") == (number,)
    assert validate_pr(title, pr_body, labels, frozenset({84}), REFERENCE) == ()
    assert "body must end with Refs: #<n> trailers" in validate_pr(
        title, pr_body.replace("Refs: #84", ""), labels, frozenset({84}), REFERENCE
    )
    assert "title type does not match type/ label" in validate_pr(
        title, pr_body, wrong, frozenset({84}), REFERENCE
    )
    assert enforcement_mode("2026-09-28T00:00:00Z", "2026-09-27T00:00:00Z") == "enforce"
    assert remote_mode("2026-09-28T00:00:00Z", None, "open") == "report"
    assert blocking_findings((word,), "enforce")
    assert label_names(({"name": word},)) == (word,)
    assert page_items((({"value": word},),)) == ({"value": word},)
    assert issue_records(({"number": number}, {"pull_request": {}, "number": 0})) == (
        {"number": number},
    )
    assert open_reference_numbers(
        {number: {"state": "open"}, 0: {"state": "closed"}}
    ) == frozenset({number})
    assert changed_forms({word: word}, {word: None}) == (word,)
    assert f'name: "{kind} work item"' in render_issue_form(kind, REFERENCE)
    assert f"`{kind}`" in render_reference_page(REFERENCE)
