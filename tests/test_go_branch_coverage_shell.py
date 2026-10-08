"""Process tests for the staged Go branch coverage runner."""

import os
import time
from pathlib import Path

import pytest

from agent_orchestration_poc.shell.go_branch_coverage import (
    run_gobco,
    stage_core_module,
)


@pytest.mark.integration
def test_stage_core_module_excludes_checkout_directories(tmp_path: Path) -> None:
    """Keep Go test data while leaving unrelated checkout trees behind."""
    root = tmp_path / "source"
    destination = tmp_path / "staged"
    (root / "internal/core/example/testdata").mkdir(parents=True)
    (root / ".worktrees/worker").mkdir(parents=True)
    (root / "node_modules").mkdir()
    destination.mkdir()
    (root / "go.mod").write_text("module example\n")
    (root / "go.sum").write_text("")
    (root / "internal/core/example/example.go").write_text("package example\n")
    (root / "internal/core/example/testdata/input.txt").write_text("input\n")
    (root / ".worktrees/worker/large.txt").write_text("ignored\n")
    (root / "node_modules/package.js").write_text("ignored\n")

    stage_core_module(root, destination)

    assert (
        destination / "internal/core/example/testdata/input.txt"
    ).read_text() == "input\n"
    assert (destination / "internal/core/example/example.go").is_file()
    assert not (destination / ".worktrees").exists()
    assert not (destination / "node_modules").exists()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("script", "expected"),
    [
        ("echo 'Branch coverage: 2/2'", "Branch coverage: 2/2\n"),
        ("echo 'instrumentation failed' >&2; exit 7", "exit 7"),
    ],
)
def test_run_gobco_reports_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script: str, expected: str
) -> None:
    """Preserve successful output and include a failing subprocess diagnostic."""
    executable = tmp_path / "gobco"
    executable.write_text(f"#!/bin/sh\n{script}\n")
    executable.chmod(0o755)
    package = tmp_path / "core"
    package.mkdir()
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    if "exit 7" in script:
        with pytest.raises(
            RuntimeError, match="gobco failed.*exit 7.*instrumentation failed"
        ):
            run_gobco(package, timeout_seconds=1)
    else:
        assert run_gobco(package, timeout_seconds=1) == expected


@pytest.mark.integration
def test_run_gobco_bounds_stalled_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child held open by gobco cannot keep the coverage step waiting."""
    executable = tmp_path / "gobco"
    executable.write_text("#!/bin/sh\nsleep 30 &\nwait\n")
    executable.chmod(0o755)
    package = tmp_path / "core"
    package.mkdir()
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    started = time.monotonic()
    with pytest.raises(RuntimeError, match="gobco timed out.*after 0.1s"):
        run_gobco(package, timeout_seconds=0.1)
    assert time.monotonic() - started < 3
