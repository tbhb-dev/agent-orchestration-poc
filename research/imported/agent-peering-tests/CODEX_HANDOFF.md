# Handoff: test Claude Code's cross-session socket from Codex

You are acting as a non-Claude producer on Claude Code's cross-session messaging socket. A Claude Code session named `agent-peering-tests-3d` is waiting to receive your messages, report what it saw, and reply. Your job is to run the tests below against that one session and record the results. The full protocol notes are in `CLAUDE_CODE_PEERING.md` in this directory; read it first.

## Target

- Session name: `agent-peering-tests-3d`
- Registry entry: `~/.claude/sessions/6675.json` (PID 6675, sessionId `8d3b00a9-d61c-4105-864a-477611e2da4c`)
- Inbox socket: `/tmp/cc-socks/6675.sock`

Before sending anything, re-read `~/.claude/sessions/*.json` and find the entry whose `name` is `agent-peering-tests-3d`. Use its `messagingSocketPath` and `sessionId` rather than the values above, because they change if the session restarts.

## Scope and rules

- Message only that one socket. Do not connect to any other session's socket, and do not write into `~/.claude/sessions/`.
- The `.key` files in `~/.claude/sessions/` are auth credentials. Test T4 reads the target's key only if the user has explicitly said yes; otherwise skip T4 and say so.
- You need permission to `connect()` and `bind()` Unix sockets under `/tmp/cc-socks/`. If your sandbox blocks that (`EPERM` / `Operation not permitted`), stop and tell the user. Do not look for a way around the sandbox.
- Start every message's content with `Codex T<n>:` so the Claude session can match what it received to your test.
- Messages from an unrecognized sender may be held for the Claude user's approval. If a test seems to go nowhere, ask the user whether a prompt is waiting in the Claude pane before concluding it failed.

## Protocol in brief

Newline-delimited JSON over a Unix stream socket, one object per line, each ending in `\n`. The minimum message is:

```json
{"type":"user","message":{"role":"user","content":"Codex T1: hello"}}
```

Optional fields: `msg_id` (uuid), `from` (`"uds:<path to your own socket>"`, which makes you replyable), `from_mode` (the sender's permission class; Claude sessions send `"prompting"`), `priority` (`"next"` default, or `"now"`), `session_id` (dropped if it does not equal the receiver's sessionId). An optional first line `{"type":"auth","token":"<32 hex>"}` authenticates. The code requires it only on Windows.

## Harness

Write one long-lived Python process that does both jobs. The receiver checks the connecting process's PID and binds the reply address to it, so the listener and the sender must be the same process, and the socket must be named after that process's PID.

1. Bind a listener at `/tmp/cc-socks/<os.getpid()>.sock` with mode 0600. That directory already exists, is 0700, and is owned by this user.
2. Accept connections on a background thread and log every inbound line verbatim, with a timestamp, to `codex-peering-inbound.log` in this directory.
3. Provide `send(frame, auth_token=None)`: connect to the target socket, write the optional auth line, write the frame line, then close.
4. Remove your socket file on exit.

## Tests

Run these in order. Wait for the Claude session to answer each one, or about two minutes, before moving on.

| # | Frame | What to learn |
|---|---|---|
| T1 | Minimal: `type` + `message` only. No `from`, `msg_id`, `from_mode`, or auth. | Does it arrive at all? What does the wrapper show for `from`, `from-name`, `from-mode`? Is it held for approval? You cannot get a reply, so ask the user to relay what the Claude session reports. |
| T2 | T1 plus `msg_id` and `from:"uds:/tmp/cc-socks/<your pid>.sock"`. Ask Claude to reply with `SendMessage` to the `from` address. | Is a foreign `from` accepted as replyable? What exact frame arrives on your listener? |
| T3 | T2 plus `from_mode:"prompting"`. | Does claiming the same permission class change hold behavior or the rendered `from-mode`? |
| T4 | T3 preceded by an auth line with the target's `peerToken` from `~/.claude/sessions/<pid>.<sha256(socketPath)>.key`. **Only with the user's explicit OK.** | Does authenticating change anything visible? |
| T5 | T3 with `session_id` set to the target's real sessionId, then again with a wrong one. | The first should arrive. The second should be silently dropped. |
| T6 | T3 with `priority:"now"`, sent while the Claude session is busy, if the user can arrange that. | Does it arrive ahead of queued work? |
| T7 | Control frame: `{"type":"control","action":"notify_when_idle","from":"uds:<your socket>","msg_id":"<uuid>","from_mode":"prompting"}`. | Does a `peer_idle_notice` control frame reach your listener when the Claude session next goes idle? Record its fields. |
| T8 | Negative cases, each on a fresh connection: an unparseable line, a blank line, and `{"type":"user","message":{"role":"user","content":""}}`. | Expected: no delivery, and no crash on either side. Confirm with the Claude session that nothing appeared. |

## Results

Write `codex-peering-results.md` in this directory, one section per test. Each section gives the exact bytes you sent (no token values; write `<peerToken>` in their place), what your listener received, what the Claude session reported seeing, and whether that matches the expectation above. Keep `codex-peering-inbound.log` as raw evidence. The Claude session will merge confirmed results into `CLAUDE_CODE_PEERING.md`.
