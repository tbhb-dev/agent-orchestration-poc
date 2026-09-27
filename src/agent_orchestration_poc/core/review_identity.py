"""Pure decisions for reviewer account commands and review policy."""

from collections.abc import Sequence

REVIEWER = "tbhbbot"
IMPLEMENTER = "tbhb"
REQUIRED_CHECKS = frozenset(
    {"check", "docs", "pr-body", "imported-research", "mutation"}
)


def reviewer_command_allowed(arguments: Sequence[str]) -> bool:
    """Reject commands that could print the reviewer's credential."""
    return bool(arguments) and arguments[0] != "auth"


def reviewer_token_present(token: str) -> bool:
    """Accept a nonempty token obtained for the named reviewer."""
    return bool(token.strip())


def reviewer_identity_matches(login: str) -> bool:
    """Require the effective account to match the named reviewer."""
    return login == REVIEWER


def approval_current(reviewer: str, state: str, active: bool, last_pusher: str) -> bool:
    """Decide whether a recorded approval satisfies the project policy."""
    return (
        reviewer == REVIEWER
        and state == "APPROVED"
        and active
        and last_pusher != reviewer
    )


def another_review_round_allowed(
    changes_requested: int,
    third_verdict_at: str,
    arbitration_author: str,
    arbitration_body: str,
    arbitration_at: str,
) -> bool:
    """Require the coordinator's exact, newer arbitration command after round three."""
    if changes_requested < 3:
        return True
    return (
        arbitration_author == IMPLEMENTER
        and arbitration_body.rstrip("\r\n") == "Arbitration: authorize another round"
        and arbitration_at > third_verdict_at
    )


def required_checks_match(checks: Sequence[str]) -> bool:
    """Match the five required check contexts in the recorded ruleset."""
    return set(checks) == REQUIRED_CHECKS and len(checks) == len(REQUIRED_CHECKS)


def branch_update_method(published: bool) -> str:
    """Choose the permitted branch update method."""
    return "merge" if published else "rebase"
