"""Synthetic contracts for session normalization and privacy."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.analysis import transcript_retro

FIXTURES = Path(__file__).parent / "fixtures/transcript_retro"
rules: dict[str, Any] = vars(transcript_retro)
KEY = b"synthetic-test-key-with-at-least-32-bytes"
ROOTS = ("/tmp/agent-orchestration-poc", "/synthetic/agent-orchestration-poc")  # noqa: S108 - fixture cwd


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
    assert rules["session_details"](records, ROOTS) == (
        "synthetic-session",
        True,
        "synthetic-model",
        "",
    )
    rows = rules["normalize_codex"](records, KEY, "S1", ROOTS)
    assert [row["kind"] for row in rows] == ["call", "output", "wait", "token"]
    assert rows[3]["input_tokens"] == "12"
    assert rows[3]["output_tokens"] == ""
    assert all(row["effort"] == "" for row in rows)
    repeated, _ = rules["parse_jsonl"](
        (FIXTURES / "repeated-capture.jsonl").read_text().splitlines()
    )
    replay = records[:2] + repeated
    other = rules["normalize_codex"](replay, KEY, "S2", ROOTS)
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
    assert rules["normalize_codex"](foreign, KEY, "S1", ROOTS) == []


def test_similarly_named_directory_is_not_repository_member() -> None:
    """A matching repository name prefix does not grant membership."""
    records, _ = rules["parse_jsonl"](
        (FIXTURES / "codex-native.jsonl").read_text().splitlines()
    )
    foreign = list(records)
    first = dict(foreign[0][1])
    first["payload"] = dict(
        first["payload"], cwd="/synthetic/agent-orchestration-poc-unrelated"
    )
    foreign[0] = (1, first)
    assert rules["normalize_codex"](foreign, KEY, "S1", ROOTS) == []


def test_claude_similarly_named_directory_is_excluded() -> None:
    """Claude inventory uses the same exact root policy as Codex."""
    records = [(1, {"cwd": "/synthetic/agent-orchestration-poc-unrelated"})]
    assert (
        rules["source_metadata"]("claude-native", records, ROOTS)["state"] == "excluded"
    )
    records = [(1, {"cwd": "/synthetic/agent-orchestration-poc/.worktrees/child"})]
    assert (
        rules["source_metadata"]("claude-native", records, ROOTS)["state"] == "deferred"
    )


def test_source_metadata_exports_exact_decisions() -> None:
    """Keep every inventory decision in the value-only core."""
    codex = [
        (1, {"type": "session_meta", "payload": {"id": "sid", "cwd": ROOTS[0]}}),
        (
            2,
            {"type": "turn_context", "payload": {"model": "model-b", "effort": "high"}},
        ),
        (3, {"type": "turn_context", "payload": {"model": "model-a", "effort": "low"}}),
    ]
    assert rules["source_metadata"]("codex-native", codex, ROOTS) == {
        "harness": "codex",
        "model": "model-a,model-b",
        "effort": "high,low",
        "role": "worker",
        "state": "included",
        "reason": "",
    }
    claude = [
        (1, {"cwd": ROOTS[0], "isSidechain": True}),
        (2, {"type": "assistant", "message": {"model": "opus"}, "effort": "medium"}),
    ]
    assert rules["source_metadata"]("claude-native", claude, ROOTS) == {
        "harness": "claude",
        "model": "opus",
        "effort": "medium",
        "role": "child agent",
        "state": "deferred",
        "reason": "Claude normalization deferred",
    }
    assert rules["source_metadata"]("captured-run", [], ROOTS) == {
        "harness": "codex",
        "model": "",
        "effort": "",
        "role": "captured run log",
        "state": "deferred",
        "reason": "alternate capture pending matching, metadata unparsed",
    }
    assert rules["source_metadata"]("webhook", [], ROOTS) == {
        "harness": "github",
        "model": "",
        "effort": "",
        "role": "external delivery",
        "state": "excluded",
        "reason": "outside session-event population, metadata unparsed",
    }


def test_event_fields_and_stable_ids() -> None:
    """Assert the complete safe event schema and keyed identity."""
    context = rules["Context"](KEY, "S1", "sid", "child agent", "turn", "model", "high")
    row = rules["event"](
        context,
        7,
        datetime(2026, 9, 26, 4, tzinfo=UTC),
        "call",
        "cid",
        tool="tool",
        status="failed",
    )
    assert row == {
        "event_id": "6478b475df92af7fc10cbf7c",
        "source_id": "S1",
        "position": "7",
        "timestamp_utc": "2026-09-26T04:00:00+00:00",
        "actor": "child agent",
        "harness": "codex",
        "kind": "call",
        "turn_id": "da10fecab82841cab63279f5",
        "tool": "tool",
        "status": "failed",
        "output_bytes": "",
        "duration_ms": "",
        "input_tokens": "",
        "output_tokens": "",
        "total_tokens": "",
        "model": "model",
        "effort": "high",
    }
    assert rules["opaque"](KEY, "abc", "def") == "2490b9840bb4cb375ae1790b"


def test_usage_and_abort_export_all_numeric_fields() -> None:
    """Usage and abort rows preserve native status and numeric metadata."""
    context = rules["Context"](KEY, "S1", "sid", "worker", "turn", "model", "medium")
    stamp = datetime(2026, 9, 26, 4, tzinfo=UTC)
    usage = rules["usage_event"](
        context,
        2,
        stamp,
        {
            "response_id": "rid",
            "usage": {"input_tokens": 11, "output_tokens": 3, "total_tokens": 14},
        },
    )
    assert usage is not None
    assert (
        usage["kind"],
        usage["input_tokens"],
        usage["output_tokens"],
        usage["total_tokens"],
    ) == ("token", "11", "3", "14")
    assert (usage["position"], usage["model"], usage["effort"]) == (
        "2",
        "model",
        "medium",
    )
    aborted = rules["abort_event"](context, 3, stamp, {"turn_id": "aborted-turn"})
    assert aborted is not None
    assert (aborted["kind"], aborted["status"], aborted["position"]) == (
        "failure",
        "aborted",
        "3",
    )
    assert aborted["turn_id"] == rules["opaque"](KEY, "sid", "aborted-turn")


def test_response_events_retain_call_output_and_wait_metadata() -> None:
    """A tool pair keeps its native identity, byte count, status, and elapsed time."""
    context = rules["Context"](KEY, "S1", "sid", "child agent", "turn", "model", "high")
    start = datetime(2026, 9, 26, 4, tzinfo=UTC)
    called, pending = rules["response_events"](
        context,
        1,
        start,
        {
            "type": "function_call",
            "call_id": "cid",
            "name": "tool",
            "status": "running",
        },
        {},
    )
    assert pending == {"cid": (start, context)}
    assert called[0]["event_id"] == "6478b475df92af7fc10cbf7c"
    assert (called[0]["tool"], called[0]["status"], called[0]["position"]) == (
        "tool",
        "running",
        "1",
    )
    completed, pending = rules["response_events"](
        context,
        2,
        start.replace(microsecond=500000),
        {
            "type": "function_call_output",
            "call_id": "cid",
            "name": "tool",
            "output": "é",
        },
        pending,
    )
    assert pending == {}
    assert [row["event_id"] for row in completed] == [
        "9a008f3f59441fb7688028e6",
        "878cf023a27bbf693544d9b3",
    ]
    assert (
        completed[0]["tool"],
        completed[0]["output_bytes"],
        completed[0]["position"],
    ) == ("tool", "2", "2")
    assert (
        completed[1]["kind"],
        completed[1]["duration_ms"],
        completed[1]["position"],
    ) == ("wait", "500", "2")


def test_fallback_key_has_fixed_value() -> None:
    """Canonical payload and call context define a stable missing-ID key."""
    context = rules["Context"](KEY, "S1", "sid", "child agent", "turn", "model", "high")
    stamp = datetime(2026, 9, 26, 4, tzinfo=UTC)
    assert (
        rules["fallback_id"](context, stamp, "tool", {"b": 2, "a": 1})
        == "da1f535f255b82fb64120d39"
    )


def test_normalize_codex_exports_context_and_explicit_abort() -> None:
    """A session keeps the recorded actor, model, effort, and abort status."""
    records = [
        (
            1,
            {
                "type": "session_meta",
                "payload": {"id": "sid", "cwd": ROOTS[0], "parent_thread_id": "parent"},
            },
        ),
        (
            2,
            {
                "type": "turn_context",
                "payload": {"turn_id": "turn", "model": "model", "effort": "high"},
            },
        ),
        (
            3,
            {
                "timestamp": "2026-09-26T04:00:00Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "call_id": "cid",
                    "name": "tool",
                    "status": "running",
                },
            },
        ),
        (
            4,
            {
                "timestamp": "2026-09-26T04:00:01Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "cid",
                    "output": "ok",
                },
            },
        ),
        (
            5,
            {
                "timestamp": "2026-09-26T04:00:02Z",
                "type": "event_msg",
                "payload": {"type": "turn_aborted", "turn_id": "turn"},
            },
        ),
    ]
    rows = rules["normalize_codex"](records, KEY, "S1", ROOTS)
    assert [row["kind"] for row in rows] == ["call", "output", "wait", "failure"]
    assert [row["position"] for row in rows] == ["3", "4", "4", "5"]
    assert all(
        row["actor"] == "child agent"
        and row["model"] == "model"
        and row["effort"] == "high"
        for row in rows
    )
    assert (
        rows[0]["tool"],
        rows[0]["status"],
        rows[1]["output_bytes"],
        rows[2]["duration_ms"],
        rows[3]["status"],
    ) == ("tool", "running", "2", "1000", "aborted")


@pytest.mark.integration
def test_private_map_cannot_resolve_inside_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject relative, root-level, and symlink paths before writing."""
    from agent_orchestration_poc.shell.analysis.transcript_retro import (  # noqa: PLC0415 - mutmut copies only core source
        private_map_destination,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    original = tmp_path / "original"
    original.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = repo / "private-map.csv"
    link = outside / "linked-map.csv"
    link.symlink_to(target)
    monkeypatch.chdir(repo)
    for candidate in (Path("private-map.csv"), target, link, original / "map.csv"):
        with pytest.raises(ValueError, match="outside the repository"):
            private_map_destination(candidate, repo, original)
    assert (
        private_map_destination(outside / "safe.csv", repo, original)
        == outside / "safe.csv"
    )


def test_cross_midnight_wait_uses_prior_call() -> None:
    """An in-day output retains elapsed time from a prior-day call."""
    records, _ = rules["parse_jsonl"](
        [
            '{"timestamp":"2026-09-26T03:59:57Z","type":"session_meta","payload":{"id":"sid","cwd":"/synthetic/agent-orchestration-poc"}}',
            '{"timestamp":"2026-09-26T03:59:58Z","type":"response_item","payload":{"type":"function_call","call_id":"cid","name":"tool"}}',
            '{"timestamp":"2026-09-26T04:00:01Z","type":"response_item","payload":{"type":"function_call_output","call_id":"cid","output":"ok"}}',
        ]
    )
    rows = rules["normalize_codex"](records, KEY, "S1", ROOTS)
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
