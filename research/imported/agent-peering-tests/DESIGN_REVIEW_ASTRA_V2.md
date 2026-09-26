# Review of DESIGN_V2.md

Reviewed 2026-09-23. References below use the line numbers in the reviewed `DESIGN_V2.md` (SHA-256 `eb3f8f214e3c13049009fefb2b869e5028881c75eba829a08389fdc1773aedf6`).

V2 resolves much of the first review: the process-tree principal is explicit, confidentiality is excluded, operator-issued enrollment replaces self-claimed identity, server trust has a bootstrap source, and durable records are separate from process bindings. Moving message delivery and receive-loop behavior into a separate design is also reasonable.

The remaining blockers are concentrated at the trust boundaries. Direct TCP is configured but not enforced by the C2's acceptance rules. Project configuration in the shared worktree can widen a peer's sandbox. The exhaustive socket-holder lookup still needs an implementable contract under ordinary operator privileges. I would resolve these before calling the design an authentication boundary.

## Evidence and scope

I compared V2 with the first Astra review and the other supplied reviews, inspected the unchanged attribution prototypes, and checked the relevant local source snapshots:

- `anthropics/sandbox-runtime`: `ddbeb74711c4097014ef3056791efa83f553116c`.
- `openai/codex`: `c44deff7b1083e9660ac55d02122481f1cdf139b`.

I also consulted current Claude Code documentation and Apple's published XNU/libproc sources and keychain documentation. These sources establish implementation details or documented behavior; they do not establish the effective configuration of the user's machine. Where those conflict, this review calls for a version-specific test rather than declaring a live compromise.

No sandbox settings were changed, credentials inspected, cross-session connections attempted, or live impersonation tests run. The registration contradiction below was checked as a two-case logical model; there is no V2 implementation here to integration-test. The existing Python programs still test ancestry attribution, not TLS, enrollment, persistence, or activation.

**Severity:** P0 blocks the claimed security guarantee in an affected supported configuration. P1 is a protocol, feasibility, or recovery issue to resolve before relying on the design. Conditional attacks are labeled as such.

## Findings

### 1. P0 — Direct TCP must be an admission rule, not just the CLI's preferred route

**References:** lines 64–74, 86–101, 107–109, 313–319.

The main lookup contract accepts any socket holder whose ancestry reaches a live binding. That includes the registered harness itself when it acts as a proxy. Saying that the supported CLI connects directly does not prevent a different client from connecting through that proxy.

A conditional counterexample is:

1. B's harness still hosts its sandbox proxy, and that proxy permits CONNECT to the C2.
2. A can reach the proxy and has obtained its credential, for example from a readable diagnostic transcript. For an unauthenticated relay, the credential prerequisite disappears.
3. A tunnels pinned TLS to the real C2 through B.
4. The C2 finds B as socket owner, reaches B's binding, and accepts A's request as B under the stated rules.

All TLS checks succeed. The nested-harness rule finds no intervening harness. The optional chain-shape policy is not enabled by default. The appendix checks are also not required in the main configuration.

The inspected sandbox-runtime source adds loopback access when `allowLocalBinding` is enabled; that flag is not a prohibition on proxy use. Its proxy initialization and CONNECT authentication remain separate code paths. See [loopback rules](https://github.com/anthropics/sandbox-runtime/blob/ddbeb74711c4097014ef3056791efa83f553116c/src/sandbox/macos-sandbox-utils.ts#L1147-L1170), [proxy initialization](https://github.com/anthropics/sandbox-runtime/blob/ddbeb74711c4097014ef3056791efa83f553116c/src/sandbox/sandbox-manager.ts#L932-L956), and [CONNECT handling](https://github.com/anthropics/sandbox-runtime/blob/ddbeb74711c4097014ef3056791efa83f553116c/src/sandbox/http-proxy.ts#L425-L461).

**Change:** Add a mandatory transport-origin rule for messaging. At minimum, reject ownership by the bound harness itself in the direct-only profile. Define how other unconfined relay processes beneath a harness are rejected too; requiring confined tool-call holders is a candidate for the stated deployments, subject to validation. An unsupported proxy path must be rejected, not merely labeled lower assurance. No request field may opt into a weaker mode.

**Pass condition:** With direct access enabled, deliberately attempt the proxy route from another test peer using a fixture credential. It must be rejected even when the proxy allows the destination. Test every supported harness's relay, including relays without credentials. A successful direct-path happy test is insufficient.

### 2. P0 — Project configuration in a shared worktree must be protected and validated

**References:** lines 226–240, 262, 272.

Project scope can do more than add hooks. Current Claude Code documentation distinguishes booleans from arrays: arrays such as `excludedCommands` merge across loaded scopes, and `excludedCommands` has no managed-only lockdown. It also documents separate controls for managed-only read paths and domains. A project settings file can therefore widen the sandbox policy set at user scope. See [Keep developers from widening the policy](https://code.claude.com/docs/en/sandboxing#keep-developers-from-widening-the-policy).

If another peer can write a loaded project config, appending an excluded command could make a subsequent tool call execute without confinement. This is a conditional break: I have not verified it against the installed version.

The write-deny mitigation also needs an initial-content rule. Denying future writes to `.claude/` does not make already-present settings trustworthy, including settings checked out before launch. And a Bash-only write denial does not establish that every native editing tool, connector, or other peer is unable to modify protected configuration.

**Change:** Record effective values and the behavior of each security-relevant key, not only which settings file contains it. Either avoid loading untrusted project settings or protect and validate all loaded configuration sources. Apply the requirement to every write-capable tool. Unconfined execution caused by an in-scope peer's config change must not be dismissed as the excluded arbitrary same-UID attacker.

**Pass condition:** In an isolated fixture matching the installed version, append a harmless marker command through project settings. Verify the resulting command remains confined or the override is rejected. Separately test initial config content, live updates, and writes from each peer/tool type.

### 3. P1 — “Every holder” and “a single snapshot” remain unproven implementation requirements

**References:** lines 54, 88–97, 275.

The revised contract correctly rejects incomplete information, but does not explain how an ordinary same-UID C2 can obtain complete information in the first place. Enumerating all processes requires considering processes belonging to other users; skipping them assumes the very absence of foreign holders the algorithm promises to prove.

Apple's published XNU implementation checks caller credentials for process fd inspection and ordinarily rejects other-UID targets without the relevant privilege. Being outside a sandbox does not confer that privilege. The libproc interface also exposes PID enumeration and per-PID information calls separately; the named APIs do not themselves specify one atomic process-and-fd snapshot. See [XNU process-info access checks](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/proc_info.c) and [libproc wrappers](https://github.com/apple-oss-distributions/xnu/blob/main/libsyscall/wrappers/libproc/libproc.c).

Read literally, rejecting any unreadable table may reject ordinary traffic on a normal machine. Read narrowly, “needed for the answer” leaves unspecified how an unreadable process is ruled out. Recording start times is useful, but values sampled from successive processes do not automatically prove that all parent relationships coexisted.

**Change:** Prototype this contract before optimizing its cost. Specify the candidate process set, the evidence that excludes other processes, the supported socket-transfer assumptions, and the consistency checks between socket identification and ancestry resolution. Distinguish a collected table from an atomic snapshot. Narrow the assurance claim if the APIs cannot support it; do not silently skip unreadable candidates or default to running the whole C2 as root.

**Pass condition:** An operator-privilege implementation accepts an ordinary direct call on a machine with system daemons, and explains why every omitted process cannot affect the result. It rejects ambiguous relevant holders and inconsistent observations during fork/exit/PID churn. Passing only synthetic complete-table tests is insufficient.

### 4. P1 — The shared lookup contract makes first-time registration impossible as written

**References:** lines 86–97, 159–165.

The lookup contract requires every caller to resolve to a live binding. Registration calls that lookup and then rejects a wrapper descending from a live binding. A fresh operator-launched wrapper has no binding, so it fails the lookup; a wrapper under a bound harness fails the registration ancestry check. The protocol needs an explicit bootstrap branch.

This is a specification contradiction, not evidence of an implementation bug. The obvious intent is sound: kernel ownership identifies the wrapper, while a token authorizes creation of its first binding.

**Change:** Split kernel connection/process attribution from authorization. Registration must identify an unambiguous wrapper process, apply UID, confinement, worktree, token, and ancestry rules, and then create a binding. Messaging must resolve an existing active binding. Define registration's handling of multiple holders directly; it cannot use “all resolve to the same binding” before that binding exists.

**Pass condition:** A fresh operator wrapper registers successfully; a confined wrapper, a registered descendant, and an ambiguous multi-holder registration are rejected. Keep these distinct from the post-registration messaging tests.

### 5. P1 — The generated launch command contradicts the trusted-path requirement

**References:** lines 153, 166–167, 219–222.

The REPL prints `agent-work start ...`, while deployment requirements correctly explain why looking up `agent-work` on `PATH` from an agent-writable worktree is unsafe. The copied command is the actual enrollment ceremony. It must not depend on the operator remembering to replace its executable or having installed a suitable alias.

The harness allowlist helps only after the real wrapper is running. A planted wrapper selected by the shell executes first, outside confinement, and receives the token. Similarly, “absolute path outside the worktree and `$TMPDIR`” is not sufficient if its symlink target, executable, interpreter dependencies, or parent directory remain writable by a peer.

**Change:** Print the shell-quoted, trusted absolute wrapper path in every launch/resume command. Require the wrapper, C2, harness executables, their resolved targets, and relevant executable dependencies to be outside every peer's write access. Document the trusted-launch environment, including any directory hooks that execute before the wrapper. Scope the check to the actual packaging rather than adding a speculative universal launcher framework.

**Pass condition:** Put a harmless same-name executable first on a fixture `PATH`; the copied command still selects the trusted wrapper. A configured absolute path resolving into peer-writable storage is rejected before token redemption.

### 6. P1 — Keychain storage does not yet specify who may use the server key

**References:** lines 41, 50, 58, 115–120, 222.

The design now intentionally allows broad peer reads, while placing only an optional read-deny requirement on operator state. That is compatible with public endpoint metadata and logs, but the server's private key still requires an enforceable access boundary. Keychain storage is a location/API choice, not the complete access policy.

The inspected Claude sandbox profile permits lookup of `com.apple.securityd.xpc`; therefore lack of direct file access to a keychain does not alone prove the key is unusable through its service. This does **not** demonstrate access to the C2 key. Apple's keychain documentation describes access control for protected items and distinguishes macOS keychain implementations. See [sandbox Mach-service rules](https://github.com/anthropics/sandbox-runtime/blob/ddbeb74711c4097014ef3056791efa83f553116c/src/sandbox/macos-sandbox-utils.ts#L985-L1004), [Keychain access control lists](https://developer.apple.com/documentation/security/access-control-lists), and [TN3137](https://developer.apple.com/documentation/technotes/tn3137-on-mac-keychains).

A peer able to use the key for TLS signing need not export it to defeat the port-squatting defense. If the C2 is interpreter-based, the access policy also needs to distinguish trusted C2 use from other code using the same interpreter identity.

**Change:** Specify the keychain implementation and item access policy for signing and export, as well as any private-key materialization required by the TLS library. Public state may remain readable; private key material and unauthorized signing must be inaccessible. Resolve the inconsistency between the state directory being “not reachable” and its read denial being optional. Define deliberate recovery for key loss or rotation instead of silently teaching existing peers a new pin.

**Pass condition:** Using a disposable C2 identity, show that each supported sandbox cannot export or sign with its key or use a copied C2 executable to obtain key access. Test the packaged implementation without authorizing a new keychain prompt. The trusted C2 must still restart successfully.

### 7. P1 — Token redemption needs a transaction and a lost-response recovery rule

**References:** lines 129–133, 147–167, 196–198, 276.

The C2 consumes the token and binds the wrapper before the wrapper resolves the executable and execs it. Two routine failures expose missing transitions:

- The C2 commits redemption, but its response is lost. Retrying encounters a used token and an already-bound process. Without a same-process retry rule, “the CLI retries” is not sufficient.
- Executable validation or exec fails after redemption. The token is spent, a bound peer may remain until exit is detected, and the group can wait for activation that will never occur.

Single use is also a persistence property. Token consumption, binding installation, and generation advancement must not be partially restored after a C2 crash. Multiple independently issued tokens for one peer require peer-level exclusion; testing two redemptions of the same token covers only one race.

**Change:** Resolve and validate the executable before spending the token. Atomically persist token consumption and the new binding/generation. Permit redemption-result recovery only for the same authenticated wrapper instance, or explicitly require an operator recovery flow. Invalidate outstanding enrollment tokens when a peer is removed or rebound, and reject redemption against an obsolete expected generation. Define cleanup for failed exec and token expiry/reissue.

**Pass condition:** Drop the redemption acknowledgment, fail exec, crash between persistence steps, race two different tokens for one peer, and redeem a token after removal. There is at most one binding, consumed tokens do not revive, and the operator can recover without editing registry files.

### 8. P1 — Unknown liveness must not become permission to resume

**References:** lines 129–143, 196–200.

On startup, an indeterminate liveness result drops the binding. Resume is then forbidden only while the old binding's process is alive. The durable record does not contain the old process tuple, so dropping it can also discard the information required to enforce that rule.

For example: an inspection failure occurs while the old harness is still running; C2 restarts, drops its binding, and then sees a disconnected peer eligible for a new token. This need not give two processes valid messaging identities—the revoked old process should be rejected—but it violates the stated deliberate-kill requirement and leaves the operator with a misleading process state.

**Change:** Invalidate authorization on uncertainty, but retain the last process identity and mark its liveness unknown. Require positive evidence of exit or an explicit operator revoke/replace decision before resume. Keep the generation counter durable even when no live binding exists. At redemption, recheck peer state and the token's expected generation, rather than relying only on conditions at issuance.

**Pass condition:** Inject a process-inspection error while the old harness is alive, restart C2, and request resume. Messaging is denied under the uncertain binding, but automatic replacement remains blocked and the REPL explains why. Generation values never reset after restart or binding deletion.

### 9. P1 for the optional path — The appendix does not establish secret-free, per-command attribution

**References:** lines 313–321.

The nonce proof depends on the adversary being unable to learn the nonce. If A knows the PID and nonce of B's pending client, A can name that existing process; it does not need to create a new process carrying a chosen nonce. Kernel-visible presence proves that the process exists with those arguments, not that this particular tunneled request came from its socket. The claim that the mechanism uses no secret is therefore inaccurate. Process-inspection denial also does not cover nonce disclosure through readable diagnostics or transcripts.

The census supplies a separate check, but it enumerates only established connections, not a proven association between the accepted C2 socket and a specific proxy ingress. Half-close, buffered data, and asynchronous teardown need explicit treatment. The inspected proxy deliberately supports half-open established tunnels. A missing foreign client in a later census is not by itself proof that no foreign client supplied buffered bytes. See [proxy tunnel forwarding](https://github.com/anthropics/sandbox-runtime/blob/ddbeb74711c4097014ef3056791efa83f553116c/src/sandbox/http-proxy.ts#L591-L614).

Finally, “act, and confirm the tunnel is still open before replying” puts that check after the side effect. Suppressing the reply cannot undo an unauthorized log append. This is a missing proof and test requirement, not a demonstrated end-to-end exploit of both appendix checks.

**Change:** Since the supported configuration does not need the appendix, mark it as an unimplemented research proposal and reject that transport in V2. If retained later, explicitly treat the nonce as a short-lived secret, specify freshness and replay handling, and prove the mapping from the current request to its originating client. Make all authorization predicates hold before commit; a post-commit liveness check is not authorization.

**Pass condition:** Test known-nonce replay while a legitimate receive is pending, FIN/half-close, fully closed ingress with buffered request data, concurrent clients, and census churn. Neither a forged message nor a consumed legitimate nonce may be accepted before a failed check is noticed.

## Smaller clarifications

- **Activation and readiness:** Lines 178–180 both return context and subsequently block the same call. Define a streamed protocol or separate activation and readiness calls. Also state whether bound-but-inactive peers may send/receive and whether `join` is idempotent. A post-approval session-ID mismatch should have an explicit continue/pause policy; it is not authentication failure by itself.
- **Harness launch topology:** Keeping the wrapper PID through its own exec does not guarantee every packaged harness keeps that PID as the long-lived ancestor. Retain a launch/exit test for each allowed executable, including GUI launchers. A short-lived launcher must not silently leave an approved peer unusable.
- **Unauthenticated resource limits:** Line 248 bounds lookups “per binding,” but a connection has no binding before lookup. Add global pre-authentication connection, handshake, lookup, and queue limits. This is ordinary resource control, consistent with excluding adversarial denial of service.
- **Support status:** The transport introduction claims every harness already uses direct TCP, while the table still says the Claude Code setting is to be applied and the Codex setting is unrecorded. Label required profiles separately from verified profiles. Remove Linux implementation details from the normative macOS contract or label them future work.

## What is resolved, and what to do next

| V1 concern | V2 assessment |
| --- | --- |
| Unclear principal and confidentiality promise | Resolved at the design level. Executed code belongs to the session principal; peer secrecy is excluded. |
| Nested-harness detection treated as security | Resolved by labeling it a policy hint. Do not reintroduce it as a primary control. |
| Pin learned from an untrusted first connection | Resolved by operator-state bootstrap, subject to trusted launch and private-key access requirements above. |
| Dead registry records erase resume identity | Resolved by durable peer records. Unknown liveness and redemption recovery still need explicit handling. |
| Old waiters survive rebinding | Generation fencing is the right design. Persistence and all lifecycle transitions need tests. |
| TLS confused with application delivery semantics | Correctly separated. Delivery and background wakeup remain requirements for the separate messaging design, not additional findings against this document. |
| Proxy-based impersonation | Normal transport changed, but adversarial proxy admission remains open under the written lookup rules. |

The next useful milestone is a small macOS implementation of attribution and registration, before building the full messaging system. It should demonstrate an ordinary operator launch, mandatory rejection of proxy-originated messaging, feasible owner enumeration, and crash-safe single-use enrollment. In parallel, capture effective sandbox settings and settle the project-settings merge behavior for the exact supported versions. Keep the proxy appendix disabled until it has its own defensible protocol and tests.
