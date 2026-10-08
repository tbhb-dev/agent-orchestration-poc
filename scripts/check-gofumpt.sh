#!/usr/bin/env sh
# Fail when gofumpt would change a file. `gofumpt -l` only lists files and exits 0, so this
# script turns a non-empty listing into a failure. Checks the files given as arguments, or the
# non-ignored Go source when none are given.
set -eu
cd "$(dirname "$0")/.."
if [ "$#" -gt 0 ]; then
    out=$(gofumpt -l "$@")
else
    out=$(scripts/go-source-files.sh | xargs -0 sh -c '
        if [ "$#" -gt 0 ]; then
            gofumpt -l "$@"
        fi
    ' sh)
fi
[ -z "$out" ] || {
    echo "$out"
    echo "gofumpt would reformat the files above; run mise run fmt:go"
    exit 1
}
