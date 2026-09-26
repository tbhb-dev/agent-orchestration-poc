# Open items

What's settled but not yet written into a design, and what's still open.

## Document status

| Document | Status |
| --- | --- |
| `DESIGN_V1.md` | Not yet written; the next design document |
| `SANDBOX_TESTS.md` | Capability test matrix, not yet run |
| `DESIGN_REVIEW_*`, `DESIGN_V2_REVIEW_*` | Reviews of earlier drafts, which have been removed. Findings still apply unless listed as dropped below |
| `c2.py`, `peer.py`, `probes/` | Python test scripts for attribution and sandbox probing; not the implementation |

## DESIGN_V1.md

Carries these fixes from the reviews:

- Split attribution from authorization. Messaging holders must be confined, must be the CLI, must not be a harness process itself (this rejects traffic tunneled through Claude Code's sandbox proxy), and must descend from the binding. Registration holders must be unconfined.
- Join tokens are written to the operator state directory and the operator runs `agent-work start <harness> --join <n>`. The token never touches a terminal, clipboard, scrollback, or shell history.
- Token redemption is transactional: resolve the harness path before spending the token, persist consumption and binding together, handle a lost response.
- Unknown liveness blocks resume until the operator confirms or revokes.
- `join` (activation) and `ready` (waiting for the group) are separate calls.
- `/resume-peer` is its own command.
- Transcript slug derives from the launch working directory, plus a `cwd` field check.
- Boot ID from `kern.bootsessionuuid`; no TLS session resumption; resolve symlinks before the harness allowlist check; REPL warns when the C2's port or identity changes.
- Global pre-authentication connection limits.
- The chain-shape policy is dropped. The proxy appendix is demoted to unimplemented research.
- Document what `allowLocalBinding` opens beyond the C2: every loopback listener on the machine, and binding any port.

## Decisions pending test results

Run `SANDBOX_TESTS.md` first. The results decide:

- **Where the C2's private key lives.** A 0600 file only works if every supported harness can read-deny the state directory (test 7). A keychain item with no trusted apps works if sandboxed access is blocked or prompts (tests 8 and 9). Otherwise, keep the key in memory only, at the cost of relaunching every peer when the C2 restarts. The residual risk in every case: impersonating the C2 needs the key and a moment when its port is free.
- **Whether Antigravity is supportable.** Its embedded Seatbelt profile allows every Mach lookup and every sysctl read. If `launchctl submit`, `open`, or `osascript` from a tool call produces an unconfined process, the confinement check fails for that harness.
- **Clipboard and tmux exposure.** Less important now that tokens stay in the state directory, but still worth knowing.
- **Cross-harness argument reads.** Whether one harness's tool call can read another's process arguments.
- **`.claude/` write access** from Codex and Antigravity tool calls.

Calibrate `probes/confinement_probe.py` against `self` and a sandboxed tool-call process before trusting any confinement result.

## Codex permission modes

- `/status` shows **Workspace (Approve for me)**, which most likely means Codex approves its own requests to rerun commands outside the sandbox. The earlier Codex attribution runs may have been unsandboxed, so they show attribution works, not that Codex's sandbox allows loopback.
- There are no sandbox settings in `~/.codex/config.toml`. The Codex source shows the default `workspace-write` sandbox denies loopback unless `network_access = true` (which opens all outbound network) or a managed proxy with local binding.
- Decide which Codex permission modes agent-work supports. A mode where the agent can approve its own escape from the sandbox defeats the confinement check, and self-approved `agent-work` calls would also be rejected as unconfined. Run the capability tests in a fresh Codex session with escalations prompting, and deny them.

## Project configuration in a shared worktree

The risk isn't limited to sandbox keys. Project scope can also add things that run outside the sandbox, such as a `statusLine` command, MCP servers in `.mcp.json`, and hooks. Array keys such as `excludedCommands` merge across scopes, so project settings can widen the user-scope sandbox policy. The Codex and Antigravity sandboxes need a write deny on `.claude/` and `.mcp.json` in the worktree. Also check the reverse: whether Claude Code or Codex can write another harness's project config that's loaded live. Denying writes doesn't make config already in the worktree trustworthy, so launch also needs an initial-content check.

## Harness recognition

Recognize Antigravity by `agy` and `antigravity`. The standalone Gemini CLI is deprecated and not supported.

## Messaging design (not written)

Belongs in its own document:

- Messages go into shared logs, with a cursor per agent (the Kafka consumer-offset model). Broadcast to a group is one append to a log everyone reads.
- Replies carry a correlation ID so a `send` waiting for a reply only matches its own reply, not whatever a concurrent `receive` picks up.
- At-least-once delivery: a waiter returns a message without consuming it, and it's marked handled on acknowledgment, so a session that dies mid-receive gets a duplicate, not a drop.
- One waiter per session and type, so a new one replaces an old one left over from before a compaction or restart.
- `receive` and `send` take an agent-chosen timeout and run as background tool calls. All three harnesses start a new turn when a background call returns.
- Per-send idempotency keys, late replies, and what an agent should do after a timeout.
- The operator is a first-class participant through the REPL.

## Shared memory design (not written)

- Two tiers so far: checked-in, which is branch-scoped and reconciled at merge, and worktree-local, gitignored.
- A possible third tier for live state shared across worktrees: `$(git rev-parse --git-common-dir)/agent-work/`, shared by every worktree on the machine and never checked in.
- For checked-in memory, one file per entry avoids most merge conflicts. Append-only log files can use `merge=union` in `.gitattributes`, which is correct only for append-only data.
- Memory is untrusted shared state; any peer can write it.

## Implementation notes

- The implementation is Go. Pinned TLS checks the fingerprint in `VerifyPeerCertificate` and never falls back to system roots.
- On macOS the C2 should use libproc for socket lookups. `lsof` took about 40 ms per connection.
- Linux is out of scope for now. Claude Code on Linux puts tool calls in a separate network namespace with no direct path to host loopback, so it needs its own design.
