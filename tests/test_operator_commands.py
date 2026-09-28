"""Fixture and property checks for pure operator command decisions."""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.operator_commands import (
    Decision,
    Effects,
    decide,
    effects,
    latest_ask,
    numbered_ask,
    parse_command,
    preflight,
    valid_selection,
    valid_source,
)

FIXTURES = Path(__file__).parent / "fixtures/operator-commands"
FORMS = (
    ("/approve all", "approve", "1,2,3"),
    ("/approve lines=1,3", "approve", "1,3"),
    ("/reject lines=2", "reject", "2"),
    ("/choose option=2", "choose", "2"),
    ("/answer text=known fact", "answer", "known fact"),
    ("/question text=what changed?", "question", "what changed?"),
    ("/defer reason=need evidence", "defer", "need evidence"),
    ("/withdraw", "withdraw", ""),
)


def fixture(item_type: str) -> dict[str, Any]:
    """Load one checked-in issue or pull request payload."""
    return cast(
        "dict[str, Any]", json.loads((FIXTURES / f"{item_type}.json").read_text())
    )


@pytest.mark.parametrize("item_type", ["issue", "pr"])
@pytest.mark.parametrize(("body", "kind", "value"), list(FORMS))
def test_valid_forms_on_both_items(
    item_type: str, body: str, kind: str, value: str
) -> None:
    data = fixture(item_type)
    data["comment"]["body"] = body
    result = decide(data["event"], data["comment"], data["item"], (data["ask"],))
    assert result.reaction == "+1"
    assert result.add_label
    assert result.command is not None
    assert (result.command.kind, result.command.value) == (kind, value)
    assert result.command.ask_id == 99
    assert result.command.ask_updated_at == "2026-09-28T12:00:00Z"


@pytest.mark.parametrize(
    "body",
    [
        "/approve lines=1,1",
        "/approve lines=3,1",
        "/approve lines=1-3",
        "/approve lines=4",
        "/approve lines=",
        "/reject lines=4",
        "/choose option=3",
        "/answer text= ",
        "/question text=",
        "/defer reason=",
        "/Approve all",
        "/approve all now",
        "/approve all\nmore",
        "/answer text=hi\nbye",
        "/answer text=$(touch /tmp/hostile)",
    ],
)
def test_invalid_or_literal_text(body: str) -> None:
    data = fixture("issue")
    data["comment"]["body"] = body
    result = decide(data["event"], data["comment"], data["item"], (data["ask"],))
    if "$(touch" in body:
        assert result.reaction == "+1"
        assert result.command is not None
        assert result.command.value == "$(touch /tmp/hostile)"
    else:
        assert result.reaction == "confused"
        assert not result.add_label


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actor", "someone"),
        ("action", "edited"),
    ],
)
def test_ignored_event(field: str, value: str) -> None:
    data = fixture("issue")
    data["event"][field] = value
    assert (
        decide(data["event"], data["comment"], data["item"], (data["ask"],)).reaction
        is None
    )


def test_identity_and_item_refusals() -> None:
    for section, field, value in (
        ("comment", "author_association", "COLLABORATOR"),
        ("comment", "updated_at", "2026-09-28T12:02:00Z"),
        ("item", "state", "closed"),
        ("item", "labels", list[dict[str, str]]()),
        ("event", "comment_id", 101),
        ("event", "is_pr", True),
    ):
        data = fixture("issue")
        data[section][field] = value
        assert (
            decide(
                data["event"], data["comment"], data["item"], (data["ask"],)
            ).reaction
            is None
        )
    data = fixture("issue")
    data["comment"]["user"]["login"] = "other"
    assert (
        decide(data["event"], data["comment"], data["item"], (data["ask"],)).reaction
        is None
    )
    data = fixture("issue")
    data["item"]["labels"].append({"name": "operator/review"})
    assert (
        decide(data["event"], data["comment"], data["item"], (data["ask"],)).reaction
        is None
    )


def test_missing_ambiguous_and_paginated_ask() -> None:
    data = fixture("issue")
    assert (
        decide(data["event"], data["comment"], data["item"], ()).reaction == "confused"
    )
    duplicate = data["ask"] | {
        "body": data["ask"]["body"] + "\n### Operator ask: another"
    }
    assert latest_ask((duplicate,)) is None
    assert (
        decide(data["event"], data["comment"], data["item"], (duplicate,)).reaction
        == "confused"
    )
    older = data["ask"] | {"id": 98, "created_at": "2026-09-27T12:00:00Z"}
    assert latest_ask((older, data["ask"])) is None
    assert (
        decide(
            data["event"], data["comment"], data["item"], (older, data["ask"])
        ).reaction
        == "confused"
    )
    retired = older | {
        "body": older["body"].replace("Operator ask:", "Resolved operator ask:")
    }
    assert latest_ask((retired, data["ask"])) == data["ask"]
    assert (
        decide(
            data["event"], data["comment"], data["item"], (retired, data["ask"])
        ).reaction
        == "+1"
    )


def test_numbered_prose_outside_ask_sections_is_not_selectable() -> None:
    data = fixture("issue")
    data["ask"]["body"] = (
        "1. Preface\n### Operator ask: approval only\n"
        "1. Intro\nApproval lines:\n1. Allow action\n"
        "## Background\n2. Unrelated fact\nOptions:\nOption 3: unrelated"
    )
    assert numbered_ask(data["ask"]["body"]) == ((1,), ())
    data["comment"]["body"] = "/choose option=2"
    assert (
        decide(data["event"], data["comment"], data["item"], (data["ask"],)).reaction
        == "confused"
    )


@pytest.mark.parametrize("item_type", ["issue", "pr"])
def test_preflight_fixture_gate(item_type: str) -> None:
    data = fixture(item_type)
    event = data["event"] | {"issue": data["item"], "comment": {"id": 100}}
    assert preflight(event, 11, 12) is not None
    assert preflight(event, 999, 998) is None
    assert preflight(event | {"actor": "other"}, 11, 12) is None
    assert preflight(event | {"action": "edited"}, 11, 12) is None
    assert preflight(event | {"comment": {"id": 0}}, 11, 12) is None
    wrong_type = event | {
        "issue": data["item"] | {"number": 12 if item_type == "issue" else 11}
    }
    assert preflight(wrong_type, 11, 12) is None


def test_numbered_ask_requires_unique_numbers() -> None:
    data = fixture("issue")
    assert numbered_ask(data["ask"]["body"]) == ((1, 2, 3), (1, 2))
    assert numbered_ask("no ask") is None
    assert numbered_ask("### Operator ask\nApproval lines:\n1. one\n1. two") is None


@given(st.integers(min_value=1, max_value=100))
def test_numbered_ask_property(number: int) -> None:
    body = f"### Operator ask: property\nApproval lines:\n{number}. one"
    assert numbered_ask(body) == ((number,), ())


@given(st.integers(min_value=1, max_value=100))
def test_latest_ask_ignores_page_order(number: int) -> None:
    data = fixture("issue")
    older = data["ask"] | {
        "id": number,
        "created_at": "2026-09-27T12:00:00Z",
        "body": data["ask"]["body"].replace("Operator ask:", "Resolved operator ask:"),
    }
    assert latest_ask((older, data["ask"])) == latest_ask((data["ask"], older))


@given(st.text().filter(lambda actor: actor != "tbhb"))
def test_valid_source_rejects_other_actors(actor: str) -> None:
    data = fixture("issue")
    data["event"]["actor"] = actor
    assert not valid_source(data["event"], data["comment"], data["item"])


@given(st.integers(min_value=1, max_value=10))
def test_selection_is_bound_to_current_lines(number: int) -> None:
    ask = fixture("issue")["ask"]["body"]
    selected = valid_selection("reject", str(number), ask)
    assert (selected is not None) is (number in {1, 2, 3})


@given(st.sampled_from([form[0] for form in FORMS]))
def test_decision_is_deterministic(body: str) -> None:
    data = fixture("pr")
    data["comment"]["body"] = body
    values = (data["event"], data["comment"], data["item"], (data["ask"],))
    assert decide(*values) == decide(*values)


@pytest.mark.parametrize(
    ("decision", "labels", "reactions", "expected"),
    [
        (Decision("+1", True), frozenset(), (), Effects("+1", True)),
        (
            Decision("+1", True),
            frozenset({"operator/replied"}),
            (),
            Effects("+1", False),
        ),
        (
            Decision("+1", True),
            frozenset(),
            (("github-actions[bot]", "+1"),),
            Effects(None, False),
        ),
        (
            Decision("+1", True),
            frozenset(),
            (("github-actions[bot]", "confused"),),
            Effects(None, False),
        ),
        (
            Decision("confused"),
            frozenset(),
            (("github-actions[bot]", "+1"),),
            Effects(None, False),
        ),
    ],
)
def test_effects_preserve_first_acknowledgement(
    decision: Decision,
    labels: frozenset[str],
    reactions: tuple[tuple[str, str], ...],
    expected: Effects,
) -> None:
    assert effects(decision, labels, reactions) == expected


@given(st.text())
def test_effects_ignore_other_reaction_authors(login: str) -> None:
    if login != "github-actions[bot]":
        result = effects(Decision("+1", True), frozenset(), ((login, "confused"),))
        assert result == Effects("+1", True)


@given(st.text())
def test_parser_never_accepts_multiline(text: str) -> None:
    if "\n" in text.strip() or "\r" in text.strip():
        assert parse_command(text) is None


@given(st.lists(st.integers(min_value=1, max_value=100), min_size=2, max_size=8))
def test_line_selection_requires_strict_ascending(numbers: list[int]) -> None:
    data = fixture("issue")
    value = ",".join(map(str, numbers))
    data["comment"]["body"] = f"/approve lines={value}"
    result = decide(data["event"], data["comment"], data["item"], (data["ask"],))
    valid = numbers == sorted(set(numbers)) and set(numbers) <= {1, 2, 3}
    assert (result.reaction == "+1") is valid
