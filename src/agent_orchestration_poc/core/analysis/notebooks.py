"""Parse notebook source and check committable analysis text."""

import re
from hashlib import sha256


def split_qmd(source: str) -> tuple[str, str]:
    """Return Markdown prose and Python cells from a Quarto text notebook."""
    prose: list[str] = []
    code: list[str] = []
    fence = ""
    python_cell = False
    for line in source.splitlines(keepends=True):
        marker = re.match(r"^(`{3,})(.*)$", line)
        if not fence and marker:
            fence = marker.group(1)
            python_cell = marker.group(2).strip() == "{python}"
            prose.append(f"{fence}python\n" if python_cell else line)
        elif fence and line.strip() == fence:
            prose.append(line)
            fence = ""
            python_cell = False
        elif python_cell:
            code.append(line)
        else:
            prose.append(line)
    if fence:
        raise ValueError("unclosed notebook code fence")
    return "".join(prose), "".join(code)


def supporting_sample(issue_id: str, row_ids: list[str]) -> list[str]:
    """Choose the protocol's deterministic supporting-row sample."""
    unique = set(row_ids)
    return sorted(
        unique,
        key=lambda row: (sha256(f"{issue_id}|{row}".encode()).hexdigest(), row),
    )[:10]


def is_private_notebook(source: str) -> bool:
    """Read the explicit private-input flag from notebook frontmatter."""
    if not source.startswith("---\n"):
        return False
    parts = source.split("\n---\n", 1)
    if len(parts) != 2:
        return False
    frontmatter = parts[0]
    return bool(re.search(r"(?m)^private-input:\s*true\s*$", frontmatter))


def privacy_findings(source: str) -> list[str]:
    """Flag synthetic secret signatures and raw private-record fields."""
    findings: list[str] = []
    if re.search(r"ghp_[A-Za-z0-9]{36}\b", source):
        findings.append("GitHub token signature")
    if re.search(
        r'(?i)(?:"(?:prompt|transcript|private_prompt)"\s*:'
        r"|\b(?:prompt|transcript|private_prompt)\s*,)",
        source,
    ):
        findings.append("private raw record field")
    return findings
