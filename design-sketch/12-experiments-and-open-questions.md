# Experiments and open questions

Each experiment should get its own directory under `experiments/` with the scripts, the raw evidence, the versions of everything involved (macOS, `container`, harnesses, shpool, Tailscale), and a write-up that ends up in the docs site. Order below is roughly by how much of the design depends on the answer.

## Critical path

1. **Harnesses on Linux arm64 inside an Apple Containers VM.** Do Claude Code, Codex, and `agy` all install and run there? How does each authenticate with the operator's subscriptions (Keychain for Claude Code on macOS won't be available)? If `agy` doesn't run on Linux arm64, design the hybrid where `agy` sessions stay on the host.
2. **Shared authentication across sessions.** For each harness: where credentials live on Linux, whether it rotates refresh tokens, what happens when several sessions share one credentials file or config directory (including sessions in different VMs refreshing at once), whether it accepts a long-lived token or externally supplied credentials, and whether a host credential broker is feasible. The goal is one login per harness for every session on the machine; see the options table in `06-containers.md`.
3. **`container exec -it` fidelity.** Resize forwarding, raw mode, latency, and whether Claude Code's, Codex's, and `agy`'s TUIs render correctly through it.
4. **shpool in the guest.** Attach with a command, force attach, one client per session, screen restore modes on reattach for each harness's TUI, detach key collisions, behavior when the exec channel dies.
5. **Worktree mounts.** A worktree plus the main repository's `.git` mounted at identical paths; `git status`, commits, hooks, and worktree operations from inside the VM; permissions across per-agent users and the operator user with a shared group and umask `002`. Compare with a clone per group.
6. **Embedded NATS as the bus.** The subject and stream layout, durable pull consumers with multiple filter subjects, acks and redelivery, `Nats-Msg-Id` deduplication, correlation by header, key-value buckets with compare-and-set for claims and per-key TTLs, one account per group, and per-agent subject permissions. Confirm an agent can't publish as another agent or read another group's subjects.
7. **NATS topology and reachability.** One server in the daemon versus a server per group VM as a leaf node; how a VM on an internal network reaches the host listener, and how to bind that listener only where VMs can reach it.
8. **NATS credentials and agent identity.** Per-agent credentials files owned by per-agent Linux users inside the VM; per-worker credentials on the host for the bootstrap; whether NATS auth callout with the research's kernel attribution is worth building.
9. **Waiter semantics.** How outstanding pull fetches behave across each harness's compaction and restart, and whether to cap them per consumer or cancel stale ones.
10. **Bus wake mechanisms per harness.** Background `receive` in all three (the research verified background calls on the host; repeat in the VM), `Stop`-hook pending-message checks, and the terminal nudge.

## Important

11. **Host file watching on virtiofs writes.** How promptly the host sees writes that agents make inside the VM, for the UI's live file view.
12. **Egress.** Internal networks, the host proxy, and whether each harness and common tools honor proxy variables.
13. **Memory per group VM** with three harnesses running.
14. **Terminal fidelity end to end.** Truecolor, hyperlinks, bracketed paste, Shift+Enter and other modified keys, and OSC 52 clipboard through shpool, exec, the daemon, and xterm.js.
15. **Tailscale integration.** `tsnet` versus `tailscale serve`, caller identity, HTTPS, and keystroke latency from a phone.
16. **WebGL context limits** for xterm.js in WKWebView (Tauri) and in Safari and Chrome.
17. **Harness-native control surfaces inside a VM.** `claude agents --json` and cross-session messaging, the Codex app-server, `agy --remote-control`. Are any of them better status sources than hooks?

## Bootstrap-specific

18. **Initial prompts.** Starting each harness interactively with a first prompt pointing at a brief file.
19. **Host loopback for workers.** Which settings allow each harness's sandboxed tool calls to reach the embedded NATS server on loopback (the research left the Codex setting unconfirmed).
20. **Hooks on the host** for status and inbox checks in all three harnesses.

## Open design questions

- Daemon language: Go or Rust. Inputs: the Tauri shell is Rust either way; embedded `nats-server` and `tsnet` are Go libraries; PTY, VT emulation, and WebSocket libraries exist in both; the bootstrap tooling is already Go. A Rust daemon would supervise a separate Go process for the NATS server.
- Protocol schema format and code generation for Go or Rust and TypeScript.
- Whether `agentd-guest` (one in-VM supervisor per group owning PTYs, and possibly a NATS leaf server, over one exec channel) is needed for the PoC or only later.
- Claims and write coordination inside a group.
- Worktree location and naming, for both bootstrap workers and PoC groups.
- Credential handling per harness inside VMs, including whether one login per harness can serve every session.
- Whether harness configuration comes only from the image and per-agent volumes, never from the worktree.
- How much of the research's kernel attribution design the host bootstrap needs, and whether NATS auth callout is the place to put it.

## Persistence alternatives considered

Kept here so the reasoning isn't lost if shpool doesn't hold up.

| Approach | Survives daemon restart | Raw bytes to xterm.js | Screen on reattach | Build cost |
| --- | --- | --- | --- | --- |
| tmux attach per session | Yes | No (re-rendered) | Free repaint | Low |
| tmux control mode per group | Yes | Yes | Daemon snapshot | Medium |
| dtach or abduco | Yes | Yes | Partial redraw only | Low |
| shpool | Yes | Yes | Restored by shpool | Low |
| In-VM supervisor (`agentd-guest`) | Yes | Yes | Guest-side VT | High |
| No persistence, harness-native resume | No (conversation resumes) | Yes | Not applicable | Lowest |
| Headless protocols (stream-json, Codex app-server, ACP) | Depends | No terminal | Not applicable | High (UI per protocol) |

Headless protocols are also worth considering for delegated worker agents that don't need a TUI, alongside terminal sessions for agents the operator drives interactively.
