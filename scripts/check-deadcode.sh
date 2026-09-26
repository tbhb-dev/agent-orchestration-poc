#!/usr/bin/env sh
# Fail when deadcode reports a function unreachable from the binaries and tests.
set -eu
cd "$(dirname "$0")/.."
out=$(deadcode -test ./...)
if [ -n "$out" ]; then
    printf '%s\n' "$out"
    exit 1
fi
