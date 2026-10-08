#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../.."
exec /usr/bin/env PYTHONPATH="$PWD/src" PYTHONSAFEPATH=1 /Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3 experiments/02-host-socket-attribution/preflight_claude_interactive.py
