"""Collect git blobs and pinned scc classifications for the pure size counter."""

import argparse
import json
import logging
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from agent_orchestration_poc.core.pr_size import (
    Classification,
    FileResult,
    changed_fragments,
    classify_samples,
    measure_file,
    needs_scc,
    parse_name_status,
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


def _scc(
    content: bytes,
    suffix: str,
    language: str | None = None,
    filename: str | None = None,
) -> tuple[int, bool, bool, str]:
    if not content:
        return 0, False, False, ""
    with tempfile.TemporaryDirectory(prefix="pr-size-") as directory:
        sample = Path(directory) / (filename or f"sample{suffix}")
        sample.write_bytes(content)
        language_option = (
            ("--count-as-pattern", f"*:{language}:{language}") if language else ()
        )
        output = _run("scc", *SCC_OPTIONS, *language_option, directory)
    rows = cast("list[dict[str, Any]]", json.loads(output))
    if not rows:
        raise ValueError(f"scc did not classify {suffix or 'extensionless'} content")
    files = cast("list[dict[str, Any]]", rows[0]["Files"])
    if len(files) != 1:
        raise ValueError("scc returned an unexpected per-file result")
    return (
        int(rows[0]["Code"]),
        bool(files[0]["Generated"]),
        bool(files[0]["Minified"]),
        str(rows[0]["Name"]),
    )


def _names(base: str, head: str) -> tuple[tuple[str, str | None, str], ...]:
    return parse_name_status(
        _run("git", "diff", "--name-status", "-z", "-M", base, head)
    )


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
                _scc(blob, suffix, filename=Path(name).name)
                for blob, suffix, name in (
                    (before, old_suffix, old_path or path),
                    (after, new_suffix, path),
                )
                if blob
            )
            removed_language = full[0][3] if before and not old_suffix else None
            added_language = full[-1][3] if after and not new_suffix else None
            removed_code = _scc(
                "".join(fragments.removed).encode(), old_suffix, removed_language
            )[0]
            added_code = _scc(
                "".join(fragments.added).encode(), new_suffix, added_language
            )[0]
            classification = classify_samples(
                tuple(
                    (code, generated, minified) for code, generated, minified, _ in full
                ),
                removed_code,
                added_code,
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
    sys.stdout.write(
        json.dumps(
            {
                "total_units": total_units(results),
                "files": [asdict(result) for result in results],
            },
            sort_keys=True,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
