---
title: "0005: property and mutation testing gates"
description: Selected property and mutation tools, score floors, and CI seed policy for the pure core.
---

## Status

Accepted 2026-09-26 for issues #59 and #60 after the coordinator's [property decision](https://github.com/tbhb/agent-orchestration-poc/issues/59#issuecomment-5850421709) and [mutation decision](https://github.com/tbhb/agent-orchestration-poc/issues/60#issuecomment-5850421848).

## Context

The functional core needs tests that explore generated inputs and measure whether assertions reject changes to its logic. The [testing research](https://github.com/tbhb/agent-orchestration-poc/tree/main/research/gates/testing) compared the tools against Go 1.27.1 and Python 3.14.6 before the core received code.

## Decision

Use `pgregory.net/rapid` v1.3.0 in `go.mod` and Hypothesis 6.168.1 in the Python dev group. Their properties run with ordinary tests in `mise run check`. Required CI sets a fixed `RAPID_SEED` and `RAPID_NOFAILFILE=1`. Hypothesis uses its built-in derandomized `ci` profile. Local runs use random seeds. A nightly workflow runs both languages with random seeds and files an issue containing the seeds and output if either fails.

Use gremlins 0.6.0 through mise for `internal/core/`, with floors of 90 percent for the share of covered mutants killed and for mutant coverage. Reject timed-out mutants separately because gremlins excludes them from both scores. Use mutmut 3.8.0 for `src/agent_orchestration_poc/core/`, delete its `mutants/` cache before each run, and require a score of at least 90 percent from `export-cicd-stats`. Count killed mutants against killed, survived, timed out, suspicious, and uncovered mutants.

Gate coverage on every pull request in `mise run check:coverage`. Go 1.27.1 statement profiles must reach 95 percent in `internal/core/` and 70 percent across shell packages, including `cmd/` and packages with no test files. Pin gobco 1.3.4 to measure at least 90 percent of Go core branch outcomes. Coverage.py 7.16.1 measures Python branches, with separate core floors of 95 percent for lines and 90 percent for branches. Python shell lines have a 70 percent floor when shell code exists. Pure tested functions make the threshold decisions from the Go profile, gobco output, and coverage.py JSON. `research/gates/testing/coverage-branches-87.md` records gobco's limits.

Run `mise run check:mutation` outside the fast `check` aggregate. Its CI job always reports a result on pull requests and pushes to `main`. It runs mutation tools only when core code or tests change, so it can be required without leaving an absent status.

## Consequences

Rapid offers typed generators and shrinking inside named Go subtests. Hypothesis integrates with pytest and has a built-in CI profile. The research rejected gopter because its type-changing generator mapping loses automatic shrinking, and `testing/quick` is frozen. Go-mutesting failed under Go 1.27.1. Cosmic-ray was slower in the trial, generated more equivalent comparison mutants, and edited the source tree during a run (research/gates/testing/notes.md §§1 through 4).

Issue #87 raised the mutation floors after the first real scores. Recalibrate only with a recorded run and a reviewed reason. Reopen this decision if the tools stop supporting the pinned language versions, the score includes persistent equivalent mutants, or mutation runtime makes the full-core job impractical.

## Evidence

The source clone commits, release tags, trials, and caveats are in `research/gates/testing/versions.md` and `research/gates/testing/notes.md`. The first repository scores and the gate failure after weakening a test are recorded in `reports/inputs/testing-gates-failing-examples-2026-09-26.md`.

Issue #87 first measurements, gate failures, and equivalent mutants are in `reports/inputs/coverage-floors-87-evidence-2026-09-26.md`.
