# Coordinator handoff

Date: 2026-09-26, evening. Previous coordinator session: `0b1b7917-950a-4135-8c89-7951a84c8690`. Start the new Claude Code session on `claude-fable-5-1[1m]` with `@HANDOFF.md`.

## Current phase and operator decisions

Phase 0 is complete pending the operator's approval of the revised plan as a whole and the model and effort assignments. Permission modes, concurrency of three workers per harness, unattended `agy`, squash-only merges, the evidence-commit policy, and coordinator-managed branch protection are approved or applied. The operator must also confirm whether the `tbhb` account has GitHub Pro, which is needed to enforce branch protection on this private personal repository. See [PLAN.md](PLAN.md), Status, GitHub workflow, Concurrency, Permission modes, and Phase 0; and [the checkpoint report](reports/phase-0-checkpoint.md), Open questions.

## Open pull requests

[PR #1](https://github.com/tbhb/agent-orchestration-poc/pull/1) is the only open PR. It carries the revised phase 0 plan on `docs/phase-0-plan`, four commits above `main` at `7a57116`, and awaits operator approval before a squash merge. No issues exist yet; the [Project](https://github.com/users/tbhb/projects/9) has no items.

## Worker roster

No workers are provisioned or running. Phase 0 used one-shot coordinator subagents for system assessment, dependency clones, the initial commit, permission facts, model inventory, model research, harness research, GitHub Projects research, and NATS research; all have finished.

## Decisions since the operator handoff

See [PLAN.md](PLAN.md): Names; Repository layout; GitHub workflow; Retrospectives, devlog, and mechanical checks; Coordinator session rollover; The build group; Concurrency; Permission modes; Models and effort levels; Dependency sources; Phases; Departures from the design sketch; Assumptions register; Research gates for languages and stacks; Standing rules for workers; and Open questions for the operator. The [phase 0 decisions brief](reports/inputs/phase-0-decisions.md) preserves the inputs.

## Gotchas discovered

- `codex exec` in a linked worktree needs `--add-dir <repo>/.git` to stage and commit; see [PLAN.md](PLAN.md), Permission modes, Codex.
- Mise shims are absent from non-interactive shells; run provisioned processes and CI steps through mise. See [PLAN.md](PLAN.md), What the system assessment established.
- The operator's Codex config inherits only core environment variables and strips names matching `*KEY*`, `*SECRET*`, or `*TOKEN*` from tool shells. See [PLAN.md](PLAN.md), Permission modes, Codex.
- A subagent lead stalled for nearly two hours after its sub-reports finished. Give every dispatch longer than fifteen minutes a heartbeat monitor. See [PLAN.md](PLAN.md), Retrospectives, devlog, and mechanical checks.
- Git's `info/exclude` is case-insensitive on this filesystem: `/INPUTS/` in the common [exclude file](../../.git/info/exclude) hid `reports/inputs/`. Check ignore behavior when adding case-variant paths.
- The operator's Codex config sets `approvals_reviewer = "auto_review"`; `approval_policy = "never"` avoids invoking that reviewer. See [PLAN.md](PLAN.md), Permission modes, Codex.
- Attribution trailers are forbidden in commits and PR bodies. The PR body becomes the squash commit body. See [PLAN.md](PLAN.md), GitHub workflow, Commits and Pull requests.

## Next three actions

1. If the operator has approved the revised plan and model assignments, squash merge PR #1 and record the GitHub Pro answer.
2. Dispatch phase 1 items 1 (tooling), 1a (Go research gate), 1b (Python research gate), and 2 (skeleton) in parallel worktrees using the models and efforts in [PLAN.md](PLAN.md). Name the cloned sources each brief must read, as recorded in [dependency-clones.md](experiments/00-system-assessment/dependency-clones.md). Gate skeleton code on the Go and Python research outputs.
3. Run the first `codex exec` devlog entry for phase 0 under `reports/devlog/` and open the phase 0 retro as the first retro. The retro must propose at least one mechanical check; the silent-worker timer and case-insensitive exclude are candidates. See [PLAN.md](PLAN.md), Retrospectives, devlog, and mechanical checks.

## Verify before acting

Run `git status` on `main` and this worktree; inspect `gh pr view 1`, the Project board, and the coordinator's memory index at `~/.claude/projects/-Users-tony-Code-github-com-tbhb-agent-orchestration-poc/memory/MEMORY.md`. The index loads automatically, and its linked files contain today's operator preferences. Read them before acting. Report any discrepancy with this document to the operator. See [PLAN.md](PLAN.md), Coordinator session rollover.
