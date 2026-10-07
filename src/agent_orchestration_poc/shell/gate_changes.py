"""Collect Git tree contents and run the pure gate comparison."""

import argparse
import logging
import os
import subprocess
import tomllib
from pathlib import Path

from agent_orchestration_poc.core.gate_changes import compare, match_justifications

LOGGER = logging.getLogger(__name__)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def _content(revision: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout
    if result.returncode == 128 and "does not exist" in result.stderr:
        return ""
    if result.returncode == 128 and "exists on disk" in result.stderr:
        return ""
    raise RuntimeError(
        f"cannot read {path} at {revision}: git exit {result.returncode}"
    )


def run(base: str, head: str, body_file: Path) -> int:
    """Collect both revisions and report gate findings and missing reasons."""
    registry = tomllib.loads(Path("config/gate-registry.toml").read_text())
    merge_base = _git("merge-base", base, head).strip()
    paths = tuple(_git("diff", "--name-only", merge_base, head).splitlines())
    before = {path: _content(merge_base, path) for path in paths}
    after = {path: _content(head, path) for path in paths}
    findings = compare(before, after, registry)
    problems = match_justifications(findings, body_file.read_text())
    LOGGER.info("Gate comparison: merge base %s, head %s", merge_base, head)
    for finding in findings:
        LOGGER.info("%s: %s", finding.id, finding.detail)
    for problem in problems:
        LOGGER.error("%s", problem)
    if not findings:
        LOGGER.info("No registered gate findings")
    return int(bool(problems) or any(f.id.startswith("gate:syntax:") for f in findings))


def main() -> int:
    """Parse the local three-input gate check contract."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.environ.get("GATE_BASE_SHA"))
    parser.add_argument("--head", default=os.environ.get("GATE_HEAD_SHA"))
    parser.add_argument(
        "--body-file", type=Path, default=os.environ.get("GATE_BODY_FILE")
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not any((args.base, args.head, args.body_file)):
        LOGGER.info("Gate comparison skipped outside a pull request")
        return 0
    if not all((args.base, args.head, args.body_file)):
        parser.error("base, head, and body-file are required together")
    return run(args.base, args.head, args.body_file)


if __name__ == "__main__":
    raise SystemExit(main())
