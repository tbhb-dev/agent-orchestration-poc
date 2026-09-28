---
title: Messaging API
summary: "Proposed participant messaging and request routes, receive alternatives, backpressure, and operator-management boundaries."
type: design
status: draft
tags:
  - area/messaging
  - scope/destination
updated: 2026-09-27
---

**Decided direction — operator discussion on 2026-09-27, recorded in Claude's conversation-model handoff:** One agentd per host owns messaging; Groups are logical authority and policy scopes, not isolation boundaries or conversation spaces. The experiment starts with DMs whose participants receive everything, ambient channels whose mentions enter inboxes, and threads within either. The purpose is to compare how agents work with inbox-style and ambient coordination. Detailed mechanics below are **proposed**, not accepted interfaces or implementation.

“Channel” is a provisional product name; **Claude MCP channels** means the unrelated harness transport. Open names are room, topic, space, or keeping channel with a qualified harness term. No file or route is renamed merely to settle that naming question.

**Codex interface synthesis from Claude's proposed mechanics:** Route names below are sketches, not implementation or accepted names. The generic conversation routes avoid settling the provisional channel name. They replace standalone thread management in this recommended model.

## Shared contract

Requests authenticate through the [shared identity path](spiffe-mtls-authentication.md). Agentd derives participant and kind from the validated SVID path and checks the kind-specific authority binding; there are no impersonation flags or arbitrary recipient-inbox selectors. Requests/responses use JSON and UTC timestamps. CLI text versus JSON default is independently open. Current authorization applies to history, status, receipts, and retries; a DM crosses Groups only when each relevant policy permits it.

Bots use the same application routes under their own principal, through either decided SPIFFE mechanism. `agentw` remains the workload client, not a required bot wrapper. Registration, installation grants, endpoint configuration, and revocation belong to `agentctl` or an authorized operator management surface, not these application routes. Operator messaging is a proposed participant use; management permission is separate.

The [participant authority model](participants-and-permissions.md) governs grant/containment/membership checks. Workload-role unification under installations remains optional. A participant selector is an address, never a sender-kind claim. Presence and optional capability discovery use participant IDs and visibility-filtered kind-specific results; a pull-only recipient should be identifiable without claiming automatic wake.

## Candidate routes

| Method and route | Proposed meaning |
| --- | --- |
| `POST /v1/messages` | DM send, channel post, or rooted reply; one send-idempotency namespace. |
| `GET /v1/conversations?kind=dm|channel` | Authorized DM/channel discovery. |
| `GET /v1/conversations/{id}` | Kind, audience/membership, metadata, and authority scope. |
| `GET /v1/conversations/{id}/messages` | Authorized history; no cursor or receipt mutation. |
| `GET /v1/messages/{root_id}/replies` | Rooted conversation replies visible to caller. |
| `GET /v1/messages/{id}` | Authorized message inspection; no receipt. |
| `GET /v1/messages?view=inbox|sent` | Original delivery or sender records; not all ambient history. |
| `POST /v1/conversations` | Create a channel under Group policy with a client creation key. |
| `PUT/DELETE /v1/conversations/{id}/members/{participant_id}` | Explicit channel membership only, optional brief on add. |
| `PUT/DELETE /v1/conversations/{id}/roles/{group_id}/{role_id}` | Idempotent channel role rule, subject to owner policy. |
| `PUT /v1/conversations/{id}/read-cursor` | Monotonic caller read boundary; channel only. |
| `GET /v1/inbox/summary` | Authorized per-channel unread/mention summaries. |
| `POST /v1/inbox/receive` | Pending delivery rows with A/B contract still open; optional unread summary. |
| `POST /v1/inbox/ack` | Option A only: acknowledge owned attempt. |
| `GET /v1/messages/{id}/status` | Delivery evidence and explicit replies; bounded condition waits. |

## Send and retry

Example DM find-or-create request:

```json
{
  "client_message_id": "review-001",
  "destination": {"kind": "dm", "participants": [
    {"kind": "participant", "id": "worker-2"},
    {"kind": "role", "group_id": "group-c", "id": "merger"}
  ]},
  "thread_root_id": null,
  "reply_to_id": null,
  "expects_reply": true,
  "reply_by": null,
  "body": "Ready for review."
}
```

The sender is included automatically. Existing DM sends use `destination: {kind: dm, conversation_id: ...}` instead of participant selectors, never both. Resolve roles once for a new message and use the unique participant-set DM. Every other participant receives the message; no subset destination within an existing DM. Proposed self-only/empty-peer sends return `422 no_recipients`.

Example channel post:

```json
{
  "client_message_id": "merge-post-001",
  "destination": {"kind": "channel", "conversation_id": "channel-merges"},
  "mentions": [{"kind": "role", "group_id": "group-c", "id": "merger"}],
  "body": "Worktree A is ready to merge."
}
```

`mentions: []` is a valid ambient post with no deliveries or wakes. Mention kinds are participant, Group-qualified role, and channel-wide (`{kind: channel}`); the last requires broadcast authority. Body text never resolves mentions. A default-channel convenience selector `{kind: group_default_channel, group_id: ...}` resolves to an ambient channel post; adding a structured channel-wide mention makes it a wake-capable broadcast. Reject mentions on DMs initially, since their entire audience already receives every message.

A rooted reply uses the parent DM/channel destination, a top-level `thread_root_id`, and explicit `reply_to_id` (root or a reply under it). Validate parent/root and visibility together. A private reply uses a DM addressed only to the original sender, `reply_to_id` referencing the original, and null root; the original may belong to another conversation. Cross-conversation references require read and send authority and never grant original-message access to new recipients. Only original delivery recipients can produce a per-recipient `replied_at`; other authorized replies remain relationship evidence.

Return `201` for new acceptance, with message ID, conversation ID, optional root ID, client key, accepted timestamp, and `duplicate: false`. An authorized identical retry returns `200` with the original fields and `duplicate: true`. A changed same-key request returns `409 idempotency_conflict`. Admission of a channel post is successful even with zero deliveries. A matching retry never re-resolves participants, mentions, defaults, or roots.

Normalize documented omissions (`thread_root_id`, `reply_to_id`, `reply_by` to null; mentions to empty; expects-reply to false) before comparison. Compare selector sets in a documented canonical order, preserve exact body text, and reject unknown fields. Retry a find-or-create send with the original selectors/absent conversation and root, never substitute returned IDs. Incarnation is derived, not part of caller intent. Canonicalization, retention, and exact error envelopes still need implementation decisions.

**Earlier review proposals remain open:** Infer an omitted selector Group only when the authenticated workload has exactly one eligible Group; otherwise require it. Keep omission and resolved scope separately so retries do not reroute. No single owning Group is fabricated for a cross-Group DM. Candidate urgency normal/urgent participates in canonical comparison and Group authorization, without creating an ambient delivery or steering permission. Authorized recipient lifecycle diagnostics may accompany acceptance with sample time and redaction/partial metadata; retries may return newer diagnostics for the original recipient set. These are not immutable acceptance facts.

**Proposed relay fields:** `asserted_external_author` is opaque bridge-supplied metadata accepted only under an inbound asserted-authorship grant. Store/render it separately from authenticated `sender_participant_id`. Agentd derives `originating_bridge_participant_id` for a new inbound relay; a namespaced `external_message_id` supports bridge correlation, not sender authentication. Include supplied relay intent in canonical retry comparison. Reject unauthorized fields. Outbound relay requires a separate resource/destination egress grant even if the bot can read the message. Exact field encoding and multi-hop preservation remain open.

## Inspection and history

DM participants see their fixed-set history under current policy. Channel readers see messages within authorized join intervals; root replies inherit that visibility. Recommend requiring root visibility to enter an older channel thread, rather than implicitly revealing hidden history to a newly mentioned member. History reads never create deliveries, acquire attempts, advance a cursor, or set seen. Receipt and runtime-metadata visibility require independent authority.

The earlier keyset proposal remains open: descending history uses `seq < last_seen_seq`; ascending catch-up uses `seq > after_seq` through a fixed returned high-water mark. Return bounded items and query-bound opaque page cursors. Current policy is reapplied on each page; no frozen membership or server-held result snapshot is promised. No time-based expiry does not mean permanent validity across retention/database changes. Conversation list ordering is a separate specification task.

## Channel reads and membership

The summary contains per-channel `unread_count`, `mention_count`, and `latest_seq`, with pagination and explicit unavailable/partial fields. Count accessible non-self posts/replies above the read boundary; mention count uses accepted mention evidence, not every participant-thread delivery. Pending inbox delivery count is separate. Receive may include this summary within its shared output budget; an unread ambient summary alone must not generate a native wake or complete a wait for a new inbox delivery.

Recommend a side-effect-free catch-up fetch followed by explicit `PUT read-cursor` with `through_seq`. Advance monotonically within an authorized completed range and not beyond the channel high-water mark. Return changed/current boundary; repeated/lower values are no-ops. Listing that also advances remains an alternative with lost-output risk. An explicit cursor claim records caller intent, not proof the model saw the returned bytes. Do not advance through omitted/truncated pages or turn the cursor into a seen receipt.

Channel creation uses a caller-scoped `client_conversation_id` and immutable canonical creation request; identical retries return the original, changed retries conflict. Default-channel provisioning must also converge on one mapping per Group. Creation/join/post/mention/management authority is Group-policy governed, never merely creator privilege.

Explicit add/remove and role-rule changes are idempotent by value. Adding an explicit member returns effective membership and its sources; deleting that source can leave a role-derived membership active. Concurrent opposing changes resolve by commit order with events for actual transitions. No operation key is needed for pure set changes. An optional brief has its own pre-reported `client_message_id` and follows ordinary send retries; write the brief as a channel-visible post mentioning the newcomer atomically with add. Invalid/oversized/conflicting brief aborts the whole mutation. An old brief retry must not reactivate a subsequently removed member. A no-op add plus a new brief key accepts a new brief. Membership-only notifications remain open, not implicit message receipts.

No standalone `POST /v1/threads`, thread member mutation, or thread close route is proposed in this recommended profile. Threads derive from messages; retaining extra controls remains an explicit alternative. Mutable-DM membership is also an alternative, not an endpoint silently added here. Metadata edit/version behavior can be specified when an actual edit surface is needed.

## Receive alternatives

This A/B comparison is for model-facing workload consumers. Bots need programmatic receipt semantics: a successful qualified webhook response or explicit pull/stream message acknowledgment. Candidate existing receive/ack operations may be reused under a bot binding, but that does not choose A for models. Initial bot protocols remain open. SSE hints are not acknowledgments; bot seen evidence is not applicable. Operator consumption requires a separately designed profile.

```json
{
  "limit": 10,
  "max_bytes": 8192,
  "wait_seconds": 30
}
```

**Open choice, not an operator decision:** Claude's review recommends fetch-and-record for model consumers while retaining programmatic adapter receipts. The original explicit-ack proposal remains an alternative. The detailed token flow below describes option A only; option B would change both the response and the meaning of delivery.

| Concern | A: leased receive plus explicit ack | B: model-facing fetch-and-record |
| --- | --- | --- |
| Model action | Receive, retain token, then ack. | One receive call; no token or lease. |
| When `delivered_at` changes | Authorized ack of the acquired attempt. | Atomic selection and update when agentd prepares the receive result. |
| Lost response | Lease expiry can offer the message again. | Selected rows are already delivered; ordinary pending receive will not offer them again. |
| Model forgets or compacts | A forgotten token/ack can cause duplicate input and action. | No forgotten-ack redelivery, but lost or overlooked content requires history inspection. |
| Evidence | Consumer reports input acceptance; this does not prove complete model input or understanding. | Agentd recorded a handoff attempt, not confirmed client receipt. |
| Ownership | Claims coordinate programmatic/push/pull paths; retain retry evidence. | One SQLite transaction prevents two receives selecting the same pending rows; reconcile any external adapter attempt first. |

**Codex qualification of option B:** A database transaction cannot atomically commit an HTTP response reaching the CLI. Commit-before-response can suppress a message the model never received; response-before-commit risks repeats. List/show/thread reads retain recoverable content but do not themselves guarantee discovery after a lost response. If chosen, record `delivered_via=receive` and document the weaker handoff meaning; a request-result replay mechanism would be additional storage/design, not something this sketch already provides. Option A also cannot prove that the model read an untruncated tool result. Compare these failure modes rather than claiming either option proves attention.

Programmatic full-content push adapters may still need leased attempts and explicit internal receipts under either option. Durable adapter attempts and wake attempts remain distinct from model-held tokens. No option permits automatic fallback to pull while the outcome of an external content injection is unresolved.

### Common receive limits

The example `max_bytes` value above is illustrative, not a qualified harness limit. Bound both item count and the total serialized response budget, including metadata, token fields where applicable, JSON escaping, and envelope overhead. The CLI also bounds rendered output, including delimiters/provenance in text mode. Derive published defaults and maxima from the smallest supported tool-output budget with headroom; these limits have not been measured.

Never split or silently truncate a message body while marking it delivered. Select only complete envelopes that fit. If even the next envelope cannot fit the effective budget, return an explicit size/budget error without marking that item delivered or acquiring it; require an adequate bounded retrieval path. Limit maximum stored body size too, so a permanently unreceivable head item cannot stall the inbox. Test aggregate output, Unicode, escaping, and wrapper overhead, not just individual message bodies.

### Option A: leased receive and explicit ack

`POST /v1/inbox/receive` targets only the authenticated participant under its qualified consumer profile. Agentd selects pending messages through the same dispatcher that coordinates push adapters. The response contains `items`, each with a message, an opaque `delivery_token`, and `lease_expires_at`. An empty response after the wait budget is a normal `200 OK`, not a delivery failure. Agentd clamps item count, total bytes, and wait duration to published limits; their values remain open.

**Proposed coordination mechanism:** Each token identifies a leased attempt bound to message, recipient participant, kind-specific authority binding, and delivery mechanism. While that attempt owns the row, competing receive calls and push dispatchers cannot acquire it. Expiry makes an unacknowledged delivery eligible for another attempt; it cannot undo external input that already occurred. Long polls must recheck authorization before returning content and use the data-flow page's registration/recheck protocol to avoid lost wakeups.

The client explicitly acknowledges one item:

```json
{
  "message_id": "message-001",
  "delivery_token": "opaque-attempt-token"
}
```

An accepted acknowledgment records delivery via `receive` and returns `200 OK` with the recorded receipt and `duplicate: false`. Repeating the same successfully acknowledged attempt returns that receipt with `duplicate: true`, while the caller remains authorized. An expired unacknowledged or superseded attempt returns `409 stale_delivery`; a fenced workload incarnation or revoked bot binding cannot use its former authority. Agentd must atomically validate attempt ownership when updating delivery evidence.

A receive response lost in transit leaves a leased attempt that can expire and be retried. The initial sketch does not make receive requests idempotent; repeating one can acquire other unclaimed rows. Clients should bound retries, acknowledge what they actually receive, and recover pending work after expiry. Short leases limit delay but increase duplicate risk; duration and renewal are open.

The token is not an independent workload credential and cannot bypass authentication. Ack records input acceptance, not that a model understood the message. No general participant route sets `seen_at`; trusted adapter evidence must correlate a message and model input. Push receipts likewise enter agentd through an internal service or separately scoped integration interface, not a caller-controlled mechanism override.

## Status and waiting

Only delivery recipients have per-recipient receipts: all DM peers, explicit channel mentions, and eligible channel-thread participants. Ambient-only posts return an empty receipt set and explicit reply relationships. Codex recommends `422 no_delivery_recipients` for recipient waits on an empty set, avoiding a vacuous `all` success. A channel cursor is never seen evidence. For bot recipients, seen is not applicable; reject a seen-wait aggregate containing such recipients as an unsupported condition rather than silently excluding them or waiting forever. Operator receipt conditions remain unqualified.

`GET /v1/messages/{id}/status` returns authorized per-recipient evidence and explicit reply message references. It does not collapse delivery, seen, and replied into one linear state: a qualifying reply can exist without an observed seen event. A recipient may inspect its own receipt; a sender's aggregate view requires authority over the corresponding recipient set.

**Proposed from Claude's review:** Embed each recipient's current lifecycle and authorized presence in every status and wait result, including a timed-out reply wait. Include a deterministic one-line summary plus raw evidence, so callers need not separately query each participant. Presence visibility is checked independently: permission to view a receipt does not automatically grant runtime metadata or another message's trigger ID. Use an explicit unavailable/redacted value where needed. Presence is sampled current state, not a historical receipt and not necessarily from one transaction with the durable receipts.

Optional query parameters `wait_for=delivered|seen|replied`, `recipient_scope=any|all`, and `wait_seconds` support bounded waiting. Both condition and recipient scope are required when waiting. Evaluate against the original recipient snapshot, not today's membership. A condition requiring an aggregate the caller may not inspect is rejected rather than evaluated against a misleading filtered subset.

Return the current authorized evidence plus `condition_met` and `timed_out`. A wait timeout is a normal response and does not cancel the message, withdraw the reply request, or prove delivery failed. `seen` may never become observable for an adapter; reply deadlines do not schedule enforcement. State changes wake waiters as hints, and waiters reconcile from SQLite after reconnect or timeout. Wake status waiters on relevant presence/lifecycle changes as well as receipt changes, while keeping `condition_met` tied to the requested receipt condition. This initially provides current-state convergence, not replay of every transition.

## Presence

Presence targets and selectors now use participant IDs. Workload lifecycle/activity and incarnation-pinned waits below are workload-specific. Bots expose reachability, with registration status separate, and use revocation/generation checks; `idle` and `seen` are not applicable to bots and should return an explicit unsupported-condition result rather than wait forever. Operator presence/attention semantics remain open. Optional capability metadata reports evidence/version and allowed visibility, not self-declared abilities.

**Proposed revision from Claude's review:** Start with authoritative workload lifecycle plus observed reachability and activity. Defer declared availability and `PUT /v1/presence/self` rather than relying on models to refresh it. The concern about model behavior is a review judgment, not tested evidence. Observation freshness is kept in memory; persisted debug/audit history, if later added, cannot restore live presence after restart.

| Method and route | Meaning |
| --- | --- |
| `GET /v1/presence?group_id=...` | List authorized lifecycle and observed presence with summaries. |
| `GET /v1/participants/{id}/presence` | Inspect one authorized participant's kind-appropriate observations. |

Lifecycle comes directly from agentd's workload records, using their defined states (for example running, suspended, or terminated) and transition time/reconciliation status. Do not invent suspended state from an expired heartbeat. Running is control-plane lifecycle state, not proof of current reachability or model activity.

**Proposed from Claude's second review:** Prefer fresh qualified backend-adapter observations for reachability, with authenticated contact supplementary. A running process/sandbox alone proves neither a responsive harness nor a working delivery path. Return the scope of the evidence and unknown where no path is qualified; source conflicts require reconciliation. The [backend evidence matrix](messaging-schema.md#expected-backend-evidence) is inference pending adapter validation.

Reachability and activity each carry effective value, source, `observed_at`, `expires_at`, and `stale`. Busy activity additionally carries optional `started_at`, native turn identity, and `trigger_message_ids` backed by specific adapter evidence. `started_at` is the observed turn start, not the latest heartbeat; keep it null if unknown. On expiry retain any permitted historical detail as stale but present the effective activity as unknown. Restart clears live observations; do not imply retained last-contact history when none exists.

**Correlation limit:** An adapter may report which application message or messages were supplied as triggering input, but a native turn ID alone cannot establish that link. Notification-first push usually identifies only a wake attempt; later receive can return several messages during unrelated work. Leave `trigger_message_ids` empty/unknown unless qualified evidence connects them. Even a known trigger does not prove the model remains focused on that message. Filter trigger IDs against message visibility and never reveal hidden workload activity through the summary.

A summary can say "busy since 14:02; turn began with your message", "suspended", or "activity unknown; last observed contact 20 minutes ago" when the corresponding evidence permits it. Avoid "working on your message" as an unqualified assertion. Construct summaries from authorized structured fields, not model-authored speculation; raw fields remain available for scripts.

A single-workload read may include `wait_for=reachable|idle` and `wait_seconds` for a bounded condition wait. Return `condition_met` and `timed_out` using the message-status convention. Idle requires fresh reachable and idle signals for the same active incarnation. Require `expected_incarnation`, obtained from an initial presence read; return `409 incarnation_changed` if it differs or is replaced, and `409 target_inactive` if no active incarnation can be bound. Wake on expiry, lifecycle changes, and observations; reauthorize before returning. Group presence lists are best-effort current views, not frozen simultaneous snapshots.

A channel-scoped presence filter is optional and independently authorized; membership alone does not reveal runtime state. Presence neither sets message receipts nor removes busy/unreachable members from durable recipient sets. Historical replay, heartbeat cadence, source precedence, and exact lifecycle vocabulary remain open. The earlier declaration API remains a deferred alternative, not part of this proposed first surface.

## Waiting transports and SSE

**Proposed from the operator's SSE discussion:** Persistent clients/adapters may use an authenticated SSE stream of inbox-available and state-change hints; finite CLI commands may use bounded long-polling. Both use the same application reads and chosen receive contract. A stream notification never acquires a message or sets a receipt, and an SSE connection alone does not wake an idle model: the harness adapter still supplies that step.

Start with hints plus reconciliation on initial connection, reconnect, and bounded refresh. The registration/recheck protocol must avoid lost wakeups. A later replay profile could use `Last-Event-ID` and the proposed event log, but needs authorized filtering, retention/gap handling, and cursor-reset semantics first. Message-list `seq` cursors cannot replay receipts, and the generalized `messaging_events` proposal covers durable message/thread changes, while live presence observations are not replayed from it. Keep event route/filter names open rather than pretending this is a complete streaming API.

Streams and long polls remain bound to participant and current kind-specific authority (workload incarnation or bot registration/generation) and current policy; recheck authorization and close fenced connections. Define credential refresh/reconnect behavior explicitly. **Unqualified sbx assumption from Claude's review:** The `wait_seconds: 30` examples do not establish that Docker's credential proxy supports that hold time or unbuffered SSE. Measure idle/total timeouts, buffering, disconnects, credential expiry, and reconnect behavior as proposed additions to [BV-05 transport qualification](backend-validation-spikes.md#bv-05-sbx-kit-routing-and-server-trust) and [BV-06 refresh/failure qualification](backend-validation-spikes.md#bv-06-sbx-token-mediation-refresh-and-destination-scope) before choosing limits. Short immediate polls with backoff are the compatible fallback candidate; a disconnected request is not automatically a successful empty timeout.

## Errors and retry guidance

Use a stable error envelope such as `{"error":{"code":"idempotency_conflict","message":"The key was already used with different content.","retryable":false}}`. Error text is for explanation; clients branch on codes. A transport failure can leave a write outcome unknown regardless of an error's retry guidance.

| HTTP status | Candidate codes | Client behavior |
| --- | --- | --- |
| `400` | `invalid_request`, `invalid_cursor` | Correct the request or restart pagination. |
| `401` | `unauthenticated` | Restore the configured authentication path; do not substitute a sender ID. |
| `403` | `forbidden`, `incarnation_inactive`, `registration_revoked` | Stop this operation; current authority is insufficient. |
| `404` | `not_found` | Resource absent or concealed by visibility policy. |
| `409` | `idempotency_conflict`, `stale_delivery`, `incarnation_changed`, `target_inactive` | Reconcile the relevant send, attempt, conversation/root scope, or target incarnation; do not silently change intent. |
| `413` | `message_too_large` | Reduce the body to the published limit. |
| `422` | `no_recipients`, `invalid_reply`, `recipient_not_member`, `no_delivery_recipients`, `unsupported_condition`, `group_required` | Correct destination, thread membership, or reply relationship. |
| `429`, `503` | `rate_limited`, `unavailable` | Respect retry guidance; preserve keys on send retries. |

## Requests, backpressure, and management separation

**Codex integration proposal from [structured requests](messaging-requests.md):** Ordinary sends default to `kind: message`; request creation uses `POST /v1/messages` with `kind: request` and a `request` object containing `assignment` and optional `deadline`. `reply_by` and `deadline` normalize to one value; conflicting values are invalid. `notice` is internal-only. Callers cannot supply `caused_by`, `causal_depth`, or authenticated sender fields.

| Method and route | Proposed meaning |
| --- | --- |
| `GET /v1/requests` | Authorized requests filtered by sender, candidate, assignee, state, or conversation; bounded pagination. |
| `GET /v1/requests/{message_id}` | Request state and authorized per-recipient outcomes; presence remains independent. |
| `POST /v1/requests/{message_id}/claim` | Explicit claim with a stable `client_operation_id`; original eligible candidates only. |
| `POST /v1/requests/{message_id}/cancel` | Sender cancellation with a stable `client_operation_id`; terminal transitions serialized. |

Request replies use `POST /v1/messages` with `reply_to_id`, `request_id`, optional `claim: true`, optional `outcome: completed|declined|failed`, and authorized `fulfilled_by` references. `request_id` must identify the request being answered; it is not permission to choose another recipient's outcome. Destination/root must still be explicit: private sender-DM reply and parent-audience thread reply remain distinct. Store outcome reference visibility separately; ambient request readers must not gain access to a private reply's body. No claim/outcome is inferred from prose. Reply insertion and transition are atomic. For `any`, an eligible outcome can claim and resolve atomically; a non-assignee cannot resolve another assignee's work. See the [request counterproposal](messaging-requests.md#codex-review) for individual declines before assignment.

Claim/cancel operation keys are scoped to authenticated actor, with operation kind in canonical comparison, compared against the normalized request, and recovered before reevaluating current state. Changed same-key input conflicts. Reply mutations use the existing send key. Exact route naming, request-list pagination, and whether requests enter the first experiment remain open.

Extend acceptance results with `publication_state: held|published|discarded` and nullable `published_at`; distinguish acceptance from publication and delivery. A retry retains original acceptance facts but may expose newer disposition/status as separately labeled current state. Held bodies are available only to sender inspection and authorized oversight, never ordinary conversation history or receive. Add an optional `advisory` containing authorized pending/unanswered counts, independently permission-filtered presence with sample time, and a suggestion to wait. This is soft backpressure, not a failed send or a new immutable acceptance fact. A delivered recipient may still have an unanswered request.

| HTTP status | Candidate code | Guidance |
| --- | --- | --- |
| `403` | `participant_muted`, `conversation_paused`, `messaging_frozen` | Explicit admission policy block; retry only after control changes. Freeze exemptions remain an oversight policy proposal. |
| `409` | `request_already_claimed`, `request_closed` | Reconcile request state; no reply was accepted by a failed atomic transition. |
| `403` | `not_request_recipient` | Ambient visibility alone grants no claim/outcome eligibility. |
| `429` | `rate_limited` | Return permitted bucket detail and `retry_after_seconds`; preserve send key for retry. |

Expose oversight reads, hold release/discard, redaction, mute/pause/freeze, and breaker management through a separate [operator management surface](operator-oversight.md), not workload messaging routes. Delegation requires explicit scoped permissions and an independently designed management contract. Possessing a capability, conversation membership, or operator-authored text grants none of these actions.

HTTP payloads stay JSON. Model-facing CLI text envelopes versus JSON remain an independent unresolved default; [envelope review](messaging-envelope.md#codex-review) reconciles Claude's text recommendation with earlier alternatives. Preview/truncation responses must be explicitly incomplete and non-consuming. SSE continues to carry authorized hints with reconciliation; request/control events do not imply an accepted durable replay contract or access to operator-only audit.

## Storage implications and open decisions

Conversation identity/membership, channel admission intervals and cursors, accepted mention resolution, message roots, and transition evidence extend the two-table message/delivery starting point. Receive option A needs durable ownership/ack retry evidence; B still has a lost-output gap. Full-content attempts need durable uncertainty recovery while hints may remain transient. Experiment telemetry must expose gaps without being mistaken for application receipts.

## Provenance and open decisions

The operator's 2026-09-27 discussion, handed off by Claude, decided one agentd per host, Groups as policy scopes, the DM/channel/thread starting set, and the comparative experiment. Claude proposed participant-set DM identity, ambient channel cursors, structured mentions, dynamic role membership, message-rooted threads, and the route/command direction. Codex's recommendations on immutable DM sets, explicit cursor advancement, reply audience, admission history, retries, and experiment instrumentation are synthesis, not further operator decisions.

Claude's earlier API/commands, threads/presence, and delivery reviews remain proposal sources where this model does not supersede them. The earlier operator-agreed immediate-add/idempotent-membership/optional-brief pattern is carried into proposed explicit channel membership; its former standalone-thread placement is replaced only as a recommendation. No implementation, migration, harness experiment, or PoC scope transfer was performed.

Still open: explicit ack versus receive-records-delivery; presence fields and integration into status/waits; unmet-wait exit code; Group inference; keyset pagination; JSON/text default; aggregate byte limits; per-harness content versus hints; hooks versus Claude MCP channels for Claude wakeup; urgency policy; and the product name. The text keeps review recommendations visible without deciding these choices. See [experiment design](messaging-experiments.md).

The participant/authority revision follows the operator's 2026-09-27 discussion handed off by Claude: bots, both SPIFFE mechanisms, installation scope, bridge-as-bot permissions, and the capability/permission distinction are decided. Participant kinds, storage, grants, custody, lifecycle, and delivery mechanics remain Claude proposals with labeled Codex synthesis in [Participants and permissions](participants-and-permissions.md). Bot enrollment/issuer, initial delivery mechanisms, ambient membership, workload installation unification, and federation scope remain open alongside the earlier messaging choices.

The 2026-09-27 pre-review integration carries Claude's loop/budget, oversight, request, and envelope proposals into this page with labeled Codex synthesis. All new mechanics remain proposed. Operator message authority, request inclusion in the first experiment, every control threshold, and earlier messaging/participant open decisions remain unresolved; see the four source pages linked from [the index](README.md). No implementation or new harness probe was performed.
