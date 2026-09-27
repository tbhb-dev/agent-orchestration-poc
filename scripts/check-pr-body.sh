#!/usr/bin/env bash
# Check a pull request body against the commit convention in PLAN.md (GitHub workflow, Commits and
# Pull requests). The squash commit takes the body verbatim, so the body has to pass what a commit
# message has to pass. Usage: check-pr-body.sh '<PR title>' < body, or
# check-pr-body.sh --commit-msg <message file>.
#
# Fails when the body carries an attribution trailer, when it has no `Refs: #<n>` trailer, or when
# the title is a feat or exp change and the body has no Evidence section containing a link.
set -euo pipefail
if [[ ${1:-} == --commit-msg ]]; then
    mode=commit
    message=${2:?usage: check-pr-body.sh --commit-msg <message file>}
    body=$(tr -d '\r' < "$message")
    title=${body%%$'\n'*}
    [[ $title == wip ]] && { echo "wip commit exempt"; exit 0; }
else
    mode=pr
    title=${1:?usage: check-pr-body.sh '<PR title>' < body}
    body=$(tr -d '\r')
fi
status=0

attribution=$(printf '%s\n' "$body" | grep -inE '^[[:space:]>*-]*(assisted-by|co-authored-by|generated-by|generated with|made with|written-by|authored-by)' || true)
if [ -n "$attribution" ]; then
    echo "attribution trailer found; the plan forbids them in commits and PR bodies:"
    echo "$attribution" | sed 's/^/  /'
    status=1
fi

if ! printf '%s\n' "$body" | grep -qE '^Refs: #[0-9]+[[:space:]]*$'; then
    echo "missing 'Refs: #<issue>' trailer"
    status=1
fi

case "$mode:$title" in
    pr:feat:*|pr:feat\(*|pr:feat!:*|pr:exp:*|pr:exp\(*|pr:exp!:*)
        # The evidence section runs from a heading containing "evidence" to the next heading.
        evidence=$(printf '%s\n' "$body" | awk '
            /^#+ /            { in_section = tolower($0) ~ /evidence/; next }
            in_section        { print }
        ')
        if [ -z "$evidence" ]; then
            echo "feat and exp changes need an Evidence section in the PR body"
            status=1
        elif ! printf '%s\n' "$evidence" | grep -qE 'https?://|\]\('; then
            echo "the Evidence section has no link (a URL or a Markdown link to experiments/ output)"
            status=1
        fi
        ;;
esac

if [[ $status -eq 0 ]]; then
    [[ $mode == commit ]] && echo "commit message ok" || echo "PR body ok"
fi
exit "$status"
