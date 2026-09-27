# Temporary worker launcher

This issue #176 scaffold is replaced by the production provisioner in [#28](https://github.com/tbhb/agent-orchestration-poc/issues/28).

## Launch and inspect

The coordinator supplies an explicit `unix:///absolute/socket/path` endpoint for each Codex launch. The launcher records that endpoint and passes it to the interactive TUI with `--remote`. The selected model and effort remain explicit. The brief is the startup prompt. The command supplies no client-side `--add-dir` or writable-root override. The operator must approve and configure the app server for this socket before a live trial. There is no default endpoint.

```sh
mise run worker:launch -- --name alice --issue 176 --harness codex --model gpt-6-sol --effort high --branch tooling/176-alice --worktree /absolute/path/to/.worktrees/tooling-176-alice --brief-file /absolute/path/to/brief.md --endpoint unix:///operator/recorded/socket.sock
mise run worker:readiness -- <run-id>
mise run worker:status -- <run-id>
```

Each command returns JSON. Launch includes `run_id`, `state`, `reason`, `endpoint`, and `observed_at`. Readiness checks the tmux pane and process generations. It correlates the process-held rollout with the startup brief. The thread ID must appear in `thread/loaded/list` at the recorded endpoint, and `thread/read` must return that same ID with the recorded cwd, model, and effort. A stored but unloaded thread cannot become ready. `ready` and `busy` exit 0, a trust prompt or unsupported agy send path exits 2 as `blocked`, and missing or stale identity exits 3 as `unknown`.

Status returns the same readiness at the top level and under `readiness`. Its `status` object reports an advisory #178 snapshot from `.local-cache/worker-messaging/status/<run-id>.json`, including `source`, `age_seconds`, and `availability`. A matching run ID, pane generation, and timestamp are required. A record at most 120 seconds old is `fresh`. A fresh record cannot override `unknown` readiness.

Later Codex input uses `codex queue` only after a fresh `ready` or `busy` result. This scaffold has no send command. Queue acceptance is not delivery proof. Claude remains `unknown` until #187 supplies a correlated live `ListAgents` result tied to session ID, PID and start, pane generation, cwd, peer handle, observation time, and brief uptake. Agy is limited to bounded work without a clean-pause promise until an external control path is verified.

## Registry recovery

The ignored `.local-cache/worker-messaging/registry.json` uses schema version 1. It records the run, issue, assigned harness and model, branch and worktree, pane and process generations, native ID, endpoint, timestamps, and state. It stores a brief digest rather than prompt text. Missing or corrupt records fail closed. For recovery, the coordinator correlates Git worktree and tmux observations with process start and native runtime identity because the CLI rejects an existing checkout without a matching registry owner.

## Coordinator live trial handoff

The live trial waits for the operator's decision on the three `Operator approval needed` paragraphs in [#176](https://github.com/tbhb/agent-orchestration-poc/issues/176). The coordinator records the selected server command, PID, socket, effective workspace roots, and baseline permission before launch. Use a disposable brief, branch, worktree, and tmux window. Never target tmux session 0.

Capture the launch JSON and the exact TUI argv. Verify its startup brief and selected model and effort. Query `thread/loaded/list` on the recorded socket, find the exact rollout thread ID, then call `thread/read` for that ID and compare `thread.cwd`, `thread.model`, and `thread.reasoningEffort` with the registry. Capture the effective roots from `thread/start.runtimeWorkspaceRoots`. Run a disposable worker `git add` and normal-hook `git commit` in its exclusive worktree. Record exit codes and redacted responses in [launcher evidence](../evidence/launcher.md) and the issue's named raw evidence files. A failed observation remains `unknown` and disables later sends.

Probe an unloaded thread, a stale pane or PID, a restarted runtime, and a trust prompt. Pause and clean up only the disposable worker. Follow the selected operator restoration procedure and recheck a fresh thread's roots and a Git-directory write denial against the recorded baseline. Revalidate every surviving or recovered thread before further sends. The fake-endpoint tests in this delivery do not establish any of these live outcomes.
