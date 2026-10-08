"""Exercise the task wrappers with an isolated Git common directory."""

import os
import subprocess
import tomllib
from pathlib import Path

import pytest

TASKS = (
    "check",
    "check:mutation",
    "check:mutation:go",
    "check:mutation:python",
    "docs:build",
)
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.integration
@pytest.mark.parametrize("task", TASKS)
@pytest.mark.parametrize("installed", [False, True])
@pytest.mark.parametrize("status", [0, 75])
def test_task_wrapper(tmp_path: Path, task: str, installed: bool, status: int) -> None:
    """Preserve task invocation and failure without falling back after failure."""
    config = tomllib.loads((ROOT / "mise.toml").read_text())
    wrapper = config["tasks"][task]
    assert "depends" not in wrapper
    common = tmp_path / "repository with spaces" / ".git"
    common.mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    commands = {
        "git": '#!/bin/sh\nprintf "%s\\n" "$TEST_COMMON"\n',
        "mise": '#!/bin/sh\nprintf "work:%s:%s\\n" "$1" "$2"\nexit "$TEST_STATUS"\n',
    }
    for name, script in commands.items():
        executable = bin_dir / name
        executable.write_text(script)
        executable.chmod(0o755)
    if installed:
        semaphore = common.parent / ".holding" / "bin" / "check-semaphore"
        semaphore.parent.mkdir(parents=True)
        semaphore.write_text(
            '#!/bin/sh\n[ "$1" = -- ] || exit 2\nshift\n'
            'printf "admitted\\n"\nexec "$@"\n'
        )
        semaphore.chmod(0o755)
    result = subprocess.run(
        ["sh", "-ec", wrapper["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "TEST_COMMON": str(common),
            "TEST_STATUS": str(status),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == status
    assert result.stdout == ("admitted\n" if installed else "") + f"work:run:_{task}\n"
    assert result.stderr == (
        "" if installed else f"check-semaphore absent; running {task} unchanged\n"
    )
