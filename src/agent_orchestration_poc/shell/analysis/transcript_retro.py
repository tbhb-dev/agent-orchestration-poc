"""Filesystem checks for private transcript inventory output."""

import gzip
from pathlib import Path

from agent_orchestration_poc.core.analysis.notebooks import privacy_findings


def scan_compressed_evidence(evidence: Path) -> None:
    """Reject private content in both committed compressed tables."""
    for name in ("inventory.csv.gz", "events.csv.gz"):
        with gzip.open(evidence / name, "rt", encoding="utf-8") as source:
            findings = privacy_findings(source.read())
        if findings:
            raise ValueError(f"{name}: {', '.join(findings)}")


def private_map_destination(path: Path, *repository_roots: Path) -> Path:
    """Resolve a map destination and reject writes into either checkout."""
    destination = path.resolve()
    if any(destination.is_relative_to(root.resolve()) for root in repository_roots):
        raise ValueError("private source map must be outside the repository")
    return destination
