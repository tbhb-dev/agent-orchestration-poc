#!/usr/bin/env sh
# Validate fenced mermaid blocks. Installs the pinned mermaid package on first use. Checks the
# files given as arguments, or every Markdown file the documentation checks cover when none are given.
set -eu
cd "$(dirname "$0")/.."
pnpm install --frozen-lockfile --dir scripts/mermaid-check --silent
if [ "$#" -gt 0 ]; then
    exec node scripts/mermaid-check/check.mjs "$@"
fi
scripts/markdown-files.sh | xargs -r node scripts/mermaid-check/check.mjs
