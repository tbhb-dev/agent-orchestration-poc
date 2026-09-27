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
    ("path", "created", "allowed"),
    [
        ("/repo/.worktrees/worker", True, True),
        ("/repo/.worktrees/worker", False, False),
        ("/repo", True, False),
        ("/repo/.worktrees", True, False),
        ("/repo/.worktrees/worker/nested", True, False),
        ("/other/worker", True, False),
    ],
)
def test_trust_target(path: str, created: bool, allowed: bool) -> None:
    """Only a launcher-created exact child of the worktree directory is eligible."""
    if allowed:
        assert identity.trust_target(path, "/repo", created) == path
    else:
        with pytest.raises(ValueError, match="launcher-created"):
            identity.trust_target(path, "/repo", created)


@given(
    st.text(min_size=1).filter(
        lambda name: (
            "/" not in name
            and "\x00" not in name
            and name not in {".", ".."}
            and all(not 0xD800 <= ord(char) <= 0xDFFF for char in name)
        )
    )
)
def test_trust_target_property(name: str) -> None:
    """A direct child is eligible only when creation belongs to this run."""
    path = f"/repo/.worktrees/{name}"
    assert identity.trust_target(path, "/repo", True) == path
    with pytest.raises(ValueError, match="launcher-created"):
        identity.trust_target(path, "/repo", False)


@pytest.mark.parametrize("value", ["trusted", None])
def test_trust_write_params(value: str | None) -> None:
    """Both registration and removal use the tagged replace request shape."""
    params = identity.trust_write_params('/repo/.worktrees/a"b', value)
    assert params == {
        "edits": [
            {
                "keyPath": 'projects."/repo/.worktrees/a\\"b".trust_level',
                "value": value,
                "mergeStrategy": "replace",
            }
        ],
        "filePath": None,
        "expectedVersion": None,
        "reloadUserConfig": True,
    }


def server_key_segments(key: str) -> list[str]:
    """Mirror the pinned config manager's quoted-key parser for this test."""
    segments: list[str] = []
    segment = ""
    quoted = False
    index = 0
    while index < len(key):
        char = key[index]
        if char == '"' and not segment and not quoted:
            quoted = True
        elif char == '"' and quoted:
            quoted = False
        elif char == "\\" and quoted:
            index += 1
            if index == len(key):
                raise ValueError("unterminated escape")
            segment += key[index]
        elif char == "." and not quoted:
            if not segment:
                raise ValueError("empty segment")
            segments.append(segment)
            segment = ""
        elif char == '"':
            raise ValueError("invalid quote")
        else:
            segment += char
        index += 1
    if quoted or not segment:
        raise ValueError("incomplete key")
    return [*segments, segment]


@pytest.mark.parametrize(
    "path",
    [
        "/repo/.worktrees/a\nb",
        "/repo/.worktrees/a\\b",
        '/repo/.worktrees/a"b',
        "/repo/.worktrees/a.b",
    ],
)
def test_trust_key_server_roundtrip(path: str) -> None:
    """The server parser must select exactly the requested worktree."""
    key = identity.trust_write_params(path, "trusted")["edits"][0]["keyPath"]
    assert server_key_segments(key) == ["projects", path, "trust_level"]


@given(
    st.text(min_size=1).filter(
        lambda path: (
            "\x00" not in path
            and all(not 0xD800 <= ord(char) <= 0xDFFF for char in path)
        )
    )
)
def test_trust_write_params_property(path: str) -> None:
    """Every escaped key decodes to exactly the path supplied."""
    params = identity.trust_write_params(path, "trusted")
    key = params["edits"][0]["keyPath"]
    assert server_key_segments(key) == ["projects", path, "trust_level"]


@pytest.mark.parametrize("path", ["a\x00b", "a\ud800b"])
def test_trust_key_rejects_unrepresentable_path(path: str) -> None:
    """Reject bytes the config path cannot persist before any write."""
    with pytest.raises(ValueError, match="trust path"):
        identity.trust_write_params(path, "trusted")


@pytest.mark.parametrize(
    ("response", "confirmed"),
    [({"status": "ok"}, True), ({"status": "okOverridden"}, False), ({}, False)],
)
def test_trust_write_confirmed(response: dict[str, Any], confirmed: bool) -> None:
    """An overridden or missing status cannot establish the edit."""
    assert identity.trust_write_confirmed(response) is confirmed


@given(st.text().filter(lambda status: status != "ok"))
def test_trust_write_confirmed_property(status: str) -> None:
    """Every other write status fails the confirmation gate."""
    assert not identity.trust_write_confirmed({"status": status})


@pytest.mark.parametrize(
    ("entry", "expected", "confirmed"),
    [
        ({"trust_level": "trusted"}, "trusted", True),
        ({"trust_level": "untrusted"}, "trusted", False),
        (None, "trusted", False),
        (None, None, True),
        ({}, None, True),
        ({"trust_level": "trusted"}, None, False),
    ],
)
def test_trust_readback(entry: object, expected: str | None, confirmed: bool) -> None:
    """Only the exact project key establishes registration or removal."""
    projects = {} if entry is None else {"/worker": entry}
    response = {"config": {"projects": projects}, "layers": []}
    assert identity.trust_readback(response, "/worker", expected) is confirmed
    assert not identity.trust_readback(response, "/other", "trusted")


@given(st.text(min_size=1))
def test_trust_readback_property(other: str) -> None:
    """A different project key cannot satisfy exact-path registration."""
    if other == "/worker":
        return
    response = {
        "config": {"projects": {other: {"trust_level": "trusted"}}},
        "layers": [],
    }
    assert not identity.trust_readback(response, "/worker", "trusted")


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"layers": []},
        {"config": {}, "layers": None},
        {"config": {"projects": []}, "layers": []},
    ],
)
def test_trust_readback_rejects_invalid_response(response: dict[str, Any]) -> None:
    """Malformed read-backs cannot confirm even an absent entry."""
    assert not identity.trust_readback(response, "/worker", None)


@pytest.mark.parametrize(
    ("row", "result"),
    [
        ({}, None),
        ({"trust_registered": True}, None),
        ({"trust_registered": False}, ("blocked", "folder trust removed")),
        (
            {"trust_blocked": True, "reason": "write failed"},
            ("blocked", "write failed"),
        ),
    ],
)
def test_trust_gate(row: dict[str, Any], result: tuple[str, str] | None) -> None:
    """A blocked edit or completed cleanup remains ineligible for sends."""
    assert identity.trust_gate(row) == result


@given(st.text())
def test_trust_gate_property(reason: str) -> None:
    """Every recorded trust failure retains its reason on reinspection."""
    assert identity.trust_gate({"trust_blocked": True, "reason": reason}) == (
        "blocked",
        reason,
    )


@pytest.mark.parametrize(
    ("action", "outcome", "expected"),
    [
        ("register", "confirmed", (True, False, "confirmed")),
        ("register", "preflight", (None, True, "failed")),
        ("register", "conflict", (None, True, "failed")),
        ("register", "write_failed", (None, True, "failed")),
        ("remove", "confirmed", (False, False, "confirmed")),
        ("remove", "write_failed", (True, True, "failed")),
    ],
)
def test_trust_transition_values(
    action: str, outcome: str, expected: tuple[bool | None, bool, str]
) -> None:
    """Trust state, ownership, and event results come from plain values."""
    original: dict[str, Any] = {"state": "starting"}
    if action == "remove":
        original["trust_registered"] = True
    snapshot = original.copy()
    started = identity.trust_transition(original, "attempted", "time-1", action=action)
    if outcome not in {"preflight", "conflict"}:
        started = identity.trust_transition(started, "writing", "time-2")
        assert started["trust_write_attempted"] is True
        assert started["reason"] == f"folder trust {action} outcome unknown"
    final = identity.trust_transition(started, outcome, "time-3", reason="denied")
    assert original == snapshot
    assert final.get("trust_registered") is expected[0]
    assert final["trust_blocked"] is expected[1]
    assert final["trust_events"][-1]["result"] == expected[2]
    if outcome == "conflict":
        assert final["trust_conflict"] is True
    if outcome == "write_failed":
        assert final["reason"] == f"folder trust {action} failed: denied"


@pytest.mark.parametrize(
    ("row", "error"),
    [
        (
            {"harness": "codex", "trust_events": [{}], "trust_write_attempted": True},
            None,
        ),
        (
            {"harness": "codex", "trust_events": [{}]},
            "run has no launcher-owned Codex trust write",
        ),
        (
            {"harness": "claude", "trust_events": [{}], "trust_write_attempted": True},
            "run has no launcher-owned Codex trust write",
        ),
        (
            {
                "harness": "codex",
                "trust_events": [{}],
                "trust_write_attempted": True,
                "trust_registered": False,
            },
            "run trust entry was already removed",
        ),
    ],
)
def test_trust_cleanup_eligibility(row: dict[str, Any], error: str | None) -> None:
    """An ambiguous owned write is eligible; preflight and removed rows are not."""
    assert identity.trust_cleanup_error(row) == error


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


@pytest.mark.parametrize("changed", ["pane_generation", "pid", "process_start"])
def test_stale_trust_pane_is_unknown(changed: str) -> None:
    """Trust text in a replaced pane cannot identify the recorded worker."""
    case = fixture("readiness.json")
    seen = {**case["seen"], "trust_prompt": True, changed: "replaced"}
    assert identity.readiness(case["record"], seen)[0] == "unknown"


@given(st.text(min_size=1).filter(lambda value: value != "Sun Sep 27 01:00:00 2026"))
def test_stale_process_with_trust_property(start: str) -> None:
    """Any changed process start outranks text left in the pane."""
    case = fixture("readiness.json")
    seen = {**case["seen"], "trust_prompt": True, "process_start": start}
    assert identity.readiness(case["record"], seen)[0] == "unknown"


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
    ("roots", "expected"),
    [(["/repo/.git"], True), (["/other"], False), ([], False)],
)
def test_reported_common_git_root(roots: list[str], expected: bool) -> None:
    """The server must report the exact common Git directory for the thread."""
    assert identity.common_git_root("/repo/.git", roots) is expected


@given(st.text(min_size=1).filter(lambda root: root != "/repo/.git"))
def test_unreported_common_git_root_property(root: str) -> None:
    """Any different reported root cannot stand in for the common Git root."""
    assert not identity.common_git_root("/repo/.git", [root])


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("session|@4|%5|123\n", ("session", "@4", "%5", "123")),
        ("session|@4|%5|0\n", ("session", "@4", "%5", "0")),
        ("|||\n", None),
        ("session|@4|%5|", None),
        ("session|@4|%5|abc", None),
    ],
)
def test_tmux_pane_fields(output: str, expected: tuple[str, ...] | None) -> None:
    """Only a complete display response names a live target."""
    assert identity.tmux_pane_fields(output) == expected


@given(st.text().filter(lambda value: not value.rstrip().isdecimal()))
def test_tmux_pane_pid_property(value: str) -> None:
    """No PID that remains nonnumeric after output trimming reaches observation."""
    assert identity.tmux_pane_fields(f"session|@4|%5|{value}") is None


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
    assert "GIT_AUTHOR_NAME=tbhb-agent" in command
    assert "GIT_COMMITTER_NAME=tbhb-agent" in command


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
