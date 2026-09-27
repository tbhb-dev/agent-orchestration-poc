"""Pure construction and validation of local check timing records."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath

NON_MECHANICAL = frozenset(
    {
        "check",
        "fmt",
        "docs:dev",
        "review:preflight",
        "pr:wait-check",
        "checkpoint:closure-audit",
    }
)


def child_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Restore the command's Python path after the wrapper imports its module."""
    child = dict(environment)
    was_set = child.pop("CHECK_TIMING_PYTHONPATH_WAS_SET", None)
    original = child.pop("CHECK_TIMING_PARENT_PYTHONPATH", "")
    if was_set == "1":
        child["PYTHONPATH"] = original
    elif was_set == "0":
        child.pop("PYTHONPATH", None)
    return child


@dataclass(frozen=True)
class TimingContext:
    """Metadata collected at the command boundary."""

    commit_sha: str | None
    branch: str | None
    origin: str
    actor: str | None
    host: str


@dataclass(frozen=True)
class TimingRecord:
    """Fields allowed in the local SQLite store."""

    name: str
    started_at: str
    duration_ns: int
    exit_status: int
    commit_sha: str | None
    branch: str | None
    origin: str
    actor: str | None
    host: str


def main_clone_from_common_dir(common_dir: str) -> PurePath:
    """Locate the main clone from git's absolute common directory."""
    path = PurePath(common_dir)
    if not path.is_absolute() or path.name != ".git":
        raise ValueError("expected the main clone's absolute .git directory")
    return path.parent


def parse_git_snapshot(output: str) -> tuple[PurePath, str, str | None]:
    """Parse one git rev-parse call for the main clone, commit, and branch."""
    lines = output.splitlines()
    if len(lines) != 3 or len(lines[1]) != 40:
        raise ValueError("invalid git snapshot")
    root = main_clone_from_common_dir(lines[0])
    branch = None if lines[2] == "HEAD" else lines[2]
    return root, lines[1], branch


def origin_and_actor(
    github_actions: str | None, explicit_actor: str | None, github_actor: str | None
) -> tuple[str, str | None]:
    """Derive only a known actor and an explicit CI origin."""
    return (
        "ci" if github_actions == "true" else "local",
        explicit_actor or github_actor or None,
    )


def builtin_config(hook_id: str) -> str:
    """Build a one-hook prek configuration for an existing pinned builtin."""
    if hook_id not in (
        "trailing-whitespace",
        "end-of-file-fixer",
        "check-added-large-files",
    ):
        raise ValueError("unsupported builtin hook")
    return f'[[repos]]\nrepo = "builtin"\nhooks = [{{ id = "{hook_id}" }}]\n'


def make_record(
    name: str,
    started_at: str,
    duration_ns: int,
    exit_status: int,
    context: TimingContext,
) -> TimingRecord:
    """Validate and normalize safe timing fields without reading process state."""
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError as error:
        raise ValueError("invalid UTC start timestamp") from error
    offset = started.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ValueError("start timestamp must be UTC")
    if not name or duration_ns < 0 or exit_status < 0 or not context.host:
        raise ValueError("invalid timing field")
    if context.origin not in ("local", "ci"):
        raise ValueError("invalid timing origin")
    return TimingRecord(
        name=name,
        started_at=started.astimezone(UTC).isoformat(),
        duration_ns=duration_ns,
        exit_status=exit_status,
        commit_sha=context.commit_sha or None,
        branch=context.branch or None,
        origin=context.origin,
        actor=context.actor or None,
        host=context.host,
    )


def inventory_missing(
    tasks: Mapping[str, str | None],
    hooks: Mapping[str, str],
    recorded: Sequence[str],
) -> tuple[str, ...]:
    """Find configured checks with no wrapper or stored invocation."""
    records = set(recorded)
    missing = []
    for name, run in tasks.items():
        if name in NON_MECHANICAL or name.startswith("check-timings:") or run is None:
            continue
        key = f"task:{name}"
        if f"record-check.sh {key} --" not in run or key not in records:
            missing.append(key)
    for name, entry in hooks.items():
        key = f"hook:{name}"
        if f"record-check.sh {key} --" not in entry or key not in records:
            missing.append(key)
    return tuple(sorted(missing))
