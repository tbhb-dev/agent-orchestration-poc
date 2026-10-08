#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
scripts/go-source-files.sh | xargs -0 sh -c '
    if [ "$#" -gt 0 ]; then
        gofumpt -w "$@"
    fi
' sh
