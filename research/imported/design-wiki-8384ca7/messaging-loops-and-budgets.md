---
title: Messaging loops, storms, and wake budgets
summary: "Proposed combined wake policy and loop controls, with Codex review of accounting, causal evidence, and recovery gaps."
type: design
status: draft
tags:
  - area/messaging
  - area/orchestration
  - area/security
  - scope/destination
updated: 2026-09-27
---

**Claim status:** Everything on this page is **proposed**. Claude drafted it at the operator's request on 2026-09-27 after the operator asked for pre-review design of loop and budget controls. No threshold, mechanism, or schema change here has been accepted or tested. It builds on the [schema](messaging-schema.md), [data flow](messaging-data-flow.md), [delivery](messaging-delivery.md), and [experiment](messaging-experiments.md) pages, and uses "participant" in the sense of the [integrated participant proposal](participants-and-permissions.md), where workloads, bots, and the operator are all participants.

**Review navigation:** Claude's original proposal is retained below. The labeled [Codex review](#codex-review-and-combined-wake-policy) records integration recommendations and qualifications; where they differ, both remain proposals for operator review.

## Why this needs its own design

Once several agents and bots share conversations, the most likely failure is not a lost message but a runaway one. Every wake spends a model turn, and model turns are the system's scarcest and most expensive resource. A messaging system that stores every message correctly can still burn a large budget in minutes if nothing limits how often participants wake each other.

The failure modes worth designing against:

| Failure | How it happens |
| --- | --- |
| Ping-pong | Two agents trade acknowledgments ("thanks", "you're welcome", "let me know if you need anything") and each reply wakes the other. |
| Request cycles | A asks B for something, B asks A for context, A asks B again, and no one does the underlying work. |
| Fan-out amplification | A role mention wakes five workloads, each replies in the multi-participant DM, and every reply wakes the other four. |
| Mention storms | Repeated channel-wide mentions wake every member of a large channel. |
| Anxious re-pings | A sender with no visible reason for silence re-sends to a busy recipient, as observed in the operator's earlier PoCs. |
| Bot floods | A misbehaving or misconfigured bot posts or mentions at machine speed. |
| Bridge echoes | A bidirectional bridge relays its own relays back and forth. Loop prevention for bridges is covered in the participant model's bridge design. |
| Resume storms | After laptop sleep, backlogged deliveries and expired presence signals all fire wakes at once. |

## The governing principle: budget wakes, not messages

Storing a message is cheap. Waking a participant is not. The controls below therefore distinguish between the two:

- **Rate limits reject sends.** When a participant exceeds its send allowance, acceptance fails with an explicit error and a retry-after hint. The sender learns immediately and nothing is stored.
- **Wake budgets defer wakes.** When a recipient or group exceeds its wake allowance, messages are still accepted and delivery rows are still written. Only the adapter wake is postponed, to the next natural turn boundary or the next budget window. The recipient loses latency, not messages.
- **Circuit breakers pause and escalate.** When agentd detects a likely loop, it stops waking the participants involved in that conversation and alerts the operator. It doesn't delete, rewrite, or hide anything.

Nothing in this design silently drops an accepted message. A control that loses messages would create exactly the uncertainty that produced anxious re-pings in the first place.

## Send rate limits

Apply per-participant token-bucket limits at acceptance, with separate buckets for actions of different cost:

| Action | Relative cost | Rationale |
| --- | --- | --- |
| Ambient channel post without mentions | Low | Wakes no one, but can still flood history, UI views, and unread counts. |
| DM message | Medium | Wakes every other participant in the DM. |
| Targeted mention | Medium | Wakes each resolved mentioned member. |
| Role mention | Higher, scaled by resolved count | One action can wake many workloads. |
| Channel-wide mention | Highest | Wakes every member; already policy-gated. |

A rejected send returns `429 rate_limited` with `retry_after_seconds` and the exhausted bucket. The canonical retry rules still apply: a later retry with the same client message ID is the same logical send, not a new one.

Limits are set by Group policy for workloads and by installation for bots. Bots should start with tighter defaults than workloads, since a bot can post at machine speed without a model turn slowing it down. The specific numbers are **unknown** and should come from the [experiment](messaging-experiments.md), not from guesses written here.

## Wake budgets

**Per-recipient wake budget.** Cap how many adapter wakes a single workload receives in a rolling window. When the cap is reached, further deliveries stay pending and are presented together at the recipient's next turn boundary or when the window resets. This extends the coalescing already proposed in the [delivery page's urgency design](messaging-delivery.md#wake-timing-and-urgency). Urgent messages from participants whose policy permits urgency may bypass the recipient cap, but they still count toward the group budget below.

**Per-group wake budget.** Track aggregate wakes across a group's workloads per window, and show the current consumption to the operator. When the budget is exhausted, normal-urgency wakes are deferred for the whole group, urgent wakes are allowed only for roles the policy names, and the operator receives an attention notice. The operator can raise the budget, pause the group, or let deferral continue.

**Measure turns before tokens.** A token budget would track real cost more closely, but the research shows usage accounting has traps: a Codex fork inherits its source's cumulative totals, so summing thread totals double-counts, and compaction emits usage samples that aren't billable responses ([R2](https://github.com/tbhb/agent-orchestration-poc/blob/0d04ae5facd63448e278a08be68ce54922e6c994/research/imported/agent-session-tests/CODEX_SESSION_MANAGEMENT.md), E14). Start with wake counts, which agentd controls and can count exactly. Add token-based budgets later only from per-response accounting that avoids those traps.

## Loop detection and circuit breakers

**Structural signals only.** Agentd should detect loops from message structure, not by judging message content with a model. Running an LLM inside the trusted daemon would add cost and a prompt-injection surface to the component that must stay simplest. Candidate signals:

- A high rate of messages within one conversation among a small, unchanging participant set, with no other participants posting.
- Long chains of explicit replies (`reply_to_id` pointing at the previous message) alternating between the same two participants.
- Short bodies repeated at a steady cadence, which catches acknowledgment ping-pong. This uses length and timing, not meaning.
- Request cycles: A's request to B leads to B's request to A, detected through request links once [structured requests](messaging-requests.md) exist.
- Causal depth beyond a threshold (see below).

Thresholds are **unknown** and need tuning against real runs. False positives are expected at first, which is part of why a trip pauses and escalates instead of blocking permanently.

**What a trip does.** When a breaker trips for a conversation:

1. Agentd stops waking the involved participants for deliveries from that conversation. Messages are still accepted, and deliveries remain pending and readable by pull.
2. Agentd posts an agentd notice into the conversation, using the notice kind from the [envelope design](messaging-envelope.md), saying that wakes for this conversation are paused pending operator review.
3. The operator gets an attention item showing the conversation, the triggering signal, and recent messages, with actions to resume, keep paused, or pause the participants more broadly through [operator oversight](operator-oversight.md).

A tripped breaker affects one conversation's wakes, not the participants' other work, and not their ability to read or send.

## Causal depth

When an injecting adapter knows which message started the current turn, the presence design already records that as trigger evidence. That evidence can also label the messages the turn produces: a message sent during a turn triggered by message M gets `caused_by = M` and `causal_depth = depth(M) + 1`. Messages from the operator, bots, or turns with no known trigger start at depth zero.

Agentd derives these fields from adapter evidence, never from a client-supplied value, so an agent can't reset its own depth. When trigger evidence is unavailable, for example with pull delivery or an sbx workload without an injecting adapter, the depth is **unknown**, not zero, and the depth limit doesn't apply. The limit then protects only the adapter paths that can supply evidence, which is a known gap.

A depth limit works like a hop limit in network protocols: past some depth, wakes from further messages in the chain require the operator's release. The threshold is **unknown**. A limit that's too low would break legitimate multi-step delegation chains, so the experiment should measure typical depths first.

## Softer backpressure for anxious senders

Anxious re-pinging isn't malicious, and rejecting it would make it worse. Instead, when a sender DMs or mentions a recipient that already holds several undelivered or unanswered messages from the same sender, the send succeeds and the result includes an advisory:

- how many earlier messages from this sender are still pending or unanswered,
- the recipient's current presence summary, such as "busy in a turn since 14:02,"
- a suggestion to wait with `message wait` instead of sending again.

This pairs with the proposal to embed presence in status and wait results. The advisory is information, not enforcement. If a sender keeps going, the ordinary rate limits apply.

## Resume storms after sleep

When the laptop wakes, three things happen at once: pending deliveries become deliverable, presence signals expire together, and waits and leases may observe a large clock jump. Proposed handling:

- **Coalesce per workload.** Send at most one wake per workload for its entire backlog, with small random jitter across workloads so they don't all start turns in the same second.
- **Use monotonic time for leases, expiry, and budgets.** Wall-clock jumps across sleep must not count as elapsed budget windows or expire everything spuriously. Where wall-clock time is shown to users, keep it separate from the timers that drive behavior.
- **Don't treat mass presence expiry as mass departure.** Expired signals become unknown, as the presence design already specifies. Nothing should react to unknown by waking or retrying.

## Schema and interface implications

These are candidate additions for the other pages, listed here so the pieces stay connected:

- **Rate-limit state** in memory, keyed by participant and bucket. It doesn't need to survive restart, since a restart resetting buckets is harmless at this scale.
- **Wake-budget counters** per workload and per group, in memory, with the operator view reading them live.
- **Breaker state** per conversation: tripped or not, trigger signal, trip time, and who resumed it. This one should be durable, because a restart shouldn't silently un-pause a loop the operator hasn't reviewed.
- **Message fields** `caused_by` and `causal_depth`, set by agentd from adapter evidence, nullable when unknown.
- **Event log kinds** for rate-limit rejections, deferred wakes, breaker trips and resumes, and budget exhaustion. These feed both the operator view and the experiment metrics.
- **Error codes** `rate_limited` (existing candidate), plus a send-result advisory structure for soft backpressure.
- **Agentd notice** as a message kind for breaker announcements, rendered by the envelope design.

## Open questions

- Initial thresholds for every limit, budget, and detector. All are unknown until the experiment produces data.
- Whether a tripped breaker should also defer wakes for the involved participants in other conversations, or stay scoped to one conversation.
- Whether workloads can hold permission to resume breakers in their own group, such as a coordinator, or whether resume is operator-only.
- How wake budgets interact with presence-based scheduling, for example whether a budget-deferred wake waits for idle activity.
- Whether ambient posts need a separate history-size or rate limit per channel beyond the per-participant bucket.
- Token-based budgets and their accounting source, deferred until per-response accounting is reliable.

## Codex review and combined wake policy

**Peer review and canonical policy proposal, 2026-09-27:** Keep the combined urgency, suppression, budget, and coalescing policy here; [delivery](messaging-delivery.md#wake-timing-and-urgency) owns harness mechanisms and timing. This is a proposed ownership reconciliation, not a selected product policy. All thresholds, window sizes, urgency allowances, and delegation remain open.

Proposed evaluation order: require a currently authorized delivery obligation and qualified adapter; honor hold/nonpublication, pause/freeze/quiet, tripped breakers, and harness permission waits; apply recipient and applicable Group budgets; then apply harness-specific normal/urgent timing and coalescing. A capability to steer is not permission to steer. Urgency may use a specifically permitted recipient-budget exception and a bounded Group urgent reserve; it cannot bypass hard suppression or turn ambient history into inbox delivery. Unbounded urgent exemptions would recreate the storm. Charge one coalesced wake attempt once per recipient and each applicable policy scope, not once per included message. Cross-Group/ownerless-DM budget composition remains open alongside multi-scope permissions; do not charge an arbitrary invented owning Group. Bot polling/webhook rate limits are separate from workload model-wake budgets.

Recommend quiet as the default breaker response: published messages and pending deliveries remain readable by pull. Hold is an optional operator escalation, not implicit breaker behavior. Publish at most one ambient notice per trip generation with no delivery rows or wakes, including in a DM; generate operator attention separately with coalescing. Breaker state is durable. Resume must recheck policy and budgets and stagger backlog wakes, not emit one wake per old message. Native inputs already submitted or of unknown outcome may still run; “stops waking” describes future agentd dispatch, not retroactive control of a harness queue.

**Evidence qualification:** R2 E14 at the pinned revision supports deduplicated per-response accounting and the warning about inherited fork totals and repeated/compaction usage snapshots. It did not establish billing or prove every compaction sample is unbillable. Count agentd wake attempts exactly within a defined counter lifetime; separately track native acceptance, unknown submission outcomes, observed new turns, and usage. Coalescing, busy-turn injection, natural pull, and duplicate native submissions break a one-wake/one-turn equation. The opening “most likely failure” is a motivating hypothesis, not a measured ranking of failures.

**Causal-depth counterproposal:** The earlier sentence assigning zero to missing triggers conflicts with the following unknown rule. Recommend null when evidence is missing, including pull/non-injecting profiles and bot/operator sends without known independent origin. Zero requires evidence of an independent root. A known parent whose depth is unknown does not become a known-depth child. Multiple triggers need a defined aggregation rule; until qualified, preserve unknown rather than pick one. Native turn membership is scheduling correlation, not proof that all sends semantically answer its triggering message. Treat depth as a partial detector and report its coverage; ordinary rate/budget controls remain necessary. Chronological reply/request links can reveal repeated dependencies but cannot by themselves establish semantic deadlock.

**Restart and sleep counterproposal:** In-memory bucket/counter resets are an enforcement gap, not proven harmless. Record counter generation/reset and measure restart bursts; conservative startup allowances or durable accounting are alternatives if the gap matters. Monotonic clocks differ in whether suspend time counts. Specify elapsed-time semantics for each timer and qualify platform behavior; do not extend SVID expiry or real deadlines by treating sleep as nonexistent. On wake, recheck credentials and current policy, invalidate stale presence, and coalesce backlog. Unknown presence must not itself trigger a wake. At a natural turn boundary, authenticated pull may drain messages without a wake; an injected reminder still passes the budgets, so “next boundary” is not an unlimited exemption.

Proposed tests: legitimate rapid collaboration causing false trips; urgent floods; concurrent rate admissions; rejected/duplicate sends and accounting; native-submit uncertainty; sleep/restart storms; quiet conversation mixed with eligible messages in one batch; operator-alert recursion; and unknown causal evidence across pull and content-push profiles. The [schema](messaging-schema.md#requests-controls-and-publication) integrates durable state and events; the single [retention decision](messaging-schema.md#retention-and-redaction-open-decision) covers audit/control history. None of these tests has run.

## Provenance

The operator asked on 2026-09-27 for design of loop, storm, and budget controls before a multi-model review of the wiki. Claude identified the failure modes and wrote the controls on this page as proposals. The anxious re-ping behavior comes from the operator's earlier PoC observations reported in the same discussion. The usage-accounting caution cites the Codex session-management research at the pinned PoC revision. No control here was implemented or tested.

Codex reviewed this page on 2026-09-27 against the pinned imports and the integrated participant/conversation model. The labeled review adds counterproposals, evidence limits, failure cases, and links to schema/interface owners; it preserves Claude's original proposals for multi-model review. No new operator decision, implementation, or experiment is claimed.
