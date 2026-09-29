#!/usr/bin/env bash
# Record a bounded probe without shell expansion of the command arguments.
set -u
ledger=$(dirname "$0")/ledger.txt
output=$(mktemp)
{
    printf '### %s\n$' "$(date '+%Y-%m-%dT%H:%M:%S%z')"
    printf ' %q' "$@"
    printf '\n'
} >>"$ledger"
"$@" >"$output" 2>&1
status=$?
cat "$output" | tee -a "$ledger"
printf '[exit %d]\n\n' "$status" >>"$ledger"
printf '[exit %d]\n' "$status"
rm "$output"
exit "$status"
