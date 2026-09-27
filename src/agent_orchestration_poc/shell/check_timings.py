"""Run checks unchanged and append their safe timing metadata to SQLite."""

import os
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from agent_orchestration_poc.core.check_timings import (
    TimingContext,
    TimingRecord,
    builtin_config,
    child_environment,
    main_clone_from_common_dir,
    make_record,
    origin_and_actor,
    parse_git_snapshot,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS local_checks (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    duration_ns INTEGER NOT NULL CHECK (duration_ns >= 0),
    exit_status INTEGER NOT NULL,
    commit_sha TEXT,
    branch TEXT,
    origin TEXT NOT NULL,
    actor TEXT,
    host TEXT NOT NULL
)
"""


def store_path() -> Path:
    """Return the ignored store in the main clone or reject an unsafe location."""
    result = subprocess.run(
        ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("git common directory unavailable")
    root = Path(main_clone_from_common_dir(result.stdout.strip()))
    relative = ".local-cache/check-timings/timings.sqlite3"
    ignored = subprocess.run(
        ("git", "-C", str(root), "check-ignore", "-q", relative), check=False
    )
    if ignored.returncode != 0:
        raise ValueError("timing store is not ignored")
    return root / relative


def _snapshot() -> tuple[Path, TimingContext]:
    result = subprocess.run(
        (
            "git",
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
            "HEAD",
            "--abbrev-ref",
            "HEAD",
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("git snapshot unavailable")
    root, commit_sha, branch = parse_git_snapshot(result.stdout)
    origin, actor = origin_and_actor(
        os.environ.get("GITHUB_ACTIONS"),
        os.environ.get("CHECK_TIMING_ACTOR"),
        os.environ.get("GITHUB_ACTOR"),
    )
    return Path(root), TimingContext(
        commit_sha, branch, origin, actor, socket.gethostname()
    )


def append_record(path: Path, record: TimingRecord) -> None:
    """Append one record with a short SQLite transaction."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=2)) as connection, connection:
        connection.execute(SCHEMA)
        connection.execute(
            """INSERT INTO local_checks
            (name, started_at, duration_ns, exit_status, commit_sha, branch, origin, actor, host)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.name,
                record.started_at,
                record.duration_ns,
                record.exit_status,
                record.commit_sha,
                record.branch,
                record.origin,
                record.actor,
                record.host,
            ),
        )


def run_recorded(name: str, argv: Sequence[str]) -> int:
    """Preserve command streams and status even if timing storage fails."""
    started_at = datetime.now(tz=UTC).isoformat()
    start_ns = time.monotonic_ns()
    child = subprocess.Popen(argv, env=child_environment(os.environ))
    try:
        status = child.wait()
    except KeyboardInterrupt:
        child.send_signal(signal.SIGINT)
        status = child.wait()
    duration_ns = time.monotonic_ns() - start_ns
    exit_status = 128 - status if status < 0 else status
    try:
        root, context = _snapshot()
        record = make_record(name, started_at, duration_ns, exit_status, context)
        append_record(root / ".local-cache/check-timings/timings.sqlite3", record)
    except OSError, sqlite3.Error, ValueError:
        pass
    return exit_status


def main() -> int:
    """Invoke the named check after a literal -- separator."""
    if len(sys.argv) < 4 or sys.argv[2] != "--":
        sys.stderr.write("usage: record-check NAME -- COMMAND [ARG ...]\n")
        return 2
    if sys.argv[3] == "__builtin__":
        if len(sys.argv) < 5:
            return 2
        hook_id = sys.argv[4]
        with tempfile.TemporaryDirectory(prefix="check-timing-hook-") as temporary:
            config = Path(temporary) / "prek.toml"
            config.write_text(builtin_config(hook_id))
            return run_recorded(
                sys.argv[1],
                (
                    "prek",
                    "run",
                    hook_id,
                    "--config",
                    str(config),
                    "--files",
                    *sys.argv[5:],
                ),
            )
    return run_recorded(sys.argv[1], sys.argv[3:])


if __name__ == "__main__":
    raise SystemExit(main())
