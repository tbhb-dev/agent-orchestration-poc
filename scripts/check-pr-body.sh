#!/usr/bin/env sh
# Check a pull request body against the commit convention in PLAN.md (GitHub workflow, Commits and
# Pull requests). The squash commit takes the body verbatim, so the body has to pass what a commit
# message has to pass. Usage: check-pr-body.sh '<PR title>' < body
#
# Fails when the body carries an attribution trailer, when it has no `Refs: #<n>` trailer, or when
# the title is a feat or exp change and the body has no Evidence section containing a link.
set -eu
title=${1:?usage: check-pr-body.sh '<PR title>' < body}
body=$(tr -d '\r')
status=0

attribution=$(printf '%s\n' "$body" | grep -inE '^[^a-z]*(assisted-by|co-authored-by|generated-by|generated with|made with)' || true)
if [ -n "$attribution" ]; then
    echo "attribution trailer found; the plan forbids them in commits and PR bodies:"
    echo "$attribution" | sed 's/^/  /'
    status=1
fi

if ! printf '%s\n' "$body" | grep -qE '^Refs: #[0-9]+'; then
    echo "missing 'Refs: #<issue>' trailer"
    status=1
fi

case "$title" in
    feat:*|feat\(*|feat!:*|exp:*|exp\(*|exp!:*)
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

[ "$status" -eq 0 ] && echo "PR body ok"
exit "$status"
