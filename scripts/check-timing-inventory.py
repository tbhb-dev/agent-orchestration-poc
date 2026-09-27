"""Compare the configured task and hook inventory with local records."""

import sqlite3
import sys
import tomllib
from contextlib import closing
from pathlib import Path

from agent_orchestration_poc.core.check_timings import inventory_missing
from agent_orchestration_poc.shell.check_timings import store_path


def main() -> int:
    """Return failure if a configured mechanical check lacks a stored run."""
    root = Path(__file__).resolve().parent.parent
    tasks_toml = tomllib.loads((root / "mise.toml").read_text())
    hooks_toml = tomllib.loads((root / "prek.toml").read_text())
    tasks = {name: task.get("run") for name, task in tasks_toml["tasks"].items()}
    hooks = {
        hook["id"]: hook["entry"]
        for repo in hooks_toml["repos"]
        for hook in repo["hooks"]
    }
    try:
        with closing(
            sqlite3.connect(f"file:{store_path()}?mode=ro", uri=True)
        ) as connection:
            recorded = [
                row[0]
                for row in connection.execute("SELECT DISTINCT name FROM local_checks")
            ]
    except (OSError, sqlite3.Error, ValueError) as error:
        sys.stderr.write(f"timing store unavailable: {error}\n")
        return 1
    missing = inventory_missing(tasks, hooks, recorded)
    for name in missing:
        sys.stderr.write(f"missing timing: {name}\n")
    sys.stdout.write(
        f"{len(tasks)} tasks, {len(hooks)} hooks, {len(missing)} missing\n"
    )
    return int(bool(missing))


if __name__ == "__main__":
    raise SystemExit(main())
