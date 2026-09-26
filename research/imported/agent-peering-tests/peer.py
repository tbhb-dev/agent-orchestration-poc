#!/usr/bin/env python3
"""Peer-side client for the agent-work TCP attribution test.

Run from inside a harness session (Bash tool or equivalent):

    python3 peer.py <label> [--port 47322] [--delay SECONDS]

Connects to the C2 on 127.0.0.1, sends the label, and prints the C2's
attribution report. Sends no credentials: the C2 identifies the caller from
the kernel's view of who owns the socket.

--delay waits before connecting, which is useful for background tool calls so
the connect happens after the harness has handed control back.
"""
import argparse
import os
import socket
import sys
import time


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("label")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument(
        "--port", type=int, default=int(os.environ.get("AGENTWORK_PORT", "47322"))
    )
    ap.add_argument("--delay", type=float, default=0.0)
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    if args.delay:
        time.sleep(args.delay)

    try:
        with socket.create_connection((args.host, args.port), timeout=args.timeout) as s:
            s.sendall(args.label.encode())
            chunks = []
            while True:
                data = s.recv(65536)
                if not data:
                    break
                chunks.append(data)
    except OSError as exc:
        print(f"peer: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(b"".join(chunks).decode(errors="replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
