"""Temporary #176 coordinator CLI; #28 replaces this scaffold."""

import argparse
import fcntl
import json
import re
import subprocess
import sys
from pathlib import Path

import launcher


def parser() -> argparse.ArgumentParser:
    """Build the temporary coordinator command parser."""
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)
    launch = commands.add_parser("launch")
    for key in [
        "name",
        "issue",
        "harness",
        "model",
        "effort",
        "branch",
        "worktree",
        "brief-file",
    ]:
        launch.add_argument(f"--{key}", required=True)
    launch.add_argument("--endpoint")
    commands.add_parser("status").add_argument("run_id")
    commands.add_parser("readiness").add_argument("run_id")
    return result


def main() -> int:
    """Report one machine-readable readiness result without exposing the brief."""
    args = parser().parse_args()
    try:
        launcher.STORE.parent.mkdir(parents=True, exist_ok=True)
        with (launcher.STORE.parent / "registry.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            row, state, reason = _dispatch(args)
            status = launcher.status_record(row) if args.command == "status" else None
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.stdout.write(json.dumps({"state": "unknown", "reason": str(error)}) + "\n")
        return 3
    output = {
        "run_id": row["run_id"],
        "state": state,
        "reason": reason,
        "endpoint": row.get("endpoint"),
        "observed_at": row.get("observed_at"),
    }
    if status is not None:
        output["readiness"] = {
            key: output[key] for key in ("state", "reason", "endpoint", "observed_at")
        }
        output["status"] = status
    sys.stdout.write(json.dumps(output) + "\n")
    return {"ready": 0, "busy": 0, "blocked": 2, "unknown": 3}[state]


def _dispatch(args: argparse.Namespace) -> tuple[dict[str, object], str, str]:
    """Dispatch a locked operation."""
    if args.command == "launch":
        if not re.fullmatch(r"[a-z][a-z0-9-]*", args.name):
            raise ValueError("name must be lowercase letters, numbers, and hyphens")
        if args.harness not in {"codex", "claude", "agy"}:
            raise ValueError("unsupported harness")
        if not args.issue.isdecimal() or int(args.issue) < 1:
            raise ValueError("issue must be a positive number")
        request = {
            "name": args.name,
            "issue": int(args.issue),
            "harness": args.harness,
            "model": args.model,
            "effort": args.effort,
            "branch": args.branch,
            "worktree": str(Path(args.worktree).resolve()),
            "brief_file": str(Path(args.brief_file).resolve()),
            "endpoint": args.endpoint,
            "tmux_name": args.name,
        }
        return launcher.launch(request)
    return launcher.status(args.run_id)


if __name__ == "__main__":
    sys.exit(main())
