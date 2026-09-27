#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

tmp=$(mktemp -d "${TMPDIR:-/tmp}/ignore-collisions.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

run_case() {
    local name=$1 file=$2 expected_status=$3 expected_output=$4 repo="$tmp/$1"
    mkdir -p "$repo"
    cp "tests/fixtures/ignore-collisions/$name/rules" "$repo/.gitignore"
    cp "tests/fixtures/ignore-collisions/$name/$file" "$repo/$file"
    git -C "$repo" init -q
    git -C "$repo" add -f -- .gitignore "$file"

    local output status
    if output=$(scripts/check-ignore-collisions.sh "$repo" 2>&1); then
        status=0
    else
        status=$?
    fi
    if [[ $status -ne $expected_status || $output != "$expected_output" ]]; then
        printf '%s: expected exit %s and output %q, got exit %s and output %q\n' \
            "$name" "$expected_status" "$expected_output" "$status" "$output"
        exit 1
    fi
    printf '%s fixture: exit %s\n' "$name" "$status"
    [[ -z $output ]] || printf '%s\n' "$output"
}

run_case negated keep.txt 0 ''
run_case ignored blocked.txt 1 $'ignored tracked path: .gitignore:1:*.txt\tblocked.txt'
echo 'ignore collision fixtures ok'
