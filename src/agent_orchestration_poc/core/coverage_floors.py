"""Evaluate language coverage reports without reading files or running tests."""

from typing import TypedDict


class Summary(TypedDict):
    """Coverage.py statement and branch counts for one file."""

    covered_lines: int  # noqa: V107  Read from coverage JSON by key.
    num_statements: int  # noqa: V107  Read from coverage JSON by key.
    covered_branches: int  # noqa: V107  Read from coverage JSON by key.
    num_branches: int  # noqa: V107  Read from coverage JSON by key.


class File(TypedDict):
    """Coverage.py report entry for one file."""

    summary: Summary


class Report(TypedDict):
    """Coverage.py JSON fields needed by the gate."""

    meta: dict[str, bool]  # noqa: V107  Read from coverage JSON by key.
    files: dict[str, File]


def percent(covered: int, total: int) -> float:
    """Return a percentage, treating an empty group as fully covered."""
    return 100.0 if total == 0 else 100 * covered / total


def evaluate_python(report: Report) -> tuple[float, float, float | None, bool]:
    """Gate core lines and branches, plus shell lines when shell code exists."""
    core_lines = core_total = core_branches = branch_total = 0
    shell_lines = shell_total = 0
    for path, entry in report["files"].items():
        summary = entry["summary"]
        if "/core/" in path:
            core_lines += summary["covered_lines"]
            core_total += summary["num_statements"]
            core_branches += summary["covered_branches"]
            branch_total += summary["num_branches"]
        elif "/shell/" in path:
            shell_lines += summary["covered_lines"]
            shell_total += summary["num_statements"]
    shell_score = percent(shell_lines, shell_total) if shell_total else None
    passed = (
        report["meta"]["branch_coverage"]
        and core_total > 0
        and core_lines * 100 >= core_total * 95
        and (branch_total == 0 or core_branches * 100 >= branch_total * 90)
        and (shell_total == 0 or shell_lines * 100 >= shell_total * 70)
    )
    return (
        percent(core_lines, core_total),
        percent(core_branches, branch_total),
        shell_score,
        passed,
    )


def evaluate_go(profile: str) -> tuple[float, float, bool]:
    """Gate core and shell statement counts from a Go coverprofile."""
    core_covered = core_total = shell_covered = shell_total = 0
    for line in profile.splitlines()[1:]:
        path, statements, hits = line.split()
        count = int(statements)
        covered = count if int(hits) > 0 else 0
        if "/internal/core/" in path:
            core_covered += covered
            core_total += count
        elif "/internal/" in path or "/cmd/" in path:
            shell_covered += covered
            shell_total += count
    passed = (
        core_total > 0
        and shell_total > 0
        and core_covered * 100 >= core_total * 95
        and shell_covered * 100 >= shell_total * 70
    )
    return (
        percent(core_covered, core_total),
        percent(shell_covered, shell_total),
        passed,
    )


def evaluate_gobco(outputs: list[str]) -> tuple[float, bool]:
    """Gate the aggregate branch count printed for each Go core package."""
    covered = total = 0
    for output in outputs:
        summary = next(
            line for line in output.splitlines() if line.startswith("Branch coverage: ")
        )
        pair = summary.removeprefix("Branch coverage: ").split("/")
        covered += int(pair[0])
        total += int(pair[1])
    return percent(covered, total), total > 0 and covered * 100 >= total * 90
