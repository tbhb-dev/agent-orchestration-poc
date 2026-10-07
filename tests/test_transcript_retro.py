"""Synthetic contracts for session normalization and privacy."""

import runpy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

MODULE = (
    Path(__file__).resolve().parents[1] / "experiments/18-transcript-retro/normalize.py"
)
if not MODULE.is_file():
    # Mutmut copies tests under mutants/ without experiment scripts.
    MODULE = MODULE.parents[3] / MODULE.relative_to(MODULE.parents[2])
FIXTURES = Path(__file__).parent / "fixtures/transcript_retro"
rules: dict[str, Any] = runpy.run_path(str(MODULE))
KEY = b"synthetic-test-key-with-at-least-32-bytes"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-09-26T04:00:00Z", True),
        ("2026-09-27T03:59:59-00:00", True),
        ("2026-09-26T03:59:59Z", False),
        ("2026-09-27T04:00:00Z", False),
        ("2026-09-26T04:00:00", False),
        ("bad", False),
        (None, False),
    ],
)
def test_day_bounds(value: object, expected: bool) -> None:
    """Use the New York local day and reject unknown timestamps."""
    assert rules["in_day"](rules["utc_time"](value)) is expected


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("codex-sessions/x.jsonl", "codex-native"),
        ("claude-code/x.jsonl", "claude-native"),
        ("codex-runs/x.log", "captured-run"),
        ("webhooks/x.json", "webhook"),
        ("other/x", "unknown"),
    ],
)
def test_source_type(relative: str, expected: str) -> None:
    """Keep source precedence categories explicit."""
    assert rules["source_type"](relative) == expected


def test_native_fixture_preserves_unknowns_and_deduplicates() -> None:
    """A repeated capture does not add calls, outputs, waits, or tokens."""
    records, bad = rules["parse_jsonl"](
        (FIXTURES / "codex-native.jsonl").read_text().splitlines()
    )
    assert bad == 0
    assert rules["record_range"](records) == (
        "2026-09-26T03:59:59+00:00",
        "2026-09-27T04:00:00+00:00",
        0,
    )
    assert rules["session_details"](records) == (
        "synthetic-session",
        True,
        "synthetic-model",
        "",
    )
    rows = rules["normalize_codex"](records, KEY, "S1")
    assert [row["kind"] for row in rows] == ["call", "output", "wait", "token"]
    assert rows[3]["input_tokens"] == "12"
    assert rows[3]["output_tokens"] == ""
    assert all(row["effort"] == "" for row in rows)
    repeated, _ = rules["parse_jsonl"](
        (FIXTURES / "repeated-capture.jsonl").read_text().splitlines()
    )
    replay = records[:2] + repeated
    other = rules["normalize_codex"](replay, KEY, "S2")
    unique, duplicate, ambiguous = rules["deduplicate"](rows + other)
    assert len(unique) == 4
    assert duplicate == 3
    assert ambiguous == 0
    rules["validate_export"](unique)


def test_bad_records_and_ambiguous_match() -> None:
    """Unreadable lines and conflicting duplicate fields remain visible."""
    rows, bad = rules["parse_jsonl"](["not json", "[]", '{"timestamp":"bad"}'])
    assert bad == 2
    assert rules["record_range"](rows) == ("", "", 1)
    context = rules["Context"](KEY, "S1", "sid")
    original = rules["event"](
        context, 1, datetime(2026, 9, 26, 4, tzinfo=UTC), "call", "cid"
    )
    changed = dict(original, status="failed")
    assert rules["deduplicate"]([original, changed])[1:] == (1, 1)


def test_pure_response_rules_and_fallback() -> None:
    """Calls and outputs produce one wait without changing input state."""
    context = rules["Context"](KEY, "S1", "sid", "child agent", "turn")
    start = datetime(2026, 9, 26, 4, tzinfo=UTC)
    calls: dict[str, Any] = {}
    called, next_calls = rules["response_events"](
        context,
        1,
        start,
        {"type": "function_call", "call_id": "cid", "name": "tool"},
        calls,
    )
    assert calls == {}
    assert called[0]["actor"] == "child agent"
    output, finished = rules["response_events"](
        context,
        2,
        start.replace(second=1),
        {"type": "function_call_output", "call_id": "cid", "output": "ok"},
        next_calls,
    )
    assert next_calls
    assert finished == {}
    assert [row["kind"] for row in output] == ["output", "wait"]
    assert output[1]["duration_ms"] == "1000"
    fallback = rules["fallback_id"](context, start, "tool", {"b": 2, "a": 1})
    assert fallback == rules["fallback_id"](context, start, "tool", {"a": 1, "b": 2})
    assert fallback != rules["fallback_id"](context, start, "tool", {"a": 2, "b": 1})


@pytest.mark.parametrize(
    ("native_kind", "payload", "expected"),
    [
        ("token_usage_record", {"usage": {"input_tokens": 1}}, "token"),
        ("token_usage_record", {}, None),
        ("event_msg", {"type": "turn_aborted", "turn_id": "turn"}, "failure"),
        ("event_msg", {"type": "turn_aborted"}, None),
        ("event_msg", {"type": "task_complete"}, None),
    ],
)
def test_other_event_rules(
    native_kind: str, payload: dict[str, Any], expected: str | None
) -> None:
    """Usage and failure require explicit native fields."""
    context = rules["Context"](KEY, "S1", "sid")
    result = rules["other_event"](
        context, 1, datetime(2026, 9, 26, 4, tzinfo=UTC), native_kind, payload
    )
    assert (result["kind"] if result else None) == expected


def test_child_actor_and_foreign_session() -> None:
    """A parent link identifies child agents and foreign sessions stay out."""
    records, _ = rules["parse_jsonl"](
        (FIXTURES / "codex-native.jsonl").read_text().splitlines()
    )
    assert rules["session_actor"](records) == "worker"
    child = list(records)
    child[0] = (
        1,
        {
            "type": "session_meta",
            "payload": {
                "id": "sid",
                "parent_thread_id": "parent",
                "cwd": "/synthetic/agent-orchestration-poc",
            },
        },
    )
    assert rules["session_actor"](child) == "child agent"
    foreign = [
        (
            1,
            {
                "type": "session_meta",
                "payload": {"id": "sid", "cwd": "/synthetic/other"},
            },
        )
    ]
    assert rules["normalize_codex"](foreign, KEY, "S1") == []


def test_cross_midnight_wait_uses_prior_call() -> None:
    """An in-day output retains elapsed time from a prior-day call."""
    records, _ = rules["parse_jsonl"](
        [
            '{"timestamp":"2026-09-26T03:59:57Z","type":"session_meta","payload":{"id":"sid","cwd":"/synthetic/agent-orchestration-poc"}}',
            '{"timestamp":"2026-09-26T03:59:58Z","type":"response_item","payload":{"type":"function_call","call_id":"cid","name":"tool"}}',
            '{"timestamp":"2026-09-26T04:00:01Z","type":"response_item","payload":{"type":"function_call_output","call_id":"cid","output":"ok"}}',
        ]
    )
    rows = rules["normalize_codex"](records, KEY, "S1")
    assert [row["kind"] for row in rows] == ["output", "wait"]
    assert rows[1]["duration_ms"] == "3000"


@pytest.mark.parametrize("field", ["prompt", "transcript", "private_prompt"])
def test_raw_record_is_rejected(field: str) -> None:
    """Synthetic private fields cannot enter committed event rows."""
    row = dict.fromkeys(rules["EVENT_FIELDS"], "")
    row[field] = "synthetic raw record"
    with pytest.raises(ValueError, match="schema"):
        rules["validate_export"]([row])


def test_secret_signature_is_rejected() -> None:
    """A planted token shape cannot enter event output."""
    row = dict.fromkeys(rules["EVENT_FIELDS"], "")
    row["tool"] = "ghp_" + "X" * 36
    with pytest.raises(ValueError, match="private content"):
        rules["validate_export"]([row])


@given(st.text(max_size=40), st.text(max_size=40))
def test_opaque_ids_are_stable_and_domain_separated(a: str, b: str) -> None:
    """Matching inputs have stable IDs and changed components change IDs."""
    same = rules["opaque"](KEY, a, b)
    assert same == rules["opaque"](KEY, a, b)
    if a != b:
        assert same != rules["opaque"](KEY, b, a)
