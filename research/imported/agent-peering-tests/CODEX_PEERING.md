# Codex cross-session peering

Findings from live experiments on **2026-09-26**, macOS, against the user-designated recipient `01a0de04-2459-7913-97cf-bd483040cd02`. The sending session was `01a0ddff-0c52-7570-9c0d-036b9f382ecc`.

The practical entry point is:

```sh
codex queue --thread '<session UUID or exact session name>' \
  --message 'Your message'
```

This submits ordinary user input to another Codex thread through an app server. In our tests, a loaded idle recipient started a turn automatically; a loaded busy recipient processed queued messages as separate subsequent turns. A stored thread reported as `notLoaded` accepted a queue entry but did not start it during observation. There is no observed automatic peer identity, return address, or reply delivery to the sending process. An agent can submit a reply by invoking the same command with the original sender's thread UUID, supplied explicitly in the request; the reply still needs to be consumed on the receiving side.

**Evidence labels:** **[observed]** means exercised against the running installation; **[schema]** means exposed in locally generated protocol types or CLI help but not necessarily exercised; **[docs]** means public documentation; **[inference]** means an interpretation rather than a verified implementation guarantee. These findings are version-specific, not a promise about every Codex client or deployment.

## Versions and scope

- Initial sender: `codex-cli 0.156.1`, reached through `~/.local/bin/codex` → `~/.codex/packages/standalone/current/bin/codex`. **[observed]**
- Later in this exploration, the same CLI reported `0.157.1`. We did not issue an update command. The later addressing, queue-management, storage, and steering probes used that version. **[observed]**
- The running managed app server reported `0.157.1`, with managed binary `~/.codex/packages/app-server-daemon/current/bin/codex`. **[observed]**
- The recipient's metadata reported `source: "vscode"`, `cliVersion: "0.157.1"`, `history_mode: "paginated"`, and name `Acknowledge queue probe`. This is the metadata value, not an assertion about which visible application window the user had open. **[observed]**
- Local configuration contained `desktop.followUpQueueMode = "queue"`; we did not change it or compare settings. **[observed]**
- All delivered probes targeted that recipient or the originating session for explicit return-message/storage tests. Negative addressing probes used deliberately nonexistent identifiers. No unrelated thread was messaged, renamed, archived, or stopped.

The [public CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli) had no `codex queue` entry when inspected. The installed CLI help and version-matched schemas were more informative for this feature. Public [app-server documentation](https://learn.chatgpt.com/docs/app-server) describes the surrounding protocol, transports, initialization, history, and steering; the queue-specific behavior below comes primarily from local evidence.

## Architecture and discovery

### Shared app server, with thread-addressed queues

The observed path is:

```text
producer (Codex, Claude, shell, or another program)
    │ codex queue / app-server RPC
    ▼
shared local Codex app server
    │ thread/queue/add
    ▼
queue for recipient thread UUID
    │ when eligible to run in the tested setup
    ▼
user-message turn → agent response in recipient history
```

This does not require a parent/subagent relationship. The two test sessions were separate threads. It also does not require a dedicated peer tool in the sending model: a process able to invoke the CLI or speak the app-server protocol can submit input. Direct protocol submission from a standalone Python process succeeded. **[observed]**

Do not confuse this with the model's `collaboration.send_message`/`followup_task` tools. Those address agents within an existing agent tree; the mechanism explored here addresses an independent thread UUID or exact name through the app server.

### Finding the recipient

- `codex agents` is an interactive browser of sessions on the shared local daemon. Its help describes remote-endpoint options too. **[schema]**
- `thread/list` supports pagination and filters including `cwd`, `searchTerm`, `sourceKinds`, and `archived`. Its `searchTerm` is a substring search, not the CLI's exact-name resolver. **[schema]**
- `thread/loaded/list` lists loaded threads; it is distinct from the stored-history list. **[schema]**
- `thread/read` with `{ "threadId": "…" }` returns metadata and runtime status. We observed `idle` and used it to wait for tests to finish. **[observed]**
- `$CODEX_THREAD_ID` identified the current thread inside both the sending and receiving sessions' shell environments. It is useful as an explicit reply address. Check that it exists rather than assuming every launch path sets it. **[observed]**
- Local `~/.codex/state_5.sqlite` contains a `threads` table with `id`, `name`, `title`, `rollout_path`, `source`, `cwd`, `cli_version`, and `history_mode`, among other fields. We used read-only SQLite queries scoped to the designated UUID. This is an internal storage format, not a stable discovery API. **[observed]**

UUIDs are preferable for automation: names can change or be ambiguous. The installed binary contains an ambiguity error beginning `Multiple sessions match`, but we did not create duplicate names to exercise that case.

### Socket and transport

The default local endpoint observed was:

```text
~/.codex/app-server-control/app-server-control.sock
  → /private/tmp/codex-daemon-501/<hashed socket name>
```

The control directory had mode `0700`; the resolved socket had mode `0600`, owned by UID 501. We successfully connected as that user without supplying an application-level token. **[observed]** This does not establish behavior across users or with remote authentication.

**The Unix socket carries WebSocket traffic, not raw newline-delimited JSON.** Our working client performed an HTTP Upgrade handshake over `AF_UNIX`, then exchanged JSON messages inside WebSocket frames. **[observed]** Public documentation confirms WebSocket-over-Unix transport and distinguishes it from newline-delimited JSON on `codex app-server --stdio`. **[docs]**

`codex app-server proxy` describes itself as proxying stdio bytes to the control socket. Sending bare JSON lines through it produced no initialization response and timed out. Do not assume this command converts JSONL into WebSocket frames. The successful probe connected to the Unix socket with WebSocket framing instead.

Useful inspection commands:

```sh
codex --version
codex queue --help
codex app-server daemon version
codex app-server generate-ts --experimental --out /tmp/codex-protocol
```

The schema generator does not need to start a model turn. Generate from the binary version you intend to use; sender and daemon can differ. Our first schema export used 0.156.1, and we regenerated it after the CLI reported 0.157.1.

## CLI contract and observed addressing behavior

```sh
codex queue --thread 01a0de04-2459-7913-97cf-bd483040cd02 \
  --message 'PROBE: please acknowledge receipt.'

codex queue --thread 'Acknowledge queue probe' \
  --message 'PROBE: please acknowledge receipt.'

codex queue --remote unix:// \
  --thread 01a0de04-2459-7913-97cf-bd483040cd02 \
  --message 'PROBE: explicitly use the default Unix endpoint.'
```

All three addressing forms above succeeded. **[observed]** Name-based examples depend on that name still being current.

Success output has this form and exits with status 0:

```text
Queued message 01a0de04-cdb6-7630-bc8d-c8cf7b72a8a2 for thread 01a0de04-2459-7913-97cf-bd483040cd02.
```

The UUID after `Queued message` identifies the **queued submission**, not the response turn. The command returns after submission and does not return the recipient's answer or wait for task completion. We observed the same behavior while the recipient remained busy. The help exposes no queue-specific `--wait`, JSON-output, sender-address, reply-address, deduplication, or priority switch. **[observed/help]**

| Input | Observed result |
|---|---|
| Full recipient UUID | Accepted and delivered |
| Exact name `Acknowledge queue probe` | Accepted; recipient replied `NAME-ACK` |
| UUID prefix `01a0de04` | Exit 1: `No active session found matching '01a0de04'.` |
| Name prefix `Acknowledge queue pr` | Exit 1 with the same no-match form |
| Nonexistent name | Exit 1 with the no-match form |
| Nonexistent, syntactically valid UUID | Exit 1; `thread/queue/add` failed with `no rollout found for thread id …` and RPC code `-32603` |
| `--message ''` | Exit 2: a value is required for `--message` |
| `--message '   '` | Accepted; created a turn; agent asked what to do next |
| Multiline Unicode text | Newlines, `café → Claude`, quotation marks, and literal `$literal` arrived intact |
| `--remote unix://` | Accepted and delivered |

`--remote` also advertises `unix://PATH`, `ws://host:port`, and `wss://host:port`. `--remote-auth-token-env` names an environment variable containing the remote bearer token. These other endpoints/authentication modes were not tested. **[schema]**

The help includes common options such as model, profile, sandbox, working directory, and image flags. Their appearance is not proof that every option meaningfully changes a queued turn. We did not test configuration overrides or image attachment behavior.

For arbitrary text, pass an argument vector rather than constructing shell source:

```python
import subprocess

result = subprocess.run(
    ["codex", "queue", "--thread", recipient_uuid, "--message", message],
    capture_output=True, text=True, timeout=30,
)
```

A timeout leaves acceptance uncertain; do not blindly resend. Use an application-level probe ID and check history/queue first.

## Delivery timing, identity, and replies

### Idle and busy delivery

The first introduction, `QUEUE-PROBE-01`, started a new turn at `14:00:51.898Z` and finished at `14:00:54.655Z`. The recipient said:

> Received QUEUE-PROBE-01. It arrived as a new turn with no ongoing work. There’s no existing task to resume.

Next we requested a 25-second shell sleep and queued A and B while that turn was active. The transcript establishes this sequence:

| UTC time | Event |
|---|---|
| 14:01:18.329 | Timed task turn started |
| 14:01:21.120 | Agent called `sleep 25` |
| 14:01:46.188 | Sleep completion returned to agent |
| 14:01:47.707 | Timed task completed with `BUSY-02-DONE` |
| 14:01:47.712 | A started as a new turn |
| 14:01:49.460 | A completed with `ACK-A` |
| 14:01:49.463 | B started as another new turn |
| 14:01:51.154 | B completed with `ACK-B` |

The follow-ups did not steer or interrupt the active task and were not combined into one turn. **[observed]** These observations establish FIFO processing in this test, not a universal ordering guarantee under concurrent producers, manual reordering, restarts, or competing clients.

### How messages look to the recipient

The stored input was an ordinary `role: "user"` text message; the app-server history exposed it as a `userMessage`. It did not contain a `<cross-session-message>` wrapper. When specifically asked, the recipient reported no harness-provided sender session ID, return address, or permission-class label. **[observed]**

Thus the sender's introduction and authorization claim are message text, not authenticated peer metadata. There was no observed Claude-style permission-class comparison or held-for-approval peer-delivery notice. We did not test differing recipient permission policies, so this is not a claim that every request will execute without approval. Tool execution continues to have its own sandbox and approval rules.

For a useful application-level envelope, include explicit fields in the text:

```text
Peer request PEER-123
From: <sender thread UUID or descriptive identity>
Reply-to: <explicit reply mechanism/address>
Task: ...
Please include PEER-123 in your response.
```

These fields are conventions, not native routing or verified identity.

### Explicit reply experiment

We asked the recipient to run:

```sh
codex queue --thread 01a0ddff-0c52-7570-9c0d-036b9f382ecc \
  --message 'PEERING-RETURN-05: reply from 01a0de04-2459-7913-97cf-bd483040cd02; test receipt only, no action required.'
```

It succeeded after the recipient's own sandbox rejected the state-database write and its approved retry completed. The originating session was still working, and the reply appeared as pending submission `01a0de0a-c295-7bf2-9cd8-88cbae77d2cc` in its queue. We observed it using `thread/queue/list`, then deleted that exact test submission to avoid an unnecessary extra turn. **[observed]** This verifies reverse submission and pending receipt, not consumption of the reply as a completed model turn. A later status check reported the originating session as `notLoaded` on this daemon: its ongoing work was not evidence that this daemon owned its live execution. Do not attribute the pending reply solely to the sender being busy.

There was no automatic callback to the original shell command. To obtain an answer, either observe the recipient's history/events or request an explicit return message. A Claude sender needs a Claude-specific return transport if it wants the answer delivered into Claude; merely naming Claude in the prompt does not establish that transport.

## Direct app-server API

The working experimental client used a WebSocket connection to the existing daemon's Unix socket. No separate Codex app-server process was launched for these RPC tests.

### Initialization

Send an initialization request, wait for its result, then send the notification:

```json
{"id":1,"method":"initialize","params":{"clientInfo":{"name":"codex_peering_probe","title":"Codex peering probe","version":"0.1"},"capabilities":{"experimentalApi":true}}}
{"method":"initialized","params":{}}
```

Messages use request IDs and `result`/`error` responses; the `jsonrpc` header is omitted. On WebSocket transports each JSON message is a WebSocket message. **[docs/observed]**

The observed initialization result included `userAgent`, `codexHome`, `platformFamily`, and `platformOs`. Without `experimentalApi: true`, both tested queue methods (`thread/queue/add` and `thread/queue/list`) failed with code `-32600` and `… requires experimentalApi capability`. **[observed]** Use experimental opt-in for the queue API; do not assume other methods are ungated simply because they were not individually tested without it.

### Add and inspect queued input

```json
{"id":2,"method":"thread/queue/add","params":{"threadId":"<recipient UUID>","input":[{"type":"text","text":"PEER-123: hello","text_elements":[]}],"clientUserMessageId":"<caller-generated UUID>"}}
```

Response shape:

```json
{"id":2,"result":{"queuedSubmission":{"id":"<queue UUID>","input":[{"type":"text","text":"PEER-123: hello","text_elements":[]}],"clientUserMessageId":"<caller-generated UUID>"}}}
```

Queue API methods from the 0.157.1 generated types:

| Method | Parameters beyond `threadId` | Result | Live verification |
|---|---|---|---|
| `thread/queue/add` | `input`, `clientUserMessageId` | `queuedSubmission` | Added and delivered input |
| `thread/queue/list` | optional `cursor`, `limit` | `data`, `nextCursor` | Listed, reconnected, paginated |
| `thread/queue/update` | `queuedSubmissionId`, replacement `input` | `queuedSubmission` | Edited B before delivery |
| `thread/queue/delete` | `queuedSubmissionId` | `deleted` boolean | First delete true; second false |
| `thread/queue/reorder` | `queuedSubmissionIds` | empty object | Moved edited B ahead of other pending probes |
| `thread/queue/start` | optional `queuedSubmissionId` | `turn` | Busy/empty/unloaded errors tested; successful manual start not tested |

`QueuedSubmission` contains `id`, `input`, and `clientUserMessageId`. The protocol's `UserInput` union also supports image, local image, audio, local audio, skill, and mention variants. Only text was exercised here. **[schema]**

### Mutation, ordering, and retry details

- Updating B changed the delivered text and the answer to `MGMT-B-EDITED`. Its queue ID and client message ID remained the same. **[observed]**
- Reordering requires **every currently queued submission exactly once**. Omitting one produced `-32600: queue reorder must include every queued submission exactly once`. Account for changes between list and reorder; do not overwrite another producer's work. **[observed]**
- Deleting a pending probe prevented that probe from becoming a user turn. Deleting its ID again returned `{ "deleted": false }`. This does not establish cancellation of an already running turn. **[observed]**
- Calling `thread/queue/start` while work was active/pending returned `-32600: thread already has an active or pending turn`. With an empty idle queue it returned `-32600: queue is empty`. **[observed]**
- Two adds with the **same `clientUserMessageId`** and different text produced different queue UUIDs. Both eventually ran: `MGMT-A`, then `MGMT-DUPLICATE`. Treat that field as correlation data, not an idempotency key. Identical-text retries were not separately tested. **[observed]**
- The management batch began while a whitespace-only turn was active, before its requested 35-second task started. Our reorder moved B ahead of that pending timed task as well as A. The original 25-second experiment independently establishes queuing during an executing shell tool; do not use the management batch's timing to claim the sleep itself was interrupted.

### Notifications and answer correlation

After `thread/resume` with `{ "threadId": "…", "excludeTurns": true }`, our client received the recipient's events. Resuming this already loaded thread rejoined it; it did not start another model turn. **[observed]** The generated resume type documents rejoining a running thread and the difference from loading history. **[schema]**

Observed notifications included:

```text
thread/queue/changed
thread/status/changed
turn/started
turn/completed
item/started
item/completed
item/agentMessage/delta
```

A queue-change notification had this shape:

```json
{"method":"thread/queue/changed","params":{"threadId":"<thread UUID>"},"emittedAtMs":1790431515561}
```

It is an invalidation signal: it does not contain the queued item or a delivery receipt. Re-read the queue when necessary. A disappearance from the pending queue alone cannot distinguish consumption from deletion.

For history-based verification we successfully called:

```json
{"id":3,"method":"thread/turns/list","params":{"threadId":"<thread UUID>","limit":10,"itemsView":"full"}}
```

This returned turns, their statuses, user messages, command executions, and agent messages. Responses had pagination cursors; continue paging if the desired probe is not on the first page. `thread/items/list` offers item pagination in the schema but was not separately exercised.

There are several different IDs:

1. RPC request `id`: matches a protocol response to a call.
2. `queuedSubmission.id`: identifies the pending entry for update/delete/reorder.
3. `clientUserMessageId`: caller correlation value; appears as `userMessage.clientId` in observed turn history.
4. Turn `id`: identifies execution and is used by steering/interrupt APIs.
5. Individual message/item IDs: identify transcript items.

The CLI prints item 2, but does not print item 3. An API producer can retain both from the add response. A CLI producer should include a unique textual probe ID and correlate through queue/history; after the item has already been consumed, its printed queue UUID is not itself a turn UUID. Do not correlate solely by client ID if your application reuses it.

## On-disk persistence

The installation had a separate `~/.codex/queue_1.sqlite`, with WAL/SHM sidecars. Its observed schema included:

```sql
CREATE TABLE queued_items (
    id TEXT PRIMARY KEY NOT NULL,
    thread_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    queue_order INTEGER NOT NULL,
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);
CREATE TABLE queued_thread_revisions (
    revision INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL UNIQUE
);
```

Two removable probes queued to the originating session appeared immediately in `queued_items` with orders 0 and 1. A payload looked like:

```json
{"UserInput":{"content":[{"type":"text","text":"STORAGE-06-X: receipt-only experiment; no action required.","text_elements":[]}],"client_id":"9614a8df-9508-4c2a-8766-8ca7ddef8bae"}}
```

We disconnected the producer, opened a new connection, and fetched the same two entries with `limit: 1`. The first `nextCursor` happened to be `"1"`, and the second was null. Treat cursors as opaque despite that simple observed value. Both probes were then deleted through the API. **[observed]**

This establishes on-disk storage and survival of **producer connection closure**. It does not establish recovery after daemon crash, restart, a loaded recipient becoming unloaded, or machine reboot. We did not stop the shared daemon to test those cases. Do not write directly to these databases; their table names and payload representation are internal implementation details.

The recipient's local rollout was:

```text
~/.codex/sessions/2026/09/26/rollout-2026-09-26T10-00-08-01a0de04-2459-7913-97cf-bd483040cd02.jsonl
```

We used it to cross-check early `task_started`/`task_complete` events and exact input text. Because the session is marked paginated and the installation also has `thread_history_1.sqlite`, do not assume a single JSONL file is a complete history interface forever. Prefer the tested history RPC for consumers.

### Stored but not loaded: acceptance is not wake-up

The originating session was actively running this exploration, yet `thread/read` on the shared daemon returned `{ "type": "notLoaded" }` for its UUID. We therefore ran a final, removable probe against that UUID without resuming it:

1. Read status: `notLoaded`.
2. Call `thread/queue/add`: accepted, returning queue ID `01a0de12-8676-72d2-9c9d-c5fa0d61b227`.
3. After four seconds: status still `notLoaded`, and the exact entry was still pending.
4. Call `thread/queue/start` for that entry: `-32600: resume the thread before starting a queued message`.
5. Delete that entry: `{ "deleted": true }`.

**[observed]** Thus a known UUID can accept queued input even though it is not loaded on the addressed server. The process currently running a conversation and the server storing its queue are not necessarily the same runtime. We did not resume the originating thread on another server, which could create competing execution. How the original runtime discovers such pending input, or how a later resume drains it, remains untested. Treat `--remote`/server selection and thread runtime status as part of addressing, not just the UUID.

## Queue versus active-turn steering

`codex queue` did not interrupt active work. For guidance intended for the current turn, the app-server exposes `turn/steer`:

```json
{"id":4,"method":"turn/steer","params":{"threadId":"<recipient UUID>","expectedTurnId":"<active turn UUID>","input":[{"type":"text","text":"Please include STEER-RECEIVED in this turn's answer.","text_elements":[]}]}}
```

We started a turn containing a 12-second sleep, then sent a steering message while it was active. **[observed]**

- A deliberately wrong `expectedTurnId` returned `-32600`, reporting the expected and actual active IDs.
- The correct ID returned `{ "turnId": "01a0de0b-8e5b-7cb2-8dc7-764f5a7a0dc6" }`.
- The original input and steering input appeared in that **same turn**.
- The sleep completed, and the final answer was `STEER-BASE` followed by `STEER-RECEIVED`.

This distinguishes steering from queuing. It does not establish that steering cancels tools or is consumed at every possible instant during a blocking operation. No CLI `queue` priority flag was found; use the appropriate API rather than treating queue and steer as interchangeable.

The generated 0.157.1 `TurnSteerParams` requires `threadId`, `expectedTurnId`, and `input`; it also exposes optional `clientUserMessageId`, `responsesapiClientMetadata`, and `additionalContext`. The response contains only `turnId`. **[schema]** A successful RPC response acknowledges the steering request; inspect subsequent items and turn completion to establish that the model used the input. The caller must obtain the actual active turn ID rather than substituting a thread ID or queued-submission ID.

The companion [session-management study](../agent-session-tests/CODEX_SESSION_MANAGEMENT.md) verified metadata/history inspection from a second client without resuming the thread. Its steering/interrupt operations were schema findings and proposed future tests, not executed controls. The live steering experiment above supplies evidence that study did not yet have; it does not settle all of its multi-client control questions.

A later attempt to extend the steering tests checked recipient state before submitting any input. The original recipient returned `notLoaded` with one existing pending message, so the probe stopped without resuming it, starting a turn, steering it, or changing that queue entry. That pending message must not be mistaken for a probe created by the new test. Tony subsequently authorized creating a fresh interactive recipient in tmux, as described below.

### Interactive tmux follow-up: verified negatives and timing-probe limits

On the existing tmux server we created session `codex-steering-757a243a`, pane `%33`, and launched an interactive Codex 0.157.1 client connected with `--remote unix://`. The new thread is `01a0de45-529c-78f1-89a5-76d437dc1671`. It started in a newly created scratch directory with `--sandbox read-only --ask-for-approval on-request`; the empty scratch folder's trust prompt was accepted. No model override was supplied; the UI reported GPT-6-Astra.

The initial prompt produced `STEERING-RECIPIENT-READY`. The test controller confirmed that the thread was loaded and idle and that its pending queue was empty. **[observed]**

From a separately initialized client with `experimentalApi: false`, which had not called `thread/resume`, two negative requests returned:

| Request | Observed response |
|---|---|
| `turn/steer` against an idle thread, with a previous turn's ID | `-32600: no active turn to steer` |
| `turn/steer` omitting `expectedTurnId` | ``-32600: Invalid request: missing field `expectedTurnId` `` |

These establish validation behavior, not successful steering from an unsubscribed client or the absence of every possible capability gate on a valid request.

The planned busy comparison was to start a 20-second command, establish that it was running, then add one queued follow-up and send steering inputs A/B from the separate client. **The timing precondition failed before any of those three follow-ups were submitted.** We stopped after three attempts under the project's bounded-verification rule:

1. **History-only observation:** repeated `thread/turns/list` reads did not expose an `inProgress` command item during the observation window. A tmux capture did show the command running. The probe exited with `No active tool observed; cannot establish busy timing`.
2. **Subscribed observer plus history polling:** the observer rejoined the loaded thread, but the probe treated an immediate history snapshot as a completed turn and exited. This version did not require the snapshot's turn ID to match the new turn before its completion check.
3. **Exact-turn matching plus event-assisted observation:** after correcting that guard, the probe still exited with `Turn completed before command observation`. A subsequent independent read reported the same new turn as `inProgress`, and tmux displayed its running command. The exact abort-triggering snapshot was not retained, so the underlying cause is unresolved; this is not evidence that the command had actually completed or that steering was rejected.

Final history showed that all three commands completed normally, each with `STEER-TOOL-FINISHED`, exit code 0, and final answer `STEER-EXT-BASE`. There were no model-turn errors. The blocker was the diagnostic client's running-tool observation and history reconciliation, not an observed failure of `turn/steer` to accept active-turn input. The earlier successful 12-second steering test remains valid.

Scoped evidence, including accepted turn IDs, RPC errors, and final command/turn history, is retained in [probes/codex-steering-20260926.json](probes/codex-steering-20260926.json). The next probe should retain every triggering snapshot and raw event, use live command-start events as the timing authority, and avoid interpreting an immediately read history summary as a definitive execution-state transition.

The tmux session was left available, with Codex idle and zero pending inputs at the final check. To inspect it from a terminal:

```sh
tmux attach-session -t codex-steering-757a243a
```

Still unverified by this follow-up: successful steering from a client that never resumes the thread, two steering inputs within one confirmed tool-running interval, their ordering relative to queued input, and a separate late-steer test immediately after completion. No interruption or cancellation test was performed.

## Sandboxing, permissions, and failures

The first CLI send from the sender's workspace sandbox failed before acceptance:

```text
failed to initialize state database
... /Users/tony/.codex/state_5.sqlite ...
(code: 8) attempt to write a readonly database
```

Retrying the user-authorized action with approved access outside that restriction succeeded. Direct Unix-socket access also required permission outside the sender's sandbox; a diagnostic command received `Operation not permitted`. **[observed]**

The CLI is not a read-only operation merely because the message asks the recipient only to acknowledge. It initializes local state and causes queue/history writes. Socket accessibility, local state access, target availability, queue acceptance, model execution, and completion are separate stages.

One earlier daemon-version check reported a missing default control socket; later checks found it and connected successfully with the necessary access. We did not establish whether the initial absence was startup timing or another environmental difference. Do not infer that the queue command itself always creates or starts the daemon from this sequence.

The binary contains a diagnostic for a server that does not support `thread/queue/add`, advising update/restart. **[binary string, not exercised]** Inspect versions before diagnosing a protocol mismatch, and do not restart a shared server casually: it may host other work.

Local credential-free connection was observed only under the same operating-system user and these socket permissions. Remote WebSocket authentication, cross-user isolation, recipient approval changes, and cross-machine routing were not tested. The message's ordinary user-role presentation is significant for integrations: neither a claimed `From:` nor a claim of user approval becomes verified merely by appearing in queued text.

## Comparison with Claude Code peering

See [CLAUDE_CODE_PEERING.md](CLAUDE_CODE_PEERING.md) for that implementation's separate evidence and limitations.

| Concern | Codex in these tests | Claude notes in this repository |
|---|---|---|
| Address | Thread UUID or exact name | Registry name or inbox socket; unique prefix observed |
| Local transport | Shared app-server WebSocket over Unix socket | Per-session Unix socket with JSON lines |
| Busy recipient | Separate subsequent turns with queue | Peer input injected during work at tool boundaries |
| Active-turn guidance | Separate `turn/steer` API, verified | Peer-message timing/priority mechanisms |
| Model-visible attribution | Ordinary user text; no peer wrapper observed | Cross-session wrapper with sender information |
| Return delivery | Explicit reverse queue call or observe history | Reply address/control-frame mechanisms |
| Pending-item management | List/update/delete/reorder API, persisted SQLite entries | Different protocol; do not assume API parity |

## Remaining boundaries and suggested next experiments

The tests above establish a useful local peering mechanism, but leave these questions open:

- Consumption after a stored `notLoaded` thread is resumed, delivery to an archived thread, and coordination with a thread executing under another runtime. Acceptance without loading was observed; eventual delivery was not.
- Whether automatic draining continues with every recipient UI/client disconnected; the designated recipient remained available throughout.
- Daemon restart/crash persistence and recovery semantics, including an already claimed/running item.
- Duplicate exact session names and changes of name during resolution.
- Cross-directory name resolution and cross-`CODEX_HOME` behavior.
- Concurrent producers, queue capacity, rate/size limits, and exactly identical retries.
- Successful manual `thread/queue/start`, and races between start, edit, deletion, and automatic consumption.
- Images, audio, skills/mentions, and queue CLI configuration overrides.
- Remote TCP/WebSocket authentication and cross-machine operation.
- Behavior under different follow-up settings, approval policies, interrupted turns, and failed model turns.

These were left untested rather than closing the recipient's UI, restarting shared infrastructure, or modifying unrelated sessions. [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md) provides a scoped Claude-to-Codex test plan; [CODEX_HANDOFF.md](CODEX_HANDOFF.md) covers the opposite transport direction.
