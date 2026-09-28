---
title: Identity schema
summary: "Proposed identity records, kind-specific authority bindings, credential metadata, and authorization invariants."
type: design
status: draft
tags:
  - area/identity
  - area/security
  - scope/destination
updated: 2026-09-28
---

**Proposed initial sketch, 2026-09-27:** This logical schema develops [SPIFFE authentication](spiffe-mtls-authentication.md) and [Participants and permissions](participants-and-permissions.md); it is not a database migration or an accepted issuer design. The decided host-wrapper mTLS and sbx-mediated JWT paths share participant authorization. Bots have separate custody and lifecycle; operator enrollment remains open. See [data flow](identity-data-flow.md), [API](identity-api.md), [commands](identity-commands.md), and [threat model](identity-threat-model.md).

## Ownership and records

Agentd owns registration, workload authority, installations, and authorization decisions. The selected issuer owns issuance and verification material; its storage is not prescribed here. The wrapper/runtime adapter owns local execution evidence. These records refer to existing workload, Group, role, and participant objects rather than creating a parallel identity registry for messaging.

```text
participants(
  participant_id PK, kind, identity_registration_ref, created_at
)
workload_authority(
  participant_id PK/FK, workload_id UNIQUE/FK, group_id, immutable_role_id,
  registration_state, active_incarnation_id NULL, revision
)
workload_incarnations(
  incarnation_id PK, participant_id FK, backend, state,
  enrollment_id, execution_binding_ref, liveness_policy_ref NULL,
  created_at, activated_at NULL, fenced_at NULL
)
bot_authority(
  participant_id PK/FK, registration_state, credential_generation, revision
)
operator_authority(
  participant_id PK/FK, registration_state, session_binding_ref, revision
)
operator_grants(                           -- interim proposal, not selected
  grant_id PK, participant_id FK, scope_kind, scope_id,
  explicit_grants, state, revision
)
enrollments(
  enrollment_id PK, participant_id FK, authority_binding,
  controller_ref, allowed_credential_methods, state, revision
)
credential_bindings(                       -- candidate A only
  credential_ref PK, enrollment_id FK, method, verified_credential_digest,
  audience NULL, issued_at, expires_at
)
installations(
  installation_id PK, participant_id FK, scope_kind, scope_id,
  explicit_grants, state, revision
)
trust_profiles(                            -- protected configuration
  profile_id PK, purpose, trust_domain NULL, public_material_ref,
  expected_service_id NULL, expected_dns_names, revision
)
identity_events(
  event_id PK, occurred_at, actor_binding, subject_id, action,
  expected_revision, resulting_revision, request_id, outcome, reason_code
)
```

`authority_binding` is a tagged value: workload incarnation, bot credential generation, or an operator binding whose concrete shape is still undesigned. `controller_ref` identifies authenticated infrastructure authorized to enroll that specific binding; it is not the represented application principal. `execution_binding_ref` points to protected process-instance evidence or an immutable sandbox binding, never just a PID or display name. Capability evidence remains in the participant model and does not grant permission.

The operator record is a placeholder for a separately qualified human-session/local-credential mapping, not a claim that workload enrollment supports operators. Installations initially describe bot grants; workload roles and operator permissions remain separate policy adapters until their unification is decided. Reuse the [messaging schema's](messaging-schema.md#participants-and-authorization) participant identity and acceptance-time attribution; do not copy conversation membership into identity grants.

## Invariants

- A participant has exactly the detail record appropriate to its registered kind. Match the authenticated trust domain and full SPIFFE path against that record; namespace examples remain proposals.
- A workload has at most one active incarnation. Its provisioned role is immutable for that identity; role changes require a new authorized identity. Resume keeps the participant and role, but allocates a new incarnation.
- Preparing an incarnation permits only its scoped bootstrap; application requests require active authority. Fencing is terminal for that incarnation. Suspend fences the expected incarnation and clears the active pointer only if it still names that incarnation.
- Ordinary credential renewal preserves the authority binding. The proposed bot cutoff advances its generation and invalidates existing enrollments, requiring separately authorized re-attestation; registration revocation blocks all activity; it does not fabricate a workload incarnation. Re-registration cannot silently restore grants or callbacks.
- Every credential binding belongs to its enrollment's participant and authority generation. Authenticated old credentials cannot be rebound to the current generation by looking up the participant's latest state.
- Grant scope and permission must match together. Host scope means this agentd's resources; it is not a wildcard action or federation permission. Unknown cross-Group DM composition is denied pending design.
- Lifecycle, grant, and audit mutations use conditional revisions and durable transactions. Historical IDs remain attributable after revocation; opaque participant and SPIFFE path identifiers are never reassigned to another actor or authority generation.

## Authenticated binding is an implementation gate

**Revised after [Claude IR-01/IR-13](identity-preliminary-review-claude.md), all candidates proposed:** Compare the following mechanisms before selecting an issuer integration. None permits a caller header or a stable subject lookup to select the latest authority generation.

| Candidate | Binding and compatible delivery | Cost or unresolved constraint |
| --- | --- | --- |
| A: Credential digest registry | A digest of each verified leaf or complete JWT resolves to an immutable enrollment/binding; agentd brokers every issuance. | Durable per-credential state; record before delivery, not atomically with activation. Direct issuer delivery without prior authoritative registration is incompatible. |
| B: Authority-scoped SPIFFE path | An exact registered path embeds the workload incarnation or bot generation; both SVID formats can carry it. | Changes the stable-SPIFFE-ID proposal, requires issuer registration/attestation updates and cutoff races to be qualified. Direct delivery is a candidate only if old enrollment cannot obtain the successor path. |
| C: Issuance-time watermark | Compare authenticated issuance times with a stored cutoff. | Backdating, clock steps, timestamp granularity, and missing claims make this unsuitable as the initial recommendation. |
| D: Private JWT binding claim | A signed, collision-resistant claim identifies the authority binding. | Producer/consumer agreement required; JWT-only, so X.509 still needs another mechanism. No custom certificate extension is selected. |

**Documented, checked 2026-09-28:** JWT-SVID requires `sub`, `aud`, and `exp`; `jti` is permitted but not required, and validators need not track its uniqueness. Candidate A therefore proposes a unique issuance identifier such as `jti` plus collision rejection; never remap an existing digest across generations. Additional claims require interoperability agreement. [JWT-SVID specification](https://github.com/spiffe/spiffe/blob/main/standards/JWT-SVID.md).

**Inference:** Equal claims and deterministic signing can yield identical token bytes across a rapid cutoff, so signature validity alone cannot establish generation uniqueness. Test this with the selected issuer rather than relying on signature randomness. The inspected specification lists RSA and ECDSA algorithms, not Ed25519; Claude's generic Ed25519 example is not adopted as a JWT-SVID recipe.

Candidate B examples are `/workloads/<id>/incarnations/<id>` and `/bots/<id>/generations/<id>`. The X.509-SVID specification permits exactly one URI SAN; the epoch would be part of that SPIFFE ID, not a second identity SAN. [X.509-SVID specification](https://github.com/spiffe/spiffe/blob/main/standards/X509-SVID.md). Stable messaging identity remains `participant_id`; registration maps exact full paths to it, never loose prefixes. `identity_registration_ref` represents whichever registration scheme is selected; stable `spiffe_id UNIQUE` applies only to candidates that preserve one ID per participant.

For A, durably insert the digest-to-enrollment mapping before releasing a credential, derive its binding from the immutable enrollment, and check activation separately on each application use. Test all issuer-exposed bypass paths, not just broker success. Unknown digests fail closed after restart; recover authoritative mappings or issue fresh credentials through valid enrollment rather than assigning old credentials to current state. Measure sbx issuance, resolver spawning, persistence, and cleanup costs; do not equate one row with a mandatory fsync per request without checking transaction behavior.

Claude favors B first; Codex supports comparing B and A against the same cutoff/recovery fixtures, without selecting either. Direct Workload API compatibility is an integration gate, not a consequence of path syntax alone. Test resumed TLS sessions for preserved authenticated binding, expiry, and live revocation; no TLS-stack behavior is assumed. BV-03/BV-07 must settle this before backend acceptance.

## Lifecycle and policy records

**Proposed canonical incarnation state table, reconciling IR-02:**

| State | Application authority | Allowed transition |
| --- | --- | --- |
| `preparing` | None; only separately entitled bootstrap | `active` on authorized readiness; `fenced` on abandon, cancellation, or a selected preparation timeout. |
| `active` | Requires valid credential, live binding, and policy | `fenced` on suspend, observed exit, retirement, or a selected liveness policy's cutoff. |
| `fenced` | None; terminal | No reactivation; resume creates a new incarnation. |

Workload registration is `active` or `retired`, independently of execution. Retirement fences its incarnations and blocks new preparation/enrollment; IDs and history are retained. Resume ensures every predecessor is fenced, including when its exit report was lost; already-fenced predecessors need no second transition. Group reassignment and cross-backend resume are unselected: this sketch defines neither an in-place Group change nor automatic backend migration. Any future backend change must use a new incarnation and its backend's authentication method while preserving stable attribution.

The interim `operator_grants` shape gives scoped permissions a proposed storage home without choosing installation unification. [Oversight](operator-oversight.md#participation-and-oversight-are-different-authorities) originally proposes operator installations; that remains the alternative, not an accepted host-wide default. Operator authentication/session shape is still open. `allowed_credential_methods` is an explicit set: enabling both bot methods is possible in the sketch, not implicit; requests still present exactly one. Bot cutoff covers both methods and every old enrollment.

Keep enrollments separate for now because enrollment entitlement and application authority have different revoke/re-attest transitions, not to speculate about multiple controllers. Each enrollment binds immutably to one authority generation; re-attestation creates a new record. Candidate A's credential rows derive that binding and have no independent cutoff field/API. Trust profiles can be protected configuration rather than database tables.

**Proposed serialization:** Keep authority/grant changes and messaging acceptance in agentd's same SQLite transaction domain, using the single-writer serialization already proposed for messaging. Acceptance checks live authority within that transaction. A separate store would need an equally explicit ordering protocol; a preflight RPC check is insufficient. This is a storage recommendation, not a requirement supplied by SPIFFE.

## Control bootstrap and liveness choices

Controller entitlement is enforced least privilege within the intended system and protects against misconfiguration and confused deputies. It is not isolation from arbitrary trusted same-UID processes; managed-code exclusion depends on qualified confinement of control endpoints and enrollment material. Candidate bootstrap choices are authenticated OS peer evidence plus a one-use nonce delivered through a protected inherited descriptor, issuer-native attestation, or a protected per-controller credential. Socket permissions alone do not distinguish same-UID controllers. The sbx resolver needs a host-resident protected binding/credential; bot enrollment material similarly needs custody and revocation beyond SVID rotation. No candidate is selected.

The `liveness_policy_ref` is a placeholder, not an implemented lease. Compare explicit controller heartbeats/leases with renewal-informed reconciliation. Renewal is credential-service contact, not proof of harness liveness; an idle sbx workload may make no token requests. Credential expiry always denies that credential but does not alone specify terminal fencing. Laptop sleep/wake, clock discontinuities, stale-authority bounds, and automatic continuation versus explicit resume remain operator choices. If leases are selected, define their renewal interface and expiry policy before implementation.

## Storage and trust boundaries

No private key, raw JWT, enrollment secret, or human session secret belongs in messaging rows, ordinary audit events, workspaces, or diagnostic output. Credential metadata and public bundles still need integrity and access control. Private keys live in protected issuer/wrapper/bot storage according to the custody profile; key generation versus delivery remains open.

Keep trust profiles for workload X.509 verification, JWT verification, wrapper verification of agentd's service identity, and conventional HTTPS server CA/name verification distinct. The Docker guest's proxy trust is another boundary. Sharing an implementation or CA does not collapse these purposes. Persist the installation server CA across restart; missing established CA state requires recovery rather than silent replacement.

Live connections keep a principal plus its binding and credential deadline, but cannot cache an unlimited authorization grant. Restart must restore durable fences and registrations before serving; uncertain liveness needs reconciliation. Liveness timing, audit retention, digest retention, policy invalidation, trust-root rollover, and issuer integration remain open. Audit records establish attributable operations, not the human intent behind them.

## Provenance

The source pages above own accepted direction and earlier participant proposals. Record names, revisions, credential-digest binding, and transaction rules here are Codex synthesis requested on 2026-09-27. Qualification maps to [BV-03, BV-04, and BV-07](backend-validation-spikes.md); bot/operator extensions require additional bounded tests. No implementation, schema execution, or security test was performed.

**Review integration, 2026-09-28:** Revised against [Claude’s preliminary review and Codex disposition](identity-preliminary-review-claude.md#codex-reconciliation). Corrections and new recommendations remain proposed; no issuer, bootstrap, liveness policy, or operator installation model is selected.
