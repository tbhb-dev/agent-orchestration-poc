---
title: Initial backend validation spikes
summary: "Issue-ready validation questions, fixtures, dependencies, and completion criteria for host mode and Docker Sandboxes."
type: input
status: active
tags:
  - scope/bridge
  - area/security
  - area/orchestration
  - area/containers
updated: 2026-09-28
---

## Purpose and scope

This is the handoff for the PoC coordinator to seed validation work from the accepted [host-mode and Docker Sandboxes scope](spiffe-mtls-authentication.md#initial-backend-scope). The backend selection is decided; these spike boundaries and experiment designs are proposed. No spike below is completed or experimentally verified by this page. Stable IDs are wiki references, not existing issue numbers.

Start with macOS, Claude Code, and Codex as the proposed first qualification slice. Record exact versions and interactive versus headless profiles separately. Linux and additional harnesses are follow-on matrix entries unless the PoC coordinator explicitly expands the initial slice; macOS results do not qualify them. Use small agentw-equivalent clients and disposable service fixtures before involving real harnesses. A fixture proves its tested contract, not production integration.

Do not design a custom sandbox, require an outer macOS sandbox, or investigate arbitrary hostile same-UID host processes as a release gate. Managed harnesses attempting to cross the configured boundary remain in scope. TCP fallback, other sandbox products, remote placement, and a full frontend are deferred. A failed required property produces a blocked or unsupported profile, not an automatic expansion into those alternatives.

The coordinator should first reconcile these IDs with current PoC issues and imported evidence, splitting by platform/profile only where execution requires it. Link an existing issue when it already owns the question. This page does not assign owners, change PoC scope automatically, or prescribe its issue workflow.

## Evidence contract for every spike

Each issue should copy its question, fixture, cases, dependencies, and completion criteria below. Before execution, name the bounded runtime profile and the target decision. Freeze that matrix for the run; report missing access or unsupported capabilities instead of silently substituting a different profile.

Each result must include:

- A reproducible script or fixture, exact commands, pinned source revisions where used, OS/architecture, runtime and harness versions, effective configuration, and process/transport topology.
- A case table with expected behavior, actual behavior, evidence location, and classification: allowed, blocked, prompted, unsupported, or inconclusive. Distinguish a policy denial from a connection or tool failure.
- Positive controls proving the fixture works and negative controls exercising the claimed boundary. Record whether a check was observed, documented, inferred, or simulated; deterministic simulation does not establish OS behavior.
- A concise decision: supported recipe, unsupported profile, required design change, or unresolved blocker. State residual caveats and the exact follow-on question, rather than extending the spike indefinitely.
- Cleanup and before/after state for disposable resources. Use fake credentials and test workspaces. Do not expose private keys or usable bearer values in reports; credential fingerprints and issuance counters suffice.

A spike is complete when its bounded question has an evidence-backed answer, including a reproducible failure. Completion is not acceptance of a failing security property. After three materially different failed approaches, stop and report the blocker. Live daemon restarts, OS trust changes, and settings changes need a controlled test environment or the operator's authorization; do not change the operator's existing configuration merely to complete a probe.

## Dependency and execution map

| ID | Question | Prerequisites |
| --- | --- | --- |
| BV-01 | Can host callers retain trustworthy local identity? | None; disposable local gateway |
| BV-02 | Can each harness protect the trusted wrapper and control plane? | BV-01 transport recipe; fixture work can begin independently |
| BV-03 | Can issuance, enrollment, and first-use trust bootstrap stay outside workloads? | None; isolated issuer/control fixture |
| BV-04 | Can mTLS and JWT produce the same authorized workload principal? | BV-03 credential format; synthetic tests may start earlier |
| BV-05 | Can the generated sbx kit establish trusted, injected HTTPS to agentd? | None; disposable CA and receiver suffice |
| BV-06 | Does sbx preserve identity and secrecy through refresh and failure? | BV-05 working transport, BV-03 for real resolver integration |
| BV-07 | Can authority be fenced through renewal, crashes, and resume? | BV-03/04, plus BV-01 or BV-06 for each backend |
| BV-08 | What launch, observation, cancellation, and storage contracts are available? | None for runtime probes; BV-07 for authority reconciliation |
| BV-09 | Can terminal attachment survive disconnection without granting extra control? | BV-08 launch/lifetime results |
| BV-10 | Does the composed backend satisfy the qualified contract? | Required prior results for that backend/profile |

BV-01 and BV-05 are the early feasibility gates. BV-03 and BV-08 can proceed alongside them. Do not block host qualification on sbx-specific failures or vice versa. BV-10 requires actual integrated components; a row exercised solely by a stub remains unqualified.

## BV-01: Host socket access and caller attribution

**Question and decision:** Can agentw reach a per-workload Unix socket while the gateway binds the actual connecting process instance to the intended workload? Select a supported socket configuration and process-membership algorithm, or identify the exact attribution gap.

**Fixture:** Two wrapper-launched process trees, A and B, with separate sockets and a tiny request client. Log kernel peer evidence and trusted launch records. Begin with ordinary child processes; repeat through each harness's real execution path. On macOS inspect audit-token evidence; on other separately qualified platforms use their corresponding kernel mechanism.

**Required cases:**

1. Accept A's legitimate descendants at A's gateway; reject B at A, including forged workload names and PID headers. Repeat with both launched beneath a shared tmux server.
2. Record which process connects when the harness enables socket access. If a relay connects, demonstrate whether it preserves an authenticated per-workload binding; never treat the relay PID as the original client's PID.
3. Exercise exec, nested children, detached/reparented children, parent exit, and helper processes. Define which are supported and reject ambiguous membership.
4. Exercise stale launch records and rapid process churn. Test PID-reuse logic deterministically as well; distinguish simulated reuse from an observed OS reuse event.
5. Probe inherited/transferred descriptors, socket replacement, and a connection held across workload exit using disposable targets. Decide how connection lifetime affects attribution.

**Done when:** A versioned configuration recipe and binding algorithm account for every case, with two-workload traces. A relay or unsupported helper path may block a profile; unauthenticated TCP is not a fallback. Feed the recipe to BV-02 and the connection-lifetime rules to BV-07.

## BV-02: Managed-harness confinement and credential custody

**Question and decision:** Under which exact harness configurations can managed code reach the peer gateway while being denied management authority, credentials, and wrapper modification?

**Fixture:** BV-01's two wrappers plus a dummy enrollment socket, canary private key, configuration files, and disposable processes. Use the [supervisor-protection matrix](supervisor-protection.md#validation-plan-and-caveat-format), filtered to the accepted threat model. Test Claude and Codex separately; do not infer native-tool confinement from a shell result.

**Required cases:**

1. Permit ordinary peer operations and workspace edits. Attempt enrollment, renewal for B, management calls, and access to B's socket from A.
2. Attempt canary reads, replacement, and signing-key use through shell and native file tools. Include writable parents, symlinks, loaded project settings, and wrapper launch inputs.
3. Attempt harmless process inspection first, then signaling/debugger access against disposable wrapper targets. Separate confidentiality, integrity, and availability results.
4. Exercise configured helper/MCP/plugin paths and interactive versus headless execution. Unavailable surfaces remain explicitly untested. Test a malicious preexisting project configuration and sandbox initialization failure.
5. Test whether code can relax its own protections or obtain an unsandboxed execution path. An operator-approved policy change is a different profile; an unprompted escape under the original profile is a gap.

**Done when:** Publish a minimal supported configuration per tested profile, a protection/caveat matrix, and a proposed startup capability check. A prompt is not a denial. Unsupported profiles must be detectable or explicitly selected with their weaker guarantees; do not claim arbitrary same-UID isolation.

## BV-03: Issuance, enrollment, and installation trust

**Question and decision:** What minimal SPIFFE implementation and enrollment protocol can issue short-lived workload credentials while keeping issuance authority outside workloads?

**Fixture:** One selected issuer candidate, a disposable agentd control-service prototype, two immutable workload/incarnation records, and a wrapper/resolver client. Compare candidate documentation only as needed to choose this first prototype; a general issuer bake-off is outside scope. Keep the installation's server CA, X.509 workload bundle, and JWT verification keys distinct in the fixture even if the selected implementation manages them together.

**Required cases:**

1. Generate the server CA once; restart and retain its identity. Issue and renew a correctly named server leaf without replacing the root. Verify private key permissions and that the kit receives only the public certificate.
2. Issue an X.509-SVID and an audience-bound JWT-SVID for A. Record SPIFFE ID, lifetime, key generation/custody, trust-domain layout, and how incarnation binding is authenticated. Do not assume it is automatically supplied by SPIFFE.
3. Specify how the trusted wrapper and host resolver are authorized on the control interface. Reject caller-selected B identity, role elevation, suspended-incarnation renewal, and application-socket attempts to issue credentials.
4. Renew successfully before expiry; exercise issuer outage, expired credentials, restart, and verification-key/bundle rollover with bounded overlap. Missing/corrupt CA state must not silently replace an established trust root.

**Review-derived qualification additions, 2026-09-28, proposed:** Compare the [binding candidates](identity-schema.md#authenticated-binding-is-an-implementation-gate) before selecting an integration. Under digest binding, test identical-claims rapid JWT issuance across generations, delivery-before-registration crashes, and every issuer-exposed non-broker path. Such credentials must be rejected unless the selected mechanism independently establishes their authorized binding. Record the inspected path inventory; a few passing requests do not prove completeness. Test wrapper/resolver refusal to fall back to operator credentials.

**Done when:** Produce the selected integration recipe, control-request/authorization contract, credential and principal shapes, renewal policy, and custody diagram. Clearly distinguish a custom broker protocol from the standardized SPIFFE Workload API. Full root-CA rollover automation is deferred; document its required distribution boundary.

## BV-04: Shared authentication and authorization

**Question and decision:** Can one workload API safely accept either X.509-SVID mTLS or JWT-SVID over server-authenticated TLS, producing the same principal and operation checks?

**Fixture:** A test HTTPS service with optional validated client certificates, BV-03 credentials, two workloads with different Group/role permissions, and a small request/stream endpoint. No production API implementation is required.

**Required cases:**

1. Accept each valid method and prove identical Group, role, incarnation, and operation enforcement. Reject an enrollment/infrastructure identity as a workload caller.
2. Reject absent credentials, malformed/expired JWTs, wrong signature, audience or subject, untrusted/expired client certificates, and valid credentials for an unauthorized workload or operation.
3. Present both methods, including conflicting identities and invalid-plus-valid combinations. Exercise the proposed rejection rule without silent fallback; record TLS-handshake versus HTTP rejection separately.
4. Validate agentd's expected identity on the wrapper path and conventional name/CA verification on the ordinary HTTPS path. Test wrong server identity, hostname, and CA.
5. Confirm the workload surface cannot reach management routes or select an arbitrary upstream destination. Exercise stream establishment and authorization context retention.

**Review-derived qualification addition, 2026-09-28, proposed:** Exercise resumed TLS sessions with expired, fenced, and cut-off authority, checking preserved original identity/binding and current authorization rather than assuming a full handshake is repeated.

**Done when:** Deliver a complete authentication matrix and common-principal contract. Choose a shared listener if qualified; separate listeners are acceptable only with the same authorization semantics and an explained compatibility reason. Docker compatibility is confirmed in BV-05/10, not inferred from a generic HTTP client.

## BV-05: sbx kit, routing, and server trust

**Question and decision:** Does the generated local kit suffice to reach a private-CA agentd endpoint through Docker's credential-injecting path, and what exact bootstrap is required?

**Fixture:** An isolated sbx test environment, generated public-CA kit, local HTTPS receiver, dummy secret, and disposable sandbox. Start with the user's kit proposal. Select and record a kit schema supported by the installed sbx version; do not mix syntax from different documentation generations.

**Required cases:**

1. Create headlessly with local kits enabled; test the disabled setting and required credential binding in an isolated configuration. Record a clear prerequisite failure rather than silently broadening policy. Repeated setup should reuse the installation CA and avoid duplicate bindings.
2. Compare a clean sandbox without the CA kit against one with it. Observe proxy path, receiver-side TLS/SNI, and whether injection occurred. Test a valid leaf, unrelated CA, wrong hostname, and expired leaf. Successful curl alone is insufficient evidence.
3. Test the source authentication page’s proposed `https://host.docker.internal:<agentd-port>` host-service route; no alternate hostname is selected. Record guest URL, DNS/dial destination, policy target, injection match, and upstream verification name independently.
4. Preserve Docker's existing proxy trust. Confirm kit contents contain the public CA only. Test leaf renewal and sandbox restart without reinstalling a new root.
5. Test the receiver requesting an optional client certificate while the proxy uses bearer authentication. Record whether that breaks the shared-listener proposal.

**Done when:** Supply a complete versioned kit and bootstrap recipe plus a trust-path matrix, or a reproducible blocker. Do not presume guest kit changes are propagated to the host proxy or presume they cannot be. If kit-only setup fails, identify the failing hop before testing a process-scoped host bundle in a separately recorded configuration. Wider OS trust changes are a follow-on choice, not an implicit requirement.

## BV-06: sbx token mediation, refresh, and destination scope

**Question and decision:** Does Docker's sandbox-scoped resolver provide fresh authority without letting a workload retrieve, redirect, or impersonate another workload's token?

**Fixture:** BV-05 transport, two sandboxes A/B, a host resolver using the BV-03 control fixture, short-lived JWTs, issuance counters, and controlled target/redirect receivers. Use immutable incarnation IDs in resolver bindings, not reusable names. The proposed `agentctl worker-token` can initially be a fixture executable.

**Required cases:**

1. Confirm A/B arrive with distinct principals while guest environment/files contain placeholders only. Swap placeholders and forge identity headers; B must never acquire A's principal.
2. Measure resolver invocations under on-demand refresh, concurrent requests, and any cache actually observed. Advance through real short expiry intervals; measure timing rather than assuming documented caching semantics.
3. Fail the resolver by timeout, nonzero exit, malformed output, control-service outage, and revoked incarnation. Observe whether Docker reuses cached values; agentd must reject expired or revoked authority regardless.
4. Test same-host wrong ports, other hosts, redirects, direct connections, and proxy bypass. Distinguish network permission from injection scope. No unintended receiver may obtain a real token; the legitimate API must not reflect Authorization into guest-visible responses or errors.
5. Recreate a sandbox name and restart the test daemon. Confirm stale bindings cannot enroll or represent a successor and record any credential material visible in guest-accessible diagnostics.

**Review-derived qualification additions, 2026-09-28, proposed:** Resume into a new incarnation, remove the predecessor’s resolver binding, and verify the new binding before activation. Measure resolver process count, signing latency, durable-write cost if applicable, and guest-triggered concurrency. Compare on-demand and bounded-cache candidates only after measuring remaining validity and cutoff behavior; agentd issuance limits do not by themselves bound host process spawning.

**Done when:** Publish resolver/binding commands, measured cache/failure semantics, destination restrictions, and the two-sandbox adversarial matrix. Choose a token lifetime from observed refresh behavior; do not solve an unknown refresh failure by assuming long-lived tokens.

## BV-07: Authority lifecycle and incarnation fencing

**Question and decision:** How do registration, renewal, suspension, resume, and recovery prevent obsolete processes or credentials from retaining authority?

**Fixture:** BV-04 service with an explicit lifecycle state machine, short-lived credentials, a request loop and persistent stream, plus each backend's qualified caller path. Use injected event delays and controlled crashes; simulate machine loss by loss of heartbeat/connectivity without shutting down the operator's machine.

**Required cases:**

1. Admit requests only after authorized readiness. Rotate credentials during activity; verify both new connections and existing streams follow the declared expiry/revalidation policy.
2. Suspend A and reject further work with still-unexpired credentials. Define and measure the bound for terminating or fencing existing streams and in-flight operations.
3. Resume into a new incarnation. Deliver delayed suspend/renew events from the predecessor, replay its credentials, and reuse its display name. None may affect or represent the successor.
4. Crash wrapper, harness, resolver, and agentd separately; test lost exit notification and reconnect. Distinguish viewer/attach-process exit from actual workload exit.
5. Define reconciliation after unknown outcome and retry. Do not replay work with external effects merely because observation was lost.

**Review-derived qualification additions, 2026-09-28, proposed:** Use the [canonical proposed state table](identity-schema.md#lifecycle-and-policy-records), including abandoned preparation and workload retirement. Exercise sleep/wake and clock discontinuities under each liveness candidate, identity-state rollback from backup, and fence-versus-message acceptance in the same transaction domain. Restore must not silently reinstate old authority; its recovery policy is a prerequisite for a supported backup-restore path.

**Done when:** Publish a state-transition table, authenticated incarnation representation, event ordering/idempotency rules, liveness timing, and measured failure traces. A declared stale-authority window needs an explicit decision; credential rotation alone does not count as fencing.

## BV-08: Runtime and launcher lifecycle with storage

**Question and decision:** What minimal backend/Launcher contract supports host and sbx workloads without conflating terminal attachment, harness lifetime, and native conversation state?

**Fixture:** One shared disposable workspace, private state for A/B, host wrappers launched directly and in tmux, and sbx workloads. Begin with deterministic long-running commands and repeat lifecycle-sensitive cases with real harnesses. No terminal frontend is needed.

**Required cases:**

1. Prepare, create, launch interactively, launch headlessly, observe readiness, collect output/exit status, cancel, and clean up. Record unsupported operations and partial-creation rollback.
2. Disconnect/kill the attach process, reconnect, and restart the controller. Identify which events terminate the harness, wrapper, VM, or authority; reconcile with BV-07.
3. Resume a native conversation separately from reattaching a live process. Define mapping among workload ID, incarnation, sandbox name, and harness conversation ID.
4. Confirm shared workspace changes and private harness-state retention across stop/start and resume. Test A's access to B's private state under each supported profile; shared files are deliberately not a private-state boundary.
5. Exercise concurrent creation/name collision, repeated cancellation/cleanup, and an interrupted provisioning sequence. Report retained artifacts and avoid deleting unrelated workspace data.

**Done when:** Produce a per-backend capability table and minimal prepare/launch/observe/cancel/resume/cleanup contract, including storage ownership and recovery limits. Do not require tmux or an exec operation to supply native resume semantics.

## BV-09: Terminal observation and attachment

**Question and decision:** Which terminal owner and attachment adapter can preserve a real harness session through viewer disconnect while supporting the [terminal contract](mental-model.md#terminal-attachment-and-ui-streaming)?

**Fixture:** BV-08 interactive workloads, a minimal browser-compatible transport and terminal viewer or protocol client, two observers, and one controller. Reuse existing PoC terminal evidence where its versions/topology match. Full Tauri packaging and remote deployment are out of scope.

**Required cases:**

1. Detach/reconnect to the same live PTY; capture output generated while detached and verify redraw/history restoration with an actual harness TUI. New shell creation is not reattachment.
2. Stream authoritative dimensions and lifecycle status. Exercise resize, controller handoff, and two simultaneous observers.
3. Enforce read-only access at the server: reject input, resize, signals, and terminal-generated responses from observers. Verify workload credentials and runtime-management endpoints never enter the viewer.
4. Slow/disconnect a viewer and exceed bounded output retention. Keep the harness progressing and signal/resynchronize lost state explicitly.
5. Restart the attachment service/controller and report what survives. Distinguish terminal replay, transcript persistence, and native conversation recovery.

**Done when:** Select a terminal owner/adapter per qualified backend and publish reconnect, ownership, backpressure, retention, and authorization behavior. Qualify the minimum read-only milestone separately from interactive control; a failed advanced feature need not invalidate working read-only streaming.

## BV-10: Composed two-workload acceptance

**Question and decision:** Do the individually qualified pieces still satisfy their guarantees when assembled for each supported backend/harness profile?

**Fixture:** Two workloads per backend using the actual selected issuance, gateway/injection, and lifecycle components, plus an agentd-like API implementing the chosen principal contract. Use the supported configuration from prior spikes; identify any remaining stub explicitly.

**Required cases:** Perform legitimate peer operations, cross-workload attempts, management-access attempts, renewal across expiry, suspension of a live stream, crash/reconciliation, and resume into a new incarnation. Run concurrent A/B activity so identity mixing cannot hide behind serial tests. Confirm headless outcome capture and interactive reconnect where those capabilities are claimed.

**Done when:** Produce a supported-profile matrix, linked evidence for every required property, remaining blockers, and a proposed implementation sequence. Re-run only composed boundaries and changed assumptions; do not duplicate every earlier low-level test. No backend becomes qualified solely because another backend passed. Update the destination wiki with measured conclusions after review; keep raw probe scripts/results and issue status in the PoC.

## Coordinator handoff

Seed BV-01 through BV-10 as bounded work, linking or splitting existing issues rather than duplicating them. Preserve prerequisites and distinguish discovery completion from product acceptance. The deliverable is a reconciled spike map and the evidence needed to decide supported recipes, not a commitment to ship every prototype.

The [authentication design](spiffe-mtls-authentication.md) owns the current intended security contract; [supervisor protection](supervisor-protection.md) supplies adversarial test leads; the [runtime survey](local-sandbox-runtimes.md#contract-implications) and [mental model](mental-model.md#task-lifecycle-and-backend-contracts) supply lifecycle and attachment questions. Their older custom-sandbox and broader platform investigations do not expand this page's initial scope.
