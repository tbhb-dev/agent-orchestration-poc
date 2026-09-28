"""Write one disposable incarnation record from a running harness root."""

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from .lifecycle_core import (  # pyrefly: ignore[missing-import]
    PROFILES,
    Record,
    validate,
)
from .observe import current_start  # pyrefly: ignore[missing-import]


def main() -> None:
    """Write the root process identity inside its approved profile home."""
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("workload_id")
    parser.add_argument("incarnation")
    parser.add_argument("conversation_id")
    parser.add_argument("--update-conversation", action="store_true")
    args = parser.parse_args()
    home = Path(f"/private/tmp/bv01-228-{args.profile}")
    if args.update_conversation:
        path = home / "lifecycle.json"
        saved = Record(**json.loads(path.read_text()))
        if (
            saved.profile != args.profile
            or saved.workload_id != args.workload_id
            or saved.incarnation != args.incarnation
        ):
            parser.error("saved incarnation differs")
        updated = replace(saved, conversation_id=args.conversation_id)
        if not validate(updated):
            parser.error("invalid conversation ID")
        path.write_text(json.dumps(asdict(updated)) + "\n")
        return
    pid = int((home / "root.pid").read_text().strip())
    start = current_start(pid)
    if start is None:
        parser.error("recorded root process is absent")
    record = Record(
        args.profile,
        args.workload_id,
        args.incarnation,
        args.conversation_id,
        pid,
        start,
    )
    if not validate(record):
        parser.error("incomplete identity")
    (home / "lifecycle.json").write_text(json.dumps(asdict(record)) + "\n")


if __name__ == "__main__":
    main()
