# BV-01 stage B commands prepared during readiness

These commands are prepared, not executed. Run them only after the operator reports that the new `eslogger` capture is running and its `audit-positive-rerun` control appeared. Use a fresh supervisor shell in the assigned worktree. Follow the [merged runbook](../../stage-two-runbook.md) for per-cell evidence collection, stop conditions, and teardown. Prepared launch scripts live in the mode-700 homes. Previous versions are in each home's `rerun-prior-stage-two/`.

## One-time gate

~~~sh
set -eu
cd /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/exp-228-harness-rerun
umask 077
capture=/private/tmp/bv01-228-codex-headless/file-opens-rerun.json
test -f "$capture"
test -f /private/tmp/bv01-228-codex-headless/file-opens-rerun.pid
grep -F -q 'audit-positive-rerun' "$capture"
test ! -s /private/tmp/bv01-228-codex-headless/file-opens-rerun.err
test "$(/Users/tony/.codex/packages/standalone/releases/0.157.1-aarch64-apple-darwin/bin/codex --version)" = 'codex-cli 0.157.1'
test "$(claude --version)" = '2.1.284 (Claude Code)'
probe=experiments/02-host-socket-attribution/probe.py
responder=experiments/02-host-socket-attribution/model_responder.py
~~~

## Repeat for one literal profile at a time

Assign `profile` to the next literal name in the launch order below, then run this setup block in the same supervisor shell. Keep each responder, listener, launch root, and result scoped to that profile. A failed assertion stops the cell.

~~~sh
home="/private/tmp/bv01-228-$profile"
test -d "$home"
test ! -e "$home/root.pid"
test ! -e "$home/go"
test ! -e "$home/gateway.sock"
test ! -e "$home/model-start.json"
PYTHONSAFEPATH=1 mise exec -- uv run python "$responder" --host 127.0.0.1 --port 0 --profile "$profile" --log "$home/model.jsonl" > "$home/model-start.json" 2> "$home/model.err" &
model_pid=$!
attempt=0
while test ! -s "$home/model-start.json"; do
  attempt=$((attempt + 1))
  test "$attempt" -le 100
  sleep 0.05
done
port=$(mise exec -- python -c 'import json,sys; print(json.load(open(sys.argv[1]))["port"])' "$home/model-start.json")
printf '%s\n' "$port" > "$home/model-port"
lsof -nP -a -p "$model_pid" -iTCP
~~~

For either Codex profile, set its fresh responder port in the already seeded config and confirm the OP-33 values before launching. The config has only the fake key's environment-variable name, not a usable credential.

~~~sh
mise exec -- python - "$home/codex/config.toml" "$port" "$home/workspace" <<'PY'
import pathlib
import re
import sys
import tomllib

path = pathlib.Path(sys.argv[1])
port = sys.argv[2]
workspace = sys.argv[3]
updated, count = re.subn(
    r'(?m)^base_url = "http://127\.0\.0\.1:[0-9]+/v1"$',
    f'base_url = "http://127.0.0.1:{port}/v1"',
    path.read_text(),
)
assert count == 1
data = tomllib.loads(updated)
assert data["check_for_update_on_startup"] is False
assert data["features"]["plugins"] is False
assert data["projects"][workspace]["trust_level"] == "trusted"
path.write_text(updated)
PY
~~~

Launch the literal cell command below, then immediately run the common listener barrier. For an interactive cell, create only the dedicated tmux server with the command shown before its first `new-window`. Leave the default server and session 0 alone.

~~~sh
attempt=0
while test ! -s "$home/root.pid"; do
  attempt=$((attempt + 1))
  test "$attempt" -le 100
  sleep 0.05
done
root_pid=$(cat "$home/root.pid")
PYTHONSAFEPATH=1 mise exec -- uv run python "$probe" server "$home/gateway.sock" "$root_pid" 1 > "$home/listener.jsonl" 2> "$home/listener.err" &
listener_pid=$!
attempt=0
while test ! -S "$home/gateway.sock"; do
  attempt=$((attempt + 1))
  test "$attempt" -le 100
  sleep 0.05
done
: > "$home/go"
~~~

## Literal launch order

1. Set `profile=codex-headless`, run the per-cell setup and Codex port update, then launch with `sh /private/tmp/bv01-228-codex-headless/launch.sh > /private/tmp/bv01-228-codex-headless/harness.out 2> /private/tmp/bv01-228-codex-headless/harness.err &` and run the listener barrier.
2. After that cell ends and its recorded processes are handled under the runbook, set `profile=codex-interactive`, run the per-cell setup and Codex port update, start the dedicated server with `tmux -S /private/tmp/bv01-228-probe.tmux -f /dev/null new-session -d -s bv01 -n anchor 'sleep 7200'`, then launch with `tmux -S /private/tmp/bv01-228-probe.tmux new-window -t bv01 -n codex-interactive 'sh /private/tmp/bv01-228-codex-interactive/launch.sh'` and run the listener barrier. Its exact native-tool prompt is `Run python3 experiments/02-host-socket-attribution/probe.py client /private/tmp/bv01-228-codex-interactive/gateway.sock codex-interactive and then stop.`
3. After that cell ends, set `profile=claude-headless`, run the per-cell setup, then launch with `sh /private/tmp/bv01-228-claude-headless/launch.sh > /private/tmp/bv01-228-claude-headless/harness.out 2> /private/tmp/bv01-228-claude-headless/harness.err &` and run the listener barrier. The script contains its literal native-tool prompt.
4. After that cell ends, set `profile=claude-interactive`, run the per-cell setup, then launch with `tmux -S /private/tmp/bv01-228-probe.tmux new-window -t bv01 -n claude-interactive 'sh /private/tmp/bv01-228-claude-interactive/launch.sh'` and run the listener barrier. Its exact native-tool prompt is `Run python3 experiments/02-host-socket-attribution/probe.py client /private/tmp/bv01-228-claude-interactive/gateway.sock claude-interactive and then stop.`

The operator stops the privileged capture only after the executor reports that all cells and their descendants have ended. The old capture and all four homes remain for the later teardown decision.
