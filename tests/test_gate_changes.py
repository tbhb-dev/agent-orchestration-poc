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
    _gate_selectors,
    _golangci_selectors,
    _identifier,
    _yaml_exclusions,
    compare,
    compare_registries,
    match_justifications,
    monitored_path,
    reconcile_registries,
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
    ("path", "old", "new"),
    [
        ("biome.json", "**", "!src"),
        (".jscpd.json", "python", ""),
        (".golangci.yml", "    - nestif", ""),
    ],
)
def test_existing_selector_weakenings(path: str, old: str, new: str) -> None:
    before = (CONFIG_ROOT / path).read_text()
    after = before.replace(old, new, 1)
    findings = compare({path: before}, {path: after}, REGISTRY)
    assert findings
    assert match_justifications(findings, "")


def test_selector_findings_have_exact_identity() -> None:
    empty: list[str] = []
    for path, old, new, item in (
        (
            "biome.json",
            {"files": {"includes": ["**"]}},
            {"files": {"includes": ["**", "!src"]}},
            "!src",
        ),
        (
            "biome.json",
            {"files": {"includes": ["**"]}},
            {"files": {"includes": empty}},
            "**",
        ),
        (".jscpd.json", {"format": ["go", "python"]}, {"format": ["go"]}, "python"),
    ):
        digest = hashlib.sha256(item.encode()).hexdigest()[:12]
        assert _gate_selectors(path, old, new) == (
            Finding(f"gate:selector:{path}:{digest}:weakened", item),
        )
    assert (
        _gate_selectors(
            "biome.json", {"files": {"includes": ["!src"]}}, {"files": {"includes": []}}
        )
        == ()
    )
    assert (
        _gate_selectors(".jscpd.json", {"format": ["go"]}, {"format": ["go", "python"]})
        == ()
    )
    assert _gate_selectors("pyproject.toml", {}, {}) == ()


def test_golangci_selector_findings_have_exact_identity() -> None:
    before = "linters:\n  enable:\n    - funlen\n    - nestif\n  settings:\n"
    after = before.replace("    - nestif\n", "")
    assert _golangci_selectors(before, after) == (
        Finding("gate:gate:.golangci.yml:nestif:removed", "nestif"),
    )
    assert _golangci_selectors(before, before + "    - new\n") == ()
    assert _golangci_selectors(before, "linters:\n") == (
        Finding(
            "gate:syntax:.golangci.yml:linters.enable:unknown",
            "linter enable list changed syntax",
        ),
    )
    finding = _golangci_selectors(before, after)
    assert (
        match_justifications(
            finding, f"## Gate justifications\n\n- {finding[0].id}: Reviewed removal.\n"
        )
        == ()
    )


def test_existing_unclassified_gate_controls_fail_closed() -> None:
    biome = (CONFIG_ROOT / "biome.json").read_text()
    warning = biome.replace('"level": "error"', '"level": "warn"', 1)
    go = (CONFIG_ROOT / ".golangci.yml").read_text()
    lax = go.replace("  exclusions:\n", "  exclusions:\n    generated: lax\n", 1)
    for path, before, after in (
        ("biome.json", biome, warning),
        (".golangci.yml", go, lax),
    ):
        findings = compare({path: before}, {path: after}, REGISTRY)
        assert findings
        assert match_justifications(findings, "")


@pytest.mark.parametrize(
    ("previous", "current", "change"),
    [
        ("error", "warn", "weakened"),
        ("warn", "off", "weakened"),
        ("off", "warn", None),
        ("warn", "error", None),
        ("error", "unsupported", "unknown"),
    ],
)
def test_biome_rule_level_changes(
    previous: str, current: str, change: str | None
) -> None:
    def document(level: str) -> dict[str, Any]:
        return {"linter": {"rules": {"complexity": {"rule": {"level": level}}}}}

    findings = _biome_changes(document(previous), document(current), "", "")
    if change is None:
        assert findings == ()
    else:
        kind = "gate" if change == "weakened" else "syntax"
        assert len(findings) == 1
        assert (
            findings[0].id == f"gate:{kind}:biome.json:complexity.rule.level:{change}"
        )


def test_registry_change_keeps_baseline_gate_coverage() -> None:
    before = (CONFIG_ROOT / "config/gate-registry.toml").read_text()
    after = before.replace(
        'direction = "floor", enabled = true', 'direction = "floor", enabled = false', 1
    )
    findings = compare_registries(before, after)
    assert findings
    assert match_justifications(findings, "")
    baseline = tomllib.loads(before)
    config = (CONFIG_ROOT / ".gremlins.yaml").read_text()
    lowered = config.replace("efficacy: 90", "efficacy: 80")
    assert any(
        f.id.startswith("gate:threshold:")
        for f in compare(
            {".gremlins.yaml": config}, {".gremlins.yaml": lowered}, baseline
        )
    )


def test_registry_extension_parses_changed_config() -> None:
    before = (CONFIG_ROOT / "config/gate-registry.toml").read_text()
    old_pattern = "max-complexity = (?P<value>\\d+)"
    new_pattern = "max-complexity\\s*=\\s*(?P<value>\\d+)"
    assert old_pattern in before
    after = before.replace(old_pattern, new_pattern, 1)
    baseline = tomllib.loads(before)
    registry = reconcile_registries(baseline, tomllib.loads(after))
    config = (CONFIG_ROOT / "pyproject.toml").read_text()
    changed = config.replace("max-complexity = 10", "max-complexity=10", 1)
    findings = compare(
        {"pyproject.toml": config}, {"pyproject.toml": changed}, registry
    )
    assert not any(f.id.startswith("gate:syntax:") for f in findings)
    assert compare_registries(before, after)


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("thresholds", "unleash.threshold.efficacy"),
        ("required", "coverage.branch"),
        ("suppressions", "noqa"),
    ],
)
def test_registry_entry_changes_have_exact_identity(section: str, key: str) -> None:
    before = (CONFIG_ROOT / "config/gate-registry.toml").read_text()
    # Remove the exact line from the text so the remaining entries stay valid TOML.
    line = next(
        line
        for line in before.splitlines(keepends=True)
        if f'key = "{key}"' in line or f'kind = "{key}"' in line
    )
    altered = before.replace(line, "")
    assert compare_registries(before, altered) == (
        Finding(
            f"gate:registry:config/gate-registry.toml:{section}.{key}:changed",
            f"{section}.{key} removed or altered",
        ),
    )


def test_registry_review_path_and_bootstrap() -> None:
    before = (CONFIG_ROOT / "config/gate-registry.toml").read_text()
    after = before.replace('"prek.toml", ', "")
    assert compare_registries(before, after) == (
        Finding(
            "gate:registry:config/gate-registry.toml:prek.toml:removed",
            "review path prek.toml removed",
        ),
    )
    assert compare_registries(before, before) == ()
    assert compare_registries("", before) == ()
    assert compare_registries(before, "[broken") == (
        Finding(
            "gate:syntax:config/gate-registry.toml:registry:unknown",
            "registry cannot be parsed",
        ),
    )


def test_identical_suppressions_have_separate_locations() -> None:
    before = "first = unknown  # noqa: F821\nsecond = unknown\n"
    after = "first = unknown  # noqa: F821\nsecond = unknown  # noqa: F821\nthird = unknown  # noqa: F821\n"
    findings = compare({"sample.py": before}, {"sample.py": after}, REGISTRY)
    assert len([f for f in findings if f.id.startswith("gate:suppression:")]) == 2
    moved = compare(
        {"sample.py": before},
        {"sample.py": "first = unknown\nsecond = unknown  # noqa: F821\n"},
        REGISTRY,
    )
    assert any(f.id.startswith("gate:suppression:") for f in moved)


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
    digest = hashlib.sha256(f"1:{line.strip()}".encode()).hexdigest()[:12]
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
    config = tmp_path / "pyproject.toml"
    config.write_text((CONFIG_ROOT / "pyproject.toml").read_text())
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
    registry_path = tmp_path / "config/gate-registry.toml"
    old_registry = registry_path.read_text()
    registry_path.write_text(
        old_registry.replace(
            "max-complexity = (?P<value>\\d+)",
            "max-complexity\\s*=\\s*(?P<value>\\d+)",
            1,
        )
    )
    config.write_text(
        config.read_text().replace("max-complexity = 10", "max-complexity=10", 1)
    )
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(
        ["git", *identity, "commit", "-qm", "registry extension"], check=True
    )
    extended_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    registry_finding = compare_registries(old_registry, registry_path.read_text())[0]
    body.write_text(
        (FIXTURES / "reasons.txt").read_text()
        + f"- {registry_finding.id}: Extend parser for equivalent spacing.\n"
    )
    assert shell.run(base, extended_head, body) == 0
