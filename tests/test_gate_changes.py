"""Pure gate comparison and pull request reason fixtures."""

import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.gate_changes import (
    Finding,
    _biome_changes,
    _flatten_exclusions,
    _identifier,
    _yaml_exclusions,
    compare,
    match_justifications,
    monitored_path,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = ROOT if (ROOT / "config/gate-registry.toml").is_file() else ROOT.parent
FIXTURES = ROOT / "tests/fixtures/gate_changes"
REGISTRY = tomllib.loads((CONFIG_ROOT / "config/gate-registry.toml").read_text())
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
    before = (CONFIG_ROOT / path).read_text()
    match = re.search(entry["pattern"], before)
    assert match is not None
    value = int(match.group("value"))
    weaker = value - 1 if entry["direction"] == "floor" else value + 1
    after = before[: match.start("value")] + str(weaker) + before[match.end("value") :]
    findings = compare({path: before}, {path: after}, REGISTRY)
    assert any(
        f.id == f"gate:threshold:{path}:{entry['key']}.0:weakened"
        and f.detail == f"{entry['key']}: {value} to {weaker}"
        for f in findings
    )
    assert compare({path: before}, {path: before}, REGISTRY) == ()
    stronger = value + 1 if entry["direction"] == "floor" else value - 1
    after = (
        before[: match.start("value")] + str(stronger) + before[match.end("value") :]
    )
    assert not any(
        f.id.startswith("gate:threshold:")
        for f in compare({path: before}, {path: after}, REGISTRY)
    )
    assert not any(
        f.id.startswith("gate:syntax:")
        for f in compare({path: before}, {path: after}, REGISTRY)
    )


@pytest.mark.parametrize("entry", REGISTRY["required"], ids=lambda entry: entry["key"])
def test_each_required_gate_removal(entry: dict[str, Any]) -> None:
    path = entry["path"]
    before = (CONFIG_ROOT / path).read_text()
    match = re.search(entry["pattern"], before)
    assert match is not None
    after = before[: match.start()] + before[match.end() :]
    findings = compare({path: before}, {path: after}, REGISTRY)
    assert any(
        f.id == f"gate:gate:{path}:{entry['key']}:removed"
        and f.detail == f"{entry['key']} removed or disabled"
        for f in findings
    )


@pytest.mark.parametrize("case", SUPPRESSIONS, ids=lambda case: case["kind"])
def test_each_supported_suppression(case: dict[str, str]) -> None:
    entry = next(
        entry for entry in REGISTRY["suppressions"] if entry["kind"] == case["kind"]
    )
    line = case["line"]
    assert re.search(entry["pattern"], line)
    findings = compare({case["path"]: ""}, {case["path"]: line}, REGISTRY)
    digest = hashlib.sha256(line.strip().encode()).hexdigest()[:12]
    assert any(
        f.id == f"gate:suppression:{case['path']}:{case['kind']}.{digest}:added"
        and f.detail == line.strip()
        for f in findings
    )


def test_added_exclusion_and_disabled_gate() -> None:
    before = (
        '{"ignore": ["old"], "linter": {"enabled": true, "rules": {"complexity": {}}}}'
    )
    after = '{"ignore": ["old", "new"], "linter": {"enabled": false, "rules": {}}}'
    findings = compare({"biome.json": before}, {"biome.json": after}, REGISTRY)
    assert any(f.id.startswith("gate:exclusion:") for f in findings)
    assert any(
        f.id == "gate:gate:biome.json:complexity:removed"
        and f.detail == "linter rule complexity removed"
        for f in findings
    )
    assert any(
        f.id == "gate:gate:biome.json:linter:disabled"
        and f.detail == "Biome linter disabled"
        for f in findings
    )


def test_lint_exclusion_and_rule_disable() -> None:
    before = (CONFIG_ROOT / ".golangci.yml").read_text()
    after = before.replace(
        "      - path: _test\\.go",
        "      - path: generated\\.go\n      - path: _test\\.go",
    )
    findings = compare({".golangci.yml": before}, {".golangci.yml": after}, REGISTRY)
    assert any(
        f.id.startswith("gate:exclusion:.golangci.yml:")
        and f.detail == "- path: generated\\.go"
        for f in findings
    )

    before_biome = (CONFIG_ROOT / "biome.json").read_text()
    after_biome = before_biome.replace('"level": "error"', '"level": "off"', 1)
    findings = compare(
        {"biome.json": before_biome}, {"biome.json": after_biome}, REGISTRY
    )
    assert any(
        f.id == "gate:gate:biome.json:rule-level:disabled"
        and f.detail == "Biome rule set to off"
        for f in findings
    )


@pytest.mark.parametrize(
    ("path", "addition"),
    [
        ("pyproject.toml", "max-future = 42"),
        (".gremlins.yaml", "max-future: 42"),
        (".golangci.yml", "max-future: 42"),
        (".jscpd.json", '"maxFuture": 42'),
        ("biome.json", '"maxFuture": 42'),
    ],
)
def test_unknown_numeric_gate_fails_closed(path: str, addition: str) -> None:
    before = (CONFIG_ROOT / path).read_text()
    if path.endswith(".json"):
        document = json.loads(before)
        document["maxFuture"] = 42
        after = json.dumps(document)
    else:
        after = before + "\n" + addition + "\n"
    findings = compare({path: before}, {path: after}, REGISTRY)
    if path.endswith(".json"):
        expected = Finding(
            f"gate:syntax:{path}:maxFuture:unknown",
            "unregistered numeric gate: maxFuture",
        )
    else:
        digest = hashlib.sha256(addition.encode()).hexdigest()[:12]
        expected = Finding(f"gate:syntax:{path}:{digest}:unknown", addition)
    assert expected in findings


@given(st.text(alphabet="abc", min_size=1, max_size=12))
def test_biome_rule_removal_property(name: str) -> None:
    old = {"linter": {"rules": {name: {"level": "error"}}}}
    new: dict[str, Any] = {"linter": {"rules": {}}}
    assert _biome_changes(old, new, "", "") == (
        Finding(f"gate:gate:biome.json:{name}:removed", f"linter rule {name} removed"),
    )


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ({}, {}),
        ({"linter": {}}, {"linter": {}}),
        ({"linter": {"rules": {}}}, {"linter": {"rules": {}}}),
    ],
)
def test_biome_missing_optional_sections(
    old: dict[str, Any], new: dict[str, Any]
) -> None:
    assert _biome_changes(old, new, "", "") == ()


def test_biome_retained_rule_and_existing_disabled_level() -> None:
    rules = {"linter": {"rules": {"kept": {"level": "error"}}}}
    assert _biome_changes(rules, rules, "", "") == ()
    off = '"level": "off"'
    assert _biome_changes({}, {}, off, off) == ()


@pytest.mark.parametrize("key", ["ignore", "exclude", "skip", "filterwarnings"])
def test_nested_exclusion_keys(key: str) -> None:
    value = {"tool": {"nested": {key: ["a", "b"]}}}
    assert _flatten_exclusions(value) == frozenset(
        {f'tool.nested.{key}="a"', f'tool.nested.{key}="b"'}
    )


def test_normalized_finding_id() -> None:
    assert (
        _identifier("gate", "./path\\to/file", "key", "removed")
        == "gate:gate:path/to/file:key:removed"
    )


def test_yaml_exclusions_only_in_linter_section() -> None:
    before = "linters:\n  exclusions:\n    rules:\n      - path: old\nformatters:\n"
    after = before.replace("      - path: old", "      - path: old\n      - path: new")
    digest = hashlib.sha256(b"- path: new").hexdigest()[:12]
    assert _yaml_exclusions(".golangci.yml", before, after) == (
        Finding(f"gate:exclusion:.golangci.yml:{digest}:added", "- path: new"),
    )
    assert (
        _yaml_exclusions(".golangci.yml", before, before + "  enable:\n    - new\n")
        == ()
    )
    assert _yaml_exclusions(".golangci.yml", "linters:\n", after) == ()


def test_malformed_and_missing_baseline_configs_fail_closed() -> None:
    valid = (CONFIG_ROOT / "pyproject.toml").read_text()
    broken = valid + "\n[invalid\n"
    findings = compare({"pyproject.toml": valid}, {"pyproject.toml": broken}, REGISTRY)
    assert any(f.id == "gate:syntax:pyproject.toml:config:unknown" for f in findings)
    before = '{"minLines": "auto", "minTokens": 50}'
    after = '{"minLines": 5, "minTokens": 50}'
    findings = compare({".jscpd.json": before}, {".jscpd.json": after}, REGISTRY)
    assert any(f.id == "gate:syntax:.jscpd.json:minLines:unknown" for f in findings)


def test_python_literal_is_not_a_suppression() -> None:
    value = (FIXTURES / "python_literal.txt").read_text()
    assert compare({"sample.py": ""}, {"sample.py": value}, REGISTRY) == ()


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("sample.py", True),
        (".github/workflows/check.yml", True),
        ("biome.json", True),
        ("image.png", False),
    ],
)
def test_monitored_paths(path: str, expected: bool) -> None:
    assert monitored_path(path, REGISTRY) is expected


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


def test_pr_body_fixtures_cover_both_edit_directions() -> None:
    base = {"mise.toml": "old", ".github/workflows/check.yml": "old"}
    head = {"mise.toml": "new", ".github/workflows/check.yml": "new"}
    findings = compare(base, head, REGISTRY)
    assert (
        match_justifications(findings, (FIXTURES / "pr-body-pass.txt").read_text())
        == ()
    )
    assert (
        len(match_justifications(findings, (FIXTURES / "pr-body-fail.txt").read_text()))
        == 2
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
    shell = pytest.importorskip("agent_orchestration_poc.shell.gate_changes")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/gate-registry.toml").write_text(
        (CONFIG_ROOT / "config/gate-registry.toml").read_text()
    )
    (tmp_path / ".github/workflows").mkdir(parents=True)
    workflow = tmp_path / ".github/workflows/check.yml"
    workflow.write_text("on: pull_request\n")
    subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "add", "."], check=True)
    identity = ["-c", "user.name=Test", "-c", "user.email=test@example.invalid"]
    subprocess.run(["git", *identity, "commit", "-qm", "base"], check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    workflow.write_text("on: push\n")
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", *identity, "commit", "-qm", "head"], check=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    body = tmp_path / "body.txt"
    body.write_text("## Gate justifications\n\nNone.\n")
    assert shell.run(base, head, body) == 1
    body.write_text((FIXTURES / "reasons.txt").read_text())
    assert shell.run(base, head, body) == 0
