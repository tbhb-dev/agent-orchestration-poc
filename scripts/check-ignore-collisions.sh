#!/usr/bin/env bash
# Check tracked paths against Git ignores, then warn about case-folded directory matches.
set -euo pipefail
cd "${1:-$(dirname "$0")/..}"

paths=()
dirs=()
while IFS= read -r -d '' path; do
    paths+=("$path")
    parent=${path%/*}
    [[ $parent == "$path" ]] && continue
    while [[ $parent != . ]]; do
        found=0
        for dir in "${dirs[@]+"${dirs[@]}"}"; do
            [[ $dir == "$parent" ]] && found=1
        done
        [[ $found -eq 1 ]] || dirs+=("$parent")
        [[ $parent == */* ]] || break
        parent=${parent%/*}
    done
done < <(git ls-files -z)

status=0
if [[ ${#paths[@]} -gt 0 ]]; then
    # Personal global ignores vary by machine and are outside this repository check.
    while IFS= read -r -d '' source &&
        IFS= read -r -d '' line &&
        IFS= read -r -d '' pattern &&
        IFS= read -r -d '' path; do
        [[ $pattern == '!'* ]] && continue
        printf 'ignored tracked path: %s:%s:%s\t%s\n' "$source" "$line" "$pattern" "$path"
        status=1
    done < <(printf '%s\0' "${paths[@]}" | git -c core.excludesFile=/dev/null check-ignore -v -z --no-index --stdin)
fi

sources=()
while IFS= read -r -d '' source; do
    sources+=("$source")
done < <(git ls-files -z --cached --others --exclude-standard -- '.gitignore' '**/.gitignore')
common_dir=$(git rev-parse --git-common-dir)
[[ -f $common_dir/info/exclude ]] && sources+=("$common_dir/info/exclude")

shopt -s nocasematch
for source in "${sources[@]+"${sources[@]}"}"; do
    scope=${source%/.gitignore}
    [[ $scope == "$source" ]] && scope=.
    number=0
    while IFS= read -r entry || [[ -n $entry ]]; do
        number=$((number + 1))
        [[ -n $entry && $entry != \#* && $entry != '!'* ]] || continue
        pattern=${entry#/}
        pattern=${pattern%/}
        [[ -n $pattern ]] || continue
        for dir in "${dirs[@]+"${dirs[@]}"}"; do
            relative=$dir
            if [[ $scope != . ]]; then
                [[ $dir == "$scope/"* ]] || continue
                relative=${dir#"$scope/"}
            fi
            leaf=${relative##*/}
            # Gitignore entries may contain globs; pattern matching is intentional.
            # shellcheck disable=SC2053
            if [[ $relative == $pattern || $leaf == $pattern ]]; then
                printf 'case-insensitive directory match: %s:%s:%s -> %s\n' "$source" "$number" "$entry" "$dir"
            fi
        done
    done <"$source"
done
exit "$status"
