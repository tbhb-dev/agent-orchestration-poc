"""Temporary #176 plain value identity tests; #28 replaces this scaffold."""
# ruff: noqa: S101

import json
from pathlib import Path
from typing import Any, cast

import identity
import pytest
from hypothesis import given
from hypothesis import strategies as st


def fixture(name: str) -> dict[str, Any]:
    """Read one sanitized identity fixture."""
    path = Path(__file__).parent / "fixtures/launcher" / name
    return cast("dict[str, Any]", json.loads(path.read_text()))


@pytest.mark.parametrize(
    ("change", "value", "state"), fixture("cases.json")["observations"]
)
def test_readiness_cases(change: str, value: object, state: str) -> None:
    """Reject stale targets, missing uptake, and trust prompts."""
    case = fixture("readiness.json")
    assert (
        identity.readiness(case["record"], {**case["seen"], change: value})[0] == state
    )


def test_clean_restart() -> None:
    """A fresh row and matching generation can become ready."""
    case = fixture("readiness.json")
    changes = fixture("cases.json")["restart"]
    assert (
        identity.readiness({**case["record"], **changes}, {**case["seen"], **changes})[
            0
        ]
        == "ready"
    )


@given(st.integers(min_value=1).filter(lambda pid: pid != 100))
def test_pid_reuse_property(pid: int) -> None:
    """Any other PID is never ready."""
    case = fixture("readiness.json")
    assert (
        identity.readiness(case["record"], {**case["seen"], "pid": pid})[0] == "unknown"
    )


@pytest.mark.parametrize("field", ["name", "branch", "worktree", "tmux_name"])
def test_reservation(field: str) -> None:
    """An owned launch address cannot be reused for another run."""
    request = dict.fromkeys(("name", "branch", "worktree", "tmux_name"), "original")
    assert identity.reservation([], request) == "create"
    assert identity.reservation([request], request) == "inspect"
    assert (
        identity.reservation([request], {**request, field: "different"})
        == "duplicate ownership"
    )


@given(
    st.sampled_from(["name", "branch", "worktree", "tmux_name"]), st.text(min_size=1)
)
def test_reservation_property(field: str, suffix: str) -> None:
    """Changing one owned field never creates an independent run."""
    request = dict.fromkeys(("name", "branch", "worktree", "tmux_name"), "original")
    assert (
        identity.reservation([request], {**request, field: "original" + suffix})
        == "duplicate ownership"
    )


def test_codex_candidate() -> None:
    """A thread needs one process-held rollout in the worktree."""
    rows = [{"id": "one", "cwd": "worktree", "path": "rollout"}]
    assert identity.codex_candidate(rows, "worktree", ["rollout"]) == "one"
    assert identity.codex_candidate(rows, "worktree", []) is None
    assert identity.codex_candidate(rows * 2, "worktree", ["rollout"]) is None


@given(st.text(min_size=1))
def test_codex_candidate_property(other: str) -> None:
    """A different cwd cannot claim the process-held rollout."""
    rows = [{"id": "one", "cwd": "worktree", "path": "rollout"}]
    assert identity.codex_candidate(rows, "worktree/" + other, ["rollout"]) is None


@pytest.mark.parametrize(
    ("key", "value"),
    [("pid", 101), ("procStart", "later"), ("tmux", "other"), ("cwd", "other")],
)
def test_claude_candidate(key: str, value: object) -> None:
    """Process, start, pane, and cwd identify one live entry."""
    case = fixture("claude.json")
    assert identity.claude_candidate([case["entry"]], case["seen"]) == case["entry"]
    assert (
        identity.claude_candidate([{**case["entry"], key: value}], case["seen"]) is None
    )


@given(st.integers(min_value=1).filter(lambda pid: pid != 100))
def test_claude_candidate_property(pid: int) -> None:
    """A recycled PID cannot inherit a native Claude identity."""
    case = fixture("claude.json")
    assert (
        identity.claude_candidate([{**case["entry"], "pid": pid}], case["seen"]) is None
    )


def test_codex_native_response_decisions() -> None:
    """A loaded string ID and tagged active status imply busy."""
    assert identity.loaded_ids({"data": ["thread-1"], "nextCursor": None}) == {
        "thread-1"
    }
    assert identity.codex_busy({"status": {"type": "active", "activeFlags": []}})
    assert not identity.codex_busy({"status": {"type": "idle"}})
    assert not identity.codex_busy({"status": {"type": "notLoaded"}})
    thread = {"id": "thread-1", "cwd": "/worker", "status": {"type": "idle"}}
    assert identity.codex_runtime_facts("thread-1", "/worker", True, thread)["loaded"]
    assert not identity.codex_runtime_facts(
        "thread-1", "/worker", True, {**thread, "status": {"type": "notLoaded"}}
    )["loaded"]


def test_worktree_ownership_decisions() -> None:
    """Only a recorded run may inspect an existing checkout."""
    listed = "worktree /existing\nbranch refs/heads/tooling/176-worker\n"
    assert (
        identity.worktree_action("/existing", "tooling/176-worker", listed, True, False)
        == "reject"
    )
    assert (
        identity.worktree_action("/existing", "tooling/176-worker", listed, True, True)
        == "inspect"
    )
    assert identity.worktree_action("/new", "main", "", False, False) == "reject"
    assert (
        identity.worktree_action("/new", "tooling/176-worker", "", False, False)
        == "create"
    )
    assert (
        identity.worktree_action("/missing", "tooling/176-worker", "", False, True)
        == "reject"
    )


def test_tmux_window_decisions() -> None:
    """A missing server is empty; other failures remain errors."""
    assert identity.window_names(1, "no server running", "") == []
    assert identity.window_names(0, "", "alice\nbob\n") == ["alice", "bob"]
    with pytest.raises(ValueError, match="tmux window observation failed"):
        identity.window_names(1, "permission denied", "")
    with pytest.raises(ValueError, match="tmux window observation failed"):
        identity.window_names(
            1, "error connecting to socket (Operation not permitted)", ""
        )
    assert identity.session_missing(1, "can't find session: worker-messaging")
    assert identity.session_missing(1, "no server running")
    assert not identity.session_missing(0, "")
    with pytest.raises(ValueError, match="tmux session observation failed"):
        identity.session_missing(1, "Operation not permitted")


def test_command_uses_captured_paths() -> None:
    """Main and linked checkout use the same common Git directory and shim."""
    row = {"harness": "codex", "model": "m", "effort": "high", "worktree": "/new"}
    command = identity.command(
        row, "brief", "/repo/.holding/shim", "/repo/.git", "/usr/bin"
    )
    assert "--add-dir /repo/.git" in command
    assert "PATH=/repo/.holding/shim:/usr/bin" in command


def test_main_is_rejected_even_with_recorded_owner() -> None:
    """A saved row never permits work on main."""
    request = dict.fromkeys(("name", "branch", "worktree", "tmux_name"), "main")
    assert identity.reservation([request], request) == "main branch is forbidden"
