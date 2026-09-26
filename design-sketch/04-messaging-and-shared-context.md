# Messaging and shared context

This is the part of the system that has to work in two places: on the host, where the coordinating agent uses it to run the build (see [10-bootstrap-orchestration.md](10-bootstrap-orchestration.md)), and inside groups in the PoC. It should be one design with the same protocol in both places.

The messaging system uses an embedded NATS server, not a filesystem-based message bus. That decision came from the operator. The semantics sketched in `agent-peering-tests/OPEN_ITEMS.md` (durable logs, per-consumer cursors, at-least-once delivery, reply correlation, blocking receives as background tool calls) still stand; NATS and JetStream supply most of them directly. Read that document and `agent-peering-tests/DESIGN_V2.md` before changing anything here.

## Why embedded NATS

- `nats-server` can run in-process as a Go library, so the broker is part of a binary the project ships rather than a separate service to install and supervise.
- JetStream gives durable streams, durable consumers (the per-consumer cursor), explicit acknowledgment with redelivery (at-least-once), message deduplication by ID within a window (idempotent sends), and pull fetches with a timeout (the blocking `receive`).
- Core NATS request-reply and headers cover reply correlation.
- JetStream key-value buckets cover live coordination state: status, roster, and claims, with compare-and-set on revisions for claim acquisition.
- Accounts and per-user subject permissions give isolation between groups and let the server enforce who may publish as whom.
- A mature Go client, and clients for TypeScript and Rust if anything outside Go ever needs one.

The embedded server makes Go the natural language for whatever process hosts the broker. If the daemon ends up in Rust, the broker is a Go process the daemon supervises.

## Where the server runs

Two topologies to choose between by experiment:

**One embedded server on the host (starting proposal).** The daemon (or, during the bootstrap, a host broker process) embeds the server. Each group is its own NATS account, so groups can't see each other's subjects. Agents in a group VM connect over the network path from the VM to the host, on the group's internal network, with credentials scoped to their group's account. JetStream storage lives on the host, so agents can't tamper with the log files, and the daemon observes every group without extra plumbing. The cost: if the daemon restarts, agents lose the bus until it's back, and the VM needs a network path to one host port.

**An embedded server per group VM, connected to the host as a leaf node.** Each group VM runs its own server (inside the in-VM broker or `agentd-guest`) with JetStream storage in the VM, and connects to a hub server in the daemon as a leaf node. Agents keep messaging if the daemon restarts, and the daemon still sees everything through the leaf connection. The cost: storage sits where agents can reach it, two servers per group path to configure, and more moving parts for a PoC.

The bootstrap on the host uses the first shape: one embedded server bound to `127.0.0.1`.

## Subjects and streams

A sketch, to be refined:

| Subject | Meaning |
| --- | --- |
| `grp.<group>.msg.all.<from>` | Broadcast to the group |
| `grp.<group>.msg.dm.<to>.<from>` | Direct message |
| `grp.<group>.msg.op.<from>` | Message to the operator |
| `grp.<group>.evt.<agent>.<kind>` | Lifecycle events from hooks (turn started, turn ended, blocked) |

- One JetStream stream per group captures `grp.<group>.msg.>` and `grp.<group>.evt.>` with file storage and a retention policy the group's policy sets.
- The sender's name is the last token of every message subject, and subject permissions only let each agent publish subjects ending in its own name. The server enforces sender identity, so no envelope field has to be trusted.
- Each agent has a durable pull consumer filtered to `grp.<group>.msg.all.*` and `grp.<group>.msg.dm.<self>.*` (multiple filter subjects on one consumer need NATS 2.10 or later). The consumer's state is the agent's cursor. Agents can't subscribe to other agents' direct subjects. Confidentiality between agents is out of scope anyway, but there's no reason to make snooping trivial.
- Explicit acks with an ack wait and a delivery limit give at-least-once delivery. A session that dies mid-receive gets the message again after the ack wait.
- Sends set `Nats-Msg-Id` to an idempotency key so retries inside the duplicate window are dropped by the server.
- Replies carry a `Correlation-Id` header naming the message they answer. `send --wait` fetches only replies with its own correlation ID, so it doesn't consume messages a concurrent `receive` should get.

Message bodies are JSON:

```json
{
  "text": "Rebased on main; tests pass locally.",
  "refs": { "issue": 12, "pr": 31 },
  "harness_session_id": "..."
}
```

Headers carry the metadata: `Nats-Msg-Id`, `Correlation-Id`, `Reply-To-Id`, `Kind` (message, question, answer, event), and a timestamp.

## Agent-facing CLI

Agents use `agentctl` from their shell tool. The research established that all three harnesses keep background tool calls in the harness's process tree and start a new turn when a background call returns, so a blocking `receive` run in the background is a harness-agnostic way to wake on delivery. Under NATS, `receive` is a pull fetch of one message with an expiry.

```text
agentctl join                         # activate; returns role, roster, instructions
agentctl send <to> <text> [--wait N]  # to: agent name, '*' for the group, 'operator'
agentctl receive [--timeout N]        # pull fetch; returns next unacknowledged message
agentctl ack <id>
agentctl status [--set working|idle|blocked --detail "..."]
agentctl roster
agentctl memory get|put|list|search ...
agentctl claim <path-glob> [--release]
```

Output should be compact and machine-readable, with a short human summary, since models read it.

The research wanted one waiter per session so a stale waiter from before a compaction can't steal messages. Pull consumers allow several outstanding fetches by default. Decide whether to cap outstanding fetches per consumer, have `agentctl` cancel a previous waiter, or accept duplicates and rely on acks. That needs an experiment with each harness's compaction and restart behavior.

## Wake mechanisms, in order of preference

1. **Background `receive`.** Works everywhere a shell tool works. Depends on the agent keeping a receive outstanding, which the join instructions must make routine.
2. **Hooks.** A `Stop` hook (or each harness's equivalent) checks for pending messages when a turn ends (consumer info reports the pending count) and, where the harness allows, continues the session with them. Hooks also publish lifecycle events to `grp.<group>.evt.>`.
3. **Terminal nudge.** When an agent is idle with nothing outstanding and messages pending, the daemon writes a short pointer into its terminal ("You have 2 messages; run agentctl receive"), using bracketed paste with a separate Enter. Content never goes through the terminal.
4. **Harness-native channels.** Claude Code's cross-session messaging, the Codex app-server, and `agy`'s remote control are worth evaluating as observers or delivery paths, but each only covers one harness.

## Identity

NATS authenticates connections, not processes, so identity depends on how each agent gets its credentials and who else can read them.

**Inside a group VM.** Each agent runs as its own Linux user. Its NATS credentials (an nkey or user JWT scoped to its group account and its own publish subjects) live in a file readable only by that user. An agent can't read another agent's credentials without becoming that user, and agent users have no sudo. Operator shells run as the `operator` user with operator credentials. This replaces the Unix-socket peer-credential idea from earlier drafts. NATS doesn't listen on Unix sockets, as far as the design conversation knew, so file permissions carry the identity instead.

**On the host (bootstrap).** Workers run under their harnesses' own sandboxes. Each worker gets its own credentials at launch. Options, from simplest to strongest:

- Per-worker credentials injected into the harness environment. The principal is the harness process tree, and the research recorded that Seatbelt `process-info` rules stop one sandboxed harness reading another's environment. Adequate for the operator's own build workers.
- NATS auth callout, which lets an external service decide each connection's identity. A callout service could apply the research's kernel attribution: find the process that owns the connecting socket, walk its ancestry to a bound harness, and issue that worker's identity. Worth an experiment if the simple option proves too weak.

The research also recorded host transport constraints that apply to the NATS listener: Claude Code needs `sandbox.network.allowLocalBinding: true` for direct loopback, the client must connect to the literal `127.0.0.1` with an IPv4 socket (the Seatbelt rule doesn't match the IPv4-mapped IPv6 form), and which Codex setting enables loopback was still unconfirmed.

## Observability for the operator

The daemon reads each group's stream with an ordered consumer, which doesn't disturb any agent's cursor, and relays history and live messages to clients. The UI shows a group timeline with filters by agent and channel, threads grouped by correlation ID, delivery and acknowledgment state per recipient (from consumer info), and a composer that publishes as the operator to one agent, several, or the whole group. Every peer-supplied string is sanitized before display (control characters, escape sequences, and bidirectional overrides), carrying forward the research's rule that the operator's view is a security surface. The daemon is the only client-facing API; browsers don't connect to NATS directly.

## Shared context

### Live coordination state in JetStream key-value buckets

| Bucket | Keys | Notes |
| --- | --- | --- |
| Status | Agent name | Last status and detail, written by hooks and `agentctl status` |
| Roster | Agent name | Role, harness, native session ID, joined time |
| Claims | Path glob | Holder and expiry; acquire with create-if-absent, release or renew with compare-and-set on the revision, and let expired claims age out (per-key TTLs need a recent NATS release) |
| Decisions | Sequential ID | Append-only decision log with rationale and author (or a stream, if ordering and history matter more) |
| Brief | Fixed key | The group's goal, constraints, and definition of done |

### Memory tiers stay in files

Memory that belongs with the code stays in files:

| Tier | Location | Scope | Notes |
| --- | --- | --- | --- |
| Checked-in | In the repository (for example `.agents/memory/`) | Branch; reaches other worktrees when the branch merges | One file per entry to avoid merge conflicts; `merge=union` only for append-only files |
| Worktree-local | In the worktree, gitignored (for example `.agents/local/`) | This group only | Scratch notes, working state, handoff notes between sessions |

The research also floated a machine-local tier under `$(git rev-parse --git-common-dir)/agent-work/` for live state shared across worktrees. With NATS, a cross-group key-value bucket in a shared account may serve that purpose better; decide if a need appears.

At teardown the daemon offers to promote worktree-local entries into checked-in memory, and archives the group's stream and buckets to the operator state directory.

### Rules

- All shared context is untrusted shared state. Any member can write it, and any member can plant instructions in it. Agents should treat it as input, not as commands.
- Writes through `agentctl` record author and time. The server's subject permissions and per-agent credentials make the author trustworthy for anything written through NATS; git history is the backstop for the file tiers.
- Size limits on messages and values (set in the server's limits and the stream configuration) and schema checks on anything the daemon parses.
