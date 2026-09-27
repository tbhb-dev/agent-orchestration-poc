# Temporary worker launcher

This issue #176 scaffold is replaced by the production provisioner in [#28](https://github.com/tbhb/agent-orchestration-poc/issues/28).

## Start a worker

Run `mise run worker:launch -- --name alice --issue 176 --harness codex --model gpt-6-sol --effort high --branch tooling/176-alice --worktree /absolute/path/to/.worktrees/tooling-176-alice --brief-file /absolute/path/to/brief.md` from this checkout.

The command reserves the name, branch, worktree, and tmux window, creates the worktree if needed, and passes the brief as the interactive startup prompt. It never types later input into the pane. A `ready` result exits zero, `blocked` exits 2, and `unknown` exits 3. `busy` exits zero and means the native recipient is loaded but has an active turn. All output is JSON with `run_id`, `state`, and `reason`.

Run `mise run worker:status -- <run-id>` or `mise run worker:readiness -- <run-id>` to recheck a recorded run. Each run checks tmux and process generations, then confirms native identity and first brief uptake at the endpoint. Missing observations return `unknown`. If the UI displays a prompt to trust the folder, readiness is `blocked` until the operator resolves it.

Codex follow-up input uses `codex queue --thread <native-id> --message <text>` only after readiness is `ready` or `busy`. A queue request starts a later turn when the current one ends. This scaffold has no send command. Claude peer send readiness requires a `ListAgents` observation that the external coordinator cannot obtain through the installed CLI, so this launcher reports `unknown`. Agy is restricted to bounded work without clean-pause promises and reports `blocked` for an external send path until a bounded live control test establishes one.

## Registry and recovery

The ignored `.local-cache/worker-messaging/registry.json` has schema `version: 1` and an array of `runs`. Each row records the run ID, issue, worker name, harness, model, effort, branch, worktree, tmux session, window, pane and generation, native ID, endpoint, launch and observation times, PID and start time, state, and reason. It holds a SHA-256 brief digest for uptake comparison, not the prompt. The directory and files are owner only. Keep the registry with the worktree until the run ends.

If the registry is missing or corrupt, the launcher refuses an existing worktree, even when its branch matches. Do not infer ownership from a window title or the newest saved session. Recovery requires a coordinator to correlate `git worktree list --porcelain`, `tmux list-windows` and `tmux list-panes`, process start time, and the harness's native runtime before recording a new run. The CLI has no automatic recovery command. A stale generation or unloaded native recipient remains `unknown`.

The [#153](https://github.com/tbhb/agent-orchestration-poc/issues/153) stop report uses a separate version 1 run record. Map this registry's `run_id`, `worktree`, `branch`, and `launch_time` to its `run_id`, `worktree_path`, `branch`, and `launched_at`, then supply `worker_id`, `ended_at`, `final_message_path`, and `log_path` from the coordinator. These schemas differ. The launcher exports the stage one `tbhbagent` author and committer identity described by [#134](https://github.com/tbhb/agent-orchestration-poc/issues/134). It does not change signing or account settings.

## Coordinator live verification handoff

Run these commands only in an operator-authorized coordinator session with process and Unix-socket access, from the checkout containing this PR. Use a disposable branch, worktree, brief, and tmux window. The commands capture local evidence under a private temporary directory. Redact transcript content and scan it before committing. A result of `unknown` is evidence of a failed observation, not readiness. Do not change trust or harness settings as part of this trial.

```sh
TRIAL_DIR=$(mktemp -d /private/tmp/worker176-live.XXXXXX)
TRIAL_NAME=worker176live
TRIAL_BRANCH=tooling/176-live-probe
TRIAL_WORKTREE="$TRIAL_DIR/worktree"
printf 'Reply with exactly LIVE-176-READY. Then wait for another message.\n' > "$TRIAL_DIR/brief.md"
mise exec -- codex --version > "$TRIAL_DIR/codex-version.txt"
mise exec -- tmux -V > "$TRIAL_DIR/tmux-version.txt"
mise run worker:launch -- --name "$TRIAL_NAME" --issue 176 --harness codex --model gpt-6-sol --effort medium --branch "$TRIAL_BRANCH" --worktree "$TRIAL_WORKTREE" --brief-file "$TRIAL_DIR/brief.md" > "$TRIAL_DIR/launch.json"
printf 'launch exit=%s\n' "$?"
cat "$TRIAL_DIR/launch.json"
```

Expect version commands to exit 0 and identify the installed versions. Launch exits 0 with `state: ready` only if all native checks pass, 2 for `blocked`, or 3 for `unknown`. Its JSON must contain a `run_id` and reason. `mise exec -- tmux capture-pane -p -t worker-messaging:$TRIAL_NAME` must exit 0 and show `LIVE-176-READY`. This marker alone does not prove native readiness. A folder-trust prompt must instead yield `blocked` and exit 2, and must stay unanswered until the operator decides how to handle it.

```sh
RUN_ID=$(mise exec -- python -c 'import json,sys; print(json.load(open(sys.argv[1]))["run_id"])' "$TRIAL_DIR/launch.json")
mise exec -- python -c 'import json,sys; p=".local-cache/worker-messaging/registry.json"; r=next(x for x in json.load(open(p))["runs"] if x["run_id"]==sys.argv[1]); print(json.dumps({k:r.get(k) for k in ("native_id","endpoint","pid","process_start","tmux_pane","pane_generation","worktree","state","reason")}))' "$RUN_ID" > "$TRIAL_DIR/identity.json"
cat "$TRIAL_DIR/identity.json"
mise exec -- tmux display-message -p -t "worker-messaging:$TRIAL_NAME" '#{pane_id}|#{pane_pid}|#{window_id}' > "$TRIAL_DIR/tmux.txt"
mise exec -- ps -o pid=,lstart=,command= -p "$(mise exec -- python -c 'import json,sys; print(json.load(open(sys.argv[1]))["pid"])' "$TRIAL_DIR/identity.json")" > "$TRIAL_DIR/process.txt"
mise exec -- git worktree list --porcelain > "$TRIAL_DIR/worktrees.txt"
mise exec -- lsof -Fn -p "$(mise exec -- python -c 'import json,sys; print(json.load(open(sys.argv[1]))["pid"])' "$TRIAL_DIR/identity.json")" > "$TRIAL_DIR/open-files.txt"
PYTHONPATH=scaffolding/worker-messaging mise exec -- python -c 'import json,sys; from adapters.codex_launch import rollout; paths=[line[1:] for line in open(sys.argv[1]).read().splitlines() if line.startswith("n/") and "/sessions/" in line and "rollout-" in line]; assert len(paths)==1, paths; r=rollout(paths[0]); print(json.dumps({"id":r["id"],"cwd":r["cwd"],"path":r["path"],"started":r["started"]}))' "$TRIAL_DIR/open-files.txt" > "$TRIAL_DIR/rollout.json"
cat "$TRIAL_DIR/rollout.json"
```

Expect each command to exit 0. The registry PID, pane ID, process start, and worktree must match the tmux, `ps`, and Git observations. `rollout.json` must show `started: true` with the same `native_id` and cwd as `identity.json`. The `lsof` output must contain exactly one process-held `rollout-*.jsonl`. Do not select a rollout by latest timestamp. The following command calls the same owning endpoint used by the launcher. Its JSON must show `loaded: true` with the exact registry thread ID and cwd. The tagged `status.type` must be `idle` or `active`. The adapter calls `thread/loaded/list` through all cursor pages and then `thread/read` on that endpoint.

```sh
PYTHONPATH=scaffolding/worker-messaging mise exec -- python -c 'import json,sys; from adapters.codex_launch import runtime_thread; r=json.load(open(sys.argv[1])); loaded,thread=runtime_thread(r["endpoint"],r["native_id"]); print(json.dumps({"loaded":loaded,"id":thread.get("id"),"cwd":thread.get("cwd"),"status":thread.get("status")}))' "$TRIAL_DIR/identity.json" > "$TRIAL_DIR/native.json"
cat "$TRIAL_DIR/native.json"
mise run worker:readiness -- "$RUN_ID" > "$TRIAL_DIR/idle.json"
printf 'idle exit=%s\n' "$?"
cat "$TRIAL_DIR/idle.json"
```

Expect the native command to exit 0. `idle.json` should report `ready` with exit 0 after the first brief is confirmed and the loaded runtime matches the recorded process and pane. For a controlled busy state, run the following while the disposable worker is ready. Queue exit 0 means acceptance, not delivery. Capture the busy snapshot before the task ends. If it ends first, record the busy case as missed.

```sh
NATIVE_ID=$(mise exec -- python -c 'import json,sys; print(json.load(open(sys.argv[1]))["native_id"])' "$TRIAL_DIR/identity.json")
mise exec -- codex queue --thread "$NATIVE_ID" --message 'Run a shell sleep for 30 seconds, then reply with exactly LIVE-176-BUSY.'
printf 'queue exit=%s\n' "$?"
PYTHONPATH=scaffolding/worker-messaging mise exec -- python -c 'import json,sys; from adapters.codex_launch import runtime_thread; r=json.load(open(sys.argv[1])); loaded,thread=runtime_thread(r["endpoint"],r["native_id"]); print(json.dumps({"loaded":loaded,"id":thread.get("id"),"cwd":thread.get("cwd"),"status":thread.get("status")}))' "$TRIAL_DIR/identity.json" > "$TRIAL_DIR/busy-native.json"
mise run worker:readiness -- "$RUN_ID" > "$TRIAL_DIR/busy.json"
printf 'busy exit=%s\n' "$?"
cat "$TRIAL_DIR/busy-native.json" "$TRIAL_DIR/busy.json"
```

Expect `busy-native.json` to contain `loaded: true` and `status.type: active`, and `busy.json` to contain `state: busy` with exit 0. After the `LIVE-176-BUSY` marker appears in `mise exec -- tmux capture-pane -p -t "worker-messaging:$TRIAL_NAME"`, rerun `mise run worker:readiness -- "$RUN_ID"`. Expect `state: ready` and exit 0.

To check unload and generation reuse, stop only this trial pane and inspect the old run. Both commands below must exit as indicated. A new disposable launch with a different name, branch, worktree, and brief can then exercise PID or pane reuse. Capture its new identity and rerun the old status command. The old run must remain `unknown` even if an identifier is reused.

```sh
mise exec -- tmux kill-window -t "worker-messaging:$TRIAL_NAME"
printf 'kill exit=%s\n' "$?"
mise run worker:status -- "$RUN_ID" > "$TRIAL_DIR/stopped.json"
printf 'stopped exit=%s\n' "$?"
cat "$TRIAL_DIR/stopped.json"
```

Expect kill exit 0 and `stopped.json` to contain `state: unknown` with exit 3 and a stale or missing tmux reason. A runtime restart is disruptive and requires separate operator authorization. If authorized, record `mise exec -- codex app-server daemon restart` and its exit code, then repeat the native command and `mise run worker:status -- "$RUN_ID"`. Expect the old run to remain `unknown` with exit 3. An unloaded old thread must not become ready by reading persisted history. Do not resume it merely to make the check pass.

For Claude, the same disposable launch and tmux/`ps`/cwd checks can run with `--harness claude --model haiku --effort low`. Expect startup uptake to be visible, but this scaffold has no external `ListAgents` adapter and hard-codes `loaded: false`: readiness must be `unknown` with exit 3. A capable Claude coordinator must separately record its `ListAgents` response and provide an adapter handoff before claiming ready. For agy 1.2.11, use a separate bounded disposable task with no follow-up requirement. The external sender and clean-pause path remain unproved, so do not send through an inferred inbox or claim ready. These Claude and agy gaps keep issue #176 open.

After capturing exit codes and redacted JSON, scan with `mise exec -- gitleaks dir --no-banner --redact=100 "$TRIAL_DIR"`. Kill only the trial window, verify the trial worktree is clean with `mise exec -- git -C "$TRIAL_WORKTREE" status --porcelain`, then remove it with `mise exec -- git worktree remove "$TRIAL_WORKTREE"` and delete the trial branch with `mise exec -- git branch -d "$TRIAL_BRANCH"`. Retain the evidence directory until the coordinator has reviewed the results.
