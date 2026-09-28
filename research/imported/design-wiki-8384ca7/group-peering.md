---
title: Groups and peering
summary: "Group and host authority scopes, cross-Group conversation proposals, and requests that never grant authority."
type: design
status: draft
tags:
  - area/orchestration
  - area/identity
  - area/messaging
  - scope/destination
updated: 2026-09-27
---

Claim status: **decided direction**: Groups coordinate and authorize workloads across workspaces. The earlier one-daemon-per-Group topology was replaced on 2026-09-27 by the workload architecture; one external agentd may manage multiple Groups. Identity authority and peering mechanics remain open.

**Current scope, 2026-09-27:** [Host mode and Docker Sandboxes](spiffe-mtls-authentication.md#initial-backend-scope) are the initial targets. Workload requests use SPIFFE credentials and shared agentd authorization. Cross-daemon trust and group peering below remain separate design questions; the bespoke microVM/sidecar profile is deferred.

## Group and trust boundary

A Group is a logical coordination and authorization scope; one `agentd` may serve several Groups. Its workloads have authenticated identities and assigned roles, and its policy governs their operations. The [destination mental model](mental-model.md) distinguishes interactive Sessions, headless Tasks, and Workspaces; Sessions and Tasks are workloads under the current authentication contract.

**Decided in the operator's 2026-09-27 discussion, via Claude's handoff:** One agentd per host; Groups are authority/policy scopes, not conversation spaces or isolation boundaries. Different hosts may have different daemons; creating a Group on one host does not create another daemon. Their host placement does not itself create an isolation boundary. The earlier PID-only authentication topology is [obsolete](peer-authentication.md); the current host wrapper uses SPIFFE upstream.

**Proposed:** Keep durable group identity separate from a daemon process incarnation and an isolation-boundary identity. A restart should not silently create a new group, and sharing a host should not merge groups. Recovery and lifecycle fencing still require a concrete contract.

## Three groups on one clone

The operator's example has workloads on worktrees A and B and a merge Group C on the clone's main worktree. **Claude proposal from the 2026-09-27 conversation-model discussion:** Create a `merges` channel owned by C, admitting C's merger role and the coordinator roles from A and B through explicitly Group-qualified dynamic membership rules. On one host all are served by its agentd; future hosts require a separate federation design.

Coordinators post readiness ambiently; they mention C's merger role when they need inbox delivery, or reply in a rooted discussion with its eligible participants. Channel-wide mentions require C's policy authority because they wake many workloads and spend model turns. A request to merge remains attributable peer content; C decides what work to launch. Posting or membership grants no merge authority, filesystem access, or C-local coordinator role. Admit foreign roles in their original scope, preserving the receiving-policy invariant below.

**Proposed alternative:** Use a fixed-participant DM for work needing every message in each participant's inbox. Each recipient's own Group policy must permit the sender; there is no owning Group for the DM. This illustrates the [conversation experiment](messaging-experiments.md), not a selected coordination winner. Default-channel creation, dynamic membership, join-point history, and mention snapshots remain mechanics for review.

Channels are a plausible future unit for cross-daemon federation. **Prior art, not a design decision:** Matrix synchronizes room state/history among participating homeservers through federation. [Matrix specification](https://spec.matrix.org/latest/). No Matrix protocol, replicated state model, or eventual-consistency requirement is adopted here; the initial single-host experiment does not qualify federation.

**Codex integration of Claude's structured-request proposal, 2026-09-27:** In the three-worktree example, a coordinator from A or B can post a `kind: request`, `assignment: any` message in C's `merges` channel, explicitly addressing eligible merger participants through its qualified role. A merger claims under C's policy and replies with a reported outcome, optionally linking a separately authorized Task. [Requests](messaging-requests.md) coordinate judgment; they never grant repository, lifecycle, merge, or cross-Group authority. Ambient readers are not automatically claim candidates. Whether this enters the first experiment remains open.

## Installations and scope

**Decided — operator discussion on 2026-09-27, recorded in Claude's handoff:** Bots may be installed into a Group or host-wide. Groups and host need not be the only scopes; projects and collections are undesigned future possibilities. Bridges are bots whose installations carry bridging permissions, not a distinct principal kind. Capability describes ability, not a Group-policy grant.

**Claude proposal:** An installation associates a participant with `(scope_kind, scope_id)` and explicit permissions. Conversation membership is separate. Host-wide means resources controlled by this agentd, with listed grants and operator-visible audit; it does not mean every operation or automatic access to every channel. Host-wide semantics under federation remain open. Foreign bot identities retain their original kind/scope just as foreign workload roles do.

[Containment](participants-and-permissions.md#installation-membership-and-containment) is a resource/scope/action function, not a presumed single-parent hierarchy. Channel scope follows its owner; thread scope follows its parent. Cross-Group DMs remain ownerless in the current proposal and require a defined multi-scope authorization contract, not arbitrary assignment to one Group. Collections may eventually overlap; this is design insurance against an unknown, not a requirement to build a graph now.

Unifying workload roles as Group installations and the operator as an explicit host installation is a conditional recommendation if broader workload scopes are expected; it adds abstraction and is not selected. Bot ambient reads still compare permission-plus-membership with permission-only access; recommend the former for visible participation without deciding it. Outbound relay is a separate egress permission, and inbound external authors remain bot assertions rather than local authority.

## Identity authority options

[SPIFFE workload authentication](spiffe-mtls-authentication.md) establishes the workload principal at agentd. Cross-daemon group authentication must additionally establish which group scopes a remote daemon may represent. A PID and a caller-supplied group name cannot answer that question across a service boundary.

The options below concern cross-daemon authority distribution, not whether workload requests use SPIFFE. They remain design alternatives, not selected implementations:

| Model | Basis for trusting a remote sender | Main design obligation |
| --- | --- | --- |
| Federated daemon identity | The recipient trusts an enrolled remote daemon to attest identities within its group | Define trust introduction, issuer scope, key replacement, and revocation between groups |
| Centralized identity | A control-plane authority defines group and peer identities, with daemons acting under delegated authority | Define delegation, revocation, and what remains usable when the authority is unavailable |
| Central enrollment with local peer authority | The control plane enrolls group daemons; each daemon enrolls and attests its own peers within an authorized scope | Define exactly which membership and role decisions are local and which require central approval |

The third option is a possible division of responsibility, not a decision to combine every mechanism. Even the centralized variant needs trustworthy backend workload enrollment, while federation can still use a common discovery service or operator UI. A control plane may itself run on the laptop; centralized identity does not imply a hosted cloud dependency.

Identity authority and message transport are separate choices. Direct daemon-to-daemon messaging can use centrally established trust. Messages routed through a common service can retain federated identities. Broker placement should not silently decide who may issue identities.

The [current SPIFFE authentication design](spiffe-mtls-authentication.md) supplies the workload identity foundation; cross-daemon authority choices do not revive PID-only authentication. A logical Group need not be a SPIFFE trust domain; federation is relevant when independently administered identity authorities need to establish trust.

## Authorization at the receiving group

**Proposed invariant:** The receiving group authorizes the remote identity in its original scope. For example, `group A / peer X / coordinator` is not the merge group's coordinator. Identical role names do not imply identical authority or inherited membership.

The sender's daemon should derive sender identity and role from the authenticated workload principal and current policy. The receiving daemon must authenticate the issuing authority, establish its permitted group scope, and apply local policy to the requested operation. Authentication must bind identity to the message and destination; a remote group must not be able to relabel a forwarded request as a locally originating peer request.

Candidate message provenance includes issuing daemon/group identity, peer identity, immutable bound role, execution or binding generation, and message identity. The exact envelope, freshness rules, credential mechanism, delivery semantics, and treatment of forwarded messages remain open. Group policy should separately decide whether a remote group can send messages, subscribe to information, request work, or perform a more privileged operation.

Multiple groups on one unisolated host may share a compromise domain even with separate credentials. The logical issuer scope remains useful for correct authorization and attribution, but protection of one group's keys from another needs actual enforcement rather than a namespace convention.

## Shared host services

The earlier mandatory shared Codex app server per isolation boundary is obsolete. Host mode must qualify the selected harness launch topology and local gateway attribution; it does not require reviving a shared-server architecture. If an adapter uses a shared service, it must demonstrate workload separation and protect management access under [BV-01/BV-02](backend-validation-spikes.md). Group federation does not solve that local binding problem.

## Group standing context future work

**Future work proposed by Claude's second thread/presence review, 2026-09-27:** Separate standing facts from conversational messages: a small current Group-level document maintained by an authorized coordinator or operator and supplied to newcomers on Group join. Examples include "the merge group owns main" and "do not touch migrations". This may reduce repeated context in [channel add briefs](messaging-schema.md#channels-and-membership), but is not a conversation membership change or an accepted feature.

Authority to edit, versioning/freshness, join-time delivery, recovery after missed updates, size limits, and read policy remain open. A document describes operating context; its text cannot itself grant permissions or replace agentd policy. No schema, endpoint, or CLI is specified yet. This records the review's recommendation, not an operator decision or tested behavior.

## Decisions still needed

Choose who introduces trusted groups and who may issue peer identities and roles. Decide whether already enrolled groups must continue messaging or launching peers while the control plane is unavailable, and how revocation behaves during that interval. Define the receiving group's authorization policy for the three-worktree example before selecting credentials or transport.

The accepted Group definition, multi-Group daemon scope and three-worktree use case come from the operator's 2026-09-27 discussion. The identity alternatives, separation of transport from authority, and proposed recipient-policy rules are wiki synthesis for further discussion. No peering or isolation experiment was run for this page.

The operator's 2026-09-27 discussion, handed off by Claude, decided one agentd per host and the DM/ambient-channel/thread experiment. The merges-channel, foreign role admission, and cross-Group DM mechanics are Claude proposals; Codex synthesized the example and federation qualification. Earlier identity-authority alternatives remain open.

The operator's 2026-09-27 participant/authority discussion, handed off by Claude, decided bots as distinct messaging participants, both SPIFFE authentication mechanisms, Group/host installation scopes with future scopes possible, bridges as bot installations with bridging permissions, and capabilities distinct from permissions. The participant/installation mechanics are Claude proposals; Codex's kind-specific lifecycle, containment, and evidence qualifications are linked from [Participants and permissions](participants-and-permissions.md). Issuer/enrollment, first bot delivery paths, ambient membership, workload installation unification, and host-wide federation meaning remain open.

The 2026-09-27 pre-review integration carries Claude's loop/budget, oversight, request, and envelope proposals into this page with labeled Codex synthesis. All new mechanics remain proposed. Operator message authority, request inclusion in the first experiment, every control threshold, and earlier messaging/participant open decisions remain unresolved; see the four source pages linked from [the index](README.md). No implementation or new harness probe was performed.
