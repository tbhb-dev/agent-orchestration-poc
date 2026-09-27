"""Temporary #176 file registry; #28 replaces this scaffold."""

import json
import os
from pathlib import Path
from typing import Any, cast

SCHEMA = 1


def read(path: Path) -> list[dict[str, Any]]:
    """Read the local registry without recovering malformed state as empty."""
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if data.get("version") != SCHEMA or not isinstance(data.get("runs"), list):
        raise ValueError("unsupported or invalid registry schema")
    return cast("list[dict[str, Any]]", data["runs"])


def write(path: Path, rows: list[dict[str, Any]]) -> None:
    """Replace a registry snapshot atomically with owner-only permissions."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    draft = path.with_suffix(".tmp")
    fd = os.open(draft, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump({"version": SCHEMA, "runs": rows}, stream, indent=2)
        stream.write("\n")
    draft.replace(path)


def read_status(path: Path) -> dict[str, Any] | None:
    """Read a worker status snapshot if one exists."""
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise TypeError("invalid status snapshot")
    return data
