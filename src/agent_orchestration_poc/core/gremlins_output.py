"""Evaluate gremlins results without side effects."""

from collections.abc import Mapping
from typing import cast


def evaluate(result: Mapping[str, object]) -> tuple[int, int, bool]:
    """Return the mutant count, timeout count, and completion decision."""
    files = cast("list[dict[str, object]]", result["files"])
    statuses = [
        mutation["status"]
        for file in files
        for mutation in cast("list[dict[str, str]]", file["mutations"])
    ]
    timed_out = sum(status == "TIMED OUT" for status in statuses)
    return len(statuses), timed_out, bool(statuses) and timed_out == 0
