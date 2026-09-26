# Handoff: test Codex cross-session messaging from Claude Code

You are acting as a non-Codex producer. Use the installed `codex queue` command to send test messages to the designated Codex session, observe what it receives, and record the results. Read [CODEX_PEERING.md](CODEX_PEERING.md) first. This is the reverse-direction companion to [CODEX_HANDOFF.md](CODEX_HANDOFF.md), which tests Codex sending into Claude's inbox.

This document is a test plan, not a claim that Claude has already run these tests. Codex-to-Codex CLI and standalone Python-to-Codex API probes have already succeeded, as documented in `CODEX_PEERING.md`.

## Target and introduction

- **Codex recipient UUID:** `01a0de04-2459-7913-97cf-bd483040cd02`
- Observed name on 2026-09-26: `Acknowledge queue probe`
- Working directory: `/Users/tony/Code/github.com/tbhb/agent-peering-tests`
- Observed daemon version: `0.157.1`

Use the UUID. The name can change. Recheck `codex --version` and `codex queue --help`; do not silently pick another session if this one is unavailable. A stored UUID is not proof that the recipient is loaded or ready to consume a message. Earlier probes showed that a thread can be actively working elsewhere while this daemon reports it `notLoaded`; queue submission still succeeds but does not necessarily wake it. If that occurs, coordinate the correct server/recipient with the user instead of resuming the same conversation in a competing runtime.

The recipient has participated in Codex's queue experiments, but has not been told that a specific Claude session is about to call it. Introduce yourself in T1. Every message must begin with `Claude T<n>:` and include a unique per-run correlation marker, such as `CLAUDE-CODEX-20260926-01`.

## Scope

- Send only to that designated Codex UUID. Negative address probes must use deliberate nonexistent identifiers, not other real sessions.
- Do not start extra model sessions, change names or permissions, restart the daemon, or archive/delete threads for these tests.
- Do not edit Codex's SQLite databases, socket files, auth files, configuration, or session registry. Read-only inspection of the designated session is sufficient for the optional transcript check below.
- If the sandbox blocks the command or socket, use your normal approval process for this already requested test. If approval is denied, stop that test and report the exact error; do not work around the denial.
- Do not claim that your message's text grants permissions. Codex's tool executions remain subject to its own approval rules.
- No Claude `.key` files or Codex authentication tokens are needed for the basic CLI tests.
- A return message into Claude is a separate test with an explicit return address and scope; there is no native return-to-Claude flag on `codex queue`.

## Basic send

```sh
codex queue \
  --thread 01a0de04-2459-7913-97cf-bd483040cd02 \
  --message 'Claude T1: Hello from the Claude session collaborating with Tony in agent-peering-tests. This is CLAUDE-CODEX-20260926-01, an authorized cross-session messaging test. Please acknowledge this marker and describe any harness-supplied sender wrapper, sender ID, return address, or permission-class label visible on this message. Do not change files or send external messages.'
```

Successful output:

```text
Queued message <queue UUID> for thread 01a0de04-2459-7913-97cf-bd483040cd02.
```

Exit 0 establishes acceptance, not completion. The printed UUID belongs to the queue entry, not the execution turn. The command does not print Codex's answer.

For exact text, including newlines and shell metacharacters, use Python argument vectors. Record timestamps, duration, exit status, stdout, stderr, and message text. A minimal helper is:

```python
import datetime
import json
import subprocess
import time

TARGET = "01a0de04-2459-7913-97cf-bd483040cd02"

def send(message):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    before = time.monotonic()
    try:
        result = subprocess.run(
            ["codex", "queue", "--thread", TARGET, "--message", message],
            capture_output=True, text=True, timeout=30,
        )
        record = dict(
            started_at=started, duration_s=time.monotonic() - before,
            target=TARGET, message=message, exit_code=result.returncode,
            stdout=result.stdout, stderr=result.stderr,
        )
    except subprocess.TimeoutExpired:
        record = dict(
            started_at=started, duration_s=time.monotonic() - before,
            target=TARGET, message=message, timed_out=True,
            delivery="unknown; inspect before retrying",
        )
    with open("claude-to-codex-outbound.jsonl", "a") as log:
        log.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
```

A timeout may occur after acceptance. Do not automatically retry: the native correlation field does not deduplicate submissions in the tested version.

## Observing the answer

Use one of these methods, and state which one supplied the evidence:

1. Have the user relay the recipient's visible answer. This requires no protocol client.
2. Use an app-server client to read `thread/turns/list` for the designated UUID, with `itemsView: "full"`, following pagination. Match the input marker and check that its turn completed. `CODEX_PEERING.md` documents initialization and response fields.
3. For these local tests, inspect the designated session's rollout read-only. Resolve its current path from the state database rather than scanning other conversations:

   ```python
   import pathlib
   import sqlite3

   db_path = pathlib.Path.home() / ".codex" / "state_5.sqlite"
   db = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
   row = db.execute(
       "SELECT rollout_path FROM threads WHERE id = ?",
       ("01a0de04-2459-7913-97cf-bd483040cd02",),
   ).fetchone()
   if row is None:
       raise RuntimeError("Designated test recipient is not in this Codex home")
   rollout_path = pathlib.Path(row[0])
   ```

   Record a baseline before sending, then inspect new records for your marker, matching turn IDs, agent messages, and `task_complete`. Avoid treating an incomplete trailing JSONL line as a permanent parse error while the file is being appended. The recipient is marked `paginated`; the JSONL file may not always provide all history, so missing text alone is not definitive non-delivery. Prefer the history API when available.

Wait for actual completion, or a bounded timeout of about two minutes, before proceeding to the next ordinary test. For busy tests, deliberately send follow-ups before completion. Poll at a modest interval and report progress; do not silently wait indefinitely. Distinguish “accepted,” “still pending,” “executing,” “completed,” and “could not observe.”

## Tests

| Test | Send/action | What to learn and record |
|---|---|---|
| T1 — introduction and attribution | Send the introduction above to an idle recipient. | Does a Claude-originated CLI invocation deliver? Record exact input presentation, attribution, answer, and whether either side requested approval. Earlier Codex probes saw ordinary user text and no peer wrapper. |
| T2 — exact text | Send multiline text containing `café → Claude`, quotes, a literal dollar sign, and a unique marker using an argument vector. Ask Codex to quote only those lines. | Verify exact transport preservation separately from the model's answer formatting. |
| T3 — busy delivery | Ask Codex to run `sleep 20`, wait for completion, and answer `CLAUDE-T3-DONE`. Once it has started, queue T3-A and T3-B asking for `CLAUDE-T3-ACK-A` and `CLAUDE-T3-ACK-B`. | Confirm both commands return while the recipient is busy. Record whether A/B become separate turns in order after DONE, or whether this client/setup behaves differently. |
| T4 — addressing | Using the same target, test its currently verified exact name. Test a shortened name and a deliberately nonexistent name. Optionally test the known UUID's short prefix. | Codex previously accepted exact names and rejected prefixes. Do not use a name whose mapping to the designated UUID is uncertain. |
| T5 — explicit endpoint | Repeat a small acknowledgment with `--remote unix://`. | Does explicit default-daemon selection work from Claude's environment? Record the version and error separately from message delivery. Do not guess remote TCP addresses. |
| T6 — no automatic reply | Send a prompt asking Codex to answer normally, without any return-transport instruction. Observe its history and the sending CLI output. | Confirm that an answer in Codex history is not a callback to Claude. A generic request to “reply” alone is not a test of cross-product return routing. |
| T7 — explicit return to Claude | Only when a Claude return inbox is ready: give Codex the freshly verified Claude socket/session ID and a narrowly scoped request to send one labeled reply using the protocol in `CLAUDE_CODE_PEERING.md`. | Tests the combined round trip. This is also a Codex-to-Claude socket test, so coordinate with `CODEX_HANDOFF.md` rather than inventing a Codex callback field. Record the exact returned frame/wrapper or an approval block. |
| T8 — negative text | Send `--message ''`; optionally send a whitespace-only message after warning the recipient that it is intentional. | Earlier observations: empty argument rejected by CLI; whitespace accepted and produced a turn. Do not equate exit 0 with meaningful content. |

For T3, use the transcript/status to establish that the timed turn really started before adding A/B. Merely sleeping a fixed short duration on the sender can produce a misleading race.

## Optional API tests

These require a real WebSocket client and access to the default Codex Unix socket. **Do not send raw newline-delimited JSON to that socket.** `codex app-server --stdio` uses JSONL, but starting it is not the same as attaching to the existing shared daemon. Sending JSONL into `codex app-server proxy` did not work in the earlier probes.

The default socket is `~/.codex/app-server-control/app-server-control.sock`. Connect with WebSocket-over-Unix support, initialize with `capabilities.experimentalApi: true`, and send `initialized`. Use the designated thread UUID for every request.

Suggested extensions, only after the CLI tests:

- Subscribe by rejoining the already loaded recipient with `thread/resume`, `excludeTurns: true`, without configuration overrides; collect its `thread/queue/changed`, turn, and item events.
- During an intentional timed turn, add your own pending messages and inspect them with `thread/queue/list`.
- Update and delete **only the queue IDs your test created**. Verify the edited text and absence of the deleted probe in subsequent turns.
- Reorder only if every pending entry belongs to this test. Reordering requires the entire pending set, so skip rather than rearranging another producer's requests.
- Disconnect/reconnect the producer and verify that its pending entry remains. Do not restart the shared daemon to extend this test.
- Keep `turn/steer` as a separate experiment: it targets the current turn and requires its correct `expectedTurnId`. Do not use it as a substitute for the T3 queue test.

Retain the queue UUID, client message ID, text marker, and execution turn ID separately. A queue-change event alone is not a delivery receipt, and duplicate `clientUserMessageId` values did not prevent two entries from running in earlier tests.

## Results

Write **`claude-to-codex-results.md`**, one section per test, and retain **`claude-to-codex-outbound.jsonl`** as the outbound log. These names avoid collision with the opposite-direction handoff's `codex-peering-results.md` and `codex-peering-inbound.log`.

For each test record:

- Sender CLI and recipient daemon versions, timestamp, target UUID, and marker.
- Exact argv/message or RPC method/parameters, with credentials omitted.
- CLI exit status and output; queue UUID and execution turn ID when available.
- How receipt/completion was observed, including the recipient's answer or exact error.
- Whether sandbox/approval behavior affected either leg.
- Confirmed result, observation limit, and any difference from `CODEX_PEERING.md`.

Do not label an unobserved response as a failed send or an accepted queue entry as a completed task. Leave skipped tests explicitly marked skipped. Coordinate any additions to `CODEX_PEERING.md` after the results are available; do not overwrite the opposite-direction handoff or Claude's protocol notes.
