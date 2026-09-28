#!/usr/bin/env bash
# Restart the BV-05 loopback receiver with the named leaf; extra args pass through.
leaf=$1; shift
pkill -f 'fixture.py serve' ; sleep 1
cd /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/exp-229-sbx-kit-trust-4 || exit 1
PYTHONSAFEPATH=1 nohup mise exec -- python experiments/03-sbx-kit-trust/fixture.py serve --root /private/tmp/bv05-pki --leaf "$leaf" --port 18443 --log /private/tmp/bv05-run/receiver.jsonl --deliveries /private/tmp/bv05-run/deliveries.jsonl "$@" > /private/tmp/bv05-run/serve.out 2>&1 &
sleep 2
cat /private/tmp/bv05-run/serve.out
