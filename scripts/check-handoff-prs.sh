#!/usr/bin/env bash
# Verify that PRs described as open in the handoff are open on GitHub.
set -euo pipefail

classify_open_pr_lines() {
    local line clause rest reference before after number
    local before_pattern='(^|[^[:alpha:]])open[[:space:]]*\[?$'
    local no_open_pattern='(^|[^[:alpha:]])no[[:space:]]+open[[:space:]]*\[?$'
    local after_pattern='^[[:space:]):|,-]*(is[[:space:]]+still[[:space:]]+|is[[:space:]]+|remains[[:space:]]+|still[[:space:]]+)?open([^[:alpha:]]|$)'
    shopt -s nocasematch
    while IFS= read -r line || [[ -n $line ]]; do
        while [[ -n $line ]]; do
            clause=${line%%'. '*}
            if [[ $clause == "$line" ]]; then
                line=
            else
                line=${line#*'. '}
            fi
            rest=$clause
            while [[ $rest =~ (pull/[0-9]+|[Pp][Rr][[:space:]]*#[0-9]+) ]]; do
                reference=${BASH_REMATCH[1]}
                before=${rest%%"$reference"*}
                after=${rest#*"$reference"}
                [[ ${#before} -gt 60 ]] && before=${before: -60}
                if { [[ $before =~ $before_pattern ]] && [[ ! $before =~ $no_open_pattern ]]; } ||
                    [[ ${after:0:60} =~ $after_pattern ]]; then
                    number=${reference//[^0-9]/}
                    printf '%s\n' "$number"
                fi
                rest=$after
            done
        done
    done
}

if [[ ${1:-} == --classify ]]; then
    classify_open_pr_lines
    exit 0
fi

cd "${1:-$(dirname "$0")/..}"
references=$(cat HANDOFF.md docs/src/content/docs/project/handoff.md | classify_open_pr_lines | sort -u)
if [[ -z $references ]]; then
    echo "handoff has no PR references described as open"
    exit 0
fi
status=0
while IFS= read -r number; do
    state=$(gh pr view "$number" --json state --jq .state) || { status=1; continue; }
    if [[ $state == OPEN ]]; then
        printf 'PR #%s is open\n' "$number"
    else
        printf 'handoff calls PR #%s open, but GitHub reports %s\n' "$number" "$state"
        status=1
    fi
done <<< "$references"
exit "$status"
