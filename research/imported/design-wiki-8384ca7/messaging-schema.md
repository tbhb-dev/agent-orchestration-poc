---
title: Messaging schema
summary: "Proposed participant messaging persistence, request state, held publication, control events, receipts, and shared retention questions."
type: design
status: draft
tags:
  - area/messaging
  - scope/destination
updated: 2026-09-27
---

**Decided direction — operator discussion on 2026-09-27, recorded in Claude's conversation-model handoff:** One agentd per host owns messaging; Groups are logical authority and policy scopes, not isolation boundaries or conversation spaces. The experiment starts with DMs whose participants receive everything, ambient channels whose mentions enter inboxes, and threads within either. The purpose is to compare how agents work with inbox-style and ambient coordination. Detailed mechanics below are **proposed**, not accepted interfaces or implementation.

“Channel” is a provisional product name; **Claude MCP channels** means the unrelated harness transport. Open names are room, topic, space, or keeping channel with a qualified harness term. No file or route is renamed merely to settle that naming question.

Read [data flow](messaging-data-flow.md), [API](messaging-api.md), and [commands](messaging-commands.md) for behavior. [SPIFFE authentication](spiffe-mtls-authentication.md) supplies participant identity; [Group peering](group-peering.md) defines authority across Groups.

## Ownership and scope

Agentd alone accesses SQLite or a future NATS/JetStream broker. Start with SQLite and after-commit in-process hints. DMs, mentions, and channel-thread participant delivery use fan-out on write; ambient channel history uses fan-out on read. One authoritative copy of a message serves both views. The first experiment is on one host; cross-Group policy is proposed here, while cross-daemon transport remains future work.

**Existing durability proposal, still open:** WAL with `synchronous=FULL` is the candidate acceptance contract. SQLite documents that NORMAL in WAL can lose recent commits on power loss; FULL adds synchronization. Cost and target-platform guarantees remain unmeasured. [SQLite synchronous pragma](https://www.sqlite.org/pragma.html#pragma_synchronous). Inbox identity is the logical participant; only a currently authorized kind-specific binding consumes it. Resume neither creates a new inbox nor legitimizes stale credentials.

## Participants and authorization

[Participants and permissions](participants-and-permissions.md) is canonical for the proposed workload/bot/operator kinds, SPIFFE namespaces, installations, membership, and containment. All message/conversation references use participant IDs. Role selectors still select trusted assigned roles; generalizing IDs does not assign workload roles to bots/operators. Channel owning-Group checks remain; cross-Group DMs have no owning Group and require the explicit multi-scope policy composition described there.

Recommend participant base records with per-kind detail records rather than a nullable all-kinds lifecycle row. Message/receipt snapshots retain constrained nullable workload incarnation or bot registration/credential generation fields; operator session-binding provenance is an open detail. These are kind-specific evidence, not caller-set identity. Keep authenticated participant stable through authorized rotation; bot registration revocation stops activity and streams even if memberships remain stored.

Bridge assertions and origin markers join canonical request comparison where caller-supplied. Agentd derives a new originating-bridge marker from the authenticated bot under an inbound relay grant; opaque asserted authors never replace sender identity. Unauthorized asserted-author metadata is rejected. Outbound relay needs separate egress permission. See [bridge provenance](participants-and-permissions.md#bridge-permissions-and-provenance).

## Logical schema

This is a relationship sketch, not DDL. Types, constraints, migrations, deletion, and retention remain open. Proposed tables are:

```text
conversations (
  id, kind                 -- dm | channel
  owning_group_id          -- channel only; null for DM
  dm_participant_set_key   -- DM only; unique canonical set
  channel_name, metadata
  created_by_participant_id, client_conversation_id, creation_request
  created_at
)
conversation_members (
  conversation_id, participant_id, membership_kind  -- fixed DM | explicit channel
  state, joined_after_seq, updated_at
  PRIMARY KEY (conversation_id, participant_id)
)
channel_membership_rules (
  channel_id, selector_group_id, role_id         -- idempotent selector identity
)
channel_membership_intervals (
  channel_id, participant_id, joined_after_seq, left_at_seq
  -- proposed evidence of effective explicit/role admission; union of sources
)
channel_read_cursors (
  channel_id, participant_id, last_read_seq
  PRIMARY KEY (channel_id, participant_id)
)
messages (
  id, seq                   -- external ID plus publication order; null seq while held
  conversation_id
  thread_root_id            -- null for top-level; points to root message
  sender_participant_id
  sender_incarnation                        -- workload only
  sender_bot_generation                     -- bot only
  client_message_id, canonical_request
  addressed_to              -- original structured selectors/target
  mentions                  -- structured participant, scoped role, or channel-wide selectors
  reply_to_id, expects_reply, reply_by, body, created_at
  asserted_external_author                 -- permissioned bridge claim, opaque
  originating_bridge_participant_id, external_message_id
  urgency                   -- candidate normal | urgent; still open
  UNIQUE (sender_participant_id, client_message_id)
)
deliveries (
  message_id, recipient_participant_id, queued_at
  delivered_at, delivered_via
  delivered_incarnation                           -- workload only
  delivered_bot_generation                         -- bot only
  seen_at, replied_at
  PRIMARY KEY (message_id, recipient_participant_id)
)
INDEX deliveries_pending (recipient_participant_id, delivered_at, message_id)
```

Group authority is reached through channel ownership or the DM participants' applicable policy scopes; a DM has no invented owning Group. Retain acceptance-time policy/resolution evidence for audit without treating it as permanent authorization. Conditional constraints separate DM keys from channel ownership. The DM key uses stable participant IDs, never workload incarnations or bot credential generations; use unambiguous sorted serialization and verify set equality if a hash is used. Concurrent find-or-create and first-send acceptance share a transaction and uniqueness constraint.

**Existing ordering proposal, not newly decided:** Assign integer `seq` within agentd's single SQLite writer, separate from clock-derived external IDs. An AUTOINCREMENT-backed sequence is a candidate for non-reuse; concrete DDL still needs validation. [SQLite AUTOINCREMENT](https://www.sqlite.org/autoinc.html). Message-list keysets may use `seq < last_seen_seq` for descending history; catch-up uses ascending order above a cursor through a fixed high-water mark. Apply current authorization on every page. Keysets need no stored result snapshot or time expiry but do not promise perpetual validity across retention, database replacement, or format changes. Message publication order, event-log order, channel read cursor, and delivery state are distinct. The hold integration below refines the original acceptance-order proposal: held acceptance allocates no public sequence.

## Requests, controls, and publication

**Codex integration proposal, 2026-09-27:** This extends the sketch above from Claude's [requests](messaging-requests.md), [loop controls](messaging-loops-and-budgets.md), [oversight](operator-oversight.md), and [envelope](messaging-envelope.md) proposals. None of these additions is decided or DDL. Ordinary messages retain the existing behavior; the following publication distinction is needed if holds are adopted.

```text
messages additions (
  kind                       -- message | request | notice
  publication_state          -- held | published | discarded
  published_at               -- null until released/published
  caused_by, causal_depth     -- trusted trigger evidence; null when unknown
  redacted_at, redacted_by_participant_id
  notice_template_id         -- internal notices only
)
message_holds (
  message_id, reason, intended_recipient_snapshot, policy_evidence
  held_at, released_at, discarded_at, acted_by_participant_id
)
requests (
  message_id PRIMARY KEY, assignment, status, assignee_participant_id
  deadline, outcome_message_id, fulfilled_by, updated_at
)
request_recipients (
  request_message_id, recipient_participant_id, status, outcome_message_id
  PRIMARY KEY (request_message_id, recipient_participant_id)
)
request_operations (
  actor_participant_id, client_operation_id, canonical_request_digest, result
  PRIMARY KEY (actor_participant_id, client_operation_id)
  -- claim/cancel retries; operation kind participates in canonical comparison
)
conversation_breakers (
  conversation_id PRIMARY KEY, state, trigger_signal, tripped_at
  resumed_at, resumed_by_participant_id, generation
)
messaging_interventions (
  id, kind, scope_kind, scope_id, state, actor_participant_id, updated_at
)
```

**Publication-order counterproposal:** `created_at` remains acceptance time; `seq` is allocated only when published, with `published_at`, in the same transaction as delivery rows. A held or discarded message has no public sequence. This qualifies the earlier acceptance-order sketch: ordinary acceptance and publication coincide, but a later release must appear above an already-advanced channel cursor. Private sender status and oversight can inspect holds; inbox, history, thread participation, unread summaries, SSE content, and bridge exports cannot reveal held bodies. Allocating a sequence at hold acceptance without a separate release cursor would lose later releases from catch-up.

Recommend freezing intended recipients at acceptance, then rechecking policy, membership, root visibility, and request transitions on release. Release does not re-expand roles or add newly eligible participants. If that snapshot is no longer admissible, keep the item held with a reason for operator disposition rather than silently shrinking or expanding its audience. Resolving recipients only at release is an alternative requiring an explicit operator choice. Hold release publishes once, creates deliveries once, and activates any request record/transition atomically. Discard retains a sender-visible disposition without publishing. Repeated release/discard operations return their committed result; mutually exclusive dispositions conflict. Persist active oversight controls so restart cannot undo them.

Whether bots may create/claim requests remains an open per-kind permission-policy choice from the requests page; generic participant IDs do not settle it.

Request candidate eligibility is a fixed snapshot of the request's declared recipients, not every ambient reader. Reject a request with no eligible candidates in this initial proposal; an open-call channel request is a separate undesigned alternative. `any` stores one winning assignee; `each` stores independent recipient states. Keep per-recipient decline evidence for `any` too: an unclaimed candidate declining should not disqualify other candidates. Plain replies preserve current status. Claim, outcome, reply-message insertion, and event insertion share one transaction. Completion records the participant's reported outcome, not proof that external work succeeded. Keep `deadline` and existing `reply_by` as one canonical value for requests, rejecting conflicting inputs rather than running two timers. `fulfilled_by` links are independently authorized and do not grant access to the linked Task.

`caused_by` and `causal_depth` are agentd-derived scheduling provenance, never writable identity or semantic proof of causation. Unknown pull/non-injecting evidence stays null; known parent with unknown depth also yields unknown depth. A known independent root may be zero; bot/operator kind alone does not establish independence. Multiple triggering inputs require an explicit aggregation rule before a scalar depth can be enforced. See [causal review](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy).

Notices are a restricted internal producer, not a fourth participant kind or a client impersonation option. Recommend nullable sender only for `kind=notice` with an internal template ID and producer provenance; participant sends require an authenticated sender and cannot select this kind. An inbox hint is an adapter control payload, not a new message. A persisted breaker notice is ambient, including in a DM: it creates no delivery rows, reply expectation, or native wake. This is a proposed explicit exception to DM fan-out, preventing breaker recursion. Operator attention travels through a separate authorized event/view.

Rate buckets and recipient/Group wake counters deliberately remain in memory; durable breaker/control state and delivery obligations survive restart. Their reset weakens enforcement and must be measured, not described as harmless. The [combined wake policy](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy) owns urgency precedence and accounting scope; adapter mechanisms remain on the delivery page.

Extend the existing event-log proposal with `rate_limit_rejected`, `wake_deferred`, `breaker_tripped`, `breaker_resumed`, `budget_exhausted`, `request_claimed`, `request_resolved`, `request_cancelled`, `request_fulfillment_linked`, `oversight_read`, `intervention_changed`, `message_held`, `message_released`, `message_discarded`, and `message_redacted`. Persist state-changing events with their state transaction. Rejections and counter exhaustion need bounded/coalesced audit recording so a flood cannot flood the log; exact rejected-attempt counts and crash persistence of in-memory samples remain qualification questions. Events carry IDs, actor, scope, reason, and timestamps, not body copies. Oversight events are management-visible, not automatically conversation-visible or workload SSE events. Replay and retention remain open.

## Retention and redaction open decision

**Central open item:** Define retention together for published and held/discarded bodies, redaction tombstones, closed requests and recipient outcomes, audit/control events, idempotency keys/fingerprints, exports, backups, and native delivery-attempt payloads. No duration, secure-erasure guarantee, or permanent retry horizon is selected. Preserve necessary references without retaining unwanted body copies; expiration must explicitly bound retry and history guarantees rather than treating an old key as safely new without a contract.

Redaction retains ID, sender, conversation position, and reply/root references but removes the body from authorized views and controlled derived stores. `canonical_request` currently duplicates body bytes: redact that copy too. Recommend a protected canonical-request digest plus original routing evidence for retry comparison after body removal; digest construction and retention require review. Do not return old plaintext on retries or replay. Race redaction against queued payloads and adapter dispatch: stop controllable pending content, retain a tombstone, and report any already submitted or unknown exposure. Receipts are a lower bound on exposure, not a complete recipient list. External transcripts/exports already obtained cannot be retracted. [Oversight review](operator-oversight.md#codex-review) distinguishes logical removal from secure erasure.

## Message identity and immutable acceptance

Derive sender participant, kind, and current kind-specific binding from authenticated identity and authoritative registration state. Store the original canonical request and resolved conversation, mentions, recipients, and acceptance time. The same sender/key and same normalized request returns the original acceptance; changed content conflicts. Compare destination selectors, body, parent/root, explicit reply, mentions, urgency if enabled, and reply intent. If requests are adopted, canonical comparison also includes message kind, assignment/deadline, request ID, claim/outcome, and fulfillment references; an identical body with a different lifecycle mutation is not an identical retry. Preserve body bytes. Look up a retry before resolving roles, default Groups, DM sets, or a default channel again. Current authorization is still required to return the original result.

A retry of a find-or-create DM repeats its original selectors and absent conversation/root fields, not the returned conversation ID. It never re-expands roles, creates a second DM, changes thread participation, or appends recipients. New logical messages may resolve a changed role to a different participant-set DM. Workload incarnation changes or bot credential rotation do not change the logical participant/send key; current registration and grants still apply. Retention of idempotency evidence remains open.

## DMs and participant sets

**Claude proposal; Codex recommends for the experiment:** Resolve participant/role selectors to a deduplicated set, include the authenticated sender, then find or create one DM for that exact set. A scoped role resolving to multiple participants forms a multi-participant DM. Every message and DM-thread reply is readable by and delivered to that fixed set, subject to current policy; exclude the sender from inbox delivery because it already owns the sent message. A one-participant self-DM is an open extension; recommend rejecting it initially as `no_recipients`.

For cross-Group DMs, each recipient's applicable authority policy must permit this sender to message that recipient; sender-side policy also applies. Every participant must be allowed to receive the whole body and see the participant identities. Reject the whole send on an unauthorized participant rather than silently shrinking the set. Multiple policy memberships and their composition need specification. Same host does not imply cross-Group authority, and DM identity needs no owning Group.

| Participant change alternative | Consequence | Recommendation |
| --- | --- | --- |
| New DM for the new set | Old DM/history remains intact; first new message supplies the brief. | Start here; stable audience makes “everyone gets everything” intelligible. |
| Idempotent add to existing DM, optional brief | Less fragmentation; audience differs across history and requires history/receipt rules. | Retain as alternative, not the active sketch. |

No implicit add occurs when replying. Removing or disabling a participant changes authorization/lifecycle, not the historical participant set; how a now-unsendable DM is archived is open. Repeated same-set messages reuse the DM, replacing the earlier new-thread-per-send proposal without choosing a general mutable-DM design.

## Channels and membership

**Claude proposal:** A channel is owned by one Group whose policy governs creation, join, post, mention, and management. Give each Group a default channel. The former Group-send meaning becomes an ambient post there; a Group-wide wake is an explicitly authorized channel-wide mention. Channel membership is separate from Group membership and can combine explicit participants with dynamic, Group-qualified role selectors, including roles in other Groups. Never equate a foreign role with a local role of the same name.

Explicit membership carries forward immediate add, idempotent set/remove, and an optional brief. Adding an already explicit member is a no-op; new brief keys still create new messages. Role selectors dynamically admit newly matching participants. **Codex synthesis:** Effective membership is the union of authorized explicit and role sources; removing an explicit source does not evict a member still admitted by a role. Report that fact. Exclusions/overrides, self-leave from role membership, and wider bans are open rather than silently invented. Rule changes and role/participant lifecycle changes must reconcile admission boundaries before concurrent sends or reads proceed.

**Join-point proposal:** Record when effective membership begins, including role-based admission, against the message sequence. A late first read must not become the join time. Preserve admission intervals to avoid granting messages from gaps after leave/rejoin; recommend resuming the cursor while skipping unauthorized gaps. Granting all earlier history or resetting on rejoin are alternatives requiring policy decisions. Reads always require current channel authority as well as an eligible history interval. Role admission is not retroactive access to all past posts.

**Codex synthesis for optional briefs:** Commit a normal channel post with a structured mention of the added participant atomically with the explicit add. It has ordinary delivery receipts and is visible to other entitled channel readers; private content belongs in a DM. Define admission-before-brief ordering so the newcomer can read its brief. This preserves atomic add/brief retry semantics without inventing a private post in an ambient channel. Membership-only adapter hints versus CLI warnings remain an open earlier-review choice; a role-admission flood must not silently become broadcast wakeups. [Group standing context](group-peering.md#group-standing-context-future-work) remains separate future work.

## Addressing and recipient snapshots

| Message kind | Delivery set at acceptance, excluding sender | Ambient/history access |
| --- | --- | --- |
| DM top-level or thread reply | All other fixed DM participants | All participants under current policy. |
| Channel top-level, no mentions | Empty, intentionally valid | Current authorized members from their join intervals. |
| Channel top-level with mentions | Deduplicated resolved mentioned members | Same ambient view; mention does not create exclusive content. |
| Channel-thread reply | Current eligible thread participants plus resolved mentions | Other entitled channel members see it ambiently. |

Mentions are structured participant, scoped-role, or channel-wide selectors; never parse the body to authorize wakes. Resolve only current channel members under mention policy. Recommend rejecting an invalid explicit target or an empty requested role mention rather than silently dropping intended recipients. The sender may render in mention metadata but receives no duplicate inbox row. An ambient post with no delivery rows succeeds; the old empty-recipient rejection applies to a DM with no peer, not to channel posting. A thread reply may also have no eligible other participant and remain a valid ambient post.

Resolve authorization, role membership, effective joins, thread participation, and recipients in one consistent transaction or validate their versions before commit. Later membership changes never backfill or delete historical deliveries. Duplicate selectors and overlap between mention and thread participation yield one row. Presence never filters recipients; suspended/terminated admission remains a separate open policy. Proposed send-time lifecycle diagnostics sample only authorized delivery recipients and do not redefine acceptance or predict a reply.

## Threads and membership

**Claude proposal; Codex recommends:** Replace standalone thread creation with `thread_root_id` pointing to a top-level message in the same DM/channel. A reply into the thread creates its derived identity on demand; a nested reply retains the original root and uses `reply_to_id` for the exact answered message. No separate thread ID/table is necessary for the initial experiment. A root is not its own reply. Root deletion/retention needs a policy, such as retaining a reference tombstone, before implementation.

DM threads inherit the fixed DM audience. Channel-thread participants are the root author, participants that posted a reply, and resolved participants mentioned in the root or replies. Record or derive participation from accepted evidence, not today's expansion of an old role mention. Eligibility still requires current channel membership and history access. On each reply, snapshot existing eligible participants plus new mentions, exclude the sender, and then retain its participation for future replies. A new participant receives no retroactive inbox entries.

**History edge, Codex recommendation:** Joining a channel after an old thread began does not automatically reveal its older root. Initially require root visibility to reply or receive participant/mention routing within that thread; reject an attempted mention that would need hidden context. Start a new top-level post with an authorized summary instead. Granting an old thread's history explicitly is an alternative for later policy design, not an accidental consequence of mentioning someone.

Recommend dropping thread-level add/leave, explicit creation, and closed state for the experiment; there is no identified case requiring them beyond what a root message and parent membership provide. Keeping controls for channel threads is an alternative if implicit participation causes too much inbox traffic. Explicit follow/unfollow is optional future work. This is a proposed replacement for the earlier thread model, not a claim those mechanics were never agreed in their original context.

## History visibility under review

The earlier `members|restricted` standalone-thread proposal is re-homed: DM participants share their fixed-set history; channels use join-point history under owner policy, with threads inheriting it. Ambient access creates no deliveries or seen receipts. Private exchanges belong in a distinct DM. Full channel backlog for newcomers versus join-point history remains a future policy alternative; current mechanics recommend join points. Current policy revocation still controls reads and cannot retract already-read text.

## Channel catch-up and read cursors

**Claude proposal:** Each effective member has a channel cursor and an unread summary (`unread_count`, `mention_count`, `latest_seq`) in receive output and a dedicated read surface. Codex recommends counting accessible posts/replies above that cursor, excluding the member's own posts; mention count is the subset explicitly mentioned at acceptance, not all participant-thread deliveries or pending delivery count. Keep mention resolution evidence distinct from the union delivery set, for example in accepted events. The summary must not expose hidden intervals or revoked channels.

Listing/history inspection is side-effect free. An explicit read advancement moves `last_read_seq` monotonically to a caller-selected authorized boundary within a completed ascending catch-up range; it is idempotent by value and cannot exceed that channel's accepted high-water mark. Recommend separate fetch and advancement so a lost output does not silently clear unread counts. Listing-and-advancing is the cheaper alternative but risks lost-response skips; leave it open. Paging must not advance past omitted/truncated results. Cursor advancement neither acknowledges a mention delivery nor sets `seen_at`; receive/ack likewise does not advance a channel cursor. These are different records of different actions.

## Delivery evidence

**Kind-specific proposal:** Delivery rows name participant recipients, but evidence depends on kind. Workloads retain A/B receive and qualified harness evidence. Bots use a qualified webhook response or programmatic pull/stream acknowledgment and have `seen` explicitly not applicable, never inferred from success. Bot presence is reachability only, with registration state separate; operator UI receipt/attention semantics remain unspecified. Responses should distinguish not-applicable from a null workload seen observation. No receipt grants authority or proves downstream bot processing.

| Field | Proposed meaning |
| --- | --- |
| `queued_at` | Agentd created the recipient's durable delivery record. |
| `delivered_at` | Workload A: acknowledged acceptance; B: recorded handoff, not confirmed receipt. Bot: qualified webhook response or programmatic acknowledgment. Operator: open. |
| `delivered_via` | The mechanism associated with the first recorded delivery transition, interpreted under the chosen receive contract. |
| `delivered_incarnation` | Workload recipient execution only; null for other kinds. |
| `delivered_bot_generation` | Bot registration/credential generation associated with the receipt; null for other kinds. |
| `seen_at` | Workload-only evidence of message input to a model turn; bot seen is not applicable, operator semantics open. |
| `replied_at` | The first qualifying explicit reply from this recipient was accepted. |

Receipt timestamps are agentd-recorded transition times in this proposal, not claims about exact remote event times. For an applicable field, null means the corresponding evidence has not been recorded; it does not prove the real-world event never happened. A generic turn boundary, an HTTP response write, or broker-style acknowledgment alone cannot establish all these milestones. Seen does not mean understood or acted upon.

**Proposed consequence of strict seen evidence:** Only mechanisms that submit a specific message as model-turn input, such as a queued-input adapter, can set `seen_at`. Pull delivery through agentw and backends without an injecting adapter, likely including sbx initially, will generally record delivery without ever recording seen. Agent-facing status and the UI should present a null `seen_at` as "no visibility evidence for this mechanism," not as "unread," or senders will misread it as being ignored.

**Open receive decision from Claude's review:** The [API comparison](messaging-api.md#receive-alternatives) preserves both leased receive with explicit ack (A) and model-facing fetch-and-record without tokens (B). Under B, selecting complete bounded envelopes and recording delivery occur in one SQLite transaction, but transmitting the response does not. A lost response can leave a message marked delivered before the model ever receives it; list/show/history preserve content, not guaranteed rediscovery. Under A, forgotten acknowledgments and compaction can cause duplicate model input. Neither proves understanding or immunity to truncation. Keep this meaning difference explicit before choosing one contract.

Programmatic adapter receipts still need attempt ownership and reconciliation. Under B, a model-facing workload receive has no lease, but must not select rows whose external push outcome remains unresolved. Removing model tokens does not remove adapter attempts or notification wake records. Any request-result replay added to address response loss is additional storage, not part of the two-table sketch.

For option A and programmatic adapters, the first accepted delivery report sets `delivered_at`, `delivered_via`, and the appropriate workload-incarnation or bot-generation provenance together, conditional on `delivered_at IS NULL`. The report must be authorized for that recipient and bound to the delivery attempt and kind-specific authority binding. Duplicate reports cannot overwrite the first receipt. Attempt correlation and stale-report reconciliation remain open; these columns are not a complete attempt history or claim mechanism.

The single-row model requires agentd to coordinate competing push, bot webhook/stream, and receive paths. An initial per-recipient dispatcher could serialize them; persistent claims or an attempts table should be added only if the chosen concurrency and recovery contract needs them. Successful receipt updates do not eliminate the crash window between external harness acceptance and recording the receipt.

The [harness delivery proposal](messaging-delivery.md#per-harness-delivery-tradeoffs) now compares mechanisms per profile: Codex notification-first, a qualified Claude hook as the default wake candidate, and bounded Claude channel push content where launch and input-correlation checks qualify. Hint acceptance never changes application receipts; pull still follows the unresolved A/B contract. Notification attempts may stay in memory with bounded duplicate wake risk after restart; content attempts require durable ownership and unknown-outcome reconciliation. A qualified content observer can supply distinct delivery/seen evidence without model ack; a prompt-hook marker alone is insufficient until complete input admission is established.

**Proposed from Claude's delivery review:** A candidate `messages.urgency` field takes `normal|urgent` with normal as the default and participates in canonical retry comparison. It appears only as a candidate in the field sketch, not a selected requirement. Group policy authorizes urgent use; the [wake timing proposal](messaging-delivery.md#wake-timing-and-urgency) defines coalescing and per-harness behavior. Urgency does not change recipient membership, receipts, or authority to resume/steer participants.

## Replies and expectations

`reply_to_id` is explicit evidence of what is being answered; merely sharing a DM, channel, or root is not a reply receipt. A qualifying reply atomically sets the original delivery's first `replied_at` for the authenticated replying participant and retains the reply message reference. An ambient reader with no original delivery can reply, but no original delivery row is manufactured; record the reply relationship separately for conversation history and metrics.

**Codex synthesis to preserve audience intent:** `message reply` remains a private reply to the original sender through their participant-set DM; it may reference an accessible message in another conversation. `thread reply` deliberately uses the root's parent audience. Cross-conversation reply references require independent access and send authorization; they confer no access to the original body on other recipients. A multi-participant DM reply is never silently treated as private. The API and CLI make these two actions explicit.

`expects_reply` and `reply_by` are sender intent, not a timer, wake permission, or task-completion proof. Receipt waits evaluate the fixed delivery set. For an ambient post with no recipients, return no recipient receipts; recommend rejecting recipient `any|all` waits as inapplicable rather than vacuously complete. Explicit replies remain inspectable even without a per-recipient reply receipt. A separate wait for any conversation reply could be considered later.

## Proposed transition event log

Extend the proposed `messaging_events` log, written atomically with durable state changes, with references to conversation, root/message, actor participant ID with kind-specific provenance, subject participant ID, event kind, sequence, and recorded time. Candidate kinds include message accepted, mention resolved, reply accepted, delivery/seen/reply receipt, membership source/effective membership changed, and cursor advanced. No-op idempotent mutations emit no new transition. Events preserve accepted mention and participant evidence even when today's role membership differs. Body copies are unnecessary; visibility applies per event and reference.

**Codex synthesis:** Wake planned/submitted/observed/failed events are experiment telemetry, not delivery receipts. Record attempts and uncertainty rather than claiming an external submission and SQLite event can commit atomically. Notification-only delivery correctness may still use the proposed transient attempt map; a measured run needs durable telemetry or an external collector and explicit gaps. Content-push recovery still requires durable attempts. This reconciles the handoff's wake metrics with the earlier in-memory hint proposal. Presence heartbeats remain separate. Retention, authorized SSE replay, missing-event handling, and experiment coverage are open. See [metrics](messaging-experiments.md).

## Presence observations

Targets are participants. The detailed lifecycle/activity proposal below is the workload profile. Bots expose qualified reachability with registration/credential-generation binding, not workload activity or incarnation; operator presence needs its own profile. Independent visibility checks still apply. Which signals exist is a trusted capability property, not permission to read them. Bot ambient access still compares membership-plus-read permission with installation-only permission; recommend the former without selecting it.

**Proposed revision from Claude's API/commands review:** Expose authoritative workload lifecycle plus observed reachability and activity. Defer workload-declared availability and keep current observations in memory. The earlier availability signal and persistent observation-table sketch remain alternatives, not selected requirements. Model unreliability in refreshing declarations is a review judgment, not measured evidence.

| Field or signal | Candidate values | Authority and meaning |
| --- | --- | --- |
| Lifecycle | Workload-record states, such as running, suspended, terminated | Agentd's lifecycle records, including transition time and reconciliation status; not inferred from heartbeat expiry. |
| Reachability | `reachable`, `unreachable`, `unknown` | Qualified observations or authenticated contact; expiry means unknown, not confirmed shutdown. |
| Activity | `idle`, `busy`, `unknown` | Qualified harness adapter evidence; no evidence means unknown. |

**Proposed precedence from Claude's second review:** Prefer fresh, qualified backend-adapter reachability evidence for the current incarnation; authenticated contact supplements it rather than being the only source of freshness. An idle interactive Session should not become unknown solely because it made no agentd request. **Codex qualification:** A wrapper observing a live PID or a runtime observing a running sandbox proves runtime existence, not a functioning delivery path or responsive harness. Report that evidence as such; claim `reachable` only for the path an adapter actually checks. Keep contact's time/source separately visible. Conflicting fresh observations require reconciliation rather than letting a stale backend report override newer evidence; probe meaning, cadence, ordering, and precedence need qualification. Activity still requires harness events, not process existence or contact.

### Expected backend evidence

The following are **inferences for proposed adapters**, not verified capabilities or uniform guarantees. Lifecycle always comes from agentd records with reconciliation status.

| Profile | Expected reachability evidence | Expected activity and trigger evidence |
| --- | --- | --- |
| Host interactive with harness adapter | Wrapper process observations plus a qualified harness/delivery-path check | Harness events may supply idle/busy and start time; trigger IDs only for correlated message input. |
| sbx without a harness adapter | Runtime sandbox observations; delivery-path reachability needs a separate check | Activity and message triggers unknown. A running sandbox is insufficient. |
| Headless Task on either backend | Backend runtime observations plus any qualified control/input path | Structured harness events may supply activity; triggering input only if correlated. Headless execution alone guarantees neither. |

Candidate native activity/attention sources are described in [delivery activity evidence](messaging-delivery.md#activity-evidence-feeding-presence); their quality remains version/profile-specific. Busy-turn content insertion identifies an input added during work, not necessarily its initiating trigger. Preserve that distinction in summaries rather than labeling every correlated message as a turn starter.

Notification-first adapters generally know a wake attempt, not which application message caused work. Presence waits for idle cannot succeed from lifecycle/reachability alone; retain unknown activity and a normal timeout. See [delivery qualification](messaging-delivery.md) for mechanism-specific limits.

Proposed in-memory observation shape, not a SQLite table:

```text
presence_observation (
  participant_id
  workload_incarnation   -- workload only
  bot_generation         -- bot reachability only
  signal
  source
  value
  observed_at            -- latest agentd receipt time
  expires_at             -- freshness, not turn start
  started_at             -- optional evidenced activity start
  native_turn_id         -- optional correlation, not application thread ID
  trigger_message_ids    -- optional evidence-backed inputs; may be unknown
)
```

An observation is keyed by participant, kind-specific authority binding, signal, and source. Workload lifecycle/activity fields below apply only to workload participants. Lifecycle is read from existing authoritative workload records rather than duplicated in this cache. Running does not prove that the process is responsive. Report lifecycle uncertainty/reconciliation state explicitly when the controller cannot establish current runtime truth.

Preserve `started_at` for an observed busy turn while refreshing `observed_at`; a heartbeat must not make a 40-minute turn look 40 seconds old. If the adapter missed the start, leave it null. Correlate triggering application messages only with qualified evidence: a native turn alone, same application thread, temporal proximity, or the first message subsequently received is insufficient. Multiple triggering messages may exist. Notification-first push normally supplies a wake ID, not proof that any particular application message triggered the turn.

**Codex qualification:** Known triggering input is not proof of ongoing work on that message. Use an evidence-based summary such as "busy since 14:02; turn began with your message", never an unconditional "working on your message". A summary of suspended lifecycle or stale contact is similarly derived from authorized fields. Filter message IDs and native/runtime details under the caller's visibility policy; summaries cannot leak fields omitted from raw output.

No `daemon_generation` field is needed for this in-memory map: restart empties it and signals begin unknown until re-observed. Incarnation fencing and authenticated adapter rebinding still prevent old reports from populating the new map. On expiry, effective reachability/activity becomes unknown. On suspension, replacement, or restart, fence/clear live observations. Optional debug history does not restore fresh presence. A summary may mention last contact only while such evidence actually remains available; after restart with no retained evidence, report unknown. Source precedence and delayed-report ordering still need qualification.

Message status and wait results include this current recipient view, with observation timestamps and a short summary, under independent presence visibility checks. This makes a reply timeout informative without treating busy as a receipt or an explanation known with certainty. Missing/redacted observations remain explicit. Receipt history and sampled current presence need not represent one atomic snapshot.

Presence does not filter conversation delivery recipients or authorize work. Lifecycle and Group policy may separately restrict admission. Conversation membership grants no additional runtime-metadata visibility. A channel-scoped presence view is an optional authorized filter, not a new grant. Presence changes and expiry wake relevant waiters; they initially provide current-state reconciliation rather than durable transition replay. SSE can carry change hints without persisting every heartbeat.

## Provenance and open decisions

The operator's 2026-09-27 discussion, handed off by Claude, decided one agentd per host, Groups as policy scopes, the DM/channel/thread starting set, and the comparative experiment. Claude proposed participant-set DM identity, ambient channel cursors, structured mentions, dynamic role membership, message-rooted threads, and the route/command direction. Codex's recommendations on immutable DM sets, explicit cursor advancement, reply audience, admission history, retries, and experiment instrumentation are synthesis, not further operator decisions.

Claude's earlier API/commands, threads/presence, and delivery reviews remain proposal sources where this model does not supersede them. The earlier operator-agreed immediate-add/idempotent-membership/optional-brief pattern is carried into proposed explicit channel membership; its former standalone-thread placement is replaced only as a recommendation. No implementation, migration, harness experiment, or PoC scope transfer was performed.

Still open: explicit ack versus receive-records-delivery; presence fields and integration into status/waits; unmet-wait exit code; Group inference; keyset pagination; JSON/text default; aggregate byte limits; per-harness content versus hints; hooks versus Claude MCP channels for Claude wakeup; urgency policy; and the product name. The text keeps review recommendations visible without deciding these choices. See [experiment design](messaging-experiments.md).

The participant/authority revision follows the operator's 2026-09-27 discussion handed off by Claude: bots, both SPIFFE mechanisms, installation scope, bridge-as-bot permissions, and the capability/permission distinction are decided. Participant kinds, storage, grants, custody, lifecycle, and delivery mechanics remain Claude proposals with labeled Codex synthesis in [Participants and permissions](participants-and-permissions.md). Bot enrollment/issuer, initial delivery mechanisms, ambient membership, workload installation unification, and federation scope remain open alongside the earlier messaging choices.

The 2026-09-27 pre-review integration carries Claude's loop/budget, oversight, request, and envelope proposals into this page with labeled Codex synthesis. All new mechanics remain proposed. Operator message authority, request inclusion in the first experiment, every control threshold, and earlier messaging/participant open decisions remain unresolved; see the four source pages linked from [the index](README.md). No implementation or new harness probe was performed.
