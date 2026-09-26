# agent-work peer authentication and registration

## What agent-work is

agent-work coordinates several independent agent harness sessions working on the same codebase. The operator starts each harness (Claude Code, Codex, Antigravity) in its own terminal or tmux pane, the same way they'd run it alone, and the sessions talk to each other through a shared messaging system and shared memory.

Most multi-agent frameworks become the harness: they spawn the agents, own the loop, and bring their own configuration. agent-work goes the other way. Each harness keeps its native tools, permissions, sandboxing, and configuration, and agent-work is a coordination layer underneath them. Any harness that can run a shell command can take part.

Coordination is scoped to git worktrees. The operator typically runs several worktrees in parallel, each with its own group of coordinated sessions and its own C2. A session's worktree and project come from where it was launched (`git rev-parse --show-toplevel` and `--git-common-dir`), so group membership needs no separate configuration.

Shared memory comes in two tiers: project-scoped memory checked into the repository, and worktree-local memory that's gitignored. Checked-in memory is versioned with the branch, so a memory written in one worktree reaches others when its branch merges.

Sessions send and receive messages by running the `agent-work` CLI from their Bash tool or equivalent. Receiving blocks until a message arrives or a timeout the agent picks runs out, and sending can wait the same way for a reply. Agents run these calls as background tool calls, so the operator can keep talking to the session while it waits, and the harness starts a new turn when the call returns with a message. That gives each session a way to wake on delivery without relying on harness hooks, which some environments disable.

The operator takes part through the C2's REPL: confirming joins, messaging one peer or the whole group, and watching who's waiting on whom. Roles (lead, implementer, reviewer, and so on) are assigned when a session joins, not when it's launched.

All of this depends on knowing who's talking. A message that claims to come from the reviewer is only useful if it did, and some harness configurations won't accept direction from another agent unless they can trust where it came from.

## About this document

This document describes how agent-work authenticates peer harness sessions to the C2 process, how peers register and join, and how the C2 proves its own identity to peers. It reflects the design as of the TCP attribution tests in this directory (`c2.py`, `peer.py`).

## Threat model

The attack to stop is one peer session impersonating another: sending messages as a different role, reading another peer's messages, or hijacking another peer's identity across a resume.

Out of scope: malicious processes running under the operator's UID that aren't agent sessions. A same-UID attacker can already modify the C2's binary and config, read files the C2 reads, and in some configurations attach a debugger. Defending against that requires OS-level isolation (separate users, containers, or VMs), which this design doesn't attempt.

The design also doesn't address prompt injection through message contents. A message that authenticates as coming from peer X is still untrusted input to the receiving model.

## Components

The **C2** is a long-running process the operator starts in its own terminal, outside any sandbox. It owns the peer registry, is the only writer to the message log, and hosts the operator REPL. It listens on TCP at `127.0.0.1` only.

The **`agent-work` CLI** runs in two roles. As a launch wrapper (`agent-work start`), the operator runs it outside any sandbox to start a harness. As a messaging client (`agent-work send`, `agent-work receive`, `agent-work join`), the agent runs it from inside its harness through a Bash tool call or equivalent, in the foreground or background.

The **`/agent-work join` skill** is invoked by the operator in a harness session. It wraps `agent-work join` and the other participation instructions.

## Client identity

Clients authenticate with no secrets. The C2 identifies each caller from the kernel's view of the connection:

1. On `accept()`, the C2 takes the client's ephemeral port.
2. It asks the kernel which process owns the client end of that socket, using libproc on macOS (the test uses `lsof`) and `/proc/net/tcp` plus a `/proc/*/fd` scan, or `sock_diag`, on Linux.
3. It rejects the connection if the owner runs under a different UID.
4. It walks the owner's process ancestry up to a registered harness PID, and confirms that the harness's process start time matches the registered start time, so a recycled PID doesn't inherit an identity.
5. It rejects the connection if any unregistered harness process appears between the owner and the registered harness (the nested-harness rule).
6. If the socket has more than one holder (an fd inherited across a fork), it accepts only when every holder resolves to the same registered harness.

The resolved identity is the registered harness and whatever role is bound to it. The client never sends a credential, so there's nothing in the sandbox to read, steal, or replay.

This works because the client blocks waiting for a response, so the socket and its owner are alive during the lookup, and because a process can't choose its parent.

## Server identity

The C2 authenticates itself to clients with one-way TLS and a pinned server identity.

- The C2 generates a key pair and self-signed certificate on first run and keeps them in the keychain, so the identity survives restarts.
- The launch wrapper injects the C2's certificate (or its SPKI fingerprint) into the harness environment. It's public, so environment readability doesn't matter.
- The CLI pins that exact certificate. It doesn't trust any CA and skips hostname verification, since the pin is the whole trust decision.
- The CLI verifies the server during the handshake, before sending any message content.

This covers a peer squatting the C2's port while the C2 is down. The squatter can't complete the handshake, so it never sees request contents and can't feed fake responses. TLS also gives the channel integrity and replay protection, so the message framing doesn't need its own.

Client certificates are deliberately not used. They would put a private key back inside the sandbox, and kernel attribution is stronger client authentication for this threat model.

## Flows

### Starting the C2

The operator starts the C2. It loads its TLS identity from the keychain (creating one on first run), loads the persisted registry, and binds `127.0.0.1` on its previous port if one is recorded.

On startup it revalidates the registry: entries whose harness PID is alive with a matching start time stay, and the rest are dropped.

### Starting a peer: `agent-work start <harness>`

1. The wrapper connects to the C2 and requests registration. The C2 identifies the wrapper's PID through the kernel lookup; the wrapper claims nothing.
2. The C2 rejects the request if the wrapper descends from an already-registered harness. That stops a peer from running `agent-work start` from its own Bash tool to create a new identity.
3. The C2 records the PID, its process start time, and the worktree.
4. The wrapper injects `AGENTWORK_PORT` and the C2's certificate or fingerprint into the environment, then `exec`s into the harness. `exec` keeps the PID, so the registered PID is the harness PID.

The wrapper carries no role. Role belongs to the join step.

### Joining: `/agent-work join <role>`

1. The skill runs `agent-work join <role>`, passing the harness's session ID (`CLAUDE_SESSION_ID`, `CODEX_THREAD_ID`, or the equivalent).
2. The C2 resolves the caller to its registered harness through the kernel lookup.
3. The REPL prompts the operator with the harness type, PID, worktree, session ID, and requested role.
4. On confirmation, the C2 binds the role and session ID to that harness. Until then, the harness can't send or receive.

The session ID is self-reported, so it's bookkeeping (correlating transcripts, detecting resumes), not an authentication factor.

### Sending and receiving

Every `agent-work send` or `agent-work receive` call opens a TLS connection, verifies the pinned server identity, and sends its request. The C2 authenticates the caller per connection through the kernel lookup. Because the C2 is the only writer to the log, and the log lives somewhere the sandboxes can't write, provenance comes from the C2's authentication decision. Message signatures are optional and only useful as an audit trail if the log ever leaves the C2's control.

Background calls work the same way. All tested harnesses keep background tool calls inside the harness's process tree.

### Compaction and resume

Compaction keeps the harness process, so nothing changes.

Resume starts a new harness process with a new PID and the same session ID. The operator starts it through `agent-work start` as usual, and the join step recognizes the session ID as already bound. Rebinding an existing identity always requires operator confirmation, and the C2 refuses the rebind outright if the original harness process is still alive. That prevents one peer from joining with another peer's session ID and taking over its role.

### Main-session-only messaging

Messaging is only supported from a harness's main session, not from subagents. The nested-harness rule enforces this for harnesses spawned as child processes. Subagents that run inside the harness process (as Claude Code's do) look identical to the main session in the process tree, so for them the rule is an instruction in the join skill, not an enforced boundary. Enforcing it would need a hook that can see which agent made a tool call.

## Per-harness behavior

| Harness | Path to the C2 | Attribution granularity |
| --- | --- | --- |
| Codex | Direct TCP (default sandbox allows localhost) | Per command |
| Antigravity (`agy`) | Direct TCP (sandbox with localhost allowed) | Per command |
| Claude Code | HTTP CONNECT through the sandbox's in-process proxy | Per session |

Under Claude Code's sandbox, direct connections to localhost fail even with loopback in `sandbox.network.allowedDomains`. The only way out is the proxy advertised in `HTTPS_PROXY` and `ALL_PROXY`. `NO_PROXY` lists loopback addresses, so the CLI has to detect the proxy and tunnel to the C2 through it explicitly rather than following the usual proxy rules.

The proxy runs inside the Claude Code process, so the C2 sees `claude` as the socket owner. Attribution resolves to the correct session, but the C2 can't tell which command opened the connection, and nested-harness detection doesn't apply to traffic through the proxy. Claude Code's sandbox blocks launching nested agents, which covers most of that gap in practice.

TLS runs end to end through the CONNECT tunnel, so server pinning is unaffected.

Harness recognition in the ancestry walk is by executable name (`claude`, `codex`, `agy`, `antigravity`), with a check of the script argument for processes launched through `node`, `bun`, `deno`, or `python`.

## Work and personal environments

The same design works in both. In the work environment, Codex and Claude Code sandboxes allow localhost, and the C2 runs outside the sandbox, so it can do the kernel lookup even though the sandboxes deny `ps` and process inspection. Unix domain sockets are blocked there, which is why the design uses TCP.

Whether the work Claude Code sandbox routes loopback through a proxy the way the personal configuration does hasn't been checked. If it does, attribution for Claude Code at work is per session, as described above.

## Verified

Tested with `c2.py` and `peer.py`:

- Background tool calls stay in the harness's process tree in Claude Code, Codex, and Antigravity.
- Foreground, background, and exec-mode calls resolve to the correct harness in all three.
- Nested harnesses are rejected in all three, with direct connections.
- Claude Code's sandbox proxy runs inside the Claude Code process, and connections through it resolve to the correct session.
- Resume changes the harness PID and keeps the session ID.
- Owner lookup through `lsof` takes about 40 ms per connection.

## Open questions

- **Cross-session proxy isolation in Claude Code.** If one session could reach another's proxy port, it could tunnel to the C2 and be attributed as the other session. The expectation is that each session's sandbox only allows its own proxy. Test by having session A connect to session B's proxy port.
- **Work Claude Code proxy behavior.** Whether loopback goes through a proxy under the work sandbox configuration.
- **Subagent enforcement.** Whether each harness exposes enough in hooks to block messaging from subagents.
- **libproc lookup cost.** Expected to be well under the `lsof` numbers, but not yet measured.

## Alternatives considered

**Keys or tokens injected through the environment.** Rejected as the primary mechanism because they depend on peers being unable to read each other's environments. That holds under the work sandboxes but not in general, and every variant (per-session signing keys, bearer tokens bound at join) inherits the dependency.

**Content-addressed public key files.** Naming a key file by its hash proves the file wasn't altered, but not which role it belongs to. The integrity problem moves to the role-to-hash mapping, which is just as writable.

**Unix domain sockets with peer credentials.** The cleanest attribution (per process, no proxy in the path), but blocked by the work sandboxes and by Codex's default sandbox. Still an option for Claude Code if its sandbox's Unix socket allowlist permits a specific path and per-command attribution becomes worth the extra surface.

**A port file in the worktree.** Rejected because agents can write to the worktree, and a rewritten port file would redirect peers to an impostor. The launch wrapper injects the port instead.

**Mutual TLS.** Server authentication is adopted. Client certificates are rejected because they'd put a private key inside the sandbox.

**Response signing with an injected public key.** Superseded by TLS. Signing authenticated responses but still let a port squatter read request contents before the client noticed.
