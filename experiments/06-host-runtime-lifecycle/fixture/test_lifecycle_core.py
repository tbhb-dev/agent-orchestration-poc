"""Plain-value examples and properties for the lifecycle decisions."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from .lifecycle_core import (  # pyrefly: ignore[missing-import]
    PROFILES,
    Record,
    process_start_from_query,
    process_state,
    retained_state,
    validate,
)


@pytest.mark.parametrize("profile", PROFILES)
def test_validate_profiles(profile: str) -> None:
    """Every approved profile accepts complete identity fields."""
    assert validate(Record(profile, "A", "A-1", None, 123, "start"))  # noqa: S101 - pytest assertion


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (Record("other", "A", "A-1", None, 123, "start"), False),
        (Record("codex-headless", "", "A-1", None, 123, "start"), False),
        (Record("codex-headless", "A", "", None, 123, "start"), False),
        (Record("codex-headless", "A", "A-1", "", 123, "start"), False),
        (Record("codex-headless", "A", "A-1", None, 0, "start"), False),
        (Record("codex-headless", "A", "A-1", None, 123, ""), False),
    ],
)
def test_validate_rejects_missing_identity(record: Record, expected: bool) -> None:
    """Missing fields and unapproved profiles fail validation."""
    assert validate(record) is expected  # noqa: S101 - pytest assertion


@given(st.text(min_size=1), st.integers(min_value=1))
def test_validate_property(incarnation: str, pid: int) -> None:
    """Valid values stay valid regardless of the chosen incarnation and PID."""
    assert validate(Record("claude-headless", "A", incarnation, None, pid, "start"))  # noqa: S101 - pytest assertion


@pytest.mark.parametrize(
    ("current", "expected"),
    [(None, "absent"), ("other", "different-incarnation"), ("start", "live")],
)
def test_process_state(current: str | None, expected: str) -> None:
    """PID existence alone does not prove process identity."""
    record = Record("codex-headless", "A", "A-1", None, 123, "start")
    assert process_state(record, current) == expected  # noqa: S101 - pytest assertion


def test_process_query_result() -> None:
    """Only an empty missing-PID result establishes absence."""
    assert process_start_from_query(0, "start\n", "") == "start"  # noqa: S101 - pytest assertion
    assert process_start_from_query(1, "", "") is None  # noqa: S101 - pytest assertion
    with pytest.raises(ValueError, match="permission denied"):
        process_start_from_query(1, "", "permission denied")
    with pytest.raises(ValueError, match="exited 2"):
        process_start_from_query(2, "", "")


@given(st.text(min_size=1), st.text(min_size=1))
def test_process_state_property(start: str, other: str) -> None:
    """Only the exact recorded start time counts as the same process."""
    record = Record("codex-headless", "A", "A-1", None, 123, start)
    assert (process_state(record, other) == "live") is (start == other)  # noqa: S101 - pytest assertion


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ({}, {}, "no-baseline"),
        ({"a": "x"}, {"a": "x", "b": "y"}, "retained"),
        ({"a": "x"}, {"a": "y"}, "changed-or-missing"),
        ({"a": "x"}, {}, "changed-or-missing"),
    ],
)
def test_retained_state(
    before: dict[str, str], after: dict[str, str], expected: str
) -> None:
    """Retention requires every baseline fingerprint to remain."""
    assert retained_state(before, after) == expected  # noqa: S101 - pytest assertion


@given(st.dictionaries(st.text(min_size=1), st.text(min_size=1), min_size=1))
def test_retained_state_property(state: dict[str, str]) -> None:
    """An unchanged private-state snapshot always remains retained."""
    after = state | {"new-file": state.get("new-file", "fingerprint")}
    assert retained_state(state, after) == "retained"  # noqa: S101 - pytest assertion
