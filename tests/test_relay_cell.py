"""Configuration checks for the four BV-01 relay cells."""

import runpy
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agent_orchestration_poc.core.host_socket_attribution import (
    claude_settings,
    claude_theme_choice,
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


def interactive_cell(monkeypatch: pytest.MonkeyPatch, home: Path) -> Any:  # noqa: ANN401 - runpy class
    """Create an interactive cell with an owned test run directory."""
    (home / "relay-run-r8").mkdir()
    cell_type = RELAY["Cell"]
    set_cell_paths(monkeypatch, cell_type, home, home / "evidence")
    return cell_type("claude-interactive", tmux_started=True)


@pytest.mark.parametrize("profile", ["codex-headless", "codex-interactive"])
def test_codex_profile_reads_platform_defaults_workspace_and_python(
    profile: str,
) -> None:
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
    denied = {
        str(home / "relay-run-r2"): "deny",
        str(home / "relay-run-r3"): "deny",
        str(home / "relay-run-r4"): "deny",
        str(home / "relay-run-r5"): "deny",
        str(home / "relay-run-r6"): "deny",
        str(home / "codex"): "deny",
        **{
            f"/private/tmp/bv01-228-{other}": "deny"
            for other in (
                "codex-headless",
                "codex-interactive",
                "claude-headless",
                "claude-interactive",
            )
            if other != profile
        },
    }
    if profile == "codex-headless":
        denied.update(
            {
                str(home / name): "deny"
                for name in (
                    "file-opens-relay-r2.json",
                    "file-opens-relay-r2.pid",
                    "file-opens-relay-r2.err",
                    "audit-positive-relay-r2",
                    "file-opens-relay-r6.json",
                    "file-opens-relay-r6.pid",
                    "file-opens-relay-r6.err",
                    "audit-positive-relay-r6",
                )
            }
        )
    assert config["default_permissions"] == "bv01"
    assert config["permissions"]["bv01"]["filesystem"] == {
        ":minimal": "read",
        str(workspace): "read",
        str(python): "read",
        **denied,
    }
    assert config["permissions"]["bv01"]["network"]["unix_sockets"] == {
        str(home / "gateway.sock"): "allow"
    }
    assert config["projects"][str(workspace)]["trust_level"] == "trusted"
    assert config["tui"]["screen_reader_detection_done"] is True
    assert config["tui"]["disable_paste_burst"] is True


@pytest.mark.parametrize("profile", ["claude-headless", "claude-interactive"])
def test_claude_trust_is_scoped_to_cell_workspace(profile: str) -> None:
    workspace = Path(f"/private/tmp/bv01-228-{profile}/workspace")
    config = claude_trust(workspace)
    assert config == {
        "hasCompletedOnboarding": True,
        "theme": "dark",
        "customApiKeyResponses": {"approved": ["not-a-real-key"], "rejected": []},
        "projects": {str(workspace): {"hasTrustDialogAccepted": True}},
    }


@pytest.mark.parametrize(
    "profile",
    ["codex-headless", "codex-interactive", "claude-headless", "claude-interactive"],
)
def test_launch_configuration(profile: str) -> None:
    home = Path(f"/private/tmp/bv01-228-{profile}")
    workspace = home / "workspace"
    prompt_python = "/python/bin/python3" if profile.startswith("codex-") else "python3"
    prompt = (
        f"Run {prompt_python} experiments/02-host-socket-attribution/probe.py client "
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
        "PATH": "/python/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
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
        else:
            expected_argv += ["--permission-mode", "manual"]
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


def model_rows(profile: str) -> list[dict[str, object]]:
    side = f"{'codex' if profile.startswith('codex-') else 'claude'}-side.sse"
    return [
        {"status": 200, "fixture": side, "classification": "side-request"},
        {"status": 200, "fixture": f"{profile}-tool.sse", "classification": "tool"},
        {"status": 200, "fixture": side, "classification": "retry"},
        {"status": 200, "fixture": f"{profile}-final.sse", "classification": "final"},
        {"status": 200, "fixture": side, "classification": "follow-up"},
    ]


@pytest.mark.parametrize(
    "profile",
    ["codex-interactive", "claude-interactive", "codex-headless", "claude-headless"],
)
def test_relay_result_accepts_one_tool_and_final_with_side_requests(
    profile: str,
) -> None:
    assert (
        relay_result(
            model_rows(profile),
            [{"peer": {"pid": 42}, "decision": "allowed"}],
            0,
            profile,
        )
        == "peer=42 decision=allowed requests=5 side_requests=3"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate-tool",
        "duplicate-final",
        "missing-tool",
        "missing-final",
        "wrong-order",
    ],
)
def test_relay_result_requires_exactly_one_ordered_pair(mutation: str) -> None:
    rows = model_rows("codex-interactive")
    if mutation == "duplicate-tool":
        rows.insert(2, rows[1].copy())
    elif mutation == "duplicate-final":
        rows.append(rows[3].copy())
    elif mutation == "missing-tool":
        rows.pop(1)
    elif mutation == "missing-final":
        rows.pop(3)
    else:
        rows[1], rows[3] = rows[3], rows[1]
    with pytest.raises(ValueError, match="tool and final"):
        relay_result(
            rows, [{"peer": {"pid": 42}, "decision": "allowed"}], 0, "codex-interactive"
        )


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ("status", "responder refused"),
        ("requests", "exactly one"),
        ("exit", "exited 2"),
        ("decision", "did not allow"),
    ],
)
def test_relay_result_rejects_bad_outcome(change: str, error: str) -> None:
    rows = model_rows("codex-interactive")
    requests: list[dict[str, object]] = [{"peer": {"pid": 42}, "decision": "allowed"}]
    exit_code = 0
    if change == "status":
        rows[0]["status"] = 403
    elif change == "requests":
        requests = []
    elif change == "exit":
        exit_code = 2
    else:
        requests[0]["decision"] = "blocked"
    with pytest.raises(ValueError, match=error):
        relay_result(rows, requests, exit_code, "codex-interactive")


@pytest.mark.parametrize("marker", ["❯", "›"])
def test_only_bare_input_prompt_is_ready(marker: str) -> None:
    assert empty_input_prompt(f"header\n {marker} \nfooter", marker)
    assert not empty_input_prompt(f"header\n {marker} No, exit\nfooter", marker)


def test_codex_fresh_thread_placeholder_is_ready() -> None:
    pane = (EXPERIMENT / "fixtures/codex-fresh-thread-header.snap").read_text()
    assert empty_input_prompt(pane, "›")
    assert not empty_input_prompt("Codex\n› No, exit\n", "›")


def test_claude_empty_prompt_hint_is_ready() -> None:
    assert empty_input_prompt('❯ Try "..."', "❯")
    assert empty_input_prompt('Claude\n❯ Try "write a unit test"\n', "❯")
    assert not empty_input_prompt("Claude\n❯ No, exit\n", "❯")


CLAUDE_THEME_PANE = """Welcome to Claude Code v2.1.284
 Let's get started.
 Choose the text style that looks best with your terminal
 To change this later, run /theme
   1. Auto (match terminal)
 ❯ 2. Dark mode ✔
   3. Light mode
"""


def test_claude_theme_choice_requires_exact_dialog() -> None:
    assert claude_theme_choice(CLAUDE_THEME_PANE)
    assert claude_theme_choice(
        CLAUDE_THEME_PANE.replace(
            "Welcome to Claude Code v2.1.284", "Welcome!"
        ).replace("Let's get started.", "Ready to begin.")
    )
    assert not claude_theme_choice(
        CLAUDE_THEME_PANE.replace("Dark mode ✔", "Light mode ✔")
    )
    assert not claude_theme_choice("❯ 2. Dark mode ✔\n")
    assert not claude_theme_choice(CLAUDE_THEME_PANE + "❯ Yes, trust this folder\n")


@pytest.mark.parametrize(
    ("profile", "screens"),
    [
        (
            "claude-interactive",
            [CLAUDE_THEME_PANE, 'Claude\n❯ Try "write a unit test"\n'],
        ),
        (
            "codex-interactive",
            [
                "model: loading\n› Ask Codex to do anything\n",
                "model: bv01\n› Ask Codex to do anything\n",
            ],
        ),
    ],
)
def test_interactive_prompt_handling(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    profile: str,
    screens: list[str],
) -> None:
    cell_type = RELAY["Cell"]
    run = tmp_path / "relay-run-r8"
    run.mkdir()
    set_cell_paths(monkeypatch, cell_type, tmp_path, tmp_path / "evidence")
    cell = cell_type(profile, tmux_started=True)
    panes = iter(screens)
    calls: list[tuple[str, ...]] = []

    def fake_checked(*args: str) -> str:
        calls.append(args)
        if "capture-pane" in args:
            return next(panes, f"{('›' if profile.startswith('codex-') else '❯')}\n")
        return ""

    monkeypatch.setitem(
        cell_type.prompt_interactive.__globals__, "checked", fake_checked
    )
    cell.prompt_interactive(time.monotonic() + 5)
    assert (run / "pane-before-prompt.txt").is_file()
    sent = [call for call in calls if "send-keys" in call]
    assert all(call[:3] == ("tmux", "-S", str(RELAY["TMUX_SOCKET"])) for call in sent)
    if profile.startswith("claude-"):
        assert (run / "pane-theme-choice.txt").read_text() == CLAUDE_THEME_PANE
        assert [call[-1] for call in sent[::2]] == ["Enter", "Enter"]
        prompt_call = sent[1]
    else:
        assert not (run / "pane-theme-choice.txt").exists()
        assert sent[-1][-1] == "Enter"
        prompt_call = sent[0]
    python = str(RELAY["PYTHON"]) if profile.startswith("codex-") else "python3"
    assert prompt_call[-1] == (
        f"Run {python} experiments/02-host-socket-attribution/probe.py client "
        f"{tmp_path}/gateway.sock {profile} and then stop."
    )


def test_interactive_paths_use_r8() -> None:
    cell = RELAY["Cell"]("codex-interactive")
    assert cell.run == Path("/private/tmp/bv01-228-codex-interactive/relay-run-r8")
    assert cell.evidence == EXPERIMENT / "evidence/relay-run-r8/codex-interactive"


@pytest.mark.parametrize("profile", ["codex-interactive", "claude-interactive"])
def test_prompt_waits_between_text_and_enter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile: str
) -> None:
    cell_type = RELAY["Cell"]
    (tmp_path / "relay-run-r8").mkdir()
    set_cell_paths(monkeypatch, cell_type, tmp_path, tmp_path / "evidence")
    cell = cell_type(profile, tmux_started=True)
    events: list[str] = []
    marker = "›" if profile.startswith("codex-") else "❯"

    def fake_checked(*args: str) -> str:
        if "capture-pane" in args:
            return f"{marker}\n"
        if "send-keys" in args:
            events.append(args[-1])
        return ""

    monkeypatch.setitem(cell.prompt_interactive.__globals__, "checked", fake_checked)

    def record_sleep(seconds: float) -> None:
        events.append(f"sleep:{seconds}")

    monkeypatch.setattr(time, "sleep", record_sleep)
    cell.prompt_interactive(time.monotonic() + 5)
    python = str(RELAY["PYTHON"]) if profile.startswith("codex-") else "python3"
    assert events[-3:] == [
        (
            f"Run {python} experiments/02-host-socket-attribution/probe.py client "
            f"{tmp_path}/gateway.sock {profile} and then stop."
        ),
        "sleep:0.5",
        "Enter",
    ]


def test_model_request_confirms_interactive_submission(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cell = interactive_cell(monkeypatch, tmp_path)
    (cell.run / "model.jsonl").touch()
    monkeypatch.setitem(
        cell.require_submission.__globals__,
        "checked",
        lambda *_args: pytest.fail("pane should not be read after model request"),
    )
    cell.require_submission(time.monotonic() + 5, "❯")


@pytest.mark.parametrize("profile", ["codex-interactive", "claude-interactive"])
def test_unsubmitted_prompt_saves_pane(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile: str
) -> None:
    cell_type = RELAY["Cell"]
    run = tmp_path / "relay-run-r8"
    run.mkdir()
    set_cell_paths(monkeypatch, cell_type, tmp_path, tmp_path / "evidence")
    cell = cell_type(profile, tmux_started=True)
    marker = "›" if profile.startswith("codex-") else "❯"
    ready = "› Ask Codex to do anything\n" if marker == "›" else '❯ Try "..."\n'
    stuck = f"{marker} Run probe and then stop.\n"
    panes = iter([ready, stuck])

    def fake_checked(*args: str) -> str:
        return next(panes, stuck) if "capture-pane" in args else ""

    def timed_out(predicate: Callable[[], bool], deadline: float, label: str) -> None:
        assert deadline <= time.monotonic() + 30
        assert label == "interactive prompt was not submitted"
        assert not predicate()
        raise TimeoutError(label)

    monkeypatch.setitem(cell.prompt_interactive.__globals__, "checked", fake_checked)
    monkeypatch.setitem(cell.prompt_interactive.__globals__, "wait_for", timed_out)
    with pytest.raises(TimeoutError, match="interactive prompt was not submitted"):
        cell.prompt_interactive(time.monotonic() + 60)
    assert (run / "pane-submit-timeout.txt").read_text() == stuck


def test_persistent_theme_screen_gets_one_enter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cell = interactive_cell(monkeypatch, tmp_path)
    calls: list[tuple[str, ...]] = []

    def fake_checked(*args: str) -> str:
        calls.append(args)
        return CLAUDE_THEME_PANE if "capture-pane" in args else ""

    monkeypatch.setitem(cell.prompt_interactive.__globals__, "checked", fake_checked)
    with pytest.raises(TimeoutError, match="input prompt did not appear"):
        cell.prompt_interactive(time.monotonic() + 0.25)
    assert [call[-1] for call in calls if "send-keys" in call] == ["Enter"]
    assert (
        tmp_path / "relay-run-r8/pane-prompt-timeout.txt"
    ).read_text() == CLAUDE_THEME_PANE


@pytest.mark.parametrize(
    ("pane", "name", "message"),
    [
        ("Accessing workspace:\n", "pane-trust-prompt.txt", "workspace trust"),
        ("Sign in\n", "pane-credential-prompt.txt", "credential prompt"),
        ("Pane is dead\n", "pane-dead.txt", "harness pane exited"),
    ],
)
def test_interactive_stop_saves_pane(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    pane: str,
    name: str,
    message: str,
) -> None:
    cell = interactive_cell(monkeypatch, tmp_path)
    monkeypatch.setitem(
        cell.prompt_interactive.__globals__, "checked", lambda *_args: pane
    )
    with pytest.raises(RuntimeError, match=message):
        cell.prompt_interactive(time.monotonic() + 5)
    assert (tmp_path / "relay-run-r8" / name).read_text() == pane


def test_observe_timeout_saves_pane_before_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cell = interactive_cell(monkeypatch, tmp_path)
    cell.listener = SimpleNamespace(poll=lambda: None)
    cell.harness = SimpleNamespace(poll=lambda: None)
    calls: list[tuple[str, ...]] = []

    def fake_checked(*args: str) -> str:
        calls.append(args)
        return "Waiting for permission\n"

    def timed_out(*_args: object) -> None:
        raise TimeoutError("cell completion before 540 seconds")

    monkeypatch.setitem(cell.observe.__globals__, "checked", fake_checked)
    monkeypatch.setitem(cell.observe.__globals__, "wait_for", timed_out)
    with pytest.raises(TimeoutError, match="cell completion"):
        cell.observe(time.monotonic() + 5)
    assert (
        tmp_path / "relay-run-r8/pane-observe-timeout.txt"
    ).read_text() == "Waiting for permission\n"
    assert calls == [
        (
            "tmux",
            "-S",
            str(RELAY["TMUX_SOCKET"]),
            "capture-pane",
            "-p",
            "-S",
            "-2000",
            "-t",
            "bv01:claude-interactive",
        )
    ]


def test_prompt_timeout_saves_last_pane(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cell = interactive_cell(monkeypatch, tmp_path)
    monkeypatch.setitem(
        cell.prompt_interactive.__globals__,
        "checked",
        lambda *_args: "Waiting...\n",
    )
    with pytest.raises(TimeoutError, match="input prompt did not appear"):
        cell.prompt_interactive(time.monotonic() + 0.1)
    assert (
        tmp_path / "relay-run-r8/pane-prompt-timeout.txt"
    ).read_text() == "Waiting...\n"


@pytest.mark.parametrize(
    "profile",
    ["codex-headless", "codex-interactive", "claude-headless", "claude-interactive"],
)
@pytest.mark.integration
def test_wrapper_imports_core_outside_venv(profile: str, tmp_path: Path) -> None:
    wrapper = (EXPERIMENT / f"relay-{profile}.sh").read_text()
    setup, command = wrapper.rsplit("\nexec ", 1)
    python = command.split(" experiments/02-host-socket-attribution/relay_cell.py ")[0]
    assert python == str(RELAY["PYTHON"])
    base_python = Path(sys.base_prefix) / "bin/python3"
    import_script = ' -c \'import runpy; runpy.run_path("experiments/02-host-socket-attribution/relay_cell.py", run_name="bv01_import_test")\'\n'
    import_command = setup + "\nexec " + str(base_python) + import_script

    def run_import(command_text: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "/usr/bin/env",
                "-i",
                "PATH=/usr/bin:/bin",
                f"HOME={tmp_path}",
                "/bin/sh",
                "-c",
                command_text,
            ],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    negative = run_import("exec " + str(base_python) + import_script)
    assert negative.returncode != 0
    assert "No module named 'agent_orchestration_poc'" in negative.stderr
    result = run_import(import_command)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("append_event", [False, True])
def test_capture_gate_requires_event_after_marker_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, append_event: bool
) -> None:
    capture = tmp_path / "file-opens-relay-r8.json"
    capture.write_bytes(b'{"path":"audit-positive-relay-r8"}\n')
    (tmp_path / "file-opens-relay-r8.pid").write_text("123\n")
    (tmp_path / "file-opens-relay-r8.err").touch()
    (tmp_path / "audit-positive-relay-r8").touch()
    gate = RELAY["capture_gate"]
    monkeypatch.setitem(gate.__globals__, "CAPTURE_HOME", tmp_path)
    monkeypatch.setitem(gate.__globals__, "checked", lambda *_args: "123\n")

    def wait_once(predicate: Callable[[], bool], _deadline: float, _label: str) -> None:
        if append_event:
            with capture.open("ab") as stream:
                stream.write(b"x" * (1_048_576 + 65_530) + b"audit-positive-relay-r8")
        if not predicate():
            raise TimeoutError("capture positive control")

    monkeypatch.setitem(gate.__globals__, "wait_for", wait_once)
    if append_event:
        gate()
    else:
        with pytest.raises(TimeoutError, match="capture positive control"):
            gate()


def test_capture_gate_refuses_previous_capture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in (
        "file-opens-relay.json",
        "file-opens-relay.pid",
        "file-opens-relay.err",
        "audit-positive-relay",
    ):
        (tmp_path / name).touch()
    gate = RELAY["capture_gate"]
    monkeypatch.setitem(gate.__globals__, "CAPTURE_HOME", tmp_path)
    with pytest.raises(RuntimeError, match="capture files are absent"):
        gate()


@pytest.mark.socket
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS lsof path only")
def test_stale_gateway_socket_is_removed() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        gateway = Path(directory) / "gateway.sock"
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(gateway))
        assert gateway.is_socket()
        RELAY["clear_stale_gateway"](gateway)
        assert not gateway.exists()


@pytest.mark.socket
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS lsof path only")
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
        (home / "relay-run-r8").mkdir()

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


def test_cleanup_saves_pane_before_tmux_shutdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cell_type = RELAY["Cell"]
    run = tmp_path / "relay-run-r8"
    run.mkdir()
    evidence = tmp_path / "evidence"
    set_cell_paths(monkeypatch, cell_type, tmp_path, evidence)
    cell = cell_type("claude-interactive", tmux_started=True, run_owned=True)
    calls: list[tuple[str, ...]] = []

    def fake_checked(*args: str) -> str:
        calls.append(args)
        return "Last pane\n" if "capture-pane" in args else ""

    monkeypatch.setitem(cell_type.cleanup.__globals__, "checked", fake_checked)
    assert cell.cleanup("passed", "connected")
    assert calls[:2] == [
        (
            "tmux",
            "-S",
            str(RELAY["TMUX_SOCKET"]),
            "capture-pane",
            "-p",
            "-S",
            "-2000",
            "-t",
            "bv01:claude-interactive",
        ),
        ("tmux", "-S", str(RELAY["TMUX_SOCKET"]), "kill-server"),
    ]
    assert (run / "pane-at-cleanup.txt").read_text() == "Last pane\n"
    assert (evidence / "pane-at-cleanup.txt").read_text() == "Last pane\n"


@pytest.mark.socket
def test_preflight_rejection_preserves_existing_socket_and_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cell_type = RELAY["Cell"]
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        home = Path(directory)
        evidence = home / "evidence"
        run = home / "relay-run-r8"
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
