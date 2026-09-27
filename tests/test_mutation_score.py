"""Value tests for the mutmut CI score decision."""

import pytest

from agent_orchestration_poc.core.mutation_score import evaluate


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"killed": 9, "survived": 1, "total": 10}, (90.0, True)),
        ({"killed": 8, "survived": 2, "total": 10}, (80.0, False)),
        ({"killed": 7, "survived": 3, "total": 10}, (70.0, False)),
        ({"killed": 1, "total": 1}, (100.0, True)),
        ({"killed": 1, "segfault": 25, "total": 26}, (100 / 26, False)),
        ({"killed": 9, "segfault": 1, "total": 10}, (90.0, False)),
        ({"killed": 1, "check_was_interrupted_by_user": 1, "total": 2}, (50.0, False)),
        ({"killed": 9, "skipped": 1, "total": 10}, (90.0, False)),
        ({"killed": 1, "total": 2}, (50.0, False)),
        ({"killed": 1, "total": 1, "unknown": 1}, (0.0, False)),
        ({}, (0.0, False)),
    ],
)
def test_evaluate(changes: dict[str, int], expected: tuple[float, bool]) -> None:
    stats = dict.fromkeys(
        (
            "killed",
            "survived",
            "no_tests",
            "skipped",
            "suspicious",
            "timeout",
            "check_was_interrupted_by_user",
            "segfault",
            "total",
        ),
        0,
    )
    stats.update(changes)
    assert evaluate(stats) == expected
