# agent-work peer authentication and registration, v2

This revision replaces `DESIGN.md`. It incorporates the Astra, Gemini, and Fable reviews of v1, the source reading Fable did of `anthropics/sandbox-runtime` and `openai/codex`, and confirmed facts about both target environments. A summary of what changed is at the end.

## What agent-work is

agent-work coordinates several independent agent harness sessions working on the same codebase. The operator starts each harness (Claude Code, Codex, Antigravity) in its own terminal or tmux pane, and the sessions talk to each other through a shared messaging system and shared memory.

Most multi-agent frameworks become the harness: they spawn the agents, own the loop, and bring their own configuration. agent-work goes the other way. Each harness keeps its native tools, permissions, sandboxing, and configuration, and agent-work is a coordination layer underneath them. Any harness that can run a shell command and reach loopback can take part.

Coordination is scoped to git worktrees. The operator typically runs several worktrees in parallel, each with its own group of coordinated sessions and its own C2.

Shared memory comes in two tiers: project-scoped memory checked into the repository, and worktree-local memory that's gitignored. Checked-in memory is versioned with the branch, so a memory written in one worktree reaches others when its branch merges. Both tiers are untrusted shared state (see the threat model).

Sessions send and receive messages by running the `agent-work` CLI from their Bash tool or equivalent. Receiving blocks until a message arrives or a timeout the agent picks runs out, and sending can wait the same way for a reply. Agents run these calls as background tool calls, so the operator can keep talking to the session while it waits, and the harness starts a new turn when the call returns. That gives each session a way to wake on delivery without harness hooks, which some environments disable.

The operator takes part through the C2's REPL: adding peers, messaging one peer or the whole group, and seeing each peer's state.

## Scope of this document

This document covers how the C2 identifies peer sessions, how peers are added and activated, how the C2 proves its identity to peers, and what each harness's sandbox has to allow. Message delivery semantics (framing, acknowledgment, retries, reply correlation) and the receive-loop contract per harness belong in a separate messaging design and are only referenced here.

## Threat model

### In scope

Authenticity and integrity between peers:

- A message attributed to a peer came from that peer.
- A peer can't send as another peer, alter or remove another peer's messages, or take over another peer's identity, including across a resume.
- A peer can't create a new identity for itself or enroll in a group without the operator.

### The principal is a process tree, not a model

The authenticated principal is the registered harness process and everything that runs under it: the model's tool calls, in-process subagents, and any code the agent executes, including test suites, build scripts, and anything from a repository or pull request under review. If the reviewer agent runs `npm test` on a malicious branch and the test script calls `agent-work send`, that message authenticates as the reviewer, because it did come from inside the reviewer's session.

Attribution can't tell which instruction inside a session caused a request. The optional chain-shape policy described under client identity narrows this for the drive-by case, but it isn't a boundary. Operators should treat a session that runs untrusted code as able to act with that session's identity.

### Out of scope

- **Confidentiality between peers.** Every peer should be assumed able to read the whole message log and every other peer's transcripts. Codex's sandbox reads most of the filesystem, Claude Code's read sandbox is a deny list, and every received message is written to the recipient's transcript on disk. Keeping messages secret from other peers would take OS-level isolation.
- **Malicious same-UID processes outside any sandbox.** A process running as the operator, unconfined, can already modify the C2 and its configuration. Defending against that needs separate users, containers, or VMs.
- **Prompt injection through message contents.** An authenticated message is still untrusted input to the receiving model.
- **Denial of service** is not a security goal, but the C2 applies resource bounds (see operational requirements) so a misbehaving peer can't make the system unusable by accident.

### Assumptions

- Each harness runs its tool calls inside a sandbox the operator has configured as described under deployment requirements.
- Sandboxed processes can't read the arguments or environment of processes in other sandboxes. Both the Claude Code and Codex Seatbelt profiles restrict `process-info*` to the same sandbox; the work sandboxes also deny `ps` outright.
- The operator's terminal running the REPL, and the operator-only state directory, are not reachable by sandboxed processes.

## Components

The **C2** is a long-running process the operator starts in its own terminal, outside any sandbox, one per worktree. It owns the peer registry, is the only writer to the message log, and hosts the REPL. It listens on TCP at `127.0.0.1` only.

The **`agent-work` CLI** has two roles. As the launch wrapper (`agent-work start`), the operator runs it outside any sandbox to redeem a join token and start a harness. As the messaging client (`join`, `send`, `receive`), the agent runs it from inside the harness.

The **operator state directory** (`~/.local/state/agent-work/` or platform equivalent) holds each C2's endpoint, TLS identity, and registry. It must be outside every sandbox's writable set and should be added to each sandbox's read deny list where the harness supports one.

The **`/agent-work join` skill** tells the agent to run `agent-work join` and how to participate. It doesn't authenticate anything.

## Transport

All three harnesses reach the C2 over direct TCP to `127.0.0.1`, in both the personal and work environments. No harness routes agent-work traffic through a proxy.

| Harness | Setting that allows direct loopback | Scope | Verified |
| --- | --- | --- | --- |
| Claude Code | `sandbox.network.allowLocalBinding: true` | User or managed; project scope can't set it | Work: set in managed settings. Personal: to set in user settings. |
| Codex | To be confirmed. The source shows loopback allowed only with `network_access = true` or with a managed proxy plus `allow_local_binding` | User config | Loopback worked in both environments; which setting enabled it is not yet recorded |
| Antigravity (`agy`) | Sandbox localhost allowance | User config | Personal |

In Claude Code, `allowedDomains` only controls what the sandbox proxy will dial. It doesn't change the Seatbelt profile, so loopback in `allowedDomains` without `allowLocalBinding` forces traffic through the proxy, where identity reduces to the proxy's per-session credential. That configuration is not supported by the main design; see the appendix.

`allowLocalBinding`'s outbound-loopback behavior is documented in the sandbox runtime source and README, not in Claude Code's settings reference, which describes it as a binding permission. The peering test suite should include a regression check that a sandboxed Claude Code tool call's connection to the C2 is owned by the CLI process, not by `claude`.

The CLI must connect with an `AF_INET` socket to the literal `127.0.0.1`. The Seatbelt loopback rule matches `127.0.0.1` and `::1` but not the IPv4-mapped form `::ffff:127.0.0.1` that a dual-stack socket produces.

Unix domain sockets are not used. They're blocked in the work environment, blocked by Codex's default sandbox, and on Linux Claude Code can only allow them all or none.

## Client identity

The C2 identifies every caller from the kernel's view of the connection. No client ever sends a credential.

### Lookup contract

For each accepted connection, before acting on the request:

1. Take the full connection tuple: client address and port, server address and port. Match all four when finding the client socket, not just the ports.
2. Find every process holding the client end of the socket (libproc on macOS; `/proc/net/tcp` for the inode, then a `/proc/*/fd` scan, on Linux).
3. If any process table or fd table needed for the answer is unreadable, fail closed. An incomplete holder list is a rejection, not a partial answer.
4. Reject if any holder runs under a UID other than the C2's.
5. Take a single snapshot of the process table and walk each holder's ancestry, recording `(pid, start time)` for every hop, with start times at sub-second precision (`proc_pidinfo(PROC_PIDTBSDINFO)` on macOS, `/proc/<pid>/stat` field 22 on Linux).
6. The walk must reach a live binding's harness PID whose start time and boot ID match the binding.
7. If the socket has several holders, every holder must resolve to the same live binding.
8. Before replying, confirm the connection is still open. Don't cache identity across a long-lived connection; re-resolve on each request on the connection.

Any failure is a rejection. Valid requests may fail during process churn; the CLI retries.

### Nested harnesses

If the walk passes through a process recognized as a harness (by executable path or name) before reaching the bound harness, the C2 rejects the request. This is a policy hint that catches accidents, not a security control. A renamed or copied harness binary defeats it, and a nested harness only ever gets its parent's identity, which is the same operator-approved principal.

Whether Claude Code blocks nested sessions through its sandbox or only through the `CLAUDECODE` environment variable is untested. If it's the variable, `env -u CLAUDECODE claude` starts one.

### Optional chain-shape policy

For drive-by code execution, the C2 can additionally require that the socket owner is the `agent-work` binary (by kernel-reported executable path), its parent is a shell, and that shell's parent is the bound harness. A test runner or build script that calls the CLI produces a longer chain and is rejected.

This narrows the code-execution problem without closing it: an agent can still invoke the CLI from its own shell with whatever it likes, and harnesses differ in how they spawn tool-call shells. It's offered as a per-harness option once each harness's normal chain has been recorded, not as a default.

## Server identity

The C2 authenticates itself to clients with one-way TLS and a pinned identity.

- Each C2 has its own key pair and self-signed certificate, generated on first start for that worktree and stored in the operator state directory (macOS: keychain, referenced from the state directory). A per-worktree identity means a wrapper can't be enrolled in the wrong worktree's group by a legitimate but different C2.
- The wrapper reads the C2's endpoint and certificate from the operator state directory, keyed by the worktree's `--git-common-dir` path and worktree path. It never learns them from whatever answers on the port.
- The wrapper injects `AGENTWORK_PORT` and the SPKI fingerprint into the harness environment. Both are public.
- The CLI pins the fingerprint, trusts no CA, skips hostname verification, disables TLS 1.3 early data, and verifies the server before sending any request.

A peer squatting the port while the C2 is down can't complete the handshake, so it never sees requests and can't answer them. TLS provides integrity within a connection; duplicate handling across connections belongs to the messaging design.

Client certificates are not used. They'd put a private key in the sandbox, and kernel attribution is stronger client authentication for this threat model.

## Peer records

The C2 keeps two kinds of record:

- A **durable peer record**: peer ID, worktree, harness type, role, session ID once reported, message cursor, and history. It survives harness exit and C2 restart.
- A **live binding**: the harness PID, its start time, the boot ID, and a binding generation number that increments on every bind. A durable record has at most one live binding, and a harness process can hold at most one binding.

Every waiter, pending operation, and request is tagged with the generation it was authenticated under. Delivery and commits check that the generation is still current. Rebinding or revoking a peer invalidates everything tagged with the old generation, so a blocked `receive` from a dead process can't take messages meant for its resumed successor.

Peer states: added (token issued), bound (wrapper redeemed the token), active (agent ran `join`), disconnected (harness exited, durable record kept), and removed.

Roles are exclusive within a group unless the operator explicitly allows duplicates. Changing a peer's role goes through the REPL.

## Flows

### Starting the C2

The operator starts the C2 for a worktree. It loads or creates that worktree's TLS identity, loads the registry, and binds `127.0.0.1` on its recorded port, failing clearly if the port is taken.

On startup it revalidates live bindings: a binding stays only if its PID is alive and its start time and boot ID match. If liveness can't be determined, the binding is dropped. Durable records are always kept.

### Adding a peer: `/add-peer`

The operator runs `/add-peer <harness> <role>` in the REPL. The C2 creates a durable peer record in the added state and issues a join token:

- single use,
- valid for a few minutes,
- scoped to this C2's worktree and the named harness type.

The REPL prints a copyable `agent-work start <harness> --join <token>` command, or places it on the clipboard and doesn't print the token. Printing is weaker if any sandbox can reach the operator's tmux socket, since `tmux capture-pane` can read scrollback.

### Launching: `agent-work start <harness> --join <token>`

The operator pastes the command into a terminal outside any sandbox, in the worktree.

1. The wrapper reads the C2's endpoint and fingerprint for this worktree from the operator state directory, and opens a pinned TLS connection.
2. The C2 identifies the wrapper through the kernel lookup and applies registration checks:
   - **Confinement.** The wrapper must not be inside any sandbox (`sandbox_check(pid, NULL, SANDBOX_CHECK_NO_REPORT)` on macOS; on Linux, the `Seccomp:` line in `/proc/<pid>/status` and namespace inodes compared to the C2's own). A confined process can lose its parent but can't shed its sandbox, so this closes every reparenting route for sandboxed harnesses.
   - **Ancestry.** The wrapper must not descend from a live binding. This is a second check for harnesses that run tool calls unconfined.
   - **Worktree.** The wrapper's working directory, read from the kernel, must be inside this C2's worktree.
   - **Token.** Valid, unexpired, unused, and matching the harness type.
3. On success, the C2 consumes the token and creates a live binding for the wrapper's PID, start time, and boot ID, at a new generation.
4. The wrapper resolves the harness executable from an operator-configured allowlist of absolute paths. It refuses any path under the worktree or `$TMPDIR` and never searches `PATH`.
5. The wrapper injects `AGENTWORK_PORT` and the fingerprint, then `exec`s the harness. `exec` keeps the PID and start time, so the binding now names the harness.

A leaked token is only useful to someone who can redeem it from an unconfined process in the worktree, which in this threat model is the operator.

### Activating: `agent-work join`

The operator invokes `/agent-work join` in the harness. The agent runs `agent-work join`, which sends only the session ID (`CLAUDE_CODE_SESSION_ID`, `CODEX_THREAD_ID`, or the equivalent). The C2:

1. resolves the caller to its live binding through the kernel lookup,
2. records the session ID as a claim and runs a plausibility check where possible (for Claude Code, a transcript at `~/.claude/projects/<worktree-slug>/<session-id>.jsonl` that exists and was recently modified),
3. marks the peer active, and
4. returns C2-authored context: the peer's role and instructions, the group roster, and state.

The call then blocks until the group is ready, using the same background-call pattern as `receive`, and returns when the C2 declares the group ready. By default that's when every added peer is active or the operator says go. The operator can start without a peer or remove it.

Join carries no identity claims. The binding happened at launch.

### Sending and receiving

Each `send` or `receive` opens a pinned TLS connection and sends a bounded, framed request. The C2 resolves the caller through the lookup contract, checks the binding generation, and derives sender identity and read authorization from its own state, never from request fields. The C2 is the only writer to the log.

Delivery semantics (message IDs, per-send idempotency keys, cursor and acknowledgment behavior, reply correlation, late replies) are specified in the messaging design.

### Compaction

Compaction keeps the harness process. Nothing changes.

### Resume

Resume starts a new harness process. The operator runs `/add-peer --resume <peer>` in the REPL, which issues a rebind token for the existing durable record. The C2 refuses to issue one while the old binding's process is alive, and tells the operator why so a hung process can be killed deliberately.

The operator launches the resumed harness with `agent-work start <harness> --join <token>` plus the harness's own resume flag. Redemption creates a new live binding at a new generation, invalidating the old one. The agent runs `join`, and the C2 returns context including the peer's cursor, so the session picks up where it left off.

The session ID reported at join should match the durable record's. A mismatch is shown to the operator. Claude Code's `--fork-session` produces a new session ID with shared lineage; a fork should be added as a new peer, not resumed.

### Main-session-only messaging

Messaging is supported only from a harness's main session. For child-process harnesses the nested check catches accidents. In-process subagents are indistinguishable from the main session in the process tree, so for them the rule is an instruction in the join skill. Where hooks are available, a user-scope PreToolUse hook could enforce it.

## The REPL

Every identity decision ends with the operator reading the REPL, so it's treated as a security surface.

- Control characters, escape sequences, and newlines are stripped or escaped from every peer-supplied string before display: roles, session IDs, and message contents.
- Peer state is shown with kernel-derived fields (PID, start time, executable path, working directory, TTY, confinement) laid out separately from self-reported ones, which are labeled as claims.
- For each binding the REPL can show the full ancestry to PID 1 and flags a wrapper that reached PID 1 without passing through a shell, terminal emulator, or tmux.
- Proxy-path connections, if the appendix configuration is ever used, are marked as lower assurance.

## Deployment requirements

### All environments

- Install `agent-work` at an absolute path and invoke it by that path or an alias. A `PATH` lookup from the worktree can resolve to a binary a peer planted in `node_modules/.bin`, a virtualenv, or a mise- or direnv-managed directory.
- Configure the harness allowlist with absolute paths.
- Keep agent-work's own harness configuration (skills, any hooks) in user or managed scope, never in project files in the worktree.
- Add the operator state directory to each harness's read deny list where supported.

### Project configuration in a shared worktree

A peer with write access to the worktree can edit another harness's project-scope configuration. For Claude Code, `.claude/settings.json` can add hooks, which run unconfined and are picked up live, and can widen `sandbox.excludedCommands` and `allowedDomains`. Claude Code's own sandbox denies its Bash tool writes to these files, so Claude Code peers can't do this to each other. Codex and Antigravity peers can, unless their sandboxes deny it.

- **Work environment:** closed. Managed settings replace any lower-scope value for the same key rather than merging with it, and the relevant keys are set in managed settings. Hooks are disabled there.
- **Personal environment:** the Codex and Antigravity sandboxes must deny writes under `.claude/` in the worktree. The reverse direction, whether one harness can write another's project config that's loaded live, should be checked for Codex and Antigravity config files too.

### Per-environment settings

| | Personal | Work |
| --- | --- | --- |
| Claude Code loopback | `allowLocalBinding: true` in user settings | `allowLocalBinding: true` in managed settings |
| Codex loopback | Setting to record | Setting to record |
| Antigravity loopback | Sandbox localhost allowance | Not used |
| Project settings escape | Deny `.claude/` writes from Codex and Antigravity | Closed by managed precedence |
| Hooks | Available | Disabled |
| Process inspection from sandboxes | Blocked by Seatbelt `process-info*` rules | Blocked; `ps` also denied |

### Linux

Out of scope for now. Claude Code on Linux runs tool calls in a separate network namespace with no direct path to host loopback, Unix sockets are all-or-nothing, and Codex's Linux sandbox blocks loopback without full network access. A Linux design would start from that topology rather than port the macOS lookup.

## Operational requirements

- Bound concurrent connections and lookups per binding, request size, idle time, pending tokens, and waiters per peer.
- Treat all request parsing as parsing untrusted input from sandboxed processes.
- Log every registration, activation, rebind, rejection, and the reason for each, to the operator state directory.

## Verified

Tested with `c2.py` and `peer.py`, on macOS:

- Background tool calls stay in the harness's process tree in Claude Code, Codex, and Antigravity.
- Foreground, background, and exec-mode calls resolve to the correct harness in all three over direct TCP.
- Nested harnesses (launched by name) are rejected in all three over direct TCP.
- Under a Claude Code sandbox with loopback in `allowedDomains` only, traffic goes through the in-process proxy and the C2 sees `claude` as the owner.
- Resume changes the harness PID and keeps the session ID.
- Owner lookup through `lsof` takes about 40 ms.
- The work Claude Code managed settings set `allowLocalBinding: true`, and managed keys replace lower-scope values for the same key.

These runs predate this revision's harness versions and settings being recorded. Future runs should capture harness versions, OS version, and the relevant sandbox settings alongside results.

## Tests before relying on this design

1. **Claude Code direct path.** With `allowLocalBinding: true`, a sandboxed tool call's connection to the C2 is owned by the CLI (`is_peer_py=True`), in both environments.
2. **Codex loopback setting.** Record which setting enables loopback in each environment and what else it opens.
3. **Confinement check.** `sandbox_check` reports confined for a tool-call process in each harness and unconfined for an operator terminal process. Token redemption from inside a sandbox is rejected even with a valid token.
4. **Reparenting.** A double-forked process started from each harness's tool call is still reported confined and can't register.
5. **Project settings write deny** (personal). Codex and Antigravity tool calls can't write under `.claude/` in the worktree.
6. **Cross-sandbox process inspection.** From a Codex session, `ps -E -p <pid>` against a Claude Code tool-call child fails, and vice versa. Only required for the appendix path, but it confirms an assumption the main design also leans on.
7. **Nested check behavior.** Record what happens with a renamed harness binary and with `env -u CLAUDECODE claude`, so the policy-hint label is backed by evidence.
8. **Lookup contract.** Address collisions, unreadable fd tables, fork and close during lookup, intermediate-parent exit, and PID churn all fail closed.
9. **Generations.** Kill and resume a harness with a `receive` outstanding; the old waiter gets nothing. Race two token redemptions for the same peer; exactly one succeeds.
10. **REPL sanitization.** Control characters and escape sequences in roles, session IDs, and messages render inert.

## Open questions

- **libproc lookup cost.** Expected well under the `lsof` numbers; not measured.
- **Session ID plausibility checks for Codex and Antigravity.** Where their transcripts live and whether a comparable check exists.
- **Readiness policy.** Whether groups need anything beyond "all added peers active or operator says go."
- **Chain-shape policy.** Whether each harness's normal tool-call chain is stable enough to enforce.
- **Subagent enforcement.** Whether hooks in each harness can identify subagent tool calls, for environments where hooks are available.

## Alternatives considered

**Operator-confirmed join based on ancestry (v1).** Replaced by `/add-peer` join tokens plus the confinement check. Ancestry can be shed by orphaning a process, and field-based confirmation prompts can be raced by a peer timing its own request.

**Join token redeemed by the agent inside the session.** Rejected. The token would pass through the model's context, the transcript on disk, and the command's argv, where another peer could read it and redeem it first. Without the wrapper, the CLI would also have to store the pin somewhere agent-writable between calls.

**One-time code shown in the harness and typed into the REPL.** A good ceremony for the v1 flow, since knowing the code doesn't let a peer type it. Superseded by the inverted flow, where nothing identity-bearing happens in the harness.

**Claude Code through the sandbox proxy.** Identity reduces to the proxy's per-session credential, which lives in the environment of every tool-call process. Kept only as the appendix fallback.

**Keys or tokens injected through the environment.** Depend on peers being unable to read each other's environments and on nothing printing them.

**Content-addressed public key files.** Prove a file wasn't altered, not which role it belongs to.

**Unix domain sockets with peer credentials.** Blocked at work and in Codex's default sandbox, and all-or-nothing for Claude Code on Linux.

**A port file in the worktree.** Agents can write the worktree and redirect peers to an impostor.

**Mutual TLS.** Server authentication adopted; client certificates rejected because they put a private key in the sandbox.

**Response signing with an injected public key (v1 draft).** Let a port squatter read requests before the client noticed. Superseded by pinned TLS.

**A single C2 identity shared across worktrees.** Would let a legitimate but different C2 enroll a launch in the wrong group. Replaced by per-worktree identities.

## Appendix: configurations where the proxy is the only path

Neither target environment needs this, but someone running agent-work with Claude Code configured without `allowLocalBinding` would. In that case the C2 sees `claude` as the socket owner, and any process holding that session's proxy token, which is in every tool-call process's environment, can reach the C2 as that session.

Two checks restore per-command attribution without a secret:

**Proxy-client census.** When a tunneled request arrives from harness PID `P`, the C2 enumerates established connections to `P`'s proxy port and resolves each client's owner. Every client must descend from `P`. A foreign client means someone else is using the proxy right now: refuse and alert. If a foreign and a legitimate client are open together, refuse both. This also runs continuously as monitoring.

**PID-and-nonce binding.** The CLI re-executes itself with a fresh random nonce in its arguments, then sends its PID and the nonce through the tunnel. The C2 reads that PID's arguments from the kernel (`KERN_PROCARGS2` on macOS), checks the nonce, checks the PID descends from `P` with matching start times, and checks it holds a live connection to `P`'s proxy port. An impersonator would need a process inside the victim's tree carrying a nonce it chose, which it can't create. This depends on test 6: peers must be unable to read the arguments of processes in other sandboxes.

The C2 should read the request, run both checks, act, and confirm the tunnel is still open before replying. The REPL marks these connections as lower assurance.

## Changes from v1

- Threat model promises authenticity and integrity, not confidentiality, and defines the principal as the process tree including executed code.
- All three harnesses use direct TCP in both environments; Claude Code via `allowLocalBinding`. The proxy path moves to an appendix.
- Registration uses operator-issued join tokens redeemed by the wrapper, plus a kernel confinement check, replacing ancestry-based trust.
- `agent-work join` is activation only.
- The wrapper reads endpoint and pin from operator state; each worktree's C2 has its own identity.
- Durable peer records are separate from live bindings, with boot IDs and binding generations.
- The nested-harness rule is reclassified as a policy hint.
- The lookup contract is specified to fail closed on incomplete information.
- New deployment requirements: absolute-path wrapper and harness resolution, user-scope configuration, and write denies for project settings in shared worktrees.
- The REPL is treated as a security surface.
- Linux is out of scope.
- `CLAUDE_SESSION_ID` corrected to `CLAUDE_CODE_SESSION_ID`.
