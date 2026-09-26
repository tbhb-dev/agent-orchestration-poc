#!/usr/bin/env sh
# Print every Markdown file the documentation checks cover, one per line.
# Tracked and untracked files that git does not ignore, minus research/imported/.
set -eu
cd "$(dirname "$0")/.."
git ls-files --cached --others --exclude-standard -- '*.md' | grep -v '^research/imported/' || true
