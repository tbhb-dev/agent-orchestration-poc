---
title: Phase 1 checkpoint report
description: Foundation delivered, remaining quality gates, and decisions needed before phase 2.
---

Written 2026-09-26 against merges through [PR #68](https://github.com/tbhb/agent-orchestration-poc/pull/68) at 22:22:57 UTC. Phase 1 foundation is complete pending operator approval. Phase 2 requires boundary and testing gates before core code can merge, plus operator approval to begin.

## What's done

- [PR #19](https://github.com/tbhb/agent-orchestration-poc/pull/19) delivered the phase 0 retro and devlog. [PR #20](https://github.com/tbhb/agent-orchestration-poc/pull/20), [PR #22](https://github.com/tbhb/agent-orchestration-poc/pull/22), and [PR #23](https://github.com/tbhb/agent-orchestration-poc/pull/23) delivered the Go, docs-stack, and Python gates and conventions.
- [PR #21](https://github.com/tbhb/agent-orchestration-poc/pull/21) added pinned tools and checks. [PR #24](https://github.com/tbhb/agent-orchestration-poc/pull/24) imported 117 research files, with 996 exclusions and no holdbacks.
- [PR #25](https://github.com/tbhb/agent-orchestration-poc/pull/25) added `check`, `pr-body`, and `imported-research`. [PR #55](https://github.com/tbhb/agent-orchestration-poc/pull/55) added the Starlight site and `docs` CI.
- [PR #56](https://github.com/tbhb/agent-orchestration-poc/pull/56) configured Project fields and views and filed issues #26 through #54. Three UI settings still need the operator.
- [PR #57](https://github.com/tbhb/agent-orchestration-poc/pull/57) added the skeleton. [PR #64](https://github.com/tbhb/agent-orchestration-poc/pull/64) added worker instructions, README, and site pages, leaving root plan and handoff pointers.
- [PR #65](https://github.com/tbhb/agent-orchestration-poc/pull/65) added strict pyrefly and decision 0002. [PR #66](https://github.com/tbhb/agent-orchestration-poc/pull/66), [PR #67](https://github.com/tbhb/agent-orchestration-poc/pull/67), and [PR #68](https://github.com/tbhb/agent-orchestration-poc/pull/68) added boundary, quality-gate, and property and mutation testing research.
- The live query verifies ruleset `main` (24053242). It requires a PR and `check`. Only squash merges are permitted, and force pushes and deletion are blocked. The [retro](/retros/2026-09-26-phase-1/) covers all 15 merges and the ten-PR cadence.

## Decisions made and their evidence

The [coordinator inputs](https://github.com/tbhb/agent-orchestration-poc/blob/dedf58fb223e086cc185a8a7e16a1f355d037185/reports/inputs/phase-1-coordinator-notes.md) records the operator requirements and usage snapshot. Functional core, imperative shell is binding. Every language needs boundary, property, mutation, duplicate-code, dead-code, and complexity checks. [#58](https://github.com/tbhb/agent-orchestration-poc/issues/58), [#59](https://github.com/tbhb/agent-orchestration-poc/issues/59), [#60](https://github.com/tbhb/agent-orchestration-poc/issues/60), [#62](https://github.com/tbhb/agent-orchestration-poc/issues/62), and [#63](https://github.com/tbhb/agent-orchestration-poc/issues/63) track that work. Research has merged, but enforcement is not yet verified on `main`.

The [plan](/project/plan/#assignments) moves coding and research to `gpt-6-sol` at high and reviews and design documents to `gpt-6-astra` at medium. `codex exec review` provides the first review. Fable remains coordinator and Sonnet 5 cross-checks bus semantics, credentials, and security. `agy` waits for the provisioner. Revised assignments await operator confirmation.

[Decision 0001](/decisions/0001-go-linter/) selects golangci-lint. [Decision 0002](/decisions/0002-python-type-checker/) selects strict pyrefly with two test and experiment annotation relaxations. The [docs conventions](/guides/docs-stack-conventions/) record the renderer and devlog choices. The prose lint exempts raw gate notes and checks pages.

The coordinator may merge ordinary PRs after review and green CI. Security policy, credentials, egress, and host changes remain operator boundaries. Permission questions go through AskUserQuestion. Codex receives network access per launch. The coordinator keeps a 14-minute heartbeat and the operator's docs server at port 4322. These decisions are recorded in the inputs, not re-tested by this document run.

## Open questions

- Approve phase 1 and the start of phase 2 after its prerequisites merge.
- Confirm the revised models and effort levels.
- Keep or remove pyrefly's two annotation relaxations in tests and experiments.
- Complete the Phase view group-by, Ready view Priority sort, and Project workflow targets.
- Decide whether [#35](https://github.com/tbhb/agent-orchestration-poc/issues/35) may create VMs and images when phase 3 starts.

## Risks

- Usage limits come first. The input snapshot has 41% of weekly Fable usage, 24% of the overall weekly Claude limit, and 34% of the session limit consumed. Codex has 99% of its weekly limit remaining. These figures come from the operator snapshot. Capacity under phase 2 concurrency remains unknown.
- Boundary and quality-gate enforcement on `tooling/58-boundaries-and-gates` has not merged at this snapshot. Property and mutation research is merged, but executable enforcement remains unfinished.
- Worker provisioning and the bus remain unbuilt. Parallel work on #26 and #27 after approval and boundary enforcement is a planning assumption. Their integration and runtime permission behavior still need tests.
- Formal GitHub review turnaround is unknown because no submitted reviews appear on the 15 merged PRs. PR creation-to-merge times do not measure review quality.
- Local Chromium denial leaves docs rendering and link validation to CI for Codex. The plan retains its recorded 105-alert Vale exemption.

## Proposed next steps

Confirm the operator decisions, review the remaining enforcement work, and roll over from the [handoff](/project/handoff/) to a fresh Fable session. Merge boundary enforcement before dispatching [#26](https://github.com/tbhb/agent-orchestration-poc/issues/26) for embedded NATS and [#27](https://github.com/tbhb/agent-orchestration-poc/issues/27) for agentctl to Codex in parallel. Build the checks in [#59](https://github.com/tbhb/agent-orchestration-poc/issues/59) and [#60](https://github.com/tbhb/agent-orchestration-poc/issues/60) before the first core code merges. Keep the quality gates from #62 and #63 in that merge path. Track the retro follow-ups [#70](https://github.com/tbhb/agent-orchestration-poc/issues/70) through [#74](https://github.com/tbhb/agent-orchestration-poc/issues/74) in Project 9.
