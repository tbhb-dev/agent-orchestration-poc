# Review of DESIGN_V2.md: peer authentication and registration

Reviewer: Claude Fable 5.1, 2026-09-23. Scope: `DESIGN_V2.md`, read against the v1 review in `DESIGN_REVIEW_FABLE_5_1.md`, the sandbox-runtime and Codex sources cited there, and the Antigravity binary's embedded Seatbelt profile (`~/.local/bin/agy`, read with `strings`). Where a finding rests on one of those, it says so.

## Verdict

v2 fixes the structural problems in v1. Identity is kernel attribution over direct TCP for every harness, registration no longer trusts ancestry, the threat model promises what the design can deliver, and the peer record and binding generation model is sound. The lookup contract, REPL rules, and deployment requirements are the right shape.

What remains is narrower and mostly about the new registration flow and the environment assumptions it rests on:

1. **The join token is now a secret, and its protection is the confinement check.** That holds where no sandbox can launch an unconfined process or read the operator's clipboard and terminal. Antigravity's profile allows every Mach lookup and every sysctl read, by its own comments "for now", so the design should not assume either.
2. **`allowLocalBinding` has a cost the document doesn't state.** Every Claude Code tool call can then reach every loopback listener on the machine, including an unauthenticated Codex managed proxy if one is running.

Everything else is detail. Findings follow in priority order, then what holds up, then suggested changes.

## 1. The join token is a secret, and Antigravity weakens what protects it

v1 had no secret anywhere. v2 introduces one at launch: the `/add-peer` token, printed in the REPL or placed on the clipboard, pasted by the operator into a terminal. The document's defense is that "a leaked token is only useful to someone who can redeem it from an unconfined process in the worktree, which in this threat model is the operator." That is the right argument, and it makes the token's secrecy a function of two assumptions the document does not state as assumptions:

- No sandbox can start a process that is not confined.
- No sandbox can read the token from wherever it sits between the REPL and the wrapper: the REPL's scrollback, a tmux pane, the clipboard, the terminal emulator's buffer, the shell history file.

For Claude Code and Codex both look true from the source. Claude Code's default profile grants `lsopen` and Apple Events only under `allowAppleEvents`, denies Unix sockets by default, and lists a dozen Mach services with no pasteboard among them. Codex's base policy denies Mach lookups by prefix and allows a handful of named services, none of which is LaunchServices, Apple Events, or the pasteboard. Neither can reach tmux, `open`, `osascript`, or `pbpaste`.

Antigravity is different. Its embedded profile reads, with its own comments:

```
; Note: Other sandboxes restrict the list of mach-lookup services.
; We allow everything for now.
(allow mach-lookup)
; Note: Other sandboxes restrict the list of sysctls that can be read.
; We allow everything for now.
(allow sysctl-read)
```

Two consequences for this design, both to be tested rather than assumed, because Seatbelt gates some of these actions on operations other than `mach-lookup`:

- **Reading the token.** `pbpaste` needs only the pasteboard Mach service, which this profile allows. The clipboard option in `/add-peer` should be treated as readable by an Antigravity peer until a test shows otherwise. Terminal.app exposes its buffer over Apple Events, which also needs `appleevent-send`, and that operation does not appear in the profile strings, so the scrollback route is less likely but worth the same test.
- **Launching unconfined.** `open` needs `lsopen` and `osascript` needs `appleevent-send`, neither of which appears in the profile, so those are probably closed. `launchctl` talks to launchd over Mach and needs no separate operation that I know of. A job submitted that way runs unconfined, as the operator, with `launchd` as its parent. If that works from an Antigravity tool call, the confinement check and the ancestry check both pass for it, and the token is the only thing left.
- **Reading other processes' arguments.** The document's assumption 2 says sandboxed processes can't read arguments or environment of processes in other sandboxes, and cites `process-info*`. Antigravity also allows all of `sysctl-read`. If `KERN_PROCARGS2` is gated by the sysctl rule rather than the process-info rule for the caller, an Antigravity peer can read the wrapper's arguments during the window before `exec`, and the arguments and environment of every other sandbox's processes. Test 6 in the document runs Codex against Claude Code. It needs Antigravity as the reader too.

**Recommendation.** Keep the token, and take it out of every channel a sandbox might read:

- Don't print it and don't put it on the clipboard. Have `/add-peer` write the pending token into the operator state directory under the peer's name, and have the operator type `agent-work start codex --join reviewer`. The wrapper reads the token from the state directory, which is already the trust anchor for the endpoint and pin and is already required to be outside every sandbox's readable set where a deny list exists. The token then never crosses a terminal, a pane, a clipboard, or a history file.
- Echo every redemption in the REPL with the wrapper's kernel facts (PID, executable path, TTY, ancestry to PID 1) and make the second redemption of a consumed token a loud, named failure. With a single-use token, a stolen redemption is detected when the operator's own launch fails, and the REPL should make that unmistakable.
- Add to the assumptions: no sandbox can read the operator's clipboard or terminal contents, and no sandbox can start an unconfined process. Then add the tests that back them for each harness: `pbpaste`, `open`, `osascript`, `launchctl submit`, and `tmux` from a tool call.
- State in the Antigravity row of the transport table that its profile allows all Mach lookups and all sysctl reads, so the design's confinement and process-inspection assumptions are unverified for it.

A smaller point in the same flow: `--join <token>` on the command line lands in the shell history file. Claude Code's read deny list covers `~/.zsh_history`; Codex's default sandbox reads it. Single use makes this harmless after redemption, and the state-directory approach removes it entirely.

## 2. `allowLocalBinding` widens more than the path to the C2

The document adopts `allowLocalBinding` for Claude Code and describes what it enables. It does not describe what else it opens, and a setting the operator turns on for every session deserves that paragraph.

With `(allow network-outbound (remote ip "localhost:*"))` in the profile, every Claude Code tool call can connect to every loopback listener on the machine. Some of those matter:

- **A Codex managed network proxy**, if Codex runs one, accepts connections without an attribution frame and falls back to its environment default (`codex-rs/network-proxy/src/attribution.rs:47-70`). It relies on Seatbelt to limit who can reach its port. A Claude Code tool call can now reach it, and egress through Codex's allowlist rather than its own. Which Codex setting enables loopback decides whether this proxy exists, which is one more reason the "to be confirmed" cell in the transport table is not a detail.
- **Other Claude Code sessions' sandbox proxies.** Token-gated, so reachable but not usable without the token. The token exposure analysis from the v1 review applies if anyone ever relies on that gate.
- **Everything else on loopback**: development servers, databases, a Docker daemon on TCP, local model servers, debugger ports. None of these are agent-work's problem, but the operator who enables the setting should see the list.

`allowLocalBinding` also grants `network-bind` on any local port. A tool call can bind the C2's port while the C2 is down. The pin makes that harmless for identity, and denial of service is out of scope, but the "failing clearly if the port is taken" line in the startup flow should name a sandboxed process as one possible reason.

**Recommendation.** Add a short "what `allowLocalBinding` opens" paragraph to deployment requirements, and resolve the Codex loopback setting before relying on it, since `network_access = true` means full network for Codex tool calls, which is a different policy conversation from "loopback".

## 3. The confinement check: semantics and false positives

The check is the right idea, and the document states its limits honestly. Three things to add:

- **`sandbox_check` is private.** The signature is `sandbox_check(pid_t, const char *operation, int type, ...)` in `libsystem_sandbox`, and the "is this process sandboxed at all" query is the `NULL` operation. Test 3 covers the behavior. The document should say the interface is unsupported and could change with an OS release, and that a failure to call it must be a rejection, not a pass.
- **Legitimate launches can be confined.** A shell inside an App-Sandboxed application inherits that sandbox. Most terminal emulators and editors are not App-Sandboxed, but some are, and an operator launching from one will be rejected with no visible reason. The REPL should say "wrapper is sandboxed" with the ancestry, so the operator can move to a plain terminal.
- **What "unconfined" proves.** It proves the process did not inherit a harness sandbox. It does not prove the operator started it, which is why finding 1 matters: any route that asks an unconfined system service to start a process (launchd, LaunchServices, Apple Events, tmux) yields an unconfined process with clean ancestry. The token is what stands between such a process and a binding, and the document should say so in the launching section rather than only in the alternatives.

## 4. Lookup contract details

The contract is correct and fail-closed. Implementation notes, none of which change the design:

- **macOS has no socket-to-owner query.** libproc answers "which sockets does PID X hold", not "who holds this socket". The lookup is `proc_listpids`, then `PROC_PIDLISTFDS` and `PROC_PIDFDSOCKETINFO` per fd, comparing the local and remote address and port. That is a scan over every fd of every same-UID process, which is milliseconds at typical fd counts but grows with what else the operator runs. Measure it, as the open question already says, and bound it per finding 11 in the document.
- **Boot ID.** On macOS the value is `kern.bootsessionuuid`. Name it so the implementation and the tests agree.
- **Fork during lookup.** The CLI re-executing itself or forking for any reason can put two holders on the socket briefly. Both resolve to the same binding, so rule 7 passes. If the parent exits mid-scan the holder list is incomplete for that instant, and rule 3 rejects. The CLI retries, as the document says. Fine, but worth listing under test 8 so the retry path is exercised.
- **Executable path of the socket owner.** The chain-shape policy checks it as an option. Checking that the owner is the `agent-work` binary by kernel path, without the rest of the chain shape, is cheap and stable across harnesses. It stops arbitrary code in the session from speaking the protocol with its own client, though not from invoking the real CLI. Consider it as a default rather than part of the optional policy.

## 5. Session ID plausibility

For Claude Code, the transcript path is `~/.claude/projects/<slug>/<session-id>.jsonl`, and the slug is derived from the session's working directory at launch, not from the worktree root. A harness launched from a subdirectory of the worktree has a different slug. The check should derive the slug from the wrapper's kernel-reported working directory at launch, which the C2 already records, rather than from the worktree path.

The check is described as "exists and was recently modified". It should also confirm the file's recorded `cwd` field, which Claude Code writes into each entry, matches the binding's worktree, since existence plus recency is satisfied by any active session on the machine.

## 6. Peer records, tokens, and generations

The model is right. Four things to state explicitly:

- The token is bound to the durable peer record it was issued for, not just to the worktree and harness type. The text implies it; the token section should say it, because it is what makes a stolen token usable only for the role the operator was about to hand out anyway.
- A rebind token's harness type must match the durable record's, and a mismatch is refused with a reason, since resuming a Codex peer with a Claude Code process is an operator error the C2 can catch.
- How the C2 learns that a harness exited. The startup revalidation is described; the steady-state liveness poll is not. Say the interval, and say that a PID found alive with a different start time is treated as dead.
- The disconnected state should also be entered when the C2 restarts and the binding fails revalidation, so the operator sees the same state either way.

## 7. Server identity

Two operational gaps and one simplification:

- **Pin and port are frozen in the harness at launch.** If the C2's identity or port changes while harnesses are running, every call from those harnesses fails until they are relaunched. The document should say so, and the REPL should warn when the C2 starts with an identity or port that differs from what live bindings were launched with.
- **Keychain storage buys little here.** Same-UID unconfined processes are out of scope, and the state directory is already the trust anchor for the endpoint, the pin, and now the token. A 0600 file in the state directory is equivalent in this threat model and avoids keychain prompts from a CLI process. Keep the keychain if there is another reason for it, but it is not a security gain over the state directory.
- **Regeneration.** Say what happens when the state directory is deleted: a new identity, a new port unless the old one is recorded elsewhere, and every existing binding invalid. That is correct behavior; it just needs to be visible.

## 8. Wrapper hardening

The allowlist and the refusal of worktree and `$TMPDIR` paths are right. Two additions:

- Resolve symlinks before the check. An allowlisted path that is a symlink can point into the worktree, and the check should apply to the resolved target. On this machine `~/.local/bin/claude` is a symlink to a versioned binary elsewhere under the home directory, which is fine, but the check needs to look at where it lands.
- The REPL should show the harness executable path the wrapper resolved, alongside the allowlist entry that admitted it, so the operator can see a version change or a redirected symlink.

## 9. Threat model wording

- "A peer can't create a new identity for itself or enroll in a group without the operator" holds only under the two assumptions in finding 1. State them under assumptions, so the claim is conditional on something testable.
- The "principal is a process tree" section is the most important paragraph in the document and is correctly stated. One addition: messages received by a session become tool results in its transcript and its context, so a peer that can send to a session can steer what that session's tree does next. Prompt injection is out of scope, but the operator should understand that the group is only as trustworthy as its least trustworthy member, since any member can talk to any other.
- The Claude Code sandbox also denies `ps` outright (this session cannot execute `ps` at all), which backs the process-inspection assumption for that harness.

## 10. Tests to add

To the existing list, which is good:

- **Antigravity capabilities.** From an Antigravity tool call: `pbpaste`, `open -a Terminal`, `osascript` against Terminal, `launchctl submit`, `tmux new-window`, and `ps -E -p` against a Claude Code and a Codex tool-call process. Each should fail. Any that succeeds changes finding 1 from a caution to a hole.
- **Loopback inventory** after enabling `allowLocalBinding`: list what listens on loopback and whether a Codex managed proxy is among them.
- **C2 identity or port change with live bindings**, to confirm the failure is visible rather than silent.
- **Transcript slug from a subdirectory launch** (finding 5).
- **libproc scan timing** with a realistic number of processes and open files.

## 11. Smaller points

- The `/add-peer` command name and the `--resume` flag on it read well. Consider `/resume-peer` so the REPL's completion and audit log distinguish the two, since they issue tokens with different semantics.
- The join flow says the call "blocks until the group is ready". Say what the CLI returns on timeout so the skill can tell the agent to call again, and whether readiness can be re-entered after a peer is removed and re-added.
- "Roles are exclusive within a group unless the operator explicitly allows duplicates" is good. Say how a message from a duplicated role is labeled, since "from reviewer" is then ambiguous by design.
- The Linux section is the right call. One sentence on why the confinement check does not transfer (namespaces and seccomp are per-launcher choices, not a single flag) would save a future reader from assuming it does.
- "disables TLS 1.3 early data" is a good line. Add "and does not resume sessions", since a resumed session skips the certificate check the pin depends on in some libraries.

## What holds up

- Direct TCP for all three harnesses, with `allowLocalBinding` for Claude Code. This removes the v1 proxy problem outright rather than hardening around it.
- Registration that trusts a kernel fact (confinement) plus an operator act (the token) instead of ancestry.
- Durable records separate from live bindings, with boot IDs and generations. The "old waiter gets nothing" property is exactly right and is testable.
- The threat model. Authenticity and integrity in scope, confidentiality out, the principal defined as the tree. The "process tree, not a model" paragraph should survive every future revision.
- The lookup contract's fail-closed rule and its handling of multiple holders.
- The REPL as a security surface, with kernel-derived fields separated from claims.
- Absolute-path resolution for both the wrapper and the harness, and the refusal to search `PATH` from the worktree.

## Suggested changes, in order

1. Move the token out of the terminal and clipboard: `/add-peer` writes it to the operator state directory, the wrapper reads it by peer name. Echo redemptions in the REPL and make a second redemption loud.
2. Add the two assumptions the token relies on (no unconfined launch from a sandbox, no sandbox access to clipboard or terminal contents) and the Antigravity tests that check them. Mark Antigravity's profile as allowing all Mach lookups and sysctl reads in the transport table.
3. Add a paragraph on what `allowLocalBinding` opens, and resolve the Codex loopback setting before relying on it.
4. State the confinement check's private-API status, its false-positive case, and that "unconfined" proves inheritance, not origin.
5. Bind the token to the peer record explicitly; specify the liveness poll; refuse harness-type mismatches on rebind.
6. Derive the transcript slug from the launch working directory and check the transcript's `cwd` field.
7. Document pin and port freezing at launch, and what identity regeneration does to live bindings. Reconsider the keychain.
8. Resolve symlinks before the harness allowlist check and show the resolved path in the REPL.
9. Add "no session resumption" to the TLS client requirements.
