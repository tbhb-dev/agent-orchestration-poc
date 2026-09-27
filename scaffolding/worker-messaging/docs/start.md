# Temporary worker launcher

This issue #176 scaffold is replaced by the production provisioner in [#28](https://github.com/tbhb-dev/agent-orchestration-poc/issues/28).

## Launch and inspect

The coordinator supplies an explicit `unix:///absolute/socket/path` endpoint for each Codex launch. The launcher records that endpoint and passes it to the interactive TUI with `--remote`. The selected model and effort remain explicit. The brief is the startup prompt. The command supplies no client-side `--add-dir` or writable-root override. The operator must approve and configure the app server for this socket before a live trial. There is no default endpoint.

For Codex, the launcher first creates a direct child of this repository's `.worktrees/` directory and records its owner. It runs `mise run vale:sync` there before starting the sandboxed worker. A failed sync returns a `blocked` run without registering trust or starting the TUI. Retry the same launch request after fixing the sync failure. The launcher checks the recorded endpoint for an existing exact-path trust entry, then persists a pending write before sending `config/batchWrite` to register `trusted` in the server account's user configuration. It reads `config/read` with that worktree as `cwd` and `includeLayers: true` before starting the interactive pane. An existing entry, failed write, or mismatched read-back leaves the run `blocked` and prevents TUI startup. The registry records the time and result of each attempt. This temporary user-config write is covered by the operator's 2026-09-27 scaffold approval. The containerized session-group design sets trust at container start.

```sh
mise run worker:launch -- --name alice --issue 176 --harness codex --model gpt-6-sol --effort high --branch tooling/176-alice --worktree /absolute/path/to/.worktrees/tooling-176-alice --brief-file /absolute/path/to/brief.md --endpoint unix:///operator/recorded/socket.sock
mise run worker:readiness -- <run-id>
mise run worker:status -- <run-id>
mise run worker:cleanup -- <run-id>
```

Each command returns JSON. Launch includes `run_id`, `state`, `reason`, `endpoint`, and `observed_at`. A new worktree branches from `origin/main` after a fetch. The Codex launch passes the shim path, writable `PREK_HOME`, and stage-one Git identity through per-thread `shell_environment_policy.set` overrides so remote server commands receive them. Readiness checks the tmux pane and process generations before treating trust text as a block. On the recorded Codex endpoint, `thread/list` must identify one thread in the worktree created after launch whose first-message preview matches the brief after Codex strips any `## My request for Codex:` prefix and surrounding whitespace. That ID must appear in `thread/loaded/list`, and `thread/read` must return the same ID with the recorded cwd, model, and effort. For a loaded ID, the launcher also reads `thread/resume.runtimeWorkspaceRoots` and requires the recorded common Git directory. A missing, ambiguous, or unloaded thread cannot become ready. `ready` and `busy` exit 0, a trust prompt or unsupported agy send path exits 2 as `blocked`, and missing or stale identity exits 3 as `unknown`.

Status returns the same readiness at the top level and under `readiness`. Its `status` object reports an advisory #178 snapshot from `.local-cache/worker-messaging/status/<run-id>.json`, including that relative `source`, `age_seconds`, and `availability`. A matching run ID, pane generation, and timestamp are required. A record at most 120 seconds old is `fresh`. A fresh record cannot override `unknown` readiness.

Later Codex input uses `codex queue` only after a fresh `ready` or `busy` result. This scaffold has no send command. Queue acceptance is not delivery proof. Claude remains `unknown` until #187 supplies a correlated live `ListAgents` result tied to session ID, PID and start, pane generation, cwd, peer handle, observation time, and brief uptake. Agy is limited to bounded work without a clean-pause promise until an external control path is verified.

After stopping the worker, `worker:cleanup` removes that run's exact trust key with a null replace edit and reads the same cwd to confirm absence. A project entry whose `trust_level` is JSON null confirms removal, as observed on the dedicated server. It also recovers a pending write if registration was interrupted after preflight. It returns `removed` with exit 0 on confirmation or `blocked` with exit 2 on a failed edit or read-back. A run blocked by a pre-existing entry or failed preflight cannot remove an entry. The coordinator handles tmux and worktree disposal separately.

## Registry recovery

The ignored `.local-cache/worker-messaging/registry.json` uses schema version 1. It records the run, issue, assigned harness and model, branch and worktree, pane and process generations, native ID, endpoint, timestamps, and state. It stores a brief digest rather than prompt text. Missing or corrupt records fail closed. For recovery, the coordinator correlates Git worktree and tmux observations with process start and native runtime identity because the CLI rejects an existing checkout without a matching registry owner.

## Coordinator live trial handoff

The operator approved exact-worktree trust registration for this scaffold on 2026-09-27. The coordinator records the selected server command, PID, socket, effective workspace roots, and baseline permission before launch. Use a disposable brief, branch, worktree, and tmux window. Never target tmux session 0.

Capture the launch JSON and the exact TUI argv. Verify its startup brief and selected model and effort. Query `thread/list` on the recorded socket, identify the unique startup thread from its cwd, creation time, and first-message preview, then match that ID in `thread/loaded/list`. Call `thread/read` for the ID and compare `thread.cwd`, `thread.model`, and `thread.reasoningEffort` with the registry. The launcher requests `thread/resume` only after a loaded ID and matching readback, with `excludeTurns` and no configuration overrides, then records the server's `runtimeWorkspaceRoots`. This attaches an observation client to the loaded thread until the socket closes. Capture the original TUI's `thread/start.runtimeWorkspaceRoots` response when possible for independent confirmation. Run a disposable worker `git add` and normal-hook `git commit` in its exclusive worktree. Record exit codes and redacted responses in [launcher evidence](../evidence/launcher.md) and the issue's named raw evidence files. A failed observation remains `unknown` and disables later sends.

Probe an unloaded thread, a stale pane or PID, a restarted runtime, and a trust prompt. Pause and clean up only the disposable worker. Follow the selected operator restoration procedure and recheck a fresh thread's roots and a Git-directory write denial against the recorded baseline. Revalidate every surviving or recovered thread before further sends. The fake-endpoint tests in this delivery do not establish any of these live outcomes.
