#!/bin/sh
set -eu
PYTHONPATH="$PWD/src"
PYTHONSAFEPATH=1
PYTHONPYCACHEPREFIX="/private/tmp/bv01-228-claude-interactive/tmp/pycache"
export PYTHONPATH PYTHONSAFEPATH PYTHONPYCACHEPREFIX
exec /Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3 experiments/02-host-socket-attribution/relay_cell.py claude-interactive
