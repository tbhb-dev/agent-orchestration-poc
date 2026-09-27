#!/usr/bin/env sh
# Every experiments/<NN-slug>/ directory needs a README.md, an evidence/ directory, and a versions.md.
# Directories listed in EXCEPTIONS predate the rule and are skipped.
set -eu
cd "$(dirname "$0")/.."
EXCEPTIONS="00-system-assessment"
status=0
for dir in experiments/*/; do
    [ -d "$dir" ] || continue
    name=$(basename "$dir")
    skip=0
    for exception in $EXCEPTIONS; do
        [ "$name" = "$exception" ] && skip=1
    done
    [ "$skip" -eq 1 ] && continue
    case "$name" in
        [0-9][0-9]-*) ;;
        *)
            echo "experiments/$name: directory name must be NN-slug"
            status=1
            ;;
    esac
    [ -f "$dir/README.md" ] || {
        echo "experiments/$name: missing README.md"
        status=1
    }
    [ -d "$dir/evidence" ] || {
        echo "experiments/$name: missing evidence/ directory"
        status=1
    }
    [ -f "$dir/versions.md" ] || {
        echo "experiments/$name: missing versions.md"
        status=1
    }
done
exit "$status"
