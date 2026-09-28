---
title: Harness delivery and push fallbacks
summary: "Research-backed harness delivery proposals with wake-policy integration, notice envelopes, and uncertain-delivery recovery."
type: design
status: draft
tags:
  - area/messaging
  - area/orchestration
  - scope/destination
updated: 2026-09-27
---

**Proposed, operator request on 2026-09-27:** Choose delivery per qualified harness profile. Following Claude's delivery review, propose notification-first through Codex's queue, a qualified hook as Claude's default wake candidate, and bounded content push through Claude MCP channels where launch policy and input correlation qualify. Other profiles use hints or authenticated pull. These revise the earlier global notification-first proposal; none is operator-selected. Pull follows whichever receive contract is selected, not an unconditional model ack requirement.

This page synthesizes original local research and a current documentation check. It does not report newly executed harness experiments or establish supported backend recipes. The original research was read again, selected Codex raw results were checked, and the four principal reports were confirmed byte-identical to their pinned PoC imports. All adapter choices and product mechanics below remain proposals.

Read the [schema](messaging-schema.md), [data flow](messaging-data-flow.md), [API](messaging-api.md), and [commands](messaging-commands.md) for the shared model. [SPIFFE authentication](spiffe-mtls-authentication.md) remains authoritative for workload identity and the host/sbx boundary. Native harness IDs, peer labels, and socket paths never replace that identity.

## Conversation delivery and wake eligibility

**Decided direction — operator discussion on 2026-09-27, via Claude's conversation-model handoff:** One agentd per host serves logical Group authority scopes. The experiment compares DMs, ambient product channels, and threads within either. Here “Claude MCP channels” always names the harness transport; a product “channel” is a provisional conversation construct, with room/topic/space and qualified channel terminology still open. All detailed routing and adapter choices remain proposals.

| Application event | Proposed inbox and wake behavior |
| --- | --- |
| DM message or DM-thread reply | Delivery rows for every other fixed participant; schedule adapters. |
| Ambient channel post | No deliveries and no native wake; available through authorized history/unread summary. |
| Structured channel mention | Delivery rows for resolved members; channel-wide mention requires separate policy authority. |
| Channel-thread reply | Deliver to eligible implicit participants plus mentions, once each; other members see ambient history. |
| Channel read-cursor advance | Updates unread state only; neither acknowledgment nor seen evidence. |

Group/default-channel posting is ambient. The proposed urgency field only schedules existing delivery obligations; it cannot turn an unmentioned ambient post into a wake. Generic SSE/UI state hints must not be forwarded to a harness for every channel post. This distinction is what permits the [DM-versus-channel experiment](messaging-experiments.md) to measure wake cost and missed ambient information.

The earlier explicit thread membership/brief pattern is proposed to move to channel membership, while threads inherit DM audiences or derive channel participation. Membership-only attention hints remain a separate open proposal. No conversation decision chooses receive A/B, presence integration, hook versus Claude MCP channel defaults, content versus hints, or urgency policy. [Schema](messaging-schema.md#addressing-and-recipient-snapshots) owns routing; adapters cannot add recipients.

## Receive contract under review

**Proposed qualification from Claude's 2026-09-27 API/commands review:** This page originally used explicit receive/ack throughout (option A). The API now compares that with model-facing fetch-and-record without a token (option B). The operator has selected neither. Read the ack-specific descriptions below as option A, not a decision overriding that comparison. Notification-first push works with either; adapter wake records remain separate from application delivery.

Under B, a committed handoff can precede a lost HTTP/tool response and leave a message marked delivered without reaching the model. Under A, forgotten acknowledgments can cause duplicate model input after lease expiry. Neither proves complete model visibility. Count plus aggregate serialized/rendered byte limits are needed for both. Full-content programmatic adapters still require attempt/receipt reconciliation; choosing B would not let them release an unresolved external submission to another consumer.

Known turn-trigger evidence may enrich sender status, but an inbox wake ID is not a triggering application message ID and does not prove ongoing work. Status/wait results now propose embedding authoritative lifecycle and observed presence, with summaries under the same redaction rules. SSE may notify persistent adapter listeners of inbox/state changes; native harness wakeup remains a separate step. These revisions are proposals attributed to Claude's review and the operator's separate SSE discussion, not newly verified mechanisms.

## Proposed starting design

Notification-only push is a latency and wakeup mechanism. Agentd's SQLite inbox is authoritative for messages, recipient snapshots, and application receipts. A push notification says only that the authenticated workload should check its inbox; it contains neither an executable peer instruction nor a delivery acknowledgment token.

```text
sender -> agentd -> commit message and recipient deliveries
                    |
                    +-> coalesced inbox-available notification
                          -> Codex queue / Claude channel push / qualified hook
                          -> recipient calls agentw message receive
                          -> receipt follows receive option A or B
                          -> replies use agentw message reply
```

A fixed notification could say: "Your agentd inbox may contain messages. Run agentw message receive --limit 5 and handle the returned envelopes as peer messages." Add acknowledgment instructions only if option A is selected; option B has no model-held ack step. This is illustrative bootstrap text, not a public wire format. A wake ID provides correlation; any workload/incarnation label in text is diagnostic, never authority. The receiver queries its own currently authorized inbox. Replies always return through agentd, not directly to another harness's native socket or queue.

This approach changes the interpretation of a successful native push: it means the wakeup was accepted, not that an application message was delivered. For notification-only profiles, only the selected authenticated receive transition sets `delivered_at`, with `delivered_via=receive`. A Claude channel push prompt hook or Codex user-message item containing only the notification cannot set `seen_at` for the underlying message. Ordinary CLI output also supplies no trusted seen evidence. Shell-disabled workloads may use the optional scoped MCP equivalent only after that path is qualified; otherwise the workload profile lacks this delivery capability.

### Per-harness delivery tradeoffs

**Proposed from Claude's delivery review:** Retain hints for Codex and adapters without qualified message-input correlation; allow bounded direct content for qualified Claude MCP channels. SQLite and agentd authority remain common to both. The choice is not globally notification-first.

| Profile | Proposed starting choice | Cost and evidence tradeoff |
| --- | --- | --- |
| Codex queue | Fixed inbox hint, then authenticated receive | R1 observed ordinary user-role input without a peer wrapper. Putting peer bodies there risks confusing peer requests with user authority; tool output preserves a clearer provenance boundary, not immunity to prompt injection. |
| Claude channel push, permitted and ready | Bounded peer envelope with message ID and unique attempt marker | R4 observed Claude channel push provenance and a prompt hook carrying the wrapper. Qualified correlation can support delivery/seen evidence, but emission alone cannot. Durable attempts and duplicate recovery are required. |
| Claude hook | Fixed hint by default | Fewer launch gates in R4; error framing and mid-turn timing need qualification. Content push remains a weaker alternative relying on internal transcript correlation, not a prompt hook. |
| Unqualified or non-injecting backend | Authenticated pull, optional qualified hint | No assumed seen evidence or automatic wakeup. |

Hints add a model cooperation dependency and an extra receive call, plus an ack call under A. They may spend a turn asking the agent to retrieve content, and the model can omit or defer that action. They also pass bodies through tool-output limits. R4 observed a 200 KB Claude channel push payload intact while oversized tool output could spill to a file with only a preview; that is comparative evidence for Claude MCP channels, not a safe universal size limit. Bound pushed envelopes and pull results separately, including provenance overhead, and qualify complete input at supported versions. [R1], [R4]

Notification-only profiles currently have no trusted application-message `seen_at` or causal message-to-turn link. A correlated wake proves only wake input. Content-push evidence can supply both, but still cannot prove understanding or ongoing work on the message. A stable visible message ID helps recognize repeated input; **Codex qualification:** it does not prevent duplicate action. Pull lease expiry also risks repeats, so compare both paths under the same failure scenarios.

## What the original research establishes

The observations below are version- and topology-specific. A completed local experiment is evidence for that scenario, not a universal product guarantee.

| Surface | Recorded evidence | Consequence for the proposal |
| --- | --- | --- |
| Codex input queue, CLI/app-server 0.156.1–0.157.1 on macOS | Loaded idle recipient started a turn; a busy recipient processed queued inputs in subsequent turns. `notLoaded` on the queried runtime could accept an entry without waking. [R1] | Prefer queue for ordinary next-turn notifications, but bind to the owning runtime and verify eligibility. |
| Codex retries and restart, 0.157.1 | Identical input with the same `clientUserMessageId` produced distinct queue IDs. Pending entries survived SIGKILL and drained after resume. [R2], [R3] | Native correlation IDs are not idempotency keys. Record queue IDs and reconcile before resubmission; resume may execute work. |
| Codex steering and control ownership | Matching `expectedTurnId` accepted input; stale IDs failed. A second `turn/start` while active steered the existing turn. A different runtime could report `notLoaded` while another held the writer lock. [R2], [R3] | Use explicit steering only under policy. Do not infer idle ownership from stored history or use start as an atomic idle-only operation. |
| Claude MCP channels, 2.1.283 on macOS | Idle push woke a turn; busy push joined at a tool-result boundary; bursts could share a turn. Early startup pushes were lost and no delivery acknowledgment was observed. [R4] (section 7.2) | Treat emission as an attempt and gate readiness; direct content needs correlated input evidence while its authoritative copy stays in agentd. |
| Claude channel push bootstrap and lifecycle | turns initiated only by Claude channel push omitted deferred tools/instructions until a normal turn after server connection. Missing resume flags dropped pushes. Server crash did not restart automatically during the observed 48-second window. `/clear` retained the server but changed the conversation ID. [R4] (section 7.2) | Check tool readiness separately from MCP connection. Reconcile lifecycle bindings and fall back when Claude channel push readiness is unknown. |
| Claude `asyncRewake` hooks, 2.1.283 | SessionStart/Stop waiters woke idle sessions, folded input into busy turns, and delivered a file retained while the session was dead after resume. Naive waiters accumulated; a singleton/liveness guard fixed that probe. [R4] (section 7.1) | A preconfigured hook is the proposed default Claude wake candidate after qualification. Its spool and exit status are not application delivery evidence. |
| Claude native peer socket, sender 2.1.281 / receiver 2.1.283 | Foreign producers injected input. Wrong `session_id` silently dropped it; `priority: now` waited for a running tool to finish. Visible sender wrappers were sender-supplied text. [R5] | Keep this as a version-pinned compatibility option; never use its labels as authenticated application identity or claim immediate preemption. |

The earlier [messaging sketch][R6] and [open-items note][R7] preferred background receive and asserted that all harnesses wake when a background call finishes. Those are design assertions, not sufficient evidence for every current harness/profile. This proposal preserves receive as the common application operation but requires a separate test for automatic wakeup from background completion. It does not carry forward the old direct-NATS client topology or PID-only authentication.

**Documentation check, 2026-09-27:** OpenAI documents app-server initialization, start/resume, and steering with an active-turn precondition. The inspected app-server page does not document `thread/queue/add`; the queue contract here rests on the versioned experiments and generated schemas. [Official app-server documentation](https://learn.chatgpt.com/docs/app-server).

The Claude documentation describes Claude MCP channels as a research preview with session opt-in, provider/account constraints, and organizational controls; events require a running session. A custom plugin is not automatically eligible merely because it is packaged as a plugin. [Claude MCP channels documentation](https://code.claude.com/docs/en/channels). The hooks reference documents `asyncRewake` waking on exit code 2, while ordinary async output can wait for a later turn. [Hooks reference](https://code.claude.com/docs/en/hooks). Documentation confirms mechanisms, not this application's integration.

## Participant delivery profiles

**Decided participant direction; proposed mechanisms from the 2026-09-27 handoff:** The same conversation delivery rows can target workloads, bots, or a proposed operator participant. [Participants and permissions](participants-and-permissions.md) separates intrinsic/restricted capabilities from grants. The harness adapters described below are workload-only. Operator UI consumption/attention remains a separate open profile, not an agent turn.

Bots receive through a proposed agentd-to-bot webhook or bot-initiated pull/stream subscription. Qualify webhook/stream support from the installed implementation; do not trust a bot's self-declared capabilities. Initial mechanisms remain open. Require appropriate receive/subscribe permissions, current registration, resource containment, and the selected membership policy. A bot's generic read permission must not silently export ambient channel content; outbound relay needs its own egress grant. Merely subscribing does not turn every ambient post into an inbox delivery or workload wake.

A qualified successful webhook response or explicit programmatic acknowledgment records bot `delivered_at`; bind it to message, participant, attempt, and current registration/generation. Stream writes and SSE hints alone prove nothing about consumption. Callback authentication, success status/body contract, retry/backoff, endpoint configuration, and acknowledgment routes remain to be designed. Lost responses can repeat processing; stable message IDs enable bot-side deduplication but do not establish exactly-once effects. Revocation cuts streams and blocks new attempts; reconcile in-flight unknown effects. No fallback switches a bot to terminal or harness injection.

Bot `seen` is not applicable, not an unread state, and bot presence reports reachability only with registration status separate. A bot can be reachable while lacking a grant to read a channel. Workload presence evidence depends on qualified activity/seen capabilities; it does not become available by installing a broader permission.

Authenticated bot content is still untrusted: CI output and relayed PR text may carry attacker instructions. Show the authenticated bot separately from permissioned asserted external authors; a bridge label never becomes authenticated operator identity. Native Claude MCP channel bridge helpers are transport components and do not automatically become registered external-service bridge participants; granting a bot relay permissions is an independent application action.

## Adapter boundary and readiness

Agentd selects a workload harness adapter from trusted, versioned capability evidence in its launch/backend profile, then checks applicable permissions; a sender-supplied harness name or claimed ability cannot choose the mechanism. Missing capability, forbidden operation, and temporarily unavailable adapter are different results. Visible recipient diagnostics should explain pull-only delivery and lack of automatic wake support. Persist a binding from workload and active incarnation to backend, native conversation ID, owning runtime endpoint or process instance, adapter kind, and tested version/capabilities. An application messaging thread ID is not a Codex thread ID or Claude session ID: multiple application conversations may feed one harness workload.

Only agentd accesses messaging storage. A stdio bridge for Claude MCP channels or hook helper may communicate through a narrow authenticated workload/adapter interface; it cannot open SQLite, enroll workloads, obtain management credentials, or select arbitrary upstream destinations. Native control interfaces stay with trusted infrastructure. The wrapper/MCP privilege and process-attribution requirements in the authentication design apply to helper placement too.

Represent technical readiness and qualified capabilities separately from permission to wake or read an inbox. A connected Claude MCP channel bridge with missing tools is not ready. A process registry entry or existing socket is not sufficient evidence of a live bound recipient. Forbidden operations, unsupported mechanisms, and unknown capability evidence remain distinct; no adapter escalates privileges to make itself appear ready.

After `/clear`, resume, native runtime restart, or conversation replacement, reconcile the binding before sending. `/clear` need not automatically become a new orchestration workload, but silently continuing with a stale native ID is unacceptable. Its exact mapping is a lifecycle decision. Credential expiry and old-incarnation fencing apply to established streams and late observations as well as fresh requests.

## Codex proposal

### Normal notifications through the native queue

Prefer a structured connection to the known owning app-server and its version-matched `thread/queue/add` interface over parsing CLI output. The original queue probes used WebSocket-over-Unix transport, an initialization handshake, and `experimentalApi: true`. The observed response returned a native queued-submission ID and the supplied client correlation ID. [R1] (direct app-server API)

1. Validate the workload binding and that the intended runtime owns the loaded conversation. Do not search by an ambiguous display name or use a default daemon merely because it can find stored history.
2. Create an in-memory wake attempt before submitting a small, fixed inbox notification. Supply a unique correlation value for that attempt, not a reused application send idempotency key.
3. On success, store the native queue ID and acceptance evidence. The associated application delivery rows remain pending.
4. Coalesce additional inbox messages into the outstanding notification. Its eventual receive queries current pending state rather than a frozen body embedded in the native queue.
5. Observe queue/history through native APIs where permitted. R1 successfully used paginated `thread/turns/list` with `itemsView: full`; the supplied `clientUserMessageId` appeared as `userMessage.clientId`. Match the unique attempt, bound conversation, and actual input item to record that the wake became turn input. This supplies wake evidence, not an underlying message receipt. If content push is reconsidered, equivalent correlation could supply message-specific input evidence, subject to the user-role provenance concern. Client IDs are correlation data, not idempotency keys; R1/R2 observed duplicate queue entries. A queue-change event is an invalidation hint. Disappearance alone does not distinguish execution from deletion. Correlate native input items, turn IDs, and the recorded attempt. [R1] (notifications and answer correlation)

If only `codex queue` is usable in a qualified profile, it is a compatibility wrapper for the same native queue, not an independent fallback transport. Invoke a fixed argument vector, preserve the returned queue ID, and use an application wake marker for reconciliation. Do not write the native queue database directly. A CLI timeout leaves acceptance unknown. [R1] (CLI contract)

### Busy, idle, and unloaded recipients

Queue is the proposed default for ordinary notifications because the original busy-session test deferred them to later turns. Do not automatically switch to steering when a queue request is slow: that changes delivery timing and may redirect active work.

`turn/steer` is an optional, explicitly authorized mid-turn mode using the exact current `expectedTurnId`. A rejected stale-turn request may be reconsidered under current state; a lost response is an uncertain attempt, not permission to send again immediately. A steer acceptance proves input acceptance for that turn, not tool interruption or a reply. [R2] (E6)

If queue support is absent, a controller that owns turn scheduling may retain notifications in agentd and use `turn/start` at a qualified idle boundary. The observed start-while-active behavior makes this unsuitable as an automatic replacement for queue when an interactive user or another client can race the start. In that case use pull or an operator-visible pending notification. Do not call `turn/interrupt` merely to deliver a message.

For `notLoaded`, first distinguish a wrong runtime from a genuinely suspended workload. Route to the owner if known; otherwise leave the inbox pending. Authorized workload resume belongs to lifecycle management and may drain previously queued inputs. It must preserve launch policy and establish current authority before delivery. Sending a message alone does not authorize launching or resuming compute. [R2] (E1/E5/E13)

## Claude proposal

### Conditional content-push candidate: Claude MCP channels

Where launch policy permits Claude MCP channels, configure a per-workload bridge during provisioning and send bounded message envelopes using `notifications/claude/channel` only when content-push qualification passes; otherwise send hints. Use string-valued metadata carrying an attempt marker. The original experiment found non-string metadata could drop the whole notification. This is a native Claude extension, not generic MCP push support for other harnesses. [R4] (section 7.2)

Qualify all launch gates: Claude channel push capability declaration, accepted protocol revision, session opt-in, account/provider and organization policy, and an installed/allowed plugin or explicitly authorized development configuration. A development warning is not something the adapter silently confirms. Reconnect/resume must re-establish these conditions. If the profile cannot enable Claude MCP channels, select a qualified fallback at launch rather than waiting for silently dropped notifications.

**Pinned gate evidence:** R4 observed default-allowlisted plugins `fakechat`, `telegram`, `discord`, and `imessage`; packaging a product plugin did not by itself qualify it. Development loading showed a blocking warning on every launch, including resume. Product automation must not confirm that warning through tmux. The report's code inspection identified organization controls including `allowedChannelPlugins` and exclusion of Bedrock, Vertex, and Foundry providers; these are version-pinned findings, not newly verified current eligibility. Select Claude channel push only when the workload's actual account/org/launch policy permits it; revisit the default if a product plugin becomes eligible. [R4]

Readiness requires more than a successful MCP handshake. The research lost an immediate post-handshake push and found turns initiated only by Claude channel push lacked reply-tool/instruction setup. Propose a managed bootstrap after the Claude MCP channel bridge connects that establishes inbox-access instructions and tools, with an observable readiness result. Test this with a disposable probe before exposing real work. A fixed sleep is not proof of readiness, and no arbitrary user prompt should be injected into an existing unmanaged session to repair setup. [R4] (enabling, timing, and replies)

**Proposed content receipt:** Reserve delivery ownership and persist an attempt before submission. Include authenticated sender provenance, message ID, and a unique attempt marker in a bounded peer envelope. R4 observed a `<channel source=…>` wrapper, `turnOrigin: peer`, and `UserPromptSubmit` with the full wrapper. A qualified trusted observer must match the active binding, marker, and complete expected envelope; a marker alone or a hook event preceding a rejection is insufficient. Validate subsequent admission to model input before setting `seen_at`. Record the input-acceptance receipt as `delivered_via=channel` (the existing harness-mechanism placeholder, not a product-channel receipt) and the distinct seen evidence when each threshold is met; neither requires the model to ack. Bursts may share a turn. If only a hint was sent, these observations remain wake evidence. [R4]

The observed prompt hook is a candidate for message-to-turn correlation, not proof that every hook invocation inevitably reaches inference. Qualify cancellation, hook rejection, truncation, busy-turn insertion, and native turn association. For busy insertion, record input added to an existing turn rather than falsely saying the message started it. Until these checks pass, use the hint/pull profile.

Expose only normal messaging operations if the optional MCP tool surface is used; replies call agentd's send/reply service. Do not enable `claude/channel/permission` for ordinary peer messaging. Permission relay is a separate operator authority, not something another agent's request can exercise. Claude's reference explicitly separates that capability from ordinary Claude channel push delivery. [Claude MCP channels reference](https://code.claude.com/docs/en/channels-reference).

Bind the bridge to the live process/connection and current conversation mapping, not only inherited `CLAUDE_CODE_SESSION_ID`, which was stale after `/clear` in the experiment. Use isolated endpoints, handle EOF and failed children, and detect orphaned bridges or port collisions. The original fixed-port plugin and crash results are reasons to verify recovery, not guarantees of automatic restart. [R4] (lifecycle)

### Default wake candidate: preconfigured hooks

Following Claude's review, qualify a small `asyncRewake` hook installed at authorized launch/resume. The original SessionStart/Stop arrangement maintained one waiter; on inbox availability it printed a notification and exited 2. It woke idle sessions and joined busy turns at a boundary. The probe used launch settings, required no organization gate for Claude MCP channels, and recovered a retained hint after crash/resume. This supports qualification as the default Claude wake candidate, not a guarantee on every current profile. [R4] (section 7.1)

Adapt that pattern to agentd's current inbox state through the authenticated gateway. Prefer a non-consuming availability wait: the helper does not lease messages or acknowledge them before the model can call receive. That wait is a proposed internal helper capability, not an existing public API route. If a local spool is needed, store only disposable wake hints in protected per-workload infrastructure; SQLite remains the sole application message authority.

Keep at most one waiter per incarnation, check the owning process instance rather than PID alone, and stop old waiters on exit/rebind. Re-arm on the appropriate lifecycle events, rate-limit repeated reminders, and require explicit activation of a receive loop rather than making every Stop produce an endless turn. Retained spool files in the original experiment demonstrated one recovery scenario; the rename-to-delivered step did not prove that a harness consumed input across every crash window.

Use neutral peer-inbox framing, without the prototype's promotion of peer content to an operator prompt. R4 observed that omitting internal `rewakeMessage` produces blocking-error framing naming `SessionStart:startup`. That may cause an agent to investigate an apparent failure instead of checking its inbox; this behavioral concern is untested. Qualify default framing first. If usable behavior requires `rewakeMessage` or `rewakeSummary`, record an explicit version-pinned dependency on those `@internal` fields and a fallback when they change; do not claim the profile avoids internal APIs. A hook exit status is wake evidence, not `delivered_at` or `seen_at`.

R4's hook content appeared in task-notification/system-reminder records and fired no prompt hook. Direct hook content would therefore need qualified transcript correlation with weaker, internal-format evidence and durable attempts. Keep it an alternative, not the default content route.

### Optional compatibility path: native peer socket

A trusted host adapter could target Claude's native peer socket when Claude MCP channels/hooks are unavailable and that version/profile has been explicitly qualified. The research shows genuine input delivery, but also silent session-ID mismatch drops, sender-asserted wrappers, permission-class behavior, sandbox failures, and incomplete acknowledgment semantics. [R5]

Treat this as an opt-in compatibility adapter rather than an automatic bypass of a Claude channel push or permission restriction. Resolve process instance, current native session, and endpoint from the trusted launch binding; preserve any native permission hold. Do not read unrelated session credentials or rely on observed unauthenticated macOS access as the product's security contract. The peer-socket identity mechanism is not agentd authentication.

Send only the inbox hint initially. A successful socket write does not record application delivery. Native held/denied/expired notices, when available and authenticated by the adapter's qualified binding, classify the wake attempt. They do not authorize trying a weaker path after a permission denial. `priority: now` is not a guarantee of tool preemption. [R5] (T5-WRONG/T6 and control frames)

### Credential custody for Claude MCP channels

**Observed in R4:** Claude passed `CLAUDE_CODE_MESSAGING_TOKEN` and `CLAUDE_CODE_MESSAGING_SOCKET` to every MCP server it spawned, exposing that session's native peer-messaging credentials to those children. A managed bridge inherits this exposure; treating only the bridge as privileged would miss other MCP children. Qualify launch-time child trust, environment custody, logging, and any supported isolation/filtering before enabling the profile. These are native credentials, not agentd workload credentials, and must never become the basis for application sender identity. This review read the report, not live credential values.

## Wake timing and urgency

**Integration note:** Read these timing candidates under the [combined wake policy](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy), which now owns the proposed ordering of controls, budgets, and urgency exceptions.

**Proposed from Claude's delivery review, not operator-decided:** Add `urgency: normal|urgent`, default normal, to send intent. Group policy separately authorizes urgent use and can apply quotas; reject unauthorized urgency explicitly rather than silently changing it. Include urgency in canonical retry comparison. It changes scheduling, not permissions, delivery receipts, reply deadlines, or authority to resume compute.

Coalesce normal hints per workload/incarnation. For Claude, wait for fresh idle evidence before emitting a normal hint or content push; a tool-result boundary during a busy turn is not a next-turn boundary. For idle recipients, use a bounded coalescing delay. If the delay expires while busy or activity is unknown, leave pending and expose the delay rather than silently interrupting work. The deadline bounds batching, not guaranteed delivery. A registry idle check can race a new turn; qualify the race and describe idle-only scheduling as best effort unless the adapter owns an atomic admission boundary.

Authorized urgent messages may wake idle workloads immediately or join Claude's running turn at the next supported boundary, with explicit permission/attention holds preserved. Codex urgency expedites queue submission but does not upgrade it to steering; queue timing still waits for a later turn. Mid-turn Codex steering remains a separately authorized mode. No urgency bypasses a Claude channel push gate, approval, suspension, or binding failure.

Every idle wake may spend a model turn; broadcasts can multiply that cost. Measure coalescing delay, fairness, rate limits, burst behavior, and wake budget before choosing values. **Codex qualification:** Duplicate hints are not harmless: even without repeating peer bodies they can reshape work, trigger another receive, and consume turns. Permit bounded duplicates deliberately rather than promising safety from their small size.

## Activity evidence feeding presence

**Proposed mapping from the pinned research:** Feed [presence observations](messaging-schema.md#presence-observations) from qualified native activity sources, independently of whether the adapter pushes bodies or hints. R4 reports Claude registry `busy`, `idle`, and `waiting`, with `waitingFor` values distinguishing input needed and dialog open. Validate registry PID and `procStart` against the bound live process. Preserve the native wait reason as attention detail; only a known permission dialog warrants a permission-blocked label. The `Notification` hook is a candidate source; R4 captured it during a permission-relay experiment but did not establish coverage for all wait states. [R4]

R1/R2 observed Codex `thread/status/changed`; E8 observed `waitingOnApproval` and `waitingOnUserInput`. These can provide activity/attention detail for the owning bound runtime. A wait flag does not always mean a human must respond, and observing it grants no permission to resolve it. Unknown or stale activity stays unknown. Native start events may supply busy start time; wake history alone supplies no application-message trigger. Correlated Claude channel push content can identify inputs added to a turn, but not ongoing focus. [R1], [R2]

## Headless Tasks and sbx

For manager-owned Codex Tasks, use the qualified app-server controller with exclusive turn scheduling; the queue and steer distinctions still apply. For Claude Tasks, evaluate a manager-owned `-p` streaming input/output process separately from interactive Claude MCP channels. The original report verified structured output and recorded stream-json input as help-text; it did not establish the full busy-input, retry, or acknowledgment contract. Current CLI documentation lists `--input-format stream-json` for print mode. [R4] (sections 7.1 and 8), [CLI reference](https://code.claude.com/docs/en/cli-reference).

Do not claim that writing stdin proves delivery or that a completed print-mode process can receive later pushes. If the Task has exited, leave messages queued or invoke a separately authorized resume/restart policy. An interactive Session, a headless Task, and a native conversation have different lifetimes.

Host socket observations do not qualify sbx. Start sbx with authenticated API pull over the runtime credential-proxy path. A guest-side Claude channel push/helper or remote native control adapter can be added only after its identity, connectivity, custody, and lifecycle are qualified; the host cannot assume it can reach a guest Unix socket. No raw SVID is introduced into the workload merely to make push work. Map this work to [BV-01/BV-02, BV-05/BV-06, BV-07, and BV-08](backend-validation-spikes.md), without transferring implementation scope into the PoC automatically.

## Fallback and uncertain-outcome rules

| Situation | Proposed action | What remains true |
| --- | --- | --- |
| Push capability absent or disabled before submission | Use the preselected hook or pull profile; expose degraded wake capability. | Pending inbox is intact. |
| Explicit non-acceptance, such as stale binding or unavailable endpoint | Reconcile authority/readiness, then select a permitted route. | Retry is bounded and preserves workload identity. |
| Native response lost or notification emitted without receipt | Mark the wake outcome unknown and reconcile before another push. | No application delivery receipt is inferred. |
| Wake accepted but no inbox activity | After a bounded grace period, inspect queue/harness state and expose stalled delivery; retry hints under a bounded policy. | Duplicate hints may waste turns but do not themselves repeat peer instructions. |
| Permission hold, denial, or required user input | Report blocked/attention-required; do not route around the restriction. | Messaging never grants execution approval. |
| Harness suspended or exited | Keep pending messages and wait for an authorized lifecycle transition. | No implicit launch or resume. |
| No qualified automatic wake path | Explicit receive/poll, a validated background waiter, or operator-visible pending work. | Automatic wakeup is unavailable, not silently promised. |

Fallback changes the wake transport, not sender identity, Group policy, recipient snapshot, or the selected receive contract. A bounded retry of a hint is acceptable only under the configured policy and rate limit; it is not evidence of exactly-once input. Coalesce wakes per workload/incarnation, back off, and stop retrying a dead binding. Never reorder or delete unrelated native queue entries.

For a qualified full-content push adapter, use stricter rules: persist an attempt before injection, correlate native acceptance, and keep an unresolved external submission in an uncertain state. Merely expiring a local lease cannot cancel input already accepted by the harness. Do not blindly release that same content to another push/pull consumer until reconciliation or an explicit at-least-once recovery policy permits duplicates. This stronger recovery obligation is part of the cost of choosing content push per profile.

Terminal injection is not an automatic fallback. The old sketch proposed bracketed-paste nudges, but terminal contents, foreground ownership, permission dialogs, and partial input make a safe target harder to establish. Prefer a visible operator notification. A manual terminal nudge may be investigated separately; it must not become a silent path for arbitrary message bodies or confirmation of approval dialogs.

## Pull and background-receive fallback

`agentw message receive --wait 30s --limit 5` remains the common application path, followed by explicit ack only under option A; option B records the receive handoff without a model token. Reading an inbox list is inspection, not a receipt. If the agent has shell access but no qualified push, provisioning instructions can ask it to check before beginning work and before ending a turn. That provides cooperative polling, not guaranteed idle wakeup.

A harness-managed background receive is a candidate where completion produces a model-visible event. Verify that exact behavior per harness, backend, and launch profile. A shell process that survives its launching tool is not proof that its output will wake the model. Keep one consuming waiter per incarnation, cancel/fence predecessors, and qualify output truncation, permission pauses, and tool-result buffering. Do not background a receive that acquires a short lease long before its result can be presented; either align the lease/renewal protocol or use a non-consuming availability waiter and let the foreground agent acquire messages.

Under option A, truncated CLI output must not trigger automatic acknowledgment. Under B, recorded handoff can already precede truncation or response loss; output budgets and history recovery mitigate but do not prove receipt. Bounds, explicit content retrieval, and confirmation of complete receipt need qualification. Do not reconstruct a receipt from a generic Stop/turn-completed event. Background waiters, hooks, and push attempts also cannot independently race for ownership of the same message; the agentd dispatcher coordinates receive and qualified content-push ownership.

## Attempt records and observability

**Proposed simplification from Claude's delivery review:** Notification-only adapters use an in-memory attempt map with workload/incarnation, bound runtime, unique wake marker, pending watermark, timing, native queue/correlation IDs, observed outcome, and retry budget. Coalesce and reconcile while live. After agentd restart, rebuild from durable pending deliveries and current authority/readiness; submit at most one fresh initial hint per eligible workload, subject to timing policy. Later retries remain bounded. A native queue may still contain a pre-crash hint, so duplication across restart is explicitly possible. Durable wake audit is optional diagnostics, not required delivery state.

Content-push adapters instead persist attempt ID, message/recipient, incarnation/binding, mechanism/version, immutable submitted-envelope reference, native IDs, timestamps, and `prepared|accepted|rejected|unknown` outcome before submission. A crash with no definitive result leaves an unknown attempt that blocks competing content consumption pending reconciliation or an explicit duplicate-permitting recovery policy. Retention and receipt evidence must support crash recovery and stale-report fencing. Stable IDs aid correlation, not exactly-once effects.

A wake watermark is a scheduling hint, not a consumption cursor. Accepting a hint never advances deliveries. Use register/recheck for arrivals during reconciliation. Application transitions use the proposed `messaging_events` log; measured experiment runs may also collect wake telemetry with explicit crash gaps, without requiring durable hint state for delivery correctness; transient wake telemetry never masquerades as delivery/seen events. Membership-only hints recover through current memberships and the retained transition log, not just pending message rows; their replay cursor contract remains open.

Operator diagnostics should distinguish inbox backlog, adapter unavailable, wake queued, wake outcome unknown, permission blocked, and recipient suspension. Presence remains advisory: a fresh idle signal can help schedule a wake, but it does not prove acceptance. Channel membership changes and presence changes may share a generic attention hint only if policy permits; their discovery stays in their own APIs. An optional channel-add brief is an ordinary message and follows the selected message delivery/receive contract.

## Qualification before enabling a profile

Bot qualification is separate: test callback/stream authentication, revoked registrations and grants during active delivery, duplicate webhook processing, missing acknowledgment, channel read permission without membership, and relay egress denial. Record evidence without populating bot seen/activity or workload incarnation fields. These are proposed tests; no live bot was registered or contacted.

These are proposed bounded tests, not results from this write-up. Record exact harness and runtime versions, interactive/headless profile, backend, source of each receipt, and raw evidence IDs.

| Test | Required evidence |
| --- | --- |
| Two bound workloads and wrong endpoint/session/incarnation | No cross-workload notification or receipt; wrong-runtime `notLoaded` never triggers a second owner. |
| Idle, busy tool, permission wait, and no active process | Document whether a wake creates a turn, joins it, waits, or fails; no claim of immediate tool interruption. |
| Queue retry with lost response | Demonstrate reconciliation and duplicate-risk reporting, including identical client correlation IDs. |
| Claude cold startup, missing flags, deferred tools, and Claude channel push crash | Distinguish connected from ready; pending content survives loss and reconnect. |
| Hook start/stop, timeout, compaction, `/clear`, crash, and resume | One current waiter; no old process consumes or reports on a successor's behalf. |
| Agentd crash before/after native submission | Hints rebuild/coalesce with bounded possible duplicates; content attempts durably block blind competing delivery until reconciled. |
| Many messages and many wakeups | Coalescing, ordering expectations, bounded model turns, and no missing application messages. |
| Receive versus qualified content-push path | Atomic ownership and explicit unknown-outcome recovery; lease expiry alone cannot certify non-delivery. |
| Background tool completion and oversized input | Actual model-visible wake and complete content on each qualified harness; otherwise mark unsupported. |
| Claude channel push full-content correlation | Match complete envelope and bound input admission; test rejected prompt hooks, busy insertion, duplicates, truncation, and missing observations. |
| Hook default error framing versus internal override | Measure erroneous failure investigation; document any version dependency and fallback. |
| Normal/urgent timing and broadcast cost | Coalescing, idle race, bounded batching, permission holds, and no urgency-triggered Codex steering. |
| Host and sbx separately | Qualified authenticated API route and helper custody; host results do not imply guest access. |
| Reply, channel membership, and presence handling | Explicit replies and add briefs use agentd; no receipt inferred from unrelated turns, membership changes, or online status. |

## Budget and envelope integration

**Codex integration proposal:** [Loops and budgets](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy) owns the combined policy for suppression, budgets, urgency, and coalescing. This page owns harness mechanism/timing and evidence. Its earlier urgency bypasses are conditional on that combined policy: neither urgency nor adapter capability overrides quiet/pause/freeze, revoked authorization, or a harness permission wait. Budget deferral leaves delivery pending; a later scheduler reconciliation or natural pull can recover it without a new send. A breaker defaults to quiet; hold is a separate optional escalation. Unknown causal depth in pull/non-injecting profiles is not zero and cannot be bounded by a depth threshold.

Use the [agentd notice template](messaging-envelope.md#agentd-notices) for the fixed inbox-available hint; never interpolate a sender's body into the privileged hint framing. The hint is not a persisted message and has no receipt of its own. Persisted breaker notices are ambient and wake nobody, including in DMs; separately authorized operator attention handles escalation without recursively feeding inbox wakes.

For qualified content-push paths, place the full agentd-rendered envelope inside Claude's hook or Claude MCP channel framing, retaining harness-specific evidence limits. Record the actual rendered input/attempt correlation needed for receipts without treating random envelope nonces as send identity; retention/redaction of cached content follows the [central retention item](messaging-schema.md#retention-and-redaction-open-decision). Incomplete previews cannot prove complete delivery or visibility. A queued native input may survive a later intervention; preserve submitted/unknown outcomes and reconcile rather than blindly resubmitting.

The pinned R1 Codex queue observations show ordinary user-role input without authenticated peer framing. This strengthens the notification-first recommendation; it is not a claim that every future Codex profile must behave identically or that an envelope changes harness instruction authority. [Envelope review](messaging-envelope.md#codex-review) records this qualification and the text-versus-JSON experiment. Operator message authority remains unresolved.

## Source register and evidence boundary

Original experiments were performed on 2026-09-26. The reports and selected raw evidence were inspected on 2026-09-27. The source folders were plain directories; durable citations below use their PoC imports pinned at `0d04ae5facd63448e278a08be68ce54922e6c994`. The four reports matched both the originals and committed imports at inspection. Selected raw Codex records checked directly were `busy_queue_duplicate`, `busy_queue_after_crash`, `busy_queue_resume`, `steer_stale`, `steer_valid`, and `concurrent_turn_start`. Claude outcomes here are reported observations in its original research, not freshly replayed tests.

- [R1 — Codex peering report][R1]: native queue, addressing, loaded/busy behavior, correlation, and limits of the initial experiment.
- [R2 — Codex session-management report][R2]: subsequent controlled E4–E6 and E12–E13 tests. Its restart and identical-input results extend R1's narrower observations rather than contradict them.
- [R3 — Codex raw lifecycle results][R3]: machine-readable records behind the selected checks.
- [R4 — Claude session-management report][R4]: hook inbox, Claude channel push startup/delivery/lifecycle, and headless-output research.
- [R5 — Claude peering report][R5]: native peer transport, trust labels, wrong-session drops, and busy-tool behavior.
- [R6 — Historical messaging design][R6] and [R7 — original open items][R7]: provenance for polling, hook, and terminal fallbacks; not current destination authority.

No active sessions were messaged, native queues changed, hooks installed, credentials read, or sibling repositories edited for this synthesis. The proposal still needs decisions on urgency/timing, per-profile content push, deployment of custom Claude MCP channel plugins, readiness/receipt proof, and retry budgets.

Claude's delivery review dated 2026-09-27 prompted the per-harness tradeoffs, hook default candidate, conditional Claude channel push content path, Codex history correlation, custody note, activity sources, urgency policy, and split between transient hints and durable content attempts. These remain proposals, not operator decisions. Relevant passages in pinned R1, R2, and R4 were reread for this revision; no live harness experiment or current eligibility check was performed. Codex qualifications: IDs do not deduplicate model actions; hints can disrupt work; prompt-hook observation requires admission qualification; idle checks race; and an urgent flag cannot bypass scheduling authority or permission holds.

The operator's 2026-09-27 conversation-model discussion decided the DM/ambient-channel/thread experiment and Group/host boundary. Claude supplied proposed routing mechanics; Codex synthesized the wake-eligibility table, terminology disambiguation, and telemetry distinction. Earlier harness research and all unresolved delivery choices remain unchanged in claim status.

[R1]: https://github.com/tbhb/agent-orchestration-poc/blob/0d04ae5facd63448e278a08be68ce54922e6c994/research/imported/agent-peering-tests/CODEX_PEERING.md
[R2]: https://github.com/tbhb/agent-orchestration-poc/blob/0d04ae5facd63448e278a08be68ce54922e6c994/research/imported/agent-session-tests/CODEX_SESSION_MANAGEMENT.md
[R3]: https://github.com/tbhb/agent-orchestration-poc/blob/0d04ae5facd63448e278a08be68ce54922e6c994/research/imported/agent-session-tests/session_experiments/codex/results.jsonl
[R4]: https://github.com/tbhb/agent-orchestration-poc/blob/0d04ae5facd63448e278a08be68ce54922e6c994/research/imported/agent-session-tests/CLAUDE_CODE_SESSION_MANAGEMENT.md
[R5]: https://github.com/tbhb/agent-orchestration-poc/blob/0d04ae5facd63448e278a08be68ce54922e6c994/research/imported/agent-peering-tests/CLAUDE_CODE_PEERING.md
[R6]: https://github.com/tbhb/agent-orchestration-poc/blob/0d04ae5facd63448e278a08be68ce54922e6c994/design-sketch/04-messaging-and-shared-context.md
[R7]: https://github.com/tbhb/agent-orchestration-poc/blob/0d04ae5facd63448e278a08be68ce54922e6c994/research/imported/agent-peering-tests/OPEN_ITEMS.md

The operator's 2026-09-27 participant/authority discussion, handed off by Claude, decided bots as distinct messaging participants, both SPIFFE authentication mechanisms, Group/host installation scopes with future scopes possible, bridges as bot installations with bridging permissions, and capabilities distinct from permissions. The participant/installation mechanics are Claude proposals; Codex's kind-specific lifecycle, containment, and evidence qualifications are linked from [Participants and permissions](participants-and-permissions.md). Issuer/enrollment, first bot delivery paths, ambient membership, workload installation unification, and host-wide federation meaning remain open.

The 2026-09-27 pre-review integration carries Claude's loop/budget, oversight, request, and envelope proposals into this page with labeled Codex synthesis. All new mechanics remain proposed. Operator message authority, request inclusion in the first experiment, every control threshold, and earlier messaging/participant open decisions remain unresolved; see the four source pages linked from [the index](README.md). No implementation or new harness probe was performed.
