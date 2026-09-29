#!/bin/sh
set -eu
PYTHONPATH="$PWD/src"
PYTHONSAFEPATH=1
export PYTHONPATH PYTHONSAFEPATH
exec /Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3 experiments/02-host-socket-attribution/relay_cell.py claude-headless
