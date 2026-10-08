---
title: Completed pull requests use closing lines and references
description: The issue linkage and closure contract for completed and partial pull requests.
---

## Status

Accepted 2026-10-07 for issue #124, following the operator's 2026-09-27 direction recorded in [the issue comments](https://github.com/tbhb-dev/agent-orchestration-poc/issues/124). The work is assigned to #84, #92, and a separately refined #120 or successor.

## Context

The repository requires `Refs:` in pull requests and commit messages. A reference alone does not establish a GitHub linked pull request. GitHub [documents](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) that a closing keyword in a pull request description targeting the default branch links an issue before merge and closes it when the linked pull request merges. Repository REST settings select the pull request body as the squash message. In [PR #196](https://github.com/tbhb-dev/agent-orchestration-poc/pull/196), a closing keyword embedded in partial-delivery prose reached the squash commit and [issue #176](https://github.com/tbhb-dev/agent-orchestration-poc/issues/176) closed at that commit before being reopened. The [research notes](https://github.com/tbhb-dev/agent-orchestration-poc/blob/6309b8cd416e948cadb142f783e53f75c279e096/research/gates/pr-issue-linkage/notes.md) distinguish the observed events from missing historical captures.

## Decision

A pull request that completes issue `N` has `Closes #N` on its own line directly above the final `Refs: #N` trailer. The completed issue appears in both lines. Other related issues receive `Refs:` lines without closing lines unless that same pull request also completes them. Commits before merge contain `Refs:` only. The squash message must preserve the intended closing and reference lines.

A partial delivery says the issue remains open and contains no closing keyword immediately before its issue number anywhere in the body, even in a quoted example or sentence about omission. It retains `Refs:`. Neither a reference nor an open PR makes every mentioned issue complete. The coordinator reviews the final squash message before merging.

## Consequences

The chosen closing line provides GitHub's documented pre-merge link and default-branch closure without a new closure actor. The repository has an observed keyword-driven closure at merge, but a clean linked-PR-before-merge example and a verified Project `In review` transition remain untested. The operator's board policy keeps an issue with an open PR `In progress`. Reconcile the Project workflow separately before broad use of closing lines on open PRs.

Assign the PR template, PR-body validation, and conventions to #84 or a scoped successor. Assign commit-message enforcement to #92. Issue closure automation is outside the current #120 scope and needs explicit refinement or a successor if later required. This decision preserves the five required checks, current approval, resolved threads, current branch, squash merge, and operator-only merge boundary recorded in [the workflow](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/docs/src/content/docs/workflow/index.md).

Revisit the decision if the GitHub behavior or auto-close setting changes, a positive trial contradicts the documented link behavior, or Project transition evidence conflicts with the board policy.

## Evidence

The [research notes](https://github.com/tbhb-dev/agent-orchestration-poc/blob/6309b8cd416e948cadb142f783e53f75c279e096/research/gates/pr-issue-linkage/notes.md) compare both options and propose fixtures. The [evidence log](https://github.com/tbhb-dev/agent-orchestration-poc/blob/6309b8cd416e948cadb142f783e53f75c279e096/research/gates/pr-issue-linkage/evidence.md) records source times, REST requests, header values, observed timelines, validator results, and missing captures.
