---
title: Document size conventions
description: Proposed word and token budgets for project documents and loaded instructions.
---

## Scope

These proposed budgets apply to the whole normalized text of tracked Markdown, MDX, and QMD documents. They do not replace the rule for pull request size from [issue #84](https://github.com/tbhb/agent-orchestration-poc/issues/84), which counts each added or deleted nonblank prose line as one unit. [Issue #93](https://github.com/tbhb/agent-orchestration-poc/issues/93) owns enforcement of that separate diff rule. [Issue #101](https://github.com/tbhb/agent-orchestration-poc/issues/101) will add checks for document budgets.

**Inference:** use the target as an editing signal and the limit as the point requiring a split or a justified exception. Count frontmatter, code fences, comments, and markup because they occupy context when the whole file is loaded. Normalize UTF-8, line endings, and Unicode NFC as specified in [the method](https://github.com/tbhb/agent-orchestration-poc/blob/research/100-document-size-limits/research/gates/document-size/method.md). Word and token counts from the recorded baseline are in `research/gates/document-size/counts.csv`.

| Document class | Target words | Limit words | Target tokens | Limit tokens |
| --- | ---: | ---: | ---: | ---: |
| Always-loaded instructions | 700 | 1,600 | 1,400 | 3,200 |
| On-demand reference pages | 1,000 | 2,200 | 2,000 | 4,400 |
| Design pages | 1,500 | 3,000 | 3,000 | 6,000 |
| Decisions | 500 | 800 | 1,000 | 1,600 |
| Research notes and evidence | 3,000 | 6,000 | 6,000 | 12,000 |
| Plan and handoff | 1,500 | 3,000 | 3,000 | 6,000 |
| Worker briefs | 250 | 500 | 500 | 1,000 |

**Inference:** for each Codex or Claude Code session, target at most 2,000 words or 4,000 tokens across repository instruction files actually loaded, with limits of 2,600 words or 5,200 tokens. Use the same provisional total for Antigravity after its loaded-file set is measured. Include `AGENTS.md` for Codex and `AGENTS.md`, `CLAUDE.md`, and matching `.claude/rules/` files for Claude Code. Do not add all path-scoped rules to every session. External user instructions are outside this repository budget.

**Untested:** token columns in the baseline are unavailable pending the operator's vendor API keys and the trusted collector in #101. When supported counts exist, use the highest count among the pinned vendor models for each file and loaded-file total. A missing count cannot be replaced with a word-to-token estimate. The [research notes](https://github.com/tbhb/agent-orchestration-poc/blob/research/100-document-size-limits/research/gates/document-size/notes.md) explain the source evidence, class choices, and current word-limit exceedances. Imported research remains read-only.

## Reopen the budgets

Revisit these numbers when the pinned harness or model changes, vendor token results make a current limit untenable, a measured retrieval or human-reading study on this repository shows a different threshold, or the loading behavior changes. Record the replacement measurements at a commit SHA before changing a limit. An exception for an existing raw evidence file should link an index or synthesis rather than edit its original content.
