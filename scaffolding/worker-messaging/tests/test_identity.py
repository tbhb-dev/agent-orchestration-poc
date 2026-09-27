"""Temporary #176 plain value identity tests; #28 replaces this scaffold."""
# ruff: noqa: S101

import hashlib
import json
from datetime import datetime, timedelta
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
    """One remote thread must match the launch time, cwd, and exact brief."""
    row = {
        "worktree": "/worker",
        "launch_time": "2026-09-27T01:00:00+00:00",
        "brief_digest": hashlib.sha256(b"first brief").hexdigest(),
    }
    thread = {
        "id": "one",
        "cwd": "/worker",
        "createdAt": 1790470800,
        "preview": "first brief",
    }
    assert identity.codex_candidate([thread], row) == "one"
    assert identity.codex_candidate([thread, {**thread, "id": "two"}], row) is None
    assert identity.codex_candidate([thread], {**row, "native_id": "two"}) is None
    assert identity.codex_candidate([{**thread, "createdAt": 1790470799}], row) is None
    assert identity.codex_candidate([{**thread, "preview": "other"}], row) is None


@given(st.text(min_size=1))
def test_codex_candidate_property(other: str) -> None:
    """A different cwd cannot claim a remote thread."""
    row = {
        "worktree": "/worker/" + other,
        "launch_time": "2026-09-27T01:00:00+00:00",
        "brief_digest": hashlib.sha256(b"first brief").hexdigest(),
    }
    thread = {
        "id": "one",
        "cwd": "/worker",
        "createdAt": 1790470800,
        "preview": "first brief",
    }
    assert identity.codex_candidate([thread], row) is None


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
    row = {"worktree": "/worker", "model": "gpt-6-sol", "effort": "high"}
    thread = {
        "id": "thread-1",
        "cwd": "/worker",
        "model": "gpt-6-sol",
        "reasoningEffort": "high",
        "status": {"type": "idle"},
    }
    assert identity.codex_runtime_facts("thread-1", row, True, thread)["loaded"]
    assert not identity.codex_runtime_facts(
        "thread-1", row, True, {**thread, "status": {"type": "notLoaded"}}
    )["loaded"]


@pytest.mark.parametrize(
    "name", ["codex-owning-endpoint.json", "codex-unloaded-restart.json"]
)
def test_endpoint_fixture_readback(name: str) -> None:
    """Stored history without a loaded runtime cannot grant readiness."""
    case = fixture(name)
    row = case["record"]
    readback = case["read"]
    facts = identity.codex_runtime_facts(
        row["native_id"],
        row,
        row["native_id"] in identity.loaded_ids(case["loaded"]),
        readback,
    )
    assert facts["loaded"] is (name == "codex-owning-endpoint.json")


def test_fresh_status_cannot_override_stale_native_identity() -> None:
    """Advisory status freshness leaves a native unknown unchanged."""
    case = fixture("status-fresh-stale-native.json")
    view = identity.status_view(
        case["row"], case["record"], "/status.json", case["now"]
    )
    assert view["availability"] == case["expected_availability"]
    assert case["row"]["state"] == case["expected_readiness"]


@given(st.integers(min_value=0, max_value=10000))
def test_status_age_classification(age: int) -> None:
    """Status age alone determines fresh versus stale for valid records."""
    row = {"run_id": "one", "pane_generation": "generation"}
    record = {
        "run_id": "one",
        "generation": "generation",
        "last_seen_utc": "2026-09-27T00:00:00+00:00",
    }
    now = (
        datetime.fromisoformat(record["last_seen_utc"]) + timedelta(seconds=age)
    ).isoformat()
    view = identity.status_view(row, record, "/status", now)
    assert view["availability"] == ("fresh" if age <= 120 else "stale")


@pytest.mark.parametrize(
    ("record", "availability"),
    [
        (None, "missing"),
        ({"run_id": "wrong", "generation": "generation"}, "invalid"),
        ({"run_id": "one", "generation": "wrong"}, "invalid"),
        (
            {"run_id": "one", "generation": "generation", "last_seen_utc": "bad"},
            "invalid",
        ),
    ],
)
def test_status_invalid_cases(record: dict[str, Any] | None, availability: str) -> None:
    """Missing or mismatched snapshots cannot claim freshness."""
    row = {"run_id": "one", "pane_generation": "generation"}
    view = identity.status_view(row, record, "/status", "2026-09-27T00:00:00+00:00")
    assert view["availability"] == availability
    assert view["record"] is None


@pytest.mark.parametrize("change", ["id", "cwd", "model", "reasoningEffort", "status"])
def test_codex_remote_readback_mismatch(change: str) -> None:
    """A loaded ID alone cannot establish configured worker readiness."""
    row = {"worktree": "/worker", "model": "gpt-6-sol", "effort": "high"}
    thread = {
        "id": "thread-1",
        "cwd": "/worker",
        "model": "gpt-6-sol",
        "reasoningEffort": "high",
        "status": {"type": "idle"},
    }
    assert not identity.codex_runtime_facts(
        "thread-1", row, True, {**thread, change: "wrong"}
    )["loaded"]


@given(st.text().filter(lambda value: value != "gpt-6-sol"))
def test_codex_model_readback_property(value: str) -> None:
    """No distinct model name can satisfy the recorded model check."""
    row = {"worktree": "/worker", "model": "gpt-6-sol", "effort": "high"}
    thread = {
        "id": "thread-1",
        "cwd": "/worker",
        "model": value,
        "reasoningEffort": "high",
        "status": {"type": "idle"},
    }
    assert not identity.codex_runtime_facts("thread-1", row, True, thread)["loaded"]


@given(st.text())
def test_codex_endpoint_requires_explicit_unix_socket(address: str) -> None:
    """Only absolute Unix endpoint values can enter a Codex launch."""
    if (
        address.startswith("unix:///")
        and "\x00" not in address
        and "//" not in address[7:]
        and "/../" not in f"{address[7:]}/"
        and address[7:] != "/"
    ):
        assert identity.codex_endpoint(address) == address[7:]
    else:
        with pytest.raises(ValueError, match="endpoint"):
            identity.codex_endpoint(address)


@pytest.mark.parametrize(
    ("stderr", "missing"),
    [
        ("can't find pane: %1", True),
        ("can't find window: @1", True),
        ("can't find session: workers", True),
        ("no server running", True),
        ("error connecting to socket (No such file or directory)", True),
        ("Operation not permitted", False),
        ("unexpected tmux failure", False),
    ],
)
def test_missing_tmux_target(stderr: str, missing: bool) -> None:
    """Only tmux's absent-target replies get the specific missing reason."""
    assert identity.missing_tmux_target(stderr) is missing


@given(st.text())
def test_missing_tmux_target_property(surrounding: str) -> None:
    """A missing pane marker remains recognizable amid other tmux text."""
    assert identity.missing_tmux_target(f"{surrounding}can't find pane: %1")


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
    row = {
        "harness": "codex",
        "model": "m",
        "effort": "high",
        "worktree": "/new",
        "endpoint": "unix:///private/tmp/worker.sock",
    }
    command = identity.command(row, "brief", "/repo/.holding/shim", "/usr/bin")
    assert "--remote unix:///private/tmp/worker.sock" in command
    assert "--add-dir" not in command
    assert "writable_roots" not in command
    assert "PATH=/repo/.holding/shim:/usr/bin" in command


def test_main_is_rejected_even_with_recorded_owner() -> None:
    """A saved row never permits work on main."""
    request = dict.fromkeys(("name", "branch", "worktree", "tmux_name"), "main")
    assert identity.reservation([request], request) == "main branch is forbidden"


def test_claude_transcript_brief_acceptance() -> None:
    """Session, cwd, and exact first user content must agree."""
    rows = [
        {
            "sessionId": "other",
            "cwd": "/worker",
            "type": "user",
            "message": {"content": "first brief"},
        },
        {
            "sessionId": "session-1",
            "cwd": "/other",
            "type": "user",
            "message": {"content": "first brief"},
        },
        {
            "sessionId": "session-1",
            "cwd": "/worker",
            "type": "assistant",
            "message": {"content": "first brief"},
        },
        {
            "sessionId": "session-1",
            "cwd": "/worker",
            "type": "user",
            "message": {"content": "first brief"},
        },
    ]
    digest = hashlib.sha256(b"first brief").hexdigest()
    assert identity.claude_brief_uptake(rows, "session-1", "/worker", digest)
    assert not identity.claude_brief_uptake(rows[:3], "session-1", "/worker", digest)
    assert not identity.claude_brief_uptake(rows, "session-1", "/worker", "wrong")
