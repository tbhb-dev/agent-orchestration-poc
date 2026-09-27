# Synthetic stub policy cases

All URLs, actors, item IDs, issue numbers, and records below are synthetic. No GitHub object represented here was created by this fixture.

## Stub and duplicate search

Stub URL: `https://api.github.com/users/fixture-owner/projectsV2/9/items/4242`

Title: `process(workflow): record a discovered follow-up`

Body: `Record the follow-up before it is dispatched. The current procedure lacks a durable source link.\nSource: https://github.com/fixture-owner/fixture-repo/issues/17\nRecorded-by: fixture-agent, Codex`

Search: `GET /search/issues?q=repo%3Afixture-owner%2Ffixture-repo+is%3Aissue+is%3Aopen+follow-up&per_page=100`, all pages. Draft inventory: `GET /users/fixture-owner/projectsV2/9/items?per_page=100`, all pages. Result: matching open issue 16 covers the work. Disposition: extend issue 16 and do not create item 4242. A second case has no match and permits the draft.

## Draft body and verdict

Draft URL: `https://github.com/fixture-owner/fixture-repo/issues/17#issuecomment-7001`

Draft comment body:

```text
## Goal

Record a discovered follow-up after approval.

## Context and links

Stub: https://api.github.com/users/fixture-owner/projectsV2/9/items/4242
Source: https://github.com/fixture-owner/fixture-repo/issues/17

## Dependencies and paths

Allowed paths: docs/example.md

## Acceptance criteria

- [ ] The example is documented.

## Evidence required

Run the documentation check.

## Docs impact

Update docs/example.md.

## Out of scope

Code changes.
```

Verdict URL: `https://github.com/fixture-owner/fixture-repo/issues/17#issuecomment-7002`

Verdict record: `Stub review: ready`, `Stub-URL: <item 4242 URL>`, `Draft-URL: <comment 7001 URL>`, `Body-SHA256: <digest from comment body>`, `Stub-SHA256: <digest from title and body JSON>`, `Reviewer: Codex CLI 0.157.1, gpt-6-astra, medium`. The synthetic reviewer `fixture-reviewer` represents `tbhbbot`. Both comments have equal creation and update times. An edited verdict, newer draft comment, changed Project draft, or later changes-needed verdict refuses creation.

## Creation read-back and old Backlog

Synthetic new issue URL: `https://github.com/fixture-owner/fixture-repo/issues/18`. Its `body` equals draft comment 7001 and its `user.login` is `fixture-author`, which represents `tbhbagent`. A new comment on the issue links item 4242, comments 7001 and 7002, and the digest. A differing body or author is an exception. The coordinator moves issue 18 to Refined and retires item 4242 after verification.

Synthetic old Backlog issue 12 predates the direction at `2026-09-27T05:34:59Z`. It remains issue 12 in Backlog until approved refinement. The coordinator then moves issue 12 to Refined without deletion or recreation. It is not counted as a new post-activation creation by #183.
