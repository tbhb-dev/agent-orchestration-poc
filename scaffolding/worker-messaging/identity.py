"""Temporary #176 identity decisions; #28 replaces this scaffold."""

import hashlib
import json
import shlex
from datetime import datetime
from pathlib import Path
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


def codex_brief_digest(brief: str) -> str:
    """Hash the preview text exposed by Codex for the startup message."""
    marker = "## My request for Codex:"
    preview = brief.split(marker, 1)[1] if marker in brief else brief
    return hashlib.sha256(preview.strip().encode()).hexdigest()


def codex_candidate(threads: list[dict[str, Any]], row: dict[str, Any]) -> str | None:
    """Identify one remote startup by worktree, launch time, and first brief."""
    launched = int(datetime.fromisoformat(row["launch_time"]).timestamp())
    matches = [
        thread["id"]
        for thread in threads
        if isinstance(thread.get("id"), str)
        and thread.get("cwd") == row["worktree"]
        and isinstance(thread.get("createdAt"), int)
        and thread["createdAt"] >= launched
        and isinstance(thread.get("preview"), str)
        and hashlib.sha256(thread["preview"].encode()).hexdigest()
        == row["brief_digest"]
        and (not row.get("native_id") or thread["id"] == row["native_id"])
    ]
    return matches[0] if len(matches) == 1 else None


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


def missing_tmux_target(stderr: str) -> bool:
    """Recognize tmux's missing pane, window, session, or server replies."""
    return any(
        marker in stderr
        for marker in (
            "can't find pane:",
            "can't find window:",
            "can't find session:",
            "no server running",
            "No such file or directory",
        )
    )


def tmux_pane_fields(stdout: str) -> tuple[str, str, str, str] | None:
    """Treat tmux's empty successful display as an absent target."""
    fields = stdout.strip().split("|")
    if len(fields) != 4 or not all(fields) or not fields[3].isdecimal():
        return None
    return fields[0], fields[1], fields[2], fields[3]


def common_git_root(expected: str, reported: list[str]) -> bool:
    """Require the server's thread roots to include the common Git directory."""
    return expected in reported


def codex_runtime_facts(
    found: str, row: dict[str, Any], loaded: bool, thread: dict[str, Any]
) -> dict[str, bool]:
    """Require loaded inventory and matching runtime identity and configuration."""
    status = thread.get("status")
    return {
        "loaded": loaded
        and thread.get("id") == found
        and thread.get("cwd") == row["worktree"]
        and thread.get("model") == row["model"]
        and thread.get("reasoningEffort") == row["effort"]
        and isinstance(status, dict)
        and status.get("type") in {"idle", "active"},
        "busy": codex_busy(thread),
    }


def codex_endpoint(endpoint: str | None) -> str:
    """Require a recorded absolute Unix socket address for remote Codex."""
    if not endpoint or not endpoint.startswith("unix:///"):
        raise ValueError("Codex requires an explicit absolute unix:// endpoint")
    path = endpoint.removeprefix("unix://")
    if "\x00" in path or path == "/" or "//" in path or "/../" in f"{path}/":
        raise ValueError("invalid Codex Unix endpoint")
    return path


def trust_target(worktree: str, root: str, created: bool) -> str:
    """Limit a trust edit to a newly created, direct child worktree."""
    path = Path(worktree)
    if (
        not created
        or not path.is_absolute()
        or path.parent != Path(root) / ".worktrees"
    ):
        raise ValueError("trust target is not a launcher-created worktree")
    return str(path)


def trust_write_params(worktree: str, value: str | None) -> dict[str, Any]:
    """Match the tagged TUI's replace edit for one quoted project key."""
    if value not in {"trusted", None}:
        raise ValueError("invalid trust value")
    return {
        "edits": [
            {
                "keyPath": f"projects.{json.dumps(worktree, ensure_ascii=False)}.trust_level",
                "value": value,
                "mergeStrategy": "replace",
            }
        ],
        "filePath": None,
        "expectedVersion": None,
        "reloadUserConfig": True,
    }


def trust_write_confirmed(response: dict[str, Any]) -> bool:
    """Accept only an unoverridden user-config write result."""
    return response.get("status") == "ok"


def trust_readback(response: dict[str, Any], worktree: str, value: str | None) -> bool:
    """Require the exact project key in a layered config read."""
    if not isinstance(response.get("layers"), list):
        return False
    config = response.get("config")
    if not isinstance(config, dict):
        return False
    projects = config.get("projects")
    if projects is not None and not isinstance(projects, dict):
        return False
    entry = projects.get(worktree) if isinstance(projects, dict) else None
    if value is None:
        return entry is None or isinstance(entry, dict) and "trust_level" not in entry
    return isinstance(entry, dict) and entry.get("trust_level") == value


def trust_gate(row: dict[str, Any]) -> tuple[str, str] | None:
    """Keep failed trust operations and completed cleanup ineligible for sends."""
    if row.get("trust_blocked"):
        return "blocked", row["reason"]
    if row.get("trust_registered") is False:
        return "blocked", "folder trust removed"
    return None


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


def command(row: dict[str, Any], brief: str, shim: str, path_env: str) -> str:
    """Build a harness command from captured values without reading the host."""
    if row["harness"] == "codex":
        codex_endpoint(row.get("endpoint"))
        argv = [
            "codex",
            "--remote",
            row["endpoint"],
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
    stale = (
        "target"
        if seen.get("tmux_missing")
        else next(
            (
                key
                for key in (
                    "tmux_session",
                    "tmux_window",
                    "tmux_pane",
                    "pane_generation",
                )
                if not seen.get(key) or seen[key] != record.get(key)
            ),
            None,
        )
    )
    if stale:
        return "unknown", (
            "missing tmux target" if stale == "target" else f"stale tmux {stale}"
        )
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
    if seen.get("trust_prompt"):
        return "blocked", "folder trust prompt"
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
        (
            record["harness"] == "codex" and not seen.get("roots_confirmed"),
            "common Git workspace root unconfirmed",
        ),
    )
    failed = next((reason for condition, reason in checks if condition), None)
    if failed:
        return "unknown", failed
    return (
        "busy" if seen.get("busy") else "ready"
    ), "native identity and brief confirmed"


def status_view(
    row: dict[str, Any], record: dict[str, Any] | None, source: str, now: str
) -> dict[str, Any]:
    """Classify a captured status record without changing native readiness."""
    result: dict[str, Any] = {
        "record": None,
        "source": source,
        "age_seconds": None,
        "availability": "missing" if record is None else "invalid",
    }
    if record is None:
        return result
    if record.get("run_id") != row["run_id"] or record.get("generation") != row.get(
        "pane_generation"
    ):
        return result
    try:
        age = (
            datetime.fromisoformat(now)
            - datetime.fromisoformat(record["last_seen_utc"])
        ).total_seconds()
    except KeyError, TypeError, ValueError:
        return result
    if age < 0:
        return result
    result.update(
        record=record, age_seconds=age, availability="fresh" if age <= 120 else "stale"
    )
    return result
