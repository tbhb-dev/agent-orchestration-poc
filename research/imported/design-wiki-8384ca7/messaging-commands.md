---
title: Messaging commands
summary: "Proposed agentw messaging and request commands, envelope output alternatives, and explicit incomplete-output handling."
type: design
status: draft
tags:
  - area/messaging
  - area/ux
  - scope/destination
updated: 2026-09-27
---

**Decided direction — operator discussion on 2026-09-27, recorded in Claude's conversation-model handoff:** One agentd per host owns messaging; Groups are logical authority and policy scopes, not isolation boundaries or conversation spaces. The experiment starts with DMs whose participants receive everything, ambient channels whose mentions enter inboxes, and threads within either. The purpose is to compare how agents work with inbox-style and ambient coordination. Detailed mechanics below are **proposed**, not accepted interfaces or implementation.

“Channel” is a provisional product name; **Claude MCP channels** means the unrelated harness transport. Open names are room, topic, space, or keeping channel with a qualified harness term. No file or route is renamed merely to settle that naming question.

**Codex command synthesis:** The namespace choices below implement Claude's proposed mechanics for review; they are not installed commands or final names. All operations use agentd and the [existing workload authentication path](spiffe-mtls-authentication.md), never direct SQLite/broker access.

## Participant scope

`agentw` remains the workload CLI, authenticated through its protected wrapper/proxy. Destinations, mentions, conversation members, and presence targets are participant IDs, so a workload can address an authorized bot or operator as well as another workload. A `participant:` selector does not let callers choose their authenticated kind. Bots use the shared API or an SDK under their own SVID; registration and installation management belong to `agentctl` or the operator surface, not `agentw`.

[Participants and permissions](participants-and-permissions.md) separates qualified abilities from grants. Visible recipient metadata should distinguish pull-only capability from missing permission. Optional delegation discovery can expose shell/tool capability evidence under policy. Authenticated bot/CI content remains peer data; asserted external authors are visibly labeled bridge claims and never substituted for authenticated sender. Bridge-only request fields are not general impersonation flags.

## Command shape

Use `agentw dm`, `agentw channel`, and `agentw thread` for conversation intent; retain `agentw message` for inbox, inspection, private reply, and status. The old generic send-to-Group/role/workload/thread selector interface is replaced in this sketch rather than given new meanings invisibly.

JSON versus text default remains open. Keep explicit `--format json|text`; compare readability, token cost, provenance, control characters, adversarial delimiters, and truncation. Neither format prevents prompt injection. Finite commands emit one result on stdout, diagnostics on stderr, and never prompt interactively.

| Command | Candidate API mapping |
| --- | --- |
| `dm send --to ...` or `dm send --conversation ID` | `POST /v1/messages` with DM intent. |
| `dm list`, `dm show ID`, `dm messages ID` | Conversation discovery, metadata, and history reads. |
| `channel post ID --mention ...` | `POST /v1/messages` with channel intent. |
| `channel list --unread` | Conversation discovery plus `GET /v1/inbox/summary`. |
| `channel read ID` | Side-effect-free ascending conversation catch-up fetch. |
| `channel read ID --through-seq N` | Explicit `PUT` caller read cursor; no fetch implied. |
| `channel create`, `channel add/remove`, `channel role-add/role-remove` | Keyed creation and idempotent membership/rule mutations. |
| `thread reply ROOT_MESSAGE_ID` | `POST /v1/messages` with root and exact reply reference. |
| `thread messages ROOT_MESSAGE_ID` | `GET /v1/messages/{root_id}/replies`. |
| `message reply MESSAGE_ID` | Private DM to original sender with explicit reply reference. |
| `message receive`, `message ack` | Existing receive alternatives; ack only under A. |
| `message list/show/status/wait`, `presence ...` | Existing inspection, receipt, and proposed presence surfaces. |

## Sending and replying

```sh
agentw dm send --to participant:worker-2 --to role:group-c:merger   --body 'Ready for review.' --client-message-id review-001
agentw channel post channel-merges --body-file ./merge-context.md   --mention role:group-c:merger --client-message-id merge-post-001
agentw channel post --group group-build --body 'Build passed.'   --client-message-id build-post-001
agentw channel post channel-merges --mention channel   --body 'Coordination needed.' --client-message-id merge-wake-001
agentw thread reply message-root --reply-to message-reply   --body 'That check passed.' --client-message-id thread-answer-001
agentw message reply message-001 --body 'Private response.'   --client-message-id private-answer-001
```

Repeatable DM `--to` selects participants and Group-qualified roles. Agentd includes the sender, resolves participants, and finds/creates the unique-set DM. Every participant receives each message; sending a different set recommends a different DM whose first message supplies context. Do not accept both `--conversation` and `--to`. Print resolved conversation ID and audience prominently; retries keep original selectors.

`channel post ID` is ambient unless it has structured mentions. `--group` selects the Group's default channel; it does not broadcast. Repeatable `--mention` accepts participant, scoped role, or `channel`; role expansion is restricted to entitled members and channel-wide wake requires policy permission. Literal @-text in the body is not a mention. Urgency alone does not make an ambient post wake anyone.

`thread reply ROOT` defaults `reply_to_id` to the root; `--reply-to` identifies a particular reply under the same root. Its audience follows the parent: every DM peer, or eligible channel-thread participants plus mentions. `message reply ID` preserves private sender-only routing via a DM, even when the original came from a multi-party conversation. Show that audience distinction rather than silently turning a private reply into reply-all. No unrelated same-thread post creates a reply receipt.

Choose exactly one of `--body`, `--body-file PATH`, or `--body-file -`; read it once and reuse identical bytes for retries. Send returns on durable acceptance; `message wait` is separate. `--expects-reply` and `--reply-by` remain intent, not scheduling/expiry. No sender/incarnation overrides.

**Still-open earlier recommendations:** Infer an omitted selector/default-channel Group only with one eligible Group, otherwise require it. Single-Group membership is not settled and a cross-Group DM has no owning Group. Candidate `--urgency normal|urgent` preserves intent across retries and is policy-gated; Codex stays queued unless separately authorized steering is selected. JSON/text default and byte limits remain open.

## Retry identity and uncertain outcomes

For every message-producing command, use `--client-message-id` or generate one once and report it on stderr before the first network attempt and in the final result. Retrying uses the same key/body/selectors/root/mentions. A find-or-create DM retry repeats absent conversation/root fields, not returned IDs. Reuse across separate invocations requires the original request. A duplicate result is success; changed intent under the same key conflicts. Killed processes can lose printed keys; this is not a durable client outbox.

A transport failure may leave acceptance unknown, not definitely unsent. Report the key and exact recoverable intent; do not generate a replacement or resend because a separate wait expired. Channel creation similarly uses `--client-conversation-id`. Optional add briefs have their own pre-reported `--brief-message-id`. Pure set/remove mutations and monotonic read-cursor advances are idempotent by value; opposite concurrent set operations are last-commit-wins, with current-state reconciliation after uncertainty.

## Inspecting without consuming

```sh
agentw message list --view inbox --delivery pending --limit 20
agentw dm messages dm-001 --limit 20
agentw channel list --unread
agentw channel read channel-merges --limit 20
agentw channel read channel-merges --through-seq 420
agentw thread messages message-root --limit 20
```

Inbox lists represent original delivery rows, not every ambient post. DM/channel/thread history is bounded and authorized. Proposed keyset pagination remains open: query-bound cursors have no snapshot TTL but may become invalid after retention/database changes, and current authorization can change results. Ascending channel catch-up returns a high-water mark and a safely processed boundary; do not use the latest channel sequence to skip unreturned pages.

Recommend that `channel read` fetch without mutation, then an explicit `--through-seq` call advance through the completed range. Keep list-and-advance as an alternative with lost-output/truncation risk. Label advancement as a caller read declaration, never seen or delivered. Channel unread/mention counts differ from pending deliveries: consuming a mention does not move the channel cursor, and moving that cursor does not ack the mention. Receive may include a bounded summary even when no inbox deliveries exist; it does not wake the agent by itself.

## Receive alternatives

**Open decision from Claude's review:** Compare the original explicit-ack command flow with a one-step model-facing receive. Neither is operator-selected. They share count/byte limits, authorization, and separate message receipts.

| Choice | Agent command flow | Main tradeoff |
| --- | --- | --- |
| A: leased receive and ack | `message receive`, then `message ack ID --delivery-token TOKEN`. | Lost responses recover by lease expiry, but forgotten acknowledgments or compaction can produce duplicate input and action. |
| B: fetch-and-record | `message receive` returns content and records delivery without a model-held token. | Removes the acknowledgment burden, but a lost response can leave unseen content marked delivered; recovery uses list/show/thread history. |

Under A, receive returns attempt tokens and lease expiries; acquiring a batch does not set `delivered_at`. An authorized ack records input acceptance and repeating the same accepted attempt is harmless. This does not prove complete model input or understanding. Expired attempts can be offered again, and the model may already have acted on them.

Under B, agentd atomically selects pending rows and records `delivered_at`/`delivered_via=receive` while preparing the response. There is no model-facing ack command or lease in that profile. **Codex qualification:** Successful HTTP/CLI output is not part of the SQLite transaction, so this means recorded handoff rather than confirmed receipt. A repeat receive does not recover the previous lost batch automatically. Content remains inspectable, but the workflow must recognize an unknown receive outcome and consult history; record-and-forget is not guaranteed delivery.

Illustrative option A syntax is:

```sh
agentw message receive --limit 10 --max-bytes 8192 --wait 30s
agentw message ack message-001 --delivery-token opaque-attempt-token
```

Option B uses the receive command without a follow-up ack. The `8192` budget is illustrative, not a measured safe default. Both options bound count and total output bytes, including envelopes, escaping, and CLI rendering overhead. Never mark a silently truncated message delivered. If one complete message cannot fit, return an explicit budget error and keep it pending; body limits and an adequate retrieval path must prevent permanent starvation. Test against the smallest qualified harness output limit.

Without `--wait`, receive checks immediately. A bounded wait returns work or an empty successful batch. Long-held requests through sbx remain unqualified; the CLI may need bounded immediate polls with backoff. Programmatic adapters retain their own attempt/receipt machinery where required, and cannot race a model-facing receive over unresolved external content injection. Neither option exposes a general `message seen` command.

**Recommended comparison:** Exercise a lost HTTP response, killed CLI, model forgetting ack, compaction, truncated output, repeated receive, and push/pull competition. Choose the semantics and meaning of delivered explicitly before removing either option. Claude's concerns about model reliability are design judgments to test, not measurements already made in this wiki.

## Status and waiting

For ambient posts with no delivery recipients, show an empty receipt set and explicit reply relationships. Recommend reporting an inapplicable recipient wait rather than treating `all` over zero recipients as success. Channel-thread replies include participant deliveries as well as mentions; current channel membership is not the receipt set.

```sh
agentw message status message-001
agentw message wait message-001 --for delivered --recipients all --timeout 30s
agentw message wait message-001 --for replied --recipients any --timeout 5m
```

Require explicit `--for delivered|seen|replied` and `--recipients any|all`. Conditions refer to the fixed recipient set accepted with the original message, subject to visibility policy; agentd rejects unauthorized aggregates. `seen` can remain unknown indefinitely when the harness supplies no corresponding evidence.

The CLI implements waits as bounded status requests within the overall `--timeout` budget. It checks durable state after reconnect and never resends the original message. The result contains current evidence, `condition_met`, and `timed_out`. **Proposed from Claude's review:** Both status and wait results embed each recipient's authorized lifecycle/presence and a short evidence-based summary. A reply timeout can therefore report that the recipient is busy since a known turn start, suspended, or has unknown activity without requiring additional presence commands. A message-trigger reference is included only with specific adapter evidence and visibility permission; it does not prove ongoing focus. Timing out or interrupting a wait only stops the local wait; it does not retract the message or cancel recipient work.

Use a finite default timeout, proposed as 30 seconds, and require an explicit duration for longer waits. Long waits may occupy a harness tool call; the interface should not silently substitute a background watcher or promise that blocking is appropriate for every harness. Persistent listeners may use the proposed [SSE hints](messaging-api.md#waiting-transports-and-sse) while this finite command uses bounded status waits; both reconcile authoritative state. SSE transport and automatic harness wakeup are separate capabilities.

## Channel membership and rooted threads

```sh
agentw channel create --group group-c --name merges   --client-conversation-id merges-001
agentw channel add channel-merges --participant worker-2   --brief-file ./context.md --brief-message-id welcome-001
agentw channel role-add channel-merges --group group-a --role coordinator
agentw channel remove channel-merges --participant worker-2
```

These are proposed spellings. Group policy governs immediate explicit adds and dynamic role rules. The optional brief is an atomic channel-visible post mentioning the newcomer; use a DM for private content. Repeat add/remove by value, with `changed: false` for no-ops. Report effective membership sources so an explicit removal does not appear to evict someone still admitted by a role. An identical brief-key retry returns the original brief without reactivating membership after later removal. Channel membership-only notification versus a brief-less-add warning remains open.

Recommend omitting `thread create/add/leave/close/reopen` for this experiment: posting a reply creates a rooted thread, DM participants are inherited, and channel-thread participation is implicit. Retaining management controls for channel threads is an alternative; explicit follow/unfollow is deferred. The older standalone-thread membership pattern moves to channels in this sketch. Naming remains provisional; no command spelling here settles it.

## Presence

Commands take participant IDs. Kind-aware output reports bot reachability and separate registration state, while bot `seen` and `idle` are not applicable; operator presence remains open. Workload activity examples below retain their existing proposed meaning. Capability support and permission to inspect it are independent.

```sh
agentw presence list --group group-build --limit 20
agentw presence show worker-2
agentw presence wait worker-2 --for idle --timeout 30s
```

**Proposed revision from Claude's review:** Start with authoritative lifecycle and observed signals. Defer `presence set` and the declaration API; requiring models to refresh availability is an untested reliability concern, not observed evidence. Presence list/show/wait remain available, and status/wait on a message embeds the authorized recipient view automatically.

Output includes a one-line summary alongside lifecycle, reachability, and activity evidence. For example: "busy since 14:02; turn began with your message", "suspended", or "activity unknown; last observed contact 20 minutes ago". Derive these from visible evidence, preserve unknowns, and never imply that a trigger association proves the agent is still working on that message. `started_at` is distinct from the last observation/heartbeat time; missing start evidence remains null. Live observations are in memory and reset on daemon restart or incarnation replacement.

**Proposed from Claude's second review:** Prefer qualified backend reachability evidence and show authenticated contact as supplementary. Do not label a running process/sandbox as responsive without a path check. [Backend signal quality](messaging-schema.md#expected-backend-evidence) varies; sbx without a harness adapter may have no activity evidence, so idle waits may time out normally.

For workload targets, `presence wait --for reachable|idle` uses an explicit condition and a finite timeout, proposed as 30 seconds subject to backend qualification. Idle requires fresh reachability and idle activity for the same active incarnation. Read and pin that incarnation across bounded requests; a target with no active incarnation or a replacement returns an explicit error. Expiry and lifecycle changes wake waiters too. A met condition does not prove a later send will succeed or get a reply.

Presence visibility is Group-authorized and not widened by conversation membership. Busy/unreachable/unknown observations do not filter durable recipients; authoritative lifecycle and Group policy govern admission. Unknown observations are not confirmed termination. Presence summaries use the same redaction policy as the raw fields.

## Output and exit behavior

Successful send results expose message ID, conversation ID, optional thread root ID, client message ID, acceptance time, and duplicate status. **Proposed from Claude's second review:** Also show authorized recipient lifecycle diagnostics, highlighting suspended/terminated recipients at send time. Include sampling time and explicit redaction/partial-result metadata; use status pagination for large sets. Diagnostics do not change a successful acceptance exit code or prove future delivery. Same-key retries retain the accepted recipient set while current lifecycle diagnostics may change. Receipt views preserve separate delivery, seen, and reply evidence rather than inventing a single completion state. Message content remains peer data in either output format; headers and delimiters are not permission grants or executable shell fragments.

Proposed exit codes are deliberately small; structured error codes carry detail:

| Exit code | Meaning |
| --- | --- |
| `0` | Normal outcome, including duplicate acceptance, repeated ack under option A, empty receive, or an unmet wait deadline. |
| `1` | API or transport failure; inspect the structured code and any unknown write outcome. |
| `2` | Local argument or input error. |

**Proposed from Claude's review:** A message or presence wait reaching its deadline exits 0 with `condition_met: false` and `timed_out: true`, just as an empty receive is a normal outcome. The earlier exit-code-3 proposal is superseded in this draft, not operator-decided. The claim that nonzero exits provoke model overreaction is a review judgment to test. API-level bounded waits can repeat within the overall budget; permission failures, transport errors, or incarnation changes are actual errors, not fabricated successful timeouts. Cancellation follows normal process interruption behavior and must not be translated into delivery failure. Final API/transport errors use a structured error envelope in JSON mode or an equivalent labeled text result, with concise diagnostics on stderr; local usage diagnostics go to stderr. No prompts or progress text mix into JSON stdout.

## Request commands and envelope output

**Codex integration proposal from [requests](messaging-requests.md):** These are candidate `agentw` workload commands, not implemented commands. Bots use the same API semantics under their own identity.

```sh
agentw dm send --to participant:reviewer --kind request --assignment any --body-file request.txt --client-message-id REQUEST_KEY
agentw request list --state open
agentw request show REQUEST_ID
agentw request claim REQUEST_ID --client-operation-id OPERATION_ID
agentw request reply REQUEST_ID --claim --body-file reply.txt --client-message-id MESSAGE_KEY
agentw request reply REQUEST_ID --outcome completed --body-file result.txt --client-message-id MESSAGE_KEY
agentw request cancel REQUEST_ID --client-operation-id OPERATION_ID
```

Claude also proposes a dedicated `request send` convenience command. Codex recommends first using `dm send` or `channel post` with `--kind request` to preserve explicit audience selection; whether to add that alias remains open.

`request reply` is proposed to follow `message reply`'s private original-sender DM behavior, and must report that audience. A parent-audience alternative is `thread reply` with explicit request ID and claim/outcome fields; it does not silently widen a private reply. Exact flags remain open. Requests use `--assignment any|each`, optional deadline, and optional authorized Task references. Plain replies preserve state; claims/outcomes depend on original candidate eligibility and current permissions. `show` separates reported outcome, delivery evidence, and sampled presence; it never claims a Task was verified complete or the assignee is currently working on it merely from a turn trigger. Stable mutation keys must be reported/preserved before submission like send keys; retries never invent new keys.

**Output recommendation, not a decision:** Claude's [envelope](messaging-envelope.md) proposes compact text by default for model-facing receive/show/history and `--format json` for scripts. JSON default remains an alternative for comparison; the HTTP API is JSON regardless. Text and JSON must expose the same IDs, authenticated versus asserted identity, audience, completeness, and status. Enrollment, oversight, redaction, and breaker management are not added to `agentw`.

Proposed markers are `more_pending`, `body_truncated`, `bytes_shown`, `bytes_total`, and an exact authorized fetch command, represented as labeled text or structured JSON. Prefer complete envelopes within the aggregate byte budget. If a diagnostic preview is necessary, label it incomplete and do not consume the delivery or advance a channel cursor; no ack token for an incomplete payload in A, and no delivered transition in B. Full-message retrieval still needs a bounded/chunked contract before oversized bodies can be supported; marking a preview does not solve that contract. Harness truncation after full HTTP receipt remains B's existing uncertainty. Preserve the open byte-limit and receive choices.

## Provenance and open decisions

The operator's 2026-09-27 discussion, handed off by Claude, decided one agentd per host, Groups as policy scopes, the DM/channel/thread starting set, and the comparative experiment. Claude proposed participant-set DM identity, ambient channel cursors, structured mentions, dynamic role membership, message-rooted threads, and the route/command direction. Codex's recommendations on immutable DM sets, explicit cursor advancement, reply audience, admission history, retries, and experiment instrumentation are synthesis, not further operator decisions.

Claude's earlier API/commands, threads/presence, and delivery reviews remain proposal sources where this model does not supersede them. The earlier operator-agreed immediate-add/idempotent-membership/optional-brief pattern is carried into proposed explicit channel membership; its former standalone-thread placement is replaced only as a recommendation. No implementation, migration, harness experiment, or PoC scope transfer was performed.

Still open: explicit ack versus receive-records-delivery; presence fields and integration into status/waits; unmet-wait exit code; Group inference; keyset pagination; JSON/text default; aggregate byte limits; per-harness content versus hints; hooks versus Claude MCP channels for Claude wakeup; urgency policy; and the product name. The text keeps review recommendations visible without deciding these choices. See [experiment design](messaging-experiments.md).

The participant/authority revision follows the operator's 2026-09-27 discussion handed off by Claude: bots, both SPIFFE mechanisms, installation scope, bridge-as-bot permissions, and the capability/permission distinction are decided. Participant kinds, storage, grants, custody, lifecycle, and delivery mechanics remain Claude proposals with labeled Codex synthesis in [Participants and permissions](participants-and-permissions.md). Bot enrollment/issuer, initial delivery mechanisms, ambient membership, workload installation unification, and federation scope remain open alongside the earlier messaging choices.

The 2026-09-27 pre-review integration carries Claude's loop/budget, oversight, request, and envelope proposals into this page with labeled Codex synthesis. All new mechanics remain proposed. Operator message authority, request inclusion in the first experiment, every control threshold, and earlier messaging/participant open decisions remain unresolved; see the four source pages linked from [the index](README.md). No implementation or new harness probe was performed.
