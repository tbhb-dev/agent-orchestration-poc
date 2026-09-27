# Project 9 feasibility

## Scope and command

Issue [#172](https://github.com/tbhb/agent-orchestration-poc/issues/172) specifies this read-only, disposable probe. Run `mise run monitor:project-probe -- --rest-matrix` for bounded Project and issue reads or `mise run monitor:project-probe -- --observe-seconds 2` for a bounded availability window, with neither mode requesting GraphQL or changing a Project item. Each matrix response includes the authenticated account, selected API version, status, REST resource, page count, collection time, and five-minute expiry. At most five item pages of 100 entries each are read, and each GET times out after 30 seconds. An unfinished page sequence makes the contract `unknown/incomplete`.

## Source matrix

The following sources were [verified] on 2026-09-27 with `tbhbagent` and GitHub REST API version `2026-03-10`. The endpoint definitions are [schema] in `github/docs@18945a31` at `src/rest/data/fpt-2026-03-10/projects.json`. The live command and response summary are in [the evidence](../evidence/project-feasibility.md).

| Requested value | REST source | Result and consumer contract |
| --- | --- | --- |
| Ready | Project 9 item `Status` field equals `Ready` | [verified] Field definition and item values are REST-visible. A missing item value is `unknown`. |
| Priority | Project 9 item `Priority` field | [verified] REST-visible when populated. Missing is `unknown`. |
| Phase | Project 9 item `Phase` field | [verified] REST-visible when populated. Missing is `unknown`. |
| Worker | Project 9 item `Worker` field | [verified] REST-visible when populated. Missing is `unknown`. |
| Item identity | Project 9 item `id` and `content` | [verified] Both occurred in all 143 items in this snapshot. Private IDs are omitted from committed evidence. |
| Issue or PR labels | Repository issue and PR REST responses | [verified] Issue #172 labels were readable. Labels are separate from Project item fields and never substitute for them. |

The [#168 adapter](https://github.com/tbhb/agent-orchestration-poc/issues/168) receives only values from a complete Project read, with source path, collection time, expiry, item identity, and a field-level completeness flag. An absent value, failed page, or expired observation is `unknown/incomplete`. [#157](https://github.com/tbhb/agent-orchestration-poc/issues/157) and [#159](https://github.com/tbhb/agent-orchestration-poc/issues/159) cannot treat a pending [#182](https://github.com/tbhb/agent-orchestration-poc/issues/182) ledger value or an issue label as a confirmed Project field. #182 alone owns any later readback-confirmed publication.

## Events and operator test

The pinned GitHub webhook schema at `github/docs@18945a31` describes `projects_v2_item` actions `created`, `deleted`, and `edited` for organization-level projects. It does not establish delivery for user-owned Project 9. The probe reads authenticated App metadata for subscription state when available, then reads a delivery page after the observation window and checks up to ten matching delivery details against the Project node ID. [Observed] This account received HTTP 404 from repository hook listing and HTTP 401 from both App metadata and delivery listing. App subscription and delivery for addition, removal, and field change remain `unknown`. The two-second observation did not generate a live event, and absence in that interval proves nothing about event coverage.

An operator must make the App subscription and delivery log readable without exposing credentials to a worker. The coordinator must designate and approve a disposable Project 9 item, then record its identity privately and its authorization source. Under that approval, perform one addition, one removal, and one field change, retain redacted delivery actions and timestamps, and verify the App receives each. The operator owns any App setting or grant change. Until this test, use fixture classifications only.

The permanent [Project integration replacement #186](https://github.com/tbhb/agent-orchestration-poc/issues/186) removes this probe after the real source and event path land. #167 adds the shared monitor entry point and note link. #182 adds the temporary ledger and sync. A local pending record cannot prove current Project state.
