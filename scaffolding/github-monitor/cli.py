"""Temporary #167 CLI, replaced by permanent #189 and #190."""
# ruff: noqa: INP001, T201

import argparse
import http.client
import json
import os
from contextlib import closing
from pathlib import Path

from receiver import serve
from store import Store

DEFAULT_DB = Path(".local-cache/github-monitor/state.sqlite3")


def main() -> int:
    """Run a bounded local monitor command."""
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("start", "status", "track"))
    parser.add_argument("kind", nargs="?", choices=("pr", "issue"))
    parser.add_argument("number", nargs="?", type=int)
    args = parser.parse_args()
    if args.command == "start":
        secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
        if not secret:
            parser.error("GITHUB_WEBHOOK_SECRET is required")
        installation = os.environ.get("GITHUB_INSTALLATION_ID", "")
        if not installation.isdecimal() or int(installation) <= 0:
            parser.error("GITHUB_INSTALLATION_ID must be a positive integer")
        serve(Store(DEFAULT_DB), secret.encode(), int(installation))
        return 0
    store = Store(DEFAULT_DB)
    if args.command == "track":
        if args.kind is None or args.number is None:
            parser.error("track requires kind and number")
        if args.number <= 0:
            parser.error("number must be positive")
        result: object = {"revision": store.track(args.kind, args.number)}
    else:
        status = store.status()
        try:
            with closing(
                http.client.HTTPConnection("127.0.0.1", 8787, timeout=0.5)
            ) as conn:
                conn.request("GET", "/hooks/github")
                response = conn.getresponse()
                running = (
                    response.status == 405
                    and response.getheader("X-Local-Monitor-Schema") == "1"
                )
                status["listener"] = "running" if running else "other_process"
                response.read()
        except OSError, http.client.HTTPException:
            status["listener"] = "stopped"
        result = status
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
