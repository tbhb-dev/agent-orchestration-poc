---
title: "0007: webhook-fed pull request monitor"
description: Proposed agentd state monitor, authenticated waits, GitHub App identity, and REST stopgap.
---

## Status

[untested] Proposed 2026-09-26 for [issue #98](https://github.com/tbhb/agent-orchestration-poc/issues/98). Credential and public-ingress changes require coordinator review and operator approval, and this record leaves those settings unchanged. It targets the existing App and Funnel reported by the coordinator.

## Context

[observed] Issue #98 records the operator's report that seven Codex runs exhausted the shared user GraphQL budget at about 20:21 local time on 2026-09-26. The designer did not reproduce the original exhaustion. The existing messaging sketch assumes every harness wakes when a background process exits, while the 2026-09-26 harness assessment describes Codex unified exec collection through `write_stdin`. PR #82's reviews also demonstrated that direct agent JetStream requests can spoof another sender through broker replies.

## Decision

[untested] Add the monitor to `agentd`. Receive the existing read-only GitHub App's webhooks through the fixed `/hooks/github` Funnel route to a dedicated loopback listener on port 8787, verify original bytes, persist an inbox, and reduce events with pure functions. Store one projection and publication outbox in the SQLite registry. HTTP and bus clients see the same revision. Repair dirty and stale state with installation-token REST reads. Bound collection turns and commit observations without clearing newer invalidations. Bound inbox storage, reject overload before acknowledgment, delete processed raw bodies transactionally and preserve unprocessed deliveries plus 30-day dedup metadata.

[untested] Select `agentctl` waits through #96's authenticated relay for workers. A wait specifies a condition, expected head SHA, baseline where needed, and deadline. Add coordinator-only HTTP waits on separate loopback port 8788 before #96, retaining the pure predicate, registry revision watch and HTTP endpoint afterward. Direct worker HTTP access would require separate scoped credentials. Sharing the operator credential is prohibited. Use SSE for the coordinator timeline. Preserve the prohibition on agent JetStream API and ack access. Support harness-specific result collection instead of promising that every background process automatically wakes an idle model.

[untested] Adopt a serialized coordinator-owned REST/ETag polling procedure immediately. Defer implementer and reviewer Apps to a separate #83 follow-up. Keep the monitor read-only and keep `tbhbbot` until an operator-owned fixture establishes custom App approval counting under the actual ruleset without bypass.

[untested] Retrieve the existing 1Password item through an operator-only helper under a separate service principal, using an inherited anonymous pipe into daemon memory. Do not store key files or inject secrets into worker environments. Require worker-read-denial and rotation tests before credentialed deployment. If the boundary cannot be enforced, keep the coordinator stopgap.

[observed, reported by the coordinator] The [issue #98 setup comment](https://github.com/tbhb/agent-orchestration-poc/issues/98#issuecomment-5851360250) records the App, 1Password item and fixed public URL `https://usdholt05.ibex-paradise.ts.net/hooks/github`. The later [probe comment](https://github.com/tbhb/agent-orchestration-poc/issues/98#issuecomment-5851385815), [review](https://github.com/tbhb/agent-orchestration-poc/pull/99#pullrequestreview-5328337227) and assignment report installed App delivery and signed Actions traffic. The designer did not observe those deliveries. Daemon processing, bootstrap isolation and burst recovery remain untested.

## Consequences

[inference] Central collection removes duplicated worker reads and an installation token separates the monitor's primary budget from the operator's user budget. It adds a public webhook parser, durable recovery, and credential operations. Funnel exposes only the dedicated ingress. Tailnet-only Serve requires a public relay to receive GitHub traffic. Conditional REST avoids inbound exposure but adds latency and consumes budget on changed responses.

[documented] GitHub does not automatically retry failed webhook deliveries. Authenticated conditional 304 responses avoid primary-rate-limit cost. `gh webhook forward` is a development-only extension that creates a repository or organization hook. Source versions and limits are recorded in the evidence below.

[untested] Revisit the deployment route if offline buffering is required. Preserve the coordinator-owned public route during local cutover and rollback. Revisit the worker transport if #96 cannot provide bounded authenticated requests and confirmed publication. Do not promote the design to accepted runtime behavior until crash/replay tests, secret isolation, harness reachability, and end-to-end delivery evidence exist. The monitor cannot authorize merges from a stale cache or incomplete thread history.

## Evidence

[documented] The [design page](/design/github-event-monitor/) gives the state contract, alternatives, operator actions, and work items. [Research notes](https://github.com/tbhb/agent-orchestration-poc/blob/docs/98-github-event-monitor-design/research/gates/github-events/notes.md) and [versions](https://github.com/tbhb/agent-orchestration-poc/blob/docs/98-github-event-monitor-design/research/gates/github-events/versions.md) pin GitHub docs `18945a31a4f2d97beb6c5c1a7479102e23c25727`, CLI forwarding source `115d4d6768b55c74ee7d7c61d4775d83fdc323d2`, and Tailscale v1.102.4 source `bbcd7d1fc2054b9189ebc1531acf74bd880ca0c8`. Raw issue, review, and REST records accompany them. These sources establish documentation and schema claims, not a deployed monitor.
