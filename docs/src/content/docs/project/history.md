---
title: Project history
description: Phase 0 approval and the phase 1 foundation merged on September 26, 2026.
---

## Phase 0, 2026-09-26

The initial scaffold commit `7a57116` added the operator handoff, design sketch, and project scaffold. Phase 0 assessed the host, read dependency sources, tested model access, and produced the proposed plan. The operator then approved the revised plan and model assignments.

- [PR #1](https://github.com/tbhb/agent-orchestration-poc/pull/1) added the phase 0 plan and checkpoint report, with the coordinator handoff and system assessment.

- [PR #2](https://github.com/tbhb/agent-orchestration-poc/pull/2) recorded operator approval of the plan and model assignments, with GitHub Pro confirmed.

## Phase 1 so far, 2026-09-26

The following PRs merged before issue #11's documentation work. Phase 1 remains in progress until its checkpoint is approved.

| PR | What merged |
| --- | --- |
| [#19](https://github.com/tbhb/agent-orchestration-poc/pull/19) | The phase 0 retrospective and first devlog entry. |
| [#20](https://github.com/tbhb/agent-orchestration-poc/pull/20) | The Go research gate, conventions, path-scoped rules, and decision 0001 choosing golangci-lint. |
| [#21](https://github.com/tbhb/agent-orchestration-poc/pull/21) | Pinned tools, linter configurations, prek hooks, and the initial repository guards. |
| [#22](https://github.com/tbhb/agent-orchestration-poc/pull/22) | The Astro, Starlight, and starlight-blog research gate and docs stack conventions. |
| [#23](https://github.com/tbhb/agent-orchestration-poc/pull/23) | The Python 3.14, uv, Ruff, pytest, and typing research gate, conventions, and rules. |
| [#24](https://github.com/tbhb/agent-orchestration-poc/pull/24) | The scanned research import with checksums, exclusions, and a manifest. |
| [#25](https://github.com/tbhb/agent-orchestration-poc/pull/25) | The check, PR-body, and imported-research GitHub Actions jobs. |
| [#55](https://github.com/tbhb/agent-orchestration-poc/pull/55) | The Starlight site, build-time Mermaid, devlog plugin, link validation, and docs CI. |
| [#56](https://github.com/tbhb/agent-orchestration-poc/pull/56) | Project fields and views, plus 29 phase 2 and 3 issues numbered #26 through #54. View grouping and sorting still need operator UI steps. |
| [#57](https://github.com/tbhb/agent-orchestration-poc/pull/57) | The root Go module, version-printing commands, Python library and tests, and monorepo placeholders. |

After the first green CI run, the coordinator enabled the `main` ruleset requiring a PR and `check`, with squash-only merges and protection against force pushes and deletion. See [workflow](/workflow/) for the verified configuration.

The [phase 0 report](/project/phase-0-checkpoint/), [dated handoff](/project/handoff/), [retro](/retros/2026-09-26-phase-0/), and [first devlog](/devlog/2026-09-26-phase-0-done-phase-1-started/) preserve their original reporting moments. Their pending-work statements should be read with those dates. This page was checked against `git log --oneline main` and `gh pr list --state merged --limit 20` on 2026-09-26.
