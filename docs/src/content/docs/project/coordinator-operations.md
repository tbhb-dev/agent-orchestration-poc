---
title: Coordinator operations
description: Durable dispatch, retrospective, and session continuity policy.
---

The coordinator dispatches work from [Project 9](https://github.com/users/tbhb/projects/9) and issues. The [workflow](/workflow/) and [AGENTS.md](https://github.com/tbhb/agent-orchestration-poc/blob/main/AGENTS.md) govern branches, worktrees, commits, review, checks, and merges. Historical assignments and phase task order remain in the [plan](/project/plan/) until part B, with outcomes in [checkpoints](/project/phase-1-checkpoint/) and [history](/project/history/).

## Dispatch and supervision

Give every worker its own issue, branch, worktree, explicit harness, model, and effort. Keep the assigned acceptance criteria and evidence requirements in the brief. Workers push before reporting completion. Do not treat a captured pane as a substitute for committed work. The approved concurrency starting point was three interactive workers per harness, subject to observed rate and quality data at the phase 2 checkpoint. The standing roster and earlier bootstrap method in [plan, The build group](/project/plan/#the-build-group) are dated plans, not a live roster. The [phase 0 checkpoint](/project/phase-0-checkpoint/) records the operator approval.

Check on silent workers at least every 15 minutes. Recreate the 14-minute session cron at rollover until the bus supplies last-seen status. The [phase 1 inputs](https://github.com/tbhb/agent-orchestration-poc/blob/main/reports/inputs/phase-1-coordinator-notes.md) and [plan, Retrospectives](/project/plan/#retrospectives-devlog-and-mechanical-checks) record the requirement. Treat the old bus status proposal as future work.

Keep the Astro background docs daemon available to the operator at `http://localhost:4322`, as directed in the [phase 1 operator requirements](/project/plan/#operator-requirements-added-in-phase-1).

## Retrospectives and devlog

Run a retrospective at every phase checkpoint and after every ten merged PRs in a phase. Include bus response times when available, review and CI failures, permission denials, restarts, blocked items, and coordinator interventions. Each retrospective proposes a mechanical check or explains why none applies. File action items as issues. Codex writes the retrospective and the dated devlog from raw inputs. Write a devlog entry on working days with merges, experiment results, or decisions and at checkpoints. See [plan, Retrospectives](/project/plan/#retrospectives-devlog-and-mechanical-checks), [phase 1 retro](/retros/2026-09-26-phase-1/), and [devlog](/devlog/).

## Session continuity

Keep durable decisions in issues, decision records, and repository pages. Keep working facts in coordinator memory and current state in a handoff. Workers continue independently when the coordinator rolls over. Review live state before relying on it after takeover. The six-step checked-in handoff sequence in [plan, Coordinator session rollover](/project/plan/#coordinator-session-rollover) and the [archived handoff](/project/handoff/) are historical. [Issue #123](https://github.com/tbhb/agent-orchestration-poc/issues/123) specifies the replacement procedure, including a reviewed ignored live handoff, regenerated snapshots at takeover, and archive after takeover. Until that issue is merged, use current operative instructions and do not publish the plan's old sequence here.
