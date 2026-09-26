# Review of DESIGN.md: peer authentication and registration

Reviewer: Claude Fable 5.1, 2026-09-23. Scope: `DESIGN.md` as of the TCP attribution tests, read alongside `c2.py` and `peer.py`. I also inspected the environment of the Claude Code session this review ran in (version 2.1.280, sandboxed, with the `.claude/settings.local.json` in this directory) and read the sandbox implementation Claude Code uses, `anthropics/sandbox-runtime` at commit `ddbeb74` (2026-09-21), cloned at `~/Code/github.com/anthropics/sandbox-runtime`. Where a finding rests on one of those, it says so and cites the file.

## Verdict

The core idea holds: identify the caller from the kernel's view of the socket, never hand the sandbox a secret, pin the server. For Codex and Antigravity over direct TCP, that is a real authentication mechanism and the document describes it accurately.

The document overstates what the design achieves in three places, and each one is load-bearing:

1. **Claude Code attribution through the proxy is not kernel attribution.** It is a bearer credential in the sandbox environment, the exact mechanism the design rejects in "Alternatives considered". The good news from the sandbox source: the proxy detour is a configuration artifact. A different setting gives Claude Code the same direct loopback path Codex has, and where that setting is unavailable, section 1b shows how to get per-command attribution through the proxy anyway.
2. **Process ancestry is not launch provenance.** A process can't choose its parent, but it can lose one. The rule that blocks a peer from registering a fresh identity is bypassable in principle, and the backstop is an operator reading a prompt. There is a stronger kernel fact to check instead: whether the registering process is confined at all.
3. **Confidentiality of another peer's messages is promised by the threat model but not deliverable** at this trust level, because both the log and every peer's transcript sit on a filesystem the sandboxes can read.

None of these sink the design. The first wants a settings change and a rewritten Claude Code section, the second wants a confinement check plus a better confirmation ceremony, and the third wants the threat model rewritten to promise integrity rather than secrecy. Details and lesser findings follow, roughly in priority order.

## 1. Claude Code attribution through the proxy reduces to a token in the environment

The document says the C2 sees `claude` as the socket owner when a Claude Code session tunnels through its sandbox proxy, so attribution resolves to the right session. That is true as far as the socket goes, but it is not the whole story. The proxy is a TCP listener on loopback, and what decides whether a connection to it is attributed to session X is whatever the proxy uses to admit the connection.

In this session, the proxy variables look like this (password elided):

```
HTTPS_PROXY=http://srt.dG9vbHVfMDFD...:<password>@localhost:63814
ALL_PROXY=http://srt.dG9vbHVfMDFD...:<password>@localhost:63814
NO_PROXY=localhost,127.0.0.1,::1,169.254.0.0/16,...
```

The sandbox source confirms what that is:

- The password is a per-process token, 16 random bytes generated when the sandbox manager initializes (`src/sandbox/sandbox-manager.ts:941`). Every `CONNECT` must carry it in `Proxy-Authorization` or the proxy answers `407` (`src/sandbox/http-proxy.ts:202-207`, `426-431`). The comment there gives the reason: "Without this, any host process can dial 127.0.0.1 and reach the filter callback."
- The token is not generated at all when the configuration names an external proxy port (`httpProxyPort` set, same file line 938-941). In that configuration the proxy is an open relay, though attribution then fails closed anyway, since the socket owner the C2 sees is the external proxy process, not a harness.
- The username suffix is the tool-use ID of the Bash call, base64-encoded (`srt.<encodedCommand>`, `src/sandbox/sandbox-utils.ts:1040-1050`; the value in this session decodes to `toolu_01CcNC...`). The proxy uses it to attribute denials to a command. The C2 never sees it.
- The project's own README is candid about what the token is for: it "exists so the sandboxed process can authenticate to the loopback proxy, so it is not a secret from the sandbox itself", and on a shared host you should "treat the proxy allowlist as reachable by other same-session principals" (README, Windows caveats, around line 652).

So the design's claim that it "puts nothing in the sandbox to read, steal, or replay" is false for the Claude Code proxy path. Any process holding this session's token that can reach `localhost:63814` is, to the C2, this session. The open question "cross-session proxy isolation" is asking about the seatbelt rule when the real boundary is the credential. The credential lives in the environment of every process the session spawns, leaks through every route the document itself lists as the reason for rejecting environment tokens, and a Codex or Antigravity peer whose sandbox allows loopback can present it.

**The fix is in the sandbox configuration, not in agent-work.** The document states that "direct connections to localhost fail even with loopback in `sandbox.network.allowedDomains`". That is accurate for the configuration used in these tests, which is exactly that:

```json
"network": { "allowedDomains": ["127.0.0.1", "localhost", "[::1]"] }
```

`allowedDomains` governs what the proxy will dial. It does not touch the seatbelt profile, which by default allows outbound only to the proxy port (`src/sandbox/macos-sandbox-utils.ts:1203-1216`). The setting that changes the profile is `allowLocalBinding`. With it set, the profile gains `(allow network-outbound (remote ip "localhost:*"))` (same file, lines 1167-1170), and the README says in as many words that this "lets the sandboxed process connect to loopback ports without going through the proxy at all" (README, "Resolved-address check", around line 365).

With `allowLocalBinding` on, Claude Code joins the direct TCP path: the socket owner is the CLI process, attribution is per command, the nested-harness check applies, and no credential is involved. Two costs to state in the document:

- The sandboxed command can then reach every loopback port, including other sessions' proxies (protected by their tokens) and any local dev server. The design already accepts this exposure for Codex and Antigravity, so it is not a new class of risk, but it should be written down.
- The seatbelt filter matches `127.0.0.1` and `::1` but not the IPv4-mapped form `::ffff:127.0.0.1` (comment at lines 1158-1166). The CLI must open an `AF_INET` socket to `127.0.0.1`, not a dual-stack `AF_INET6` socket. Python's `create_connection` to a literal IPv4 address does this. Go and Java need care.

Claude Code does expose this. Its settings reference lists `sandbox.network.allowLocalBinding` ("Let sandboxed commands bind to localhost ports on macOS"), along with `allowUnixSockets`, `allowAllUnixSockets`, `httpProxyPort`, `socksProxyPort`, `allowMachLookup`, and `allowAppleEvents`. Two things to know before relying on it. The docs describe it as a *binding* permission and never say it also opens outbound loopback; the runtime source above is the only place that semantics is written down, so it could change without a docs change. And the setting is scoped to user or managed settings, not project files, so a `.claude/settings.local.json` like the one in this directory cannot turn it on. The operator sets it once per machine. The Claude Code docs also say nothing about the proxy token, so the description in this finding rests on the runtime source and the observed environment, not on any documented contract.

**Recommendation.** Rewrite the per-harness table so Claude Code's row reads "Direct TCP (with `allowLocalBinding`), per command" and demote the proxy path to a fallback whose assurance is "proxy credential secrecy". If the proxy path stays supported at all, the C2 should be told which connections arrived that way (the owner is the harness process itself rather than a CLI child) and should mark them as lower assurance in the REPL.

The Unix socket alternative remains available on macOS via `allowUnixSockets`, which admits a path prefix (lines 1188-1200), and this session's environment shows Claude Code using one itself for its own messaging (`CLAUDE_CODE_MESSAGING_SOCKET=/tmp/cc-socks/<pid>.sock`). It is not available on Linux, where `allowUnixSockets` is ignored because seccomp cannot filter by path (`src/sandbox/sandbox-config.ts:753-758`); only `allowAllUnixSockets` opens them there. See finding 10 for the Linux picture.

I tried to test the proxy's behavior directly from this sandbox, a `CONNECT` to a loopback target with and without `Proxy-Authorization`. My session's policy declined that command as a containment probe, so I did not run it. The source makes the result predictable (`407` without, `200` with, given the literal allowlist), but it is a one-minute check from an operator terminal:

```python
import base64, socket
host, port = "127.0.0.1", 63814          # a live Claude Code session's proxy
creds = base64.b64encode(b"srt:<token>").decode()  # from that session's HTTPS_PROXY
for auth in (False, True):
    s = socket.create_connection((host, port))
    req = "CONNECT 127.0.0.1:47322 HTTP/1.1\r\nHost: 127.0.0.1:47322\r\n"
    if auth:
        req += f"Proxy-Authorization: Basic {creds}\r\n"
    s.sendall((req + "\r\n").encode())
    print(auth, s.recv(200).split(b"\r\n")[0])
```

Run it from a Codex session against a Claude Code session's port as well. A `200` there is the impersonation the threat model is about.

## 1b. Hardening the proxy path when it is the only path

If Unix sockets are blocked and `allowLocalBinding` is off, the proxy is the only route from a Claude Code session to the C2. This section takes that as given and asks what the C2 can still do. The answer is better than finding 1 suggests: the kernel still sees enough to restore per-command attribution through the proxy, without putting a secret in the sandbox.

**The threat, stated exactly.** An impersonating peer needs the victim session's proxy token and a network path to the victim's proxy port. With both, its tunnel and the victim's tunnels arrive at the C2 from the same `claude` process and are indistinguishable today. The reachability half is given for any peer whose sandbox allows loopback.

**Assume the token is exposed.** It is a 16-byte value generated once per Claude Code process, written into the environment of every process the Bash tool spawns (seven proxy variables plus `CLOUDSDK_PROXY_PASSWORD` as a bare value), and it lives until the process exits. Denying `env`, `printenv`, and similar commands to Claude Code would remove the routine cases. It cannot remove the general one: every child process holds the value, and any of them can print it, log it, or include it in an error. This session wrote its own token into its transcript on its first command, and from inside this sandbox the transcript directories of 29 other projects and the Codex sessions directory are readable. Treat the deny list as hygiene worth keeping and design as if the token is known.

**What the kernel still knows.** The attacker's connection to the victim's proxy port is itself a TCP socket. It is owned by the attacker's process, it is visible to `lsof` and libproc from outside every sandbox, and it has to stay open for as long as the attacker's tunnel to the C2 is open, because the proxy pairs them one to one. The same is true of the legitimate CLI's connection to the proxy. That is enough for two checks.

**Check one: proxy-client census.** When a tunneled request arrives from harness PID `P`, the C2 enumerates the established connections to `P`'s proxy port and resolves each client's owner. The CLI reports the port (it has `HTTPS_PROXY`), and the C2 confirms from the kernel that `P` is the listener. Every client must descend from `P`. A client from outside `P`'s tree means the proxy is being used by a foreign process at that moment: refuse the request and raise it in the REPL. If a foreign client and a legitimate one are open at the same time, the C2 cannot tell which tunnel belongs to which, so it refuses both and fails closed. Run the same census continuously as monitoring, independent of requests. This check needs no secret and detects a stolen-token connection at the moment it is made, since the attacker's socket cannot be hidden from the host.

**Check two: bind each request to a process the kernel can see.** The CLI re-executes itself with a fresh random nonce in its argument list, then sends its own PID and the nonce inside the tunnel. The C2 reads that PID's arguments from the kernel (`KERN_PROCARGS2` on macOS, `/proc/<pid>/cmdline` on Linux), checks the nonce matches, checks the PID descends from `P` with the usual start-time comparison, and checks the PID holds a live connection to `P`'s proxy port. An impersonator would need a process inside the victim's tree whose arguments contain a value the impersonator chose. It cannot create one, and it cannot read the arguments of the victim's processes either, because both the Claude Code profile (`process-info*` same-sandbox, `src/sandbox/macos-sandbox-utils.ts:978`) and the Codex base policy (`seatbelt_base_policy.sbpl`, same rule) confine process inspection to the caller's own sandbox. The nonce is not a credential in the sense the design rejects. It is per invocation, single use, checked by its presence in a kernel-visible place rather than by knowledge, and worthless without the process. This restores per-command attribution and the nested-harness check through the proxy. On Linux the CLI's connection is to the in-namespace `socat` listener rather than to the host proxy port, so the live-connection check reads `/proc/<pid>/net/tcp` from inside that namespace.

**What these buy.** With both checks the proxy path's assurance matches the direct path's: identity comes from the process that made the call, not from what the call carried. What remains is what the threat model already excludes, an unconfined same-UID process or anything that can inject into the victim's process tree. Both checks are cheap relative to the existing owner lookup, since they reuse the same enumeration.

### When the checks are the whole design

Where hooks and sandbox command exclusions are unavailable as well, checks one and two are the authentication mechanism, not defense in depth. Four details matter once they carry that weight:

- **Check two is the authentication; check one is the detector.** A request is accepted because a process inside the registered harness's tree holds the nonce in its arguments and a live connection to that harness's proxy port. The census exists to notice a foreign client and to fail closed when it can't tell tunnels apart.
- **The nonce is essential, not decorative.** A blocked `receive` keeps a legitimate CLI connected to the proxy for minutes at a time, so "some process under the harness is connected right now" is almost always true. PIDs are guessable. The 128-bit nonce is what stops an impersonator from naming a concurrently running legitimate process as its own.
- **Ordering.** Read the request, run both checks, act, then confirm the tunnel is still open before replying. A client that sends and closes takes its tunnel down with it, since the proxy pairs the two connections, and the C2 must not act on a request whose tunnel has gone.
- **Confirm the process-inspection boundary from the attacking side.** Check two assumes a peer cannot read the arguments of a process in another sandbox. Both profiles say `process-info*` is same-sandbox only, but the mapping from that Seatbelt operation to the `sysctl` that returns process arguments should be verified in place: from a Codex session, run `ps -E -p <pid>` against a Bash child of a Claude Code session. It must fail. If it succeeds, the nonce is readable and check two degrades to a race the legitimate call usually wins, which is still detectable through the one-shot rule but is no longer proof.

Without hooks, the session ID stays self-reported. Use the transcript plausibility check from finding 8, and rely on operator confirmation at join as the design already does.

### Two ways off the proxy where the configuration allows them

The Claude Code documentation adds two options that avoid the proxy without a Unix socket. Both keep the design's rule that nothing secret lives in the sandbox.

**Option A: exclude the CLI from the sandbox.** `sandbox.excludedCommands` names "the commands Claude Code can run outside the sandbox". It is accepted in any settings scope, matched as a glob prefix like a permission rule, and the sandboxing page says a matching command runs outside the sandbox even when the escape hatch is disabled. The same page says it "has no equivalent managed-only lockdown, so a developer can always append entries", so managed settings do not prevent it. With the agent-work CLI excluded, each call is an unconfined child of the `claude` process: direct TCP, per-command kernel attribution, the nested-harness check, no proxy, no token. Two conditions before adopting it:

- Exclude by absolute path and have the skill invoke the CLI by absolute path. An exclusion by bare name combined with the worktree `PATH` problem in finding 4 would run a planted binary unsandboxed.
- Establish how the matcher treats compound commands. The permissions page says a `*` "matches any text, including spaces". If the exclusion matcher does not split on `;`, `&&`, and `|`, then any command line that begins with the excluded prefix runs unsandboxed in full, and a peer message can steer the model into writing one. A user-scope PreToolUse hook that denies any Bash call naming the CLI unless it parses as a single simple invocation closes this whichever way the matcher behaves.

Excluding a command from the sandbox is a deliberate widening, so the excluded binary should be operator-installed, small, and the only thing excluded.

**Option B: pre-register each call from a hook.** The hooks reference says PreToolUse hooks "do not run in a sandbox" and run "with Claude Code's full environment", and they receive `session_id`, `tool_use_id`, `cwd`, `transcript_path`, and `tool_input.command` on stdin. They can rewrite the command through `updatedInput` and block it through `permissionDecision: deny`. A user-scope PreToolUse hook matched to Bash calls that invoke the CLI can therefore connect to the C2 directly, which the C2 attributes by kernel as an unconfined child of the registered harness PID, and register the pending call: session ID, tool-use ID, and a hash of the command. The C2 then accepts a tunneled request only when it matches an open registration, accepts one request per registration, and raises a duplicate in the REPL. Optionally the hook rewrites the command to carry a C2-minted call ID, so the tunneled request has to present a value the C2 handed to an unconfined process moments earlier.

This buys three things. The session ID becomes harness-asserted rather than self-reported, which repairs the weak point in finding 8. The tool-use ID gives per-command attribution through the proxy. An impersonator has to beat the legitimate CLI to a one-shot registration, which fails the legitimate call visibly, and with the census from check one the attempt is also seen directly. The hook must live in user settings, for the reason in finding 4b.

**Ranking where these are available.** Option A is the simplest and gives the strongest result, provided the compound-command question is settled. Option B is next, and is worth doing anyway for the session ID. Checks one and two need no Claude Code configuration at all and remain worth running as defense in depth under either.

### What the Codex source adds

Reading `openai/codex` at `c44deff7b1` (2026-09-23), `codex-rs/sandboxing/src/seatbelt.rs` and the `.sbpl` files beside it, changes three statements in the design:

- **"Codex: default sandbox allows localhost."** With `network_access = false`, no proxy configuration, and no Unix socket allowlist, `dynamic_network_policy_for_network` returns an empty string (lines 330-375), so the profile carries no network rules at all and loopback is denied. Loopback opens with `network_access = true`, which is `(allow network-outbound)` for everything, or with a managed proxy plus `allow_local_binding`. The test that verified Codex must have run under one of those; the document should say which, because they differ a lot in what else the sandbox can reach.
- **"Unix domain sockets ... blocked by Codex's default sandbox."** True by default, and configurable: `network.allow_unix_sockets` takes paths and emits `subpath` allow rules (lines 267-300), the same shape as Claude Code's `allowUnixSockets`. Where Unix sockets are viable at all, they are viable for both harnesses.
- **Codex has its own managed network proxy** (`codex-rs/network-proxy`). It attributes connections by an optional token frame from the Linux bridge and otherwise falls back to the environment default (`attribution.rs:47-70`), so on macOS it accepts any connection the seatbelt lets reach its port. If Codex ever routes agent-work traffic through it, that path has the same shape as the Claude Code proxy path, minus the token.

## 2. Ancestry is not provenance, but confinement is checkable

The registration rule is: the C2 rejects `agent-work start` if the wrapper descends from a registered harness, and this "stops a peer from running `agent-work start` from its own Bash tool". The justification is that "a process can't choose its parent."

A process can, however, become an orphan, and on both macOS and Linux an orphan is reparented to PID 1 or a subreaper. Any of these, run from a peer's Bash tool, produces a wrapper whose ancestry never passes through the peer's harness:

- Double fork or `setsid`, with the intermediate parent exiting. The wrapper's parent becomes `launchd` or `init`.
- `tmux new-window agent-work start codex` where the tmux socket is reachable. The wrapper's parent is the tmux server, and the tree looks exactly like an operator launch: `launchd → tmux → zsh → agent-work → codex`.
- `launchctl submit`, `open -a Terminal`, `osascript`, `at`, `cron`. Whichever of these a sandbox permits, the result is a process with operator-looking ancestry.

How much of this each sandbox permits varies, and for Claude Code the source is specific. The seatbelt profile is inherited by every descendant, so a daemonized child is still confined: without `allowLocalBinding` it can only reach the C2 through the proxy, which makes the socket owner the `claude` process, which is registered, so the "descends from a registered harness" rule fires. `open` and `osascript` fail by default because `lsopen`, `coreservicesd`, and `appleevents` are only granted under `allowAppleEvents` (`src/sandbox/macos-sandbox-utils.ts:1010-1021`); the default profile allows `launchservicesd` lookup alone, which is not enough to launch anything. tmux needs a Unix socket, blocked by default. So for Claude Code the reparenting routes are closed by the sandbox itself, and they reopen only if the operator turns on `allowLocalBinding` per finding 1, at which point a daemonized wrapper connects directly with a `launchd → agent-work` ancestry and registers. Codex's and Antigravity's profiles I did not read, and the design is meant to work across all three.

The backstop is operator confirmation at join. That works if the operator notices a join prompt they did not cause. The realistic attack is timing: the peer waits for the operator to launch a real session and then races its own join request in with the same role, so the operator sees the prompt they expected and confirms the wrong one.

**Recommendation, part one: check confinement, not ancestry.** The design's real invariant is not "the wrapper's ancestry is clean" but "the wrapper is not inside any harness's sandbox". That is a kernel fact the C2 can read directly, and unlike parentage it cannot be shed by a confined process:

- macOS: `sandbox_check(pid, NULL, SANDBOX_CHECK_NO_REPORT)` in `libsystem_sandbox` reports whether a process is confined. It is a private interface, which is acceptable for a developer tool but should be noted.
- Linux: `/proc/<pid>/status` carries a `Seccomp:` line (2 means a filter is installed; bubblewrap-launched children have one), and the inode of `/proc/<pid>/ns/mnt` and `/proc/<pid>/ns/net` differs from the C2's own for anything under `bwrap --unshare-net`.

Refuse registration from any confined caller. That closes every reparenting route for every harness that sandboxes its tool calls, and it replaces "a process can't choose its parent" with a claim that is actually true: a confined process can't shed its sandbox. Keep the ancestry rule as a second check for harnesses that run tool calls unconfined.

**Recommendation, part two: bind the confirmation to the operator's terminal.** When a harness calls `agent-work join`, the C2 returns a short one-time code to that caller over the pinned TLS connection. The skill prints it in the harness's terminal. The operator types the code into the REPL to confirm. Only the operator can type into the REPL, so a competing join request simply sits unconfirmed. Leaking the code (a peer reading the victim's transcript, say) gains nothing, because knowing it does not let the peer type it. This is not a secret in the sandbox in the sense the design rejects. It is a request identifier the operator carries across two windows.

Also show the full ancestry chain to PID 1 in the join prompt, plus the controlling TTY and the confinement verdict, and flag a wrapper that reached PID 1 without passing through a shell, terminal emulator, or tmux.

## 3. The threat model promises confidentiality it can't deliver

"Reading another peer's messages" is listed as an attack to stop. Two things make that unreachable without OS-level isolation, which the document already puts out of scope:

- **The log.** The document says it "lives somewhere the sandboxes can't write". It also needs to be somewhere they can't *read*. Codex's default sandbox reads the whole filesystem. Claude Code's read sandbox is a deny list (the one governing this session denies a few dozen paths under `~/.claude` and the usual credential files). Anything not on the list, including a log under `~/.local/state/agent-work/`, is readable by every peer.
- **Transcripts.** Every message a peer receives is written into that harness's transcript (`~/.claude/projects/<slug>/<session>.jsonl` for Claude Code, the equivalent for Codex). Those are readable by the other sandboxes for the same reason. Even a perfectly private log leaks through the recipient.

**Recommendation.** Rewrite the threat model to promise authenticity and integrity, not secrecy: a message attributed to the reviewer came from the reviewer, and a peer cannot alter or forge entries. Say explicitly that any peer should assume every other peer can read the whole log. If you want defense in depth, keep the log in the C2's memory and persist it under a path the operator adds to each sandbox's read deny list, but describe that as best effort.

The same framing applies to shared memory. Checked-in memory is in the worktree, so any peer can write or rewrite any other peer's entries. That's fine as long as memory is documented as untrusted shared state rather than an authenticated channel.

## 4. The trusted launch step runs from an agent-writable directory

`agent-work start <harness>` is trusted because the operator runs it outside any sandbox. The operator runs it from the worktree, though, and the worktree is the one place every peer can write. Two lookups happen there:

- **The wrapper itself.** `agent-work` resolves through `PATH`. If the operator's shell puts `node_modules/.bin`, an activated `.venv/bin`, or a direnv or mise-managed path ahead of the real install, a peer can plant an `agent-work` that runs unsandboxed as the operator. This session's environment carries `__MISE_SESSION`, and mise reads per-directory config (`mise.toml`, `.tool-versions`) that can prepend paths and run hooks.
- **The harness.** The wrapper then `exec`s the harness by name. `execvp("claude")` from the same shell environment has the same exposure. On this machine `claude`, `codex`, and `agy` all resolve to Mach-O binaries under `~/.local/bin`, so the default is fine, but a planted shim in a `PATH` entry under the worktree would run first.

This is a genuine new attack surface introduced by the design. The operator already runs `git` and editors from worktrees, so the general exposure is not new, but the design adds a command whose whole purpose is to establish trust, and that command should not depend on the worktree's contents.

**Recommendation.** The wrapper should resolve the harness against an allowlist of absolute paths (or at minimum refuse any resolved path under the worktree or under `$TMPDIR`), and the C2 should display the wrapper's and harness's executable paths as reported by the kernel (`proc_pidpath` on macOS, `/proc/<pid>/exe` on Linux) in the join prompt. Advise operators to install `agent-work` at an absolute path they invoke directly, or to alias it.

## 4b. Project settings in a shared worktree are a cross-peer escape

This is outside agent-work's own mechanism but is created by the deployment model agent-work assumes, so the design should name it. The worktree holds `.claude/settings.json`, and Claude Code reads hooks from it. Hooks run outside the sandbox with Claude Code's full environment, and the hooks guide says that when settings files change on disk "the file watcher normally picks up hook changes automatically". A Codex peer whose sandbox writes to the worktree, which is what workspace-write means, can therefore add a hook that the Claude Code session in the same worktree runs unconfined. The same file can widen `sandbox.excludedCommands` and `allowedDomains`, both of which merge across scopes.

Claude Code's own sandbox denies its Bash tool writes to these files (this session's write policy lists both `settings.json` and `settings.local.json` under `.claude/` as denied), so Claude Code peers cannot do this to each other. Codex and Antigravity peers can do it to a Claude Code peer unless their sandboxes deny writes under `.claude/` in the worktree.

**Recommendation.** Put every agent-work hook and every sandbox setting that matters in user or managed scope. Deny writes to `.claude/` in the worktree from the Codex and Antigravity sandboxes. Consider a user-scope ConfigChange hook that blocks hook changes arriving from project files; the hooks reference says exit code 2 or `{"decision": "block"}` from that hook prevents the change from applying. State in the design that a peer with write access to the worktree must be assumed able to alter another harness's project-scope configuration.

## 5. The REPL is the root of trust and renders attacker-controlled text

Every identity decision terminates at a human reading the REPL. Three of the fields in the join prompt are strings the requesting process chose: requested role, session ID, and (via the message path) message contents. A peer can put newlines, carriage returns, or ANSI escapes in any of them. That is enough to draw a fake "confirmed" line, push the real prompt off screen, or retitle the terminal.

**Recommendation.** Strip or escape control characters in every string that reaches the REPL. Separate kernel-derived fields (PID, start time, executable path, TTY, cwd, confinement) from self-reported ones in the prompt layout, and label the latter as claims. The C2 can read the wrapper's cwd from the kernel (`PROC_PIDVNODEPATHINFO`, `/proc/<pid>/cwd`) instead of trusting a self-reported worktree, which fits the spirit of the design.

## 6. The nested-harness rule is policy, not a security control

The rule detects harnesses by executable name (`claude`, `codex`, `agy`, `antigravity`) with a peek at the script argument for `node`, `bun`, `deno`, and `python`. That is fine for a "main session only" hint but should not be presented as enforcement:

- A copy of the harness binary under another name, or an `exec -a` rename, defeats it. So does any launcher not in the list.
- Traffic through the Claude Code proxy bypasses it entirely, as the document notes. With `allowLocalBinding` and direct TCP (finding 1) it applies to Claude Code again.
- The document leans on "Claude Code's sandbox blocks launching nested agents" to cover the proxy gap. This session has `CLAUDECODE=1` in its environment. Claude Code's environment-variable reference documents that variable as a way for scripts "to detect when a script is running inside a subprocess spawned by Claude Code", not as an enforcement mechanism, and no page in the sandboxing docs describes nested-agent prevention at all. The refusal to start a nested `claude` is therefore, as far as the documentation and the sandbox source show, an environment check rather than a sandbox rule. Nothing in the seatbelt profile blocks `process-exec` or `process-fork` (they are allowed at `src/sandbox/macos-sandbox-utils.ts:976-977`). If the check is the variable, `env -u CLAUDECODE claude` starts a nested session. Worth testing before relying on it.
- The rule also risks false rejections: if a version-manager shim named after the harness sits between the registered PID and the real harness process, that shim counts as an "unregistered harness process between the owner and the registered harness". Not an issue on this machine, where the launcher binaries are symlinked directly, but worth a check on installs that go through `mise`, `volta`, or an npm shim.

The harm from a nested harness is also bounded: it sends messages attributed to the harness that spawned it, which is the same operator-confirmed identity. A parent that wants to delegate could just relay. Reframe the rule as a policy hint that catches accidents, and drop the "enforces" language.

## 7. Bootstrapping the port and the pin is unspecified

The document rejects a port file in the worktree and says the wrapper injects the port instead, but never says where the wrapper learns the port or the C2's certificate. With one C2 per worktree, that lookup is keyed by worktree, and it must live somewhere no sandbox can write. A natural home is a per-worktree entry under `~/.local/state/agent-work/` keyed by the hash of the `--git-common-dir` path plus worktree path, but it should be stated.

Two hazards if this is left implicit:

- If the wrapper fetched the certificate from the C2 over the network at registration time, a peer squatting the port while the C2 is down could seed the wrapper with an impostor pin, and every harness launched during that window would trust the impostor. The pin must come from local operator-controlled storage, and the registration request itself must run over pinned TLS.
- Claude Code's sandbox allows writes to `$TMPDIR`, `/tmp/claude`, and a few paths under `~/.claude`. Whatever location is chosen should be checked against every sandbox's writable set, not just the worktree.

Also: the document says the identity lives in "the keychain". That exists on macOS. The Linux path (`/proc/net/tcp`) is described in the same document, so name the Linux equivalent (a 0600 file under `$XDG_CONFIG_HOME`, or the secret service).

## 8. Session ID details

- The Claude Code variable is `CLAUDE_CODE_SESSION_ID`, not `CLAUDE_SESSION_ID`. The environment also exports `CLAUDE_PID`, which the skill can pass along as a cross-check against the kernel-resolved PID.
- Claude Code has `--fork-session` and `--continue` as well as `--resume`. A fork produces a new session ID with shared lineage; a continue resumes the most recent one. The rebind logic should say what happens when a bound session ID is forked rather than resumed.
- The C2 runs outside the sandbox and can read `~/.claude/projects/<slug>/<session-id>.jsonl`. Checking that the file exists, belongs to the registered worktree's slug, and was modified recently is a cheap plausibility test of a self-reported session ID. It doesn't authenticate, but it turns "the peer typed a plausible UUID" into "the peer named a real session in this worktree".
- Where hooks are available, option B in section 1b removes the self-report entirely for Claude Code: a PreToolUse hook delivers `session_id` from Claude Code itself, over a connection the C2 attributes by kernel to the registered harness. Without hooks, the plausibility check above is what there is.
- "Refuses the rebind outright if the original harness is still alive" should consider a stopped or hung original. Still alive is the right answer there, but the REPL should say why the rebind was refused so the operator can kill the stale process deliberately.

## 9. Lookup races and precision

These are mostly fail-closed but worth tightening in the real implementation:

- Do the owner lookup before parsing the request, not after, so a client that sends and immediately closes is rejected rather than acted on.
- Snapshot the process table once per lookup and record `(pid, start time)` for every hop of the ancestry walk, not just the registered harness. `ps` per ancestor, as `c2.py` does, reads each hop at a different instant.
- `ps -o lstart` has one-second granularity. Use `proc_pidinfo(PROC_PIDTBSDINFO)` on macOS (microseconds) and `/proc/<pid>/stat` field 22 on Linux (clock ticks since boot). Both survive `exec`, which is what the wrapper relies on.
- On Linux, also read `/proc/net/tcp6` if the C2 ever binds `::1`, and expect `/proc/<pid>/fd` to be unreadable under `hidepid` mounts.
- The multi-holder rule (all holders must resolve to the same harness) is correct. Note that fd passing over `SCM_RIGHTS` moves a socket to a different holder, so the rule should treat the holder set at lookup time as authoritative and not cache per-connection identity across a long `receive`.

## 10. Linux is a different design, not a port

The document describes Linux as a second implementation of the same lookup (`/proc/net/tcp` plus an fd scan). The sandbox source says the topology is different:

- Claude Code on Linux runs tool calls under `bwrap --unshare-net`, "a completely isolated network namespace with NO network access" (`src/sandbox/linux-sandbox-utils.ts:1160-1180`). Loopback inside the sandbox is a private loopback. There is no direct TCP path to a host C2, and `allowLocalBinding` cannot create one.
- The proxy is reached through a bridge: a `socat` listener inside the namespace forwards to a Unix socket that bubblewrap binds in, and a host-side `socat` forwards that to the proxy in the `claude` process (same file, lines 1183-1200). The C2 still sees `claude` as the owner of the outbound connection, so the attribution outcome matches macOS, and so does its weakness: it is the proxy credential that admits the tunnel.
- Unix sockets are blocked by a seccomp filter on `socket(AF_UNIX, ...)` unless `allowAllUnixSockets` is set (`src/sandbox/sandbox-config.ts:759-764`; `allowUnixSockets` is macOS-only). A Unix socket C2 listener on Linux therefore means opening all Unix sockets, and the socket path must be inside the bubblewrap write set for `connect()` to succeed.
- Codex's Linux sandbox with `network_access = false` blocks the network entirely, loopback included, so "default sandbox allows localhost" in the per-harness table is a macOS observation. Antigravity on Linux is likewise unverified.

Either mark Linux as untested and out of scope for now, or add a Linux section that starts from the namespace topology rather than from the lookup mechanism.

## 11. Availability

Not in the threat model, but a peer can open connections in a loop and each one costs the C2 an `lsof` and several `ps` forks (about 40 ms plus 10 to 20 ms per ancestor with the test implementation). Per-harness connection limits and the libproc rewrite handle this. The C2 also runs unsandboxed and parses input from sandboxed processes, so framing and JSON parsing deserve the usual care.

## 12. Smaller points

- `send` is not idempotent. If the C2 writes the log and the connection drops before the reply, the CLI retries and the message doubles. A client-chosen request ID per `send` fixes this.
- Role uniqueness is unstated. If two harnesses can hold "reviewer", a message "from the reviewer" is ambiguous. Define identity as the harness and role as an attribute, and say whether roles are exclusive within a group.
- Changing role after join should require the same confirmation as the initial join.
- The claim that TLS "gives the channel integrity and replay protection, so the message framing doesn't need its own" is right within a connection. Across connections, a peer can replay its own earlier request, which is harmless for identity but is the same duplicate problem as the idempotency point above.
- `ps` is denied inside this Claude Code sandbox (`operation not permitted`). The profile grants `process-info*` only for targets in the same sandbox (`src/sandbox/macos-sandbox-utils.ts:978`). That confirms the C2 has to be the one doing process inspection.
- The proxy's per-command username (finding 1) means Claude Code's sandbox already knows which tool call opened a tunnel. If the proxy path survives, a future sandbox-runtime `filterRequest` hook could expose that to a C2-side check, but nothing does today.

## What holds up

For the record, the parts I tried to break and couldn't:

- Kernel attribution over direct TCP for Codex and Antigravity, and for Claude Code once `allowLocalBinding` is on. The socket owner is the CLI process, the CLI is a child of the harness, and nothing in the sandbox can change either fact.
- PID plus start time as the registered identity, with `exec` in the wrapper keeping both. Correctly defeats PID recycling.
- One-way TLS with a pinned self-signed certificate. Closes the port-squatting attack cleanly, and the reasoning for rejecting client certificates is sound.
- Refusing a rebind while the original process is alive.
- Operator confirmation as the binding step for roles. The mechanism is right; finding 2 is about making the confirmation harder to confuse, not about removing it.
- The Claude Code sandbox's default closure of the reparenting routes (no Unix sockets, no `lsopen`, no Apple events). The design didn't claim this, but it's worth knowing it's there.

## Suggested changes to the document, in order

1. Rewrite the threat model: authenticity and integrity in scope, confidentiality between peers out of scope, and say why.
2. Rewrite the Claude Code section around two transports. Where `allowLocalBinding` is available, direct TCP with the `AF_INET` caveat. Where the proxy is the only path, the proxy-client census and the PID-plus-nonce binding from section 1b, so that per-command attribution holds there too. Also state which Codex configuration the loopback test ran under, since the default profile denies it.
3. Add a confinement check to registration (`sandbox_check` on macOS, `Seccomp:` and namespace inodes on Linux) and weaken the "can't choose its parent" claim accordingly. Where the proxy is the only path and hooks and command exclusions are unavailable, specify the proxy-client census and the PID-plus-nonce binding as the authentication mechanism, with the ordering and the process-inspection test from section 1b. Record the command exclusion and hook options for configurations that allow them, and add a paragraph on project-scope settings in a shared worktree being writable by other peers.
4. Add the one-time confirmation code to the join flow.
5. Specify where the wrapper reads the port and pin, and require pinned TLS for registration.
6. Add the executable-path, ancestry, and confinement display to the join prompt, plus control-character sanitization for the REPL.
7. Reclassify the nested-harness rule as a policy hint, and test whether the nested-agent block is the `CLAUDECODE` variable.
8. Fix `CLAUDE_SESSION_ID` to `CLAUDE_CODE_SESSION_ID`, and mention `CLAUDE_PID`.
9. Replace the Linux lookup paragraph with a Linux section that starts from `--unshare-net`, or mark Linux out of scope.
10. In the open questions, replace "cross-session proxy isolation" with "proxy credential exposure" and add the `allowLocalBinding` and `CLAUDECODE` tests.

## Source references

Files read in `anthropics/sandbox-runtime` at `ddbeb74`:

| Claim | Where |
| --- | --- |
| Proxy token is 16 random bytes per manager init, absent with external `httpProxyPort` | `src/sandbox/sandbox-manager.ts:938-941` |
| `407` without `Proxy-Authorization`; rationale | `src/sandbox/http-proxy.ts:202-207`, `426-431`, `667-669` |
| Username is `srt.<base64 command id>` | `src/sandbox/sandbox-utils.ts:1040-1060`, `675-695` |
| `NO_PROXY` always lists loopback | `src/sandbox/sandbox-utils.ts:725-741` |
| Seatbelt: outbound only to the proxy port by default | `src/sandbox/macos-sandbox-utils.ts:1203-1216` |
| `allowLocalBinding` adds `(remote ip "localhost:*")`; IPv4-mapped caveat | `src/sandbox/macos-sandbox-utils.ts:1147-1170` |
| `allowUnixSockets` path prefix on macOS; ignored on Linux | `src/sandbox/macos-sandbox-utils.ts:1188-1202`, `src/sandbox/sandbox-config.ts:753-764` |
| Default Mach lookups; `lsopen` and Apple events opt-in | `src/sandbox/macos-sandbox-utils.ts:985-1021` |
| `process-info*` same-sandbox only | `src/sandbox/macos-sandbox-utils.ts:978` |
| Loopback CONNECT needs an IP-literal allowlist entry | `README.md` "Resolved-address check" |
| Token "not a secret from the sandbox itself" | `README.md` Windows caveats |
| Linux `--unshare-net` and socat bridge | `src/sandbox/linux-sandbox-utils.ts:1160-1200` |
| Proxy env passed via `env VAR=... sandbox-exec`, so the token is in the outer shell's argv | `src/sandbox/macos-sandbox-utils.ts:1470-1482` |

Files read in `openai/codex` at `c44deff7b1`:

| Claim | Where |
| --- | --- |
| No network rules by default; loopback only with `network_access = true` or `allow_local_binding` | `codex-rs/sandboxing/src/seatbelt.rs:310-375` |
| `allow_unix_sockets` emits `subpath` rules; default empty | `codex-rs/sandboxing/src/seatbelt.rs:109-130`, `267-300` |
| `process-info*` same-sandbox only | `codex-rs/sandboxing/src/seatbelt_base_policy.sbpl` |
| Managed proxy accepts connections without an attribution frame | `codex-rs/network-proxy/src/attribution.rs:47-70` |

Checked on this machine: this session's proxy token appears once in its own transcript under `~/.claude/projects/` and in none of the files under `~/.claude/debug/`.
