---
title: 0016, Project drafts hold unrefined work
description: Decision for Project 9 stubs, exact-body refinement, and issue creation.
---

## Status

Proposed on 2026-09-27 for [issue #161](https://github.com/tbhb/agent-orchestration-poc/issues/161). The coordinator's [later direction](https://github.com/tbhb/agent-orchestration-poc/issues/161#issuecomment-5853040703) governs new work now. The full review and exception-check contract activates only after the coordinator records the UTC instant described below.

## Context

Agents need to record discovered work before its scope is approved. Creating an issue first gave duplicate work an issue number in [#141](https://github.com/tbhb/agent-orchestration-poc/issues/141) and [#142](https://github.com/tbhb/agent-orchestration-poc/issues/142). A Project draft has no repository issue number or comment thread. A sub-issue is already an issue, so it cannot be a stub.

The [option evidence](/workflow/stub-refinement/#store-and-review-evidence) compares a Project draft with a repository discussion. Project 9 already holds work and exposes drafts through paginated REST reads. Discussions would place unrefined work outside the board and require another inventory for duplicate search. The Project draft is the canonical store.

## Decision

An agent records a short Project 9 draft in Backlog after a paginated duplicate search. Its title, what and why, source issue or PR URL, and recording agent identify the stub. The source issue or PR holds a `Stub:` link and later holds an author comment containing the complete proposed issue body. That comment is the stable draft-body URL. A separate `tbhbbot` comment on the same source records the verdict, the draft-body URL, the Project item URL, and exact digests. Each review round creates a new comment. Edited comments are invalid.

The reviewer binds approval to the exact full-body comment bytes and the current Project draft title and body. A changed Project draft or a new author revision requires a new review. The latest effective `tbhbbot` verdict for that stub governs. After approval, `tbhbagent` creates an issue through REST with the exact approved body. A read-back verifies its body and `user.login`. A new issue comment links the approved stub and digest. The coordinator places the new issue in Refinement and retires the draft only after the read-back succeeds. This is a linked replacement rather than the GitHub draft-conversion mutation, whose documented path is GraphQL. The operator's current REST-only rule excludes that mutation.

Backlog contains draft stubs. Refinement contains approved issues awaiting readiness. Ready means dispatchable now and contains at most eight items. In progress, Blocked, and Done follow. In review is retired. Existing Backlog issues stay issues and move to Refinement after approval. The coordinator preserves their issue numbers during this transition.

## Consequences

The source thread provides stable comment URLs and a distinct reviewer identity, but it can be edited or deleted. A missing or edited author snapshot or verdict fails closed. The draft-to-issue relationship needs a checked source link and a post-creation issue comment. The coordinator controls Project status and draft retirement, while agents wait for approval before creating an issue.

The exact activation instant is pending a coordinator comment on #161 of the form `Stub policy activation: YYYY-MM-DDTHH:MM:SSZ`, after #90's effective-verdict contract and #183's fixture-verified checker are available. The direction for new unrefined work is already in force from the coordinator comment created at `2026-09-27T05:34:59Z`. These instants serve different purposes. The checker uses the later activation instant and reports exceptions without editing GitHub.

## Evidence

The [workflow](/workflow/stub-refinement/) gives the REST paths, byte contract, transition, and manual escalation. The [evidence record](https://github.com/tbhb/agent-orchestration-poc/blob/main/reports/inputs/stub-workflow-evidence.md) records versioned documentation, read-only probes, synthetic fixtures, and validation limits. Revisit this decision if GitHub adds an approved REST conversion path that preserves exact body bytes and author identity, or if the source-thread review store becomes unavailable.
