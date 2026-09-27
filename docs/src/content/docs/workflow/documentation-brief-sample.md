---
title: Documentation brief example
description: A checked example of a Codex documentation dispatch and its local prose gate.
---

The coordinator uses the [documentation brief template](https://github.com/tbhb/agent-orchestration-poc/blob/main/docs/briefs/documentation-brief-template.md) when dispatching Codex writing work. The [sample brief](https://github.com/tbhb/agent-orchestration-poc/blob/main/docs/briefs/documentation-brief-sample.md) covers the four [phase 1 retrospective](/retros/2026-09-26-phase-1/) follow-ups.

## Local verification

Run `mise run check:vale -- docs/briefs/documentation-brief-sample.md docs/src/content/docs/workflow/documentation-brief-sample.md` to check the sample brief and this page with the pinned Vale style. Run `mise run check:rumdl` and `mise run check:guard-markdown` before handing the pages back to the coordinator.
