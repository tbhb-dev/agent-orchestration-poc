#!/usr/bin/env bash
# Run one command, append a timestamped record with its exit code to the BV-05 run-4 ledger.
LOG=/private/tmp/claude-501/-Users-tony-Code-github-com-tbhb-agent-orchestration-poc/349b16d0-2964-4b4f-8e5a-2d911ebe9dc8/scratchpad/bv05-run4/ledger.txt
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')
out=$(bash -c "$1" 2>&1)
rc=$?
printf '### %s\n$ %s\n%s\n[exit %d]\n\n' "$ts" "$1" "$out" "$rc" >>"$LOG"
printf '%s\n[exit %d]\n' "$out" "$rc"
