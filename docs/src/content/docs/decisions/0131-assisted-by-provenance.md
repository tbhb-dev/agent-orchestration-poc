---
title: "0131 Assisted-by provenance convention"
description: Proposed agent provenance syntax, aggregation, and cutover cases for issue 131.
---

## Status

Proposed 2026-09-27 for [issue #131](https://github.com/tbhb/agent-orchestration-poc/issues/131), without activating attribution trailers. The phase 0 prohibition remains binding until #134. Reference integration with #84 and the issue-linking examples from #124 remain pending. The issue-number filename avoids claiming a sequential decision number reserved by another worker.

## Context

The operator asked for “a common, consistent way like this to trace provenance” on 2026-09-26, as quoted in #131. The issue records the direction to use one Linux kernel style `Assisted-by:` trailer per contributing agent on commits. PR bodies contain the sum of commit trailers, and reviews also require trailers.

The [plan's commit rule](/project/plan/#commits) and [PR #81](https://github.com/tbhb/agent-orchestration-poc/pull/81) prohibit attribution and co-author trailers and put harness/model information in the PR evidence section. At cutover, this decision supersedes that prohibition only for the exact `Assisted-by:` convention below. It does not authorize co-author trailers, change GitHub account ownership, or replace review identity checks.

[Documented] The [kernel source at fd179f8a05be3ccae366b9b96e176b51fbe54aab](https://github.com/torvalds/linux/blob/fd179f8a05be3ccae366b9b96e176b51fbe54aab/Documentation/process/coding-assistants.rst#L49) specifies `Assisted-by: LLM [TOOL1] [TOOL2]`. Optional tools are specialized analyzers. We adopt the trailer key with richer provenance and omit tools. [Git v2.51.0's trailer documentation](https://github.com/git/git/blob/c44beea485f0f2feaf460e2ac87fdd5608d63cf0/Documentation/git-interpret-trailers.adoc) provides the end-of-message key/value convention. We define the project fields and aggregation rules below, including review attribution.

## Decision

### Exact syntax

Each line has this format, with exactly one ASCII space between fields:

```text
Assisted-by: <harness>/<version> model=<model> effort=<effort> agent=<agent>
```

The key, field names, order, and case are literal. Values contain no whitespace. No indentation, wrapping, trailing spaces, Markdown bullets, quotes, or code fences surround actual trailers. Use LF line endings with at most one final LF. The final contiguous trailer block follows a blank line. Attribution lines precede the existing `Refs:` lines, but issue and review comments do not require an artificial `Refs:` line.

Harness is one of `codex-cli`, `claude-code`, or `agy`. Version is the actual contributing executable's complete release identifier, matching `[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?`. Never substitute `latest`, omit it, or copy another worker's version. Validation fails if the version is missing until evidence supplies it.

Model is the exact full model identifier recorded for the contribution, using `[a-z0-9][a-z0-9._-]*`. Resolve aliases such as `fable` from retained run evidence. Preserve agy's full requested model variant when the harness does not expose a resolved model. This field records the supported evidence, not proof of the provider's internal execution. Context-window options belong in run evidence rather than the model ID when the harness reports the same resolved model.

Effort is the explicitly selected control value, not an estimate of reasoning performed. Codex permits `low`, `medium`, `high`, `xhigh`, `max`, or `ultra` in provenance. Claude permits `low`, `medium`, `high`, `xhigh`, or `max`. agy permits `low`, `medium`, `high`, or `max`. Listing a value here does not authorize its use under the project's launch policy. Use `unavailable` only when versioned evidence establishes that this harness/model has no effort control. Unknown, implicit default, and omitted effort fail. The recorded inventory lists an effort control for each configured row below.

Agent is a stable public run identifier matching `[a-z0-9][a-z0-9-]{0,63}`. The coordinator allocates distinct IDs before contribution and retains their mapping in dispatch evidence. Reuse the ID when resuming that run, but give each separate worker, delegated agent, and coordinator run a distinct ID, even with identical harness/model settings. Do not embed private session IDs, credentials, or email addresses. Account and signing design remains #132's responsibility.

The verifier checks both grammar and the evidence-backed catalog of harness/version/model/effort combinations. Syntactically valid but unknown values fail until the catalog is deliberately extended. The table is the initial documented snapshot, not a promise that future versions or model choices will work.

### Reference values

The following are exact synthetic trailer values. Replace only the agent ID with the actual allocated ID and the configuration fields with recorded values from the approved catalog when they differ. The source is `experiments/00-system-assessment/model-inventory.md` at `cc1f59c7f7a932f7f9dba7073e1e63789d1328e5`.

| Harness and model | Exact example | Version and effort treatment |
| --- | --- | --- |
| Codex CLI, gpt-6-sol | `Assisted-by: codex-cli/0.157.1 model=gpt-6-sol effort=high agent=impl-131` | Record actual version and explicit override. Model-list support is recorded, with no fresh per-pair runtime test here. |
| Codex CLI, gpt-6-astra | `Assisted-by: codex-cli/0.157.1 model=gpt-6-astra effort=medium agent=docs-131` | Record actual version and explicit override. This worker's assigned configuration is medium. |
| Claude Code, Fable 5.1 | `Assisted-by: claude-code/2.1.283 model=claude-fable-5-1 effort=high agent=coord-131` | Resolve Fable aliases from evidence. Effort availability is harness-wide help-text evidence. |
| Claude Code, Sonnet 5 | `Assisted-by: claude-code/2.1.283 model=claude-sonnet-5 effort=medium agent=review-131` | Record actual version and selected effort. Per-model effort behavior remains untested. |
| agy, Gemini 3.1 Pro High | `Assisted-by: agy/1.2.11 model=gemini-3.1-pro-high effort=high agent=research-131` | Version and explicit flag are recorded. Resolved-model reporting is unavailable. Flag versus model-tier interaction is untested. |
| Any future catalog entry without an effort control | No admitted value yet | Require documented lack of a control before admitting `effort=unavailable`. Never use it to conceal missing evidence for the rows above. |

Tools do not appear in the trailer. Record compiler, analyzer, plugin, and test-tool versions in evidence when relevant. A tool that invokes another contributing agent requires that agent's own trailer. Routine deterministic tool execution does not create an agent contributor.

### Contributors and aggregation

A contributing agent creates or materially changes code, documentation, evidence, tests, or decisions retained in the artifact. Include delegated contributions even when another agent commits them. Merely scheduling, relaying unchanged text, or mechanically invoking a command is not authorship. Human-only artifacts have zero agent trailers and must not invent an agent.

Within an artifact, use one line per contributing agent ID. Freeze the version, model, and effort for that ID. Allocate a new ID for contributions after a configuration change, and retain the relationship in dispatch evidence. Runs with identical settings remain separate because their agent IDs differ. Reject repeated identical lines within one artifact. Sort complete `Assisted-by:` lines by ascending ASCII byte order. Across commits, collapse identical lines when forming the PR union.

For a PR targeting `main`, collect commits reachable from its recorded head but not reachable from its recorded current target SHA, including branch merge commits. Compute the set union of those commits' attribution lines, sorted as above. The PR body's attribution block must equal that set exactly. A missing or extra line fails. A changed head or target requires recollection. Partial commit reads fail closed. Do not take the union of every ancestor ever seen on the branch.

When updating a published branch, merge `main` and never rewrite pushed history. Attribute a new merge-main commit to agents that selected, resolved, or verified substantive integration decisions. A coordinator making those decisions contributes even if Git reports a clean merge. Inherited commits already reachable from the target do not enter the union. A wholly mechanical merge with no agent judgment does not add an agent. Source commit trailers remain unchanged.

The coordinator's own material contributions follow the same rule. For coordinator-only PR-body drafting or substantive revision, add an empty provenance commit that records the coordinator's contribution. Include its trailer and explain the contribution in the body, with `Refs:` as required. Refresh the PR union to include this commit. This does not authorize empty commits before cutover. A relay of unchanged approved text does not need new attribution. Review-only work remains attributed on the review and is not added to the PR union unless it contributes retained changes.

### Reviews, issues, and squash commits

End an agent-authored review verdict with its own canonical trailer block, identifying all agents contributing to that verdict. Each inline comment, including an implementer reply, independently carries its contributors' block. A parent review's trailer does not cover its inline threads. Preserve the existing verdict first-line and account requirements from #83, and the issue-review verdict, body digest, and freshness requirements from #90. A trailer asserts provenance and is not authentication or approval.

An agent-authored issue body ends with author trailers. Agent-authored role comments, including refinement, dispatch, status, arbitration, and coordinator merge explanations, include their own trailers. Exact-body command protocols such as #83's arbitration text need an explicit parser migration at cutover that separates the command from the final attribution block. Before that migration, the exact existing command remains binding. Appending a trailer now would invalidate it. Bot-generated transport notifications with no contributing agent have no fabricated trailer.

The squash subject is the PR title. Its body is the final PR body, preserving the canonical union exactly. Revalidate head, target, body, and union before merge. Do not replace contributors with the merging account or add a merge-only coordinator line. An agent whose only act is mechanically submitting the approved merge has no new contribution. Substantive coordinator edits require the provenance commit and union refresh before the merge. Signing and account policy remains separate.

`Refs:` identifies related issues and is not attribution. The closing-link contract is assigned to issue #124. Preserve current `Refs:` requirements while that decision is pending. If #124 selects a closing keyword, its line remains separate from the attribution block and does not make every referenced issue completed. The exact completed-issue/closing-line examples cannot be finalized until that decision is available.

### Open pull requests at cutover

The operator's unanswered question is whether the new rule applies to PRs already open at cutover. Do not infer an answer from #84's independent form-validator migration. Issue #134 must record the operator's decision and the authoritative cutover timestamp before enabling this verifier.

If the answer is yes, a pre-cutover open PR lacking attribution produces a blocking migration finding. If the answer is no, the same PR produces a nonblocking legacy report, while a PR created at or after cutover is enforced. Both policies reject missing creation or cutover metadata as indeterminate. The boundary is PR creation time, not branch creation time. Under either answer, migration of published unsigned or unattributed commits needs a separately approved, append-only plan. Do not rewrite pushed commits under this decision.

## Consequences

This convention distinguishes agent runs for exact union checks. Dispatch must record their identifiers. It also requires provenance commits for coordinator-only PR prose contributions. The current prohibition, hooks, templates, accounts, and live artifacts are unchanged. #132 owns identity design, #133 owns verification, and #134 owns activation after the dependent work. The verifier must put parsing, sorting, and union decisions in pure core functions and GitHub/git collection in the shell.

Revisit the catalog when a harness or model changes, and revisit the format if run identity cannot be collected reliably. Do not convert an unknown fact into a guessed value to pass a check.

## Evidence

The repository artifact `research/gates/assisted-by/evidence.md` records exact source commits, passages, commands, and validation limits. `research/gates/assisted-by/examples.md` supplies proposed passing and failing cases for the future verifier. No runtime provenance verifier is implemented or claimed here.
