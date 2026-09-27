"""Value tests for the gremlins completion decision."""

import pytest

from agent_orchestration_poc.core.gremlins_output import evaluate


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (["KILLED"], (1, 0, True)),
        (["TIMED OUT"], (1, 1, False)),
        ([], (0, 0, False)),
        (["KILLED", "TIMED OUT"], (2, 1, False)),
    ],
)
def test_evaluate(statuses: list[str], expected: tuple[int, int, bool]) -> None:
    result = {"files": [{"mutations": [{"status": status} for status in statuses]}]}
    assert evaluate(result) == expected
