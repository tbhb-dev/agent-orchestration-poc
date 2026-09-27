"""Exercise the report-file fallback in an isolated temporary directory."""

import json
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    """Capture atomic replacement, stale generation, and interrupted writing."""
    with tempfile.TemporaryDirectory(
        prefix="exp214-report-", dir="/private/tmp"
    ) as directory:
        root = Path(directory)
        final = root / "report.json"
        temporary = root / "report.json.tmp"
        old = {
            "schema": 1,
            "run_id": "run-1",
            "generation": "gen-1",
            "state": "finished",
            "observed_at": "2020-01-01T00:00:00Z",
        }
        new = {
            "schema": 1,
            "run_id": "run-2",
            "generation": "gen-2",
            "state": "finished",
            "observed_at": datetime.now(tz=UTC).isoformat(),
        }
        final.write_text(json.dumps(old))
        print(
            json.dumps(
                {
                    "at": datetime.now(tz=UTC).isoformat(),
                    "case": "stale",
                    "expected": "gen-2",
                    "report": json.loads(final.read_text()),
                }
            ),
            flush=True,
        )
        temporary.write_text('{"schema":1,"run_id":"run-2"')
        print(
            json.dumps(
                {
                    "at": datetime.now(tz=UTC).isoformat(),
                    "case": "before-rename",
                    "final": json.loads(final.read_text()),
                    "temporary_complete": False,
                }
            ),
            flush=True,
        )
        temporary.write_text(json.dumps(new))
        temporary.replace(final)
        print(
            json.dumps(
                {
                    "at": datetime.now(tz=UTC).isoformat(),
                    "case": "after-rename",
                    "final": json.loads(final.read_text()),
                    "temporary_exists": temporary.exists(),
                }
            ),
            flush=True,
        )
        child = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import time; Path('report.json.tmp').write_text('{\"schema\":1'); time.sleep(60)",
            ],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 5
        while not temporary.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        child.kill()
        child.wait(timeout=5)
        print(
            json.dumps(
                {
                    "at": datetime.now(tz=UTC).isoformat(),
                    "case": "writer-killed",
                    "writer_returncode": child.returncode,
                    "final": json.loads(final.read_text()),
                    "temporary_complete": False,
                    "temporary_exists": temporary.exists(),
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
