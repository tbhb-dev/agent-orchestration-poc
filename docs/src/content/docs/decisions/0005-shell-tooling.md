---
title: "0005: shell scripts use ShellCheck and shfmt"
description: Pinned shell analysis and formatting for repository scripts and future hooks.
---

## Status

Accepted 2026-09-26 for issue #30 (research/gates/shell/notes.md, ShellCheck and shfmt proposal).

## Context

Current repository scripts are POSIX `sh` files. Planned hooks and agent-image scripts will cross macOS Bash 3.2, Bash 5 in the image, zsh hook commands, and GNU and BSD userland. The research probes found interpreter differences that a source formatter alone cannot catch (research/gates/shell/notes.md, Bash, zsh, and userland sections).

ShellCheck 0.11.0 reports portability and common shell defects for sh and Bash scripts, while shfmt 3.14.0 parses and formats the selected dialect. Their versioned sources and commits are recorded in `research/gates/shell/versions.md` (ShellCheck `README.md:435-500`, shfmt `cmd/shfmt/shfmt.1.scd:23-78`).

## Decision

Pin ShellCheck 0.11.0 and shfmt 3.14.0 through mise. Run ShellCheck with `--severity=style` and shfmt with `-d -i 4 -ci` on `scripts/*.sh` in `check:shell`, include that task in the `check` aggregate, and use matching mise-backed prek hooks. Provide `fmt:shell` with the same shfmt settings. The current `sh` shebangs make ShellCheck apply POSIX portability rules.

## Consequences

The first formatter run changes only `scripts/check-experiments.sh`, `scripts/check-gofumpt.sh`, and `scripts/check-pr-body.sh`. ShellCheck does not report findings in the eight scripts, so no exemptions are needed. The imported `research/imported/verify.sh` remains immutable and outside the gate (research/gates/shell/notes.md, ShellCheck and shfmt proposal).

The task and prek matcher cover current repository-owned shell scripts. Add hook and image script paths to both when those files are added. ShellCheck does not analyze zsh or fish semantics, and neither tool verifies interpreter selection, subprocess behavior, hook protocols, or GNU versus BSD flags. Test those separately on the target runtime. Revisit the pins or rule scope when an agent-image Bash version is pinned or shell code expands beyond `scripts/`.

## Evidence

`mise exec -- shellcheck --severity=style scripts/*.sh` did not report issues before formatting. `mise exec -- shfmt -d -i 4 -ci scripts/*.sh` named exactly the three scripts above. `mise run fmt:shell` applied those changes and `mise run check:shell` passed. The Bash 3.2, source-built Bash 5.3, and zsh 5.9 probe commands and outputs are recorded in `research/gates/shell/notes.md` with source versions in `research/gates/shell/versions.md`.
