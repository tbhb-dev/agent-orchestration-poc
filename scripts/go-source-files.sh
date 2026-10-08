#!/usr/bin/env sh
# List tracked and untracked Go source while honoring repository ignore rules.
set -eu
cd "$(dirname "$0")/.."
# The quoted script runs in the child shell so its path variables expand there.
# shellcheck disable=SC2016
git ls-files -z --cached --others --exclude-standard -- '*.go' | xargs -0 sh -c '
    for path do
        if [ -f "$path" ]; then
            printf "%s\000" "$path"
        fi
    done
' sh
