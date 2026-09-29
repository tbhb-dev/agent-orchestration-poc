#!/bin/sh
set -eu
printf '%s\n' "$$" > /private/tmp/bv01-228-claude-interactive/root.pid
while test ! -e /private/tmp/bv01-228-claude-interactive/go; do sleep 0.05; done
cd /private/tmp/bv01-228-claude-interactive/workspace
port=$(cat /private/tmp/bv01-228-claude-interactive/model-port)
exec env -i HOME=/private/tmp/bv01-228-claude-interactive CLAUDE_CONFIG_DIR=/private/tmp/bv01-228-claude-interactive/claude TMPDIR=/private/tmp/bv01-228-claude-interactive/tmp XDG_CONFIG_HOME=/private/tmp/bv01-228-claude-interactive/xdg PYTHONPATH=/private/tmp/bv01-228-claude-interactive/workspace ANTHROPIC_API_KEY=not-a-real-key ANTHROPIC_BASE_URL="http://127.0.0.1:$port" PATH=/Users/tony/.local/bin:/Users/tony/.local/share/mise/installs/python/3.14.6/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm-256color LANG=C.UTF-8 claude --bare --strict-mcp-config --setting-sources '' --settings /private/tmp/bv01-228-claude-interactive/settings.json
