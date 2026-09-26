# Design review: agent-work peer authentication and registration

Reviewed 2026-09-23 against `DESIGN.md`, `c2.py`, and `peer.py`.

The design is a promising way to attribute ordinary tool calls without distributing client secrets, but it does not yet establish the adversarial peer-isolation guarantee it claims. The largest unresolved issue is whether a peer can cause traffic to originate from another registered process, especially its proxy. A correct socket-owner lookup would then authenticate the wrong originating session by design.

Keep the separation between process registration, operator-approved role assignment, and server authentication. Before treating the system as an authentication boundary, specify the sandbox capabilities it requires, close the proxy question, and define identity lifetime across process death and C2 restart.

## Scope and evidence

This is a design review, not a completed penetration test. I inspected both prototypes and ran isolated Python checks against the existing recognition and Linux lookup functions with synthetic process/socket data. I did not start harness sessions, test live cross-session proxy access, benchmark libproc, or reproduce the document's historical integration tests. Platform facts below are linked to primary specifications or the Linux man-pages project; harness behavior remains a deployment-specific assumption until tested.

The prototypes test socket attribution and ancestry reporting. They do not implement TLS, registration, process-start-time validation, join approval, persistence, resume, worktree authorization, or message delivery. Their `ACCEPT` result means that a recognizable ancestor was found, not that the proposed authentication protocol has passed.

Priority meanings: **P0** blocks the stated security guarantee; **P1** needs resolution before implementation is relied upon; **P2** is an operational or specification gap. Conditional attacks are identified as such.

## Findings

### 1. P0 — The threat model needs a capability boundary, not a distinction between agent and non-agent processes

**References:** `DESIGN.md:23–29`, `95`, `125–129`, `151`.

An agent can execute an arbitrary helper process. Excluding malicious same-UID processes that “aren't agent sessions” must not exclude those helpers, or the exclusion removes the principal attack surface. Conversely, an unsandboxed agent with the operator's file and process access can exercise the same attacks the document excludes for other same-UID processes.

Protecting the log against writes is insufficient for the stated goal of preventing peers from reading each other's messages. Its contents, pending queues, registry, backups, and diagnostic output also need protection against unauthorized reads. The server key, trusted pin source, C2/CLI executables, and their configuration need appropriate protection too. A keychain storage location alone does not specify which processes may request use of the key.

Shared writable code introduces another limit: if peer A can modify a helper that peer B subsequently executes, the resulting traffic really does originate under B. Attribution cannot prove which model intended that request. This is distinct from message-content prompt injection and needs an explicit scope decision.

**Recommendation:** Define an adversarial peer as the harness plus any code it can execute or cause to execute. Specify supported sandbox profiles and their required filesystem, process, IPC, network, and escalation restrictions. Explicitly state whether shared-code execution is trusted or outside the guarantee. Unsupported or unrestricted profiles should be described as cooperative attribution, not peer isolation. Do not infer a security property solely from whether a process is called an agent.

**Acceptance test:** From each supported profile, attempt to read another peer's queued/logged messages, modify trusted configuration or executable inputs, use the C2 key, and reach another harness's control interfaces. Record actual restrictions and any approval path that changes them.

### 2. P0 — Proxy isolation is a prerequisite for authentication, including access from other harness types

**References:** `DESIGN.md:111–121`, `144`.

If A can issue CONNECT requests through B's proxy, the C2 will observe B's harness as the socket owner and assign B's role. A can run TLS through that tunnel using the public server pin. Server pinning prevents a fake C2; it does not establish who initiated a tunnel through a genuine peer's proxy.

The proposed test of Claude session A against Claude session B is necessary but incomplete. The document also expects Codex and Antigravity to reach localhost directly. Their ability to reach a Claude proxy must be tested. Likewise, A's own proxy might be able to CONNECT to B's loopback proxy even if A cannot do so directly. This is a conditional attack, not a demonstrated property of the current sandboxes.

Blocking launch of a nested harness does not solve the issue: a short socket client is sufficient. Nor does more accurate ancestry inspection at the C2 recover the origin lost at the proxy.

**Recommendation:** Promote this open question to a release gate. Accept proxied attribution only for a verified profile in which other peers cannot use that proxy, directly or transitively. If that cannot be established, use an isolation boundary or a trusted relay that authenticates its ingress; otherwise remove the isolation claim for that transport.

**Acceptance test:** Build a source-profile × destination-proxy matrix covering same-harness and mixed-harness pairs, separate worktrees, direct loopback, and chained CONNECT. An unauthorized attempt must fail before a request can be accepted as B. A port being undisclosed is not a pass condition.

### 3. P1 — An ancestry walk is not an atomic proof of the connection's origin

**References:** `DESIGN.md:43–52`; `c2.py:43–98`, `111–137`.

The statement that the client blocks and therefore its owner stays alive describes the cooperative CLI. An adversarial client need not follow it. Socket holders and process ancestry can change while separate kernel queries are running. Checking only the registered harness's start time leaves intermediate process identity and ancestry observations unspecified. Repeating a scan can detect some changes, but does not by itself create an atomic snapshot.

There are also concrete prototype limitations:

- Linux lookup compares only the two ports, not either address or socket state. A synthetic row for `127.0.0.2:50000 -> 127.0.0.1:47322` was selected for a lookup intended for a client at `127.0.0.1:50000`. This demonstrates an incorrect selection primitive, not a complete TLS impersonation exploit.
- The `/proc` scan silently skips inaccessible processes and returns the readable holders. An isolated check with one readable holder and one unreadable process returned the readable PID with no indication that enumeration was incomplete. It therefore cannot substantiate “every holder” from that result alone.
- The lookup API returns one UID for a list of holders. The macOS parser overwrites that UID as it processes matching records; neither interface expresses verified per-holder credentials.

`sock_diag` provides socket identity information, including UID and inode, but its documented Internet-socket response does not provide the complete holder PID list. It cannot simply replace the process-to-fd association step. See [sock_diag(7)](https://man7.org/linux/man-pages/man7/sock_diag.7.html).

**Recommendation:** Specify the exact lookup contract: address family, full local/remote tuple, relevant network namespace, socket identity/state, per-process start identity and credentials, visibility requirements, and handling of races or incomplete results. Reject uncertain attribution. Explain which sandbox restrictions prevent socket transfer and cross-peer relaying; the “all holders” rule alone cannot prove who supplied the bytes. If the available OS APIs cannot establish the required property, narrow the claim rather than treating enumeration as a credential primitive.

**Acceptance test:** Exercise address collisions, fork/close during lookup, intermediate-parent exit, PID churn, unreadable fd tables, socket handoff where permitted, and namespace differences. Valid traffic may fail closed during churn; uncertain traffic must never inherit another peer's identity.

### 4. P1 — Executable names and current ancestry do not enforce main-session-only access or operator-originated registration

**References:** `DESIGN.md:47`, `52`, `77–80`, `107`, `123`; `c2.py:140–163`.

Names can identify ordinary launch forms, but a renamed harness or an unrecognized launcher still executes within the registered ancestor's tree. The nested-harness rule would miss it. The existing matcher also accepts unrelated prefixes and misses interpreter options before a script. This is consistent with a diagnostic heuristic, not an adversarial boundary.

Current ancestry is not permanent launch provenance. For example, Linux reparents orphaned processes to a surviving subreaper or namespace init. An agent-originated helper that loses its harness ancestry can cease to satisfy the proposed registration rejection rule, if the sandbox permits it to survive. See [PR_SET_CHILD_SUBREAPER](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html) and [pid_namespaces(7)](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html).

This does **not** automatically grant a role: the operator join approval remains a separate defense. It does invalidate the stronger assertion that rejecting registered descendants proves a registration came from the operator. In-process subagents already have the same limitation acknowledged in the design.

**Recommendation:** Define the authenticated principal as a registered process tree, including its in-process agents and permitted descendants. Treat name-based nested detection as a cooperative restriction. If main-session-only authorization is required, identify a trusted harness enforcement point. Keep operator approval mandatory for all new identities, and present names/session IDs as descriptive metadata rather than attested facts. Also define what happens when a launcher spawns the real harness and exits instead of preserving the registered PID through exec.

**Acceptance test:** Use renamed executables, interpreter flags, an unregistered intermediary, orphaned helpers, and actual packaged launchers. Confirm that no alternate registration path creates an approved identity, and document which subagent restrictions are instructions only.

### 5. P1 — Server trust has a bootstrap gap and no defined C2/worktree identity scope

**References:** `DESIGN.md:9`, `58–61`, `71`, `77–80`, `157`.

The messaging CLI receives a pin from the wrapper, but the wrapper first connects to the C2 to register. The document does not say how the wrapper discovers and authenticates that C2 before accepting its pin. If the wrapper learns the pin from the first server answering at a port, a squatter can become the trusted server for the new launch.

It is also unclear whether the key is global to the operator, per project, or per worktree. With several C2s, a shared certificate authenticates possession of the shared key, not the intended coordination group. The registration protocol must prevent a valid but wrong C2 from silently enrolling a launch in another worktree.

**Recommendation:** Give the wrapper a trusted discovery source outside peer write access, binding the intended worktree/C2 identity, endpoint, and pin. Define how the C2 obtains and validates the launch worktree; the kernel's socket-owner result does not itself contain that information. Either use distinct C2 identities or authenticate the intended group explicitly and reject mismatches. Specify certificate versus SPKI pin semantics, replacement/rotation, and Linux key storage. If the previous port is occupied, fail clearly or provide a trusted update path for already-running harnesses.

**Acceptance test:** Start a fake listener before a fresh wrapper launch; it must not supply the accepted pin. Redirect discovery to a different legitimate C2; registration must fail for a group mismatch. Exercise key loss/rotation and port conflict with existing peers.

### 6. P1 — Dropping dead registry entries conflicts with resume continuity

**References:** `DESIGN.md:71–73`, `86–103`.

Startup drops entries whose harness is dead, but resume requires recognizing a session ID as already bound. If the dropped entry is the only session-to-peer/role record, restarting the C2 after a harness exit erases the information needed to distinguish a resume from a new join. The design does not identify a separate durable record that preserves it.

Process identity also needs host-boot scope when persisted. On Linux, `/proc/PID/stat` start time is elapsed ticks since boot, not a globally unique creation timestamp. A `(PID, start time)` pair alone should not be trusted across boots. See [proc_pid_stat(5)](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html).

**Recommendation:** Separate a durable peer record from its live process binding. Preserve peer ID, namespaced harness session ID, worktree, approved role, history, and resume eligibility when invalidating a dead binding. Bind the live instance to boot identity, PID, start time, and an incrementing binding generation. Treat permission errors during liveness checks as uncertainty, not proof of death. Keep operator confirmation because the claimed session ID is not proof of continuity.

**Acceptance test:** Join, queue messages, exit the harness, restart C2, and resume. The same durable identity and history should be offered for explicit approval. Test stale records after reboot and a process whose status cannot be inspected.

### 7. P1 — In-flight operations need revocation and rebinding semantics

**References:** `DESIGN.md:89`, `95–103`.

Authentication is described as per connection, while receive/send-and-wait calls can remain open. Consider B holding a blocked receive, B's harness exiting, a child or proxy retaining the connection, and the operator approving a resumed B. The old waiter must not receive messages intended for the new binding. Similar ambiguity exists when a role changes or a join prompt remains pending while its originating process exits.

Concurrent joins or rebinds also require atomic checks. Two requests must not both observe an available identity and each install a binding. Deferring the decision to the REPL does not remove this race.

**Recommendation:** Define transitions for registered, pending approval, active, disconnected, and revoked bindings. Associate every pending approval, waiter, and request with a binding generation. Revalidate that generation at approval and delivery/commit; invalidate old waiters on rebind or revocation. Define role uniqueness and reassignment explicitly, and derive sender identity and receive authorization from C2 state rather than request fields. Authorize reads, history access, replies, and broadcasts within the bound worktree.

**Acceptance test:** Race two joins for the same role/session; kill and resume a harness with a receive outstanding; approve a stale prompt; change a role while send-and-wait is active. There must be one authorized binding and no delivery through its predecessor.

### 8. P2 — TLS replay protection does not define message delivery or retries

**References:** `DESIGN.md:13`, `63`, `93–95`.

TLS protects the channel but does not resolve application duplicates. If C2 commits a send and the connection fails before acknowledgment, a retry on a new TLS connection is a new valid request. Likewise, removing a received message before confirmed delivery can lose it, while redelivery can duplicate it. Waiting for a reply requires a correlation identity and a rule for replies arriving after timeout.

TLS also does not supply application framing: the protocol still needs a message boundary, size bound, and handling of partial reads. The prototype's single `recv(1024)` is adequate only as a small diagnostic convenience. TLS 1.3 early data introduces additional replay considerations; disable 0-RTT for these operations unless deliberately designed for it. See [RFC 8446, section 8](https://www.rfc-editor.org/rfc/rfc8446.html#section-8).

**Recommendation:** Specify delivery semantics separately from authentication. A minimal approach is bounded framing, durable message IDs, a retry key scoped to the authenticated peer, explicit acknowledgment/cursor behavior, and reply correlation. State what “sent” means relative to persistence. Avoid implying exactly-once processing merely because the transport is TLS.

**Acceptance test:** Drop the connection after commit but before acknowledgment, retry a send, restart C2 during receive delivery, and deliver a reply after its waiter times out. Outcomes must follow a documented policy without silently losing or multiplying work.

### 9. P2 — Background process attribution does not establish reliable agent wakeup

**References:** `DESIGN.md:13`, `97`, `135–139`.

The verified ancestry observations do not establish that every harness starts a useful model turn when a background receive completes, or that the behavior survives an idle UI, compaction, operator activity, or canceled tool calls. The universal compatibility statement is stronger than the evidence described. A harness capable of invoking a shell command does not necessarily support the required background completion semantics.

There is also a liveness issue if two peers both use send-and-wait and neither maintains an independent receive path. A wait-status display makes the problem visible but does not resolve it.

**Recommendation:** Define a receive-loop contract per supported harness, including cancellation, timeouts, rearming, and how replies are handled while another send is waiting. Record versions and sandbox/background settings. Describe shell invocation as a transport prerequisite and automatic wakeup as an independently tested capability.

**Acceptance test:** Leave a session idle, deliver a message, and verify that it starts a turn, processes the message, and rearms receive. Repeat during operator input, compaction, simultaneous send-and-wait, and C2 restart. Verify behavior rather than only process ancestry.

### 10. P2 — Unauthenticated connections and approval prompts need resource bounds

**References:** `DESIGN.md:43–48`, `88–89`, `140`, `147`; `c2.py:168–185`, `249–252`.

Every connection can cause a potentially expensive process scan. The test server also starts a thread per connection and waits for data before attribution. A peer can generate connections or repeated joins without impersonating anyone and exhaust the C2 or bury the operator in prompts. This does not invalidate authentication itself, but can make the coordination service unusable.

**Recommendation:** State whether malicious denial of service is excluded. Regardless, bound concurrent handshakes/lookups, request size, idle time, pending approvals, and per-peer waiters. Deduplicate pending joins for a binding. Escape peer-controlled role/session/message text before rendering it in the operator terminal. Measure full request latency and concurrency, not only the socket lookup mean.

**Acceptance test:** Hold idle connections open, send oversized frames, burst joins and receive calls, and submit control characters in displayed fields. Established peers and the operator should remain responsive within the chosen limits.

## Isolated checks performed

These checks imported `c2.py` without changing it. Socket/process tests used `unittest.mock`; they are parser and contract checks, not live OS exploits.

| Check | Observed result | What it establishes |
| --- | --- | --- |
| `harness_of('/usr/local/bin/claude --version')` | `claude` | Expected name recognized. |
| `harness_of('/tmp/renamed-harness')` | `None` | Recognition depends on naming, not executable identity. |
| `harness_of('/usr/local/bin/node --max-old-space-size=4096 /opt/claude/cli.js')` | `None` | Interpreter options defeat the current script-position heuristic. |
| `harness_of('/tmp/codex-helper')` | `codex` | Prefix matching can classify unrelated commands as harnesses. |
| Linux row has matching ports but client address `127.0.0.2` | Returns synthetic PID `101`, UID `501` | Address mismatch is not checked. |
| Linux scan has readable PID `101` and unreadable PID `202` | Returns PID `101` without an incompleteness indicator | The result does not establish exhaustive holder enumeration. |

No live proxy-isolation or end-to-end security test was performed. The existing “Verified” section should keep its useful observations, but attach reproducible commands, harness versions, OS versions, sandbox profiles, and captured outcomes. Separate observed compatibility from security properties still awaiting adversarial tests.

## Suggested revision order

1. Define the supported threat model and process-tree principal. Make cross-profile proxy isolation a prerequisite; this decides whether the central mechanism can meet the goal.
2. Specify trusted wrapper bootstrap, C2/worktree binding, and the exact OS attribution contract. Prototype the hardest assumptions before implementing the full protocol.
3. Define durable peer identity, live binding generations, atomic operator approval, revocation, and resume. Test restart and outstanding-waiter scenarios together.
4. Specify bounded message framing, authorization, retry/delivery semantics, and harness receive-loop behavior. Build the acceptance tests above into a reproducible matrix.

The smallest defensible first version authenticates an operator-approved process tree under explicitly verified sandbox restrictions. Stronger statements about the individual model session, main-session-only access, or arbitrary harness configurations should wait for an enforcement mechanism and corresponding tests.
