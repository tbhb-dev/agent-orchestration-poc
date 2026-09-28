#!/usr/bin/env sh
set -eu

source_root=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM

run_case() {
    name=$1
    expected=$2
    title=$3
    repo="$scratch/$name"
    mkdir -p "$repo/scripts" "$repo/research/imported"
    cp "$source_root/scripts/check-imported-research.sh" "$repo/scripts/"
    printf 'first\n' >"$repo/research/imported/MANIFEST.md"
    printf 'first\n' >"$repo/research/imported/MANIFEST.tsv"
    printf 'source\n' >"$repo/research/imported/copy.md"
    git -C "$repo" init -q
    git -C "$repo" add .
    git -C "$repo" -c user.name=Test -c user.email=test@example.invalid commit -qm base
    base=$(git -C "$repo" rev-parse HEAD)

    case "$name" in
        append | non_import)
            printf 'second\n' >>"$repo/research/imported/MANIFEST.md"
            printf 'second\n' >>"$repo/research/imported/MANIFEST.tsv"
            ;;
        append_*)
            count=${name#append_}
            while [ "$count" -gt 0 ]; do
                printf 'line %s\n' "$count" >>"$repo/research/imported/MANIFEST.md"
                printf 'line %s\n' "$count" >>"$repo/research/imported/MANIFEST.tsv"
                count=$((count - 1))
            done
            ;;
        changed_line) printf 'changed\n' >"$repo/research/imported/MANIFEST.md" ;;
        deleted_line) : >"$repo/research/imported/MANIFEST.tsv" ;;
        modified_copy) printf 'changed\n' >"$repo/research/imported/copy.md" ;;
        deleted_manifest) rm "$repo/research/imported/MANIFEST.md" ;;
        renamed_manifest) mv "$repo/research/imported/MANIFEST.md" "$repo/research/imported/RENAMED.md" ;;
        added_copy | added_copy_non_import) printf 'new\n' >"$repo/research/imported/new.md" ;;
    esac
    git -C "$repo" add -A
    git -C "$repo" -c user.name=Test -c user.email=test@example.invalid commit -qm "$name"
    if output=$("$repo/scripts/check-imported-research.sh" "$base" "$title" 2>&1); then
        actual=0
    else
        actual=$?
    fi
    printf '%s: exit %s\n%s\n' "$name" "$actual" "$output"
    [ "$actual" -eq "$expected" ]
}

run_case append 0 'research(import): append manifests'
run_case changed_line 1 'research(import): change manifest'
run_case deleted_line 1 'research(import): delete manifest line'
run_case non_import 1 'tooling(import): append manifests'
run_case modified_copy 1 'research(import): change imported copy'
run_case deleted_manifest 1 'research(import): delete manifest'
run_case renamed_manifest 1 'research(import): rename manifest'
run_case added_copy 0 'research(import): add imported copy'
run_case added_copy_non_import 1 'tooling(import): add imported copy'

# Sample the append rule across different positive line counts for both manifests.
for count in 1 2 3 4 5; do
    run_case "append_$count" 0 'research(import): append manifests'
done
