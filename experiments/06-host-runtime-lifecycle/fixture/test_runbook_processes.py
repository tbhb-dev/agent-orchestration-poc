"""Stand-in for the runbook's supervisor and workload PID handling."""

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.integration
def test_supervisor_wait_and_listener_owner(tmp_path: Path) -> None:
    """The socket owner is Python, while the launching shell waits on uv."""
    if shutil.which("lsof") is None:
        pytest.skip("lsof is unavailable")
    script = """
set -eu
mise exec -- uv run python -u -c 'import json,os,socket,time; s=socket.socket(); s.bind(("127.0.0.1",0)); s.listen(); print(json.dumps({"pid":os.getpid(),"port":s.getsockname()[1]}),flush=True); time.sleep(30)' > "$1/start.json" &
supervisor_pid=$!
trap 'kill "$supervisor_pid" 2>/dev/null || :; wait "$supervisor_pid" 2>/dev/null || :' EXIT
while test ! -s "$1/start.json"; do sleep 0.05; done
responder_pid=$(mise exec -- python -c 'import json,sys; print(json.load(open(sys.argv[1]))["pid"])' "$1/start.json")
lsof -nP -a -p "$responder_pid" -iTCP >/dev/null
kill "$responder_pid"
kill "$supervisor_pid"
wait "$supervisor_pid" || :
trap - EXIT
mise exec -- uv run python -c 'raise SystemExit(7)' &
launch_job_pid=$!
if wait "$launch_job_pid"; then exit 1; else result=$?; fi
test "$result" -eq 7
"""
    result = subprocess.run(
        ["sh", "-c", script, "sh", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=45,
    )
    assert result.returncode == 0, result.stderr  # noqa: S101 - pytest assertion
