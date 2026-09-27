"""Plain-value and property checks for review policy decisions."""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.review_identity import (
    REQUIRED_CHECKS,
    another_review_round_allowed,
    approval_current,
    branch_update_method,
    required_checks_match,
    reviewer_command_allowed,
    reviewer_identity_matches,
    reviewer_token_present,
)

FIXTURES = Path(__file__).parent
POLICY = cast(
    "dict[str, list[dict[str, Any]]]",
    json.loads((FIXTURES / "policy.json").read_text()),
)


@pytest.mark.parametrize("case", POLICY["approvals"], ids=lambda case: case["case"])
def test_approval(case: dict[str, Any]) -> None:
    assert (
        approval_current(
            case["reviewer"], case["state"], case["active"], case["last_pusher"]
        )
        is case["expected"]
    )


@pytest.mark.parametrize("case", POLICY["rounds"], ids=lambda case: case["case"])
def test_round(case: dict[str, Any]) -> None:
    assert (
        another_review_round_allowed(
            case["changes_requested"],
            case["third_verdict_at"],
            case["arbitration_author"],
            case["arbitration_body"],
            case["arbitration_at"],
        )
        is case["expected"]
    )


@pytest.mark.parametrize("case", POLICY["checks"], ids=lambda case: case["case"])
def test_required_checks(case: dict[str, Any]) -> None:
    assert required_checks_match(case["checks"]) is case["expected"]


@pytest.mark.parametrize("case", POLICY["branches"], ids=lambda case: case["case"])
def test_branch_method(case: dict[str, Any]) -> None:
    assert branch_update_method(case["published"]) == case["expected"]


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [([], False), (["auth", "token"], False), (["pr", "review", "1"], True)],
)
def test_reviewer_command(arguments: list[str], expected: bool) -> None:
    assert reviewer_command_allowed(arguments) is expected


@pytest.mark.parametrize(
    ("token", "expected"), [("", False), ("   ", False), ("fixture-only", True)]
)
def test_token_presence(token: str, expected: bool) -> None:
    assert reviewer_token_present(token) is expected


@pytest.mark.parametrize(
    ("login", "expected"), [("tbhbbot", True), ("tbhb", False), ("", False)]
)
def test_reviewer_identity(login: str, expected: bool) -> None:
    assert reviewer_identity_matches(login) is expected


@given(st.lists(st.text(), max_size=5))
def test_auth_command_never_allowed(tail: list[str]) -> None:
    assert not reviewer_command_allowed(["auth", *tail])


@given(st.text().filter(lambda value: value != "tbhbbot"))
def test_other_identity_never_matches(login: str) -> None:
    assert not reviewer_identity_matches(login)


@given(st.text())
def test_token_presence_matches_nonblank(token: str) -> None:
    assert reviewer_token_present(token) is bool(token.strip())


@given(st.text().filter(lambda value: value != "tbhbbot"))
def test_other_reviewer_cannot_approve(reviewer: str) -> None:
    assert not approval_current(reviewer, "APPROVED", True, "tbhb")


@given(st.integers(min_value=0, max_value=2))
def test_fewer_than_three_requests_allow_round(count: int) -> None:
    assert another_review_round_allowed(count, "", "", "", "")


@given(st.permutations(tuple(REQUIRED_CHECKS)))
def test_required_checks_are_order_independent(checks: list[str]) -> None:
    assert required_checks_match(checks)


@given(st.booleans())
def test_branch_method_matches_publication(published: bool) -> None:
    assert branch_update_method(published) == ("merge" if published else "rebase")
