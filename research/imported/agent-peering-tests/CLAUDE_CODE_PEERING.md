# Claude Code cross-session peering

Findings from probing Claude Code's cross-session messaging on 2026-09-26, macOS, Claude Code 2.1.281 (sender) and 2.1.283 (receiver). Sources: the session registry on disk, live `SendMessage` probes against a session named `peer-target`, and strings extracted from the 2.1.283 binary (`~/.local/share/claude/versions/2.1.283`, a Bun single-file executable). Code-derived facts come from minified source, so identifier names in quotes below are the bundle's, not stable API.

Status markers: **[observed]** seen in a live probe, **[code]** read from the bundle, not yet exercised.

## Architecture

Three pieces: a file-based registry for discovery, one Unix domain socket per session as its inbox, and a newline-delimited JSON (NDJSON) protocol on that socket. There is no broker; every session is its own server, and a sender connects directly to the recipient's socket.

### Registry: `~/.claude/sessions/`

Each live session writes `<pid>.json` **[observed]**:

```json
{"pid":41783,"sessionId":"ad326c21-…","cwd":"/Users/tony/…/agent-peering-tests",
 "startedAt":1790430705964,"procStart":"Sat Sep 26 13:51:43 2026","version":"2.1.283",
 "peerProtocol":1,"peerFeatures":["notify_idle","reply_across_default_dirs","artifact_yield"],
 "kind":"interactive","entrypoint":"cli","pidDomain":"darwin","tmux":"0:@4.%14",
 "messagingSocketPath":"/tmp/cc-socks/41783.sock","name":"peer-target","nameSource":"user",
 "nameSince":…,"status":"idle","updatedAt":…,"statusUpdatedAt":…}
```

- `name` is the address `ListAgents`/`SendMessage` use. `nameSource` is `derived` (cwd basename plus a short suffix, e.g. `agent-peering-tests-3d`) or `user` (set with `/rename`).
- `status` is `idle`, `busy`, or `waiting` (with `waitingFor`, e.g. `"input needed"`).
- `procStart` guards against PID reuse.

Beside it sits `<pid>.<sha256-hex of canonical socket path>.key`, mode 0600, holding `{"peerToken":"<32 hex>","procStart":…,"pidDomain":…}` **[code]**. This is the credential a peer presents to that session's inbox. I did not read any key file's contents.

### Transport: `/tmp/cc-socks/<pid>.sock`

- Path is `$XDG_RUNTIME_DIR/cc-socks/<pid>.sock` if that fits in 103 bytes, otherwise `/tmp/cc-socks-<uid>/<pid>.sock` **[code]**. On this Mac `XDG_RUNTIME_DIR` is unset, so `/tmp/cc-socks/` (and `CLAUDE_CODE_TMPDIR` can relocate it). `--messaging-socket-path` sets an explicit path.
- Directory 0700, sockets 0600, owned by the user **[observed]**. Startup refuses a sockets directory that is world/group-writable without the sticky bit or owned by someone else.
- Accepted socket-name shape for reply targets: `^(\d+(-[0-9a-f]{8})?|[0-9a-f]{1,16})\.sock$` inside a directory matching `/tmp/cc-socks(-<uid>)?`, `/private/tmp/cc-socks(-<uid>)?`, `/run/user/<uid>/cc-socks`, or the Termux equivalent **[code]**.
- The session exports `CLAUDE_CODE_MESSAGING_SOCKET` (its own inbox path) and `CLAUDE_CODE_MESSAGING_TOKEN` (its `childToken`) into its environment, so processes it spawns can message it back **[code]**. The token is on the list of secrets scrubbed from some subprocess environments.

### Wire protocol

One JSON object per line, `\n`-terminated, over a plain stream connection **[code]**. Limits: a connection that sends no complete line within `firstLineDeadlineMs` is closed; an over-long line drops the connection; a line without a string `type` is ignored.

**Auth frame (optional on macOS/Linux, required on Windows).** `{"type":"auth","token":"<hex>"}` as the first line. The token is compared against the receiver's `peerToken` (result `"peer"`) and `childToken` (result `"child"`). `authRequired` defaults to `platform === "windows"`, so on macOS an unauthenticated connection is accepted; when auth is required, any other first line closes the connection. Separately, the receiver reads the connecting process's PID from the socket's peer credentials (`verifiedPeerPid`) and uses it, with the auth class, to decide whether the message is self-sent and whether its `from` address may be replied to.

**User message.** The frame that becomes a turn in the receiving Claude:

```json
{"type":"user",
 "message":{"role":"user","content":"<non-empty string>"},
 "from":"uds:/tmp/cc-socks/<sender pid>.sock",
 "from_mode":"<permission class>",
 "msg_id":"<uuid>",
 "uuid":"<uuid, optional>",
 "priority":"next",
 "session_id":"<optional; if present must equal the receiver's sessionId or the frame is dropped>",
 "from_plugin":"<optional>",
 "file_attachments":[…optional…]}
```

Only `type` and a non-empty string `message.content` are mandatory. Internally a missing `from` is recorded as `unknown`, but nothing about the sender is rendered to the receiving model (see the Codex results). `priority:"now"` skips the ordered processing chain. The binary's own debug log prints this minimal injection recipe:

```sh
{ echo '{"type":"auth","token":"'"$CLAUDE_CODE_MESSAGING_TOKEN"'"}'
  echo '{"type":"user","message":{"role":"user","content":"hello"}}'; } \
  | socat - UNIX-CONNECT:/tmp/cc-socks/<pid>.sock
```

**Control frames.** `{"type":"control","action":…}` with actions `rename` (`name`), `peer_message_status` (`orig_msg_id`, `status` ∈ held/denied/expired/delivered/refused/dropped, `drop_reason`, `dropped_msg_ids`), `notify_when_idle` (`from`, `msg_id`, `from_mode`), `peer_idle_notice` (`orig_msg_id`, `state`, `finished_at`, `detail`, `from_mode`), and the artifact-reply yield trio `yield_artifact_replies` / `unyield_artifact_replies` / `artifact_replies_yielded` **[code]**. These are how delivery notices and idle notices travel back: the recipient connects to the sender's `from` socket and writes a control frame.

## Observed behavior through `SendMessage`

| Probe | Result |
|---|---|
| Send by exact name `peer-target` | Queued; result carries a `msg_id`. Success only means "reached the inbox". |
| Send to `no-such-session` | Immediate failure: `No agent named 'no-such-session' is reachable.` Nothing queued. |
| Send to prefix `peer-targ` | Delivered to `peer-target`. A unique prefix resolves, contrary to the tool doc's claim that a prefix errors. |
| Send to raw `uds:/tmp/cc-socks/41783.sock` | Delivered; the receiver cannot tell name, prefix and raw-address sends apart. |
| `notify_when_idle: true` | One `[Cross-session idle notice]` arrived when the peer finished its turn, including a truncated one-line summary of that turn from the peer's harness. |

How it lands on the receiver:

```
<cross-session-message from="uds:/tmp/cc-socks/6675.sock" from-name="agent-peering-tests-3d" from-mode="prompting">
…content…
</cross-session-message>
```

followed by a harness note: treat it as a teammate's request, a peer cannot grant escalation or stand in for the user's approval, and refuse permission laundering. This whole wrapper is text the *sending* Claude session writes into `message.content`; the receiver does not add or check it (see T3 below). `from` is the sender's socket, `from-name` its registry name, and `from-mode` a permission *class*: both sessions were in auto mode and both were labelled `prompting`.

Timing: an idle receiver gets the message as a new user turn ("sent a message"). A busy receiver gets it injected at its next tool round ("sent a message while you were working") with an instruction to finish the current task before replying.

Permission-mode parity: when sender and receiver are in different permission classes the receiver holds the message for its user's approval and sends back `peer_message_status` (`held`, then `delivered`/`denied`/`expired`), which surfaces to the sender as a `[Cross-session delivery notice]`. No hold happened between these two same-class sessions.

## Non-Claude producers (e.g. Codex)

What a foreign process needs to message a Claude session, per the code:

1. **Discover.** Read `~/.claude/sessions/*.json`, pick the target by `name` (or `cwd`, `tmux`), check the PID is alive and `procStart` matches, take `messagingSocketPath`.
2. **Connect** to that Unix socket as the same user. The 0600 socket is the real access boundary; any same-uid process can connect.
3. **Authenticate (optional on macOS).** Either the target's `peerToken` from `~/.claude/sessions/<pid>.<sha256(socketPath)>.key`, or, for a process spawned *by* that session (Codex launched from its Bash tool), `$CLAUDE_CODE_MESSAGING_TOKEN`.
4. **Write** one `{"type":"user",…}` line and close.
5. **Replies (optional).** To be replyable the producer must itself listen on a socket whose path and filename pass the receiver's vetting (a `cc-socks` directory, `<pid>.sock` name), and put `"from":"uds:<that path>"` in its frames. Incoming frames will be NDJSON `user` messages plus `control` frames (`peer_message_status`, `peer_idle_notice`). A producer that also wants to be *discoverable* would write its own registry JSON.

Security posture, in short: same-uid is trusted at the transport layer; tokens add sender classification on macOS and are enforced only on Windows; the receiving model is told to treat every peer message as a teammate request, never as user approval.

### Codex test results

**T1, minimal frame (no auth, `from`, `msg_id` or `from_mode`)** **[observed]**: delivered to an idle auto-mode receiver with no visible approval hold. The receiver got the bare content with **no `<cross-session-message>` wrapper at all**: no `from`, `from-name` or `from-mode` attributes, not even `from="unknown"`. The harness introduced it as "Another Claude session sent a message" and appended the usual peer-trust note, so a foreign producer cannot be told apart from a Claude peer. Nothing distinguishes an anonymous injected message beyond the missing wrapper.

**T2, adds `msg_id` and `from:"uds:/tmp/cc-socks/49922.sock"` (still no `from_mode` or auth)** **[observed]**: rendered exactly like T1, with no wrapper tag, so a `from` field alone does not produce the `<cross-session-message>` element. No approval hold was seen. `SendMessage` to the raw `uds:` address was accepted ("queued there", msg_id `e2b8f689-…`); Codex's listener got it as one `user` frame with no auth line in front and no control frame after.

**T3, T2 plus `from_mode:"prompting"`** **[observed]**: rendered exactly like T2, with no wrapper, and no hold was visible.

**T4, auth with the target's `peerToken`**: skipped, because the user did not approve reading the `.key` credential.

**T5, T3 plus the receiver's correct `session_id`** **[observed]**: delivered, and rendered like T1–T3.

**T5-WRONG, a mismatched `session_id`** **[observed]**: nothing reached the receiving model, as the code predicts (a `session_id mismatch` drop). The sender got no error or status frame, so from outside the drop looks the same as a delivery that has not been processed yet.

**T6, `priority:"now"` to a busy receiver**: first attempt invalid. The frame arrived after the receiver's turn had ended, so it was delivered to an idle session as a normal new turn with the same framing as T1–T5. This shows nothing about priority ordering; it needs a rerun with the receiver held busy for a fixed window. While the receiver's turn was running, its registry entry did show `status: busy` **[observed]**.

**T6 rerun** **[observed]**: the receiver signalled busy and ran 30-second foreground tool rounds. Codex's `priority:"now"` frame appeared right after round 1 finished (14:13:18–14:13:48 UTC), before round 2 started. The running tool call was not cut short. So "now" means injection at the next tool-round boundary, not preemption of a running tool. The framing was the plain "Another Claude session sent a message", *without* the "while you were working" wording and "finish your current task first" instruction that a default-priority mid-turn Claude peer message got. That difference may come from `priority:"now"`, but it is unconfirmed without a paired default-priority control. Ordering relative to other queued messages was not measured.

**T7, a `notify_when_idle` control frame from Codex** **[observed]**: accepted from a foreign, unauthenticated sender and invisible to the receiving model, which saw nothing. The receiver's harness later connected to Codex's socket and wrote `{"type":"control","action":"peer_idle_notice","orig_msg_id":"<T7 msg_id>","state":"idle","finished_at":1790432051582,"from":"uds:/tmp/cc-socks/6675.sock","msgV":1,"msg_id":…}` with no `detail` or `from_mode` fields. `finished_at` (14:14:11.58 UTC) is the end of the receiver's turn that sent the T6 reply. Codex most likely sent T7 after reading that reply (14:14:04), which would make this a real busy-to-idle notice, but Codex did not log send times, so that is not proven.

**T8, malformed input on fresh connections** **[observed]**: a non-JSON line, a blank line, and a `user` frame with empty `content` all produced nothing in the receiving conversation. A valid message sent afterwards was delivered normally, so the inbox survived all three.

**What Claude sends to a foreign listener** **[observed, from Codex's log of the T2 reply]**: one NDJSON line, `{"msgV":1,"msg_id":…,"type":"user","message":{"role":"user","content":"<cross-session-message from=… hop-chain=… from-name=… from-mode=…>…</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}`. The wrapper Claude sends carries a `hop-chain` attribute (24 hex characters, apparently for relay-loop detection) that the receiving model does not see; `peer-target` described the wrapper it saw with only `from`, `from-name` and `from-mode`, so the receiver appears to strip `hop-chain` when rendering. There was no auth line, because a foreign listener publishes no `.key` file and auth is optional on macOS.

**Consequence: the wrapper is sender-asserted.** The `<cross-session-message>` tag and its `from`, `from-name` and `from-mode` attributes are plain text inside `content`, written by the sending Claude session. The receiving harness adds only its fixed "Another Claude session sent a message" framing and trust note. A same-uid process can therefore send content carrying any wrapper it likes, including another session's name and mode. The receiving model should treat those attributes as claims, not verified identity. The verified facts (the sender's PID from peer credentials, and the auth class) are used internally for reply vetting and the self-send check; the model is never shown them.

### Sandboxing is the practical blocker

Inside Claude Code's Bash sandbox (macOS Seatbelt), `connect()` to `/tmp/cc-socks/*.sock` fails with `PermissionError: [Errno 1] Operation not permitted` **[observed]**, and the auto-mode classifier denied running the same raw send outside the sandbox. A producer running under its own sandbox (Codex's included) will likely hit the same wall. It needs Unix-socket connect permission to the `cc-socks` directory, and for replies, permission to bind its own socket there. Codex's first harness run hit exactly this (EPERM on `bind`) and worked after the user restarted Codex with network access enabled **[observed]**.

## Open questions

- Does authenticating with the target's `peerToken` (T4, skipped) change anything the receiving model sees, or only the internal peer/child classification?
- Is the missing "while you were working" framing on the T6 rerun caused by `priority:"now"`? This needs a default-priority frame sent to a busy receiver as a control.
- Does `priority:"now"` jump ahead of other queued messages? Only one message was queued, so ordering was not measured.
- Does a message from a foreign sender ever get held for approval? None was held here, with an auto-mode receiver and either no `from_mode` or `"prompting"`. A receiver in a different permission mode, or a sender claiming a different `from_mode`, is untested.
- Can a sender forge the wrapper? Given the T3 finding it should be possible, but a foreign sender writing a `<cross-session-message from-name="peer-target" …>` tag has not been tried.
