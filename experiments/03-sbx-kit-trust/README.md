# BV-05: sbx kit routing and server trust

## Decision

**Partial investigation, reproducible local blocker:** the operator approved the local-kit setting probe and creation of clean and kit sandboxes on the installed sbx on 2026-09-28. A process-scoped host bundle was conditional on identifying a kit-only failure hop. Before any mutation, `sbx ls --json` returned `Not authenticated to Docker`, and `sbx settings get --json kit.allowLocalKits` could not start the stopped daemon because this worker's sandbox denied opening the daemon stderr log. The initial setting override and sandbox list could not be established. Changing the setting could erase a pre-existing override on undo, so no stateful probe ran. [The before and after ledger](evidence/operator-state-attempt.md) records the commands, exit codes, and remaining uncertainty. The generated kit's upstream trust effect, injection path, optional client-certificate compatibility, and sbx hold-time remain untested. Issue #229 remains open and no backend profile is qualified.

## Bounded profile and topology

The proposed profile is local sbx v0.45.1 on macOS 26.5.1 arm64, with no real harness, a disposable private CA, a loopback HTTPS receiver, a dummy bearer value, and disposable clean and kit sandboxes. The operator authorized the installed sbx rather than an isolated daemon/configuration for this continuation. The intended guest URL is exactly `https://host.docker.internal:<agentd-port>`. The receiver represents agentd only for transport testing. It does not grant a workload identity or handle message delivery.

The intended path has two TLS hops: guest to Docker's credential proxy, then Docker's host proxy to the receiver. The guest must retain Docker's existing proxy certificate trust. A generated public-CA kit can add guest trust for direct or bypass paths, but its effect on host-proxy upstream trust is the question under test. A successful guest HTTP response alone would leave injection unproven. Receiver SNI and upstream verification need separate evidence.

## Trust-path matrix to fill during the authorized run

| Hop | Name and trust question | Evidence required | Status |
| --- | --- | --- | --- |
| Guest URL | `host.docker.internal:<agentd-port>` | Exact URL and guest DNS result | Untested |
| Guest to proxy | Docker proxy certificate | Guest verification and `sbx policy log` proxy path | Documented path, runtime untested |
| Proxy policy | `localhost:<agentd-port>` after translation | Effective allow rule and dial destination | Documented translation, runtime untested |
| Injection | Kit service/domain match | Placeholder at guest and dummy value fingerprint at receiver | Untested |
| Proxy to receiver | Disposable CA and DNS SAN | Receiver TLS/SNI, leaf chain, verification name, and negative controls | Untested |
| Optional client certificate | Bearer request on shared listener | TLS handshake and application authentication result | Untested |

## Fixture and execution boundary

No executable fixture is committed because the approved installed-sbx probe stopped at its before-state check. `sbx daemon status` reported stopped before and after. The settings read tried to start sandboxd and failed at the sandbox boundary, while `sbx ls` reported missing Docker authentication. The worker could not establish whether a `kit.allowLocalKits` override or either proposed sandbox name already exists. The required undo is `sbx settings unset kit.allowLocalKits`, which would not restore an unknown pre-existing override. No setting, sandbox, daemon, credential, or trust-store mutation was attempted.

After access to the approved installed sbx is established and its starting state is recorded, generate a persistent disposable CA and keep only its public PEM in the kit's `files/home/` tree. Use schema version 2, `kind: mixin`, an `apiKey` injection declaration for the exact host-service destination, and a separate network allow rule. Install the CA by adding it to the sandbox's existing system trust with `update-ca-certificates`. Do not replace the guest bundle. Set up the dummy binding once, record the CA fingerprint and issuance count, and check reuse on repeated setup. Run an untrusted-leaf rejection before installing the kit. The private key and dummy bearer value must remain outside committed evidence.

The test matrix then varies only the receiver leaf and CA, recording guest URL, proxy path, receiver SNI and dummy injection marker for each run. Repeat after leaf renewal and sandbox restart without regenerating the root. Test optional client-certificate negotiation on the same HTTPS listener. For the bounded wait, use a fixture endpoint that holds a non-consuming request for a measured interval and emits a distinct timeout or disconnect marker. Record delivery-evidence state before and after timeout and reconnection. None of those runtime observations can be inferred from the static evidence here.

## Evidence and cleanup

[Versions](versions.md), the [original read-only evidence](evidence/read-only.md), and the [operator-state attempt](evidence/operator-state-attempt.md) record what was checked. The operator-state ledger supplies a case table with expected and actual behavior. The before-state check ended before fixture creation or any undo. The daemon's stopped status matches the starting observation, but the sandbox list and effective settings remain unknown, so full installation-state equivalence cannot be confirmed. The local `mise run vale:sync` setup completed successfully.
