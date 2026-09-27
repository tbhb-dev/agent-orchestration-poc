---
title: Temporary GitHub monitor repair
description: Fixture-backed REST repair contract, recovery commands, and incomplete component limits for issue 179.
---

## Scope and recovery

Run `mise run monitor:status` to inspect the local store, then `mise run monitor:repair -- --tracked` from the coordinator's protected App launcher. The operator stated on 2026-09-27 that every monitor App read permission is granted, as recorded in the coordinator's #179 note. The launcher supplies `GITHUB_APP_INSTALLATION_ID=165297562`, `GITHUB_APP_READ_SCOPES`, and a short-lived `GITHUB_INSTALLATION_TOKEN`. App key retrieval and token requests remain coordinator operations outside this command. The token stays out of output and committed evidence. The coordinator has not requested an installation token, so live App repair remains untested.

The command reads only objects in the version 1 store's explicit tracking set. It takes an exclusive local lock for installation `165297562` and REST `core`, makes one header-establishing repository GET, then caps collection at 20 requests and 10 pages per object while keeping at least 100 primary requests in reserve. Unknown or contradictory response headers stop the pass. Each response updates the observed REST header record. Reset time alone never admits a request. The future #170 scheduler receives the same installation and resource identity, page count, worst-case request count, and observed headers before it replaces this serialized bootstrap.

The conditional cache is stored under ignored `.local-cache/github-monitor/` and is named for installation, REST resource, and API version `2026-03-10`. Each page key is the complete URL. A 304 reuses the matching page's saved ETag and exact body, including its pagination Link. New 200 responses replace those values and clear an absent Link. A missing page, HTTP failure, limit, or changed final read leaves affected components incomplete.

## Component sources

| Component | REST source | Final proof and current limit |
| --- | --- | --- |
| Issue body and state | `GET /repos/tbhb/agent-orchestration-poc/issues/{n}` | Initial and final body, state, and update digest must match. |
| Issue verdict comments | `GET /repos/tbhb/agent-orchestration-poc/issues/{n}/comments?per_page=100` | Follow Link pagination, then reread the comment set. Missing pages leave it unknown. |
| Issue and PR labels | Issue detail and `GET /repos/tbhb/agent-orchestration-poc/issues/{n}/labels?per_page=100` | Follow Link pagination. The issue body reread guards the authoritative detail. |
| PR head, base, body, and state | Issue detail and `GET /repos/tbhb/agent-orchestration-poc/pulls/{n}` | Initial and final issue body and PR head, base, state, and update digest must match. |
| PR reviews | `GET /repos/tbhb/agent-orchestration-poc/pulls/{n}/reviews?per_page=100` | Review pages are read, but complete thread resolution is unsupported and the component remains unknown. |
| PR review comments and threads | `GET /repos/tbhb/agent-orchestration-poc/pulls/{n}/comments?per_page=100` | Review comment pages are read, but not reread at the end. Resolved thread state also lacks an implemented authoritative REST read. The component remains unknown. |
| Check runs and statuses | `GET /repos/tbhb/agent-orchestration-poc/commits/{head}/check-runs?per_page=100` and `GET /repos/tbhb/agent-orchestration-poc/commits/{head}/status` | Both are reread after collection. Latest workflow attempt selection is unsupported and checks remain unknown. |
| Required ruleset and last pusher | Repository ruleset and PR commit sources | These sources are not implemented, so merge readiness remains unknown. |
| Project fields | Source investigation in #172 | Excluded from this repair. No Project field is published as complete. |

Each completed component report specifies its endpoints, collected pages, page completion, ETag, exact-body SHA-256, initial and final digests, collection time, and unknown reason. An interrupted collection reports its error and leaves the component unknown. The local store clears a component only if its captured invalidation generation still matches in the committing transaction. Failed passes retract existing complete observations at that generation. Receiver restarts advance generations and mark prior observations stale until a complete repair. An unchanged local generation cannot replace the final authoritative rereads.

The repair publishes current state only. REST cannot reconstruct an unobserved intermediate event or prove its order. A failed pass retains stale or dirty state, and the coordinator can rerun it after resolving the reported reason and checking remaining budget. The command does not write GitHub or decide whether a PR is merge ready.
