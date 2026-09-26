---
title: Coordinator handoff
description: Approved phase 1 state and the next actions for starting phase 2.
---

Date: 2026-09-26, late evening America/New_York. Previous coordinator session: `0c08c1dc-01da-4925-b0b5-05e7a9a20588`. Start a fresh `claude-fable-5-1[1m]` session with `@HANDOFF.md`. This snapshot includes merges through [PR #76](https://github.com/tbhb/agent-orchestration-poc/pull/76) at 22:56:47 UTC. Verify live state before acting.

## Current phase and operator decisions

The operator approved the [phase 1 checkpoint report](/project/phase-1-checkpoint/) on 2026-09-26 and asked to roll the coordinator session over. Phase 2 starts in the next session. Codex `gpt-6-sol` at high handles code and research, `gpt-6-astra` at medium handles reviews and design documents, and `codex exec review` provides the first review pass. Fable coordinates. Sonnet 5 only cross-checks bus semantics, credentials, and security. The operator chose strict typing everywhere, tracked in #77. Still open are the Project UI settings for Phase view group-by, Ready view sort by Priority, and workflow targets, plus whether #35 may create VMs and images when phase 3 starts.

Phase 0 approval and GitHub Pro confirmation remain recorded decisions. Ruleset `main` (24053242) is active. Ordinary reviewed PRs may be merged by the coordinator after green CI. Security policy, credentials, egress, and host changes still require the operator.

## Pull requests and in-flight work

Paths below are relative to `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc`. The live `gh pr list --state open` returned no PR on 2026-09-26. PRs #75 and #76 have merged, and issues #58, #62, #63, and #69 are closed. The [phase 1 command evidence](https://github.com/tbhb/agent-orchestration-poc/tree/dedf58fb223e086cc185a8a7e16a1f355d037185/reports/inputs/phase-1-history) preserves the earlier snapshot. Check the testing branch again before dispatch.

| Work | Branch | Worktree | Snapshot |
| --- | --- | --- | --- |
| Property and mutation testing gates, strict typing, #59, #60, #77 | `tooling/59-60-77-testing-and-strict` | `.worktrees/tooling-59-60-77-testing-and-strict` | Detached Codex `gpt-6-sol` high run was dispatched to build the checks and open its own PR. No PR appeared in the live list. Check its last-message file and log under the previous session's scratchpad, and confirm process state before treating it as active. |

The prior session's scratchpad is `/private/tmp/claude-501/-Users-tony-Code-github-com-tbhb-agent-orchestration-poc/0c08c1dc-01da-4925-b0b5-05e7a9a20588/scratchpad/`. Look for `codex-59-60-77.last.md` and `codex-59-60-77.log`. During this refresh, the log existed and the last-message file did not.

## Worker roster

No workers are provisioned. Codex runs are launched from the coordinator's shell. The testing branch is the remaining coding dispatch in the supplied roster. A worktree listing does not prove process liveness. Local `pgrep -f "codex exec"` returned a sysmond error during this refresh, so confirm its state from the run output and GitHub before redispatching. The bus roster and status bucket are still unbuilt. `agy` remains unused until the provisioner exists.

## Decisions since the last handoff

- The operator read the phase 1 checkpoint report, said it looks good, approved phase 1, and requested a fresh coordinator session for phase 2.
- The operator confirmed Codex `gpt-6-sol` at high for code and research, `gpt-6-astra` at medium for reviews and design documents, and `codex exec review` as the first pass. Fable coordinates. Sonnet 5 only cross-checks bus semantics, credentials, and security.
- The usage snapshot has Fable weekly usage at 41%, overall Claude weekly usage at 24%, and session usage at 34%, all consumed. Codex weekly usage has 99% remaining. Refresh the meters before dispatch.
- Functional core, imperative shell is binding. Every language needs boundary enforcement, property and mutation tests, duplicate-code and dead-code gates, and complexity limits. #58 through #63 track the requirements and research.
- The operator chose strict typing everywhere. Issue #77 removes pyrefly's test and experiment relaxations for `implicit-any-parameter` and `unannotated-return` and the matching Ruff `ANN` exemptions. [Decision 0002](/decisions/0002-python-type-checker/) records the earlier settings pending its update.
- Subagent definitions in `.claude/agents/` hold model and effort. The prose lint exempts raw gate notes under `research/gates/`. Codex-written pages are linted. The plan retains its existing exemption. Conventions live under `guides/`, and root plan and handoff files are pointers.
- Send permission requests to the operator through AskUserQuestion. Report Codex and agy blocks that project configuration could fix. Codex launches include `-c sandbox_workspace_write.network_access=true`.
- Keep the docs daemon available at `http://localhost:4322`. Recreate a 14-minute session heartbeat for cache continuity and worker check-ins.

## Gotchas discovered

- zsh does not word-split unquoted variables, and two coordinator scripts failed. Use explicit arguments or bash scripts.
- Branches predating workflow merges can lack CI. Rebase and verify the workflow definitions before review.
- Ruff needs exclusions for imported research and fenced Markdown code.
- Semicolons in citation lists fail the prose rules. Run Vale before handing pages back.
- `gh pr checks --watch` can return while a check is pending. Run `gh pr checks` afterward and confirm every check concluded success. The `main` ruleset refuses an early merge.
- Issue #6 was closed early and reopened. Check merged-PR evidence before closing work.
- Links into local git metadata fail in CI. Keep machine-local paths as code text.
- Claude auto mode denied merges, settings edits, and cleanup. The operator owns permission changes.
- Codex could not run Chromium in its sandbox. Use docs CI for rendering and internal links.
- The coordinator Bash tool caps commands at ten minutes. Launch longer Codex work detached and monitor it.
- Linked Codex worktrees need the common `.git` directory writable to stage and commit.
- Non-interactive shells may lack mise shims. Run project tools through mise.
- A case-insensitive `/INPUTS/` exclude previously hid `reports/inputs/`. Check ignored paths before staging evidence.
- The Astro dev daemon does not serve pages added by `git pull`. After a merge that adds pages, run `astro dev stop` in `docs/`, restart with `mise run docs:dev` from the repository root, and curl the new page before sending the operator its link.

## Next three actions

1. Verify live state, recreate the 14-minute heartbeat cron, and check the docs daemon. Review `tooling/59-60-77-testing-and-strict` when its PR opens, confirm every check succeeded, and merge it through the coordinator.
2. Dispatch #26 (embedded NATS in `agentd`) and #27 (`agentctl`) to Codex `gpt-6-sol` at high in separate worktrees. Each brief must state the functional core rule and required gates. Cite the cloned NATS sources at `nats-server` `3e8ddaa7fcdf2c6a0688f8872ca465eab08f1221` and `nats.go` `5adc9d5d34ce8e3b7b8b002c5bd502a8b7a323d3`. Put pure subjects, permissions, message envelopes, and claims in `internal/core/`, with NATS and SQLite calls in shell packages.
3. Dispatch retro tooling #15, #16, #17, and #70 through #74 to Codex as one or two small PRs. Dispatch #28 (registry and host-tmux backend) once #26 is in review.

## Verify before acting

Run `git status`, `git worktree list`, `gh pr list --state open`, and `gh issue list --state open`. Inspect Project 9 and the coordinator memory index at `~/.claude/projects/-Users-tony-Code-github-com-tbhb-agent-orchestration-poc/memory/MEMORY.md`. Compare PR heads, check conclusions, and the testing branch with this snapshot. Report discrepancies to the operator. Do not infer live workers from directories.

Recreate the 14-minute heartbeat cron in the new coordinator session and verify its next trigger. It also checks silent workers. No stalled worker was observed in phase 1, but the new session still needs the timer.

From the docs directory, run `mise exec -- pnpm exec astro dev status`. If it shows the daemon stopped, restart it through `mise run docs:dev` with the project's background-daemon procedure and port 4322. Verify the page responds at `http://localhost:4322`. Inspect the installed CLI help before selecting daemon flags. Do not start a duplicate listener.

Read the [plan](/project/plan/#operator-requirements-added-in-phase-1), the [coordinator inputs](https://github.com/tbhb/agent-orchestration-poc/blob/dedf58fb223e086cc185a8a7e16a1f355d037185/reports/inputs/phase-1-coordinator-notes.md), and the [retro actions](/retros/2026-09-26-phase-1/#action-items). Verify local permission settings without editing them. Resume `claude --resume 0c08c1dc-01da-4925-b0b5-05e7a9a20588` only if the handoff and durable records cannot recover needed context.
