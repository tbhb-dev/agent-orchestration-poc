---
description: Repository foundation, quality requirements, and the phase 2 approval checkpoint.
title: Phase 1 foundation
date: 2026-09-26
authors: [codex]
phase: 1
tags: [workflow, tooling, research]
---

## What landed

Fifteen phase 1 PRs merged. [PR #19](https://github.com/tbhb/agent-orchestration-poc/pull/19) added the phase 0 retro and devlog. [PR #20](https://github.com/tbhb/agent-orchestration-poc/pull/20), [PR #22](https://github.com/tbhb/agent-orchestration-poc/pull/22), and [PR #23](https://github.com/tbhb/agent-orchestration-poc/pull/23) established the Go, docs, and Python research gates. [PR #21](https://github.com/tbhb/agent-orchestration-poc/pull/21) added pinned tools and local checks. [PR #24](https://github.com/tbhb/agent-orchestration-poc/pull/24) imported 117 research files with a manifest.

[PR #25](https://github.com/tbhb/agent-orchestration-poc/pull/25) added CI, [PR #56](https://github.com/tbhb/agent-orchestration-poc/pull/56) configured Project fields and filed issues #26 through #54, [PR #55](https://github.com/tbhb/agent-orchestration-poc/pull/55) built the docs site and docs CI, and [PR #57](https://github.com/tbhb/agent-orchestration-poc/pull/57) added the Go and Python skeleton. [PR #64](https://github.com/tbhb/agent-orchestration-poc/pull/64) added worker instructions and moved project pages into the site. [PR #65](https://github.com/tbhb/agent-orchestration-poc/pull/65) adopted strict pyrefly. [PR #66](https://github.com/tbhb/agent-orchestration-poc/pull/66), [PR #67](https://github.com/tbhb/agent-orchestration-poc/pull/67), and [PR #68](https://github.com/tbhb/agent-orchestration-poc/pull/68) recorded boundary, quality-gate, and testing research.

## Decisions and their evidence

[Decision 0001](/decisions/0001-go-linter/) selects golangci-lint. [Decision 0002](/decisions/0002-python-type-checker/) selects strict pyrefly. The [docs conventions](/guides/docs-stack-conventions/) record inline SVG Mermaid rendering and starlight-blog. The [command evidence](https://github.com/tbhb/agent-orchestration-poc/tree/dedf58fb223e086cc185a8a7e16a1f355d037185/reports/inputs/phase-1-history) verifies the active `main` ruleset requiring a PR and `check`.

The [coordinator inputs](https://github.com/tbhb/agent-orchestration-poc/blob/dedf58fb223e086cc185a8a7e16a1f355d037185/reports/inputs/phase-1-coordinator-notes.md) adds functional core, imperative shell, language boundary tools, property and mutation tests, and duplicate-code, dead-code, and complexity gates. The [plan](/project/plan/) shifts coding and research to Codex Sol at high and review and design documents to Astra at medium. Operator confirmation remains part of this checkpoint.

## Problems and how they were resolved

A handoff link to local git metadata failed the first CI run. Its correction passed CI. The docs branch needed a rebase to pick up workflows. Ruff exclusions stopped checks on imported research and fenced Markdown code. Semicolon citation lists needed a second Vale pass.

The operator adjusted local Claude permissions after merge and settings denials. Codex docs rendering stays in CI because Chromium was blocked locally. A named-check waiter is tracked in [#72](https://github.com/tbhb/agent-orchestration-poc/issues/72) after an early issue closure. The [retro](/retros/2026-09-26-phase-1/) records the other follow-ups and distinguishes PR elapsed time from unavailable review timing.

## What is next

The operator reviews the [phase 1 checkpoint](/project/phase-1-checkpoint/) and confirms assignments and pyrefly exceptions. Boundary and quality-gate enforcement continues on `tooling/58-boundaries-and-gates`. Property and mutation research has merged, but those gates still need code before core logic can merge. After approval and the boundary merge, Codex starts [#26](https://github.com/tbhb/agent-orchestration-poc/issues/26) and [#27](https://github.com/tbhb/agent-orchestration-poc/issues/27) in parallel. The next coordinator starts from the [regenerated handoff](/project/handoff/).
