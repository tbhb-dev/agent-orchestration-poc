"""Temporary #176 identity decisions; #28 replaces this scaffold."""

from typing import Any


def reservation(rows: list[dict[str, Any]], request: dict[str, Any]) -> str:
    """Choose create, inspect, or reject from recorded ownership values."""
    owned = ("name", "branch", "worktree", "tmux_name")
    matches = [row for row in rows if any(row[key] == request[key] for key in owned)]
    if not matches:
        return "create"
    if len(matches) == 1 and all(
        matches[0].get(key) == value
        for key, value in request.items()
        if key != "brief_file"
    ):
        return "inspect"
    return "duplicate ownership"


def codex_candidate(
    rollouts: list[dict[str, Any]], worktree: str, open_files: list[str]
) -> str | None:
    """Accept only a rollout held open by the exact tmux process in this cwd."""
    matches = [
        row["id"]
        for row in rollouts
        if row.get("cwd") == worktree and row.get("path") in open_files
    ]
    return matches[0] if len(matches) == 1 else None


def claude_candidate(
    entries: list[dict[str, Any]], observation: dict[str, Any]
) -> dict[str, Any] | None:
    """Match a live registry entry to process, start, pane, and cwd."""
    matches = [
        entry
        for entry in entries
        if entry.get("pid") == observation.get("pid")
        and entry.get("procStart")
        == observation.get("process_start_utc", observation.get("process_start"))
        and entry.get("tmux") == observation.get("tmux_target")
        and entry.get("cwd") == observation.get("worktree")
        and entry.get("entrypoint") == "cli"
        and entry.get("kind") == "interactive"
    ]
    return matches[0] if len(matches) == 1 else None


def readiness(record: dict[str, Any], seen: dict[str, Any]) -> tuple[str, str]:
    """Fail closed on stale generations, identities, and absent brief uptake."""
    if seen.get("trust_prompt"):
        return "blocked", "folder trust prompt"
    stale = next(
        (
            key
            for key in ("tmux_session", "tmux_window", "tmux_pane", "pane_generation")
            if not seen.get(key) or seen[key] != record.get(key)
        ),
        None,
    )
    if stale:
        return "unknown", f"stale tmux {stale}"
    stale = next(
        (
            key
            for key in ("pid", "process_start")
            if not seen.get(key) or seen[key] != record.get(key)
        ),
        None,
    )
    if stale:
        return "unknown", f"stale process {stale}"
    if record["harness"] == "agy":
        return "blocked", "external send path unverified"
    checks = (
        (
            not seen.get("native_id") or seen["native_id"] != record.get("native_id"),
            "native identity mismatch",
        ),
        (seen.get("endpoint") != record.get("endpoint"), "runtime endpoint mismatch"),
        (not seen.get("loaded"), "recipient unloaded"),
        (not seen.get("brief_uptake"), "first brief uptake unconfirmed"),
    )
    failed = next((reason for condition, reason in checks if condition), None)
    if failed:
        return "unknown", failed
    return (
        "busy" if seen.get("busy") else "ready"
    ), "native identity and brief confirmed"
