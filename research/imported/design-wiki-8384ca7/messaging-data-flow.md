---
title: Messaging data flow
summary: "Proposed messaging acceptance, request transitions, held release, budgeted wakes, SSE reconciliation, and recovery cases."
type: design
status: draft
tags:
  - area/messaging
  - area/orchestration
  - scope/destination
updated: 2026-09-27
---

**Decided direction — operator discussion on 2026-09-27, recorded in Claude's conversation-model handoff:** One agentd per host owns messaging; Groups are logical authority and policy scopes, not isolation boundaries or conversation spaces. The experiment starts with DMs whose participants receive everything, ambient channels whose mentions enter inboxes, and threads within either. The purpose is to compare how agents work with inbox-style and ambient coordination. Detailed mechanics below are **proposed**, not accepted interfaces or implementation.

“Channel” is a provisional product name; **Claude MCP channels** means the unrelated harness transport. Open names are room, topic, space, or keeping channel with a qualified harness term. No file or route is renamed merely to settle that naming question.

The [schema](messaging-schema.md) owns proposed relationships; [API](messaging-api.md) and [commands](messaging-commands.md) expose them. Authenticated participants call agentd; only agentd touches SQLite or any future broker. Host and sbx use their existing [authentication paths](spiffe-mtls-authentication.md).

## 1. Send

Choose a DM participant selector set or existing DM, a channel (including a Group's default channel), or a message-rooted reply. Supply a stable client message key and exact body, structured mentions if applicable, and explicit reply intent. A body containing an @-name is just text; it does not acquire mention authority. Proposed urgency is intent subject to policy, not a permission to wake arbitrary workloads.

## 2. Authenticate and authorize

Validate the SVID, derive sender participant and kind from its registered SPIFFE path, then check workload incarnation, bot registration/credential generation, or the separately designed operator binding. Evaluate applicable permission grants and containment, plus membership/history policy; workload installation unification remains open. For a DM, validate sender-side and every recipient's applicable policy; the DM has no owning Group. For a channel, validate owner policy for posting, mentions, explicit/role membership, and foreign role scope. Thread replies additionally require authorized root visibility. Authorization to read a conversation does not grant authority to control its participants or see their runtime metadata.

Before acceptance, require the appropriate inbound bridge permission for asserted external authorship; reject unauthorized metadata rather than stripping it. Store the bot as authenticated sender and the external author as an opaque claim. A bridge verifies external-service authentication locally; agentd does not authenticate the claimed external author. Bot-provided content, including CI output, remains untrusted. Outbound relay checks a separate egress grant again before dispatch.

## 3. Resolve and commit

First check an existing sender/key against the normalized original request. A match returns the original result under current authority before any role, default Group/channel, or DM re-resolution. A mismatch conflicts. Lost responses remain unknown acceptance, recovered with the same request/key.

The following is the ordinary publication path; the [controls and requests flow](#controls-and-requests-acceptance-flow) below proposes private held acceptance as an exception, with publication and delivery rows delayed until release.

For a new DM send, resolve concrete participants plus sender, find/create the unique canonical set, and atomically write the message, deliveries for all other participants, and events. For a top-level channel post, commit one message and accepted structured-mention resolution. Create deliveries only for mentioned current members, excluding sender; no mentions means zero deliveries and success. Channel-wide mention requires separate policy authority and snapshots all eligible members.

For a rooted reply, validate that the root belongs to the parent and keep `reply_to_id` separate from the root reference. DM replies deliver to all other DM participants. Channel replies deliver to existing eligible implicit participants plus new mentions, with overlap deduplicated. The author becomes a participant for later replies. No historical deliveries are added for new participants. Reject invalid or inaccessible mentioned targets rather than silently omitting them.

Resolve role membership, effective admission intervals, policy, root eligibility, and recipients consistently with the write transaction or validate unchanged versions. Role changes and new matching workloads update effective admission before dependent operations; first channel read does not establish the join point. Send retries do not repeat participation or membership changes. Presence never silently filters the recipient set.

The response means durable acceptance, including a resolved conversation/root and intended recipient set (delivery rows exist only after publication), not model visibility or task completion. Earlier-review proposals would also sample authorized current recipient lifecycle, marking sampling time and redaction; duplicate acceptance stays fixed while diagnostics may change. Suspended/terminated admission remains an open policy.

## 4. Notify after commit

DM deliveries, structured mentions, and channel-thread participant deliveries enter the existing inbox dispatcher. Ambient channel posts update history/unread state without waking a workload. A UI or authorized SSE listener may receive a non-waking state-change hint, but an adapter must not convert every ambient event into model input.

Register interest before checking durable state, or use an equivalent generation/recheck protocol to avoid lost wakeups. On restart/reconnect, reconcile pending delivery rows and authorized unread summaries. SSE remains a proposed hint transport with bounded refresh; durable replay needs event retention, filtering, and gap semantics. Message-list keysets and read cursors are not SSE event offsets.

Urgency and wake coalescing remain proposals: normal Claude input waits for a qualified idle boundary, with bounded batching while idle; busy/unknown can delay it longer. Urgent Claude input may join a busy turn under policy. Codex stays queued unless a separate steering mode is authorized. Ambient urgency alone never creates deliveries or wakes. [Harness timing](messaging-delivery.md#wake-timing-and-urgency) covers races, permission holds, and cost.

## 5. Deliver and record acceptance

The [per-harness alternatives](messaging-delivery.md#per-harness-delivery-tradeoffs) remain open: Codex hints, qualified Claude hooks, and conditional Claude MCP channel content. Native acceptance of a hint never changes message receipts. Notification attempt maps may be transient with bounded duplicates after restart; content submission reserves ownership and persists attempt evidence before external effects. Unknown content outcomes cannot be released to competing push/pull merely by lease expiry.

Receive still compares A (leased attempts plus model ack) and B (atomic fetch-and-record). Under A, a lost response can recover after expiry, but forgotten ack can repeat model input. Under B, commit-before-response can mark unseen content delivered; list/show/history retain content without guaranteeing rediscovery. Neither proves understanding. Programmatic adapters require separately qualified acceptance/seen evidence.

Proposed count and aggregate output-byte budgets include envelopes, provenance, escaping, and wrapper headroom. Values remain unmeasured. Never intentionally split a message while recording delivery; an oversized next item requires an explicit error and an adequate retrieval path. Under B, later tool truncation or output loss remains a separate handoff gap.

For A/programmatic receipts, atomically validate attempt, recipient, current authority, and kind-specific binding before setting the first delivery timestamp/mechanism and workload incarnation or bot generation. Duplicate reports do not overwrite the first receipt. Reconcile old uncertain attempts without assigning their evidence to a successor.

**Proposed bot path:** Select a qualified webhook, pull, or acknowledged stream mechanism, not a harness adapter. The bot's installation and current registration constrain what may be delivered or subscribed to. A webhook success or explicit message acknowledgment records bot delivery; writing SSE bytes does not. Lost responses retain duplicate/unknown-outcome risk. Revocation stops new dispatch and closes streams; in-flight external effects require reconciliation. Support order and protocols remain open. Operator delivery is a separate unqualified profile.

## 6. Record visibility and replies

For workload recipients, set `seen_at` only from qualified evidence of a particular message in model input. A cursor advance, generic turn boundary, HTTP write, or successful hint is insufficient. Pull profiles may never have trusted seen evidence. Correlated Claude MCP channel input may qualify; a prompt hook by itself needs admission validation.

An explicit accepted reply records its relationship and may update the original delivery's first `replied_at` for this replying recipient. Ambient readers without an original delivery do not create one retroactively. Private `message reply` targets the original sender's DM; `thread reply` uses the parent audience. Neither silently claims every pending message in the thread was answered. Sender status and waits reconcile durable evidence, not receipt notifications alone.

## Channel catch-up flow

An explicit or effective role join records an admission boundary. Authorized list/catch-up reads return bounded visible posts/replies, in ascending sequence through a fixed high-water mark when advancing unread state. Fetching/listing is recommended to leave the cursor unchanged. The caller then explicitly advances through its completed range; repeated or lower boundaries do not regress it. A lost fetch response can be fetched again; a lost advance response is retried by value. Advancing does not acknowledge inbox mentions or prove model attention.

Receive and a dedicated summary surface may return unread count, explicit-mention count, and latest authorized sequence per channel. These counts are filtered by effective membership intervals/current policy and are independent of pending deliveries. Include summary bytes in the receive budget and expose pagination/partial summaries rather than silently dropping channels. Channel listing that also advances is an open alternative with response-loss risk.

## Thread lifecycle flow

Recommend deriving a thread from its root message on first reply. DM audience is inherited; channel participation follows root authorship, accepted replies, and accepted mentions. No separate thread add/leave/close is needed in this recommended experiment. Keeping those controls or adding follow/unfollow remains an alternative if measurements justify it.

The earlier immediate-add/optional-brief flow moves to explicit channel membership: atomically set membership, write its transition, and optionally post a brief mentioning the new member. The brief is channel-visible, not private. Repeated no-op adds create no new membership event; a new brief key creates a new message. Membership-only attention hints versus CLI warnings remain open and must not turn role admissions into uncontrolled wakes. Removing an explicit source does not remove a matching role-derived grant.

## Presence flow

Participants are the targets, with kind-specific capability evidence: bots report reachability and separate registration status; operators need a future profile. The following lifecycle/activity flow applies to workloads. A recipient's visible capabilities can explain pull-only delivery or missing activity evidence without changing permissions.

**Proposed review revision:** Read authoritative lifecycle from workload records and keep observed reachability/activity in memory. Trusted adapters report incarnation-bound observations with freshness; a known turn-start event supplies `started_at`, which remains distinct from heartbeat receipt time. Declared availability is deferred rather than requiring agents to refresh it. Clear observations on daemon restart and fence replacements/suspension; late reports cannot revive an obsolete execution.

**Proposed from Claude's second review:** Source reachability primarily from qualified backend adapters, with authenticated contact supplementary. Process/sandbox existence is runtime evidence, not sufficient proof of a reachable delivery path. Keep the signal unknown when only existence is known; resolve conflicting observations and expose their sources. [Expected backend evidence](messaging-schema.md#expected-backend-evidence) varies by profile; sbx without a harness adapter need not report activity. The in-memory map needs no daemon-generation field or persisted-observation invalidation: restart empties it. Rebind trusted adapters and retain incarnation fencing before accepting new reports.

An adapter may associate a turn with specific triggering messages only when its input evidence supports that relation. An inbox-available hint and a later multi-message receive do not establish a single cause or ongoing focus. Message status and wait responses embed current authorized recipient observations and a deterministic summary, so a reply timeout may report busy-since, suspended, or activity-unknown without a second command. Preserve missing/redacted fields and do not infer attention or task completion.

Observation updates, expiry, and lifecycle transitions wake presence/status waiters. Recheck state and authority after registering interest; expiry must be visible even without new traffic. Receipt conditions remain receipt conditions: a presence change can refresh the explanation without making `replied` true. Streams and bounded polls are notification transports, not message acknowledgments.

For sbx, holding a request for 30 seconds and streaming unbuffered SSE are both unqualified. Proposed additions to the transport spikes should measure buffering, idle/total timeout, proxy reconnect, credential expiry, and fencing of long-held requests. Use immediate bounded reads with backoff if that is the only qualified profile; a network failure remains an error or unknown write outcome, not a synthetic empty result.

Presence proposals remain open. An optional channel view would still require independent visibility. Presence remains advisory and does not remove busy/unknown members from the recipient snapshot. Authoritative lifecycle and Group policy govern admission separately. Historical debug state, if recorded later, cannot restore liveness.

## Controls and requests acceptance flow

**Codex integration proposal from Claude's four pre-review pages:** The following refines sections 2–4 if [controls](messaging-loops-and-budgets.md), [holds](operator-oversight.md), and [requests](messaging-requests.md) are adopted. Authenticate and authorize before revealing either controls or a prior acceptance. Then look up the sender/key: return an authorized identical committed result before applying new-send controls or resolving mutable selectors again. Otherwise a later mute could obscure a successful send whose response was lost. A changed request still conflicts.

For a new send, check mute, conversation pause, and Group/host freeze; validate addressing and resolve its proposed snapshot to price fan-out; apply rate limits; decide whether policy holds the send; then validate request eligibility, claim, and outcome. Recheck authoritative policy/control state at the commit boundary. Rate admission needs serialization with acceptance so concurrent sends cannot overspend; failed validation must not consume a successful-send charge. A rejected rate check stores no message/key acceptance, though a bounded rejection audit event may be stored. A held acceptance consumes admission once; release is not another send charge.

Without a hold, commit message, publication sequence, deliveries, request transition, and corresponding durable events together. With a hold, commit only the private held record and intended audience, with no public sequence, deliveries, thread participation, or request claim/outcome effect. Validate those transitions again on release; holding an outcome does not reserve a claim. Release atomically publishes at a fresh sequence and creates delivery rows under the [schema release rules](messaging-schema.md#requests-controls-and-publication). Discard reports the operator disposition to sender status. Neither action implies cancellation or completion of external work.

After commit, use the [combined wake policy](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy). Quiet/breaker state suppresses automatic wakes while leaving published inbox/history readable. Budget exhaustion defers eligible wakes and coalesces pending work; it does not mark delivery, seen, or replied. A natural authenticated pull can consume pending rows under receive A/B without spending a wake. A breaker trip persists before subsequent dispatches, records its signal, optionally publishes one ambient notice per trip generation, and creates separate operator attention. Already submitted or uncertain native inputs may still execute; controls cannot promise retraction.

Request replies carry an explicit request ID and optional claim/outcome. The transaction checks original candidate eligibility and current access, resolves claim competition, inserts the reply, and changes only the authorized request state. A failed claim rejects the entire reply send; plain progress replies do not close or reopen the request. Cancellation races outcomes by commit order and does not stop a running tool/Task. Authorized retries recover the same result before checking current terminal state.

### Additional recovery cases

| Case | Proposed result or qualification |
| --- | --- |
| Crash after held acceptance or release, before response | Same key returns held/released disposition; no duplicate publication or delivery rows. |
| Role/member/grant changes while held | Release revalidation fails explicitly; no new audience or silent partial release. |
| Reader advances channel cursor while a message is held | Release receives a new public sequence and is discoverable on catch-up. |
| Two claims, or claim/outcome versus cancellation | One atomic winner; losing send has no reply message or partial request mutation. |
| Hold on a request outcome, followed by another resolution | Release revalidates and remains held on conflict; acceptance did not reserve a transition. |
| Crash after breaker trip; restart/sleep with backlog | Durable quiet remains; counters reset with explicit accounting uncertainty; stagger reconciled wake attempts. |
| Budget expires without any new send or SSE connection | Scheduler reconciles durable pending rows; no dependence on receiving another notification. |
| Quiet/pause/redaction races an adapter submission | Fence future dispatch; surface uncertain/already submitted input instead of claiming it was withdrawn. |
| Oversight read while member receives the same message | Separate audit only; no operator membership, delivery receipt, seen state, or channel cursor mutation. |
| Redaction followed by same-key retry or event replay | No body copy leaks; fingerprint/retention contract governs retry recovery. |

These are proposed tests, not completed checks. SSE remains an optional authorized change-hint transport followed by state reconciliation; neither SSE receipt nor reconnect generates harness wakes or overrides budgets.

## Recovery cases to validate

Also test wrong-kind SPIFFE paths, bot registration revocation during a stream/webhook, bridge claims without an inbound grant, outbound relay without egress permission, origin-marker echo suppression, and host-wide grants without channel membership under the recommended ambient profile. A bot retry after credential rotation must retain its participant/message key without acquiring a new audience.

| Case | Expected result or open limitation |
| --- | --- |
| Same send key after role/default-channel change | Original conversation, mentions, and recipient set returned; no re-expansion. |
| Concurrent first sends to the same participant set | One DM identity, distinct messages for distinct keys. |
| Ambient post with no mentions | Accepted with no deliveries, receipt aggregate, or adapter wake. |
| Role join races channel post | Coherent admission boundary and send-time mention snapshot. |
| Mention overlaps thread participation | One delivery row and one scheduling input per recipient. |
| New member mentioned in an inaccessible old thread | Reject under the recommended root-visibility rule; no history leak. |
| Explicit remove while role still matches | Effective membership remains; response explains the remaining source. |
| Catch-up pagination, truncation, or lost output | No implicit cursor advance past omitted content; no fake seen evidence. |
| Forgotten ack / lost B receive response | Preserve the documented alternative-specific duplicate/loss risks. |
| Crash after native content submission | Durable uncertain attempt blocks blind competing delivery. |
| Replay or retention gap | Explicit reset/reconciliation; do not claim complete event coverage. |
| Presence/credential expiry on a long-held request | Recheck authority; no synthetic successful timeout on transport failure. |

## Provenance and open decisions

The operator's 2026-09-27 discussion, handed off by Claude, decided one agentd per host, Groups as policy scopes, the DM/channel/thread starting set, and the comparative experiment. Claude proposed participant-set DM identity, ambient channel cursors, structured mentions, dynamic role membership, message-rooted threads, and the route/command direction. Codex's recommendations on immutable DM sets, explicit cursor advancement, reply audience, admission history, retries, and experiment instrumentation are synthesis, not further operator decisions.

Claude's earlier API/commands, threads/presence, and delivery reviews remain proposal sources where this model does not supersede them. The earlier operator-agreed immediate-add/idempotent-membership/optional-brief pattern is carried into proposed explicit channel membership; its former standalone-thread placement is replaced only as a recommendation. No implementation, migration, harness experiment, or PoC scope transfer was performed.

Still open: explicit ack versus receive-records-delivery; presence fields and integration into status/waits; unmet-wait exit code; Group inference; keyset pagination; JSON/text default; aggregate byte limits; per-harness content versus hints; hooks versus Claude MCP channels for Claude wakeup; urgency policy; and the product name. The text keeps review recommendations visible without deciding these choices. See [experiment design](messaging-experiments.md).

The participant/authority revision follows the operator's 2026-09-27 discussion handed off by Claude: bots, both SPIFFE mechanisms, installation scope, bridge-as-bot permissions, and the capability/permission distinction are decided. Participant kinds, storage, grants, custody, lifecycle, and delivery mechanics remain Claude proposals with labeled Codex synthesis in [Participants and permissions](participants-and-permissions.md). Bot enrollment/issuer, initial delivery mechanisms, ambient membership, workload installation unification, and federation scope remain open alongside the earlier messaging choices.

The 2026-09-27 pre-review integration carries Claude's loop/budget, oversight, request, and envelope proposals into this page with labeled Codex synthesis. All new mechanics remain proposed. Operator message authority, request inclusion in the first experiment, every control threshold, and earlier messaging/participant open decisions remain unresolved; see the four source pages linked from [the index](README.md). No implementation or new harness probe was performed.
