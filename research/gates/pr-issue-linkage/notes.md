# Pull request and issue linkage research

## Scope and sources

This research answers [#124](https://github.com/tbhb-dev/agent-orchestration-poc/issues/124) for pull requests targeting this repository's default branch. [Evidence](evidence.md) records the read-only requests, source times, and limits. GitHub's [linking documentation](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) says a supported keyword in the pull request description links an issue before merge and a linked issue closes when that pull request merges into the default branch. It distinguishes a keyword in a commit message, which closes an issue when the commit reaches the default branch without listing the pull request as linked. The [squash settings documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-squashing-for-pull-requests) permits a pull request title and description as the squash message, and the repository's REST settings select `PR_TITLE` and `PR_BODY`.

The coordinator proposed option A before the research and recorded the operator's 2026-09-27 preference for using both a closing line and `Refs:` on a completed issue in [#124's comments](https://github.com/tbhb-dev/agent-orchestration-poc/issues/124). That direction is the policy input. The sources and observed examples below bound the behavioral claims.

## Examples and limits

| Example | Before merge | At merge and afterward | Limit |
| --- | --- | --- | --- |
| [PR #80](https://github.com/tbhb-dev/agent-orchestration-poc/pull/80) and [issue #59](https://github.com/tbhb-dev/agent-orchestration-poc/issues/59) | [Observed] The issue timeline has a `cross-referenced` event from PR #80 at 2026-09-26 23:20:57 UTC. The current PR body has three `Refs:` lines and no closing keyword. | [Observed] PR #80 merged at 2026-09-27 00:11:18 UTC. Its [squash commit](https://github.com/tbhb-dev/agent-orchestration-poc/commit/ee61cb093bcb229bfdab498183ae5f22e595fc14) contains the three `Refs:` lines. Issue #59 has a separate `closed` event at 00:11:25 UTC without a commit ID. | [Untested] No retained body-at-merge capture or closure-action record proves why issue #59 closed. A cross-reference is not evidence of a linked pull request. |
| [PR #196](https://github.com/tbhb-dev/agent-orchestration-poc/pull/196) and [issue #176](https://github.com/tbhb-dev/agent-orchestration-poc/issues/176) | [Observed] The issue timeline has a `cross-referenced` event from PR #196 at 2026-09-27 13:31:44 UTC. The current PR body says it is a partial delivery and has `Refs: #176`. | [Observed] PR #196 merged at 13:48:09 UTC. Its [squash commit](https://github.com/tbhb-dev/agent-orchestration-poc/commit/af9716f7445f168dfc942f81d3c8be624314c9e6) retained a closing keyword directly before `#176` within a sentence saying the line was omitted. The issue's `closed` event at 13:48:11 UTC names that commit. The issue was reopened at 13:54:27 UTC. | [Inference] The keyword in the default-branch commit caused the closure. The matching commit ID and timing support this strongly, but GitHub exposes no separate parser trace. The current PR body is not a retained body-at-merge capture. |
| Project 9 status | [Observed] The #176 and #59 issue timelines include `project_v2_item_status_changed` events. | [Documented] GitHub's [Project automation documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations) describes event-driven Status changes. | [Untested] The REST timeline omits prior and new values and the workflow identity. Neither a present Status nor these events proves an `In review` transition from a linked-PR workflow. |

The 2026-09-27 coordinator [comment on #124](https://github.com/tbhb-dev/agent-orchestration-poc/issues/124) records a seven-open-PR survey with no closing keyword and only cross-reference events for #132, #84, and #109. This is an attributed historical report, not a fresh seven-PR sample in this research. The current read of their issue timelines also shows cross-references, with no observed connection event in the returned pages. A clean, positive linked-PR-before-merge example for this repository is unavailable, so that outcome remains [untested] here and [documented] by GitHub.

## Options

| Test | Option A, completed-issue closing line plus `Refs:` | Option B, `Refs:` plus explicit closure automation |
| --- | --- | --- |
| Link before merge | [Documented] A keyword in the default-target PR description links the completed issue. [Untested] No clean repository example was retained. | [Documented] A commit reference does not list its PR as linked. [Inference] `Refs:` alone does not establish a linked PR. Automation would need a separate manual link or API operation. |
| Closure at merge | [Documented] GitHub closes a linked issue on default-branch merge when auto-close is enabled. [Observed] The #196 squash commit keyword coincided with closure of #176. | [Untested] A new, authorized post-merge actor would have to identify completed issues, close only those, and handle failures and retries. No such implementation was tested. |
| Project `In review` transition | [Untested] A link may trigger the configured Project workflow, but no retained transition value or workflow identity proves it. The operator says open PRs should leave issues `In progress`, so Project workflow settings need separate reconciliation before broad rollout. | [Untested] `Refs:` does not provide the linked-PR trigger. A separate Project update would need its own policy and evidence. |
| Squash body propagation | [Observed] The #80 and #196 squash commits contain their PR body content, with line wrapping. [Schema] Repository settings select `PR_BODY`. | [Observed] `Refs:` propagates by the same setting. The automation still needs an independent completion signal. |
| Safety of partial delivery | [Observed] PR #196 demonstrates that a closing keyword anywhere before an issue number in the squash body can close an issue despite prose saying it stays open. | [Inference] An explicit closure actor can omit the partial issue, but requires additional implementation, permissions, and a reliable completion decision. |

Option A is selected for the completed issue. It uses GitHub's documented link and close behavior, has an observed default-branch closure example, and follows the operator's stated contract. This selection does not claim a repository-observed clean link-before-merge transition or a verified Project `In review` transition.

## Contract and assignments

For a PR that completes issue `N`, put `Closes #N` on its own line directly above the final `Refs: #N` trailer. Keep the completed issue in both lines, because the present [PR body checker](../../../scripts/check-pr-body.sh) requires `Refs:` even when a closing line exists. Other related issues can have their own `Refs:` lines. A PR with several completed issues may carry a separate closing line for each completed issue and a `Refs:` line for each. A reference alone never authorizes closure.

For a partial delivery, omit every closing keyword immediately before an issue number anywhere in the PR body, including examples in prose and code formatting. State that the PR is partial and the issue stays open. Commits keep only `Refs:`. Check the final squash message for accidental keywords before merge, because the #196 case shows that the resulting commit can close an issue independently of a PR link.

Assign the PR template, PR-body validator, and workflow conventions to [#84](https://github.com/tbhb-dev/agent-orchestration-poc/issues/84) or its explicitly scoped successor. They should allow and validate an optional closing line immediately before final `Refs:` trailers without requiring it on partial work. Assign commit-message enforcement to [#92](https://github.com/tbhb-dev/agent-orchestration-poc/issues/92) with #84's reference contract. Assign any coordinator issue-closure action only to a separately refined [#120](https://github.com/tbhb-dev/agent-orchestration-poc/issues/120) or successor, because #120 currently excludes closure. Option A does not require that action for a completed issue. Project workflow reconciliation also needs a separately scoped owner before broad use of closing lines on open PRs.

The chosen policy does not change the active [main ruleset](https://github.com/tbhb-dev/agent-orchestration-poc/rules/24053242): `check`, `docs`, `pr-body`, `imported-research`, and `mutation` must pass, one current review must approve the latest push, threads must be resolved, the branch must be current, and the merge must be a squash. Operator-only merge boundaries in [the workflow](../../../docs/src/content/docs/workflow/index.md) remain in force. Coordinate shared workflow and decision-index changes with PRs #115, #121, #117, and #125, and affected implementation with #84, #92, #120, and #123.

## Proposed fixtures

These are proposals for the owners above, not implemented tests. Replace `N`, `M`, and `K` with disposable test issue numbers or pure fixture values.

| Case | Body shape | Expected result |
| --- | --- | --- |
| Completed issue only | Closing line for `N`, then `Refs: #N` | PR-body validation passes and, for a default-target PR, GitHub links `N` before merge and closes `N` at merge. The live GitHub steps remain untested here. |
| Closing line only | Closing line for `N` without `Refs:` | Current `mise run check:pr-body` fails. A migration must be explicit before changing this expectation. |
| Partial delivery | State that `N` stays open, then `Refs: #N`, with no keyword-number pair | PR-body validation passes and `N` remains open after merge. |
| Multiple references | Closing line for completed `N`, then `Refs: #N` and `Refs: #M` | `N` links and closes, while `M` remains open. |
| Multiple completed issues | Closing lines for completed `N` and `M`, then both `Refs:` lines | Both completed issues link and close. |
| Unlinked reference | `Refs: #N` only | Validator passes, while GitHub does not list the PR as linked through that trailer. |
| Accidental keyword | A sentence or code span containing a supported keyword directly before `#N` in a partial PR | Future validator fails. The #196 merge shows the closure hazard. |
| Squash propagation | A completed PR body with closing and reference lines | Capture the PR body at merge and compare it with the default-branch squash commit. |

Revisit this choice if GitHub's linked-PR behavior or repository auto-close setting changes, a positive before-merge trial contradicts the documentation, or the Project workflow produces a status transition that conflicts with the operator's board policy.
