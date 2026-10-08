"""Pure workflow reference, form, and validation decisions."""

import re
from datetime import datetime
from typing import Any

type Reference = dict[str, Any]
type Label = tuple[str, str]

TITLE = re.compile(r"^([a-z]+)\(([a-z][a-z0-9-]*)\): ([a-z]+) (.+)$")
INCIDENT = re.compile(r"^inc(?:\(([a-z][a-z0-9-]*)\))?: (\S.*)$")
PARENT = re.compile(r"^(initiative|epic): ([^\n]*)$")
PARENT_KEY = re.compile(r"^[A-Z]\d+(?:-[A-Z]\d+)*(?=$|\s|[.:)])")
PARENT_ORDINAL = re.compile(r"^(?:\d+|[IVXLCDM]{1,4})(?:[.:)]| ?-(?:\s|$))")
PARENT_STAGE = re.compile(r"^(?i:phase|part|step) ?\d+(?=$|\s|[.:)])")
HEADING = re.compile(r"(?m)^#{2,3} ([^\n]+)\s*$")
REF = re.compile(r"^Refs: #(\d+)$")


def valid_parent_summary(summary: str) -> bool:
    """Accept text without a leading parent key, ordinal, or numbered stage."""
    summary = summary.strip()
    return bool(summary) and not any(
        pattern.match(summary) for pattern in (PARENT_KEY, PARENT_ORDINAL, PARENT_STAGE)
    )


def validate_title(
    title: str, reference: Reference, *, issue: bool = False
) -> tuple[str, ...]:
    """Check a conventional subject against the closed reference."""
    if issue and title in reference["title_label_exceptions"]:
        return ()
    if issue and (parent := PARENT.fullmatch(title)):
        return (
            ("parent summary needs text without a leading key or ordinal",)
            if not valid_parent_summary(parent.group(2))
            else ()
        )
    if issue and (match_incident := INCIDENT.fullmatch(title)):
        scope = match_incident.group(1)
        return (
            (f"unknown scope: {scope}",)
            if scope and scope not in reference["titles"]["scopes"]
            else ()
        )
    match = TITLE.fullmatch(title)
    if not match:
        return ("title must be type(scope): verb object",)
    kind, scope, verb, obj = match.groups()
    findings = []
    if kind not in reference["titles"]["types"]:
        findings.append(f"unknown type: {kind}")
    if kind in reference["titles"]["issue_only"]:
        findings.append(f"issue-only type: {kind}")
    if scope not in reference["titles"]["scopes"]:
        findings.append(f"unknown scope: {scope}")
    if verb not in reference["titles"]["verbs"] or not obj.strip():
        findings.append("subject needs a listed imperative verb and an object")
    if title.endswith("."):
        findings.append("subject ends in a period")
    return tuple(findings)


def sections(body: str) -> dict[str, str]:
    """Extract second-level Markdown sections without I/O."""
    headings = list(HEADING.finditer(body))
    return {
        match.group(1): body[match.end() : headings[index + 1].start()].strip()
        if index + 1 < len(headings)
        else body[match.end() :].strip()
        for index, match in enumerate(headings)
    }


def valid_allowed_path(path: str) -> bool:
    """Accept anchored repository paths with whole-segment glob tokens."""
    if not path or path.startswith(("/", "!", "~")) or "\\" in path:
        return False
    return all(
        segment not in ("", ".", "..")
        and (
            segment in ("*", "**") or bool(re.fullmatch(r"[A-Za-z0-9_.@+-]+", segment))
        )
        for segment in path.split("/")
    )


def expected_labels(reference: Reference) -> dict[str, Label]:
    """Expand label families and their reference-defined metadata."""
    labels = reference["labels"]
    expected = {
        f"{prefix}/{value}": (
            labels[f"{prefix}_description"].format(value=value),
            labels[f"{prefix}_color"],
        )
        for prefix, values in (
            ("area", labels["areas"]),
            ("phase", labels["phases"]),
            ("harness", labels["harnesses"]),
            ("type", {name.split("/", 1)[1] for name in reference["types"].values()}),
            (
                "type",
                {
                    name.split("/", 1)[1]
                    for name in reference["titles"]["parent_labels"]
                },
            ),
            ("invalid", labels["invalid"]),
            ("review", labels["review"]),
        )
        for value in values
    }
    expected["blocked"] = (labels["blocked_description"], labels["blocked_color"])
    expected["needs-operator"] = (
        labels["operator_description"],
        labels["operator_color"],
    )
    for old, new in reference["migration"].get("labels", {}).items():
        expected[old] = (
            labels["type_description"].format(value=old.split("/", 1)[1]),
            expected[new][1],
        )
    return expected


def validate_labels(names: tuple[str, ...], reference: Reference) -> tuple[str, ...]:
    """Require one known label in each workflow family."""
    expected = expected_labels(reference)
    findings = []
    if any(name in reference["titles"]["parent_labels"] for name in names):
        return (
            ()
            if len([name for name in names if name.startswith("type/")]) == 1
            else ("expected exactly one type/ label",)
        )
    for prefix in ("area/", "type/", "phase/", "harness/"):
        family = [name for name in names if name.startswith(prefix)]
        classes = {
            reference["migration"].get("labels", {}).get(name, name) for name in family
        }
        if len(classes) != 1:
            findings.append(f"expected exactly one {prefix} label")
        findings.extend(
            f"unknown label: {name}" for name in family if name not in expected
        )
    return tuple(findings)


def validate_type_label(
    title: str, labels: tuple[str, ...], reference: Reference, *, issue: bool = False
) -> tuple[str, ...]:
    """Match the title type to its required type label."""
    match = TITLE.fullmatch(title)
    if issue and (parent := PARENT.fullmatch(title)):
        required = f"type/{parent.group(1)}"
    elif issue and INCIDENT.fullmatch(title):
        required = "type/incident"
    elif issue and title in reference["title_label_exceptions"]:
        required = reference["title_label_exceptions"][title]
    elif match:
        required = reference["types"].get(match.group(1))
    else:
        return ()
    actual = {
        reference["migration"].get("labels", {}).get(label, label) for label in labels
    }
    return ("title type does not match type/ label",) if required not in actual else ()


def validate_issue(
    title: str, body: str, labels: tuple[str, ...], reference: Reference
) -> tuple[str, ...]:
    """Report all issue form findings from supplied values."""
    parent_labels = set(reference["titles"]["parent_labels"]) & set(labels)
    if parent_labels:
        return (
            validate_title(title, reference, issue=True)
            + validate_labels(labels, reference)
            + validate_type_label(title, labels, reference, issue=True)
        )
    findings = list(
        validate_title(title, reference, issue=True)
        + validate_labels(labels, reference)
        + validate_type_label(title, labels, reference, issue=True)
    )
    if INCIDENT.fullmatch(title):
        return tuple(findings)
    parts = sections(body)
    findings.extend(
        f"missing or empty section: {name}"
        for name in reference["forms"]["issue_fields"]
        if not parts.get(name)
    )
    if parts.get("Acceptance criteria") and not re.search(
        r"(?m)^\s*[-*+] \[[ xX]\] ", parts["Acceptance criteria"]
    ):
        findings.append("Acceptance criteria needs a checkbox")
    dependencies = parts.get("Dependencies and paths", "")
    if not re.search(
        r"(?:#\d+|https://github\.com/[^\s)]+/(?:issues|pull)/\d+)", dependencies
    ):
        findings.append("dependencies need an issue or PR reference")
    path_text = (
        parts.get("Allowed paths") or dependencies.partition("Allowed paths:")[2]
    )
    paths = (
        [
            line.strip().removeprefix("- ").strip("`")
            for line in path_text.splitlines()
            if line.strip()
        ]
        if parts.get("Allowed paths")
        else re.findall(r"`([^`]+)`", path_text)
    )
    if not path_text or not paths:
        findings.append("issue needs an Allowed paths list")
    findings.extend(
        f"invalid allowed path: {path}"
        for path in paths
        if not valid_allowed_path(path)
    )
    evidence = parts.get("Evidence required", "")
    if not re.search(r"`[^`]*[/\.][^`]+`", evidence) or not re.search(
        r"`(?:mise run|mise exec --|gh api|gh query|git )[^`]+`", evidence
    ):
        findings.append("evidence needs a named path and exact command")
    return tuple(findings)


def refs(body: str) -> tuple[int, ...]:
    """Read a contiguous final block of one or more Refs trailers."""
    lines = body.rstrip().splitlines()
    numbers = []
    for line in reversed(lines):
        match = REF.fullmatch(line)
        if not match:
            break
        numbers.append(int(match.group(1)))
    return tuple(reversed(numbers))


def validate_pr(
    title: str,
    body: str,
    labels: tuple[str, ...],
    open_issues: frozenset[int],
    reference: Reference,
) -> tuple[str, ...]:
    """Validate the remote PR form and its open issue references."""
    findings = list(
        validate_title(title, reference)
        + validate_labels(labels, reference)
        + validate_type_label(title, labels, reference)
    )
    parts = sections(body)
    findings.extend(
        f"missing section: {name}"
        for name in reference["forms"]["pr_sections"]
        if name not in parts
    )
    if title.startswith(("feat(", "feat:", "exp(", "exp:")) and not re.search(
        r"https?://|\]\([^)]*\)", parts.get("Evidence", "")
    ):
        findings.append("feat and exp need an Evidence link")
    numbers = refs(body)
    if not numbers:
        findings.append("body must end with Refs: #<n> trailers")
    if len(numbers) != len(set(numbers)):
        findings.append("duplicate Refs trailer")
    findings.extend(
        f"issue #{number} is not open"
        for number in numbers
        if number not in open_issues
    )
    return tuple(findings)


def enforcement_mode(created_at: str | None, cutoff: str | None) -> str:
    """Decide whether a remote PR is enforced, reported, or invalid."""
    if not created_at or not cutoff:
        return "invalid"
    try:
        created = datetime.fromisoformat(created_at)
        merged = datetime.fromisoformat(cutoff)
        if created.tzinfo is None or merged.tzinfo is None:
            return "invalid"
        return "enforce" if created >= merged else "report"
    except ValueError:
        return "invalid"


def remote_mode(
    created_at: str | None, cutoff: str | None, validator_state: str
) -> str:
    """Report while the activation PR is open, then use its merge time."""
    if enforcement_mode(created_at, created_at) == "invalid":
        return "invalid"
    if cutoff:
        return enforcement_mode(created_at, cutoff)
    return "report" if validator_state == "open" else "invalid"


def blocking_findings(findings: tuple[str, ...], mode: str) -> bool:
    """Decide whether findings block an enforced check."""
    return bool(findings) and mode != "report"


def label_names(raw: tuple[dict[str, str], ...]) -> tuple[str, ...]:
    """Keep only label names from REST values."""
    return tuple(label["name"] for label in raw)


def page_items(
    pages: tuple[tuple[dict[str, Any], ...], ...],
) -> tuple[dict[str, Any], ...]:
    """Flatten paginated REST collections without dropping a page."""
    return tuple(item for page in pages for item in page)


def issue_records(raw: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    """Exclude pull requests from the issues REST collection."""
    return tuple(item for item in raw if "pull_request" not in item)


def open_reference_numbers(raw: dict[int, dict[str, Any]]) -> frozenset[int]:
    """Select open issues while excluding pull requests."""
    return frozenset(
        number
        for number, item in raw.items()
        if item.get("state") == "open" and "pull_request" not in item
    )


def changed_forms(
    expected: dict[str, str], actual: dict[str, str | None]
) -> tuple[str, ...]:
    """Find generated paths whose recorded contents differ."""
    return tuple(
        path for path, content in expected.items() if actual.get(path) != content
    )


def generated_files(reference: Reference) -> dict[str, str]:
    """Choose generated paths and render their expected content."""
    expected = {
        f".github/ISSUE_TEMPLATE/{kind}.yml": render_issue_form(kind, reference)
        for kind in reference["titles"]["types"]
    }
    expected["docs/src/content/docs/guides/workflow-reference.md"] = (
        render_reference_page(reference)
    )
    return expected


def render_issue_form(kind: str, reference: Reference) -> str:
    """Render one generated GitHub issue form from the reference."""
    incident = kind in reference["titles"]["issue_only"]
    fields = reference["forms"]["incident_fields" if incident else "issue_fields"]
    lines = [
        "---",
        "# do not edit: generated from config/workflow-reference.toml",
        f'name: "{"incident" if incident else f"{kind} work item"}"',
        f'description: "{"Open an incident" if incident else f"Open a {kind} work item"}"',
        f'title: "{kind}: "'
        if kind in reference["titles"]["optional_scope"]
        else f'title: "{kind}(scope): "',
        f'labels: ["{reference["types"][kind]}"]',
        "body:",
    ]
    form_fields = (
        fields
        if incident
        else fields[:3] + [reference["forms"]["allowed_paths_field"]] + fields[3:]
    )
    for name in form_fields:
        lines.extend(
            ("  - type: textarea", "    attributes:", f'      label: "{name}"')
        )
        if name == "Dependencies and paths":
            lines.extend(
                (
                    "      description: >-",
                    "        Name dependent issues and pull requests.",
                )
            )
        if name == reference["forms"]["allowed_paths_field"]:
            lines.extend(
                (
                    "      description: >-",
                    "        List repo-relative literals or anchored globs, one per line.",
                )
            )
        if name == "Evidence required":
            lines.append('      description: "Name evidence paths and exact commands."')
        lines.extend(("    validations:", "      required: true"))
    return "\n".join(lines) + "\n"


def render_reference_page(reference: Reference) -> str:
    """Render the checked conventions page from the reference."""
    titles = reference["titles"]
    size = reference["size"]
    types = ", ".join(f"`{item}`" for item in titles["types"])
    scopes = ", ".join(f"`{item}`" for item in titles["scopes"])
    verbs = ", ".join(f"`{item}`" for item in titles["verbs"])
    fields = ", ".join(f"`{item}`" for item in reference["forms"]["issue_fields"])
    pr_sections = ", ".join(f"`{item}`" for item in reference["forms"]["pr_sections"])
    exclusions = ", ".join(f"`{item}`" for item in size["excluded"])
    labels_table = "\n".join(
        f"| `{name}` | {description} | `#{color}` |"
        for name, (description, color) in sorted(expected_labels(reference).items())
    )
    type_table = "\n".join(
        f"| `{kind}` | `{label}` |" for kind, label in reference["types"].items()
    )
    migration_table = "\n".join(
        f"| `{old}` | `{new}` |"
        for old, new in reference["migration"].get("labels", {}).items()
    )
    return f"""---
title: Workflow reference
description: Checked types, scopes, labels, forms, and pull request size rules.
---

<!-- do not edit: generated from config/workflow-reference.toml -->

## Titles and branches

Types: {types}.

Scopes: {scopes}.

Subject verbs: {verbs}.

Titles use `type(scope): verb object` without a final period. Commit subjects have at most {titles["max_length"]} characters. Branches use `{titles["branch_pattern"]}`. A new scope needs a reference edit in the same PR.

Issues also admit `inc: summary` and `inc(scope): summary` with no imperative verb. Parent issues use `initiative: summary` or `epic: summary` without a key or ordinal. PR titles keep the conventional pattern.

`workflow` remains an area and scope, but is retired as a commit type because `process` and `tooling` describe the two kinds of workflow changes without a separate overlapping type.

## Labels

| Name | Description | Color |
| --- | --- | --- |
{labels_table}

Each issue and PR has exactly one `area/`, `type/`, `phase/`, and `harness/` label. Type-to-label mapping:

Parent issues require one `type/initiative` or `type/epic` label and are exempt from form, `area/`, `phase/`, and `harness/` checks. An old and new label for the same class count as one during migration.

| Type | Label |
| --- | --- |
{type_table}

The relabel-only exceptions are keyed by their exact issue titles in the reference. These issues keep their titles. The migration table remains until the final read-back in issue #200:

| Old label | New label |
| --- | --- |
{migration_table}

## Forms and references

Issue fields: {fields}. `Allowed paths` is a separate form field.

Allowed paths use {reference["forms"]["allowed_path_syntax"]}.

Evidence requires {reference["forms"]["evidence_requires"]}. PR sections: {pr_sections}. A PR ends with one or more `Refs: #<n>` lines naming open issues.

## Pull request size

Pin `{size["tool"]}` at {size["version"]}. Code counts {size["code_unit"]}. Prose counts {size["prose_unit"]}. Compare from the {size["base"]}.

Target {size["target"]} and limit {size["limit"]} units. Project Size S is at most {size["small"]}, M at most {size["medium"]}, and L at most {size["large"]}. Split larger estimates during refinement.

Excluded paths: {exclusions}. Also exclude `scc` detected generated and minified files, vendored code, test fixtures, evidence directories, and exported diagrams. Keep excluded files in per-file output with raw added and deleted counts and a reason.

Run `mise run pr:size -- origin/main` for a PR targeting `main`, or pass the upstream target of a stacked PR. The command emits JSON with `total_units` and per-file raw added, raw deleted, counted units, and exclusion reason. `mise run check:pr-size-contract` prints passing and over-limit fixture results.

The counter classifies removed and added fragments with `scc`. A fragment inside a multiline comment can be counted as code because its enclosing delimiters are absent. Subtracting full-file code counts avoids that error but loses equal-count replacements, so the fragment method is the recorded contract. Issue #93 owns CI enforcement.

## Agent provenance

[Decision 0131](/decisions/0131-assisted-by-provenance/) defines the proposed provenance contract for issue #131. It remains inactive until [#134](https://github.com/tbhb/agent-orchestration-poc/issues/134). Current hooks still prohibit attribution trailers. This generated page preserves the provenance section reserved by #131.

Use this exact line format after cutover:

```text
Assisted-by: <harness>/<version> model=<model> effort=<effort> agent=<agent>
```

The [admitted combinations](/decisions/0131-assisted-by-provenance/#admitted-combinations) define the complete catalog by exact harness/version and the Cartesian product of each row's model and effort lists. The [reference values](/decisions/0131-assisted-by-provenance/#reference-values) show literal examples for Codex Sol and Astra, Claude Fable and Sonnet, and agy. Catalog lookup rejects unknown tuples, including every use of `unavailable`, while launch permission and runtime verification remain separate requirements.

Use one line per contributing agent ID, freeze that ID's configuration, sort complete lines by ASCII bytes, and reject duplicates within each artifact. The PR body contains the exact set union of its selected commits' lines. Preserve that union when deriving the squash body. Reviews, inline comments, implementer replies, issue bodies, and coordinator notes each carry their own contributors. Project draft bodies include trailers. Typed field edits use the separate provenance record defined in the decision.

After cutover, ordinary agent communication and Project edits use `tbhbagent`, and reviews use `tbhbbot`. The coordinator is subject to the same rule. Attribution is separate from operator authority, account verification, and signing. The decision records the #132/#134/#135 coordinator clarifications and keeps today's `tbhb` implementer workflow intact.

Keep `Refs:` as issue references. Closing keywords, if selected by #124, belong before the final trailer block and apply only to completed issues. The proposed cases in `research/gates/assisted-by/examples.md` cover both #124 options, completed-issue-only and multiple-reference bodies, an issue that remains open, and squash propagation. Policy selection remains with #124. Closure behavior remains inactive here.
"""
