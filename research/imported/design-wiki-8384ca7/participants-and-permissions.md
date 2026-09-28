---
title: Participants and permissions
summary: "Participants, SPIFFE identity, bot installations and bridging grants, and the distinction between capabilities, permissions, membership, and scope."
type: design
status: draft
tags:
  - area/identity
  - area/security
  - area/messaging
  - scope/destination
updated: 2026-09-28
---

**Decided — operator discussion on 2026-09-27, recorded in Claude's participant/authority handoff:** Bots are messaging participants distinct from agent workloads. They have their own SPIFFE identities and authenticate using X.509-SVID mTLS or JWT-SVID bearer tokens over server-authenticated TLS. Bots can be installed into a Group or host-wide; future projects or collections may become scopes but are undesigned. Every bridge is a bot whose installation includes bridging permissions; bridge is not a separate participant kind. Capabilities describe what a participant can do, while permissions describe what policy allows.

**Proposed mechanics:** Claude's workload/bot/operator participant abstraction, identity namespaces, installation model, custody, lifecycle, and delivery contracts below are not additional operator decisions. [Authentication](spiffe-mtls-authentication.md), [messaging schema](messaging-schema.md), and [delivery](messaging-delivery.md) apply this model. The operator remains a first-class messaging participant in this proposal, without implicitly giving every operator message management authority.

The [identity schema](identity-schema.md) sketches these kind-specific records and authority bindings; the [identity API](identity-api.md) separates registration, enrollment, and installation control from application operations. Their proposed mechanics do not decide workload/operator installation unification or operator enrollment.

## Participant identity and kind

Use a stable `participant_id` for senders, recipients, memberships, DM participant-set keys, structured mentions, read cursors, presence targets, and event actors/subjects. Proposed kinds are `workload`, `bot`, and `operator`. A workload participant maps to a managed Session/Task; a bot is installed integration software; an operator represents a person in conversation. Installations are grants to a participant, not additional messaging identities. Multiple installations do not duplicate that participant's inbox or rewrite a sender.

Propose distinct SPIFFE paths under the selected trust domain: `/workloads/<id>`, `/bots/<id>`, and `/operators/<id>`. Exact namespace and operator enrollment remain open. Derive kind only after validating the SVID and matching its exact path structure and registered ID; no request field, display name, asserted author, or arbitrary prefix match can override it. Both authenticators yield `(participant_id, kind, authentication_method, current_authority_binding)`. A valid issuer signature alone is insufficient: registration, lifecycle, grants, resource access, and revocation still apply. Internal service identities do not become messaging participants by accident.

## Kind-specific lifecycle and storage

| Representation | Tradeoff | Recommendation |
| --- | --- | --- |
| Nullable kind-specific columns | Simple joins but many invalid combinations require checks. | Reasonable for a small initial migration. |
| Participant base plus per-kind detail records | Explicit lifecycle ownership and room for operator/bot differences; extra joins. | Codex recommends for the canonical model. |

Proposed logical records are `participants(id, kind, spiffe_id, capability_record)`, workload details with workload binding/active incarnation, bot details with registration state and credential generation, and operator details with an as-yet-unspecified authenticated session/credential binding. Require exactly the appropriate kind detail; reject mismatched namespaces and records. Message and receipt provenance can use nullable kind-specific snapshots with constraints: workload incarnation only for workloads, bot credential generation only for bots, and a separately designed operator binding. Do not invent operator or bot workload incarnations.

Workload suspension/resume and incarnation fencing stay as designed. Bots use registration revocation and credential cutoff, including existing streams and pending webhook attempts. Rotation alone need not revoke registration; define generation cutoff independently from token/certificate expiry. The [identity sketch](identity-schema.md#lifecycle-and-policy-records) now proposes cutoff invalidating prior enrollments as well, requiring independently authorized re-attestation rather than letting a stolen enrollment obtain the successor generation. This remains a proposal, not a new decision. Revoking one installation removes only its grants; other applicable installations may still authorize an action. Revoking the bot registration blocks all its activity regardless of remaining memberships. Removing memberships versus keeping them inert is open; preserve historical attribution either way. Re-registration must not silently reactivate grants or stale queued callbacks.

## Installation, membership, and containment

**Claude proposal:** An installation records a participant, `(scope_kind, scope_id)`, explicit permission grants, and revocation/audit state. Today scope kinds are host and Group. Host means this agentd's authority domain, not every machine or future federation peer. Host-wide still lists permissions and appears in audit and the operator installation view; it is not an implicit wildcard grant.

Membership is participation in a DM or channel. Installation makes an operation eligible; conversation membership and history policy can impose additional constraints. Neither membership alone nor a working SPIFFE credential grants read, post, mention, management, or outbound-relay permission. Grants must be evaluated for the actual operation and resource, not combined into a broader scope by mixing unrelated permissions from different installations.

**Codex qualification of the handoff:** Its statement that DMs belong to Groups conflicts with the earlier proposed ownerless cross-Group DM. Retain the latter until decided otherwise. A channel has an owning Group; a channel-thread inherits that scope. A DM and its threads have participant-associated policy scopes, not one invented owning Group. Recommend requiring all relevant participant-side policy checks for cross-Group DM operations; a Group-scoped bot grant must not automatically cover a DM merely because one member belongs to that Group. Explicit cross-Group authorization and operator/host-only participant cases need a defined composition rule before they are enabled.

Containment should be a function such as `resource_within_scope(resource, scope, action_context)`, not a parent-pointer walk. For a local channel, evaluate its owner; for a thread, its parent; for a DM, the applicable multi-scope policy contract above. Host containment covers this agentd's resources, but never substitutes for the requested permission. Unknown resource/scope combinations fail closed until defined. Non-hierarchical projects/collections are design insurance, not established requirements: a Group might eventually occur in several collections, and future federation may cross hosts.

| Authority-model choice | Benefit and cost | Recommendation |
| --- | --- | --- |
| Unify workload roles and operators as installations | One grant model; workload role becomes Group-scoped role-derived grants, operator can have explicit host grants. Adds an abstraction to every authorization path. | Conditionally favor if workloads gain project/collection scopes; operator has not selected it. |
| Keep workload role policy separate; use installations for bots | Smaller immediate change; more than one policy adapter must produce consistent authorization. | Viable if broader workload scopes are not needed. |

Until chosen, both map to a common authorization decision; references to installations do not silently migrate workload provisioning. Role remains authoritative provisioned identity data under the current workload design, not a bot-supplied claim. Whether role membership can include bots/operators needs an explicit assignment policy; participant generalization does not enroll them into workload roles.

## Ambient bot access

Two alternatives remain open: require both installation read permission and explicit/effective channel membership, or let an installation read grant authorize ambient access without membership. Claude leaned toward membership; Codex recommends it for the first experiment so a host-wide bot visibly joins the channels it reads and uses the existing admission/cursor rules. Permission-only reading would need an explicit history boundary and auditable subscriptions rather than borrowing a nonexistent join point. Host-wide scope alone is never read permission. DM access still requires the relevant participant relationship and policy.

## Capabilities versus permissions

Intrinsic capabilities come from harness, model, backend, or installed bot implementation: push wake, message-specific seen evidence, interactive/headless execution, shell/MCP support, tool-output limits, image input, webhook/stream delivery, thread handling, or outbound-relay implementation. Restrictions can narrow them, such as shell disabled, read-only runtime, blocked runtime egress, or removed tools. A bot implementing outbound relay still needs a separate egress permission.

**Claude's proposed classification rule:** Ask who enforces the restriction. A harness/runtime/backend restriction narrows capability even if the operator chose it; an agentd authorization check is permission. Shell disabled is capability; forbidding channel-wide mentions is permission. Linux capabilities and named protocol capability declarations retain their external technical meanings; they are not installation grant names.

Trusted launch profiles, backend controls, bot installation qualification, and adapters provide capability records with source, evidence level (`documented`, `observed`, `verified`, or explicitly unknown), version, and restrictions. Participant self-assertions cannot qualify an ability. Effective operations require both a qualified capability and applicable permission; unsupported, unqualified, and forbidden are distinct results. Capability versions normally change with a workload launch/incarnation or a bot implementation/profile change; permission changes can take effect during execution. Health/readiness remains live evidence rather than a static capability promise.

Delivery selects a qualified mechanism and then checks permission. A pull-only workload must be reported as lacking automatic wake support even for a DM. Presence exposes only the signals a kind/adapter can supply. Delegation can expose candidate shell/tool/image capabilities under visibility policy. Admission checks that the backend can enforce the requested protection profile before launch; permission to launch cannot supply a missing backend capability.

## Bots, credentials, and delivery

**Decided authentication; proposed custody:** An operator-installed bot may hold its own SVID and private key and obtain credentials through a standard SPIFFE Workload API if the chosen issuer/deployment provides one. This is deliberately looser custody than an untrusted agent workload's wrapper/proxy. It does not make bot message content trusted. If agentd brokers issuance, bot registration/enrollment must be separate from workload launch provisioning. Issuer, attestation, enrollment, renewal, and operator credentials remain open.

External services outside the installation's trust domain are proposed to connect through a local bridge bot. The bridge validates their own authentication, such as a webhook signature, then acts under its bot SVID. **Codex qualification:** Those services are not enrolled to hold these SVIDs in this design; this is a trust/deployment boundary, not a universal claim that remote software could never use SPIFFE. No external account name is converted into a local operator principal.

Bots have no harness wake adapter. Candidate paths are agentd-to-bot webhooks or bot-initiated pull/stream subscriptions. Delivery means a qualified successful webhook response or explicit programmatic acknowledgment of a pulled/streamed message, not merely writing bytes or opening SSE. Support order, retries, callback authentication, and acknowledgment protocol remain open. Bot `seen` is not applicable, distinct from unknown workload seen evidence; presence reports reachability, not model activity. Operator delivery/read acknowledgment needs separate design and is not assigned bot or workload semantics.

## Bridge permissions and provenance

A bridge is a bot installation with explicit bridging grants. Candidate grants are inbound relay with asserted authorship and outbound relay; they are separate permissions. Plain bots may send under their own identity but cannot set asserted-author fields without the inbound grant. Reject an unauthorized asserted author instead of stripping it. Check authority over the destination/resource at acceptance and outbound dispatch.

Always store/render the authenticated bot participant separately from `asserted_external_author` opaque metadata. The bridge owns external identity mapping; agentd neither verifies nor normalizes those identities. A display may say “bridge B asserts Tony in #eng,” never “authenticated operator Tony.” Authenticated CI messages can contain attacker-written PR descriptions or test output; their body, external labels, and links remain untrusted peer content and can inject instructions into agent contexts.

Outbound relay is data egress and requires its own explicit permission over the source and destination. Operator installation views should show outbound destinations and grants. Reading a channel or receiving a DM is not permission to export it. Revocation must prevent future sends on existing subscriptions; data already exported cannot be retracted by that check.

Propose `originating_bridge_participant_id` plus a namespaced external message ID, with the authenticated bot retained as sender. Agentd assigns the originating bridge from the principal for a new inbound relay; preservation across additional trusted hops needs an explicit protocol. Bridges remember mapped origin/external IDs and skip their own echoes. **Codex synthesis:** One marker only addresses simple self-echo, not every multi-bridge cycle; qualify deduplication/hop policy and persist bridge-side retry identity. These markers are untrusted provenance, never permission. R5 observed a sender-supplied `hop-chain` attribute whose loop-detection purpose was inferred, not tested as a guarantee. [Pinned Claude peering report, R5](https://github.com/tbhb/agent-orchestration-poc/blob/0d04ae5facd63448e278a08be68ce54922e6c994/research/imported/agent-peering-tests/CLAUDE_CODE_PEERING.md).

## Provenance and open decisions

The operator's 2026-09-27 discussion, recorded by Claude, decided bots as non-workload participants, their two SPIFFE authentication mechanisms, Group/host installation scope with future scopes possible, bridges as permissioned bot installations, and capabilities distinct from permissions. Claude proposed the participant kinds and mechanics. Codex added the recommended per-kind records, ownerless-DM containment qualification, grant-composition cautions, operator lifecycle boundary, and loop-limit qualification as synthesis.

Open: issuer and bot/operator enrollment; first bot delivery paths; membership versus installation-only ambient reads; workload/operator installation unification; multi-scope DM containment; host-wide meaning under federation; and all earlier conversation, receive/ack, presence, output, pagination, byte-limit, harness-delivery, urgency, and naming choices. No live enrollment, credentials, bots, services, or PoC changes were involved in writing this page.
