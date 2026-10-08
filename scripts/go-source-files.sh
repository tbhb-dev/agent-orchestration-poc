#!/usr/bin/env sh
# List tracked and untracked Go source while honoring repository ignore rules.
set -eu
cd "$(dirname "$0")/.."
git ls-files -z --cached --others --exclude-standard -- '*.go'
