---
title: Identity API
summary: "Proposed application identity inspection and separate control interfaces for enrollment, lifecycle, grants, and credential issuance."
type: design
status: draft
tags:
  - area/identity
  - area/security
  - scope/destination
updated: 2026-09-28
---

**Proposed initial sketch, 2026-09-27:** Routes and payloads are design candidates, not implemented endpoints or the standard SPIFFE Workload API. [SPIFFE authentication](spiffe-mtls-authentication.md) owns the authentication direction; [schema](identity-schema.md) and [data flow](identity-data-flow.md) define the proposed bindings and transitions. [Commands](identity-commands.md) maps the operator and workload surfaces; [threat model](identity-threat-model.md) records qualification gates.

## Surface separation

| Surface | Caller and authentication | Allowed responsibility |
| --- | --- | --- |
| Application HTTPS | Workload wrapper or runtime proxy; registered bot with either supported SVID mechanism | Scoped application operations and inspection of the caller's own identity. No issuance or management proxy. |
| Local workload gateway | Kernel/process binding to a managed host workload | Fixed allowlist of application routes under the wrapper's workload authority. |
| Authorized control interface | Authenticated operator or narrowly enrolled infrastructure; bootstrap still open | Registration, provisioning, lifecycle, policy changes, and specifically entitled issuance. |
| Browser UI backend | Authenticated human session mapped to an operator | Scoped operator operations; per-human audit and session revocation. Browser holds no SVID. |

`/control/v1` below is a logical route namespace on the separately protected control interface, not an application-listener prefix that workloads can reach. A Unix-socket pathname or installed CLI is not authentication. Infrastructure enrollment authority does not imply operator policy authority. **Proposed mode separation after IR-05:** issuance accepts only the enrolled custody/controller principal, including a separately attested bot custody component. An operator principal manages enrollment and revocation but cannot call issuance as a shortcut; wrapper/resolver modes cannot load or fall back to operator credentials. This is application-level least privilege, not isolation from a trusted OS user.

The proposed shared application listener accepts exactly one method: validated X.509-SVID mTLS or a JWT-SVID bearer token over validated server TLS. Reject both, neither, and invalid presented credentials; never fall back from an invalid client certificate to JWT. Certificate rejection may occur during TLS negotiation before an HTTP error exists. Separate listeners remain an option if runtime compatibility requires them, with the same authorization rules.

## Common principal and self-inspection

Authenticators produce a server-internal value with `participant_id`, `kind`, `spiffe_id`, `authentication_method`, verified `binding_evidence` (`credential_ref` only for candidate A), kind-specific `authority_binding`, and credential expiry. Authorization reads current registration and policy; a principal is not a permanent permission snapshot. The [credential binding gate](identity-schema.md#authenticated-binding-is-an-implementation-gate) must be resolved before this value can be trusted.

`GET /v1/identity` returns a safe, side-effect-free view of the authenticated caller. It takes no participant selector and returns no credential, key location, enrollment handle, or infrastructure identity. Example workload response:

```json
{
  "participant_id": "participant-17",
  "kind": "workload",
  "authentication_method": "x509_svid",
  "authority_binding": {"kind": "workload", "incarnation_id": "incarnation-42"},
  "group_id": "group-build",
  "role_id": "worker",
  "authority_revision": 8
}
```

A bot response substitutes its generation and omits workload Group/role fields. Operator shape awaits its identity path. This reports the effective upstream principal; it does not certify complete sandbox confinement or list all resource permissions. Existing [messaging routes](messaging-api.md) consume the same principal without adding caller-supplied identity fields.

## Candidate control routes

All reads require appropriate visibility permission. IDs select targets, never prove entitlement. Mutations require authorization for the action and target; issuance has a narrower controller/enrollment check.

| Method and route                                        | Proposed input and effect                                                                                                                                          |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `GET /control/v1/identities/{participant_id}`           | Return registration, safe binding status, revisions, and visible installation metadata.                                                                            |
| `POST /control/v1/workloads/{workload_id}/incarnations` | Provision/resume an already authorized workload; `backend`, `expected_revision`, `request_id`. Reserve a preparing incarnation; never override its immutable role. |
| `POST /control/v1/incarnations/{id}/enrollment`         | Bind an entitled controller and allowed method to that reserved incarnation; bootstrap evidence remains issuer-specific.                                           |
| `POST /control/v1/incarnations/{id}/activate`           | `expected_revision`, qualified execution/readiness evidence, `request_id`; conditionally activate.                                                                 |
| `POST /control/v1/incarnations/{id}/suspend`            | `expected_revision`, reason, `request_id`; fence this incarnation, never its successor.                                                                            |
| `POST /control/v1/enrollments/{id}/credentials`         | `method`, optional public-key request where supported, `issuance_id` for correlation; derive identity, binding, audience, and lifetime from authorized enrollment policy.           |
| `POST /control/v1/bots`                                 | Register a distinct bot participant with no implicit grants; `request_id` and display metadata.                                                                    |
| `POST /control/v1/bots/{id}/enrollment`                 | Enroll the registered bot under selected attestation/custody; no workload-launch entitlement.                                                                      |
| `POST /control/v1/bots/{id}/credential-cutoff`          | Proposed generation advance plus invalidation of all prior enrollments; old credentials lose authority. Fresh issuance requires separately authorized re-attestation.                                          |
| `POST /control/v1/bots/{id}/revoke`                     | Conditional registration revocation across all installations; retain historical attribution.                                                                       |
| `POST /control/v1/installations`                        | `participant_id`, host/Group scope, explicit grants, `request_id`; initially bot installations only. Grantor must be entitled to delegate every grant.             |
| `POST /control/v1/installations/{id}/revoke`            | Conditional revocation of this grant set only.                                                                                                                     |
| `GET /control/v1/identity-events`                       | Scoped, paginated audit metadata; never credential payloads.                                                                                                       |

The [canonical incarnation state table](identity-schema.md#lifecycle-and-policy-records) owns activation, suspension, and retirement semantics. Operator grant storage remains an interim proposal; no management grant is inferred from operator kind.

Initial workload creation/role assignment stays with the workload-management design; this sketch consumes those records instead of inventing a second launch API. Credential renewal uses the same enrollment route with a fresh issuance request, preserving the binding. A preparing enrollment can obtain only the credentials needed for its authorized bootstrap; application access still waits for activation. The sbx resolver requests tokens only for active incarnations.

Credential responses travel only to the entitled custody component on the protected interface. JWT responses carry `token` and `expires_at`; X.509 responses carry the chain and required verification material, with local key generation versus protected key delivery still open. Treat these responses as secrets: no generic logging, UI rendering, or ordinary JSON diagnostic output. Issuer-specific exchange and standard Workload API delivery are alternatives to this broker proposal, not assumed compatible implementations.

## Mutation and failure contract

Ordinary mutations carry `request_id` and, for existing targets, `expected_revision`. Authenticate and authorize first, then look up `(actor, request_id)` before testing the expected revision. Compare normalized route, target, and intent: identical retries return the recorded outcome after current authorization; changed intent conflicts. Creation uses the same actor/key namespace without a preexisting target. Only a new request evaluates the revision and performs the conditional mutation. Retention must cover the documented retry window; its duration is open. Commit the state change and audit event together. Resume, activation, and fencing use the same workload revision so racing controllers cannot activate two incarnations. A late suspend for an old incarnation may report its terminal state but cannot mutate a successor.

For secret-bearing issuance, `issuance_id` is audit correlation, not a replay guarantee. Issuance retries require separate care: retain nonsecret issuance metadata rather than storing a raw JWT in generic retry records. If a credential response is lost, reconcile its issuance status and perform fresh authorized issuance when needed; do not claim exactly-once issuance. With local key generation, a separate CSR-bound idempotency key could safely replay a public certificate chain for identical CSR and intent, after current authorization; key delivery would not share that guarantee. This favors CSR custody without selecting it. A fence racing with issuance may leave a validly signed but unusable credential, which live authorization must reject.

| Status | Candidate code | Caller behavior |
| --- | --- | --- |
| `400` | `invalid_request`, `ambiguous_authentication` | Correct the request; do not retry with weaker authentication. |
| `401` | `invalid_credential`, `credential_expired` | Reauthenticate through the authorized custody path. |
| `403` | `forbidden`, `incarnation_inactive`, `registration_revoked` | Stop; a different target/name/header cannot restore authority. |
| `404` | `not_found` | Missing or undisclosed target; avoid identity enumeration. |
| `409` | `revision_conflict`, `idempotency_conflict`, `incarnation_changed` | Reconcile state and original intent before retrying. |
| `503` | `issuer_unavailable`, `authority_unavailable` | Bounded retry; deny when current authority cannot be established. |

Application mutations recheck authority at acceptance; reads and streams recheck before releasing further protected data. Expiry or revocation requires reauthentication/reconnection as applicable and cannot be bypassed by keeping TLS alive. Exact stream closure bounds and in-flight-effect treatment follow the [lifecycle flow](identity-data-flow.md#renewal-fencing-and-recovery).

## Open contracts and provenance

Bootstrap authentication, attestation payloads, leases, issuer selection, authenticated generation encoding, operator login/session/delegation routes, and trust-root administration are intentionally unresolved. General-purpose impersonation, credential export to workloads, and cross-host enrollment are not part of this sketch. The routes are new Codex synthesis from the source wiki on 2026-09-27; qualify workload contracts through BV-03/BV-04/BV-07 and add separately scoped bot/operator checks before implementation acceptance.

**Review integration, 2026-09-28:** Revised against [Claude’s preliminary review and Codex disposition](identity-preliminary-review-claude.md#codex-reconciliation). Corrections and new recommendations remain proposed; no issuer, bootstrap, liveness policy, or operator installation model is selected.
