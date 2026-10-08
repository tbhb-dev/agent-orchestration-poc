---
title: "0011: dependency updates enter through coordinator-owned pull requests"
description: Research selection and deferred enablement for bounded dependency proposals.
---

## Status

[proposed] Selection recorded 2026-10-07 for [issue #91](https://github.com/tbhb-dev/agent-orchestration-poc/issues/91). This record selects Renovate for a later advisory trial. It does not enable a service or approve service-authored merges. The operator and the dependent workflow gates control activation.

## Context

[documented] The [research comparison](https://github.com/tbhb/agent-orchestration-poc/blob/research/91-dependency-updates/reports/inputs/dependency-update-research.md) reads Renovate source at `0dfb75020092789b7dc3f398e31259173f24b69f`, Dependabot source at `328836263e30e52540e77f0595a6b87b319271ce`, and GitHub's Dependabot options reference. It compares Go, uv, pnpm, mise, and full SHA GitHub Action pins at the repository's recorded versions.

[documented] The current workflow requires a worker PR authored by the implementer identity, an issue-number branch, an open `Refs` issue, approved review identity, and five required checks. A generated dependency PR has no exception to those contracts. The existing `lodash-es` alert repair belongs to [#102](https://github.com/tbhb-dev/agent-orchestration-poc/issues/102).

## Decision

[proposed] Use Renovate as the candidate advisory service because its versioned managers describe Go, uv, pnpm, mise, and Actions. The coordinator handles an unsupported mise backend, an unannotated Action SHA, or a failed updater manually. Service proposals remain advisory. The coordinator selects or creates an open issue with compliant labels and allowed paths. A dispatched worker produces the mergeable PR under the current identity policy.

[proposed] Cap routine Renovate PRs at two and vulnerability PRs at one through separate concurrent limits. Group routine patch and minor updates by ecosystem and update class. Keep security fixes separate. Keep each major migration separate from unrelated updates. The coordinator enforces the repository-wide count when proposals from other sources are present.

[proposed] A worker verifies release notes and source commits, exact pins, lockfile diffs, and stack rules before the worker PR. The coordinator arranges a different-model `tbhbbot` review. Activation waits for #92 and #93, the configuration validator with passing and failing fixtures, a real advisory proposal, and a coordinator-owned PR with the required `check`, `docs`, `pr-body`, `imported-research`, and `mutation` results, current approval, resolved threads, and an up-to-date branch. Operator-owned installation or credential changes stay outside the worker PR. A change to permit service-authored mergeable PRs needs a separate #83/#89 identity policy decision.

## Consequences

[inference] Renovate's broad manager coverage reduces manual discovery. It adds an operator-owned service dependency and a handoff step. The repository's bare Action SHAs need version comments before Renovate can track them, and its specific mise backends and lockfile formats need live validation. The proposed two-plus-one limit covers Renovate's separate security budget only if configured and observed as documented.

## Evidence

[documented] [Research and source links](https://github.com/tbhb/agent-orchestration-poc/blob/research/91-dependency-updates/reports/inputs/dependency-update-research.md) and the [evidence ledger](https://github.com/tbhb/agent-orchestration-poc/blob/research/91-dependency-updates/reports/inputs/dependency-update-evidence.md) distinguish source support from repository behavior. Revisit this selection if the live trial cannot handle a required ecosystem, cannot hold the combined proposal cap, or cannot pass the coordinator-owned PR gate.
