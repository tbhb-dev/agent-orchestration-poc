#!/bin/sh
set -eu
printf '%s\n' "$$" > /private/tmp/bv01-228-codex-interactive/root.pid
while test ! -e /private/tmp/bv01-228-codex-interactive/go; do sleep 0.05; done
cd /private/tmp/bv01-228-codex-interactive/workspace
exec env -i HOME=/private/tmp/bv01-228-codex-interactive CODEX_HOME=/private/tmp/bv01-228-codex-interactive/codex TMPDIR=/private/tmp/bv01-228-codex-interactive/tmp XDG_CONFIG_HOME=/private/tmp/bv01-228-codex-interactive/xdg PYTHONPATH=/private/tmp/bv01-228-codex-interactive/workspace BV01_FAKE_OPENAI_KEY=not-a-real-key PATH=/Users/tony/.local/bin:/Users/tony/.local/share/mise/installs/python/3.14.6/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm-256color LANG=C.UTF-8 /Users/tony/.codex/packages/standalone/releases/0.157.1-aarch64-apple-darwin/bin/codex -C /private/tmp/bv01-228-codex-interactive/workspace -c approval_policy=never
