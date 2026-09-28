---
title: Identity threat model
summary: "Initial identity assets, adversaries, trust boundaries, abuse cases, and qualification gates for host and sbx backends."
type: design
status: draft
tags:
  - area/identity
  - area/security
  - scope/destination
updated: 2026-09-28
---

**Proposed initial sketch, 2026-09-27:** This threat model organizes the accepted scope and unverified protections in [SPIFFE authentication](spiffe-mtls-authentication.md), [Participants and permissions](participants-and-permissions.md), and [supervisor protection](supervisor-protection.md). It reviews the proposed [schema](identity-schema.md), [data flow](identity-data-flow.md), [API](identity-api.md), and [commands](identity-commands.md). It is not a security assessment of an implementation.

## Assets and intended properties

Protect participant attribution, immutable workload roles, active incarnation and bot-generation bindings, enrollment authority, private keys/JWTs, trust-root integrity, grants, human-session mapping, and attributable audit history. Protect application content against unauthorized reads and operations against unauthorized mutation. Availability is a separate property: correct authentication alone does not prevent resource exhaustion or process termination.

The intended contract is that a caller exercises only its currently authorized participant authority, across either supported authentication method, without managed workload code obtaining reusable orchestration credentials. An authenticated request establishes the responsible participant, not whose intent caused that participant to act. Capability metadata, message text, external author assertions, and membership are not credentials or implicit grants.

## Adversaries and assumptions

In scope are malicious managed harness code and repository inputs; a different managed workload; an unregistered or compromised bot; spoofed bridge authors; a network attacker; stolen/replayed credentials; and stale or racing controllers. Compromised credentials are bounded by the principal's remaining grants and cutoff enforcement, not magically made harmless by SPIFFE.

**Decided host boundary:** The OS user is trusted; arbitrary same-UID tampering with wrapper memory, keys, and launch bindings is outside the accepted host threat model. Malicious code operating through a supposedly supported managed harness remains in scope, including native tools, helpers, MCP/plugins, project configuration, and paths that escape shell-only restrictions. A bypass under the supported profile is a gap, not an operator-authorized relaxation. Deliberately permissive operator configuration has weaker declared guarantees.

The OS kernel, selected issuer, agentd, custody components, and their protected configuration form the trusted computing base. Their compromise can defeat identity; this sketch does not promise protection from a malicious host administrator or compromised kernel. For sbx, runtime isolation and credential-proxy behavior are assumptions to qualify, not inherited guarantees from a product name. Arbitrary cross-host federation and the deferred custom microVM architecture are outside the initial profile.

Groups on one unisolated host can share a compromise domain; distinct credentials and policy scopes do not create process isolation. Controller and bot enrollment secrets are authority-bearing assets even when SVIDs are short-lived.

## Trust boundaries

| Boundary | Evidence needed before relying on it |
| --- | --- |
| Host harness → wrapper application socket | Kernel process-instance evidence tied to the trusted launch record, qualified across relays, helpers, and descriptor transfer. |
| Managed execution → control, credentials, and configuration | Effective restrictions for every supported tool surface; protected ancestors, launch inputs, and settings. |
| Wrapper → agentd | Valid workload X.509-SVID, expected service identity, exact registration, authenticated incarnation binding, and current policy. |
| Guest → runtime proxy → agentd | Sandbox-specific attribution and injection; independently valid TLS trust/name checks on the relevant hops; no token reflection or redirect leakage. |
| Controller/resolver → issuance | Authenticated entitlement to one allowed enrollment/binding; qualified harness confinement protects access to control endpoints and secrets. Entitlement is least privilege, not arbitrary same-UID isolation. |
| Bot → agentd | Registered bot kind, generation/cutoff enforcement, explicit installation grants, and conversation policy. |
| Human/browser → UI backend → operator operation | Authenticated per-human mapping, session revocation, scoped authority, and no browser SVID. |

## Abuse cases and proposed controls

All controls below are requirements or candidates, not verified defenses. BV references point to the existing [validation spikes](backend-validation-spikes.md). Bot/operator rows are additional design qualification needs, not automatic additions to the PoC backlog.

| Threat | Proposed control and negative check | Evidence gate or residual risk |
| --- | --- | --- |
| Workload B connects to A's socket, forges a PID, or shares tmux ancestry | Use kernel peer evidence and launch-instance membership; reject B, stale PID reuse, ambiguous helpers, and foreign descriptor use. | BV-01; a socket pathname or relay PID alone proves too little. |
| Managed tool reads keys or alters wrapper configuration | Protect files, process state, control sockets, parent paths, and effective harness settings across shell and native tools. | BV-02; shell-only confinement is insufficient. |
| Workload self-enrolls as coordinator or another participant | Separate control exposure and authenticated enrollment; derive role/identity from provisioned records. Test forged target and wrong-kind enrollment. | BV-03; bootstrap/attestation remains unresolved. |
| Valid issuer credential names an unregistered participant or service identity | Exact trust-domain/path/record match and kind-specific authorization. Reject unknown IDs and infrastructure identities on application routes. | BV-04 plus bot namespace tests. |
| Both credentials, invalid-plus-valid credentials, or wrong JWT audience | Reject ambiguous methods without fallback; validate each method's identity, trust, and time rules. | BV-04; record TLS rejection separately from HTTP errors. |
| Old credential acquires a successor's authority | Authenticated credential-to-incarnation/generation mapping plus live state, never “subject → latest incarnation.” | BV-03/BV-07; wire binding and issuer integration are blocking choices. |
| Long-lived connection bypasses expiry or revocation | Recheck current authority before new protected work/data and invalidate streams on cutoff/expiry. | BV-07; closure timing and already buffered/committed effects remain explicit limits. |
| Delayed suspend/renewal races with resume | Conditional revisions, terminal fences, immutable incarnation IDs, and commit ordering. Replay predecessor events against an active successor. | BV-07; rotation is not fencing. |
| Guest steals/replays a JWT or redirects injection | Sandbox-scoped resolver, narrow destination matching, audience restriction, secret-free logs/errors, and no token reflection. Test redirects, other ports, placeholder swaps, and proxy bypass. | BV-06; bearer tokens are replayable if exposed until expiry/cutoff. |
| Agentd impersonation or CA substitution | Protect persistent CA state; verify service identity or HTTPS DNS name as appropriate. Reject wrong CA/name and missing established trust state. | BV-03/BV-05; guest CA kit does not yet establish host-proxy trust. |
| Issuer outage or crash restores stale authority | No unauthenticated fallback; expiry enforcement, durable fences, bounded liveness, and restart reconciliation. | BV-07; stale-authority window awaits a timing decision. |
| Bot combines unrelated installations into broader authority | Evaluate action and containment together; revoke registration across all grants, and installations individually. | Additional bot tests; cross-Group DM composition remains disabled until defined. |
| Bridge assertion becomes a local operator/workload identity | Preserve authenticated bot sender, label asserted author, separate inbound relay and outbound egress grants. | Additional bridge tests; a bot can still export data through unmediated external access. |
| Browser caller selects another human or backend-wide authority | Protected per-human session mapping; reauthorization on operations/streams, revocation, and appropriate CSRF/session protections for the eventual transport. | Additional operator tests; login/delegation protocol unselected. |
| Authorized workload acts as a proxy for another actor or follows injected workspace content | Preserve attribution and constrain grants; do not claim identity validates intent or sanitizes message content. | Residual semantic/confused-deputy risk; harness approval authority remains separate. |
| Connection, issuance, resolver-spawn, or audit flood | Rate-limit issuance per incarnation at agentd and bound runtime resolver concurrency/invocations before process creation where supported. | Agentd rate limits alone cannot prevent host process spawning; measure cost and runtime controls in BV-06. |
| Stolen bot enrollment material survives SVID cutoff | Proposed cutoff invalidates enrollment as well as generation; re-attestation requires independent authorized recovery, not the compromised secret. | Additional bot fixture; cutoff must cover issuer-native delivery and pending callbacks too. |
| Restoring old identity state restores revoked authority | Treat backup restore as a trust-recovery event; block serving until rollback-safe authority is established. | External monotonic epochs or coordinated invalidation/re-enrollment across both SVID formats are candidates, not selected controls. JWT key rotation alone does not invalidate X.509 credentials or restored grants. |
| Clock steps, skew, or laptop sleep change validity/liveness | Check expiry on request and stream use; test forward/backward clock changes and sleep/wake with the chosen issuer/profile. | Grace bounds and continuation versus resume remain open; time alone is not a reliable generation binding. |
| Reused identity path transfers old credentials to a new actor | Never reassign opaque participant/path identifiers; map full registered paths and explicit epochs. | Registry invariant and restore tests; loose prefix matching is insufficient. |
| Bot webhook leaks content or follows stale authority | If callbacks are selected, authorize destination and agentd-to-bot authentication, reject redirect/SSRF paths, and cancel/recheck pending attempts on cutoff. | Delivery method unselected; no claim that inbound bot authentication protects outbound webhooks. |
| TLS resumption reuses stale authentication context | Preserve authenticated binding and independently recheck expiry, registration, and fences on resumed sessions. | BV-04/BV-07 targeted tests; chosen TLS-stack behavior is unknown. |

## Release questions and limits

The first acceptance gate is two concurrently active workloads under each claimed backend/harness profile, with successful legitimate operations and failed cross-workload, enrollment, stale-generation, and credential-leak attempts. BV-10 composes the earlier checks; a passing stub or another backend is not qualification. Keep versions, effective configuration, observed failures, and untested tool paths with the evidence. Report observed outcomes per frozen profile and targeted verified checks; no finite matrix proves universal absence of bypasses. Token non-reflection is an intended requirement, with observations limited to the output surfaces actually tested.

Resolve issuer/bootstrap selection, authenticated generation binding, local caller attribution, sbx upstream trust, refresh/caching behavior, and revocation/reconciliation bounds before claiming the intended contract. Bot/operator flows need their own lifecycle and adversarial tests. Cross-host trust, automated root rollover, and audit retention remain separate design questions; a trusted foreign issuer alone must never grant local Group authority.

Revocation cannot erase prior reads, retract already delivered messages, or undo committed external effects. Audit logs can identify the authenticated actor and observed transitions but cannot prove that all exposure was recorded. Retention follows the shared [retention decision](messaging-schema.md#retention-and-redaction-open-decision); do not duplicate bearer secrets or message bodies merely to strengthen audit claims.

## Candidate bot qualification input

**Proposed follow-on, transferable only by operator decision:** Use two registered bots with both allowed authentication methods, one workload, two scoped installations, a persistent stream, and a stub callback destination if callbacks are selected. Exercise namespace/kind confusion, direct-issuer bypass attempts, stolen enrollment after cutoff, old-generation streams, installation-only versus registration revocation, queued callbacks, and re-attestation that does not restore old grants. Completion requires a dated binding/custody recipe and negative traces for every supported path. This is not a new numbered PoC spike. Operator authentication still needs a separate bounded design and fixture before oversight qualification.

## Provenance

The host threat-model exclusion and initial backend direction come from the source wiki's recorded operator decisions. The table consolidates its validation leads and adds explicit schema/API abuse cases as Codex proposals requested on 2026-09-27. No adversarial probe, live runtime change, or new PoC work was performed.

**Review integration, 2026-09-28:** Revised against [Claude’s preliminary review and Codex disposition](identity-preliminary-review-claude.md#codex-reconciliation). Corrections and new recommendations remain proposed; no issuer, bootstrap, liveness policy, or operator installation model is selected.
