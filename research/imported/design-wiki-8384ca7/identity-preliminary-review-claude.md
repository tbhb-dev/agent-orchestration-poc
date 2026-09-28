---
title: Identity sketches preliminary review (Claude)
summary: "Claude's preliminary review of the five identity design sketches, with prioritized findings and reconcilable proposals for Codex."
type: research
status: draft
tags:
  - area/identity
  - area/security
  - scope/destination
updated: 2026-09-28
---

**Review status, 2026-09-28:** Claude reviewed the [identity schema](identity-schema.md), [data flow](identity-data-flow.md), [API](identity-api.md), [commands](identity-commands.md), and [threat model](identity-threat-model.md) at the operator's request, as initial destination-state proposals. Every recommendation here is `proposed`. Nothing on this page is an operator decision, and no probe, implementation, or PoC change was made. The five sketches were not edited.

Sources read: [AGENTS.md](AGENTS.md), [README](README.md), [SPIFFE authentication](spiffe-mtls-authentication.md), [Participants and permissions](participants-and-permissions.md), [backend validation spikes](backend-validation-spikes.md), [operator oversight](operator-oversight.md), [group peering](group-peering.md), and the participant section of the [messaging schema](messaging-schema.md#participants-and-authorization). [Supervisor protection](supervisor-protection.md) was not reread; findings that touch harness confinement defer to BV-02 as the sketches already do.

External facts checked during review are cited inline. Claims about SPIRE, Go TLS, and Docker runtime behavior that were not checked are labeled `inference` or `unknown`.

## Overall assessment

The sketches are a solid first cut. They hold the source wiki's line between decided direction and proposed mechanics better than most first drafts, and they refuse the usual shortcuts: no "subject resolves to latest incarnation," no fallback between authentication methods, no caller-supplied kind or role, no raw bearer tokens in retry records.

The weakest area is the one the sketches already flag: the credential-digest binding. It is feasible only when agentd brokers every issuance, and several of its stated requirements are either wrong ("atomic with activation") or unmet by the JWT-SVID format as specified. The gate should compare at least three candidate mechanisms rather than qualify one.

The second structural gap is lifecycle semantics. Suspend and fence are used inconsistently across the five pages and the source authentication page, and the incarnation state machine is never enumerated. That ambiguity will surface as a real bug the first time a suspended workload resumes.

The third gap is control-plane authentication. The sketches describe fine-grained controller entitlement, but under the decided host threat model (same-UID processes trusted) most of that entitlement is least-privilege hygiene rather than an enforceable boundary. The pages should say which is which.

Beyond those, operator permissions have no home in the schema, the bot cutoff does not cut off a compromised enrollment, `agentctl` mixes operator and infrastructure principals, and the sbx resume path omits resolver rebinding. Most other issues are details reasonably deferred.

## Strengths worth preserving

- The application/control surface split in the [API](identity-api.md) table, including the statement that infrastructure enrollment authority does not imply operator policy authority.
- Kind-specific authority bindings, with explicit refusal to invent workload incarnations for bots or operators.
- The invariant that old credentials cannot be rebound to current state by participant lookup. Every alternative proposed below keeps it.
- The resolver output contract in [commands](identity-commands.md): token-only stdout, empty stdout on failure, sanitized stderr, no progress output.
- The issuance retry stance: no exactly-once claim, fresh authorized issuance after a lost response, and live authorization rejecting a validly signed credential minted during a fence race.
- The concurrency rule in [data flow](identity-data-flow.md#renewal-fencing-and-recovery) that work committed before a fence stands and work reaching acceptance after it is denied, with honest limits on dispatched external effects.
- The [threat model's](identity-threat-model.md) explicit trusted computing base, residual-risk column, and statement that authentication establishes the responsible participant, not intent.
- Consistent evidence labeling and BV mapping, with bot/operator checks kept out of the PoC backlog by implication.

## Priority scale and finding types

- **P0:** implementation-blocking. Resolve or explicitly bound before any sketch becomes an implementation input.
- **P1:** should be corrected in the next sketch revision; a wrong reading could propagate into other pages.
- **P2:** reasonably deferred or polish.

Each finding is typed as a **consistency correction**, **new proposal**, **operator decision**, or **qualification experiment**. Several carry more than one type.

## P0 findings

### IR-01: The credential-digest binding is feasible only under a fully brokered issuer, and its stated requirements need correction

**Location:** [Schema, "Authenticated binding is an implementation gate"](identity-schema.md#authenticated-binding-is-an-implementation-gate); echoed by the `credential_bindings` record, [data flow](identity-data-flow.md) host step 2 and sandbox step 4, and the [API](identity-api.md) common principal's `credential_ref`.

**Type:** new proposal, qualification experiment, operator decision.

**Problem.** The candidate maps a digest of each issued leaf or JWT to its incarnation or generation. It works cleanly in some configurations and fails by construction in others, and two of its preconditions are misstated:

1. "Registration is atomic with activation" is the wrong requirement. The data flow issues credentials while the incarnation is still `preparing`, before activation. What must be atomic is recording the digest-to-binding row before the credential leaves the broker. Activation is a later state change on the incarnation that live authorization checks independently.
2. "Issuance yields distinguishable credentials across generations" is guaranteed for X.509 but not for JWT-SVIDs. RFC 5280 requires a CA to assign unique serial numbers, so leaf digests differ. The JWT-SVID specification requires only `sub`, `aud`, and `exp`; `jti` is optional ([JWT-SVID spec](https://www.github.com/spiffe/spiffe/blob/main/standards/JWT-SVID.md)). Two tokens for the same subject and audience issued within the same second with the same expiry can be byte-identical if the signature scheme is deterministic (Ed25519 and RSA PKCS#1 v1.5 are; ECDSA normally is not).

**Example failure.** An operator cuts off bot generation 4 and the bot immediately reissues under generation 5 within the same second. With deterministic signatures and no `jti`, the generation 4 and 5 tokens are identical. The digest lookup either collides on insert or maps a stolen generation 4 token to generation 5.

**Feasibility by case.** Labels reflect evidence strength.

| Case | Digest binding | Notes |
| --- | --- | --- |
| Brokered X.509, key delivered by broker | Feasible (`inference`) | Sign, durably record, then deliver. Delivery of private keys stays open in the source. |
| Brokered X.509, local key with CSR | Feasible (`inference`) | Same ordering. Also makes issuance retries safe; see IR-08. |
| Brokered JWT | Feasible only with a unique claim (`documented` gap) | Add `jti`; the spec permits additional registered and private claims. Once a unique or binding claim exists, a claim-based binding (candidate D below) is also available. |
| sbx on-demand JWT per request | Feasible, cost `unknown` | Docker's `--refresh on-demand` resolves at every credential use per the [source page](spiffe-mtls-authentication.md#runtime-mediated-jwt-authentication). That is one durable row, and under the messaging schema's `synchronous=FULL` candidate one fsync, per application request, plus a process spawn. Rows can be garbage-collected after `exp`. Measure in BV-06. |
| Normal rotation | Feasible | New digest, same binding; overlap is two live rows. |
| Incarnation fencing | Feasible | The digest resolves to the fenced incarnation, which live state rejects. |
| Bot generation cutoff | Feasible only if bot issuance is brokered | See next row. |
| Direct standard Workload API delivery | Not feasible by construction | Agentd never sees the leaf. Whether a candidate issuer exposes issuance events agentd could record first is `unknown`. The schema notes that direct delivery "cannot silently bypass" the binding; in practice it means bots using direct delivery cannot use this mechanism at all. |
| Agentd restart | Feasible | The table must be durable and loaded before serving. Loss fails closed and forces re-enrollment of every participant, which is acceptable but should be stated. |
| Restore from backup | Unsafe for every candidate | Restoring an older identity database rolls back fences and cutoffs and re-legitimizes credentials that were revoked after the backup. See IR-12. |
| TLS session resumption | `unknown` | A resumed mTLS session does not re-present the certificate. The server must carry the original credential reference with the session and recheck its binding. Whether the chosen TLS stack preserves peer certificates and rejects expired ones on resumption needs a targeted check. |

**Candidate mechanisms for the gate.** The schema says alternatives "may be preferable once an issuer is chosen." I recommend naming them now so BV-03 and BV-07 compare rather than qualify one:

- **A. Credential digest registry.** As sketched. Requires every issuance path to run through agentd; adds per-credential durable state; needs `jti` for JWTs.
- **B. Authority-scoped SPIFFE path.** Encode the incarnation or generation as a path segment, for example `/workloads/<w>/incarnations/<n>` and `/bots/<b>/generations/<n>`. Agentd matches the exact path and checks that `<n>` is current. This is stateless per credential, works for X.509 and JWT alike, and works with direct Workload API delivery if the issuer's registration entry is replaced at cutoff. Costs: a participant no longer has one SPIFFE ID, so `participants.spiffe_id UNIQUE` becomes a registered prefix plus current epoch; issuer registration churn at every resume and cutoff; and a namespace choice the source pages deliberately leave open. X.509-SVIDs must contain exactly one URI SAN ([X.509-SVID spec](https://github.com/spiffe/spiffe/blob/master/standards/X509-SVID.md)), so the epoch cannot ride in a second SAN; it has to live in the one path.
- **C. Issued-at watermark.** Store an `authority_not_before` per participant; reject credentials whose `iat` or `notBefore` precedes it. No per-credential rows. It fails with notBefore backdating (common for clock-skew tolerance; whether a given issuer backdates is `unknown`), one-second granularity, and host clock steps, and a fence must wait out the second boundary. Weakest of the four.
- **D. Private binding claim.** A collision-resistant private JWT claim carrying the binding. JWT only; X.509 would need a nonstandard extension, which the schema declines.

**Claude's position (`proposed`):** If the operator keeps the SPIFFE path layout open, evaluate B first. It is the only candidate that covers both credential formats and direct delivery without per-credential state. Keep A as the fallback for a fully brokered issuer. Drop C unless measurements show it is safe with the selected issuer. This does not select an issuer.

**Recommended changes.**

- Replace "atomic with activation" with "durably recorded before delivery; activation is a separate live check."
- Require a unique token identifier for every JWT under candidate A, and record that the JWT-SVID spec does not supply one by default. SPIRE appears to be adding entry-level `jti` inclusion ([SPIRE PR #7136 changelog](https://github.com/spiffe/spire/pull/7136)); its release state was not verified.
- List candidates A through D with the matrix above in the gate section, and state that bots using direct Workload API delivery rule out A.
- Add a structural negative test to BV-03: attempt issuance through every non-broker path the selected issuer exposes and require rejection at agentd.
- Record the sbx per-request cost as a BV-06 measurement target.

### IR-02: Suspend, fence, and resume semantics contradict each other, and the incarnation state machine is not enumerated

**Location:** [Schema invariants](identity-schema.md#invariants); [data flow renewal table](identity-data-flow.md#renewal-fencing-and-recovery), rows "Suspend or workload exit" and "Resume"; [API](identity-api.md) `suspend` route; source [lifecycle list](spiffe-mtls-authentication.md#launch-rotation-suspension-and-resume) steps 5 and 6.

**Type:** consistency correction, new proposal.

**Problem.** The pages disagree on whether a suspended incarnation is fenced:

- Source step 5 reports suspension on exit; step 6 fences the previous incarnation on resume. That reads as suspended-but-not-fenced.
- The data flow "Suspend" row says "conditionally fence the expected incarnation," and the "Resume" row says "fence the old incarnation before activating a newly prepared one." If suspend already fenced, the resume fence is a no-op; if it did not, the pages never say what authority a suspended incarnation retains.
- The API `suspend` route says "fence this incarnation." The schema says "fencing is terminal" and "suspend clears the active pointer," which describes two different operations without saying whether suspend performs both.

**Example failure.** A host wrapper crashes without reporting exit. Reconciliation marks the incarnation suspended but not fenced, because fencing is described as a resume step. The orphaned harness child still holds a valid certificate. If "suspended" does not reject application requests, it keeps working until expiry, and nothing on the five pages says otherwise.

**Missing states and transitions.** Preparing-to-abandoned (launch failure or timeout); lease expiry; workload retirement (the participant itself ending, as opposed to one incarnation); and whether a retired workload's participant ID may ever be reused. `workload_authority` has no registration state, so a retired workload is indistinguishable from a suspended one with a null active pointer.

**Recommended change.** Add one state table to the schema, owned there and referenced by the others. Proposed minimum:

| Incarnation state | Application authority | Exits |
| --- | --- | --- |
| `preparing` | Bootstrap only | `active` on activation; `fenced` on abandon, timeout, or cancellation |
| `active` | Yes | `fenced` on suspend, exit, lease loss, or operator action |
| `fenced` | None, terminal | none |

Treat suspend as "fence the current incarnation and clear the active pointer, conditionally." Resume then allocates and activates a new incarnation; its "fence the old one first" step becomes an assertion that the old one is already fenced. Add a workload-level `registration_state` (`active`, `retired`) separate from incarnation state.

**Alternative.** Keep a non-terminal `suspended` state if some backend needs to resume the same incarnation without re-enrollment. I see no case for it in the source pages; every resume path already allocates a new incarnation.

### IR-03: Control-interface authentication is undefined, and controller entitlement is not an enforceable boundary under the host threat model

**Location:** [API surface table](identity-api.md#surface-separation) ("bootstrap still open"); schema `controller_ref`; [commands](identity-commands.md) resolver paragraph ("authenticates through its narrowly authorized enrollment"); source [enrollment section](spiffe-mtls-authentication.md#enrollment-and-credential-custody) and [host-mode trust boundary](spiffe-mtls-authentication.md#host-mode-trust-boundary).

**Type:** operator decision, qualification experiment, consistency correction.

**Problem.** Every control route depends on authenticating either an operator or an enrolled controller, and neither mechanism is defined. That is correctly flagged as open. The subtler issue is what the sketches imply about strength. The decided host threat model trusts the OS user; arbitrary same-UID processes are out of scope. So any credential a wrapper or resolver uses to prove its narrow entitlement lives in user-readable storage, and any same-UID process can present it. The entitlement checks then protect against confused deputies and bugs (a resolver configured with the wrong incarnation ID), not against an adversary. The one adversary that is in scope, malicious managed harness code, is stopped only by BV-02 confinement keeping it away from the control socket and those secrets.

The sketches currently read as if `controller_ref` scoping were a security boundary. The threat model's boundary table row "Controller/resolver → issuance" says "workload callers cannot reach or reuse it," which is the BV-02 property, not an entitlement property.

**Recommended change.** State in the schema and threat model that controller entitlement is a least-privilege and correctness control in host mode; the security boundary is harness confinement of the control socket and controller secrets. Keep entitlement checks, because they catch real misconfiguration.

For bootstrap, record the candidates for the operator rather than choosing:

- Same-UID peer credential on a `0600` control socket, plus a single-use per-incarnation enrollment nonce passed from provisioning to the wrapper through an inherited descriptor, never argv or environment. Simple and consistent with the decided threat model.
- Issuer-native attestation (for example, a node or workload attestor), which ties bootstrap to the issuer choice.
- A per-controller long-lived credential file readable by the user; closest to the resolver's actual shape in sbx.

The sbx resolver in particular needs whatever credential it uses to live on the host, readable by the user, keyed to one incarnation. Say so, so BV-03 designs for it.

### IR-04: Bot credential cutoff does not remove a compromised enrollment

**Location:** [API](identity-api.md) `bots/{id}/credential-cutoff` ("fresh issuance requires current enrollment authorization"); [commands](identity-commands.md) `bot cutoff`; schema `bot_authority`; [data flow](identity-data-flow.md) "Bot credential cutoff" row.

**Type:** new proposal, operator decision.

**Problem.** Cutoff advances the generation so old credentials fail. The pages do not say whether the bot's enrollment survives cutoff. If it does, a bot host compromised badly enough to leak its private key has probably also leaked whatever it uses to enroll, and the attacker simply reissues under the new generation. The bot's enrollment credential is its root secret, and its custody is not described anywhere; the threat model covers stolen SVIDs but not stolen enrollment material.

A JWT-only bot sharpens this. It needs some way to mint JWTs. If that is a broker call authenticated by an enrollment secret, the enrollment secret is itself a long-lived bearer credential, which is the thing the design otherwise avoids.

**Example failure.** A bridge bot's host is compromised. The operator runs `bot cutoff`. The attacker, holding the bot's enrollment credential, requests a fresh generation 5 JWT and continues relaying.

**Recommended change.** Define two operations. "Rotate generation" advances the generation and keeps enrollment, for suspected key exposure where the enrollment is still trusted. "Cut off" advances the generation and invalidates enrollment, requiring re-attestation under operator action. Make the second the default for the `cutoff` command name, since operators reach for it under compromise. Add bot enrollment-secret custody and theft to the threat model.

**Alternative.** A single cutoff that always requires re-enrollment. Simpler, but forces re-attestation for routine hygiene rotations.

### IR-05: `agentctl` carries both operator and infrastructure principals without a separation rule

**Location:** [commands](identity-commands.md) operator surface and resolver; [operator oversight authentication](operator-oversight.md#operator-authentication) (agentctl may hold an operator SVID); [API](identity-api.md) credentials route ("entitled custody component").

**Type:** new proposal, consistency correction.

**Problem.** One executable acts as the operator CLI, the host wrapper, and the sbx resolver. The oversight proposal lets local agentctl hold an operator identity with, by default, host-wide oversight grants. Docker invokes `agentctl worker-token` on the host as the user. Nothing on the five pages says the resolver or wrapper modes must not load operator credentials, or that the operator principal cannot call the credential-issuance route.

**Example failure.** The resolver mode loads the default agentctl credential set, finds the operator identity, and uses it on the control socket because the enrollment credential is missing. The request succeeds, since the operator is authorized for most control routes, and a sandbox now runs with credentials minted under operator authority. Conversely, if operators may call the issuance route, "no credential export to workloads" in the API's open-contracts paragraph becomes a policy convention rather than a check.

**Recommended change.** Add invariants: each agentctl mode authenticates with exactly one principal type selected by mode, never by fallback; wrapper and resolver modes never read operator credentials; the issuance route accepts only enrolled controller principals, and operator authority cannot mint workload or bot credentials. Operators act on enrollment (create, revoke) rather than holding the mint capability.

**Alternative.** Ship the resolver and wrapper as a separate binary. Cleaner separation, more packaging.

## P1 findings

### IR-06: Operator permissions have no home in the schema

**Location:** schema `operator_authority` and the paragraph "Installations initially describe bot grants"; [API](identity-api.md) `installations` route ("initially bot installations only"); [operator oversight](operator-oversight.md) ("oversight is a set of permissions in the operator's installation").

**Type:** consistency correction, operator decision.

**Problem.** The oversight proposal stores operator oversight as installation grants. The identity sketches restrict installations to bots and say operator permissions stay in a separate policy adapter, but define no record for that adapter. So oversight read and every graded intervention have nowhere to live. This is the open workload/operator installation-unification question showing up concretely.

**Recommended change.** Record the conflict in both pages. Until the operator decides unification, give the schema an explicit interim, either `operator_grants(participant_id, scope_kind, scope_id, grants, state, revision)` with the same shape as installations, or permission for operator installations while workload roles stay separate. The second is a partial unification and should be flagged as such.

### IR-07: The sbx resume path omits resolver rebinding, and per-request resolution is an unbounded host-side cost

**Location:** [data flow sandbox launch](identity-data-flow.md#sandbox-launch-and-first-request); [commands](identity-commands.md) `worker-token WORKLOAD_INCARNATION_ID`; [threat model](identity-threat-model.md) flood row.

**Type:** consistency correction, new proposal, qualification experiment.

**Problem.** The resolver command line carries the incarnation ID, correctly, so a surviving old sandbox cannot obtain a successor's tokens. It follows that every sbx resume must replace the sandbox's secret binding with the new incarnation ID before activation, and remove the old one. Neither the data flow nor the commands page lists that step. Without it, the resumed sandbox's resolver keeps asking for the fenced incarnation and every request fails, or an implementer "fixes" it by passing the workload ID and resolving the current incarnation, which reintroduces the subject-to-latest pattern the design forbids.

Separately, with on-demand refresh the guest controls how often the host spawns `agentctl`, signs a JWT, and writes a row. The flood row covers connection and issuance floods at agentd, but not guest-driven process spawning on the host.

**Recommended change.** Add "rebind resolver to the new incarnation; remove the predecessor's binding" to the sandbox flow and to the resume row. Add guest-triggered resolver invocation to the threat model with a per-incarnation issuance rate limit enforced at agentd. Measure spawn and issuance latency in BV-06 before choosing between on-demand and a bounded cache.

### IR-08: The issuance route's `request_id` contradicts its own retry contract

**Location:** [API](identity-api.md) route table (`POST /control/v1/enrollments/{id}/credentials` with `request_id`) and "Mutation and failure contract."

**Type:** consistency correction, new proposal.

**Problem.** Ordinary mutations use `request_id` for idempotent replay of a recorded outcome. The issuance paragraph then says raw JWTs are not stored, so a lost response triggers fresh issuance. Both are right, but listing `request_id` on the issuance route implies replay semantics it cannot have for secrets.

X.509 with local key generation is different. The certificate chain is public, so a retry with the same `request_id` and the same CSR can safely return the same certificate. That makes the X.509 path genuinely idempotent and keeps the private key off the wire.

**Recommended change.** Define issuance `request_id` as audit correlation, not replay, for secret-bearing responses (JWTs, delivered keys). For CSR-based X.509 issuance, allow replay of the recorded certificate. Note the CSR path's retry and custody advantages in the open key-provisioning choice without selecting it.

### IR-09: Idempotency and revision checks need an explicit ordering and key scope

**Location:** [API mutation contract](identity-api.md#mutation-and-failure-contract).

**Type:** consistency correction.

**Problem.** A client retries a successful suspend after a lost response. If the server checks `expected_revision` first, the retry fails with `revision_conflict`, because the first attempt already advanced the revision. The contract says identical retries return the recorded outcome but does not fix the order. Creation routes (`POST /control/v1/bots`) have no target yet, so "under the authenticated actor and target" is undefined for them. Idempotency record retention is unstated.

**Recommended change.** Specify: look up `(actor, request_id)` first; if found, compare normalized intent and return the recorded outcome or `idempotency_conflict`; only then evaluate `expected_revision`. Key creation requests by actor and request ID alone. Defer retention length, but require it to exceed any documented client retry window.

### IR-10: Liveness has a schema field but no mechanism, and laptop sleep will trip it

**Location:** schema `lease_expires_at`; [data flow](identity-data-flow.md) "Wrapper/runtime loss" row; [API](identity-api.md) has no lease route.

**Type:** new proposal, operator decision.

**Problem.** No route renews a lease, and no page says what drives it. On a laptop, the common failure is not a crash but sleep. After eight hours asleep, every lease and short-lived credential has expired. If lease expiry fences, every workload is fenced on wake and needs an explicit resume, even though the harnesses are still running.

**Recommended change.** For the initial design, drop the separate lease and let credential renewal serve as the heartbeat: the stale-authority window equals credential lifetime plus reconciliation, and a missed renewal expires authority without fencing. Fence only on observed exit, operator action, or a reconciliation that finds the process gone. The operator should decide wake behavior: auto-renew and continue when the process binding still validates, or require resume.

**Alternative.** Keep explicit leases with a heartbeat route. More machinery, and it needs the same wake decision.

### IR-11: The commit-boundary recheck requires identity state and messaging acceptance in one transactional store

**Location:** [data flow concurrency rule](identity-data-flow.md#renewal-fencing-and-recovery); schema "Lifecycle, grant, and audit mutations use conditional revisions and durable transactions"; [messaging schema](messaging-schema.md) SQLite ownership.

**Type:** new proposal.

**Problem.** "Fencing and application acceptance share an ordering boundary" holds only if the fence write and the message insert serialize against each other. If identity records sit in a different database or process from messaging, a message can commit after a fence commits elsewhere.

**Recommended change.** State that identity authority records and messaging acceptance live in the same SQLite database under agentd's single writer, or that acceptance rechecks authority inside the same transaction by some other serialization. The same-database option is simpler and matches the existing agentd-owns-SQLite direction.

### IR-12: Threat-model gaps, and validation that cannot establish some claimed properties

**Location:** [threat model](identity-threat-model.md) abuse-case table and "Release questions and limits"; [backend validation spikes](backend-validation-spikes.md).

**Type:** new proposal, qualification experiment.

**Missing abuse cases.**

- **Identity-state rollback.** Restoring a backup of agentd's database re-legitimizes credentials revoked after the backup, for every binding candidate. Propose a monotonic epoch outside the database (or rotation of JWT verification keys on restore) and treat restore as a trust event.
- **Bot enrollment-secret theft.** See IR-04.
- **Guest-triggered resolver spawning.** See IR-07.
- **Bot callback delivery.** Agentd-to-bot webhooks are egress to an operator-registered URL, need agentd-to-bot authentication, and carry message content. Cutoff must cancel pending attempts, as [participants](participants-and-permissions.md#kind-specific-lifecycle-and-storage) says. Delivery mechanics are open, so a placeholder row suffices.
- **Time.** Clock steps, sleep, and skew affect JWT `exp`, notBefore, leases, and any watermark design. Not mentioned.
- **SPIFFE ID reuse.** If a retired participant's SPIFFE path is ever reissued, its unexpired credentials authenticate as the new participant under path-based binding. Add an invariant that SPIFFE path identifiers are opaque and never reused.
- **Cross-Group compromise on one host.** [Group peering](group-peering.md#authorization-at-the-receiving-group) notes that Groups on one unisolated host share a compromise domain. The threat model should repeat that separate credentials do not isolate Groups in host mode.

**Validation limits.**

- No spike covers bot or operator identity; the threat model says "additional bot tests" without an input. Propose a bounded bot-identity spike (namespace confusion, cutoff on live streams, enrollment separation, installation revocation) as a candidate PoC input, transferable only by operator decision.
- "Every issuance path passes through the broker" is structural. A positive BV run cannot show it; only a negative test against each issuer-exposed path can (IR-01).
- "No token reflection into guest-visible output" can be `observed` for tested surfaces, never verified exhaustively. The threat model should say so rather than listing it as a control.
- The two-workload acceptance gate demonstrates the absence of found bypasses under a frozen matrix. That is the right gate, and the page should label the result `observed` per profile rather than implying the contract is established.

### IR-13: Several pages presume the digest mechanism in their wording

**Location:** [data flow](identity-data-flow.md) host step 2 ("recording the authenticated credential-to-incarnation binding") and sandbox step 4 ("records the chosen credential binding before issuance is completed"); [API](identity-api.md) principal field `credential_ref`; schema `credential_bindings` table.

**Type:** consistency correction.

**Problem.** The gate says no mechanism is selected, but these passages describe digest registration as the flow. Under candidate B there is no per-credential row, and `credential_ref` would be the SPIFFE path plus epoch.

**Recommended change.** Phrase these steps mechanism-neutrally ("establish the authenticated binding per the selected mechanism") and mark `credential_bindings` and `credential_ref` as specific to candidate A.

### IR-14: Activation evidence is undefined

**Location:** [API](identity-api.md) `activate` route ("qualified execution/readiness evidence"); [data flow](identity-data-flow.md) host step 4.

**Type:** consistency correction.

**Problem.** The data flow says a caller asserting readiness does not establish integrity, but under the host threat model the wrapper is trusted infrastructure and its report is the only evidence available. The pages leave implementers unsure what to check.

**Recommended change.** State that activation evidence is a report from the enrolled controller for that incarnation, trusted because of the controller's enrollment, plus backend-specific facts it can observe (process binding established, sandbox running). Sandbox integrity remains a BV-02 and BV-05/06 property, not something the activate call proves.

## P2 findings

### IR-15: Schema simplifications for an initial design

**Location:** [schema records](identity-schema.md#ownership-and-records).

**Type:** new proposal.

- `enrollments` appears to be one-to-one with an authority binding (one incarnation or one bot generation). If no binding ever has two controllers, fold enrollment state into the incarnation and bot-generation records.
- `credential_bindings.authority_binding` duplicates the enrollment's binding and can drift. Derive it.
- `credential_bindings.cutoff_at` implies single-credential revocation, which has no API. Either add a route (useful for a leaked sbx JWT without fencing the workload) or drop the column for now. I lean toward deferring it; fencing the incarnation is an acceptable initial response.
- `trust_profiles` reads as configuration rather than transactional state. A config file with integrity protection may be simpler.
- `identity_events` recording both expected and resulting revision is fine; no change.

These are Claude's preferences; Codex may reasonably keep the separate tables for future multi-controller cases.

### IR-16: Command-surface completeness

**Location:** [commands operator surface](identity-commands.md#operator-surface) and [failure behavior](identity-commands.md#failure-and-review-behavior).

**Type:** new proposal.

- No list commands: participants, pending enrollments, installations per participant. Operators will need them before they need audit.
- No trust-state inspection (server CA fingerprint, workload bundle status). Useful for BV-05 debugging and for diagnosing a replaced CA.
- `--scope host:HOST` suggests multiple hosts. Since host means this agentd, a bare `host` avoids implying federation.
- Exit code `1` lumps retryable `503` with terminal `403`. A distinct transient code (for example `75`, `EX_TEMPFAIL`) lets scripts retry without parsing JSON.
- `bot enroll` must eventually hand the bot something. If that is a join secret, the command needs a protected output path (for example `--out FILE` created `0600`) or a pairing flow, since the page forbids printing secrets. Already acknowledged as blocked on bootstrap; worth naming the shape.

### IR-17: Workload Group immutability and cross-backend resume are unstated

**Location:** schema `workload_authority.group_id`; invariants.

**Type:** consistency correction, operator decision (cross-backend).

Role is immutable per identity; Group is not stated either way. Presumably the same rule applies. Separately, `workload_incarnations.backend` allows a resume on a different backend, switching authentication method. Either forbid it initially or state that the method follows the new incarnation's backend.

### IR-18: Source-page nits found while tracing

**Type:** consistency correction (source pages, outside the five sketches).

- [BV-05](backend-validation-spikes.md#bv-05-sbx-kit-routing-and-server-trust) tests a "proposed `agentd.localhost` name," which the [authentication page](spiffe-mtls-authentication.md#runtime-mediated-jwt-authentication) does not propose; it proposes `host.docker.internal`. One should cite the other or drop it.
- The authentication page's bot paragraph permits both credential methods per bot. The schema's `enrollments.allowed_credential_method` holds one value. Clarify whether a bot may hold both at once; holding both doubles the credential surface.

## Details reasonably deferred at this stage

Exact lease or credential lifetimes; trust-root rollover automation; audit and digest retention; operator human login, delegation, and multi-operator grants; cross-host federation; the optional MCP adapter; single-credential revocation; stream recheck optimization (an in-process revocation notifier fits one agentd better than per-emission reads, but either is an implementation detail); final exit-code allocation; text-versus-JSON default.

## Implementation-blocking gaps

Before any sketch becomes an implementation input: IR-01 binding mechanism selection, IR-02 state machine, IR-03 control bootstrap, IR-04 bot cutoff semantics (before bots ship), and IR-05 principal separation. IR-06 blocks operator oversight specifically. IR-11 blocks the concurrency claim. Everything else can be corrected in normal revision.

## Consolidated proposals for reconciliation

| ID | Proposal | Finding | Type |
| --- | --- | --- | --- |
| P-01 | Replace "atomic with activation" with "recorded before delivery" | IR-01 | Consistency correction |
| P-02 | Require a unique JWT identifier under digest binding; note the spec gap | IR-01 | Consistency correction |
| P-03 | List binding candidates A–D with a feasibility matrix in the gate | IR-01 | New proposal |
| P-04 | Decide whether SPIFFE paths may carry an authority epoch | IR-01 | Operator decision |
| P-05 | Add a BV-03 negative test for every non-broker issuance path | IR-01, IR-12 | Qualification experiment |
| P-06 | Test TLS session resumption against the binding | IR-01 | Qualification experiment |
| P-07 | One incarnation state table; suspend fences; workload retirement state | IR-02 | Consistency correction, new proposal |
| P-08 | Label controller entitlement as least-privilege, not a host-mode boundary | IR-03 | Consistency correction |
| P-09 | Record bootstrap candidates without selecting one | IR-03 | Operator decision |
| P-10 | Split bot rotation from cutoff; cutoff invalidates enrollment | IR-04 | New proposal, operator decision |
| P-11 | Add enrollment-secret custody and theft to the threat model | IR-04, IR-12 | New proposal |
| P-12 | One principal per agentctl mode; operators cannot mint credentials | IR-05 | New proposal |
| P-13 | Interim operator grant record pending unification | IR-06 | Consistency correction, operator decision |
| P-14 | Add sbx resolver rebinding to resume | IR-07 | Consistency correction |
| P-15 | Per-incarnation issuance rate limit; measure resolver cost | IR-07 | New proposal, qualification experiment |
| P-16 | Issuance `request_id` is correlation for secrets, replay for CSR certificates | IR-08 | Consistency correction |
| P-17 | Idempotency lookup precedes revision check; creation keyed by actor | IR-09 | Consistency correction |
| P-18 | Credential renewal as heartbeat; no separate lease initially | IR-10 | New proposal |
| P-19 | Decide sleep/wake behavior | IR-10 | Operator decision |
| P-20 | Identity and messaging acceptance share one SQLite writer | IR-11 | New proposal |
| P-21 | Add rollback, callback, time, SPIFFE ID reuse, and cross-Group rows | IR-12 | New proposal |
| P-22 | Candidate bot-identity spike, transfer by operator decision only | IR-12 | Qualification experiment, operator decision |
| P-23 | Mechanism-neutral wording in data flow and API | IR-13 | Consistency correction |
| P-24 | Define activation evidence as controller report plus observable facts | IR-14 | Consistency correction |
| P-25 | Schema simplifications | IR-15 | New proposal |
| P-26 | Command list/trust commands, scope spelling, transient exit code | IR-16 | New proposal |
| P-27 | Group immutability; cross-backend resume rule | IR-17 | Consistency correction, operator decision |
| P-28 | Source nits in BV-05 and bot method cardinality | IR-18 | Consistency correction |

## Handoff to Codex

**Recommended integration order.**

1. Pure consistency corrections that change no design: P-01, P-02, P-13 (as a recorded conflict), P-14, P-16, P-17, P-23, P-24, P-28.
2. The lifecycle state table (P-07), since IR-10, IR-12, and the binding discussion all reference its states.
3. The binding gate rewrite (P-03, P-05, P-06), leaving P-04 open for the operator.
4. Control-plane framing (P-08, P-09, P-12) and bot semantics (P-10, P-11).
5. Threat-model additions (P-21) and the transactional-store statement (P-20).
6. P2 items, if Codex agrees with them.

**Decisions needing the operator.** Whether SPIFFE paths may encode an incarnation or generation epoch (P-04); control-interface bootstrap approach (P-09); bot cutoff semantics (P-10); interim home for operator oversight grants, which touches installation unification (P-13); laptop sleep/wake authority behavior (P-19); whether to transfer a bot-identity spike to the PoC (P-22); whether a workload may resume on a different backend (P-27). None of these selects an issuer, enrollment protocol, operator authentication design, or installation unification; they narrow what those choices must satisfy.

**Unresolved disagreements with the sketches as written.** Claude prefers evaluating path-scoped binding (candidate B) ahead of the digest registry; the schema presents the digest as the leading candidate. Claude prefers suspend-as-fence with no non-terminal suspended state and no separate lease; the sketches leave room for both. Claude would fold `enrollments` into binding records; Codex may keep them for future multi-controller cases. These are open for Codex's response, and neither position is a decision.

## Codex reconciliation

**Codex disposition, 2026-09-28:** Claude's review above is preserved as written. The five identity sketches and directly related source pages now incorporate the corrections and recommendations below. “Integrated” means incorporated into draft design, not accepted by the operator or verified in an implementation. No PoC files, runtime settings, or live identity state were changed.

| Finding | Disposition | Result and remaining choice |
| --- | --- | --- |
| IR-01 | Integrated with qualifications | Schema compares A–D, fixes registration-before-delivery ordering, requires unique issuance identifiers/collision rejection for candidate A JWTs, and adds bypass/cost/TLS-resumption tests. B and A both remain candidates; B does not itself qualify issuer attestation or prevent stolen enrollment obtaining a new path. |
| IR-02 | Integrated as canonical proposal | Schema owns `preparing → active → fenced`, direct preparation abandonment, suspend-as-fence, workload retirement, and no identity reuse. Resume ensures old incarnations are fenced even if no suspension report arrived. |
| IR-03 | Integrated with qualification | Bootstrap candidates are explicit. Entitlement remains enforced least privilege; it is not same-UID isolation. Managed-code exclusion depends on qualified confinement. The review's universal claim about user-readable credential files is too broad for unselected custody mechanisms; no such storage guarantee is inferred. |
| IR-04 | Integrated stronger cutoff proposal | Cutoff advances generation and invalidates prior enrollment, requiring independently authorized re-attestation. Routine renewal preserves generation. Defer a separate generation-only rotation operation until a use case warrants it; the simpler API is sufficient for this sketch. |
| IR-05 | Integrated as proposal | One principal class per agentctl mode, no operator fallback, issuance restricted to enrolled custody/controller authority. Operators manage enrollment; same executable or OS user does not implicitly grant mint access in the API. |
| IR-06 | Integrated interim alternative | `operator_grants` gives permissions a proposed home; oversight records the conflicting installation proposal. Neither unification nor a default host-wide grant is selected. |
| IR-07 | Integrated | sbx resume replaces resolver binding before activation. Measure process spawning and persistence cost; issuance limits alone cannot bound pre-request process creation. |
| IR-08 | Integrated | Secret-bearing issuance uses correlation `issuance_id`, without secret replay promises. CSR-based public-certificate replay is an explicit candidate with its own key and current authorization. |
| IR-09 | Integrated | Authenticate/authorize, look up actor/request idempotency, compare normalized intent, then check revision for new mutations. Creation needs no preexisting target; retention must cover the promised retry window. |
| IR-10 | Partly integrated; recommendation not selected | Replace the unexplained lease field with a liveness-policy placeholder. Renewal contact is not harness liveness, especially for idle sbx guests. Compare renewal-informed reconciliation with explicit heartbeats; sleep/wake and stale-authority policy remain open. |
| IR-11 | Integrated as storage recommendation | Authority and message acceptance share one SQLite transaction domain; another design must supply equivalent serialization. Same database is a simple candidate, not the only possible mechanism. |
| IR-12 | Integrated with evidence qualification | Added rollback, enrollment theft, spawning, callback, time, ID reuse, and shared-host compromise concerns; a bounded bot fixture remains a candidate input. Restore cannot be repaired universally by JWT key rotation; X.509 credentials and rolled-back grants also matter. Targeted verification remains valid, while universal security claims do not follow from a finite matrix. |
| IR-13 | Integrated | Flows and principal evidence are mechanism-neutral; per-credential rows/ref apply only to A. Registration represents either stable IDs or explicit epoch paths. |
| IR-14 | Integrated | Readiness is an enrolled controller's report of observable backend facts. It cannot independently establish sandbox integrity. |
| IR-15 | Partly integrated | Derive credential binding from immutable enrollment, remove unused per-credential cutoff, and mark trust profiles as protected configuration. Retain enrollment as a distinct entitlement/re-attestation lifecycle, without assuming future multi-controller support. |
| IR-16 | Partly integrated, remainder deferred | Use `--scope host`; name protected enrollment handoff candidates. List/trust commands and transient exit-code allocation remain follow-on interfaces needing corresponding API contracts. |
| IR-17 | Explicitly deferred | Group reassignment and cross-backend resume are not supported transitions in this sketch pending a policy decision; no immutable-Group decision is inferred from immutable role. Any future backend change needs a fresh incarnation and its selected method. |
| IR-18 | Integrated | BV-05 uses the source's `host.docker.internal` route. Enrollment methods are an explicit allowlist; enabling both for a bot is possible but not implicit, and each request still uses exactly one method. |

**External-source check:** On 2026-09-28 Codex inspected the [JWT-SVID specification](https://github.com/spiffe/spiffe/blob/main/standards/JWT-SVID.md) and [X.509-SVID specification](https://github.com/spiffe/spiffe/blob/main/standards/X509-SVID.md). The JWT source confirms optional `jti` and additional-claim interoperability concerns; its allowed algorithms do not include Ed25519. Use the permitted deterministic RSA case for the review's collision concern rather than importing its Ed25519 example into a JWT-SVID recipe. The X.509 source confirms exactly one URI SAN. No SPIRE release behavior, Docker behavior, or TLS-stack resumption behavior was verified.

**Remaining operator decisions:** Whether authority-scoped SPIFFE paths are acceptable; bootstrap/custody selection; acceptance of enrollment-invalidating bot cutoff; operator grants versus installations; liveness and laptop wake policy; Group/backend migration policy; and whether to transfer the candidate bot qualification input. Issuer choice and authenticated binding need experiments alongside those decisions. These pages remain preliminary implementation inputs with explicit gates, not implementation-ready specifications.
