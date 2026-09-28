"""Thin process shell for a reviewed disposable host harness cell."""

import argparse
import os
import time
from pathlib import Path

from .launch_core import launch_spec  # pyrefly: ignore[missing-import]
from .lifecycle_core import PROFILES  # pyrefly: ignore[missing-import]


def main() -> None:
    """Write launch-root identity, wait for the listener, then replace this PID."""
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("phase", choices=("initial", "resume"))
    parser.add_argument("slot", choices=("A", "B"))
    args = parser.parse_args()
    home = Path(f"/private/tmp/bv01-228-{args.profile}")
    conversation_id = (
        (home / "conversation-id").read_text().strip()
        if args.phase == "resume"
        else None
    )
    port = (
        int((home / "model-port").read_text().strip())
        if args.profile.startswith("claude-")
        else None
    )
    spec = launch_spec(args.profile, args.phase, args.slot, conversation_id, port)
    Path(spec.root_file).write_text(f"{os.getpid()}\n")
    while not Path(spec.go_file).exists():
        time.sleep(0.05)
    os.chdir(spec.workspace)
    os.execvpe(spec.argv[0], spec.argv, spec.env)  # noqa: S606 - reviewed harness command replaces the wrapper


if __name__ == "__main__":
    main()
