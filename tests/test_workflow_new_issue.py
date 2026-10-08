"""Local issue creation checks with no GitHub network calls."""

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.workflow_forms import validate_issue

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = tomllib.loads((ROOT / "config/workflow-reference.toml").read_text())
TITLE = "docs(workflow): document filing"
LABELS = ("area/workflow", "type/chore", "phase/2", "harness/codex")
BODY = """## Goal
Document filing.
## Context and links
See the workflow reference.
## Dependencies and paths
Related: #317.
## Allowed paths
docs/src/content/docs/workflow/**
## Acceptance criteria
- [ ] The task passes.
## Evidence required
Run `mise run check` and read `tests/test_workflow_new_issue.py`.
## Docs impact
Update the workflow reference.
## Out of scope
Changing required fields.
"""


@pytest.mark.parametrize(
    "section",
    REFERENCE["forms"]["issue_fields"] + ["Allowed paths"],
)
def test_missing_section_is_refused(section: str) -> None:
    shortened = BODY.replace(f"## {section}\n", "## Removed\n")
    findings = validate_issue(TITLE, shortened, LABELS, REFERENCE)
    assert findings
    if section != "Allowed paths":
        assert f"missing or empty section: {section}" in findings
    else:
        assert "issue needs an Allowed paths list" in findings


@given(st.sampled_from(REFERENCE["forms"]["issue_fields"]))
def test_removing_a_required_field_always_fails(section: str) -> None:
    shortened = BODY.replace(f"## {section}\n", "## Removed\n")
    assert validate_issue(TITLE, shortened, LABELS, REFERENCE)


def test_valid_issue_passes() -> None:
    assert validate_issue(TITLE, BODY, LABELS, REFERENCE) == ()


def _fake_gh(tmp_path: Path) -> tuple[Path, Path]:
    binary = tmp_path / "gh"
    calls = tmp_path / "calls"
    binary.write_text(
        f"#!{sys.executable}\n"
        "import os, pathlib, sys\n"
        "pathlib.Path(os.environ['GH_CALLS']).write_text(repr(sys.argv[1:]) + '\\n' + sys.stdin.read())\n"
    )
    binary.chmod(0o700)
    return binary, calls


def _run_issue(tmp_path: Path, body_file: Path) -> subprocess.CompletedProcess[str]:
    _, calls = _fake_gh(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "GH_CALLS": str(calls),
    }
    args = [
        sys.executable,
        "-m",
        "agent_orchestration_poc.shell.workflow_new_issue",
        "--title",
        TITLE,
    ]
    for label in LABELS:
        args.extend(("--label", label))
    args.extend(("--body-file", str(body_file)))
    return subprocess.run(args, capture_output=True, text=True, check=False, env=env)


@pytest.mark.integration
def test_valid_issue_invokes_gh_with_validated_body(tmp_path: Path) -> None:
    body_file = tmp_path / "body.md"
    body_file.write_text(BODY)
    result = _run_issue(tmp_path, body_file)
    assert result.returncode == 0
    assert (tmp_path / "calls").read_text().endswith("\n" + BODY)
    assert "'issue', 'create'" in (tmp_path / "calls").read_text()


@pytest.mark.integration
def test_invalid_issue_reports_all_findings_without_gh(tmp_path: Path) -> None:
    result = _run_issue(tmp_path, ROOT / "tests/fixtures/invalid-issue.md")
    assert result.returncode != 0
    assert "missing or empty section: Context and links" in result.stderr
    assert "missing or empty section: Out of scope" in result.stderr
    assert not (tmp_path / "calls").exists()
