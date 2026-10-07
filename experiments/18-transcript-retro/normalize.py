"""Pure normalization rules for the private session inventory."""

import hmac
import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

__all__ = [
    "EVENT_FIELDS",
    "deduplicate",
    "normalize_codex",
    "opaque",
    "parse_jsonl",
    "record_range",
    "session_actor",
    "session_details",
    "source_type",
    "validate_export",
]

DAY_START = datetime(2026, 9, 26, 4, tzinfo=UTC)
DAY_END = datetime(2026, 9, 27, 4, tzinfo=UTC)
REPO = "agent-orchestration-poc"
EVENT_FIELDS = (
    "event_id",
    "source_id",
    "position",
    "timestamp_utc",
    "actor",
    "harness",
    "kind",
    "turn_id",
    "tool",
    "status",
    "output_bytes",
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "model",
    "effort",
)


@dataclass(frozen=True)
class Context:
    """Private native identity and the current turn's public attributes."""

    key: bytes
    source_id: str
    session_id: str
    actor: str = "worker"
    turn: str | None = None
    model: str | None = None
    effort: str | None = None


def opaque(key: bytes, *parts: str) -> str:
    """Produce a stable, keyed ID without exporting native identifiers."""
    value = json.dumps(parts, separators=(",", ":"), ensure_ascii=False).encode()
    return hmac.new(key, value, sha256).hexdigest()[:24]


def utc_time(value: object) -> datetime | None:
    """Parse an explicit ISO timestamp and reject missing time zones."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else None


def in_day(value: datetime | None) -> bool:
    """Select events by local-day UTC bounds, including crossing sessions."""
    return value is not None and DAY_START <= value < DAY_END


def source_type(relative: str) -> str:
    """Classify a snapshot member without looking at its contents."""
    if relative.startswith("codex-sessions/") and relative.endswith(".jsonl"):
        return "codex-native"
    if relative.startswith("claude-code/") and relative.endswith(".jsonl"):
        return "claude-native"
    if relative.startswith("codex-runs/"):
        return "captured-run"
    if relative.startswith("webhooks/"):
        return "webhook"
    return "unknown"


def parse_jsonl(lines: list[str]) -> tuple[list[tuple[int, dict[str, Any]]], int]:
    """Parse records and count malformed or non-object lines."""
    records: list[tuple[int, dict[str, Any]]] = []
    bad = 0
    for position, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(record, dict):
            records.append((position, record))
        else:
            bad += 1
    return records, bad


def session_details(
    records: list[tuple[int, dict[str, Any]]],
) -> tuple[str | None, bool, str, str]:
    """Extract Codex session identity, repository membership, model, and effort."""
    session_id = None
    member = False
    models: set[str] = set()
    efforts: set[str] = set()
    for _, record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        if record.get("type") == "session_meta":
            session_id = payload.get("id") or payload.get("session_id")
        if record.get("type") in {"session_meta", "turn_context"}:
            cwd = payload.get("cwd")
            member |= isinstance(cwd, str) and REPO in cwd
        if record.get("type") == "turn_context":
            if isinstance(payload.get("model"), str):
                models.add(payload["model"])
            if isinstance(payload.get("effort"), str):
                efforts.add(payload["effort"])
    return session_id, member, ",".join(sorted(models)), ",".join(sorted(efforts))


def session_actor(records: list[tuple[int, dict[str, Any]]]) -> str:
    """Use the native parent link to distinguish child agents from workers."""
    for _, record in records:
        if record.get("type") == "session_meta":
            payload = record.get("payload")
            if isinstance(payload, dict) and isinstance(
                payload.get("parent_thread_id"), str
            ):
                return "child agent"
    return "worker"


def record_range(records: list[tuple[int, dict[str, Any]]]) -> tuple[str, str, int]:
    """Report explicit record times and the unknown-time count."""
    times = [utc_time(record.get("timestamp")) for _, record in records]
    known = [stamp for stamp in times if stamp is not None]
    if not known:
        return "", "", len(times)
    return min(known).isoformat(), max(known).isoformat(), len(times) - len(known)


def event(
    context: Context,
    position: int,
    timestamp: datetime,
    kind: str,
    native_id: str,
    **attributes: object,
) -> dict[str, str]:
    """Build one safe exported row from native identifiers and numeric attributes."""
    row = dict.fromkeys(EVENT_FIELDS, "")
    row.update(
        event_id=opaque(
            context.key, context.session_id, context.turn or "", native_id, kind
        ),
        source_id=context.source_id,
        position=str(position),
        timestamp_utc=timestamp.isoformat(),
        actor=context.actor,
        harness="codex",
        kind=kind,
        turn_id=opaque(context.key, context.session_id, context.turn)
        if context.turn
        else "",
        model=context.model or "",
        effort=context.effort or "",
    )
    for name, value in attributes.items():
        if name not in EVENT_FIELDS:
            raise ValueError(f"unsupported export field: {name}")
        row[name] = "" if value is None else str(value)
    return row


def fallback_id(
    context: Context, stamp: datetime, tool: str, payload: dict[str, Any]
) -> str:
    """Key a missing native ID from time, actor, tool, and canonical payload digest."""
    normalized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    digest = opaque(context.key, "payload", normalized)
    return opaque(context.key, stamp.isoformat(), context.actor, tool, digest)


def response_events(
    context: Context,
    position: int,
    stamp: datetime,
    payload: dict[str, Any],
    calls: dict[str, tuple[datetime, Context]],
) -> tuple[list[dict[str, str]], dict[str, tuple[datetime, Context]]]:
    """Normalize one call or output and its elapsed call-to-output wait."""
    item_type = payload.get("type")
    if item_type not in {
        "custom_tool_call",
        "function_call",
        "custom_tool_call_output",
        "function_call_output",
    }:
        return [], calls
    updated = dict(calls)
    tool = payload.get("name") if isinstance(payload.get("name"), str) else ""
    call_id = payload.get("call_id")
    if not isinstance(call_id, str):
        call_id = fallback_id(context, stamp, tool, payload)
    if item_type in {"custom_tool_call", "function_call"}:
        updated[call_id] = stamp, context
        return [
            event(
                context,
                position,
                stamp,
                "call",
                call_id,
                tool=tool,
                status=payload.get("status"),
            )
        ], updated
    output = payload.get("output")
    size = len(output.encode()) if isinstance(output, str) else None
    rows = [
        event(context, position, stamp, "output", call_id, tool=tool, output_bytes=size)
    ]
    if call_id in updated:
        start, call_context = updated.pop(call_id)
        if stamp >= start:
            rows.append(
                event(
                    call_context,
                    position,
                    stamp,
                    "wait",
                    call_id,
                    tool=tool,
                    duration_ms=int((stamp - start).total_seconds() * 1000),
                )
            )
    return rows, updated


def usage_event(
    context: Context, position: int, stamp: datetime, payload: dict[str, Any]
) -> dict[str, str] | None:
    """Use response-level usage, leaving absent token fields blank."""
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    native_id = payload.get("response_id")
    if not isinstance(native_id, str):
        native_id = fallback_id(context, stamp, "token", payload)
    return event(
        context,
        position,
        stamp,
        "token",
        native_id,
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        total_tokens=usage.get("total_tokens"),
    )


def abort_event(
    context: Context, position: int, stamp: datetime, payload: dict[str, Any]
) -> dict[str, str] | None:
    """Export only an explicit turn abort with a native turn ID."""
    native_id = payload.get("turn_id")
    if not isinstance(native_id, str):
        return None
    return event(
        replace(context, turn=native_id),
        position,
        stamp,
        "failure",
        native_id,
        status="aborted",
    )


def other_event(
    context: Context,
    position: int,
    stamp: datetime,
    kind: object,
    payload: dict[str, Any],
) -> dict[str, str] | None:
    """Handle native usage records and explicit turn aborts."""
    if kind == "token_usage_record":
        return usage_event(context, position, stamp, payload)
    if kind == "event_msg" and payload.get("type") == "turn_aborted":
        return abort_event(context, position, stamp, payload)
    return None


def normalize_codex(
    records: list[tuple[int, dict[str, Any]]], key: bytes, source_id: str
) -> list[dict[str, str]]:
    """Extract Codex calls, outputs, explicit failures, usage, and tool waits."""
    session_id, member, _, _ = session_details(records)
    if not member or not isinstance(session_id, str):
        return []
    rows: list[dict[str, str]] = []
    calls: dict[str, tuple[datetime, Context]] = {}
    context = Context(key, source_id, session_id, session_actor(records))
    for position, record in records:
        stamp = utc_time(record.get("timestamp"))
        kind = record.get("type")
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        if kind == "turn_context":
            context = replace(
                context,
                turn=payload.get("turn_id")
                if isinstance(payload.get("turn_id"), str)
                else None,
                model=payload.get("model")
                if isinstance(payload.get("model"), str)
                else None,
                effort=payload.get("effort")
                if isinstance(payload.get("effort"), str)
                else None,
            )
            continue
        if stamp is None:
            continue
        if kind == "response_item":
            response, calls = response_events(context, position, stamp, payload, calls)
            if in_day(stamp):
                rows.extend(response)
            continue
        if in_day(stamp):
            other = other_event(context, position, stamp, kind, payload)
            if other is not None:
                rows.append(other)
    return rows


def deduplicate(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int, int]:
    """Keep the first native event and count repeated and conflicting keys."""
    unique: dict[str, dict[str, str]] = {}
    duplicate = 0
    ambiguous = 0
    for row in rows:
        event_id = row["event_id"]
        if event_id in unique:
            duplicate += 1
            comparable = (
                "kind",
                "timestamp_utc",
                "tool",
                "status",
                "output_bytes",
                "duration_ms",
                "input_tokens",
                "output_tokens",
                "total_tokens",
            )
            ambiguous += any(
                unique[event_id][field] != row[field] for field in comparable
            )
        else:
            unique[event_id] = row
    return list(unique.values()), duplicate, ambiguous


def validate_export(rows: list[dict[str, str]]) -> None:
    """Reject unexpected columns, raw records, and synthetic secret signatures."""
    for row in rows:
        if set(row) != set(EVENT_FIELDS):
            raise ValueError("event schema contains a raw or missing field")
        serialized = json.dumps(row)
        if re.search(r"ghp_[A-Za-z0-9]{36}\b", serialized) or re.search(
            r'(?i)"(?:prompt|transcript|private_prompt)"\s*:', serialized
        ):
            raise ValueError("private content in event row")
