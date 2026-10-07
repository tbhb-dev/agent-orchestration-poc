"""Pure gate comparison and pull request reason fixtures."""

import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.gate_changes import compare, match_justifications
from agent_orchestration_poc.shell.gate_changes import run

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/gate_changes"
REGISTRY = tomllib.loads((ROOT / "config/gate-registry.toml").read_text())
CASES = cast("list[dict[str, str]]", json.loads((FIXTURES / "cases.json").read_text()))
SUPPRESSIONS = cast(
    "list[dict[str, str]]",
    json.loads((FIXTURES / "suppression_cases.json").read_text()),
)


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_registered_config_cases(case: dict[str, str]) -> None:
    findings = compare(
        {case["path"]: case["before"]}, {case["path"]: case["after"]}, REGISTRY
    )
    assert any(finding.id.startswith(f"gate:{case['kind']}:") for finding in findings)


@pytest.mark.parametrize(
    "entry", REGISTRY["thresholds"], ids=lambda entry: entry["key"]
)
def test_each_threshold_direction(entry: dict[str, Any]) -> None:
    path = entry["path"]
    before = (ROOT / path).read_text()
    match = re.search(entry["pattern"], before)
    assert match is not None
    value = int(match.group("value"))
    weaker = value - 1 if entry["direction"] == "floor" else value + 1
    after = before[: match.start("value")] + str(weaker) + before[match.end("value") :]
    findings = compare({path: before}, {path: after}, REGISTRY)
    assert any(f.id.startswith(f"gate:threshold:{path}:") for f in findings)
    assert compare({path: before}, {path: before}, REGISTRY) == ()


@pytest.mark.parametrize("entry", REGISTRY["required"], ids=lambda entry: entry["key"])
def test_each_required_gate_removal(entry: dict[str, Any]) -> None:
    path = entry["path"]
    before = (ROOT / path).read_text()
    match = re.search(entry["pattern"], before)
    assert match is not None
    after = before[: match.start()] + before[match.end() :]
    findings = compare({path: before}, {path: after}, REGISTRY)
    assert any(f.id == f"gate:gate:{path}:{entry['key']}:removed" for f in findings)


@pytest.mark.parametrize("case", SUPPRESSIONS, ids=lambda case: case["kind"])
def test_each_supported_suppression(case: dict[str, str]) -> None:
    entry = next(
        entry for entry in REGISTRY["suppressions"] if entry["kind"] == case["kind"]
    )
    line = case["line"]
    assert re.search(entry["pattern"], line)
    findings = compare({case["path"]: ""}, {case["path"]: line}, REGISTRY)
    assert any(case["kind"] in f.id for f in findings)


def test_added_exclusion_and_disabled_gate() -> None:
    before = (
        '{"ignore": ["old"], "linter": {"enabled": true, "rules": {"complexity": {}}}}'
    )
    after = '{"ignore": ["old", "new"], "linter": {"enabled": false, "rules": {}}}'
    findings = compare({"biome.json": before}, {"biome.json": after}, REGISTRY)
    assert any(f.id.startswith("gate:exclusion:") for f in findings)
    assert any(f.id == "gate:gate:biome.json:complexity:removed" for f in findings)


def test_lint_exclusion_and_rule_disable() -> None:
    before = (ROOT / ".golangci.yml").read_text()
    after = before.replace(
        "      - path: _test\\.go",
        "      - path: generated\\.go\n      - path: _test\\.go",
    )
    findings = compare({".golangci.yml": before}, {".golangci.yml": after}, REGISTRY)
    assert any(f.id.startswith("gate:exclusion:.golangci.yml:") for f in findings)

    before_biome = (ROOT / "biome.json").read_text()
    after_biome = before_biome.replace('"level": "error"', '"level": "off"', 1)
    findings = compare(
        {"biome.json": before_biome}, {"biome.json": after_biome}, REGISTRY
    )
    assert any(f.id == "gate:gate:biome.json:rule-level:disabled" for f in findings)


def test_python_literal_is_not_a_suppression() -> None:
    value = (FIXTURES / "python_literal.txt").read_text()
    assert compare({"sample.py": ""}, {"sample.py": value}, REGISTRY) == ()


def test_partial_duplicate_and_orphan_reasons() -> None:
    findings = compare({"mise.toml": "a"}, {"mise.toml": "b"}, REGISTRY)
    identifier = findings[0].id
    body = f"## Gate justifications\n\n- {identifier}: reason\n- {identifier}: repeated\n- gate:selector:orphan:file:changed: old\n"
    problems = match_justifications(findings, body)
    assert f"duplicate justification: {identifier}" in problems
    assert "orphan justification: gate:selector:orphan:file:changed" in problems
    assert match_justifications(
        findings, "## Gate justifications\n\n- gate:incomplete\n"
    )


def test_justification_body_edits_both_directions() -> None:
    findings = compare(
        {".github/workflows/check.yml": "old"},
        {".github/workflows/check.yml": "new"},
        REGISTRY,
    )
    good = (FIXTURES / "reasons.txt").read_text()
    assert match_justifications(findings, good) == ()
    assert match_justifications(
        findings,
        good.replace(
            "The PR edit trigger runs the gate again when a reason is removed.", ""
        ),
    ) == (f"partial justification: {findings[0].id}",)
    assert match_justifications(findings, "## Gate justifications\n\nNone.\n") == (
        f"missing justification: {findings[0].id}",
    )
    assert match_justifications((), good) == (
        f"orphan justification: {findings[0].id}",
    )


@given(st.text(alphabet="abc", min_size=1, max_size=30))
def test_reason_round_trip_property(reason: str) -> None:
    findings = compare({"prek.toml": "a"}, {"prek.toml": "b"}, REGISTRY)
    body = f"## Gate justifications\n\n- {findings[0].id}: {reason}\n"
    assert match_justifications(findings, body) == ()
    assert match_justifications(findings, body.replace(reason, "")) != ()


@given(st.text(alphabet="abc", min_size=1, max_size=30))
def test_unchanged_snapshot_property(content: str) -> None:
    assert compare({"prek.toml": content}, {"prek.toml": content}, REGISTRY) == ()


@pytest.mark.integration
def test_shell_collects_merge_base_and_current_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/gate-registry.toml").write_text(
        (ROOT / "config/gate-registry.toml").read_text()
    )
    (tmp_path / ".github/workflows").mkdir(parents=True)
    workflow = tmp_path / ".github/workflows/check.yml"
    workflow.write_text("on: pull_request\n")
    subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "base",
        ],
        check=True,
    )
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    workflow.write_text("on: push\n")
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "head",
        ],
        check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    body = tmp_path / "body.txt"
    body.write_text("## Gate justifications\n\nNone.\n")
    assert run(base, head, body) == 1
    body.write_text((FIXTURES / "reasons.txt").read_text())
    assert run(base, head, body) == 0
