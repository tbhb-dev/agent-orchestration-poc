#!/usr/bin/env python3
"""Poll a controlled rollout; record persistence time/types, not private content."""
import argparse
import json
import re
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("path", type=Path)
ap.add_argument("--seconds", type=float, default=90)
ap.add_argument("--output", type=Path, required=True)
args = ap.parse_args()
end = time.monotonic()+args.seconds
with args.path.open("rb") as source, args.output.open("w") as dest:
    source.seek(0, 2)
    pending = b""
    while time.monotonic() < end:
        pending += source.read()
        while b"\n" in pending:
            line, pending = pending.split(b"\n", 1)
            row = json.loads(line)
            p = row.get("payload", {})
            dest.write(json.dumps({"observed_at":time.time(), "timestamp":row.get("timestamp"),
                "type":row.get("type"), "payload_type":p.get("type"), "role":p.get("role"),
                "bytes":len(line), "markers":sorted(set(re.findall(r"STREAM_[A-Z0-9_]+", line.decode())))})+"\n")
            dest.flush()
        time.sleep(.05)
