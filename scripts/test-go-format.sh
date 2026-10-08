#!/usr/bin/env sh
# Exercise the same file selection as the Go format task and check.
set -eu
cd "$(dirname "$0")/.."
mkdir -p node_modules
source_dir=$(mktemp -d ./issue-302-source.XXXXXX)
ignored_dir=$(mktemp -d ./node_modules/issue-302.XXXXXX)
deleted_repo=$(mktemp -d)
trap 'rm "$source_dir/file.go" "$source_dir/check.out" "$ignored_dir/bad.go" 2>/dev/null || true; rmdir "$source_dir" "$ignored_dir" node_modules 2>/dev/null || true; rm -rf "$deleted_repo"' 0
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

mkdir "$deleted_repo/scripts"
cp scripts/go-source-files.sh scripts/check-gofumpt.sh scripts/format-go.sh "$deleted_repo/scripts/"
git -C "$deleted_repo" init -q
printf 'package example\n' >"$deleted_repo/removed.go"
git -C "$deleted_repo" add removed.go
rm "$deleted_repo/removed.go"
if [ -n "$("$deleted_repo/scripts/go-source-files.sh")" ]; then
    echo 'deleted tracked Go file remained in the source inventory' >&2
    exit 1
fi
"$deleted_repo/scripts/check-gofumpt.sh"
"$deleted_repo/scripts/format-go.sh"
