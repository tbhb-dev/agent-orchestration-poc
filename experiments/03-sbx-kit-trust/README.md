# BV-05: sbx kit routing and server trust

## Decision

**Partial investigation, unresolved blocker:** the installed sbx CLI and pinned Docker documentation support a schema v2 public-CA kit proposal, but no state-changing probe ran. The operator's 2026-09-27 decision requires a concrete proposal before a probe changes daemon state, local-kit settings, process-scoped trust, or OS trust. This gate covers the disposable sandbox and daemon work needed to answer cases 1 to 5. Case 6 also lacks a fixture that runs sbx transport. The generated kit's upstream trust effect, injection path, optional client-certificate compatibility, and hold-time remain untested. Issue #229 remains open and no backend profile is qualified.

## Bounded profile and topology

The proposed profile is local sbx v0.45.1 on macOS 26.5.1 arm64, with no real harness, an isolated daemon/configuration, a disposable private CA, a loopback HTTPS receiver, a dummy bearer value, and one disposable sandbox. The intended guest URL is exactly `https://host.docker.internal:<agentd-port>`. The receiver represents agentd only for transport testing. It does not grant a workload identity or handle message delivery.

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

No executable fixture is committed because an isolated sbx daemon/configuration path has not been established from the pinned documentation or installed CLI help. `sbx settings` can start the local daemon even for a read. A template that silently targets the operator's daemon would make the experiment irreproducible and cross the operator boundary. The next operator proposal must identify where disposable daemon state and settings live. It must also specify cleanup before any `sbx create`, `sbx settings`, `sbx secret`, `sbx policy`, or `sbx kit` operation with possible daemon effects runs.

After that boundary is established, generate a persistent disposable CA and keep only its public PEM in the kit's `files/home/` tree. Use schema version 2, `kind: mixin`, an `apiKey` injection declaration for the exact host-service destination, and a separate network allow rule. Install the CA by adding it to the sandbox's existing system trust with `update-ca-certificates`. Do not replace the guest bundle. Set up the dummy binding once, record the CA fingerprint and issuance count, and check reuse on repeated setup. Run an untrusted-leaf rejection before installing the kit. The concrete command sequence needs the isolated daemon path and binding interface confirmed first. The private key and dummy bearer value must remain outside committed evidence.

The test matrix then varies only the receiver leaf and CA, recording guest URL, proxy path, receiver SNI and dummy injection marker for each run. Repeat after leaf renewal and sandbox restart without regenerating the root. Test optional client-certificate negotiation on the same HTTPS listener. For the bounded wait, use a fixture endpoint that holds a non-consuming request for a measured interval and emits a distinct timeout or disconnect marker. Record delivery-evidence state before and after timeout and reconnection. None of those runtime observations can be inferred from the static evidence here.

## Evidence and cleanup

[Versions](versions.md) and [read-only evidence](evidence/read-only.md) record what was actually checked and the required-case status. There is no before/after daemon or trust-state diff because no such state was touched. No credential, token, private key, sandbox, or receiver was created. The local `mise run vale:sync` setup completed successfully. This work did not change host configuration.
