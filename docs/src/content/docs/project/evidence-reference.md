---
title: Evidence and assessment reference
description: Sources for dated system, dependency, and design assumptions.
---

The [system assessment](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/experiments/00-system-assessment/evidence.md) and [versions](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/experiments/00-system-assessment/versions.md) are a 2026-09-26 snapshot. The records cover machine resources and installed tools, plus authentication observations, Apple Containers state, Tailscale, and Project 9's initial configuration. The [plan's assessment summary](/project/plan/#what-the-system-assessment-established) is historical, not a current inventory. The [phase 0 checkpoint](/project/phase-0-checkpoint/) and [phase 1 checkpoint](/project/phase-1-checkpoint/) describe outcomes at their stated times.

The [dependency clone manifest](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/experiments/00-system-assessment/dependency-clones.md) records source commits and nearest tags. Nearest tags are source history, not proof of the installed version. The [plan's dependency table](/project/plan/#dependency-sources) is a selection from that manifest. Read current pinned source and versioned documentation before making a code claim, as [AGENTS.md](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/AGENTS.md#evidence-and-dependencies) requires.

The [design sketch](/design/) defines starting scope, with [decision records](/decisions/) recording durable choices and [issues](https://github.com/orgs/tbhb-dev/projects/1) recording pending tests. The [phase 2 relay departure](/project/plan/#phase-2-bus-departure) is now governed by [decision 0010](/decisions/0010-agent-bus-relay/) and issues [#96](https://github.com/tbhb-dev/agent-orchestration-poc/issues/96), [#27](https://github.com/tbhb-dev/agent-orchestration-poc/issues/27), [#29](https://github.com/tbhb-dev/agent-orchestration-poc/issues/29), and [#28](https://github.com/tbhb-dev/agent-orchestration-poc/issues/28).

## Assumptions register

This register retains the eleven hypothesis-to-verification associations from the [2026-09-26 plan](/project/plan/#assumptions-register). Each cited source records findings from its date. It does not establish every runtime behavior in the assumption. Retros retire a row only after checking the verification in the right column.

| Assumption and use | Verification or disposition |
| --- | --- |
| Custom Project fields and API-created views for phase 1 Project setup. | [Phase 0 GitHub Projects research](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/experiments/00-system-assessment/github-projects-research.md). View creation remained doubtful. |
| JetStream multi-filter pull consumers, deduplication, KV compare-and-set and per-key TTL, group accounts, subject permissions, auth callout, leaf nodes, and embedded Go server for phase 2 bus and shared context. | [Phase 0 NATS research](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/experiments/00-system-assessment/nats-research.md), then phase 2 bus experiments. |
| Model capabilities and subscription usage limits for model assignments. | [Model research](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/experiments/00-system-assessment/model-research.md), [model inventory](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/experiments/00-system-assessment/model-inventory.md), and phase 2 checkpoint data. |
| Harness hooks, tools, permissions, and Linux support at installed versions for launch and phase 2 and 3 experiments. | [Phase 0 harness research](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/experiments/00-system-assessment/harness-research.md), then phase 2 and 3 experiments. |
| mise backends, tasks, and CI execution, prek stage, Biome, Starlight Mermaid, Vale, and pnpm behavior for phase 1 tooling and docs. | Phase 1 workers read cloned sources and versioned docs before configuration and recorded versions and sources in their PRs. The [phase 1 checkpoint](/project/phase-1-checkpoint/) records the outcome. |
| Apple `container` 1.4.1 networking, egress, resize, vsock, and memory return for container design and phase 3 experiments. | Phase 3 experiments on networking, egress, resize, vsock, and memory return. |
| shpool 0.11.5 attach, force attach, one-client limit, and restore modes for guest terminal design. | Phase 3 experiment 4. |
| Tailscale `tsnet` and `tailscale serve` identity headers for remote access design. | Phase 3 experiment 15. |
| xterm.js 6 addons and WKWebView WebGL limits, plus Tauri 2.12 shell behavior for terminal and UI design. | Phase 3 experiments 14 and 16 and the phase 5 UI slice. |
| Conventional Commits, squash merges, branch names, and Project field set for GitHub workflow. | Operator judgment rather than research. Retros revise them if they cost time. |
| React, React Router 8, Vite, Vitest, Playwright, Radix, xterm.js 6, and Tauri 2 APIs for phase 5 UI work and phase 1 docs. | Phase 5 frontend conventions gate and phase 1 Astro and Starlight docs-stack conventions gate. |

## Naming and sketch departures

The [phase 0 checkpoint](/project/phase-0-checkpoint/#decisions-made-and-their-evidence) records the choice of `agentd` as provisioner and later daemon, `agentctl` as its CLI, one root Go module, a shared Python helper package, pnpm workspaces, numbered experiments, and isolated `.worktrees/`. The optional guest supervisor remains an experiment outcome. The [plan's names](/project/plan/#names) and [departures](/project/plan/#departures-from-the-design-sketch) provide the original reasoning. The supposed `WORK_DESIGN.md` in the handoff did not exist. The messaging and memory bullets in `OPEN_ITEMS.md` were incorporated into the sketch, so phase 3 synthesis should cite that source rather than claim a missing import.
