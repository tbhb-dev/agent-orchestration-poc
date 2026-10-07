"""Compare registered quality gates and match pull request explanations."""

import difflib
import hashlib
import json
import re
import tokenize
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from io import StringIO
from typing import Any


@dataclass(frozen=True)
class Finding:
    """One stable gate change that needs a reason."""

    id: str
    detail: str


def _identifier(kind: str, path: str, key: str, change: str) -> str:
    normalized = path.replace("\\", "/").removeprefix("./")
    return f"gate:{kind}:{normalized}:{key}:{change}"


def _added_lines(before: str, after: str) -> tuple[str, ...]:
    old = before.splitlines()
    new = after.splitlines()
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    return tuple(
        line
        for tag, _, _, start, end in matcher.get_opcodes()
        if tag in {"replace", "insert"}
        for line in new[start:end]
    )


def _active_entries(
    path: str, entries: tuple[dict[str, Any], ...]
) -> tuple[dict[str, Any], ...]:
    return tuple(
        entry for entry in entries if entry["path"] == path and entry["enabled"]
    )


def _thresholds(
    path: str, before: str, after: str, entries: tuple[dict[str, Any], ...]
) -> tuple[Finding, ...]:
    findings = []
    for entry in _active_entries(path, entries):
        pattern = re.compile(entry["pattern"])
        old = tuple(int(match.group("value")) for match in pattern.finditer(before))
        new = tuple(int(match.group("value")) for match in pattern.finditer(after))
        key = str(entry["key"])
        if not old:
            findings.append(
                Finding(
                    _identifier("syntax", path, key, "unknown"),
                    "baseline gate syntax is unsupported",
                )
            )
            continue
        if len(new) != len(old):
            change = "unknown" if key.rsplit(".", 1)[-1] in after else "removed"
            findings.append(
                Finding(
                    _identifier(
                        "syntax" if change == "unknown" else "threshold",
                        path,
                        key,
                        change,
                    ),
                    f"{key}: gate removed or syntax changed",
                )
            )
            continue
        for index, (old_value, new_value) in enumerate(zip(old, new, strict=True)):
            weakened = (
                new_value < old_value
                if entry["direction"] == "floor"
                else new_value > old_value
            )
            if weakened:
                findings.append(
                    Finding(
                        _identifier("threshold", path, f"{key}.{index}", "weakened"),
                        f"{key}: {old_value} to {new_value}",
                    )
                )
    return tuple(findings)


def _flatten_exclusions(value: object, prefix: str = "") -> frozenset[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else key
            if any(
                word in key.lower()
                for word in ("ignore", "exclude", "skip", "filterwarnings")
            ):
                values = child if isinstance(child, list) else [child]
                found.update(
                    f"{name}={json.dumps(item, sort_keys=True)}" for item in values
                )
            else:
                found.update(_flatten_exclusions(child, name))
    return frozenset(found)


def _exclusions(path: str, before: str, after: str) -> tuple[Finding, ...]:
    if path == ".golangci.yml":
        return _yaml_exclusions(path, before, after)
    if path not in {"pyproject.toml", ".jscpd.json", "biome.json"}:
        return ()
    parser = tomllib.loads if path.endswith(".toml") else json.loads
    try:
        old = parser(before)
        new = parser(after)
    except ValueError, tomllib.TOMLDecodeError:
        return (
            Finding(
                _identifier("syntax", path, "config", "unknown"),
                "cannot parse gate configuration",
            ),
        )
    findings = []
    for value in sorted(_flatten_exclusions(new) - _flatten_exclusions(old)):
        digest = hashlib.sha256(value.encode()).hexdigest()[:12]
        findings.append(Finding(_identifier("exclusion", path, digest, "added"), value))
    if path == "biome.json":
        findings.extend(_biome_changes(old, new, before, after))
    return tuple(findings)


def _yaml_exclusions(path: str, before: str, after: str) -> tuple[Finding, ...]:
    old = before.split("  exclusions:", 1)
    new = after.split("  exclusions:", 1)
    if len(new) != 2 or len(old) != 2:
        return ()
    lines = _added_lines(
        old[1].split("formatters:", 1)[0], new[1].split("formatters:", 1)[0]
    )
    return tuple(
        Finding(
            _identifier(
                "exclusion",
                path,
                hashlib.sha256(line.strip().encode()).hexdigest()[:12],
                "added",
            ),
            line.strip(),
        )
        for line in lines
        if line.strip().startswith("-")
    )


def _biome_changes(
    old: dict[str, Any], new: dict[str, Any], before: str, after: str
) -> tuple[Finding, ...]:
    path = "biome.json"
    old_rules = old.get("linter", {}).get("rules", {})
    new_rules = new.get("linter", {}).get("rules", {})
    findings = [
        Finding(
            _identifier("gate", path, name, "removed"), f"linter rule {name} removed"
        )
        for name in sorted(old_rules)
        if name not in new_rules
    ]
    if (
        old.get("linter", {}).get("enabled") is True
        and new.get("linter", {}).get("enabled") is False
    ):
        findings.append(
            Finding(
                _identifier("gate", path, "linter", "disabled"), "Biome linter disabled"
            )
        )
    if '"level": "off"' in after and '"level": "off"' not in before:
        findings.append(
            Finding(
                _identifier("gate", path, "rule-level", "disabled"),
                "Biome rule set to off",
            )
        )
    return tuple(findings)


def _required(
    path: str, before: str, after: str, entries: tuple[dict[str, Any], ...]
) -> tuple[Finding, ...]:
    return tuple(
        Finding(
            _identifier("gate", path, str(entry["key"]), "removed"),
            f"{entry['key']} removed or disabled",
        )
        for entry in _active_entries(path, entries)
        if len(re.findall(entry["pattern"], before))
        > len(re.findall(entry["pattern"], after))
    )


def _unknown_syntax(
    path: str, before: str, after: str, entries: tuple[dict[str, Any], ...]
) -> tuple[Finding, ...]:
    if path not in {
        "pyproject.toml",
        ".jscpd.json",
        ".gremlins.yaml",
        ".golangci.yml",
        "biome.json",
    }:
        return ()
    patterns = [
        re.compile(entry["pattern"]) for entry in entries if entry["path"] == path
    ]
    if path in {".jscpd.json", "biome.json"}:
        try:
            document = json.loads(after)
        except ValueError:
            return ()  # The parser diagnostic comes from _exclusions.
        allowed = {
            str(entry["key"]).rsplit(".", 1)[-1]
            for entry in entries
            if entry["path"] == path
        }
        unknown = _unknown_numeric_keys(document, allowed)
        if unknown:
            return tuple(
                Finding(
                    _identifier("syntax", path, key, "unknown"),
                    f"unregistered numeric gate: {key}",
                )
                for key in sorted(unknown)
            )
    known_lines = {
        after.count("\n", 0, match.start("value"))
        for pattern in patterns
        for match in pattern.finditer(after)
    }
    findings = []
    changed = set(_added_lines(before, after))
    for index, line in enumerate(after.splitlines()):
        if line not in changed:
            continue
        stripped = line.strip()
        if stripped.startswith(("#", "//")):
            continue
        if not re.search(
            r"\b(?:max-|min-|max[A-Z]|min[A-Z]|threshold|floor)\w*", stripped
        ):
            continue
        if index not in known_lines:
            digest = hashlib.sha256(stripped.encode()).hexdigest()[:12]
            findings.append(
                Finding(_identifier("syntax", path, digest, "unknown"), stripped)
            )
    return tuple(findings)


def _unknown_numeric_keys(value: object, allowed: set[str]) -> frozenset[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                re.match(r"(?:max|min|floor|threshold)[A-Z_-]", key)
                and key not in allowed
            ):
                found.add(key)
            found.update(_unknown_numeric_keys(child, allowed))
    elif isinstance(value, list):
        for child in value:
            found.update(_unknown_numeric_keys(child, allowed))
    return frozenset(found)


def _suppressions(
    path: str, before: str, after: str, entries: tuple[dict[str, Any], ...]
) -> tuple[Finding, ...]:
    findings = []
    comment_kinds = {"noqa", "type-ignore", "pyrefly-ignore"}
    for entry in entries:
        if not path.endswith(tuple(entry["suffixes"])):
            continue
        old, new = before, after
        if entry["kind"] in comment_kinds:
            old = "\n".join(_python_comments(before))
            new = "\n".join(_python_comments(after))
        for line in _added_lines(old, new):
            if re.search(entry["pattern"], line):
                digest = hashlib.sha256(line.strip().encode()).hexdigest()[:12]
                kind = str(entry["kind"])
                findings.append(
                    Finding(
                        _identifier("suppression", path, f"{kind}.{digest}", "added"),
                        line.strip(),
                    )
                )
    return tuple(findings)


def _python_comments(source: str) -> tuple[str, ...]:
    return tuple(
        token.string
        for token in tokenize.generate_tokens(StringIO(source).readline)
        if token.type == tokenize.COMMENT
    )


def compare(
    base: Mapping[str, str], head: Mapping[str, str], registry: Mapping[str, Any]
) -> tuple[Finding, ...]:
    """Find registered weakenings in two Git tree snapshots."""
    thresholds = tuple(registry["thresholds"])
    required = tuple(registry["required"])
    suppressions = tuple(registry["suppressions"])
    review_paths = tuple(registry["review_paths"])
    registered = {str(entry["path"]) for entry in thresholds}
    findings: list[Finding] = []
    for path in sorted(base.keys() | head.keys()):
        before, after = base.get(path, ""), head.get(path, "")
        if before == after:
            continue
        if any(path == prefix or path.startswith(prefix) for prefix in review_paths):
            findings.append(
                Finding(
                    _identifier("selector", path, "file", "changed"),
                    "workflow or hook selector changed",
                )
            )
        if path in registered and before:
            findings.extend(_thresholds(path, before, after, thresholds))
            findings.extend(_exclusions(path, before, after))
            findings.extend(_unknown_syntax(path, before, after, thresholds))
        if before:
            findings.extend(_required(path, before, after, required))
        findings.extend(_suppressions(path, before, after, suppressions))
    return tuple(dict.fromkeys(findings))


def match_justifications(findings: tuple[Finding, ...], body: str) -> tuple[str, ...]:
    """Report missing, partial, duplicate, and orphan PR reasons."""
    section = re.search(r"(?ms)^## Gate justifications\s*\n(.*?)(?=^## |\Z)", body)
    expected = {finding.id for finding in findings}
    if section is None:
        return ("missing Gate justifications section",) if expected else ()
    reasons: dict[str, str] = {}
    problems = []
    for line in section.group(1).splitlines():
        if not line.startswith("- gate:"):
            continue
        match = re.fullmatch(r"- (gate:[^\s]+):\s*(.*)", line)
        if match is None:
            problems.append(f"partial justification: {line}")
            continue
        identifier, reason = match.groups()
        if identifier in reasons:
            problems.append(f"duplicate justification: {identifier}")
        reasons[identifier] = reason.strip()
    problems.extend(
        f"missing justification: {key}" for key in sorted(expected - reasons.keys())
    )
    problems.extend(
        f"partial justification: {key}"
        for key in sorted(expected & reasons.keys())
        if not reasons[key]
    )
    problems.extend(
        f"orphan justification: {key}" for key in sorted(reasons.keys() - expected)
    )
    return tuple(problems)
