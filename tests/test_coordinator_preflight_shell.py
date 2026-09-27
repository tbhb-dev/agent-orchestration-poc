"""Process checks for coordinator preflight commands."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.mark.integration
def test_wait_check_bounds_stalled_github_cli(tmp_path: Path) -> None:
    gh = tmp_path / "gh"
    gh.write_text(
        '#!/bin/sh\nsleep 2\nprintf \'{"headRefOid":"abc","statusCheckRollup":[]}\'\n'
    )
    gh.chmod(0o755)
    started = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent_orchestration_poc.shell.coordinator_preflight",
            "wait-check",
            "85",
            "check",
            "1",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        timeout=5,
        check=False,
    )
    assert result.returncode == 1
    assert time.monotonic() - started < 2
