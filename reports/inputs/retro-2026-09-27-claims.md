# Second retro evidence notes

These are source notes for the fixed cohort in [issue #165](https://github.com/tbhb-dev/agent-orchestration-poc/issues/165). They support a partial evidence delivery and state no quantitative conclusion. The [claim table](../../research/gates/retro-2026-09-27/claims.csv), [source table](../../research/gates/retro-2026-09-27/sources.csv), and [query transcript](../../research/gates/retro-2026-09-27/evidence/query-transcript.md) record IDs, limits, and source time.

## Cohort and missingness

Observed, C01 and C02: two successful REST requests returned 49 closed PR rows and an empty completion page. Filtering `merged_at > 2026-09-26T22:22:57Z` and `merged_at <= 2026-09-27T04:30:06Z` selects the 17 PR URLs in `pr-metrics.csv`. The repository API owner changed from `tbhb` in the issue to `tbhb-dev` in the live path, while the timestamp bounds and selected population stayed fixed.

Observed, C03: `pr-metrics.csv` has a row for every selected PR with the fields in #90's per-PR contract. `pr-files.csv`, `pr-review-rows.csv`, and `pr-ci-rows.csv` retain supporting rows. A submitted `CHANGES_REQUESTED` review is one verdict round, including reviews by either historical or renamed reviewer account. Duration is the UTC difference between PR open and merge times. A named main merge in the PR commits is a lower bound on updates, and no named merge leaves that field `unknown`.

Inference, C04: #84's [size research](../../reports/inputs/pr-size-research.md) did not settle and implement the changed-fragment classifier. [#142](https://github.com/tbhb-dev/agent-orchestration-poc/issues/142) owns it. The row's full measured #84 size and excluded raw-line count are `unknown`. The explicit excluded-path sum is retained separately and must not be reported as the complete excluded total. Project Size values were read after the PRs merged and do not prove the field at dispatch. Several are absent. Worker provenance uses the PR body or recorded Project Worker value and leaves broad `GPT-6` variants, model, or effort `unknown` when not identified.

## Scope and dependency leads

Observed, C05: [PR #137](https://github.com/tbhb-dev/agent-orchestration-poc/pull/137) states that #84 split out the PR size counter and label drift work to [#142](https://github.com/tbhb-dev/agent-orchestration-poc/issues/142) and [#141](https://github.com/tbhb-dev/agent-orchestration-poc/issues/141). Its size justification says the pre-review estimate was 797 units and later review fixes might exceed 800, while pinned scc measurement was unavailable in that sandbox. [PR #138](https://github.com/tbhb-dev/agent-orchestration-poc/pull/138), which is inside the cohort, explicitly delivered only #110's provider research after estimating the complete stack work at about 1,050 units and waiting for #107's notebook gate. [#109](https://github.com/tbhb-dev/agent-orchestration-poc/issues/109) specifies a conditional split above 800, but this source does not establish a mid-build split for #109. These are individual scope records, not a cohort size conclusion.

Observed, C06: [PR #121's review record](https://github.com/tbhb-dev/agent-orchestration-poc/pull/121) contains three `CHANGES_REQUESTED` verdicts by the reviewer account. The [coordinator arbitration](https://github.com/tbhb-dev/agent-orchestration-poc/pull/121#issuecomment-5852465388) held that PR for #107's notebook gate. [#158](https://github.com/tbhb-dev/agent-orchestration-poc/issues/158) uses this as a dependency example. PR #121 is open and outside the fixed merged cohort. Its rounds do not enter cohort denominators.

Inference: the issue's `Refs:` ambiguity for partial delivery is illustrated by [PR #137](https://github.com/tbhb-dev/agent-orchestration-poc/pull/137), which documents deferred #142/#141 work while retaining `Refs: #84`. The current partial delivery must leave #165 open. The exact impact of a closing keyword is stated in the coordinator direction for this delivery and was not experimentally retested here.

## Worker and coordination leads

Documented, C08: [#153](https://github.com/tbhb-dev/agent-orchestration-poc/issues/153) reports two workers that completed work but could not commit when a hook tried to write its log through a sandbox boundary. It also cites [PR #97](https://github.com/tbhb-dev/agent-orchestration-poc/pull/97) for a worker reaching the 90-minute limit during conflict resolution. Private run records and logs were unavailable here, so the exact workers, durations, and changed files remain `unknown`. #153 owns stopped-run diagnosis rather than this retro reproducing the private logs.

Inference: same-model review is a coordinator lead in [#165](https://github.com/tbhb-dev/agent-orchestration-poc/issues/165). The retained review and PR-body rows can establish named models where both sides disclose them, but empty reviews, broad `GPT-6` labels, and post-merge edited bodies limit a cohort-wide conclusion. The later retro should test each comparable pair under #90's definitions after the notebook gate.

Inference, C09: [#161](https://github.com/tbhb-dev/agent-orchestration-poc/issues/161) identifies [#151](https://github.com/tbhb-dev/agent-orchestration-poc/issues/151) and [#152](https://github.com/tbhb-dev/agent-orchestration-poc/issues/152) as duplicate work of [#142](https://github.com/tbhb-dev/agent-orchestration-poc/issues/142) and [#141](https://github.com/tbhb-dev/agent-orchestration-poc/issues/141). The existing owners should receive any action from the later retro. No new issue is needed for those duplicate topics.

Documented, C07: the [phase 1 retro](../../docs/src/content/docs/retros/2026-09-26-phase-1.md) records two zsh word-splitting failures in coordinator scripts. The source says the errors cost work in that session, but it does not retain enough command-level detail here for a new duration or failure rate. [#103](https://github.com/tbhb-dev/agent-orchestration-poc/issues/103) reserves private transcript efficiency analysis.

Inference: mechanical coordinator work is a lead in #165 and an analysis target in #103, including repeated reads, polling, and shell repair. The phase 1 retro names specific tasks and #103 asks for measured action and context costs. This delivery cannot rank costs without the private transcript study. It records the lead without a numerical efficiency claim.

## Concurrency and the later incident

Untested, C13: the #165 lead says concurrent work occurred without observed rate-limit errors in its earlier window. No bounded raw request/error record for that earlier window was supplied here. It can only be treated as a coordinator observation with an unspecified account and window, not evidence that all concurrent work was rate-limit free.

Documented, C10: the [first #164 incident note](https://github.com/tbhb-dev/agent-orchestration-poc/issues/164#issuecomment-5852591106) says Project field writes as historical account `tbhb` began failing around 2026-09-27 04:10 UTC, and the coordinator declared the incident at 04:22 UTC. It reports GraphQL response headers of limit 5000, used 5000, and remaining 0. The original headers are absent from this worktree, so these values remain coordinator testimony. The note infers that nine workers and command mix contributed, without a measured attribution.

Documented, C11: a [later #164 update](https://github.com/tbhb-dev/agent-orchestration-poc/issues/164#issuecomment-5852783968) reports the renamed agent account, now `tbhb-agent`, near its GraphQL limit at about 04:55 UTC and a refused Project read. It also reports that the summary rate-limit endpoint disagreed with request headers. The comment uses the old `tbhbagent` spelling from before the rename. The reviewer account changed from `tbhbbot` to `tbhb-agent-reviewer`. Reviews in retained rows may use either name. This is a different account and later time window than the first note.

Documented, C12: the [resolution update](https://github.com/tbhb-dev/agent-orchestration-poc/issues/164#issuecomment-5852895053) reports successful REST Project edits, a read-back, and a lifted pause at about 05:14 UTC. It attributes seven forbidden watch invocations from worker logs and treats old Project retry loops as a likely large but unmeasured consumer. This delivery did not inspect those private logs or independently read back the historical board state. The earlier no-error lead must not extend across either reported incident window.

## Deferred verification

Untested, C14: [PR #156](https://github.com/tbhb-dev/agent-orchestration-poc/pull/156) for #107 remains open with changes requested. Its notebook tasks are unavailable on this branch. `cohort.qmd`, independent recomputation, different-model review, the dated retro page, and the retros index belong to the second delivery. Costs, failures, useful deviations, decisions, automated-check proposal, and action items await that verified synthesis. The issue stays open after this partial delivery.
