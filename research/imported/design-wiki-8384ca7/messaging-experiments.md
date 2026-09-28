---
title: Messaging conversation experiments
summary: "Proposed comparisons of inbox and ambient coordination, wake controls, envelope formats, and structured requests."
type: design
status: draft
tags:
  - area/messaging
  - area/orchestration
  - scope/destination
updated: 2026-09-27
---

**Decided direction — operator discussion on 2026-09-27, handed off by Claude:** One agentd per host serves Groups as authority/policy scopes. The starting conversation constructs are DMs where participants receive everything, ambient channels with inbox mentions, and threads within either. The purpose is an experiment, not a predetermined winner. Channel is a provisional product name, distinct from Claude MCP channels.

**Proposed experiment mechanics:** Compare matched coordination tasks using fixed-participant DMs and ambient channels with targeted mentions. Keep workload roles, task context, model/harness versions, backend, output budgets, and Group policy comparable. Record the chosen receive A/B and adapter profile rather than mixing their effects into the conversation comparison. This page is destination experiment design, not a PoC input or scheduled work. If deliberately transferred later, create or mark the specific input as `scope/bridge`; do not infer transfer from this page.

## Participant and authority controls

The participant revision generalizes message actors/recipients to workload, bot, and operator IDs. Keep workload model-turn measures workload-only; report bot delivery/acknowledgment separately with seen not applicable. Record qualified capability profiles independently from applicable permissions so an absent wake is not mislabeled a conversation failure. Suggested bot/bridge cases include untrusted relayed content, asserted author versus authenticated sender, revocation during subscriptions, denied outbound egress, and echo/duplicate processing. Ambient bot membership versus installation-only reads remains an experimental choice to record, not a silently selected policy.

## What to compare

| Measure | Automatic evidence candidates | What still needs judgment or extra instrumentation |
| --- | --- | --- |
| Model turns spent on wakes, per workload and message | Wake attempt/input correlation, native turn IDs, accepted message/delivery references. | Native turn instrumentation is required; one wake may cover many messages and several wakes may share a turn. Report coalesced/shared/unattributed turns rather than double-counting. |
| Missed relevant information | Authorized membership intervals, posted content references, history fetch ranges, mention resolution, later action timestamps. | Main ambient risk: operator review of sampled decisions against information available at that time. A read/cursor does not prove knowledge, and no read does not prove ignorance through other sources. |
| Send-to-reply latency | Message acceptance and explicit `reply_to_id` acceptance timestamps. | Relevance/adequacy of the reply is judgment; report no-reply outcomes and run cutoff, not only completed replies. Separate original-delivery recipients from ambient responders. |
| Re-sends and pings before a reply | Distinct accepted message keys, recipients, mention resolutions, explicit follow-up references when provided. | Same-key retries are transport recovery, not anxiety. Semantic repeats/new-key pings require sampled classification; recipient overlap alone is not proof. |
| Duplicate actions | Repeated input attempts and correlated action/tool records where instrumented. | Stable IDs and duplicate sends do not establish duplicate effects. Review outcomes or task-specific action IDs to distinguish intentional repetition from double execution. |
| Channel read behavior | History fetch telemetry, cursor advances, unread summaries, preceding mentions and wake inputs. | Whether reading was unprompted, mention-driven, or explicitly instructed often needs transcript review. Cursor movement alone cannot establish motive or attention. |

## Event and telemetry contract

The proposed `messaging_events` log records accepted messages, resolved mentions, explicit replies, receipt transitions, actual membership changes, and cursor advances atomically with their database state. Retain conversation/root, actor participant/kind-specific binding, affected participant, sequence, and recorded time, with visibility-filtered access. Read-only fetches and native wakes need separate telemetry: returned ranges/count/bytes, selected adapter, attempt/native IDs, observed input/turn, and outcome uncertainty. No event should claim atomicity across a native push and SQLite commit.

Notification-only adapters may keep correctness state in memory, as the earlier delivery proposal recommends. A measured run still needs durable diagnostic events or an external collector; after a crash mark coverage gaps. Do not convert telemetry into delivery/seen receipts. Persisted content attempts remain necessary for uncertain-outcome recovery independently of measurement. No-op retries should not look like fresh membership/cursor transitions, and same-key acceptance recovery should be distinguishable from a new logical message.

## Suggested protocol

1. Use comparable tasks in both modes, varying order across runs and repeating across harness profiles. Include a normal coordination task, a long busy task, and an ambient fact needed for a later decision.
2. Record eligibility/join boundaries and a run manifest of selected unresolved semantics. For the first comparison, recommend immutable DM sets, message-rooted threads, and explicit cursor advancement; these remain proposals.
3. Exercise targeted and channel-wide mentions separately. Keep urgency/coalescing fixed within a comparison; only a later comparison should vary those. Ambient posts must produce zero workload wakes even if UI/SSE listeners learn of the update.
4. Include role changes, late joins, reconnects, lost send/receive responses, compaction, burst traffic, and a permission wait. Separate deliberately injected failure runs from ordinary behavior results.
5. Review a sampled set of decisions and actions with the operator, using a written rubric for relevance, semantic pings, and duplicate effects. Include apparent successes to avoid only studying visible failures.
6. Report denominators, missing telemetry, no-reply cases, coalesced turns, version/profile differences, and judgment disagreements. Do not claim a conversation winner from a single favorable run.

## Tradeoffs to decide from evidence

Immutable DM sets preserve a stable audience but can fragment related work when participants change; mutable DMs are the explicit alternative. Rooted threads avoid separate lifecycle/membership commands but implicit channel participation can grow inbox traffic; follow/unfollow or thread controls are alternatives if the runs demonstrate a need. Explicit channel cursor advancement avoids silent list side effects but adds model cooperation; list-and-advance is cheaper with a lost-output gap. Measure these separately from receive acknowledgments.

Neither reply speed nor low wake count is sufficient alone: channels can appear cheap by leaving relevant information unread, and DMs can appear responsive by repeatedly interrupting work. No quantitative acceptance thresholds are decided. The operator should choose the tradeoff after reviewing missed-information and duplicate-action outcomes alongside turn cost.

## Additional comparisons proposed for review

**Codex integration of Claude's four pre-review pages:** Instrument [loop/budget controls](messaging-loops-and-budgets.md) with accepted/rejected sends, resolved fan-out, wake attempts, native acceptance/unknown outcomes, observed turns, coalescing ratio, deferred age, backlog recovery, breaker trips/resumes, operator interventions, and available causal-depth coverage. Report unknown-trigger rate alongside depth distributions; pull/non-injecting profiles cannot demonstrate a universal depth bound. Separate legitimate collaboration paused by a detector from actual waste using a written rubric and operator review. Measure in-memory reset behavior, sleep recovery bursts, permitted urgent traffic, and operator attention volume before choosing any threshold.

Compare the [text envelope](messaging-envelope.md) with JSON using matched tasks, bodies, byte budgets, and harness profiles. Measure tool/output size, successful reply commands, audience mistakes, incomplete-output handling, and rubric-scored trust-boundary errors. Include fake headers, marker collisions, bridge assertions, and oversized bodies. A single model resisting one injected tag is not a security guarantee. Record versions, samples, and ambiguous outcomes; no test here has run.

[Structured requests](messaging-requests.md) are a candidate second comparison, after the inbox-versus-ambient baseline: compare duplicate work, claim races, stale claims, outcome reporting, cancellation races, and sender follow-up frequency against `expects_reply` alone. Claude recommends deferral and Codex concurs for experimental isolation; whether requests belong in the first experiment remains the operator's decision. Request status is self-reported coordination state, not verified Task success. Test `any` candidate declines and `each` partial outcomes separately.

## Provenance and open choices

The experimental direction and three constructs were decided in the operator's 2026-09-27 discussion recorded by Claude. Claude proposed the six measurement categories and conversation mechanics. Codex supplied the matched-run protocol, telemetry/judgment split, attribution rules, and failure cases as proposed synthesis. Earlier receive, presence, exit-code, Group-default, keyset, output-format, byte-budget, adapter, urgency, and naming choices remain open. No experiment was run or transferred into the sibling PoC by writing this page.

The operator's 2026-09-27 participant/authority discussion, handed off by Claude, decided bots as distinct messaging participants, both SPIFFE authentication mechanisms, Group/host installation scopes with future scopes possible, bridges as bot installations with bridging permissions, and capabilities distinct from permissions. The participant/installation mechanics are Claude proposals; Codex's kind-specific lifecycle, containment, and evidence qualifications are linked from [Participants and permissions](participants-and-permissions.md). Issuer/enrollment, first bot delivery paths, ambient membership, workload installation unification, and host-wide federation meaning remain open.

The 2026-09-27 pre-review integration carries Claude's loop/budget, oversight, request, and envelope proposals into this page with labeled Codex synthesis. All new mechanics remain proposed. Operator message authority, request inclusion in the first experiment, every control threshold, and earlier messaging/participant open decisions remain unresolved; see the four source pages linked from [the index](README.md). No implementation or new harness probe was performed.
