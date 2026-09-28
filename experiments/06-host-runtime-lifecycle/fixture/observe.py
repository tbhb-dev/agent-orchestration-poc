"""Fresh, read-only controller observer for one disposable harness home."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from .lifecycle_core import (  # pyrefly: ignore[missing-import]
    PROFILES,
    Record,
    process_state,
    retained_state,
    validate,
)


def inventory(root: Path) -> dict[str, str]:
    """Fingerprint regular files below one profile's private harness-state root."""
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            relative = path.relative_to(root).as_posix()
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def current_start(pid: int) -> str | None:
    """Read the current instance start time from the host process table."""
    observed = subprocess.run(
        ["ps", "-p", str(pid), "-o", "lstart="],
        capture_output=True,
        text=True,
        check=False,
    )
    return observed.stdout.strip() if observed.returncode == 0 else None


def observe(home: Path, baseline: Path | None) -> dict[str, object]:
    """Read only the named home and return an evidence-safe observation."""
    profile = home.name.removeprefix("bv01-228-")
    if profile not in PROFILES or home != Path(f"/private/tmp/bv01-228-{profile}"):
        raise ValueError("home is not one of the four approved paths")
    raw = json.loads((home / "lifecycle.json").read_text())
    record = Record(**raw)
    if not validate(record) or record.profile != profile:
        raise ValueError("invalid or mismatched lifecycle record")
    state_root = home / ("codex" if profile.startswith("codex-") else "claude")
    state = inventory(state_root)
    old: dict[str, str] = (
        json.loads(baseline.read_text())["private_state"] if baseline else {}
    )
    return {
        "profile": profile,
        "workload_id": record.workload_id,
        "incarnation": record.incarnation,
        "conversation_id": record.conversation_id,
        "pid": record.pid,
        "process": process_state(record, current_start(record.pid)),
        "private_file_count": len(state),
        "private_state": state,
        "retention": retained_state(old, state),
        "terminal": "separate tmux observation required"
        if profile.endswith("interactive")
        else "not applicable",
        "sandbox_name": None,
        "vm_id": None,
    }


def main() -> None:
    """Print one observer snapshot from an independent process."""
    parser = argparse.ArgumentParser()
    parser.add_argument("home", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    print(json.dumps(observe(args.home, args.baseline), sort_keys=True))


if __name__ == "__main__":
    main()
