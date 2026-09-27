# Project 9 read-only feasibility evidence

## Versions and sources

[observed] Run date: 2026-09-27 UTC. Codex CLI 0.157.1, `gpt-6-sol` at high implemented this probe. REST API version requested and selected: `2026-03-10`. Authenticated principal: `tbhbagent`. This file omits credential values, private item IDs, payloads, and field IDs.

[schema] `github/docs@18945a31a4f2d97beb6c5c1a7479102e23c25727` was read from `$TMPDIR/github-events-98/github-docs`, including `src/rest/data/fpt-2026-03-10/projects.json` item and field definitions and `src/webhooks/data/fpt/projects_v2_item.json`. The latter lists item `created`, `deleted`, and `edited` actions for organization-level projects and says the event is in public preview. `git -C "$TMPDIR/github-events-98/github-docs" rev-parse HEAD` verified the checkout commit, while user-owned Project 9 event delivery remains untested.

## REST matrix

[verified] `mise run monitor:project-probe -- --rest-matrix` exited 0. The 2026-09-27T05:17:31Z collection made five REST GETs, all HTTP 200 with selected API version `2026-03-10` and `x-ratelimit-resource: core`: `GET user`, `GET users/tbhb/projectsV2/9/fields?per_page=100`, two pages of `GET users/tbhb/projectsV2/9/items?per_page=100&fields=<four field IDs>`, and `GET repos/tbhb/agent-orchestration-poc/issues/172`. The item listing followed its `Link` next cursor and ended on page two. The command allows at most five item pages and seven total GETs. It does not call GraphQL. This complete snapshot counted 143 item identities, 143 populated Status values, 122 Priority values, 122 Phase values, and 17 Worker values. Missing values are unknown at field level. `Status=Ready` occurred zero times in this snapshot. Issue #172 labels came from the issue response and were not used as Project values. The result was marked `source-confirmed` with a five-minute expiry. It does not establish a durable mirror.

[observed] An initial direct `gh api -i` read without an API-version header selected `2022-11-28`. The probe requests `2026-03-10` explicitly. Consecutive field and item reads returned `x-ratelimit-used` 256 and 257 with `x-ratelimit-resource: core`, confirming that the item read spent one REST core request. A direct `gh api -H 'X-GitHub-Api-Version: 2026-03-10' -i 'users/tbhb/projectsV2/9/items?per_page=1' --jq 'length'` exited 0 and returned HTTP 200, selected `2026-03-10`, and REST resource `core`.

## Observation window

[observed] `mise run monitor:project-probe -- --observe-seconds 2` exited 0. Its UTC window was 2026-09-27T05:17:42Z through 05:17:45Z. `GET repos/tbhb/agent-orchestration-poc/hooks?per_page=100` returned HTTP 404 and `GET app/hook/deliveries?per_page=100` returned HTTP 401 for the authenticated user. The first selected API version `2026-03-10`, while the latter did not report a selected version. Both responses reported REST resource `webhook_deliveries`. The App subscription and observed addition, removal, and field-change delivery are `unknown`. The probe did not generate an event or edit a live item. A coordinator-approved disposable item and operator-readable App delivery log are required for a live event test.

## Tests and limits

[verified] `mise run monitor:test-project-probe` exited 0 with 17 passing tests. The tests cover partial page classification, unknown fields, missing and delayed events, unauthorized targets, URL cursor filtering, per-field source rows, and properties of counts and authorization. Later validation runs and exits are recorded in the PR. This worktree lacks a loopback receiver, so the read-only probe does not claim an integration test for delivery through the shell.

[inference] The REST item read can supply a short-lived, confirmed-field source to #168 when it uses the same bounded pages and expiry rules. #168 must mark individual unpopulated fields unknown. The local #182 ledger cannot replace that source. Event coverage for this user-owned Project remains untested.

[observed] A second `mise run monitor:project-probe -- --rest-matrix` exited 0 at 2026-09-27T05:26:18Z with 148 items across two pages, 148 Status values, 122 Priority values, 122 Phase values, and 18 Worker values. Each requested field row reported its path, selected API version, HTTP status, pagination, account, and missing-value count. [inference] The differing item counts reinforce that consumers must treat each collection as a timed observation without an atomic snapshot guarantee across pages.

## Validation and sandbox limits

[verified] `mise run fmt`, `mise run monitor:test-project-probe`, `mise run check:ruff`, `mise run check:imports`, `mise run check:pyrefly`, `mise run check:deadcode`, `mise run check:dupl`, `mise run check:vale`, and `mise run docs:build` exited 0. The final focused probe suite passed 17 tests. `mise exec -- gitleaks dir --redact --no-banner scaffolding/github-monitor` exited 0.

[observed] `mise run check` exited 0 at the revision before the 30-second REST timeout and final evidence edits. A later aggregate run stopped producing output in Go integration coverage after its other tasks passed, and was interrupted with exit 130 after a bounded wait. `mise run check:mutation` initially exited 1 because mutmut copied the tests without the disposable script. After the test loader fix, `mise run check:mutation:python` exited 0 with a 97.22 percent core score, while the first Go component exited 0 with a 97.32 percent score. A later aggregate mutation run stalled in Go mutation coverage and was interrupted with exit 130. The PR CI checks are the final gate for this revision.

[observed] `mise run docs:check-links` exited 1. Chromium could not launch inside the sandbox, and the validator reported five links in existing site files that this PR leaves unchanged: `index.md`, `decisions/0007-github-event-monitor.md`, `design/index.md`, `project/history.md`, and `workflow/tooling.md`. The sandbox also refused `ps` and `pgrep`, which prevented process inspection during the stalled coverage runs.
