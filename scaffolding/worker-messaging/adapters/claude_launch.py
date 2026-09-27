"""Temporary #176 Claude observation adapter; #28 replaces this scaffold."""

import hashlib
import json
from pathlib import Path
from typing import Any


def live_entries() -> list[dict[str, Any]]:
    """Read Claude's live registry without exposing peer credentials."""
    root = Path.home() / ".claude/sessions"
    return [json.loads(path.read_text()) for path in root.glob("*.json")]


def brief_uptake(session_id: str, worktree: str, digest: str) -> bool:
    """Confirm that the exact first prompt entered the live session history."""
    root = Path.home() / ".claude/projects"
    paths = root.glob(f"**/{session_id}.jsonl")
    for path in paths:
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("sessionId") != session_id or row.get("cwd") != worktree:
                continue
            if row.get("type") == "user":
                content = row.get("message", {}).get("content")
                if (
                    isinstance(content, str)
                    and hashlib.sha256(content.encode()).hexdigest() == digest
                ):
                    return True
    return False
