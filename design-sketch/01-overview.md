# Overview

## What this is

The PoC runs groups of interactive coding agent sessions (Claude Code, Codex, and Antigravity's `agy`) on the operator's Mac. Each group is scoped to a git worktree and runs inside its own Apple Containers VM. Agents in a group coordinate through a shared messaging bus and shared context. The operator manages groups, attaches to any session through a browser terminal (xterm.js), opens shells into a group's VM, browses the group's files, and watches and joins the message traffic between agents. The same UI runs as a Tauri desktop app and as a web app served by the daemon, and the web app is reachable remotely over Tailscale.

It continues the agent-work research in `~/Code/github.com/tbhb/agent-peering-tests` and `~/Code/github.com/tbhb/agent-session-tests`. That research assumed harnesses running directly on the host under their own Seatbelt sandboxes, coordinated by a C2 per worktree over loopback TCP with kernel-based peer attribution. The PoC moves the agents into VMs, which changes the isolation boundary, the identity story, and the transport options. Much of the research still applies: the messaging semantics in `OPEN_ITEMS.md`, the background-call wake pattern, the shared memory tiers, the session management findings for each harness, and the threat model's framing of the principal as a process tree.

## Goals

- An end-to-end demo on one Mac: create a group from a branch, have agents from all three harnesses working in it, watch them coordinate, step in through the UI, and tear it down cleanly.
- Groups as the core unit of management, isolation, messaging, and memory.
- Agents keep their native TUIs, tools, and configuration. The system coordinates harnesses; it doesn't become one.
- A single messaging and shared context design that works both for the host-side bootstrap tooling and inside groups.
- Sessions that survive UI disconnects and daemon restarts.
- Remote access that never exposes the daemon to the public internet.

## Non-goals for the PoC

- Multi-user or multi-machine operation.
- Linux or Windows hosts. The host is macOS; the guests are Linux.
- Confidentiality between agents in the same group.
- Hardened production security. The PoC should be honest about what it does and doesn't defend against, but it doesn't need to close every gap.
- Replacing any harness's own sandbox, approval, or permission model.

## Principles

- **Coordination layer, not a harness.** Anything that can run a shell command can take part in a group.
- **Groups are first-class.** Registry, policy, lifecycle, addressing, UI navigation, and isolation all hang off groups.
- **Evidence over assumption.** Every claim about a harness, Apple Containers, shpool, Tailscale, or Tauri gets verified on this machine before the design depends on it. Record versions with results.
- **One protocol, several backends.** The bus, the terminal stream, and the session API stay the same whether a session runs in host tmux, in a VM under shpool, or somewhere else later.
- **The daemon owns state; clients are views.** The desktop app, the web app, the operator CLI, and remote browsers all talk to the same daemon API.

## Vocabulary

| Term | Meaning |
| --- | --- |
| Operator | The human running the system |
| Coordinator | The agent that plans and dispatches work (Fable during the build; possibly an agent role inside groups later) |
| Group | A set of sessions scoped to one git worktree, sharing a bus, shared context, and (in the container backend) one VM |
| Session | One running process in a group: an agent session (a harness) or an operator shell |
| Harness | Claude Code, Codex, or `agy` |
| Backend | What provides a group's boundary and runs its sessions: host tmux (bootstrap), Apple Containers, possibly Docker or local |
| Bus | The group's messaging system: an embedded NATS server with JetStream (streams, durable consumers as cursors, key-value buckets), and the CLI agents use to talk |
| Shared context | Memory and coordination state shared by a group: checked-in memory, worktree-local memory, decisions, claims |
| `agentd` | Placeholder name for the host daemon |
| `agentctl` | Placeholder name for the CLI used by agents and the operator |
| `agentd-guest` | Placeholder name for an optional in-VM supervisor |
