"""Evaluate mutmut's exported CI stats without side effects."""

from collections.abc import Mapping

OUTCOMES = frozenset(
    {
        "killed",
        "survived",
        "no_tests",
        "skipped",
        "suspicious",
        "timeout",
        "check_was_interrupted_by_user",
        "segfault",
    }
)
SCORED = frozenset({"killed", "survived", "no_tests", "suspicious", "timeout"})


def evaluate(stats: Mapping[str, int]) -> tuple[float, bool]:
    """Return the score and whether a complete run meets the 80 percent floor."""
    if stats.keys() != OUTCOMES | {"total"}:
        return 0.0, False
    total = stats["total"]
    if total <= 0 or any(stats[key] < 0 for key in OUTCOMES):
        return 0.0, False
    score = 100 * stats["killed"] / total
    if sum(stats[key] for key in SCORED) != total:
        return score, False
    return score, score >= 80
