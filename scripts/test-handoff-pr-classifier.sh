#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
actual=$(scripts/check-handoff-prs.sh --classify <tests/fixtures/handoff-open-pr-lines.txt | sort -un)
expected=$(cat tests/fixtures/handoff-open-pr-expected.txt)
if [[ $actual != "$expected" ]]; then
    printf 'expected:\n%s\nactual:\n%s\n' "$expected" "$actual"
    exit 1
fi
echo "handoff classifier fixtures ok"
