#!/usr/bin/env python3
"""Capture tmux control-mode messages without sending input to the pane."""
import argparse
import json
import subprocess
import threading
import time

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--session", default="codex-stream-lab")
ap.add_argument("--seconds", type=float, default=90)
ap.add_argument("--output", required=True)
args = ap.parse_args()
p = subprocess.Popen(["tmux", "-C", "attach-session", "-t", args.session,
    "-f", "read-only,ignore-size"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, text=True)
with open(args.output, "w") as f:
    def capture():
        for line in p.stdout:
            f.write(json.dumps({"observed_at":time.time(), "line":line.rstrip("\n")})+"\n")
            f.flush()
    reader = threading.Thread(target=capture)
    reader.start()
    try:
        p.wait(timeout=args.seconds)
    except subprocess.TimeoutExpired:
        p.stdin.write("detach-client\n")
        p.stdin.flush()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.terminate()
            p.wait(timeout=3)
    reader.join(timeout=3)
if p.returncode:
    raise SystemExit(p.stderr.read())
