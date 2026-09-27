"""Temporary #176 interactive worker shell; #28 replaces this scaffold."""

import hashlib
import os
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import identity
import registry
from adapters import claude_launch, codex_launch

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / ".local-cache/worker-messaging/registry.json"
SESSION = "worker-messaging"
CODEX_ENDPOINT = str(Path.home() / ".codex/app-server-control/app-server-control.sock")


def _run(argv: list[str]) -> str:
    return subprocess.run(
        argv, capture_output=True, text=True, check=True
    ).stdout.strip()


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _pane(pane: str) -> dict[str, Any]:
    line = _run(
        [
            "tmux",
            "display-message",
            "-p",
            "-t",
            pane,
            "#{session_name}|#{window_id}|#{pane_id}|#{pane_pid}",
        ]
    )
    session, window, pane_id, pid = line.split("|")
    try:
        started = _run(["ps", "-o", "lstart=", "-p", pid])
    except OSError, subprocess.CalledProcessError:
        started = ""
    utc_start = (
        datetime.strptime(started, "%a %b %d %H:%M:%S %Y")
        .replace(tzinfo=datetime.now().astimezone().tzinfo)
        .astimezone(UTC)
        .strftime("%a %b %d %H:%M:%S %Y")
        if started
        else ""
    )
    return {
        "tmux_session": session,
        "tmux_window": window,
        "tmux_pane": pane_id,
        "pane_generation": f"{pane_id}:{pid}:{started or 'unverified'}",
        "pid": int(pid),
        "process_start": started,
        "process_start_utc": utc_start,
        "tmux_target": f"{session}:{window}.{pane_id}",
    }


def _worktree(path: Path, branch: str, owned: bool) -> None:
    listings = _run(["git", "worktree", "list", "--porcelain"])
    action = identity.worktree_action(str(path), branch, listings, path.exists(), owned)
    if action == "inspect":
        return
    if action != "create":
        raise ValueError("worktree or branch is not available for this run")
    if _run(["git", "branch", "--list", branch]):
        raise ValueError("branch exists without requested worktree")
    path.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "worktree", "add", "-b", branch, str(path), "main"])


def _command(row: dict[str, Any], brief: str) -> str:
    common_git = Path(
        _run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"])
    )
    shim = common_git.parent / ".holding/shim"
    return identity.command(row, brief, str(shim), str(common_git), os.environ["PATH"])


def _new_pane(row: dict[str, Any], brief: str) -> dict[str, Any]:
    present = subprocess.run(
        ["tmux", "has-session", "-t", SESSION],
        capture_output=True,
        text=True,
        check=False,
    )
    if identity.session_missing(present.returncode, present.stderr):
        _run(["tmux", "new-session", "-d", "-s", SESSION, "-n", "control"])
    pane = _run(
        [
            "tmux",
            "new-window",
            "-d",
            "-P",
            "-F",
            "#{pane_id}",
            "-t",
            SESSION,
            "-n",
            row["name"],
            "-c",
            row["worktree"],
            _command(row, brief),
        ]
    )
    return _pane(pane)


def _observe(row: dict[str, Any]) -> dict[str, Any]:
    seen: dict[str, Any] = {"endpoint": row["endpoint"], "native_id": row["native_id"]}
    seen.update(_pane(row["tmux_pane"]))
    capture = _run(["tmux", "capture-pane", "-p", "-S", "-80", "-t", row["tmux_pane"]])
    seen["trust_prompt"] = identity.trust_prompt(capture)
    if seen["trust_prompt"] or not seen["process_start"]:
        return seen
    if row["harness"] == "codex":
        paths = codex_launch.open_rollouts(seen["pid"])
        rollouts = [codex_launch.rollout(path) for path in paths]
        seen.update(identity.codex_facts(row, rollouts, paths))
        found = seen["native_id"]
        if found:
            loaded, thread = codex_launch.runtime_thread(row["endpoint"], found)
            seen.update(
                identity.codex_runtime_facts(found, row["worktree"], loaded, thread)
            )
    elif row["harness"] == "claude":
        seen.update(
            identity.claude_facts(claude_launch.live_entries(), seen, row["worktree"])
        )
        seen["brief_uptake"] = bool(seen["native_id"]) and claude_launch.brief_uptake(
            seen["native_id"], row["worktree"], row["brief_digest"]
        )
    else:
        seen["loaded"] = False
    return seen


def inspect(row: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    """Re-observe rather than trusting a saved row."""
    try:
        seen = _observe(row)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        state, reason = "unknown", f"observation failed: {type(error).__name__}"
    else:
        if not row["native_id"] and seen.get("native_id"):
            row["native_id"] = seen["native_id"]
            row["endpoint"] = seen["endpoint"]
        state, reason = identity.readiness(row, seen)
    row.update(state=state, reason=reason, observed_at=_now())
    return row, state, reason


def launch(request: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    """Reserve ownership, launch one TUI, and make a bounded readiness check."""
    brief = Path(request["brief_file"]).read_text()
    if not brief.strip():
        raise ValueError("brief is empty")
    request = {**request, "brief_digest": hashlib.sha256(brief.encode()).hexdigest()}
    rows = registry.read(STORE)
    decision = identity.reservation(rows, request)
    if decision == "inspect":
        row = next(item for item in rows if item["name"] == request["name"])
        _worktree(Path(row["worktree"]), row["branch"], True)
        result = inspect(row)
        registry.write(STORE, rows)
        return result
    if decision != "create":
        raise ValueError(decision)
    windows = subprocess.run(
        ["tmux", "list-windows", "-a", "-F", "#{window_name}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if request["name"] in identity.window_names(
        windows.returncode, windows.stderr, windows.stdout
    ):
        raise ValueError("tmux window name already exists")
    _worktree(Path(request["worktree"]), request["branch"], False)
    row = {
        **request,
        "run_id": str(uuid.uuid7()),
        "launch_time": _now(),
        "endpoint": CODEX_ENDPOINT if request["harness"] == "codex" else None,
        "native_id": None,
        "state": "starting",
        "observed_at": _now(),
    }
    row.pop("brief_file")
    rows.append(row)
    registry.write(STORE, rows)
    try:
        row.update(_new_pane(row, brief))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        row.update(
            state="unknown",
            reason=f"launch observation failed: {type(error).__name__}",
            observed_at=_now(),
        )
        registry.write(STORE, rows)
        return row, "unknown", row["reason"]
    registry.write(STORE, rows)
    for _ in range(8):
        result = inspect(row)
        if result[1] in {"ready", "busy", "blocked"}:
            break
        time.sleep(1)
    registry.write(STORE, rows)
    return result


def status(run_id: str) -> tuple[dict[str, Any], str, str]:
    """Reload by run ID and recheck all available identity surfaces."""
    rows = registry.read(STORE)
    row = next((item for item in rows if item["run_id"] == run_id), None)
    if row is None:
        raise ValueError("run ID not found")
    _worktree(Path(row["worktree"]), row["branch"], True)
    result = inspect(row)
    registry.write(STORE, rows)
    return result
