---
title: Coordinator handoff
description: Coordinator state as of the evening of 2026-09-26 after phase 0 approval.
---

This is the handoff as of its recorded date. The coordinator has Codex regenerate it at every checkpoint and session rollover. Verify live state before acting. Later merges are recorded in [project history](/project/history/).

Date: 2026-09-26, evening, after operator approval. Previous coordinator session: `0b1b7917-950a-4135-8c89-7951a84c8690`. Start the new Claude Code session on `claude-fable-5-1[1m]` with `@HANDOFF.md`.

## Current phase and operator decisions

Phase 0 is complete. The operator approved the revised plan and the model and effort assignments ("I approve the plan") and confirmed the `tbhb` account has GitHub Pro. Permission modes, concurrency of three workers per harness, unattended `agy`, squash-only merges, the evidence-commit policy, and coordinator-managed branch protection are approved or applied. The coordinator enables a ruleset on `main` after the first green CI run in phase 1. See [PLAN.md](/project/plan/), Status, GitHub workflow, Concurrency, Permission modes, and Phase 0. And [the checkpoint report](/project/phase-0-checkpoint/), Open questions.

## Open pull requests

[PR #1](https://github.com/tbhb/agent-orchestration-poc/pull/1) was squash-merged into `main` as `7cac91a` (`docs: add the phase 0 plan, checkpoint report, and assessment evidence (#1)`). Its `docs/phase-0-plan` branch and worktree are gone. The only open PR contains this update on `docs/handoff-after-approval`. The coordinator merges it itself. No issues exist yet. The [Project](https://github.com/users/tbhb/projects/9) has no items.

## Worker roster

No workers are provisioned or running. Phase 0 used one-shot coordinator subagents for system assessment, dependency clones, the initial commit, permission facts, model inventory, model research, harness research, GitHub Projects research, and NATS research. All have finished.

## Decisions since the operator handoff

See the sections in [PLAN.md](/project/plan/) covering Names, Repository layout, GitHub workflow, Retrospectives, devlog, and mechanical checks, Coordinator session rollover, The build group, Concurrency, Permission modes, Models and effort levels, Dependency sources, Phases, Departures from the design sketch, Assumptions register, Research gates for languages and stacks, Standing rules for workers, and Open questions for the operator. The [phase 0 decisions brief](https://github.com/tbhb/agent-orchestration-poc/blob/main/reports/inputs/phase-0-decisions.md) preserves the inputs.

## Gotchas discovered

- `codex exec` in a linked worktree needs `--add-dir <repo>/.git` to stage and commit. See [PLAN.md](/project/plan/), Permission modes, Codex.
- Mise shims are absent from non-interactive shells. Run provisioned processes and CI steps through mise. See [PLAN.md](/project/plan/), What the system assessment established.
- The operator's Codex config inherits only core environment variables and strips names matching `*KEY*`, `*SECRET*`, or `*TOKEN*` from tool shells. See [PLAN.md](/project/plan/), Permission modes, Codex.
- A subagent lead stalled for nearly two hours after its sub-reports finished. Give every dispatch longer than fifteen minutes a heartbeat monitor. See [PLAN.md](/project/plan/), Retrospectives, devlog, and mechanical checks.
- Git's `info/exclude` is case-insensitive on this filesystem: `/INPUTS/` in the common exclude file hid `reports/inputs/`. Check ignore behavior when adding case-variant paths.
- The operator's Codex config sets `approvals_reviewer = "auto_review"`. `approval_policy = "never"` avoids invoking that reviewer. See [PLAN.md](/project/plan/), Permission modes, Codex.
- Attribution trailers are forbidden in commits and PR bodies. The PR body becomes the squash commit body. See [PLAN.md](/project/plan/), GitHub workflow, Commits and Pull requests.

## Next three actions

1. Start phase 1 in a fresh coordinator session. Dispatch items 1 (tooling, including the first batch of mechanical checks and `mise install`), 1a (Go research gate), 1b (Python research gate), and 2 (skeleton) in parallel worktrees using the models and efforts in [PLAN.md](/project/plan/). Specify the cloned sources each brief must read, as recorded in [dependency-clones.md](https://github.com/tbhb/agent-orchestration-poc/blob/main/experiments/00-system-assessment/dependency-clones.md). Gate skeleton code on the Go and Python research outputs.
2. Run the first `codex exec` devlog entry for phase 0 under `reports/devlog/` and the phase 0 retro as the first retro. The retro must propose at least one mechanical check. The silent-worker timer and case-insensitive exclude are candidates. See [PLAN.md](/project/plan/), Retrospectives, devlog, and mechanical checks.
3. When CI merges, enable the `main` ruleset with a pull request requirement and required CI job. Block force pushes and deletion. Record it in the phase 1 checkpoint report.

## Verify before acting

Run `git status` on `main` and this worktree. Inspect `gh pr view 1`, the Project board, and the coordinator's memory index at `~/.claude/projects/-Users-tony-Code-github-com-tbhb-agent-orchestration-poc/memory/MEMORY.md`. The index loads automatically, and its linked files contain today's operator preferences. Read them before acting. Report any discrepancy with this document to the operator. See [PLAN.md](/project/plan/), Coordinator session rollover.
