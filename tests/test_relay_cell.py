"""Configuration checks for the four BV-01 relay cells."""

import runpy
import socket
import tempfile
import tomllib
from pathlib import Path

import pytest

from agent_orchestration_poc.core.host_socket_attribution import (
    claude_settings,
    claude_trust,
    codex_config,
    launch_command,
    relay_result,
)

REPOSITORY = Path(__file__).resolve().parents[1]
if REPOSITORY.name == "mutants":
    REPOSITORY = REPOSITORY.parent
EXPERIMENT = REPOSITORY / "experiments/02-host-socket-attribution"
RELAY = runpy.run_path(str(EXPERIMENT / "relay_cell.py"))


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
        profile, 43210, home, Path("/codex"), Path("/python/bin/python3")
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
            "claude",
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
            }
        )
    assert argv == expected_argv
    assert env == expected_env
    if profile.startswith("claude-"):
        assert claude_settings(home) == {
            "sandbox": {
                "enabled": True,
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

            def cell_home(self: object) -> Path:
                return home

            def cell_evidence(self: object) -> Path:
                return evidence

            monkeypatch.setattr(cell_type, "home", property(cell_home))
            monkeypatch.setattr(cell_type, "evidence", property(cell_evidence))
            monkeypatch.setitem(
                cell_type.preflight.__globals__, "capture_gate", lambda: None
            )
            with pytest.raises(SystemExit):
                RELAY["run_cell"]("codex-headless")
            assert gateway.is_socket()
            assert (run / "summary.json").read_text() == prior
            assert (evidence / "summary.json").read_text() == prior
