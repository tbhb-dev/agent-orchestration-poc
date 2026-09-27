# Temporary worker launcher

This issue #176 scaffold is replaced by the production provisioner in [#28](https://github.com/tbhb/agent-orchestration-poc/issues/28).

## Start a worker

Run `mise run worker:launch -- --name alice --issue 176 --harness codex --model gpt-6-sol --effort high --branch tooling/176-alice --worktree /absolute/path/to/.worktrees/tooling-176-alice --brief-file /absolute/path/to/brief.md` from this checkout.

The command reserves the name, branch, worktree, and tmux window, creates the worktree if needed, and passes the brief as the interactive startup prompt. It never types later input into the pane. A `ready` result exits zero, `blocked` exits 2, and `unknown` exits 3. `busy` exits zero and means the native recipient is loaded but has an active turn. All output is JSON with `run_id`, `state`, and `reason`.

Run `mise run worker:status -- <run-id>` or `mise run worker:readiness -- <run-id>` to recheck a recorded run. Each run checks tmux and process generations, then confirms native identity and first brief uptake at the endpoint. Missing observations return `unknown`. If the UI displays a prompt to trust the folder, readiness is `blocked` until the operator resolves it.

Codex follow-up input uses `codex queue --thread <native-id> --message <text>` only after readiness is `ready` or `busy`. A queue request starts a later turn when the current one ends. This scaffold has no send command. Claude peer send readiness requires a `ListAgents` observation that the external coordinator cannot obtain through the installed CLI, so this launcher reports `unknown`. Agy is restricted to bounded work without clean-pause promises and reports `blocked` for an external send path until a bounded live control test establishes one.

## Registry and recovery

The ignored `.local-cache/worker-messaging/registry.json` has schema `version: 1` and an array of `runs`. Each row records the run ID, issue, worker name, harness, model, effort, branch, worktree, tmux session, window, pane and generation, native ID, endpoint, launch and observation times, PID and start time, state, and reason. It holds a SHA-256 brief digest for uptake comparison, not the prompt. The directory and files are owner only. Keep the registry with the worktree until the run ends.

If the registry is missing or corrupt, do not infer ownership from a window title or the newest saved session. Recover the run by inspecting `git worktree list --porcelain`, `tmux list-windows` and `tmux list-panes`, process start time, and the harness's native runtime. Record a new run only after that correlation. A stale generation or unloaded native recipient remains `unknown`.

The [#153](https://github.com/tbhb/agent-orchestration-poc/issues/153) stop report uses a separate version 1 run record. Map this registry's `run_id`, `worktree`, `branch`, and `launch_time` to its `run_id`, `worktree_path`, `branch`, and `launched_at`, then supply `worker_id`, `ended_at`, `final_message_path`, and `log_path` from the coordinator. These schemas differ. The launcher exports the stage one `tbhbagent` author and committer identity described by [#134](https://github.com/tbhb/agent-orchestration-poc/issues/134). It does not change signing or account settings.
