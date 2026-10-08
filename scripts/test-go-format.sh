#!/usr/bin/env sh
# Exercise the same file selection as the Go format task and check.
set -eu
cd "$(dirname "$0")/.."
mkdir -p node_modules
source_dir=$(mktemp -d ./issue-302-source.XXXXXX)
ignored_dir=$(mktemp -d ./node_modules/issue-302.XXXXXX)
trap 'rm "$source_dir/file.go" "$source_dir/check.out" "$ignored_dir/bad.go" 2>/dev/null || true; rmdir "$source_dir" "$ignored_dir" node_modules 2>/dev/null || true' 0
printf 'package example\n\nvar  answer=42\n' >"$source_dir/file.go"
printf 'package ignored\n\nvar  unchanged=1\n' >"$ignored_dir/bad.go"

if scripts/check-gofumpt.sh >"$source_dir/check.out"; then
    echo 'unformatted untracked Go file escaped the format check' >&2
    exit 1
fi
if ! grep -F 'file.go' "$source_dir/check.out" >/dev/null; then
    echo 'format check failed without naming the untracked Go file' >&2
    exit 1
fi

scripts/format-go.sh
scripts/check-gofumpt.sh
if ! printf 'package ignored\n\nvar  unchanged=1\n' | cmp - "$ignored_dir/bad.go" >/dev/null; then
    echo 'formatter changed an ignored dependency file' >&2
    exit 1
fi
