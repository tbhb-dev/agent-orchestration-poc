"""Configuration checks for the four BV-01 relay cells."""

import runpy
import socket
import subprocess
import tempfile
import tomllib
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_orchestration_poc.core.host_socket_attribution import (
    claude_settings,
    claude_trust,
    codex_config,
    empty_input_prompt,
    launch_command,
    relay_result,
)

REPOSITORY = Path(__file__).resolve().parents[1]
if REPOSITORY.name == "mutants":
    REPOSITORY = REPOSITORY.parent
EXPERIMENT = REPOSITORY / "experiments/02-host-socket-attribution"
RELAY = runpy.run_path(str(EXPERIMENT / "relay_cell.py"))


def set_cell_paths(
    monkeypatch: pytest.MonkeyPatch, cell_type: object, home: Path, evidence: Path
) -> None:
    def cell_home(self: object) -> Path:
        return home

    def cell_evidence(self: object) -> Path:
        return evidence

    monkeypatch.setattr(cell_type, "home", property(cell_home))
    monkeypatch.setattr(cell_type, "evidence", property(cell_evidence))


@pytest.mark.parametrize("profile", ["codex-headless", "codex-interactive"])
def test_codex_profile_reads_only_disposable_workspace_and_python(profile: str) -> None:
    home = Path(f"/private/tmp/bv01-228-{profile}")
    config = tomllib.loads(
        codex_config(
            home,
            Path("/Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3"),
            43210,
        )
    )
    workspace = home / "workspace"
    python = Path("/Users/tony/.local/share/mise/installs/python/3.14.6")
    assert config["default_permissions"] == "bv01"
    assert config["permissions"]["bv01"]["filesystem"] == {
        str(workspace): "read",
        str(python): "read",
    }
    assert config["permissions"]["bv01"]["network"]["unix_sockets"] == {
        str(home / "gateway.sock"): "allow"
    }
    assert config["projects"][str(workspace)]["trust_level"] == "trusted"
    assert config["tui"]["screen_reader_detection_done"] is True


@pytest.mark.parametrize("profile", ["claude-headless", "claude-interactive"])
def test_claude_trust_is_scoped_to_cell_workspace(profile: str) -> None:
    workspace = Path(f"/private/tmp/bv01-228-{profile}/workspace")
    config = claude_trust(workspace)
    assert config == {
        "hasCompletedOnboarding": True,
        "theme": "dark",
        "projects": {str(workspace): {"hasTrustDialogAccepted": True}},
    }


@pytest.mark.parametrize(
    "profile",
    ["codex-headless", "codex-interactive", "claude-headless", "claude-interactive"],
)
def test_launch_configuration(profile: str) -> None:
    home = Path(f"/private/tmp/bv01-228-{profile}")
    workspace = home / "workspace"
    prompt = (
        "Run python3 experiments/02-host-socket-attribution/probe.py client "
        f"{home}/gateway.sock {profile} and then stop."
    )
    argv, env = launch_command(
        profile,
        43210,
        home,
        (Path("/codex"), Path("/claude"), Path("/python/bin/python3")),
    )
    expected_env = {
        "HOME": str(home),
        "TMPDIR": str(home / "tmp"),
        "XDG_CONFIG_HOME": str(home / "xdg"),
        "PYTHONPATH": str(workspace),
        "PATH": "/Users/tony/.local/bin:/python/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "TERM": "xterm-256color",
        "LANG": "C.UTF-8",
        "NO_COLOR": "1",
        "PYTHONUNBUFFERED": "1",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "127.0.0.1,localhost",
    }
    if profile == "codex-headless":
        expected_argv = [
            "/codex",
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "-C",
            str(workspace),
            "-c",
            "approval_policy=never",
            prompt,
        ]
    elif profile == "codex-interactive":
        expected_argv = ["/codex", "-C", str(workspace), "-c", "approval_policy=never"]
    else:
        expected_argv = [
            "/claude",
            "--bare",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--settings",
            str(home / "settings.json"),
        ]
        if profile == "claude-headless":
            expected_argv += [
                "--print",
                "--no-session-persistence",
                "--permission-prompts",
                "none",
                prompt,
            ]
    if profile.startswith("codex-"):
        expected_env.update(
            {
                "CODEX_HOME": str(home / "codex"),
                "BV01_FAKE_OPENAI_KEY": "not-a-real-key",
            }
        )
    else:
        expected_env.update(
            {
                "CLAUDE_CONFIG_DIR": str(home / "claude"),
                "ANTHROPIC_API_KEY": "not-a-real-key",
                "ANTHROPIC_BASE_URL": "http://127.0.0.1:43210",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            }
        )
    assert argv == expected_argv
    assert env == expected_env
    if profile.startswith("claude-"):
        assert claude_settings(home) == {
            "sandbox": {
                "enabled": True,
                "failIfUnavailable": True,
                "network": {
                    "allowUnixSockets": [str(home / "gateway.sock")],
                    "allowAllUnixSockets": False,
                    "allowLocalBinding": False,
                },
                "allowUnsandboxedCommands": False,
            }
        }


@pytest.mark.parametrize(
    ("rows", "requests", "exit_code", "error"),
    [
        (
            [{"status": 403}],
            [{"peer": {"pid": 1}, "decision": "allowed"}],
            0,
            "responder refused",
        ),
        ([{"status": 200}], [], 0, "exactly one"),
        (
            [{"status": 200}],
            [{"peer": {"pid": 1}, "decision": "allowed"}],
            2,
            "exited 2",
        ),
    ],
)
def test_relay_result_rejects_bad_outcome(
    rows: list[dict[str, object]],
    requests: list[dict[str, object]],
    exit_code: int,
    error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        relay_result(rows, requests, exit_code)


def test_relay_result_accepts_connector() -> None:
    assert (
        relay_result(
            [{"status": 200}], [{"peer": {"pid": 42}, "decision": "allowed"}], None
        )
        == "peer=42 decision=allowed requests=1"
    )


@pytest.mark.parametrize("marker", ["❯", "›"])
def test_only_bare_input_prompt_is_ready(marker: str) -> None:
    assert empty_input_prompt(f"header\n {marker} \nfooter", marker)
    assert not empty_input_prompt(f"header\n {marker} No, exit\nfooter", marker)


def test_codex_fresh_thread_placeholder_is_ready() -> None:
    pane = (EXPERIMENT / "fixtures/codex-fresh-thread-header.snap").read_text()
    assert empty_input_prompt(pane, "›")
    assert not empty_input_prompt("Codex\n› No, exit\n", "›")


@pytest.mark.parametrize("append_event", [False, True])
def test_capture_gate_requires_event_after_marker_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, append_event: bool
) -> None:
    capture = tmp_path / "file-opens-relay.json"
    capture.write_bytes(b'{"path":"audit-positive-relay"}\n')
    (tmp_path / "file-opens-relay.pid").write_text("123\n")
    (tmp_path / "file-opens-relay.err").touch()
    (tmp_path / "audit-positive-relay").touch()
    gate = RELAY["capture_gate"]
    monkeypatch.setitem(gate.__globals__, "CAPTURE_HOME", tmp_path)
    monkeypatch.setitem(gate.__globals__, "checked", lambda *_args: "123\n")

    def wait_once(predicate: Callable[[], bool], _deadline: float, _label: str) -> None:
        if append_event:
            with capture.open("ab") as stream:
                stream.write(b'{"path":"audit-positive-relay"}\n')
        if not predicate():
            raise TimeoutError("capture positive control")

    monkeypatch.setitem(gate.__globals__, "wait_for", wait_once)
    if append_event:
        gate()
    else:
        with pytest.raises(TimeoutError, match="capture positive control"):
            gate()


@pytest.mark.socket
def test_stale_gateway_socket_is_removed() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        gateway = Path(directory) / "gateway.sock"
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(gateway))
        assert gateway.is_socket()
        RELAY["clear_stale_gateway"](gateway)
        assert not gateway.exists()


@pytest.mark.socket
def test_held_gateway_socket_is_refused() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        gateway = Path(directory) / "gateway.sock"
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(gateway))
            listener.listen()
            with pytest.raises(RuntimeError, match="held by a process"):
                RELAY["clear_stale_gateway"](gateway)
            assert gateway.is_socket()


def test_version_uses_empty_environment_and_disposable_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_checked(*args: str) -> str:
        calls.append(args)
        return "version\n"

    monkeypatch.setitem(RELAY["version"].__globals__, "checked", fake_checked)
    assert RELAY["version"](Path("/claude"), tmp_path, "--version") == "version\n"
    assert calls == [
        (
            "/usr/bin/env",
            "-i",
            f"HOME={tmp_path}",
            f"CODEX_HOME={tmp_path / 'codex'}",
            f"CLAUDE_CONFIG_DIR={tmp_path / 'claude'}",
            "PATH=/usr/bin:/bin",
            "/claude",
            "--version",
        )
    ]


def test_terminate_does_not_signal_reused_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        RELAY["terminate"].__globals__, "process_start", lambda _pid: "later"
    )

    def no_descendants(_pid: int) -> list[int]:
        pytest.fail("reused PID must not be traversed")

    monkeypatch.setitem(RELAY["terminate"].__globals__, "descendants", no_descendants)
    RELAY["terminate"](None, 12345, "earlier")


def test_checked_bounds_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        args: tuple[str, ...],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        assert (args, check, capture_output, text, timeout) == (
            ("tool",),
            True,
            True,
            True,
            30,
        )
        return subprocess.CompletedProcess(args, 0, "ok")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert RELAY["checked"]("tool") == "ok"


def test_cleanup_continues_after_tmux_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    cell_type = RELAY["Cell"]
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        home = Path(directory)
        evidence = home / "evidence"
        (home / "relay-run").mkdir()

        set_cell_paths(monkeypatch, cell_type, home, evidence)
        cell = cell_type("claude-interactive", tmux_started=True, run_owned=True)
        cell.listener = SimpleNamespace(pid=101)
        cell.model = SimpleNamespace(pid=102)
        stopped: list[int] = []

        def fake_terminate(
            _process: object, root: int | None, _start: str | None = None
        ) -> None:
            if root is not None:
                stopped.append(root)

        def failed_tmux(*_args: str) -> str:
            raise subprocess.CalledProcessError(1, "tmux")

        monkeypatch.setitem(cell_type.cleanup.__globals__, "terminate", fake_terminate)
        monkeypatch.setitem(cell_type.cleanup.__globals__, "checked", failed_tmux)
        assert not cell.cleanup("passed", "connected")
        assert stopped == [101, 102]
        assert (evidence / "summary.json").is_file()
        assert "cleanup:" in (evidence / "summary.json").read_text()


@pytest.mark.socket
def test_preflight_rejection_preserves_existing_socket_and_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cell_type = RELAY["Cell"]
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        home = Path(directory)
        evidence = home / "evidence"
        run = home / "relay-run"
        run.mkdir()
        evidence.mkdir()
        prior = '{"status":"passed"}\n'
        (run / "summary.json").write_text(prior)
        (evidence / "summary.json").write_text(prior)
        (home / "workspace").mkdir()
        gateway = home / "gateway.sock"
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(gateway))
            listener.listen()

            set_cell_paths(monkeypatch, cell_type, home, evidence)
            monkeypatch.setitem(
                cell_type.preflight.__globals__, "capture_gate", lambda: None
            )
            with pytest.raises(SystemExit):
                RELAY["run_cell"]("codex-headless")
            assert gateway.is_socket()
            assert (run / "summary.json").read_text() == prior
            assert (evidence / "summary.json").read_text() == prior
