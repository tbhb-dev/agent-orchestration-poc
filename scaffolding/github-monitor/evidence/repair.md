# Temporary REST repair evidence

## Sources and scope

[documented] The GitHub documentation checkout at `/var/folders/ns/cc4x7s5j5271ltrw1t08w7p40000gn/T/github-events-98/github-docs` resolved to `github/docs@18945a31a4f2d97beb6c5c1a7479102e23c25727`. I read `content/rest/using-the-rest-api/rate-limits-for-the-rest-api.md` and `best-practices-for-using-the-rest-api.md` at that commit. Those pages describe response rate headers as authoritative, Link pagination, conditional ETags, serial requests, and 304 primary-budget behavior. The source checkout is under the sandbox's temporary writable root because `~/Code/github.com` is outside this worker's writable roots. The scaffold sends REST API version `2026-03-10`, matching the committed monitor design at `docs/src/content/docs/design/github-event-monitor.md`.

[schema] `scaffolding/github-monitor/store.py` version 1 stores only explicit tracked objects and per-component invalidation generations. `Store.complete_component()` compares the captured generation in a SQLite transaction. `Store.restart()` advances each generation and marks observations stale. The repair uses these published #167 interfaces without changing the shared schema.

[observed coordinator report] Issue #179 records that a coordinator `gh api 'users/tbhb/projectsV2/9/items?per_page=100&fields=<field ids>'` read returned Status, Priority, and Phase using REST core budget at 2026-09-27 01:00 as `tbhbagent`. That report is separate from this worker's fixtures. [untested] Project item PATCH remains untested and this repair does not use Project fields.

[observed dispatch] In a comment on issue #179, the coordinator recorded installation principal `165297562` from a delivered webhook payload. [untested] Its App read scopes remain unrecorded. This worker did not receive a secret, request an installation token, run `op`, or send an authenticated App request.

## Fixture and limit trace

[verified] `mise run monitor:test-repair` exited 0 with 36 tests. The loopback issue fixture made five requests: issue detail, issue comments, labels, final issue detail, and final issue comments. It covered changed issue body, changed comment body without an invalidation, and an invalidation during collection. Each yielded an incomplete identity result. The restart fixture retained stale or dirty state when the generation or final digest changed. The changed PR head test compares initial and final authoritative PR digests.

[verified] The two-page loopback fixture retained separate ETag and exact-body cache entries per page. Its second pass reused a 304 for page one only, then received 404 for page two and reported incomplete. Table tests cover a 304 with missing or mismatched saved ETag, unknown or contradictory response headers, 100-request reserve refusal, the 20-request ceiling, and the 10-page ceiling. The local file-lock fixture showed that a second bootstrap waited until the first released the same principal/resource lock.

[verified] `budget_handoff()` retains principal, REST resource, observed limit, remaining, reset, retry-after, request count, and page count as plain values for #170. Each REST response updates the shell's observed header record. The fixture uses remaining `4000` of limit `5000` and a five-request issue pass. [untested] Atomic #170 scheduler admission after #170 lands and live concurrent App bootstrap remain untested.

The endpoint and final-reread matrix is in `scaffolding/github-monitor/docs/repair.md`. PR review-thread resolution, latest check attempt selection, required ruleset, last pusher, and Project fields remain unknown or excluded. The ten-page cap can stop a PR pass before its final rereads, so the scaffold does not claim complete PR readiness. REST repair cannot recover an unobserved intermediate event history.

## Commands and limits

| Command | Exit | Result |
| --- | --- | --- |
| `mise run vale:sync` | 0 | Pinned prose styles synchronized once in this worktree. |
| `mise run monitor:repair -- --tracked` without App inputs | 2 | Refused before any network request or local store write. |
| `mise run monitor:test-repair` | 0 | 36 fixture tests passed on loopback and plain core values. |
| `mise run fmt` | 0 | No unrelated path changed. |
| `mise run check` | 0 | Repository checks and coverage floors passed. |
| `mise run check:mutation` | 0 | Go core 145 killed of 149, Python core 994 killed of 1068. Scaffolding has no mutation floor. |

[observed] `mise exec -- go run github.com/boyter/scc/v4@v4.1.0 --by-file --format json ...` counted 800 Python code lines across the three new Python files. The task adds eight TOML lines and the repair note adds 22 nonblank prose lines, for 830 #84 units before excluded evidence. This exceeds the stated 800-unit limit by 30. The split proposal is to move the provisional bootstrap, lock, and handoff contract into #170's owned budget slice. The page collector and repair decisions stay in #179. The worker did not create an issue.

[untested] Live GitHub App reads, real pagination and 304 behavior, live restart repair, installation-token acquisition, and App read-scope confirmation remain outside this fixture run. No private response body, credential, token, or key is committed.
