"""Collect git blobs and pinned scc classifications for the pure size counter."""

import argparse
import json
import logging
import subprocess
import tempfile
import tomllib
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from agent_orchestration_poc.core.pr_size import (
    Classification,
    FileResult,
    changed_fragments,
    measure_file,
    needs_scc,
    total_units,
)

ROOT = Path(__file__).resolve().parents[3]
LOGGER = logging.getLogger(__name__)
SCC_OPTIONS = (
    "--by-file",
    "--format",
    "json",
    "--gen",
    "--min",
    "--no-config",
    "--no-cocomo",
    "--no-complexity",
    "--no-gitignore",
    "--no-ignore",
    "--no-scc-ignore",
    "--count-unsupported",
)


def _run(*args: str) -> bytes:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(
            f"{args[0]} exited {result.returncode}: {result.stderr.decode(errors='replace')}"
        )
    return result.stdout


def _blob(revision: str, path: str) -> bytes:
    return _run("git", "show", f"{revision}:{path}")


def _scc(content: bytes, suffix: str) -> tuple[int, bool, bool]:
    if not content:
        return 0, False, False
    with tempfile.TemporaryDirectory(prefix="pr-size-") as directory:
        sample = Path(directory) / f"sample{suffix}"
        sample.write_bytes(content)
        output = _run("scc", *SCC_OPTIONS, str(sample))
    rows = cast("list[dict[str, Any]]", json.loads(output))
    if not rows:
        raise ValueError(f"scc did not classify {suffix or 'extensionless'} content")
    files = cast("list[dict[str, Any]]", rows[0]["Files"])
    if len(files) != 1:
        raise ValueError("scc returned an unexpected per-file result")
    return int(rows[0]["Code"]), bool(files[0]["Generated"]), bool(files[0]["Minified"])


def _names(base: str, head: str) -> tuple[tuple[str, str | None, str], ...]:
    fields = _run("git", "diff", "--name-status", "-z", "-M", base, head).split(b"\0")
    entries: list[tuple[str, str | None, str]] = []
    cursor = 0
    while cursor < len(fields) - 1:
        status = fields[cursor].decode()
        path = fields[cursor + 1].decode()
        if status.startswith("R"):
            entries.append((fields[cursor + 2].decode(), path, status))
            cursor += 3
        else:
            entries.append((path, None, status))
            cursor += 2
    return tuple(entries)


def count(base_ref: str, head: str = "HEAD") -> tuple[FileResult, ...]:
    """Compare the merge base of a target branch with one commit."""
    base = _run("git", "merge-base", base_ref, head).decode().strip()
    reference = tomllib.loads((ROOT / "config/workflow-reference.toml").read_text())
    patterns = tuple(cast("list[str]", reference["size"]["excluded"]))
    results: list[FileResult] = []
    for path, old_path, status in _names(base, head):
        before = b"" if status == "A" else _blob(base, old_path or path)
        after = b"" if status == "D" else _blob(head, path)
        binary = b"\0" in before or b"\0" in after
        fragments = changed_fragments(
            before.decode("utf-8", errors="replace"),
            after.decode("utf-8", errors="replace"),
        )
        classification = Classification(binary=binary)
        if needs_scc(path, old_path, patterns, binary):
            old_suffix = Path(old_path or path).suffix
            new_suffix = Path(path).suffix
            full = tuple(
                _scc(blob, suffix)
                for blob, suffix in ((before, old_suffix), (after, new_suffix))
                if blob
            )
            generated = any(item[1] for item in full)
            minified = any(item[2] for item in full)
            removed_code = _scc("".join(fragments.removed).encode(), old_suffix)[0]
            added_code = _scc("".join(fragments.added).encode(), new_suffix)[0]
            classification = Classification(
                removed_code, added_code, generated, minified
            )
        results.append(
            measure_file(path, old_path, fragments, classification, patterns)
        )
    return tuple(results)


def main() -> int:
    """Emit a stable JSON result for a target branch and optional head commit."""
    parser = argparse.ArgumentParser(description="Measure changed PR lines")
    parser.add_argument("base_ref", help="PR target branch, including a stacked target")
    parser.add_argument("--head", default="HEAD")
    arguments = parser.parse_args()
    try:
        results = count(arguments.base_ref, arguments.head)
    except RuntimeError, ValueError:
        LOGGER.exception("PR size unavailable")
        return 1
    LOGGER.info(
        "%s",
        json.dumps(
            {
                "total_units": total_units(results),
                "files": [asdict(result) for result in results],
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
