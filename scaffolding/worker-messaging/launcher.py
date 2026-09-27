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


def _run(argv: list[str]) -> str:
    return subprocess.run(
        argv, capture_output=True, text=True, errors="replace", check=True
    ).stdout.strip()


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _pane(pane: str) -> dict[str, Any]:
    target = subprocess.run(
        [
            "tmux",
            "display-message",
            "-p",
            "-t",
            pane,
            "#{session_name}|#{window_id}|#{pane_id}|#{pane_pid}",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    if target.returncode:
        if identity.missing_tmux_target(target.stderr):
            return {"tmux_missing": True}
        raise ValueError("tmux target observation failed")
    fields = identity.tmux_pane_fields(target.stdout)
    if fields is None:
        return {"tmux_missing": True}
    session, window, pane_id, pid = fields
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


def _worktree(path: Path, branch: str, owned: bool) -> bool:
    listings = _run(["git", "worktree", "list", "--porcelain"])
    action = identity.worktree_action(str(path), branch, listings, path.exists(), owned)
    if action == "inspect":
        return False
    if action != "create":
        raise ValueError("worktree or branch is not available for this run")
    if _run(["git", "branch", "--list", branch]):
        raise ValueError("branch exists without requested worktree")
    path.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "fetch", "origin", "main"])
    _run(["git", "worktree", "add", "-b", branch, str(path), "origin/main"])
    return True


def _change_trust(
    row: dict[str, Any], rows: list[dict[str, Any]], remove: bool
) -> bool:
    """Persist every run-owned edit attempt before contacting its endpoint."""
    target = identity.trust_target(
        row["worktree"],
        str(Path(row["git_common_dir"]).parent),
        row.get("trust_created") is True,
    )
    event = {
        "action": "remove" if remove else "register",
        "at": _now(),
        "result": "attempted",
    }
    row.setdefault("trust_events", []).append(event)
    registry.write(STORE, rows)
    try:
        codex_launch.change_trust(
            row["endpoint"], target, None if remove else "trusted"
        )
    except codex_launch.TrustConflictError as error:
        row["trust_conflict"] = True
        row["trust_blocked"] = True
        event.update(result="failed", reason=str(error))
        row.update(state="blocked", reason=str(error), observed_at=_now())
        registry.write(STORE, rows)
        return False
    except codex_launch.TrustPreflightError as error:
        row["trust_blocked"] = True
        event.update(result="failed", reason=str(error))
        row.update(state="blocked", reason=str(error), observed_at=_now())
        registry.write(STORE, rows)
        return False
    except (OSError, ValueError, EOFError, TimeoutError) as error:
        row["trust_write_attempted"] = True
        row["trust_blocked"] = True
        event.update(result="failed", reason=str(error))
        row.update(
            state="blocked",
            reason=f"folder trust {event['action']} failed: {error}",
            observed_at=_now(),
        )
        registry.write(STORE, rows)
        return False
    event["result"] = "confirmed"
    row["trust_write_attempted"] = True
    row["trust_blocked"] = False
    row["trust_registered"] = not remove
    registry.write(STORE, rows)
    return True


def _command(row: dict[str, Any], brief: str) -> str:
    common_git = Path(
        _run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"])
    )
    shim = common_git.parent / ".holding/shim"
    return identity.command(row, brief, str(shim), os.environ["PATH"])


def _new_pane(row: dict[str, Any], brief: str) -> dict[str, Any]:
    present = subprocess.run(
        ["tmux", "has-session", "-t", SESSION],
        capture_output=True,
        text=True,
        errors="replace",
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
    if seen.get("tmux_missing"):
        return seen
    capture = _run(["tmux", "capture-pane", "-p", "-S", "-80", "-t", row["tmux_pane"]])
    seen["trust_prompt"] = identity.trust_prompt(capture)
    if seen["trust_prompt"] or not seen["process_start"]:
        return seen
    if row["harness"] == "codex":
        found, loaded, thread = codex_launch.discover_thread(row["endpoint"], row)
        seen.update(native_id=found, brief_uptake=bool(found))
        if found:
            seen.update(identity.codex_runtime_facts(found, row, loaded, thread))
            roots = thread.get("runtimeWorkspaceRoots")
            if isinstance(roots, list) and all(isinstance(root, str) for root in roots):
                row["runtime_workspace_roots"] = roots
                seen["roots_confirmed"] = identity.common_git_root(
                    row.get("git_common_dir", ""), roots
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
    gate = identity.trust_gate(row)
    if gate is not None:
        state, reason = gate
        row.update(state=state, reason=reason, observed_at=_now())
        return row, state, reason
    try:
        seen = _observe(row)
    except (
        OSError,
        ValueError,
        KeyError,
        EOFError,
        subprocess.CalledProcessError,
    ) as error:
        state, reason = "unknown", f"observation failed: {type(error).__name__}"
    else:
        if not row["native_id"] and seen.get("native_id"):
            row["native_id"] = seen["native_id"]
            row["endpoint"] = seen["endpoint"]
        state, reason = identity.readiness(row, seen)
    row.update(state=state, reason=reason, observed_at=_now())
    return row, state, reason


def launch(request: dict[str, Any]) -> tuple[dict[str, Any], str, str]:  # noqa: C901
    """Reserve ownership, launch one TUI, and make a bounded readiness check."""
    common_git = None
    if request["harness"] == "codex":
        identity.codex_endpoint(request.get("endpoint"))
        common_git = _run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"]
        )
        identity.trust_target(request["worktree"], str(Path(common_git).parent), True)
    brief = Path(request["brief_file"]).read_text()
    if not brief.strip():
        raise ValueError("brief is empty")
    digest = (
        identity.codex_brief_digest(brief)
        if request["harness"] == "codex"
        else hashlib.sha256(brief.encode()).hexdigest()
    )
    request = {**request, "brief_digest": digest}
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
        errors="replace",
        check=False,
    )
    if request["name"] in identity.window_names(
        windows.returncode, windows.stderr, windows.stdout
    ):
        raise ValueError("tmux window name already exists")
    created = _worktree(Path(request["worktree"]), request["branch"], False)
    row = {
        **request,
        "run_id": str(uuid.uuid7()),
        "launch_time": _now(),
        "endpoint": request.get("endpoint") if request["harness"] == "codex" else None,
        "native_id": None,
        "state": "starting",
        "observed_at": _now(),
    }
    if request["harness"] == "codex":
        row["trust_created"] = created
        row["git_common_dir"] = common_git
    row.pop("brief_file")
    rows.append(row)
    registry.write(STORE, rows)
    if request["harness"] == "codex" and not _change_trust(row, rows, remove=False):
        return row, "blocked", row["reason"]
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


def cleanup(run_id: str) -> tuple[dict[str, Any], str, str]:
    """Remove the recorded run's exact Codex trust entry after worker cleanup."""
    rows = registry.read(STORE)
    row = next((item for item in rows if item["run_id"] == run_id), None)
    if row is None:
        raise ValueError("run ID not found")
    if (
        row["harness"] != "codex"
        or not row.get("trust_events")
        or not row.get("trust_write_attempted")
    ):
        raise ValueError("run has no launcher-owned Codex trust write")
    if row.get("trust_registered") is False:
        raise ValueError("run trust entry was already removed")
    if not _change_trust(row, rows, remove=True):
        return row, "blocked", row["reason"]
    row.update(state="removed", reason="folder trust removed", observed_at=_now())
    registry.write(STORE, rows)
    return row, "removed", row["reason"]


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


def status_record(row: dict[str, Any]) -> dict[str, Any]:
    """Read the separate #178 status snapshot as advisory information."""
    source_name = f".local-cache/worker-messaging/status/{row['run_id']}.json"
    source = ROOT / source_name
    try:
        record = registry.read_status(source)
    except OSError, ValueError, TypeError:
        record = {}
    return identity.status_view(row, record, source_name, _now())
