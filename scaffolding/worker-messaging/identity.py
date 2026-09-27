"""Temporary #176 identity decisions; #28 replaces this scaffold."""

import hashlib
import shlex
from typing import Any


def reservation(rows: list[dict[str, Any]], request: dict[str, Any]) -> str:
    """Choose create, inspect, or reject from recorded ownership values."""
    if request["branch"] in {"main", "refs/heads/main"}:
        return "main branch is forbidden"
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


def codex_rollout(rows: list[dict[str, Any]], path: str) -> dict[str, Any]:
    """Interpret captured rollout rows without reading the transcript file."""
    meta = next((row["payload"] for row in rows if row["type"] == "session_meta"), {})
    prompts = [
        part["text"]
        for row in rows
        if row["type"] == "response_item" and row["payload"].get("role") == "user"
        for part in row["payload"].get("content", [])
        if part.get("type") == "input_text"
    ]
    return {
        "id": meta.get("id"),
        "cwd": meta.get("cwd"),
        "path": path,
        "brief_digests": [
            hashlib.sha256(prompt.encode()).hexdigest() for prompt in prompts
        ],
        "started": any(
            row["type"] == "event_msg" and row["payload"].get("type") == "task_started"
            for row in rows
        ),
    }


def claude_brief_uptake(
    rows: list[dict[str, Any]], session_id: str, worktree: str, digest: str
) -> bool:
    """Accept the exact first prompt in the identified Claude session and cwd."""
    for row in rows:
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


def loaded_ids(response: dict[str, Any]) -> set[str]:
    """Decode one Codex loaded inventory page of thread ID strings."""
    data = response.get("data")
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError("invalid loaded thread inventory")
    return set(data)


def codex_busy(thread: dict[str, Any]) -> bool:
    """Recognize the tagged Codex active thread status."""
    status = thread.get("status")
    return isinstance(status, dict) and status.get("type") == "active"


def trust_prompt(capture: str) -> bool:
    """Recognize the observed folder trust prompts."""
    lower = capture.lower()
    return "trust this folder" in lower or "trust this directory" in lower


def codex_facts(
    row: dict[str, Any], rollouts: list[dict[str, Any]], paths: list[str]
) -> dict[str, Any]:
    """Derive native identity and brief uptake from process-held rollouts."""
    found = codex_candidate(rollouts, row["worktree"], paths)
    match = next((item for item in rollouts if item.get("id") == found), {})
    return {
        "native_id": found,
        "brief_uptake": bool(match.get("started"))
        and row["brief_digest"] in match.get("brief_digests", []),
    }


def codex_runtime_facts(
    found: str, worktree: str, loaded: bool, thread: dict[str, Any]
) -> dict[str, bool]:
    """Require loaded inventory and the matching runtime thread and cwd."""
    status = thread.get("status")
    return {
        "loaded": loaded
        and thread.get("id") == found
        and thread.get("cwd") == worktree
        and isinstance(status, dict)
        and status.get("type") in {"idle", "active"},
        "busy": codex_busy(thread),
    }


def claude_facts(
    entries: list[dict[str, Any]], seen: dict[str, Any], worktree: str
) -> dict[str, Any]:
    """Correlate a live Claude entry without claiming external ListAgents access."""
    candidate = claude_candidate(entries, {**seen, "worktree": worktree})
    return {
        "native_id": candidate.get("sessionId") if candidate else None,
        "endpoint": candidate.get("messagingSocketPath") if candidate else None,
        "loaded": False,
        "busy": candidate.get("status") == "busy" if candidate else False,
    }


def worktree_action(
    path: str, branch: str, listings: str, exists: bool, owned: bool
) -> str:
    """Reject main and every unowned existing checkout."""
    if branch == "main" or branch == "refs/heads/main":
        return "reject"
    blocks = [
        dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        for block in listings.split("\n\n")
    ]
    matching = any(
        block.get("worktree") == path and block.get("branch") == f"refs/heads/{branch}"
        for block in blocks
    )
    if owned:
        return "inspect" if exists and matching else "reject"
    if exists:
        return "reject"
    if any(block.get("branch") == f"refs/heads/{branch}" for block in blocks):
        return "reject"
    return "create"


def window_names(code: int, stderr: str, stdout: str) -> list[str]:
    """Treat only tmux's absent server as an empty inventory."""
    if code == 0:
        return stdout.splitlines()
    if "no server running" in stderr or (
        "error connecting to" in stderr and "No such file or directory" in stderr
    ):
        return []
    raise ValueError("tmux window observation failed")


def session_missing(code: int, stderr: str) -> bool:
    """Distinguish a missing tmux session from a failed observation."""
    if code == 0:
        return False
    if (
        "no server running" in stderr
        or "can't find session:" in stderr
        or ("error connecting to" in stderr and "No such file or directory" in stderr)
    ):
        return True
    raise ValueError("tmux session observation failed")


def command(
    row: dict[str, Any], brief: str, shim: str, common_git: str, path_env: str
) -> str:
    """Build a harness command from captured values without reading the host."""
    if row["harness"] == "codex":
        argv = [
            "codex",
            "-m",
            row["model"],
            "-c",
            f'model_reasoning_effort="{row["effort"]}"',
            "-a",
            "never",
            "-s",
            "workspace-write",
            "-C",
            row["worktree"],
            "--add-dir",
            common_git,
            brief,
        ]
    elif row["harness"] == "claude":
        argv = [
            "claude",
            "--model",
            row["model"],
            "--effort",
            row["effort"],
            "--name",
            row["name"],
            brief,
        ]
    else:
        argv = ["agy", "--model", row["model"], "--effort", row["effort"], "-i", brief]
    env = {
        "PATH": f"{shim}:{path_env}",
        "ZDOTDIR": f"{shim}/zdotdir",
        "PREK_HOME": "/private/tmp/agent-orchestration-poc-prek",
        "GIT_AUTHOR_NAME": "tbhbagent",
        "GIT_AUTHOR_EMAIL": "agent@tonyburns.net",
        "GIT_COMMITTER_NAME": "tbhbagent",
        "GIT_COMMITTER_EMAIL": "agent@tonyburns.net",
    }
    return "exec " + shlex.join(
        ["env", *(f"{key}={value}" for key, value in env.items()), *argv]
    )


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
