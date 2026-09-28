"""Pure decisions for the disposable host lifecycle observer."""

from dataclasses import dataclass

PROFILES = (
    "codex-interactive",
    "codex-headless",
    "claude-interactive",
    "claude-headless",
)


@dataclass(frozen=True)
class Record:
    """Identity saved before a controller observer exits."""

    profile: str
    workload_id: str
    incarnation: str
    conversation_id: str | None
    pid: int
    process_start: str


def validate(record: Record) -> bool:
    """Reject missing or ambiguous identities before observing a process."""
    return (
        record.profile in PROFILES
        and bool(record.workload_id)
        and bool(record.incarnation)
        and record.pid > 0
        and bool(record.process_start)
        and (record.conversation_id is None or bool(record.conversation_id))
    )


def process_state(record: Record, current_start: str | None) -> str:
    """Classify a process instance without equating a reused PID with the root."""
    if current_start is None:
        return "absent"
    if current_start != record.process_start:
        return "different-incarnation"
    return "live"


def process_start_from_query(returncode: int, stdout: str, stderr: str) -> str | None:
    """Distinguish a missing PID from an unsuccessful process-table query."""
    if returncode == 0 and stdout.strip():
        return stdout.strip()
    if returncode == 1 and not stdout.strip() and not stderr.strip():
        return None
    raise ValueError(f"ps exited {returncode}: {stderr.strip() or stdout.strip()}")


def retained_state(before: dict[str, str], after: dict[str, str]) -> str:
    """Compare private-state fingerprints without inspecting their contents."""
    if not before:
        return "no-baseline"
    if before.items() <= after.items():
        return "retained"
    return "changed-or-missing"
