---
title: "0011: document size budgets"
description: Proposed word and token limits by document class and loaded instructions.
---

## Status

Proposed 2026-09-26 for issue #100. Number 0011 avoids the 0010 collision with [PR #115](https://github.com/tbhb/agent-orchestration-poc/pull/115). The issue's allowed path still names 0010 and needs the coordinator's path update before merge. Vendor token counts and the #107 notebook verification remain pending.

## Context

At commit `d2add70d5ce58d89c188b7944f561ab9b30477b9`, 128 tracked Markdown, MDX, and QMD documents contain 266,716 words by the [recorded method](https://github.com/tbhb/agent-orchestration-poc/blob/research/100-document-size-limits/research/gates/document-size/method.md). The [research notes](https://github.com/tbhb/agent-orchestration-poc/blob/research/100-document-size-limits/research/gates/document-size/notes.md) separate vendor context capacity, instruction loading, long-context retrieval evidence, human reading, and this repository's measured distribution. No vendor study establishes a universal document-length threshold.

## Decision

**Inference:** use the targets and limits in [document size conventions](/guides/document-size-conventions/) for whole documents. Targets are editing prompts. A document beyond its limit needs a split or an explicit exception that links a navigable summary. The word limits are 1,600 for always-loaded instructions, 2,200 for on-demand references, 3,000 for designs, 800 for decisions, 6,000 for research and evidence, 3,000 for plans and handoffs, and 500 for worker briefs. The corresponding token limits are 3,200, 4,400, 6,000, 1,600, 12,000, 6,000, and 1,000. Token caps are provisional until vendor counts are available.

**Inference:** budget the total repository instructions actually loaded for each harness at a target of 2,000 words or 4,000 tokens and a limit of 2,600 words or 5,200 tokens. Use the highest supported pinned-vendor token count. Mark a missing count unavailable with a reason. Treat imported research as read-only and add indexes or syntheses outside its directory where needed.

**Documented:** [issue #84](https://github.com/tbhb/agent-orchestration-poc/issues/84) defines PR size as each added or deleted nonblank prose line being one unit. These whole-document budgets do not replace or modify that rule, and [issue #93](https://github.com/tbhb/agent-orchestration-poc/issues/93) remains its enforcement owner.

## Consequences

Sixteen existing paths exceed a proposed word limit. The [research notes](https://github.com/tbhb/agent-orchestration-poc/blob/research/100-document-size-limits/research/gates/document-size/notes.md) list each path and a split proposal. Splitting and the budget check belong to later work. Token exceedances remain unknown until the operator supplies API keys and the trusted collector in #101 records counts. The measurement notebook still needs the #104 protocol and #107 runnable tasks.

Reopen the budgets when a pinned harness or model changes, token counts conflict with a cap, a repository-specific retrieval or reading study supports another threshold, or instruction loading changes. Record a new snapshot and rerun the verified notebook before changing a number.

## Evidence

The source register, claims, inventory, per-document counts, independent recomputation, and exact commands are under `research/gates/document-size/`. The current `mise run check` and `mise run check:mutation` passed. The #107 notebook commands exit 1 because the tasks are absent, and vendor token requests were not made.
