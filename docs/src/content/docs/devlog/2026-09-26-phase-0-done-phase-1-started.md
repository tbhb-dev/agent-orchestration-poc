---
description: Phase 0 approval and the first phase 1 dispatches on September 26.
title: Phase 0 done, phase 1 started
date: 2026-09-26
authors: [codex]
phase: 1
tags: [workflow, tooling, research]
---

## What landed

[PR #1](https://github.com/tbhb/agent-orchestration-poc/pull/1) merged `PLAN.md`, [phase 0 checkpoint report](/project/phase-0-checkpoint/), `reports/inputs/phase-0-decisions.md`, `HANDOFF.md`, and the assessment under `experiments/00-system-assessment/`. [PR #2](https://github.com/tbhb/agent-orchestration-poc/pull/2) recorded the operator's approval in `HANDOFF.md`. Both merged on September 26.

Phase 1 began with issues [#3 through #14](https://github.com/tbhb/agent-orchestration-poc/issues) filed and four dispatches in isolated worktrees. Tooling (#3), the Go research gate (#4), the Python research gate (#5), and the docs stack research gate (#8) had been dispatched. Their results were still pending.

## Decisions and their evidence

The operator approved the revised plan and model assignments and confirmed GitHub Pro. `HANDOFF.md` records the answers. `experiments/00-system-assessment/model-inventory.md` records a call to every assigned model, while `experiments/00-system-assessment/permission-facts.md` separates verified flags from runtime behavior that still needs testing.

`PLAN.md`, Names and Repository layout, selects `agentd` as the bootstrap provisioner, `agentctl` as the CLI, one root Go module, a shared Python helper package, and worktrees for each worker. [phase 0 checkpoint report](/project/phase-0-checkpoint/) and `reports/inputs/phase-0-decisions.md` record the evidence and reasoning behind those choices.

`PLAN.md`, GitHub workflow, sets squash merges, Conventional Commits with `Refs:`, coordinator review, and a `main` ruleset after the first green CI run. `PLAN.md`, Retrospectives, devlog, and mechanical checks, sets a check-in for dispatches longer than fifteen minutes after a phase 0 subagent stall.

## Problems and how they were resolved

The first `codex exec` run could not commit from a linked worktree because its common `.git` directory was outside the writable paths. The launch procedure now adds that directory with `--add-dir`. `HANDOFF.md` records it.

The common `.git/info/exclude` rule `/INPUTS/` hid `reports/inputs/` on the case-insensitive filesystem. After the findings were gathered, the coordinator removed the entry from the exclude file the same evening. `HANDOFF.md` also became stale when its own PR merged. The [phase 0 retrospective](/retros/2026-09-26-phase-0/) tracks a follow-up check.

Two PRs merged before CI or branch protection existed and did not have a recorded review. The plan schedules CI first, followed by a `main` ruleset after a green run. This remains pending.

## What is next

Review the four dispatches and use the Go and Python research results to establish the prerequisites for skeleton code. Land the tooling checks and CI, then enable the `main` ruleset after its first green run. Continue the docs site and move the retro and devlog into it when ready. `PLAN.md`, Retrospectives, devlog, and mechanical checks, records that path.
