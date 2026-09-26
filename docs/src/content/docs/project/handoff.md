---
title: Coordinator handoff
description: Phase 1 checkpoint state and the prerequisites for starting phase 2.
---

Date: 2026-09-26. Previous coordinator session: `0c08c1dc-01da-4925-b0b5-05e7a9a20588`. Start a fresh `claude-fable-5-1[1m]` session with `@HANDOFF.md`. This snapshot includes merges through [PR #68](https://github.com/tbhb/agent-orchestration-poc/pull/68) at 22:22:57 UTC. Verify live state before acting.

## Current phase and operator decisions

Phase 1 foundation is complete pending operator approval. Phase 2 has not started. The operator must approve the checkpoint and confirm revised model assignments. Other decisions cover pyrefly's two annotation relaxations, three Project UI settings, and whether #35 may create VMs and images. The [checkpoint report](/project/phase-1-checkpoint/) records the questions and risks.

Phase 0 approval and GitHub Pro confirmation remain recorded decisions. Ruleset `main` (24053242) is active. Ordinary reviewed PRs may be merged by the coordinator after green CI. Security policy, credentials, egress, and host changes still require the operator.

## Pull requests and in-flight work

Paths below are relative to `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc`. The saved `gh pr list` refresh contains no pending PR at its collection time. Branch names identify work across later merges. The [command evidence](https://github.com/tbhb/agent-orchestration-poc/tree/dedf58fb223e086cc185a8a7e16a1f355d037185/reports/inputs/phase-1-history) includes the initial list, refresh, and worktree inventory.

| Work | Branch | Worktree | Snapshot |
| --- | --- | --- | --- |
| Boundary, duplicate-code, dead-code, and complexity enforcement, #58, #62, #63 | `tooling/58-boundaries-and-gates` | `.worktrees/tooling-58-boundaries-and-gates` | Codex work in flight. A PR was still pending in the captured list. |
| Property and mutation research, #59 and #60 | `research/59-60-testing` | `.worktrees/research-59-60-testing` (removed) | [PR #68](https://github.com/tbhb/agent-orchestration-poc/pull/68) merged. The gates still need code. The final inventory confirms worktree cleanup. |
| Checkpoint documents, #69 | `docs/phase-1-checkpoint` | `.worktrees/docs-phase-1-checkpoint` | This document change. Coordinator review and merge follow CI. |

## Worker roster

No workers are provisioned. Codex runs are launched from the coordinator's shell. The boundary branch is the remaining coding dispatch in the supplied roster. A worktree listing does not prove process liveness. Capture its current status before redispatching. The bus roster and status bucket are still unbuilt. `agy` remains unused until the provisioner exists.

## Decisions since the last handoff

- Coding and research move to Codex `gpt-6-sol` at high. Reviews and design documents use `gpt-6-astra` at medium, with `codex exec review` first. Fable coordinates. Sonnet 5 cross-checks bus semantics, credentials, and security. Revised assignments await confirmation.
- The usage snapshot has Fable weekly usage at 41%, overall Claude weekly usage at 24%, and session usage at 34%, all consumed. Codex weekly usage has 99% remaining. Refresh the meters before dispatch.
- Functional core, imperative shell is binding. Every language needs boundary enforcement, property and mutation tests, duplicate-code and dead-code gates, and complexity limits. #58 through #63 track the requirements and research.
- Strict pyrefly replaces ty. The test and experiment settings relax `implicit-any-parameter` and `unannotated-return` pending operator review. [Decision 0002](/decisions/0002-python-type-checker/) records the settings.
- Subagent definitions in `.claude/agents/` hold model and effort. The prose lint exempts raw gate notes under `research/gates/`. Codex-written pages are linted. The plan retains its existing exemption. Conventions live under `guides/`, and root plan and handoff files are pointers.
- Send permission requests to the operator through AskUserQuestion. Report Codex and agy blocks that project configuration could fix. Codex launches include `-c sandbox_workspace_write.network_access=true`.
- Keep the docs daemon available at `http://localhost:4322`. Recreate a 14-minute session heartbeat for cache continuity and worker check-ins.

## Gotchas discovered

- zsh does not word-split unquoted variables, and two coordinator scripts failed. Use explicit arguments or bash scripts.
- Branches predating workflow merges can lack CI. Rebase and verify the workflow definitions before review.
- Ruff needs exclusions for imported research and fenced Markdown code.
- Semicolons in citation lists fail the prose rules. Run Vale before handing pages back.
- `gh pr checks --watch` returned early in this session. Confirm every required check concluded success for the current head.
- Issue #6 was closed early and reopened. Check merged-PR evidence before closing work.
- Links into local git metadata fail in CI. Keep machine-local paths as code text.
- Claude auto mode denied merges, settings edits, and cleanup. The operator owns permission changes.
- Codex could not run Chromium in its sandbox. Use docs CI for rendering and internal links.
- The coordinator Bash tool caps commands at ten minutes. Launch longer Codex work detached and monitor it.
- Linked Codex worktrees need the common `.git` directory writable to stage and commit.
- Non-interactive shells may lack mise shims. Run project tools through mise.
- A case-insensitive `/INPUTS/` exclude previously hid `reports/inputs/`. Check ignored paths before staging evidence.

## Next three actions

1. Verify live state and present the [checkpoint report](/project/phase-1-checkpoint/) for phase 1 approval, model confirmation, and the pyrefly decision. Complete this documentation PR's review and merge through the coordinator.
2. Review and merge `tooling/58-boundaries-and-gates`. Turn #59 and #60 research into implemented checks before core code merges, with #62 and #63 enforcement in the merge path.
3. After operator approval and boundary enforcement, dispatch #26 and #27 to Codex Sol at high in separate worktrees. Start the next coordinator session from this handoff and retain the 14-minute heartbeat.

## Verify before acting

Run `git status`, `git worktree list`, `gh pr list --state open`, and `gh issue list --state open`. Inspect Project 9 and the coordinator memory index at `~/.claude/projects/-Users-tony-Code-github-com-tbhb-agent-orchestration-poc/memory/MEMORY.md`. Compare PR heads, check conclusions, and the boundary branch with this snapshot. Report discrepancies to the operator. Do not infer live workers from directories.

Recreate the 14-minute heartbeat cron in the new coordinator session and verify its next trigger. It also checks silent workers. No stalled worker was observed in phase 1, but the new session still needs the timer.

From the docs directory, run `mise exec -- pnpm exec astro dev status`. If it shows the daemon stopped, restart it through `mise run docs:dev` with the project's background-daemon procedure and port 4322. Verify the page responds at `http://localhost:4322`. Inspect the installed CLI help before selecting daemon flags. Do not start a duplicate listener.

Read the [plan](/project/plan/#operator-requirements-added-in-phase-1), the [coordinator inputs](https://github.com/tbhb/agent-orchestration-poc/blob/dedf58fb223e086cc185a8a7e16a1f355d037185/reports/inputs/phase-1-coordinator-notes.md), and the [retro actions](/retros/2026-09-26-phase-1/#action-items). Verify local permission settings without editing them. Resume `claude --resume 0c08c1dc-01da-4925-b0b5-05e7a9a20588` only if the handoff and durable records cannot recover needed context.
