---
title: "0004: duplicate, dead, and complex code gates"
description: Tool choices and starting thresholds for duplicate code, dead code, and complexity.
---

## Status

Accepted 2026-09-26 for issues #62 and #63 as operator requirements.

## Context

The scaffold has too few functions to calibrate thresholds from a useful distribution. The research gate compared available tools and ran proposed checks on the current tree (research/gates/quality-gates/notes.md §§Summary, First run).

## Decision

Use jscpd 5.3.2 for exact duplicate blocks across Go, Python, and TypeScript at 50 tokens and 5 lines. Leave golangci-lint `dupl` off because it missed the cross-package clone in the scaffold. Use deadcode from `golang.org/x/tools` 0.50.0 with `-test ./...` for Go functions, retaining golangci-lint `unused` for other names. A wrapper turns deadcode output into a failure because deadcode itself exits zero on findings. Use vulture 2.16 at confidence 60 for Python, ignoring pytest hooks and fixtures (research/gates/quality-gates/notes.md §§Duplicate code, Dead code).

Enable golangci-lint 2.14.0 `gocognit` and `gocyclo` at 15, `funlen` at 60 lines and 40 statements with tests excluded, and `nestif` at 5. Use ruff 0.16.9 `C901`, `PLR0911`, `PLR0912`, `PLR0915`, and `PLR0917` at their defaults. Use Biome 2.5.14 cognitive complexity 15, function length 60, and parameter count 5 rules at error level (research/gates/quality-gates/notes.md §Complexity).

Leave `cyclop` off because it duplicates `gocyclo`. Leave `maintidx` off because its metric is experimental. Radon and xenon disagree with ruff on cyclomatic scores and do not supply a supported threshold for this tree. Pylint would add a second Python linter for duplication alone (research/gates/quality-gates/notes.md §§Duplicate code, Complexity).

## Consequences

`check:dupl` and `check:deadcode` join the `check` aggregate. Existing Go, ruff, and Biome tasks pick up complexity settings. Review deliberate duplicate suppressions and dead code false positives with a reason. Recalibrate all thresholds at the first retro with phase 2 code, using measured findings, false positives, and run times (research/gates/quality-gates/notes.md §§First run, CI shape).

## Evidence

The source commits, versions, and first-run results are in `research/gates/quality-gates/versions.md` and `research/gates/quality-gates/notes.md`. This PR records local failure probes in `reports/inputs/gates-failing-examples-2026-09-26.md`.
