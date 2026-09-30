"""Static and mocked checks for the Claude interactive preflight."""

import json
import runpy
import subprocess
from pathlib import Path
from typing import Any

import pytest

from agent_orchestration_poc.core.host_socket_attribution import launch_command

EXPERIMENT = (
    Path(__file__).resolve().parents[1] / "experiments/02-host-socket-attribution"
)
PREFLIGHT = runpy.run_path(str(EXPERIMENT / "preflight_claude_interactive.py"))
THEME = """Choose the text style that looks best with your terminal
To change this later, run /theme
1. Auto (match terminal)
❯ 2. Dark mode ✔
3. Light mode
"""


def test_preflight_seeds_cell_configuration(tmp_path: Path) -> None:
    home = tmp_path / "claude-interactive"
    PREFLIGHT["prepare_home"](home)
    trust = json.loads((home / "claude/.claude.json").read_text())
    settings = json.loads((home / "settings.json").read_text())
    assert trust == {
        "hasCompletedOnboarding": True,
        "theme": "dark",
        "customApiKeyResponses": {"approved": ["not-a-real-key"], "rejected": []},
        "projects": {str(home / "workspace"): {"hasTrustDialogAccepted": True}},
    }
    assert settings == {
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


def test_preflight_launch_argv_matches_cell() -> None:
    home = PREFLIGHT["HOME"]
    argv, _ = launch_command(
        "claude-interactive",
        12345,
        home,
        (PREFLIGHT["CLAUDE"], PREFLIGHT["CLAUDE"], PREFLIGHT["PYTHON"]),
    )
    assert argv == [
        "/Users/tony/.local/share/claude/versions/2.1.284",
        "--bare",
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--settings",
        str(home / "settings.json"),
        "--permission-mode",
        "manual",
    ]


def test_theme_screen_answered_once_before_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, ...]] = []
    panes = iter([THEME, THEME, '❯ Try "something"\n'])

    def fake_checked(*args: str) -> str:
        calls.append(args)
        return next(panes) if "capture-pane" in args else ""

    def fake_wait(predicate: Any, label: str, on_timeout: Any = None) -> None:  # noqa: ANN401 - injected callbacks
        assert label == "Claude interactive input"
        assert not predicate()
        assert not predicate()
        assert predicate()

    monkeypatch.setitem(
        PREFLIGHT["wait_for_input"].__globals__, "checked", fake_checked
    )
    monkeypatch.setitem(PREFLIGHT["wait_for_input"].__globals__, "wait_for", fake_wait)
    PREFLIGHT["wait_for_input"](tmp_path / "tmux.sock", tmp_path)
    assert [call[-1] for call in calls if "send-keys" in call] == ["Enter"]
    assert (tmp_path / "pane-theme-choice.txt").read_text() == THEME
    assert (tmp_path / "pane-before-prompt.txt").is_file()


@pytest.mark.parametrize(
    ("pane", "name", "message"),
    [
        ("Accessing workspace:\n", "pane-trust-prompt.txt", "workspace trust"),
        ("Enter your API key\n", "pane-credential-prompt.txt", "credential prompt"),
    ],
)
def test_unexpected_first_run_screen_is_saved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pane: str, name: str, message: str
) -> None:
    def fake_wait(predicate: Any, label: str, on_timeout: Any = None) -> None:  # noqa: ANN401 - injected callbacks
        predicate()

    monkeypatch.setitem(
        PREFLIGHT["wait_for_input"].__globals__, "checked", lambda *_args: pane
    )
    monkeypatch.setitem(PREFLIGHT["wait_for_input"].__globals__, "wait_for", fake_wait)
    with pytest.raises(RuntimeError, match=message):
        PREFLIGHT["wait_for_input"](tmp_path / "tmux.sock", tmp_path)
    assert (tmp_path / name).read_text() == pane


def test_timeout_and_teardown_capture_pane(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    socket = tmp_path / "tmux.sock"
    socket.touch()

    def fake_checked(*args: str) -> str:
        if "new-session" in args:
            return ""
        if "capture-pane" in args:
            return "stalled pane\n"
        return ""

    def fake_wait(predicate: Any, label: str, on_timeout: Any = None) -> None:  # noqa: ANN401 - injected callbacks
        assert on_timeout is not None
        on_timeout()
        raise TimeoutError(label)

    globals_ = PREFLIGHT["run_interactive"].__globals__
    monkeypatch.setitem(globals_, "checked", fake_checked)
    monkeypatch.setitem(globals_, "wait_for", fake_wait)

    def fake_run(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(TimeoutError, match="Claude interactive input"):
        PREFLIGHT["run_interactive"](
            tmp_path, tmp_path, 12345, tmp_path / "model.jsonl"
        )
    assert (tmp_path / "pane-prompt-timeout.txt").read_text() == "stalled pane\n"
    assert (tmp_path / "pane-at-teardown.txt").read_text() == "stalled pane\n"


def test_run_artifacts_copy_debug_and_transcript(tmp_path: Path) -> None:
    home = tmp_path / "home"
    run = tmp_path / "run"
    run.mkdir()
    debug = home / "claude/debug/session.txt"
    transcript = home / "claude/projects/workspace/session.jsonl"
    debug.parent.mkdir(parents=True)
    transcript.parent.mkdir(parents=True)
    debug.write_text("debug")
    transcript.write_text("transcript")
    PREFLIGHT["save_claude_artifacts"](home, run, 0)
    assert (run / "claude/debug/session.txt").read_text() == "debug"
    assert (run / "claude/projects/workspace/session.jsonl").read_text() == "transcript"
