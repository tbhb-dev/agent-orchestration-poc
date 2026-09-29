"""Configuration checks for the four BV-01 relay cells."""

import runpy
import tomllib
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]
if REPOSITORY.name == "mutants":
    REPOSITORY = REPOSITORY.parent
EXPERIMENT = REPOSITORY / "experiments/02-host-socket-attribution"
RELAY = runpy.run_path(str(EXPERIMENT / "relay_cell.py"))


@pytest.mark.parametrize("profile", ["codex-headless", "codex-interactive"])
def test_codex_profile_reads_only_disposable_workspace_and_python(profile: str) -> None:
    config = tomllib.loads(RELAY["codex_config"](profile, 43210))
    home = Path(f"/private/tmp/bv01-228-{profile}")
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
    config = RELAY["claude_trust"](workspace)
    assert config == {
        "hasCompletedOnboarding": True,
        "theme": "dark",
        "projects": {str(workspace): {"hasTrustDialogAccepted": True}},
    }
