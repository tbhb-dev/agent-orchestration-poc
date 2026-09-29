#!/bin/sh
set -eu
printf '%s\n' "$$" > /private/tmp/bv01-228-claude-headless/root.pid
while test ! -e /private/tmp/bv01-228-claude-headless/go; do sleep 0.05; done
cd /private/tmp/bv01-228-claude-headless/workspace
port=$(cat /private/tmp/bv01-228-claude-headless/model-port)
exec env -i HOME=/private/tmp/bv01-228-claude-headless CLAUDE_CONFIG_DIR=/private/tmp/bv01-228-claude-headless/claude TMPDIR=/private/tmp/bv01-228-claude-headless/tmp XDG_CONFIG_HOME=/private/tmp/bv01-228-claude-headless/xdg PYTHONPATH=/private/tmp/bv01-228-claude-headless/workspace ANTHROPIC_API_KEY=not-a-real-key ANTHROPIC_BASE_URL="http://127.0.0.1:$port" PATH=/Users/tony/.local/bin:/Users/tony/.local/share/mise/installs/python/3.14.6/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm-256color LANG=C.UTF-8 claude --bare --strict-mcp-config --setting-sources '' --settings /private/tmp/bv01-228-claude-headless/settings.json --print --no-session-persistence --permission-prompts none 'Run python3 experiments/02-host-socket-attribution/probe.py client /private/tmp/bv01-228-claude-headless/gateway.sock claude-headless and then stop.'
