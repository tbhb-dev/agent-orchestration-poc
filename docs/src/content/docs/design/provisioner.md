---
title: Host provisioner
description: The issue 28 SQLite registry, tmux backend, and harness launch recipes.
---

## Operations

`agentd serve --state-dir <absolute-path> --port 4222` hosts the embedded bus and a local mode 0600 Unix socket at `<state-dir>/agentd.sock`. `agentd group start|status|stop --state-dir <path>` manages the `build` tmux session. `agentd spawn --state-dir <path> --name <worker> --harness claude|codex|agy --model <id> --effort <level> --issue <n> --type feat --slug <slug> --brief <file>` creates the branch, worktree, bus identity, and worker window. `agentd list|capture|nudge|stop` operates on the recorded worker name. `capture` accepts `--lines` and `nudge` pastes only a short inbox pointer with bracketed paste before sending Enter separately.

The host backend uses a private tmux socket. Each worker gets a window in the `build` session, a branch named `<type>/<issue>-<slug>`, and a worktree at `.worktrees/<type>-<issue>-<slug>/`. The source brief is copied to a mode 0600 file under the daemon state directory. `stop` keeps the worktree for review and recovery. Failed starts remain in the registry for diagnosis.

The operations are package functions under `internal/provision` and are temporarily mounted on `agentd`. Wiring the corresponding operator commands into `agentctl` follows issue #27. The daemon socket is local to the operator account. No container backend or automatic restart is included.

## Registry

The [schema](https://github.com/tbhb/agent-orchestration-poc/blob/feat/28-registry-tmux/internal/registry/schema.sql) has `groups` and `workers` tables and `PRAGMA user_version = 1`. `groups` stores the repository path, tmux session, lifecycle state, and creation time. `workers` stores the group foreign key, unique name, harness, explicit model and effort, issue branch, worktree, brief and credential paths, tmux window id, lifecycle state, and timestamps. A group and worker can be requested, starting, running, stopping, stopped, or failed. [Decision 0005](/decisions/0005-sqlite-driver/) records the pure Go SQLite driver choice.

## Launch recipes

The pure `internal/core/launch` function builds argv and environment values from a worker specification. The shell passes the repository's common `.git` directory as a writable root so worktree workers can stage and commit. The worktree itself is the working directory. Credentials are passed as a path in `AGENTCTL_CREDS_FILE`, never as a seed value in argv or the environment.

| Harness | Approved recipe | Writable roots and limits |
| --- | --- | --- |
| Claude Code | `claude --permission-mode auto --settings <per-worker-file> --model <id> --effort <level>` | `--add-dir <common-git-dir>` supplements the worktree. The settings file enables the sandbox and automatic approval of sandboxed Bash. The required user-scope local binding setting remains an operator input. |
| Codex | `codex -s workspace-write -a never -c sandbox_workspace_write.network_access=true -c model_reasoning_effort="<level>" -m <id> -C <worktree>` | `--add-dir <common-git-dir>` permits staging and commits. The launch also sets `shell_environment_policy.inherit="all"` so tool shells receive the group, worker, bus URL, and credential path. |
| `agy` | `agy --sandbox --dangerously-skip-permissions --model <id> --effort <level> --prompt-interactive <brief-pointer>` | `--add-dir <common-git-dir>` requests access to the shared Git metadata. Whether the `agy` sandbox actually permits writes there needs an operator-run acceptance test. |

**Observed:** a private tmux integration test started a stand-in command and captured its brief. It then delivered the fixed nudge pointer and stopped its window and server. **Verified:** file backed SQLite tests reopened and queried the registry. **Untested:** real harness spawns and sandbox access to the bus and Git metadata await the operator's subscriptions and environment. The exact procedure is in the [issue #28 evidence](https://github.com/tbhb/agent-orchestration-poc/blob/feat/28-registry-tmux/reports/inputs/registry-tmux-28-evidence-2026-09-26.md).
