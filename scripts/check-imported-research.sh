#!/usr/bin/env sh
# research/imported/ holds verbatim copies of earlier research and never changes after the import lands.
# Usage: check-imported-research.sh <base ref> ['<PR title>']
# Fails when any path under research/imported/ is modified, renamed, or deleted relative to the base,
# and when paths are added unless the PR title starts with `research(import)`. Passes when the directory
# does not exist on either side.
set -eu
base=${1:?usage: check-imported-research.sh <base ref> ['<PR title>']}
title=${2:-}
cd "$(dirname "$0")/.."
changes=$(git diff --name-status "$base...HEAD" -- research/imported/)
if [ -z "$changes" ]; then
    echo "research/imported/ unchanged"
    exit 0
fi
status=0
changed=$(printf '%s\n' "$changes" | grep -vE '^A' || true)
if [ -n "$changed" ]; then
    echo "research/imported/ is immutable once imported; these paths are modified, renamed, or deleted:"
    printf '%s\n' "$changed" | sed 's/^/  /'
    status=1
fi
added=$(printf '%s\n' "$changes" | grep -E '^A' || true)
if [ -n "$added" ]; then
    case "$title" in
        "research(import)"*)
            echo "additions to research/imported/ allowed by the research(import) title:"
            printf '%s\n' "$added" | sed 's/^/  /'
            ;;
        *)
            echo "additions to research/imported/ need a PR title starting with research(import):"
            printf '%s\n' "$added" | sed 's/^/  /'
            status=1
            ;;
    esac
fi
exit "$status"
