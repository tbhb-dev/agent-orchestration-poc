---
title: Plan extraction outline
description: Proposed short plan structure and maintenance rule for part B.
---

[Issue #154](https://github.com/tbhb-dev/agent-orchestration-poc/issues/154) creates destination pages while preserving the current [plan](/project/plan/) for review. [Part B](https://github.com/tbhb-dev/agent-orchestration-poc/issues/155) shortens it and retargets worker instructions and backlinks. The classification and one-to-one section mapping are in the issue #154 pull request's evidence table.

## Proposed short-plan outline

1. Purpose and scope of the PoC, linked to the [design sketch](/design/) and [decisions](/decisions/).
2. Phase boundaries and operator checkpoints, using the source [phase sections](/project/plan/#phases) and the compact outline below. Link the dated [checkpoints](/project/phase-0-checkpoint/) and [organization Project](https://github.com/orgs/tbhb-dev/projects/1) rather than copying task lists.
3. Navigation to [worker policy](/project/worker-policy/), [coordinator operations](/project/coordinator-operations/), [harness reference](/project/harness-reference/), [evidence reference](/project/evidence-reference/), [workflow](/workflow/), [guides](/guides/), and [history](/project/history/).

Only purpose, phase boundaries, and navigation enter the plan. Work items, order, and status belong in issues and the organization Project. Durable choices belong in decision records or focused policy pages. Dated outcomes belong in checkpoint reports. Part B must preserve every operator requirement through a named destination. It must mark superseded statements as history and retarget the audited backlinks before removing plan sections.

| Phase | Exit condition and operator checkpoint |
| --- | --- |
| 0: orientation and assessment | Operator approves the revised plan and model and effort assignments after the retro and handoff regeneration. The [phase 0 checkpoint](/project/phase-0-checkpoint/) records completion. |
| 1: repository foundation | Foundation, research import and manifest are merged, and Project 9 reflects the plan. Regenerate the handoff, run the retro, and present the [phase 1 checkpoint](/project/phase-1-checkpoint/) to the operator. |
| 2: bootstrap orchestration | One worker of each harness receives a brief and exchanges messages with the coordinator and peers. Each reports status. Review observed limits and assignments with the operator, regenerate the handoff, and run the retro before the checkpoint report. |
| 3: research and experiments | Give the operator results and proposed decisions, including a supported shared-authentication approach per harness or a documented limit and alternative. Regenerate the handoff and run the retro before the checkpoint report. |
| 4: design in the docs site | Operator reviews the design and research synthesis and explicitly approves retirement of the original sketch and imported folders after references and manifests are checked. Regenerate the handoff and run the retro before the checkpoint report. |
| 5: build the PoC | All seven vertical slices work together on this machine, the organization Project has no open phase 5 items, and docs describe the result. Demonstrate slices as they land. Regenerate the handoff and run the retro before the operator checkpoint report. |
| 6: end-to-end verification | Playwright coverage, a Codex-written demo script, and filed known gaps are ready. The operator runs the demo. Regenerate the handoff and run the retro before the checkpoint report. |
