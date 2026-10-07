"""Pure changed-line and exclusion decisions for pull request size."""

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import PurePosixPath

PROSE_SUFFIXES = frozenset({".md", ".mdx", ".rst", ".txt", ".qmd", ".adoc"})


@dataclass(frozen=True)
class Fragments:
    """Changed lines on both sides of one file comparison."""

    removed: tuple[str, ...]
    added: tuple[str, ...]


@dataclass(frozen=True)
class Classification:
    """Recorded scc output for changed fragments and complete file sides."""

    removed_code: int = 0
    added_code: int = 0
    generated: bool = False
    minified: bool = False
    binary: bool = False


@dataclass(frozen=True)
class FileResult:
    """Stable per-file result consumed by later workflow checks."""

    path: str
    old_path: str | None
    raw_added: int
    raw_deleted: int
    counted_units: int
    exclusion_reason: str | None


def changed_fragments(before: str, after: str) -> Fragments:
    """Retain every added and removed line, including equal-count replacements."""
    old = _git_lines(before)
    new = _git_lines(after)
    removed: list[str] = []
    added: list[str] = []
    for tag, start_old, end_old, start_new, end_new in SequenceMatcher(
        None, old, new, autojunk=False
    ).get_opcodes():
        if tag != "equal":
            removed.extend(old[start_old:end_old])
            added.extend(new[start_new:end_new])
    return Fragments(tuple(removed), tuple(added))


def _git_lines(content: str) -> tuple[str, ...]:
    """Split only on LF, as git does for text diffs."""
    parts = content.split("\n")
    return tuple(f"{part}\n" for part in parts[:-1]) + (
        (parts[-1],) if parts[-1] else ()
    )


def exclusion_reason(
    path: str, old_path: str | None, patterns: tuple[str, ...]
) -> str | None:
    """Name the first configured exclusion matched by either side of a rename."""
    for pattern in patterns:
        if any(
            PurePosixPath(candidate).full_match(pattern)
            for candidate in (path, old_path)
            if candidate is not None
        ):
            return f"path:{pattern}"
    return None


def needs_scc(
    path: str, old_path: str | None, patterns: tuple[str, ...], binary: bool
) -> bool:
    """Request tool classification only for included text files."""
    return not binary and exclusion_reason(path, old_path, patterns) is None


def parse_name_status(output: bytes) -> tuple[tuple[str, str | None, str], ...]:
    """Turn NUL-delimited git status output into path records."""
    fields = output.split(b"\0")
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


def classify_samples(
    full: tuple[tuple[int, bool, bool], ...],
    removed_code: int,
    added_code: int,
) -> Classification:
    """Combine recorded scc values from both complete sides and fragments."""
    return Classification(
        removed_code,
        added_code,
        any(sample[1] for sample in full),
        any(sample[2] for sample in full),
    )


def measure_file(
    path: str,
    old_path: str | None,
    fragments: Fragments,
    classification: Classification,
    patterns: tuple[str, ...],
) -> FileResult:
    """Apply configured exclusions to recorded git lines and scc values."""
    raw_added = len(fragments.added)
    raw_deleted = len(fragments.removed)
    reason = exclusion_reason(path, old_path, patterns)
    if reason is None and classification.binary:
        reason = "binary"
    if reason is None and classification.generated:
        reason = "scc:generated"
    if reason is None and classification.minified:
        reason = "scc:minified"
    if reason is not None:
        units = 0
    elif PurePosixPath(path).suffix.lower() in PROSE_SUFFIXES:
        units = sum(
            bool(line.strip()) for line in (*fragments.removed, *fragments.added)
        )
    else:
        units = classification.removed_code + classification.added_code
    return FileResult(path, old_path, raw_added, raw_deleted, units, reason)


def total_units(results: tuple[FileResult, ...]) -> int:
    """Sum the measured units from every included file."""
    return sum(result.counted_units for result in results)
