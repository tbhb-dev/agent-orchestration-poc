#!/usr/bin/env sh
# Exercise the same file selection as the Go format task and check.
set -eu
cd "$(dirname "$0")/.."
repo_root=$(pwd -P)
fixture_repo=$(mktemp -d)
trap 'rm -rf "$fixture_repo"' 0
fixture_root=$(cd "$fixture_repo" && pwd -P)
case "$fixture_root/" in
    "$repo_root/"*)
        echo 'formatter fixtures must be outside the checkout scanned by deadcode' >&2
        exit 1
        ;;
esac
mkdir "$fixture_repo/scripts"
cp scripts/go-source-files.sh scripts/check-gofumpt.sh scripts/format-go.sh "$fixture_repo/scripts/"
cp .gitignore "$fixture_repo/"
cd "$fixture_repo"
git init -q
mkdir -p node_modules
source_dir=$(mktemp -d ./issue-302-source.XXXXXX)
ignored_dir=$(mktemp -d ./node_modules/issue-302.XXXXXX)
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

rm "$source_dir/file.go"
printf 'package example\n' >removed.go
git add removed.go
rm removed.go
if [ -n "$(scripts/go-source-files.sh)" ]; then
    echo 'deleted tracked Go file remained in the source inventory' >&2
    exit 1
fi
scripts/check-gofumpt.sh
scripts/format-go.sh
