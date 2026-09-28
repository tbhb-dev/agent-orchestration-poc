---
title: Domain glossary
summary: "Shared domain vocabulary, source ownership, historical distinctions, and unresolved terminology choices across the wiki."
type: topic
status: active
tags:
  - area/orchestration
  - area/identity
  - area/messaging
  - scope/bridge
updated: 2026-09-28
---

## How to use this reference

This glossary summarizes the [README authority map](README.md#current-authority-and-historical-material); it does not replace owning pages or decide between their proposals. **Decided** denotes accepted destination terminology or direction, not implementation. **Proposed** denotes destination mechanics still under review. **Historical/PoC** and **deferred** qualify older senses; statements labeled decided inside an archive retain only their original context. Technical definitions are included where the wiki relies on their distinction, without qualifying any backend as implemented or secure.

Session, Task, Workspace, and Group name product concepts. Lowercase variants occur in prose without defining additional concepts; native harness sessions/threads, planning tasks, and historical groups do have distinct senses, identified below. Component identifiers retain their lowercase spellings. Source-page lifecycle status such as `active` or `draft` is separate from claim status. The bridge scope of this reference reflects its reconciliation of destination vocabulary with historical PoC usage; it transfers no work into the PoC.

## Vocabulary

### Acceptance

**Proposed:** Agentd durably records a valid, authorized message and its immutable acceptance facts. Ordinary acceptance publishes it and creates its delivery rows; a hold records private acceptance without publication. Acceptance does not prove native input, delivery, attention, or successful work. See [send flow](messaging-data-flow.md#3-resolve-and-commit) and [publication](messaging-schema.md#requests-controls-and-publication).

### Acknowledgment (ack)

**Proposed:** An authenticated consumer reports acceptance of a particular delivery attempt. Model-facing receive option A requires an explicit ack; option B records a handoff without one. Bot and content-adapter acknowledgments have separately qualified contracts. Ack is not a reply, channel cursor advance, or proof of model understanding. See [receive alternatives](messaging-api.md#receive-alternatives).

### Activity

**Proposed:** Qualified, fresh harness evidence of `idle`, `busy`, or `unknown`, tied to the active workload incarnation. `started_at` denotes an evidenced turn start, not the latest heartbeat. Activity is distinct from running lifecycle, reachability, availability declarations, and attention. Bot activity is not applicable; operator presence is undesigned. See [presence observations](messaging-schema.md#presence-observations).

### Agent

Contextual shorthand for an agent operating through a native harness; it is not a fourth product primitive or participant kind. For authority, current pages use **workload**; for messaging identities they propose **participant**. The historical “agent identity” covered the session process tree, not a model's intent. See [product primitives](mental-model.md#three-primitives), [participant kinds](participants-and-permissions.md#participant-identity-and-kind), and [historical identities](mental-model-poc.md#entities-and-identities).

### agentctl

The management client and, in the **current host design**, trusted harness wrapper. Management operations require authorization; installing the executable grants none. Its proposed `worker-token` helper serves the trusted sbx resolver, not an ordinary worker-role operation or credential export to agents. See [components](spiffe-mtls-authentication.md#components-and-request-path) and [identity commands](identity-commands.md#lifecycle-integration-and-protected-resolver).

### agentd

The trusted orchestration authority. **Decided direction:** one agentd per host serves logical Groups. It owns authorization and authoritative workload records; the **proposed** messaging design gives it sole access to messaging storage. Historical per-Group/per-boundary local daemons are superseded. See [Group boundary](group-peering.md#group-and-trust-boundary), [identity ownership](identity-schema.md#ownership-and-records), and [messaging ownership](messaging-schema.md#ownership-and-scope).

### agentgh

**Historical/PoC design input:** the GitHub monitor, distinct from agentd orchestration and agentgw request authorization. Its event collection/cache responsibilities are preserved for provenance, not established as a current destination component or verified live service. See [archived responsibility split](peer-authentication-historical.md#proposed-responsibility-split) and [gateway direction](peer-authentication-historical.md#gateway-direction-carried-forward-from-the-poc).

### agentgw

In the **current host proposal**, the trusted workload application-gateway function, embedded in agentctl or separately packaged, forwarding allowed operations with protected upstream credentials. Earlier senses were a GitHub gateway and then a combined identity/egress sidecar; that bespoke sidecar is deferred. These names do not require one universal proxy. See [current components](spiffe-mtls-authentication.md#components-and-request-path), [deferred sidecar](execution-isolation.md#combined-identity-and-egress-sidecar), and [historical gateway](peer-authentication-historical.md#gateway-direction-carried-forward-from-the-poc).

### agentw

The workload-facing client for messaging and permitted orchestration operations. In the **current design**, it reaches agentd through a credential-holding host wrapper or sbx credential proxy; it does not enroll itself or choose its role. Bots may use the shared API without agentw. See [participant scope](messaging-commands.md#participant-scope) and [workload identity surface](identity-commands.md#workload-surface).

### Ambient

**Decided conversation direction:** content is available to authorized readers without automatically entering their inboxes or waking them. Proposed channel mentions and implicit thread participation create selected delivery obligations while the same body remains ambiently readable. Ambient does not mean public or permission-free. See [recipient snapshots](messaging-schema.md#addressing-and-recipient-snapshots).

### Asserted external author

**Proposed bridge provenance:** opaque `asserted_external_author` metadata supplied by a bot with inbound bridging permission. Agentd authenticates the bot, not that external person/account. Keep the assertion separate from authenticated sender identity; never convert an asserted name into a local operator principal. See [bridge permissions and provenance](participants-and-permissions.md#bridge-permissions-and-provenance).

### Assignment and assignee

**Proposed structured-request terms:** `any` asks one eligible candidate to take responsibility; `each` tracks separate recipient outcomes. For `any`, the assignee is the winning claimant, not everyone addressed through a role. Eligibility and a claim do not grant execution authority or prove work started. See [request kind](messaging-requests.md#the-request-kind) and [claim qualifications](messaging-requests.md#codex-review).

### Attachment

Connection to an existing live Session's terminal, distinct from launching another command or resuming native conversation history. Read-only streaming is the **decided minimum UI goal**; full interaction is the target. **Proposed** observation/control attachments have separate authorization, with one active input/resize controller and potentially several observers. See [terminal attachment](mental-model.md#terminal-attachment-and-ui-streaming).

### Attention

**Proposed operator interaction:** a view of matters requiring human review, including mentions, holds, breaker trips, input/permission waits, and uncertain delivery. An attention item is not necessarily a conversation message or harness permission request; routing it does not resolve it. See [operator attention](operator-oversight.md#operator-attention) and [native evidence](messaging-delivery.md#activity-evidence-feeding-presence).

### Authority binding

**Proposed identity term:** the authenticated link from a credential to a workload incarnation, bot credential generation, or separately designed operator binding. `authority_binding` is kind-specific; merely looking up the participant's latest generation cannot authenticate an older credential as current. See [identity records](identity-schema.md#ownership-and-records) and [binding gate](identity-schema.md#authenticated-binding-is-an-implementation-gate).

The new [preliminary review, IR-01](identity-preliminary-review-claude.md#p0-findings) compares credential-digest, authority-scoped path, issued-at watermark, and private-claim candidates. These remain competing proposals; the glossary does not select a binding representation.

### Authorization

The policy decision allowing a currently authenticated principal to perform an operation on a resource. Identity alone, membership, a capability, or message content does not supply permission. **Proposed mechanics** combine current registration/binding, grants, scope containment, and conversation policy. See [common authority path](identity-data-flow.md#common-authority-path) and [receiving-Group authorization](group-peering.md#authorization-at-the-receiving-group).

### Backend

The execution provider implementing workload placement, lifecycle, storage, connectivity, identity custody, and protection contracts. **Decided initial targets:** host mode and Docker Sandboxes (`sbx`); remote placement is an extension direction. A backend is not a Workspace, Group, or harness, and its readiness is not Task completion. See [placement contracts](mental-model.md#workload-placement-extensibility) and [initial scope](spiffe-mtls-authentication.md#initial-backend-scope).

### Bot

**Decided:** integration software participating in messaging independently of agent workloads, with its own SPIFFE identity and either supported authentication mechanism. Bot custody, enrollment, delivery, and generation records remain **proposed**. A bot has no harness wake adapter; a bridge is a permissioned installation of a bot, not another kind. See [bots, credentials, and delivery](participants-and-permissions.md#bots-credentials-and-delivery).

### Bridge

**Decided:** a bot installation carrying bridging permissions. **Proposed** inbound relay with asserted authorship and outbound relay are separate grants. A Claude MCP channel “bridge” helper is instead a harness transport component; it does not automatically become an installed integration bot. See [bridge provenance](participants-and-permissions.md#bridge-permissions-and-provenance) and [delivery profiles](messaging-delivery.md#participant-delivery-profiles).

### Brief

**Proposed channel sense:** an optional ordinary channel post, atomically added with explicit membership and mentioning the newcomer; it is visible to entitled channel readers. This carries forward an older standalone-thread add/brief pattern. The **historical PoC group brief** and proposed Group standing context are broader context, not private channel messages. See [channel membership](messaging-schema.md#channels-and-membership) and [historical shared context](mental-model-poc.md#entities-and-identities).

### Bus

**Historical/PoC:** durable coordination storage for messages, delivery cursors, roster, claims, and decisions, proposed through NATS/JetStream. **Current messaging proposal:** agentd alone owns SQLite with after-commit hints; a broker is a possible future mechanism. Neither a bus nor terminal bytes define the product conversation model. See [historical coordination plane](mental-model-poc.md#coordination-plane) and [current ownership](messaging-schema.md#ownership-and-scope).

### Capability

**Decided:** what a participant can actually do, distinct from what policy permits. **Proposed classification:** harness/runtime restrictions narrow capability; agentd authorization restrictions are permissions. Trusted, versioned evidence qualifies abilities such as push wake, shell use, or image input. Linux capabilities and protocol capability declarations keep their technical senses and are not grant names. See [capabilities versus permissions](participants-and-permissions.md#capabilities-versus-permissions).

### Causal depth

**Proposed:** `caused_by` and `causal_depth` record agentd-derived scheduling provenance from qualified trigger evidence. They do not prove semantic causation. The original zero-for-missing-trigger wording conflicts with the review's null-for-unknown rule; the integrated recommendation preserves unknown and reserves zero for evidenced independent roots. Multiple-trigger aggregation is open. See [combined wake policy](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy).

### Channel

**Decided experiment, provisional name:** an ambient conversation space, separate from Group policy scope. **Proposed mechanics:** one owning Group, independent explicit/role-based membership, join-point history, and inbox delivery for structured mentions and eligible thread participation. Room, topic, space, or qualified “channel” remain naming alternatives. Claude MCP channels are a different harness transport. See [channels and membership](messaging-schema.md#channels-and-membership) and [conversation model](mental-model.md#conversations-within-the-authority-model).

### Circuit breaker

**Proposed:** a durable conversation-scoped control triggered by structural loop/storm signals. The integrated recommendation makes it quiet future wakes while preserving published history and pull access, with separate operator attention. It neither proves a semantic loop nor retracts already submitted native input. Hold is a separate escalation. See [combined wake policy](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy).

### Claim

Three distinct uses: **proposed request claim**, an atomic assignment by an eligible candidate; **proposed delivery-attempt ownership**, coordinating push/pull consumers; and **historical PoC file/work claims**, advisory coordination. None is an authorization grant. “Claim status” in wiki prose instead labels evidence or decision strength. See [requests](messaging-requests.md#codex-review), [leased receive](messaging-api.md#option-a-leased-receive-and-explicit-ack), and [historical questions](mental-model-poc.md#questions-the-destination-design-must-reopen).

### Claude MCP channels

A native harness push transport investigated in versioned research, not the product's ambient channel or generic MCP push. **Proposed adapters** may send hints or qualified bounded content after launch/readiness checks. Transport emission alone establishes neither receipt nor model input. See [conditional content push](messaging-delivery.md#conditional-content-push-candidate-claude-mcp-channels).

### Containment

**Proposed:** whether an operation's resource falls within a grant scope, modeled as `resource_within_scope(resource, scope, action_context)`. This is not necessarily a parent hierarchy: channels have owners, threads inherit parent scope, and cross-Group DMs need multi-scope policy. Containment does not supply the requested permission. See [installation, membership, and containment](participants-and-permissions.md#installation-membership-and-containment).

### Control plane

Responsibility for durable identity, lifecycle, policy, and reconciliation, rather than an automatic cloud service or separate process. Current agentd carries authority; cross-daemon centralized versus federated distribution remains **open**. The four-plane taxonomy is **historical PoC synthesis**, not four required destination services. See [identity authority options](group-peering.md#identity-authority-options) and [historical planes](mental-model-poc.md#the-system-has-four-planes).

### Conversation

**Proposed application model:** a DM or channel containing messages and rooted threads, with audience/history rules. A native harness conversation is separate resumable model history; several application conversations may feed one workload. Product conversation identity does not select the native runtime or confer workload authority. See [messaging schema](messaging-schema.md#logical-schema) and [adapter boundary](messaging-delivery.md#adapter-boundary-and-readiness).

### Coordinator

A scoped role for planning, dispatching, reviewing, and closing work; the functional description comes from the **historical PoC synthesis**. Current destination policy may permit a coordinator to request workloads within bounded delegation. It is not agentd, universal management authority, or the receiving Group's coordinator when acting remotely. See [role description](mental-model-poc.md#entities-and-identities), [supervisor contract](mental-model.md#what-the-supervisor-needs-to-support), and [receiving policy](group-peering.md#authorization-at-the-receiving-group).

### Credential cutoff

**Proposed, disputed bot semantics:** the sketches advance generation to reject old credentials, with fresh issuance requiring authorized enrollment. The preliminary review instead proposes reserving “cutoff” for generation advance plus enrollment invalidation, distinguishing it from rotation that retains enrollment. Neither compromise-recovery policy is decided. See [control routes](identity-api.md#candidate-control-routes) and [review IR-04](identity-preliminary-review-claude.md#p0-findings).

### Credential generation

**Proposed bot lifecycle:** an authenticated authority generation used to cut off earlier bot credentials. Ordinary rotation need not advance it; registration revocation blocks the entire bot, while installation revocation removes only particular grants. It is not a workload incarnation or an operator session. See [kind-specific lifecycle](participants-and-permissions.md#kind-specific-lifecycle-and-storage) and [identity invariants](identity-schema.md#invariants).

### Cursor

**Proposed, distinct senses:** a channel read cursor (`last_read_seq`) is a participant's monotonic declared read boundary; a page cursor selects another history page; an SSE event offset would support a separately designed replay contract. None is a delivery receipt or wake watermark. Historical bus delivery cursors should not be read as channel read declarations. See [channel catch-up](messaging-schema.md#channel-catch-up-and-read-cursors) and [SSE](messaging-api.md#waiting-transports-and-sse).

### Delivery

**Proposed:** one message's durable obligation/evidence for one recipient, keyed by message and participant. Ambient readers need no delivery row. `delivered_at` means acknowledged acceptance under receive A, recorded handoff under B, or qualified bot/adapter evidence; the choice is unresolved. Delivery is distinct from publication, wake, seen, reply, and successful downstream work. See [delivery evidence](messaging-schema.md#delivery-evidence).

### Delivery attempt

**Proposed:** an effort to hand content to a particular recipient through a selected mechanism, bound to current authority. A delivery token identifies leased attempt ownership under receive A; it is not an identity credential. Content-push attempts need durable unknown-outcome recovery; notification wake attempts may be transient. Lease expiry cannot undo external input. See [attempt records](messaging-delivery.md#attempt-records-and-observability) and [option A](messaging-api.md#option-a-leased-receive-and-explicit-ack).

### Dispatcher

**Proposed agentd responsibility:** coordinate receive and qualified push paths for participant delivery rows, avoiding competing consumption during unresolved content submission. It is not an independent message store. After-commit hints and restart reconciliation help it discover pending work; wake scheduling and delivery ownership remain distinct. See [delivery evidence](messaging-schema.md#delivery-evidence) and [delivery flow](messaging-data-flow.md#5-deliver-and-record-acceptance).

### DM (direct message)

**Decided conversation direction:** every participant gets every message. **Proposed mechanics:** a DM is identified by a unique immutable participant set, possibly larger than two and spanning Groups; all peers except the sender get delivery rows. It has no owning Group in the retained proposal. Mutable membership is an alternative; access still requires current policy. See [DM sets](messaging-schema.md#dms-and-participant-sets).

### Enrollment

**Proposed:** the authorized process establishing a controller/custody component's entitlement to obtain credentials for a particular registered participant and authority binding. Registration, issuance, activation, and enrollment are distinct steps. A socket path, native conversation ID, or installed client is not enrollment proof. Issuer and bootstrap mechanisms remain open. See [enrollment and custody](spiffe-mtls-authentication.md#enrollment-and-credential-custody) and [identity records](identity-schema.md#ownership-and-records).

### Envelope

**Proposed model-facing rendering:** agentd-authored provenance, audience, purpose, references, and completeness metadata surrounding a sender-controlled body. Text with per-render delimiters and JSON remain alternatives; the HTTP API's JSON contract does not settle CLI rendering. Sanitized labels and fences do not enforce model trust or turn bridge assertions into authenticated identity. See [envelope review](messaging-envelope.md#codex-review).

### Fan-out

**Proposed storage/routing distinction:** fan-out on write creates recipient delivery rows for DMs, mentions, and eligible channel-thread participants; fan-out on read exposes one stored message through authorized ambient history. It does not require duplicate message bodies, guarantee a wake per recipient, or make every channel reader an inbox recipient. See [messaging ownership](messaging-schema.md#ownership-and-scope) and [conversation illustration](diagrams/messaging-conversations.excalidraw.md#text-elements).

### Federation

**Open destination design:** cross-daemon trust/authority and messaging between independently managed scopes. SPIFFE federation specifically exchanges verification material across trust domains; it does not grant Group membership or operations. Sharing a host, Group name, or trusted issuer does not establish remote authority. See [identity authority options](group-peering.md#identity-authority-options) and [SPIFFE terminology](execution-isolation.md#spiffe-as-the-identity-foundation), whose deployment topology is deferred.

### Fencing

**Proposed lifecycle mechanism:** invalidate an obsolete authority binding so its processes, credentials, streams, and delayed events cannot act as or alter a successor. Workload incarnation fencing is terminal; ordinary credential renewal is not fencing. Revocation cannot undo already committed or dispatched effects. See [identity invariants](identity-schema.md#invariants) and [renewal, fencing, and recovery](identity-data-flow.md#renewal-fencing-and-recovery).

### Freeze

**Proposed messaging intervention:** reject sends and suppress future wakes at Group/host scope. An operator exception is proposed but must remain authenticated and scoped. Freeze is not workload termination, cannot retract queued native input, and has unresolved composition for ownerless cross-Group DMs. See [interventions](operator-oversight.md#graded-interventions) and [review](operator-oversight.md#codex-review).

### Grant

**Proposed authority record:** explicit permission for a participant in a specified scope, carried by an installation for bots. Scope and operation must match together; unrelated grants cannot be mixed into broader authority. Whether workload-role and operator permissions become installations is open. A grant is not an ability, membership, or new messaging identity. See [installation model](participants-and-permissions.md#installation-membership-and-containment).

### Group

**Decided:** a logical coordination, authority, and policy scope served by the host's agentd. It is not a conversation, VM, worktree, or isolation boundary. Lowercase “group” usually names the same concept, but the **historical PoC group** bundled worktree, runtime, sessions, context, and lifecycle. Current Group/Workspace cardinalities remain open. See [current boundary](group-peering.md#group-and-trust-boundary) and [historical aggregate](mental-model-poc.md#the-group-is-the-center-of-the-model).

### Harness

The native agent execution environment, such as Claude Code or Codex, retaining its tools, interaction, sandbox, and conversation recovery. It supports interactive Sessions and possibly headless Tasks; a harness name alone establishes no capability or protection guarantee. **Historical naming:** `agy` denotes the Antigravity CLI in this wiki. See [product focus](mental-model.md#the-product-focus), [historical entities](mental-model-poc.md#entities-and-identities), and [harness controls](supervisor-protection.md#harness-controls-and-gaps).

### Harness adapter

**Proposed:** trusted integration binding workload/incarnation to a native conversation and owning runtime, exposing qualified delivery, activity, or lifecycle evidence. An adapter's technical readiness is separate from permission to wake or inspect. It cannot choose another identity from sender-provided labels. See [adapter boundary and readiness](messaging-delivery.md#adapter-boundary-and-readiness).

### Hold

**Proposed:** accept a send privately for review, withholding publication, deliveries, ambient history, and wakes until authorized release. Release assigns a fresh public sequence and revalidates the frozen audience; discard retains a private disposition. An inbound-message hold does not by itself mediate a bot's outbound data export. See [publication mechanics](messaging-schema.md#requests-controls-and-publication) and [hold review](operator-oversight.md#codex-review).

### Host mode

**Decided initial backend:** native host execution using a trusted wrapper that keeps workload credentials outside the harness and authenticates upstream through X.509-SVID mTLS. The OS user is trusted; arbitrary same-UID tampering is outside the accepted threat model, while managed-harness boundary bypasses remain in scope. Integration is unverified. See [initial backends](spiffe-mtls-authentication.md#initial-backend-scope) and [host trust boundary](spiffe-mtls-authentication.md#host-mode-trust-boundary).

### Host scope

**Decided bot installation scope; proposed meaning:** resources under this agentd's authority, with explicit grants. “Host-wide” is not permission for every action, automatic membership/read access, or federation-wide reach. Host under future federation remains an open scope-composition question. See [installations and scope](group-peering.md#installations-and-scope).

### Idempotency key

**Proposed:** a stable caller-scoped key identifying one logical mutation and its normalized intent. For sends, `(sender_participant_id, client_message_id)` recovers the original acceptance without re-expanding roles; changed intent conflicts. Native queue correlation IDs and envelope nonces are not these keys. Retry retention and credential-issuance recovery have separate limits. See [immutable acceptance](messaging-schema.md#message-identity-and-immutable-acceptance) and [identity mutations](identity-api.md#mutation-and-failure-contract).

The preliminary review flags overloaded issuance `request_id`: audit correlation for secret-bearing responses versus possible replay for public certificates issued from the same signing request. This is an unresolved qualification, not a general exactly-once issuance promise. See [review IR-08/IR-09](identity-preliminary-review-claude.md#p1-findings).

### Inbox

**Proposed:** a logical participant's durable delivery view, consumed only under its current authorized binding. Resume does not create a new inbox; multiple installations do not duplicate it. Inbox rows cover DM peers, mentions, and eligible thread participants, not every readable ambient post. Native harness queues are separate. See [ownership](messaging-schema.md#ownership-and-scope), [participant identity](participants-and-permissions.md#participant-identity-and-kind), and [routing](messaging-schema.md#addressing-and-recipient-snapshots).

### Incarnation

**Proposed workload term:** a particular authorized execution binding beneath a durable workload identity, identified by `incarnation_id`. At most one is active; managed resume allocates a new one while preserving participant and role. It is not a PID, native conversation, certificate rotation, bot credential generation, or operator login session. See [identity invariants](identity-schema.md#invariants).

### Installation

**Decided bot scopes, proposed record:** a participant associated with host/Group scope, explicit grants, and revocation/audit state. It is neither a participant identity nor conversation membership. Elsewhere “installation-private CA” means the local product deployment's trust setup, and “installed version” means software installation; neither denotes this grant record. See [installation model](participants-and-permissions.md#installation-membership-and-containment) and [CA bootstrap](spiffe-mtls-authentication.md#docker-upstream-trust-investigation).

### Isolation boundary

The actual enforcement boundary protecting execution, files, credentials, or services under a qualified backend profile. It is not implied by a Group, Workspace, identity namespace, or runtime name. The dedicated microVM plus separate gateway boundary is a **deferred design**, not an initial backend requirement. See [execution/filesystem/policy separation](mental-model.md#keep-execution-filesystem-and-policy-separate) and [deferred topology](execution-isolation.md#deferred-topology).

### Launcher

**Proposed runtime responsibility:** present an interactive terminal or start a headless command after backend preparation. It is distinct from provisioning storage/authentication, terminal ownership, and actual harness lifetime. Capitalized “Launcher” does not yet establish a separate product primitive or executable. See [runtime contract implications](local-sandbox-runtimes.md#contract-implications) and [launcher validation](backend-validation-spikes.md#bv-08-runtime-and-launcher-lifecycle-with-storage).

### Lease

**Proposed, distinct uses:** a delivery lease temporarily reserves a receive attempt under option A; a workload-authority lease would bound stale execution authority. The latter lacks a selected renewal mechanism. The preliminary review proposes credential renewal as heartbeat instead, with separate sleep/wake policy. Neither lease duration nor credential expiry proves a process stopped. See [receive A](messaging-api.md#option-a-leased-receive-and-explicit-ack) and [review IR-10](identity-preliminary-review-claude.md#p1-findings).

### Lifecycle

**Proposed, kind-specific:** authoritative state transitions for workloads, bot registration/generation, and separately designed operator sessions. Workload running/suspended/terminated examples are not a finalized vocabulary or live presence observations. Message publication, request status, and intervention state have different lifecycles; “pause messaging” is not “suspend execution.” See [identity transitions](identity-data-flow.md#renewal-fencing-and-recovery) and [presence](messaging-api.md#presence).

### Membership

**Proposed conversation sense:** participation in a DM or channel, separate from installation grants and Group policy membership. Channel effective membership is the union of explicit and authorized role sources; removing one source may leave another. Admission intervals constrain history, and thread participation has its own routing meaning. See [channel membership](messaging-schema.md#channels-and-membership) and [authority separation](participants-and-permissions.md#installation-membership-and-containment).

### Mention

**Proposed:** a structured participant, Group-qualified role, or channel-wide selector resolved at acceptance under membership and permission checks. It adds inbox recipients without making the body private. Literal `@name` text is not a mention; channel-wide mention is a separately authorized fan-out. See [addressing and snapshots](messaging-schema.md#addressing-and-recipient-snapshots).

### Message

**Proposed persistence model:** one authoritative body and routing/provenance record, independent of its per-recipient deliveries and transport attempts. The proposed `kind` distinguishes ordinary `message`, structured `request`, and internal `notice`; these are not participant kinds. Authenticated authorship does not make the body trusted instructions. See [logical schema](messaging-schema.md#logical-schema) and [request/control additions](messaging-schema.md#requests-controls-and-publication).

### Mute

**Proposed messaging intervention:** reject a participant's future sends with an explicit policy error. It does not retract earlier accepted messages, revoke all identity, or stop the workload. See [graded interventions](operator-oversight.md#graded-interventions) and [review qualifications](operator-oversight.md#codex-review).

### Native conversation ID

The harness's own thread/session identifier for history, resume, and correlation. It is distinct from participant/workload identity and incarnation, and cannot confer their authority. The **obsolete** `(pid, session_id, role)` binding treated enrolled session identity differently; its automatic rebind proposal is not current guidance. See [supervisor contract](mental-model.md#what-the-supervisor-needs-to-support) and [supersession](peer-authentication.md#what-was-replaced).

### Notice

**Proposed:** restricted agentd template content, never a client-selected system sender or fourth participant kind. An inbox hint is an adapter control payload with no message/receipt. Persisted breaker notices are proposed ambient messages with no deliveries or wakes, explicitly including DMs. See [publication model](messaging-schema.md#requests-controls-and-publication) and [envelope review](messaging-envelope.md#codex-review).

### Operator

The human responsible for consequential choices and operating the system. The **proposed participant kind** represents that person in messaging; oversight and management require separate scoped authority. An authenticated operator message's instructional authority remains open, and receiving it does not approve a harness permission prompt. See [participation versus oversight](operator-oversight.md#participation-and-oversight-are-different-authorities) and [operator messages](operator-oversight.md#operator-messages-and-authority).

### Outcome

**Proposed structured-request sense:** a participant-reported `completed`, `declined`, or `failed` resolution, separate from receipts and sampled presence. It is not verified Task success; cancellation does not terminate linked work. Task execution outcome itself needs a backend result contract distinct from readiness and retained artifacts. See [request review](messaging-requests.md#codex-review) and [Task lifecycle](mental-model.md#task-lifecycle-and-backend-contracts).

### Oversight

**Proposed:** scoped management reads and interventions outside conversation participation. An oversight read creates no membership, delivery, receipt, or channel cursor advance; it produces separate audit evidence. Workload/bot delegation and operator installation unification remain open. See [oversight read](operator-oversight.md#oversight-read) and [review](operator-oversight.md#codex-review).

### Participant

**Proposed common messaging abstraction:** a stable `participant_id` with kind `workload`, `bot`, or `operator`, used for senders, recipients, membership, mentions, and cursors. Bots as distinct participants are decided; the complete three-kind abstraction and storage remain proposed. Thread “participants” means a routing subset, not additional identities. See [participant identity and kind](participants-and-permissions.md#participant-identity-and-kind) and [threads](messaging-schema.md#threads-and-membership).

### Pause

**Proposed messaging control:** reject conversation sends and suppress future wakes. Older phrases such as a breaker “pauses” a conversation's wakes mean quieting, which still permits sends/pull. Neither action suspends a workload; already submitted native input may execute. See [interventions](operator-oversight.md#graded-interventions) and [combined policy](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy).

### Peer and peering

Contextual collaboration language, not an additional participant kind. Current Group peering concerns coordination across authority scopes while preserving each sender's original scope. “Peer” in historical process authentication and native Claude peer sockets refers to different principals/transports; neither supplies current agentd identity. See [receiving policy](group-peering.md#authorization-at-the-receiving-group), [supersession](peer-authentication.md), and [native compatibility path](messaging-delivery.md#optional-compatibility-path-native-peer-socket).

### Permission

**Decided:** what policy allows a participant to do, distinct from capability. Conversation membership or a valid credential is insufficient by itself. Harness permission prompts/holds belong to the harness approval surface; a messaging grant or urgency flag cannot approve or bypass them. See [capabilities versus permissions](participants-and-permissions.md#capabilities-versus-permissions) and [fallback rules](messaging-delivery.md#fallback-and-uncertain-outcome-rules).

### Persistence

Separate retained things: process continuity while detached; native conversation history for resume; coordination records independent of a running harness; filesystem/artifact storage; and terminal screen/history for reconnection. The first taxonomy comes from **historical PoC synthesis** and is retained as a distinction, not a uniform backend guarantee. See [historical lifecycle](mental-model-poc.md#lifecycle-and-recovery), [Task contract](mental-model.md#task-lifecycle-and-backend-contracts), and [terminal contract](mental-model.md#terminal-attachment-and-ui-streaming).

### Presence

**Proposed advisory view:** authoritative workload lifecycle plus qualified, expiring reachability/activity observations. Live observations are proposed in-memory state; restart yields unknown. Presence is not a receipt, recipient filter, permission, or proof of ongoing focus. Bot reachability has separate semantics; operator presence is open and agent-declared availability is deferred. See [presence observations](messaging-schema.md#presence-observations).

### Principal

The authenticated actor whose current authority agentd evaluates. **Decided workload usage:** the managed principal underlying Session/Task. **Proposed common authenticator:** participant ID, kind, authentication method, credential, and kind-specific binding. An infrastructure enrollment principal must not accidentally become the application caller it represents. See [three primitives](mental-model.md#three-primitives), [self-inspection](identity-api.md#common-principal-and-self-inspection), and [upstream authentication](spiffe-mtls-authentication.md#upstream-mtls-and-authorization).

### Protection profile

**Proposed backend contract:** the requested and qualified execution restrictions and credential-custody guarantees for a particular harness/backend/configuration. Admission must establish the backend can enforce them; permission to launch cannot repair missing protection capability. Supported configuration is a condition of the claim, not proof all tool paths are confined. See [placement](mental-model.md#workload-placement-extensibility) and [configuration caveat](supervisor-protection.md#accepted-configuration-caveat).

### Publication

**Proposed:** making an accepted message visible in its authorized conversation and creating delivery obligations. With holds, publication occurs later at release and gets a fresh `seq`/`published_at`; `created_at` remains acceptance time. A held/discarded item has no public sequence. This distinction prevents catch-up cursors from skipping later releases. See [requests, controls, and publication](messaging-schema.md#requests-controls-and-publication).

### Quiet

**Proposed intervention:** preserve send acceptance, publication, and readable inbox/history while suppressing automatic wakes. “Delivered normally” in the original oversight table means normal obligations, not prefilled delivery receipts. Quiet may be indefinite operator policy; budget deferral is a different cause of delayed wakes. See [oversight review](operator-oversight.md#codex-review).

### Rate limit

**Proposed admission control:** reject excess new sends with retry guidance, unlike a wake budget that defers dispatch of already accepted work. Resolved fan-out can affect cost. An authorized retry recovers a previously committed acceptance before new-send controls; it is not a fresh send. See [send rate limits](messaging-loops-and-budgets.md#send-rate-limits) and [acceptance flow](messaging-data-flow.md#controls-and-requests-acceptance-flow).

### Reachability

**Proposed:** fresh, qualified evidence that a particular communication/delivery path is reachable, unreachable, or unknown. A live PID, running sandbox, or stale heartbeat is insufficient to claim a responsive harness. Reachability does not imply activity or permission; bot reachability is distinct from registration state. See [presence evidence](messaging-schema.md#presence-observations).

### Readiness

**Proposed, context-specific:** evidence that the relevant resources, authenticated execution binding, application, adapter, or tools are ready for their next operation. These gates differ: a connected MCP helper can lack tools, and a ready backend has not completed a Task. See [host launch](identity-data-flow.md#host-launch-and-first-request), [adapter readiness](messaging-delivery.md#adapter-boundary-and-readiness), and [Task contract](mental-model.md#task-lifecycle-and-backend-contracts).

### Receipt

**Proposed:** agentd-recorded evidence for a recipient/message milestone: queued, delivered, seen, or explicitly replied. These are not one guaranteed linear progression; a reply may be known without a seen observation. Null means missing applicable evidence, whereas bot seen is not applicable. Cursor advances, presence, hints, and transport writes are not receipts. See [delivery evidence](messaging-schema.md#delivery-evidence) and [status](messaging-api.md#status-and-waiting).

### Recipient snapshot

**Proposed:** the concrete deduplicated delivery set resolved under policy at acceptance, excluding the sender. Later roles/membership do not backfill recipients; retries retain the original set. Holds freeze an intended set and revalidate it at release; structured requests derive candidate eligibility from declared recipients, not ambient readership. See [addressing](messaging-schema.md#addressing-and-recipient-snapshots) and [publication](messaging-schema.md#requests-controls-and-publication).

### Redaction

**Proposed logical removal:** hide/remove body copies in controlled views/stores while retaining a tombstone's identity, position, and reply/root references. It is not verified secure erasure or retraction of external transcripts/exports. Receipt history is only a lower bound on exposure. Retention of retry fingerprints and cached envelopes remains open. See [retention and redaction](messaging-schema.md#retention-and-redaction-open-decision) and [oversight review](operator-oversight.md#codex-review).

### Registration

**Proposed identity state:** authoritative recognition of a participant and kind, distinct from enrolling credentials or granting an installation. A valid issuer signature for an unregistered identity is insufficient. Bot registration revocation disables all its activity while preserving historical attribution; revoking one installation is narrower. See [identity invariants](identity-schema.md#invariants) and [kind-specific lifecycle](participants-and-permissions.md#kind-specific-lifecycle-and-storage).

### Relay

**Proposed bot operation:** inbound relay introduces externally sourced content under authenticated bot identity; outbound relay exports content and needs separate source/destination egress authority. Read permission is not export permission. Transport relays in host/remote connectivity are another sense and require their own identity-preservation contract. See [bridge provenance](participants-and-permissions.md#bridge-permissions-and-provenance) and [local caller authentication](spiffe-mtls-authentication.md#local-caller-authentication).

### Reply

**Proposed:** an accepted message explicitly referencing another with `reply_to_id`. `message reply` privately targets the original sender's DM; `thread reply` uses the root's parent audience. Sharing a thread is not a reply receipt. Ambient responders can create reply relationships without manufacturing original delivery rows. `expects_reply`/`reply_by` express intent, not enforcement. See [replies and expectations](messaging-schema.md#replies-and-expectations).

### Request

**Proposed structured coordination:** a `kind: request` message plus claim/outcome state when fulfillment needs another participant's judgment. It differs from a free-text message with `expects_reply`, an HTTP/API operation agentd can authorize directly, and a headless Task execution. A request grants no authority; inclusion in the first experiment is open. See [requests versus operations](messaging-requests.md#requests-versus-api-operations) and [request kind](messaging-requests.md#the-request-kind).

### Resume

**Proposed managed workload operation:** preserve durable participant/role, fence obsolete authority, and activate a new incarnation with separately restored native state. Native conversation resume restores harness history; terminal reattachment reconnects to a surviving process. None alone proves process-memory recovery or permits automatic replay after unknown external effects. See [identity recovery](identity-data-flow.md#renewal-fencing-and-recovery) and [runtime distinctions](local-sandbox-runtimes.md#contract-implications).

### Role

Provisioned workload identity data, immutable for that workload in the **current authentication design**; current Group policy determines permitted operations. A role name is scoped, not universal authority. **Proposed role selectors** resolve trusted assignments for membership/addressing; general participant IDs do not automatically assign roles to bots/operators. See [upstream authorization](spiffe-mtls-authentication.md#upstream-mtls-and-authorization) and [installation model](participants-and-permissions.md#installation-membership-and-containment).

### sbx

Docker Sandboxes, a **decided initial backend target**. The proposed adapter uses sandbox-scoped runtime credential injection of JWT-SVIDs over TLS while agentw holds a placeholder. It is not synonymous with generic Docker containers, a custom agentgw sidecar, or a verified isolation guarantee. See [initial scope](spiffe-mtls-authentication.md#initial-backend-scope) and [runtime-mediated JWT authentication](spiffe-mtls-authentication.md#runtime-mediated-jwt-authentication).

### Scope

The authority/resource domain to which a grant or policy applies; bot installation scopes are currently host and Group, with projects/collections undesigned. A conversation audience and an execution isolation boundary are different concepts. Wiki `scope/destination`, `scope/bridge`, and `scope/poc` tags instead classify design provenance, not runtime permissions. See [installation scopes](participants-and-permissions.md#installation-membership-and-containment) and [project relationship](README.md#how-the-two-projects-relate).

### Seen

**Proposed workload receipt:** qualified evidence that a specific message entered model-turn input, not that it was understood or acted on. Pull and notification-only profiles may never provide it; a generic turn event, successful hint, or cursor advance is insufficient. Bot seen is not applicable; operator receipt semantics remain open. See [delivery evidence](messaging-schema.md#delivery-evidence).

### Session

**Decided:** an interactive harness session whose lifecycle and identity the product manages. Detaching does not turn it into a Task. Native harness “session” may instead mean resumable conversation history, even for a Task; an operator login session is another authority binding. **Historical PoC Session** also included operator shells. See [three primitives](mental-model.md#three-primitives), [operator path](identity-data-flow.md#bot-and-operator-paths), and [historical entities](mental-model-poc.md#entities-and-identities).

### Shared context

**Historical/PoC:** briefs, memory, decisions, claims, status, and roster, with code-adjacent knowledge in files and live coordination proposed in the bus. Current **proposed Group standing context** is a small versioned document for newcomers, separate from conversation membership and message history. Neither textual context nor a brief grants permission. See [historical state ownership](mental-model-poc.md#state-has-explicit-owners) and [standing context](group-peering.md#group-standing-context-future-work).

### SPIFFE ID

An identity URI within a trust domain, not a credential, address, or permission. Current participants propose separate exact registered paths for workloads, bots, and operators; layout and operator enrollment remain open. SPIFFE's broad technical “workload” also includes infrastructure, unlike this product's managed agent workload. See [participant kinds](participants-and-permissions.md#participant-identity-and-kind) and [technical identity reference](workload-architecture.md#identity-and-authorization), without inheriting its deferred topology.

### SPIFFE Workload API

The standard credential-delivery API, distinct from agentw's application endpoint and the proposed agentd control/issuance API. Its technical name does not turn a bot using it into a product workload. Issuer integration is open; a custom socket delivering credentials is not automatically this standard API. See [enrollment and custody](spiffe-mtls-authentication.md#enrollment-and-credential-custody) and [bot authentication](spiffe-mtls-authentication.md#participant-classes-and-bot-authentication).

### Supervisor

Trusted orchestration/control responsibility, principally agentd with protected launch, credential, and terminal-control components. Protecting it includes state and authority, not just keeping a PID alive. In **historical/deferred research**, a local guest supervisor or runtime vendor supervisor has a different placement; those names do not set current topology. See [protection requirement](supervisor-protection.md#the-requirement) and [current components](spiffe-mtls-authentication.md#components-and-request-path).

### Suspension

**Proposed workload lifecycle term with unresolved mechanics:** the identity sketches describe suspend as fencing the expected incarnation and conditionally clearing its active pointer; the earlier authentication lifecycle places fencing at resume. The preliminary review recommends a terminal fence on suspend, with a new incarnation on resume, versus a possible nonterminal suspended state. Do not infer process termination solely from authority loss. See [identity transitions](identity-data-flow.md#renewal-fencing-and-recovery), [earlier lifecycle](spiffe-mtls-authentication.md#launch-rotation-suspension-and-resume), and [review IR-02](identity-preliminary-review-claude.md#p0-findings).

### SVID

SPIFFE Verifiable Identity Document asserting a SPIFFE ID. **Decided authentication forms:** X.509-SVID with proof of private-key possession over mTLS, or audience-bound JWT-SVID bearer over server-authenticated TLS. A private key and verification bundle are separate material; valid credentials still require current registration, binding, and permission. See [mTLS](spiffe-mtls-authentication.md#upstream-mtls-and-authorization) and [JWT path](spiffe-mtls-authentication.md#runtime-mediated-jwt-authentication).

### Task

**Decided:** a headless harness execution, requested and observed programmatically; other execution backends may follow. A long-running Task or one awaiting input is still a Task. It is not a planning issue/work item, structured messaging request, or synonym for every native harness conversation. Lifecycle/result details remain proposed. See [three primitives](mental-model.md#three-primitives) and [Task contract](mental-model.md#task-lifecycle-and-backend-contracts).

### Terminal owner

**Proposed backend responsibility:** retain the existing harness PTY across UI disconnection and provide output, dimensions, and reconnectable screen/history. It is distinct from the UI renderer, attachment transport, isolation runtime, and durable conversation transcript. Tmux, shpool, and runtime facilities are candidates, not universal dependencies. See [terminal attachment and streaming](mental-model.md#terminal-attachment-and-ui-streaming).

### Thread

**Decided experiment:** discussion inside a DM or channel. **Proposed mechanics:** `thread_root_id` names a top-level message; nested replies retain that root and use `reply_to_id` for the exact answer. DM audience is inherited; channel participation follows eligible authors/repliers/mentions. Earlier standalone thread membership/lifecycle is a retained alternative, not the active recommendation. Native Codex threads are separate harness conversations. See [threads and membership](messaging-schema.md#threads-and-membership) and [adapter binding](messaging-delivery.md#adapter-boundary-and-readiness).

### Trust domain and bundle

Technical identity terms used by the design: a trust domain is an issuer-backed SPIFFE namespace; its bundle contains public verification material. Neither is a Group, host, or isolation boundary, and the bundle is not a workload's private key or certificate chain. Service TLS trust, X.509 identity verification, and JWT verification have distinct purposes. See [identity storage/trust](identity-schema.md#storage-and-trust-boundaries) and [retained technical reference](execution-isolation.md#spiffe-as-the-identity-foundation).

### Turn

A native harness unit of model work, separate from an application thread, message, delivery, or Task lifetime. **Proposed measurement:** correlate qualified inputs and native turn IDs; one wake may cover several messages, and busy-turn input need not start a new turn. Trigger evidence does not prove continuing focus. See [experiment measures](messaging-experiments.md#what-to-compare) and [presence evidence](messaging-schema.md#presence-observations).

### Urgency

**Proposed scheduling intent:** `normal|urgent`, policy-authorized and included in send retry comparison. It changes timing of existing wake-eligible delivery obligations, not recipients, receipts, or authority. Urgency cannot create an ambient delivery, bypass hard suppression/permission holds, resume compute, or silently change Codex queueing into steering. See [combined policy](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy) and [harness timing](messaging-delivery.md#wake-timing-and-urgency).

### Wake

**Proposed adapter action:** prompt an eligible workload to process input or check its inbox. Notification-only wake acceptance is not application delivery; content injection has separate receipt requirements. A wake can join a busy turn, wait, or fail, so it is not necessarily one new turn. “Wake” of a bounded waiter or laptop sleep/wake is a different sense. See [delivery starting design](messaging-delivery.md#proposed-starting-design) and [measurement](messaging-experiments.md#what-to-compare).

### Wake budget

**Proposed:** limit automatic wake attempts per recipient and applicable Group scopes while retaining accepted messages and pending deliveries. It differs from send rejection and from measured token/turn cost. Coalescing charges one attempt per recipient/scope, not each message; thresholds, urgent reserves, cross-scope composition, and restart accounting remain open. See [combined wake policy](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy).

### Worker

A workload role/addressing example for delegated work, not a separate infrastructure primitive or synonym for every participant. The wiki has no canonical fixed worker duty/permission set. `worker-token` is a proposed trusted credential resolver command, not worker-role authority. External Agent Substrate “Workers” means physical compute and is prior art only. See [identity example](identity-api.md#common-principal-and-self-inspection), [resolver](identity-commands.md#lifecycle-integration-and-protected-resolver), and [prior-art distinctions](mental-model.md#lessons-from-ax-and-agent-substrate).

### Workload

**Decided:** the managed principal underlying a Session or Task. **Proposed mechanics** connect its durable identity, assigned role, Group policy, and active incarnation. Capitalized “Workload” in the deferred architecture is the same product usage; SPIFFE's technical workload is broader. Bots and operators are not agent workloads merely because all can be participants. See [three primitives](mental-model.md#three-primitives) and [kind-specific identity](participants-and-permissions.md#kind-specific-lifecycle-and-storage).

### Workspace

**Decided:** the filesystem in which an execution boundary runs. It is not the runtime, Group, private harness state, or necessarily a repository worktree. Instance versus reusable preparation specification, sharing, persistence, and Group cardinality remain open. AX's broader setup/tool Workspace is prior art, not an alias. See [execution/filesystem/policy separation](mental-model.md#keep-execution-filesystem-and-policy-separate) and [AX comparison](mental-model.md#lessons-from-ax-and-agent-substrate).

## Unresolved terminology questions

These choices remain with the owning pages and operator; recommendations already integrated there are not new glossary decisions.

| Question | Concrete choices and source ownership |
| --- | --- |
| What should the ambient space be called? | Keep product **channel** while qualifying Claude MCP channels, or choose **room**, **topic**, or **space**. See [conversation terminology](mental-model.md#conversations-within-the-authority-model). |
| What does “delivered” promise? | Choose receive A's acknowledged acceptance or B's recorded handoff; retain separate bot, adapter, and still-undesigned operator semantics. Neither proves seen/understood. See [receive alternatives](messaging-api.md#receive-alternatives). |
| Does a DM belong to a Group? | The participant handoff's Group-owned wording conflicts with the retained ownerless cross-Group proposal. Choose ownerless multi-scope composition or explicitly revise ownership; also decide immutable participant sets versus mutable audiences. See [containment conflict](participants-and-permissions.md#installation-membership-and-containment) and [DM alternatives](messaging-schema.md#dms-and-participant-sets). |
| Is installation a universal grant abstraction? | Keep bot installations with separate workload-role/operator policy adapters, or unify them. Decide bot ambient permission-plus-membership versus permission-only access, and whether non-workloads can receive role assignments. See [installation model](participants-and-permissions.md#installation-membership-and-containment) and [ambient bot access](participants-and-permissions.md#ambient-bot-access). |
| Which scope issues authority? | Choose federated daemon, centralized, or central-enrollment/local-authority peering; define host-wide grants and budgets across hosts/multiple policy scopes. A Group need not be a trust domain. See [authority options](group-peering.md#identity-authority-options) and [budget composition](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy). |
| What is an operator message's authority? | Ordinary participant content, authenticated user direction, or coordination authority without harness approval power. Operator session/enrollment and receipt semantics also need their own contracts. See [operator messages](operator-oversight.md#operator-messages-and-authority) and [operator authentication](spiffe-mtls-authentication.md#operator-surface-authentication-proposal). |
| What objects do Workspace and role names commit us to? | Choose filesystem instance, preparation specification, or both, and Group/Workspace cardinalities. Coordinator remains a role in current usage; a durable coordinator entity and fixed worker responsibilities are not established. See [Workspace questions](mental-model.md#keep-execution-filesystem-and-policy-separate) and [historical coordinator question](mental-model-poc.md#questions-the-destination-design-must-reopen). |
| What does thread participation imply? | Retain rooted/inherited or implicit participation versus explicit thread controls/following; decide history grants for late entrants. Choose explicit channel read advancement versus list-and-advance without equating either with seen. See [threads](messaging-schema.md#threads-and-membership) and [read cursors](messaging-schema.md#channel-catch-up-and-read-cursors). |
| How much does a request status assert? | Decide first-experiment inclusion, claim release/reassignment, bot eligibility, and candidate-decline semantics. Preserve the review's distinction between reported completion and verified work, and between trigger evidence and “working on it.” See [request alternatives](messaging-requests.md#should-requests-be-in-the-first-experiment) and [review](messaging-requests.md#codex-review). |
| What do unknown cause, quiet, and pause mean operationally? | Reconcile original zero-depth wording with null unknown evidence and define multiple-trigger aggregation. Keep quiet as wake suppression, pause as send blocking, and hold as nonpublication; choose breaker escalation and bounded urgency exceptions explicitly. See [combined wake policy](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy) and [oversight review](operator-oversight.md#codex-review). |
| Which lifecycle/binding terms become contractual? | Finalize workload states and authenticated incarnation binding, separately from bot generations and operator sessions; choose issuer/bootstrap and stale-authority bounds. The credential-digest mapping is a candidate, not a selected wire contract. See [binding gate](identity-schema.md#authenticated-binding-is-an-implementation-gate) and [identity API open contracts](identity-api.md#open-contracts-and-provenance). |
| Does suspend always fence, and does cutoff revoke enrollment? | Reconcile suspend-as-terminal-fence versus a nonterminal suspended state, and bot generation-only cutoff versus cutoff requiring re-enrollment. Credential renewal as heartbeat versus an explicit authority lease also changes sleep/wake recovery. See [identity review IR-02/IR-04](identity-preliminary-review-claude.md#p0-findings) and [IR-10](identity-preliminary-review-claude.md#p1-findings); these are new review proposals, not accepted revisions. |
| Which identity does each agentctl mode use? | Choose explicit operator/controller principal separation within one executable or separate wrapper/resolver packaging. Resolve where operator grants live pending installation unification; distinguish credential-issuance correlation from ordinary mutation replay. See [identity review IR-05](identity-preliminary-review-claude.md#p0-findings) and [IR-06/IR-08](identity-preliminary-review-claude.md#p1-findings). |
| What is a complete envelope, and what survives redaction? | Choose model-facing text versus JSON and a bounded full-content retrieval contract. Retain logical redaction rather than implying secure erasure; define body, tombstone, audit, and retry-evidence retention together. See [envelope review](messaging-envelope.md#codex-review) and [central retention decision](messaging-schema.md#retention-and-redaction-open-decision). |

## Crawl coverage

Reviewed on 2026-09-28: all **31 source content pages** present at the closing inventory (27 at the initial inventory plus the concurrently added Claude identity review and three Excalidraw Markdown pages), plus README for navigation/authority and AGENTS.md for conventions only. The filesystem inventory included hidden/ignored paths and pages not directly indexed by README; the historical authentication archive and new review were read in full, as were the diagrams' text and drawing records. The review remains proposed commentary alongside its owning pages, and the diagrams defer to their source pages. Instruction files supplied no domain definitions. No live PoC behavior was inferred or sibling files consulted.

| Page reviewed | Authority and contribution |
| --- | --- |
| [README](README.md) | Authority map, current versus historical interpretation, project boundary. |
| [Backend validation spikes](backend-validation-spikes.md) | Proposed bridge input; qualification, lifecycle, readiness, and terminal contracts. |
| [Messaging architecture diagram](diagrams/messaging-architecture.excalidraw.md) | Proposed illustration subordinate to messaging data flow; component, authority, and storage labels. |
| [Conversation model diagram](diagrams/messaging-conversations.excalidraw.md) | Proposed illustration subordinate to messaging schema; Group policy, fan-out, ambient history, and thread audiences. |
| [Send-to-delivery diagram](diagrams/messaging-send-to-delivery.excalidraw.md) | Proposed simplified hint-path illustration; acceptance/delivery/seen distinctions, not a universal hint-only adapter contract. |
| [Execution isolation](execution-isolation.md) | Superseded/deferred topology; retained identity terminology and isolation distinctions. |
| [Group peering](group-peering.md) | Decided Group/host boundary; proposed cross-scope authority and standing context. |
| [Identity API](identity-api.md) | Proposed application/control split, principals, registration, enrollment, and mutations. |
| [Identity commands](identity-commands.md) | Proposed agentw/agentctl split and protected worker-token resolver. |
| [Identity data flow](identity-data-flow.md) | Proposed kind-specific launch, activation, fencing, and recovery. |
| [Claude preliminary identity review](identity-preliminary-review-claude.md) | Concurrent draft review; competing binding, suspend/cutoff, principal, grant, lease, and retry meanings. |
| [Identity schema](identity-schema.md) | Proposed records, authority bindings, and generation distinctions. |
| [Identity threat model](identity-threat-model.md) | Trust assumptions; attribution versus intent, authority versus availability. |
| [Local sandbox runtimes](local-sandbox-runtimes.md) | Research; backend/Launcher, attachment, and credential-mediation distinctions. |
| [Destination mental model](mental-model.md) | Accepted primitives and product direction; open relationships and backend contracts. |
| [Historical PoC mental model](mental-model-poc.md) | Pinned historical synthesis; old group aggregate, role descriptions, planes, and persistence. |
| [Messaging API](messaging-api.md) | Proposed receive/ack alternatives, inspection, waits, and interface meanings. |
| [Messaging commands](messaging-commands.md) | Proposed audience-sensitive commands, retry identity, and output semantics. |
| [Messaging data flow](messaging-data-flow.md) | Proposed acceptance/publication, delivery, recovery, and control ordering. |
| [Harness delivery](messaging-delivery.md) | Versioned research and proposed wake/content adapters, evidence, and native-ID distinctions. |
| [Message envelope](messaging-envelope.md) | Competing rendering proposals, notice kinds, and trust/completeness qualifications. |
| [Messaging experiments](messaging-experiments.md) | Decided comparison direction; proposed measurement, wake/turn and outcome distinctions. |
| [Loops and budgets](messaging-loops-and-budgets.md) | Proposed limits, budgets, breakers, causal evidence, and review counterproposals. |
| [Structured requests](messaging-requests.md) | Proposed assignment, claims, outcomes, Task links, and unresolved rollout. |
| [Messaging schema](messaging-schema.md) | Conversation direction and proposed persistence, routing, receipts, cursors, and presence. |
| [Operator oversight](operator-oversight.md) | Proposed participation/management distinction, interventions, attention, and redaction. |
| [Participants and permissions](participants-and-permissions.md) | Decided bot/capability distinctions; proposed kinds, installations, containment, and provenance. |
| [Peer-authentication notice](peer-authentication.md) | Current supersession boundary for PID/native-session authority. |
| [Peer-authentication archive](peer-authentication-historical.md) | Historical authority tuples, per-boundary topology, and PoC gateway/monitor senses. |
| [SPIFFE authentication](spiffe-mtls-authentication.md) | Accepted initial backends/authentication; proposed custody, enrollment, and binding mechanisms. |
| [Supervisor protection](supervisor-protection.md) | Accepted configuration caveat and research vocabulary for qualified protection. |
| [Workload architecture](workload-architecture.md) | Superseded/deferred component senses and technical identity reference. |
