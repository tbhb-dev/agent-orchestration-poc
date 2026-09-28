#!/usr/bin/env sh
# Imported copies never change after import. Only MANIFEST.md and MANIFEST.tsv may gain lines in a research(import) PR.
# Usage: check-imported-research.sh <base ref> ['<PR title>']
# Added paths need a research(import) title. Modified manifests also need that title and zero deleted lines.
# All other modifications, renames, and deletions fail. An absent directory passes.
set -eu
base=${1:?usage: check-imported-research.sh <base ref> ['<PR title>']}
title=${2:-}

allowed_change() {
    case "$3" in
        "research(import)"*) ;;
        *) return 1 ;;
    esac
    case "$1" in
        A) return 0 ;;
        M)
            case "$2" in
                research/imported/MANIFEST.md | research/imported/MANIFEST.tsv)
                    [ "$4" = 0 ]
                    return
                    ;;
            esac
            ;;
    esac
    return 1
}

cd "$(dirname "$0")/.."
changes=$(git diff --name-status "$base...HEAD" -- research/imported/)
if [ -z "$changes" ]; then
    echo "research/imported/ unchanged"
    exit 0
fi
status=0
tab=$(printf '\t')
while IFS="$tab" read -r change path rest; do
    deleted=
    case "$change:$path" in
        M:research/imported/MANIFEST.md | M:research/imported/MANIFEST.tsv)
            deleted=$(git diff --numstat "$base...HEAD" -- "$path" | cut -f2)
            ;;
    esac
    if allowed_change "$change" "$path" "$title" "$deleted"; then
        printf 'allowed: %s %s\n' "$change" "$path"
    else
        printf 'rejected: %s %s\n' "$change" "$path"
        status=1
    fi
done <<EOF
$changes
EOF
exit "$status"
