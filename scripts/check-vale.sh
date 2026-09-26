#!/usr/bin/env sh
# Lint prose with Vale. Syncs the pinned styles on first use. Lints the files given as
# arguments, or every Markdown file the documentation checks cover when none are given.
set -eu
cd "$(dirname "$0")/.."
[ -d .vale/styles/ai-tells ] && [ -d .vale/styles/ai-tells-commits ] || vale sync
if [ "$#" -gt 0 ]; then
    exec vale "$@"
fi
scripts/markdown-files.sh | xargs -r vale
