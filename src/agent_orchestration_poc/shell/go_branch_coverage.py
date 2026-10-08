"""Run gobco against a small copy of the Go core module."""

import os
import shutil
import signal
import subprocess
from pathlib import Path


def stage_core_module(root: Path, destination: Path) -> None:
    """Copy the module files gobco needs without checkout caches or worktrees."""
    for name in ("go.mod", "go.sum"):
        shutil.copy2(root / name, destination / name)
    shutil.copytree(root / "internal/core", destination / "internal/core")


def run_gobco(package: Path, *, timeout_seconds: float) -> str:
    """Return branch output or fail with the package and a bounded diagnostic."""
    with subprocess.Popen(
        ["gobco", "-branch", str(package)],
        cwd=package.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as error:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise RuntimeError(
                f"gobco timed out for {package} after {timeout_seconds:g}s"
            ) from error
        if process.returncode != 0:
            raise RuntimeError(
                f"gobco failed for {package} (exit {process.returncode}): {stderr.strip()}"
            )
        return stdout
