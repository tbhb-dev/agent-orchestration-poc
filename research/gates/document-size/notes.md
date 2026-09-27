# Document size research

## Context windows and instructions

**Documented:** OpenAI lists a 1,050,000 token context window for [`gpt-6-sol`](https://developers.openai.com/api/docs/models/gpt-6-sol) and [`gpt-6-astra`](https://developers.openai.com/api/docs/models/gpt-6-astra). The [Codex AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md) describes hierarchy loading. The versioned `openai/codex@a6bd192` source caps aggregate project instruction bytes at 32 KiB by default in `codex-rs/core/src/config/mod.rs:252` and consumes that budget while loading the discovered files in `codex-rs/core/src/agents_md.rs:68-93`. This byte cap is a loading constraint, not a useful document-length recommendation. The source snapshot and the installed CLI version match the project plan's recorded checkout, but this research did not re-run a live instruction-loading probe.

**Documented:** [Claude's model table](https://platform.claude.com/docs/en/models/overview) lists 1 million tokens for `claude-fable-5-1` and `claude-sonnet-5`. [Claude Code extension guidance](https://code.claude.com/docs/en/features-overview) says `CLAUDE.md` loads every session, recommends keeping it below 200 lines, and says path-scoped `.claude/rules/` load when matching files are opened. This is a line recommendation for that harness, not a measured word or token threshold. The repository's `CLAUDE.md` imports `AGENTS.md`, so both texts belong in the Claude loaded-context budget.

**Documented:** [Google's Gemini 3.8 Flash model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash/) lists 1,048,576 input tokens for API model `gemini-3.8-flash`. The project's `agy` inventory uses `gemini-3.8-flash-high`, a harness-specific identifier. [Antigravity's rules guide](https://codelabs.developers.google.com/getting-started-agy-ide) describes global `~/.gemini/GEMINI.md` and workspace `.agents/rules/` instructions. It does not establish that this repository's `AGENTS.md` is loaded by `agy` or provide a numerical instruction-length recommendation. Treat the `agy` loaded-file set as untested until a runtime probe records it.

**Inference:** A million-token window is a capacity ceiling for an entire session and does not justify a million-token reference page. Instructions compete with the conversation, retrieved files, tool output, and generated reasoning. The budget proposal therefore uses the measured repository distribution and much smaller reviewable pages. The numerical thresholds are policy choices, not vendor performance guarantees.

## Long-context performance and human reading

**Documented:** [Liu et al.](https://aclanthology.org/2024.tacl-1.9/) changed the position of relevant material in multi-document question answering and key-value retrieval. Several tested models did worse when the answer-bearing material was in the middle of a long input than near its beginning or end. This supports concise, titled sections and on-demand retrieval. The tasks were not agent coding sessions, and the paper does not yield a universal word limit for this project's models.

**Documented:** [Nielsen's web-reading study](https://www.nngroup.com/articles/how-users-read-on-the-web/) reported 79% of test users scanned new web pages and 16% read word by word. [Morkes and Nielsen](https://www.nngroup.com/articles/applying-writing-guidelines-web-pages/) measured better usability for concise, scannable, objective web text in a redesigned site. These were web-page studies from 1997 and 1998, not studies of technical decision records or current agent interfaces. They motivate headings and shorter reference pages but do not prescribe exact budgets.

## Classes and measured distribution

**Verified:** At `d2add70d5ce58d89c188b7944f561ab9b30477b9`, the inventory has 128 tracked documents and 266,716 normalized words. The independent scanner recomputed every per-document count and each class total with zero differences. See `method.md`, `inventory.csv`, and `counts.csv`.

| Class | Files | Words | Median words | Largest words | Why its budget differs |
| --- | ---: | ---: | ---: | ---: | --- |
| Always-loaded instructions | 5 | 3,512 | 687 | 1,469 | Repeated context cost and possible instruction dilution |
| On-demand reference pages | 12 | 11,399 | 360 | 2,573 | A reader can open a topic but should find a rule quickly |
| Design pages | 15 | 11,890 | 750 | 1,814 | Need more room for alternatives and relationships |
| Decisions | 7 | 2,595 | 390 | 481 | One choice and its evidence should stay reviewable |
| Research notes and evidence | 72 | 218,635 | 1,006 | 26,189 | Raw provenance can be long, while synthesis should remain navigable |
| Plan and handoff | 9 | 17,603 | 868 | 10,172 | Cross-project orientation needs an index and bounded active handoff |
| Worker briefs | 8 | 1,082 | 107 | 255 | A task handoff is read at dispatch and should be directly actionable |

The `research notes and evidence` class includes imported research and manifests as immutable inputs. A future split should create a new index or synthesis and leave `research/imported/` untouched. The class labels describe intended use, not a claim that every file is loaded by every harness.

## Proposed budgets

**Inference:** These targets prompt editing, and limits trigger a documented exception or a split. Token figures are provisional policy caps pending vendor counts. The governing token count for a document is the maximum of the supported counts for the pinned OpenAI, Anthropic, and Google models. An unavailable model count remains unavailable and cannot silently pass a future token gate.

| Class | Target words | Limit words | Target tokens | Limit tokens |
| --- | ---: | ---: | ---: | ---: |
| Always-loaded instructions | 700 | 1,600 | 1,400 | 3,200 |
| On-demand reference pages | 1,000 | 2,200 | 2,000 | 4,400 |
| Design pages | 1,500 | 3,000 | 3,000 | 6,000 |
| Decisions | 500 | 800 | 1,000 | 1,600 |
| Research notes and evidence | 3,000 | 6,000 | 6,000 | 12,000 |
| Plan and handoff | 1,500 | 3,000 | 3,000 | 6,000 |
| Worker briefs | 250 | 500 | 500 | 1,000 |

**Inference:** Budget the total instructions loaded by Codex at 2,000 target and 2,600 limit words, or 4,000 target and 5,200 limit tokens. Budget Claude Code's `AGENTS.md`, importing `CLAUDE.md`, and any simultaneously matching rules at 2,000 target and 2,600 limit words, or 4,000 target and 5,200 limit tokens. Apply the same provisional budget to Antigravity once its actual loaded-file set is observed. These totals are per session, not the sum of every rule stored in the repository. At the snapshot, Codex's repository `AGENTS.md` is 1,469 words. Claude's repository `AGENTS.md` plus `CLAUDE.md` plus the largest single path rule total 2,464 words, under the proposed word limit. External user instructions are outside this repository inventory.

**Documented:** [Issue #84](https://github.com/tbhb/agent-orchestration-poc/issues/84) defines one PR-size unit as each added or deleted nonblank prose line. Whole-document word and token budgets do not replace or change that rule. [Issue #93](https://github.com/tbhb/agent-orchestration-poc/issues/93) remains its enforcement owner. [Issue #101](https://github.com/tbhb/agent-orchestration-poc/issues/101) owns the future document-budget check.

## Current word-limit exceedances and split proposals

**Verified:** Sixteen paths exceed the proposed word limits at the recorded snapshot. Their exact counts are in `counts.csv`. The proposals below are future work and do not edit these inputs.

| Path | Words | Proposal |
| --- | ---: | --- |
| `FABLE_HANDOFF.md` | 3,513 | Move stable history to the project history page and leave a short current handoff |
| `docs/src/content/docs/project/plan.md` | 10,172 | Separate phase plans, standing rules, and historical decisions with a small plan index |
| `docs/src/content/docs/guides/docs-stack-conventions.md` | 2,229 | Move version history and detailed source notes to a linked research page |
| `docs/src/content/docs/guides/python-conventions.md` | 2,573 | Separate tooling reference from language rules and link both from the guide index |
| `experiments/00-system-assessment/harness-research.md` | 26,189 | Create one indexed result page per harness and leave raw evidence intact |
| `experiments/00-system-assessment/model-research.md` | 6,202 | Separate model inventory from trial method and outcomes |
| `reports/inputs/phase-0-decisions.md` | 8,719 | Add a short decision index and link numbered decision records |
| `research/gates/boundaries/notes.md` | 6,502 | Separate import checks from runtime boundary probes |
| `research/gates/go/notes.md` | 6,178 | Separate version research from linter comparison |
| `research/gates/python/notes.md` | 8,661 | Separate interpreter, formatter, test, and typing research |
| `research/gates/quality-gates/notes.md` | 6,349 | Separate duplicate, dead-code, and complexity evidence |
| `research/gates/testing/notes.md` | 6,452 | Separate property and mutation gate evidence |
| `research/imported/MANIFEST.md` | 25,798 | Keep immutable and add a generated, navigable index outside `research/imported/` |
| `research/imported/agent-peering-tests/DESIGN_REVIEW_FABLE_5_1.md` | 7,350 | Keep immutable and add a topic index outside `research/imported/` |
| `research/imported/agent-session-tests/CLAUDE_CODE_SESSION_MANAGEMENT.md` | 7,419 | Keep immutable and add a section index outside `research/imported/` |
| `research/imported/agent-session-tests/CODEX_SESSION_MANAGEMENT.md` | 7,092 | Keep immutable and add a section index outside `research/imported/` |

The research limit is an authoring target for new synthesis. Raw evidence and imported files are measured and reported, with any future exception explained rather than rewritten. The final token exceedance list remains unavailable until the operator's keys and the #101 collector can count the pinned models.
