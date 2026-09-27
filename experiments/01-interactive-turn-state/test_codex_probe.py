"""Regression test for the disposable Codex app-server probe."""

import runpy
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest


@pytest.mark.integration
def test_receive_times_out_after_partial_line() -> None:
    """A flushed fragment must not hold the reader beyond its deadline."""
    receive = cast(
        "Callable[[subprocess.Popen[bytes], float], dict[str, object]]",
        runpy.run_path(str(Path(__file__).with_name("codex-probe.py")))["receive"],
    )
    child = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-c",
            (
                "import sys, time; sys.stdout.write('{'); sys.stdout.flush(); "
                "time.sleep(0.8); sys.stdout.write('}\\n'); sys.stdout.flush()"
            ),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )
    try:
        with pytest.raises(TimeoutError, match="app-server response deadline"):
            receive(child, time.monotonic() + 0.1)
    finally:
        child.terminate()
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=2)
        if child.stdout is not None:
            child.stdout.close()
