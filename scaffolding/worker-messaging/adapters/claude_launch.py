"""Temporary #176 Claude observation adapter; #28 replaces this scaffold."""

import json
from pathlib import Path
from typing import Any

import identity


def live_entries() -> list[dict[str, Any]]:
    """Read Claude's live registry without exposing peer credentials."""
    root = Path.home() / ".claude/sessions"
    return [json.loads(path.read_text()) for path in root.glob("*.json")]


def brief_uptake(session_id: str, worktree: str, digest: str) -> bool:
    """Confirm that the exact first prompt entered the live session history."""
    root = Path.home() / ".claude/projects"
    paths = root.glob(f"**/{session_id}.jsonl")
    for path in paths:
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        if identity.claude_brief_uptake(rows, session_id, worktree, digest):
            return True
    return False
