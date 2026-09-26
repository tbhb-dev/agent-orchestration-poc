# Streaming live output from interactive Codex sessions

Tested September 26, 2026, on macOS 26.5.1 arm64, Codex CLI and shared daemon **0.157.1**, tmux **3.7b**.

**Yes: this installation supports observing an existing interactive Codex session as a structured live stream.** Connect to its owning shared app-server over WebSocket, initialize, then `thread/resume` the already-loaded thread. The original terminal UI remains usable. I verified this with independent clients observing a normal Codex TUI, including a client joining during a running command, and then verified it against the conversation conducting this investigation.

For your session manager, I would implement two live adapters: **app-server events for semantic UI rendering**, and **tmux/PTY output for terminal mirroring**. Use saved rollout records as a recovery source, not as a token stream. There are material completeness and attachment caveats below.

All experiments and evidence are in [codex/](codex/). I did **not** run `codex exec`, use its JSON output mode, or substitute SDK-driven jobs for interactive sessions. Test prompts were submitted through real interactive TUIs in a detached tmux session.

## What was actually running

The CLI on PATH was `/Users/tony/.local/bin/codex`, resolving to the standalone package. Its normal interactive mode used a separate, already-running shared daemon:

```text
codex app-server --listen unix:// --managed-daemon
```

`codex app-server daemon version` reported matching CLI, managed package, and running server versions: `0.157.1`. The default control socket was:

```text
~/.codex/app-server-control/app-server-control.sock
```

That path was a symlink into `/private/tmp/codex-daemon-501/`. Discover it through the installed CLI rather than hardcoding the temporary target. Initial socket/process inspection was blocked by this agent's sandbox; the authorized host-side experiments succeeded after escalation. This is a deployment/access boundary, not a failure of the streaming interface.

There were also desktop-app and older CLI processes on the machine. I did not treat those as the same server or attach to their unrelated sessions. A newly launched app-server is not automatically the owner of an existing TUI's live state.

The current conversation and daemon-backed test thread both recorded `originator: codex-tui`, but `source: vscode`. The standalone test recorded `source: cli`. **Do not classify the originating UI from `source` alone.** Both daemon-backed threads advertised `historyMode: paginated` while also writing JSONL rollout files. Capability checks and observed behavior were more useful than either label.

Evidence: [environment](codex/evidence/environment.txt), [runtime metadata](codex/evidence/runtime-summary.json), [this conversation's observation](codex/evidence/own-harness-probe.json).

## Results by approach

| Approach | Tested result | What you get | Main limit |
|---|---|---|---|
| WebSocket to existing daemon + `thread/resume` | Worked with original TUI active | Assistant deltas, command events/output, item and turn lifecycle, status | Version-dependent; control-capable connection; observed stdout omission |
| WebSocket through `codex app-server proxy` | Worked | Same protocol through the byte proxy | Proxy does not translate WebSocket into JSONL |
| `thread/read` without resume | Read worked after history existed | Snapshot; some status notifications | No assistant or command stream in the comparison run |
| `thread/resume` during execution | Worked | History/live-state snapshot plus future events | Already-emitted command bytes were absent from the initial snapshot |
| `tmux pipe-pane` | Worked for interactive TUI | Raw terminal output including redraws | Terminal encoding, not a message API; future bytes only |
| tmux control-mode attachment | Worked concurrently | Timestamped `%output` notifications and pane/control events | Decode tmux framing and feed a terminal emulator |
| `tmux capture-pane` | Worked | Rendered screen/scrollback text | Snapshot; loses transient states and collapsed content |
| Follow rollout JSONL | Worked during a running session | Persisted messages and tool results | Completed messages rather than token deltas; tools buffered until result |
| Shared daemon observing `--no-daemon` TUI | Not discovered in loaded-thread inventory | Terminal capture and rollout still worked | Need the owning server or a terminal/file fallback |

## Structured attachment: procedure and findings

The generated 0.157.1 schema explicitly describes `thread/resume` as rejoining a running thread when the ID is already loaded. This is importantly different from starting a second agent from the same saved history.

The tested sequence was:

```json
{"id":1,"method":"initialize","params":{"clientInfo":{"name":"session_stream_probe","version":"0.1.0"},"capabilities":{"experimentalApi":true}}}
{"method":"initialized","params":{}}
{"id":3,"method":"thread/loaded/list","params":{}}
{"id":4,"method":"thread/read","params":{"threadId":"THREAD_ID","includeTurns":false}}
{"id":5,"method":"thread/resume","params":{"threadId":"THREAD_ID","excludeTurns":true}}
```

Use the existing server's loaded-thread inventory to establish ownership before resuming. Otherwise resume can load an inactive session rather than observe the active execution you intended. The supplied observer enforces this guard. It discovers candidates by working directory, but requires an explicit ID if more than one matches. That ambiguity occurred in this experiment: working directory is not a unique session identifier.

The socket requires the **HTTP Upgrade/WebSocket handshake**. Sending JSONL directly to it closed the connection. Sending JSONL to `codex app-server proxy` timed out. A WebSocket client over a socket pair bridged through the proxy worked. The proxy is a byte transport, not a message-format converter. Local CLI help and the successful proxy capture establish this behavior.

The successful subscription delivered:

- `item/agentMessage/delta`, with `threadId`, `turnId`, `itemId`, and text fragments.
- `item/started` and `item/completed`, including assistant `phase` values `commentary` and `final_answer`.
- `item/commandExecution/outputDelta` and command completion metadata including exit code.
- `turn/started`, `turn/completed`, status and token-usage updates, plus hook notifications in this configured environment.

For the beta prompt, **310 assistant deltas** covered the commentary and final response. Concatenating the final response's deltas exactly reproduced its completed message. Keep items keyed by thread/turn/item; reconcile deltas with completed items rather than appending both as separate transcript messages. The observed `turn/completed` carried `itemsView: summary`, so its item array was not a replacement for the entire turn history.

A concurrent metadata-only reader received status/goal notifications but **no message items, assistant deltas, or command-output deltas**. Successfully reading a thread is not equivalent to subscribing to it.

### Startup and history edge cases

Before the new TUI's first submitted turn, its ID was already listed as loaded, but full `thread/resume` returned `-32600`, `no rollout found for thread id ...`. A full `thread/read` returned `-32601`, `list_turns is not supported yet`. The initial probe incorrectly announced readiness without checking the response; that bug was corrected, and the failed responses remain in the evidence.

After the first completed turn, resume with `excludeTurns: true` succeeded. Later, full resume, full read, `thread/turns/list` with `itemsView: full`, and `thread/items/list` all succeeded. Thus the early errors do not establish that this installation lacks history APIs. Treat initialization, live subscription, and history availability as separate states, and check every RPC result. I did not isolate the underlying startup condition further.

### Late join and reconnection

A fresh client joining gamma mid-command received an active thread and an in-progress turn containing the user message, commentary, and running command. The command's `aggregatedOutput` was `null` in that snapshot even though earlier output had already streamed.

The late client received only the subsequent third stdout line as a delta. The completed command then supplied all three gamma lines, recovering its missing prefix. A proxy-based client connected earlier saw all three live lines, approximately 12 and 8 seconds apart. Multiple observers coexisted with the original TUI.

This establishes fresh-connection history recovery and mid-turn observation; it does **not** establish a lossless replay cursor for disconnected clients. No token-event replay cursor was exercised. A new frontend should distinguish live deltas from recovered completed state and acknowledge a potential gap until it reconciles history.

Evidence: [successful subscription](codex/evidence/resume-attached.jsonl), [read-only comparison](codex/evidence/read-metadata-live.jsonl), [proxy connection](codex/evidence/proxy-reconnect.jsonl), [late join](codex/evidence/late-attach.jsonl), [history probes](codex/evidence/history-probes.json).

## A reproducible stdout completeness problem

Two commands printed their first line immediately and subsequent lines after sleeps:

```python
print("STREAM_BETA_ONE", flush=True)
time.sleep(5)
print("STREAM_BETA_TWO", flush=True)
time.sleep(5)
print("STREAM_BETA_THREE", flush=True)
```

For beta, the observer was attached before the turn began and received the command start. Nevertheless, both its command deltas and the completed command's `aggregatedOutput` contained only `TWO` and `THREE`. The TUI also displayed only those two output lines. Alpha independently showed the analogous omission in its terminal display.

The rollout's completed **Code Mode tool result contained all three lines** in both runs. These commands were invoked through the harness's `functions.exec` / `tools.exec_command` path; persisted tool results and frontend `commandExecution` items were different representations of the execution.

Gamma inserted a two-second delay before its first print. All three lines then appeared in the live command stream, and completion restored all three for the late observer. This is evidence of timing-sensitive loss somewhere in the frontend command-event path; it is **not proof of its internal cause**, nor a claim about every command backend or Codex version.

Do not promise a complete stdout audit trail from command deltas or terminal mirroring on this build. Completion fixes late-observer gaps, but did not repair beta's early-line omission. Preserve a way to reconcile persisted tool results, with backend-aware parsing and clear provenance.

Evidence: [screen capture](codex/evidence/daemon-screen.txt), [selected persisted results](codex/evidence/rollout-excerpts.json), [automated comparisons](codex/evidence/analysis.json).

## Terminal capture: generic, effective, and visually faithful

I created a detached tmux session and ran plain `codex` in its pane. The first capture used:

```sh
tmux pipe-pane -t "$PANE" -o 'cat >> /absolute/path/terminal.raw'
tmux capture-pane -p -S - -t "$PANE"
```

Then a separate client attached with:

```sh
tmux -C attach-session -t codex-stream-lab -f read-only,ignore-size
```

Control mode produced **2,874 `%output` records** in the retained interval. The raw pipe ultimately held **276,437 bytes**, including **32,379 ESC bytes**, for three small test turns plus UI activity. Simply stripping ANSI escapes will not reconstruct a dependable transcript: the TUI moves the cursor, redraws existing cells, wraps at pane width, and collapses tool details.

Use a terminal emulator for a web mirror, or an actual terminal attachment for a TUI mirror. Preserve terminal dimensions and resize events. `ignore-size` prevented the observer from contributing its dimensions to the pane. `read-only` applied to that tmux attachment; it is not a general security boundary around the tmux server socket.

Practical issues observed:

- This server starts window/pane numbering at 1, so an assumed `:0.0` target failed. Discover and retain the pane ID (`%28` for the primary test).
- Sending a long literal prompt and Enter immediately initially left the text in the composer. A 600 ms pause before Enter worked in the subsequent test submissions. Use explicit UI readiness checks in a real controller; this sleep is just a reproduction aid.
- `pipe-pane -o` attaches only if no pipe is already active. Inspect existing capture ownership before using it on a user's pane.
- A late terminal capture needs a screen/history seed. Combining a snapshot with live bytes requires careful synchronization; this experiment did not implement an atomic snapshot-plus-stream handoff.
- Pane capture reflects what the user sees, including truncation/collapsing and the observed missing stdout line. It cannot recover content the TUI never rendered.

The separate `codex --no-daemon` TUI also rendered and persisted a successful response, but was absent from the shared daemon's loaded-thread results. Terminal capture is therefore the useful fallback for independently hosted interactive sessions. For a session outside tmux, a PTY wrapper must normally be established at launch; reading an existing terminal device is not a broadcast tap. A custom PTY wrapper was not implemented here.

Evidence: [raw terminal bytes](codex/evidence/terminal.raw), [control messages](codex/evidence/control-live.jsonl), [standalone screen](codex/evidence/standalone-screen.txt), [standalone discovery](codex/evidence/standalone-discovery.jsonl).

## Rollout following: useful persistence, insufficient live fidelity

The test thread wrote a growing file under `~/.codex/sessions/YYYY/MM/DD/rollout-...jsonl`. A 50 ms polling reader recorded when complete JSONL records became readable. Relevant records included:

- `response_item/message`: user and completed assistant messages.
- `response_item/custom_tool_call` and `custom_tool_call_output`: Code Mode calls/results in these runs.
- `event_msg`: turn lifecycle and item-completion information.
- Additional metadata/context/usage records that should not automatically be displayed or forwarded.

For beta's 150-number final response, the live stream began **9.287 seconds before** the complete assistant message became visible in the rollout. The completed live item preceded file observation by approximately **26 ms**. The latter is within the polling resolution; this is a single-run comparison, not a latency guarantee.

The timed command's saved tool result arrived after execution and contained all stdout lines together. It did not provide the five-second-separated live tool stream. No assistant token-delta records were observed in these rollout files.

For a production follower, buffer partial lines, checkpoint by file identity and byte offset, handle replacement/truncation, and deduplicate different record representations. The supplied timing probe handles partial lines but intentionally does **not** implement rotation recovery, durable checkpoints, or a stable cross-version event model. Avoid selecting the newest rollout by modification time: concurrent threads existed here. Prefer a thread ID and its known path.

Raw rollout files contain much more than a display transcript, including instructions/context and potentially sensitive tool output. A session manager should extract explicitly allowed display records rather than forward the entire file. I retained selected controlled-test records rather than copying this conversation's full rollout.

Evidence: [beta/gamma persistence timings](codex/evidence/rollout-beta-timing.jsonl), [timing analysis](codex/evidence/analysis.json).

## Suggested session-manager design

1. **Discover the owner.** Record harness version, thread ID, server endpoint and, if present, tmux pane ID. Read the running daemon's version separately from the executable on PATH. Treat cwd/source labels as hints.
2. **Subscribe through a local broker.** Initialize, confirm the thread is already loaded in that server, and resume without configuration overrides. Obtain history separately when available. Handle the pre-first-turn error state explicitly.
3. **Normalize display events.** Maintain thread/turn/item identity, assistant phase, delta text, command output and lifecycle. Use completed items for reconciliation, retaining the stdout-completeness caveat. Keep optional/unknown notification types tolerant of version changes.
4. **Offer terminal mirroring independently.** Use tmux control mode or a launch-time PTY. Label it as the terminal view; it is a different product surface from a semantic conversation view.
5. **Recover from durable records.** On reconnect, refresh current state and completed history. Use rollout parsing only as a versioned fallback or richer-result reconciliation source, not an assumed stable API.
6. **Keep the viewer boundary explicit.** The app-server connection has control authority; this probe is observational by convention, not a server-enforced read-only role. Do not expose that socket directly to an untrusted web viewer. Filter thread IDs and allowed operations in your broker, and decide how approval requests are handled before adding control functionality.

I did not exercise approvals/multi-client approval ownership, slow-reader backpressure, daemon crashes/upgrades, remote authentication, image/audio payloads, model reasoning streams, persistent subscription replay, or production fan-out. Those remain acceptance tests, not established capabilities. I also did not test Claude Code or Antigravity; the generic tmux findings are architectural guidance, not verification of those harnesses.

## Reproduction, validation, and cleanup

See [codex/README.md](codex/README.md) for probe commands. Version-specific client request, server request, and notification schemas generated by the installed CLI are retained in [codex/schema/](codex/schema/).

`python3 codex/analyze.py` passed evidence checks for final-text reconstruction, lack of assistant items on the metadata reader, the missing beta stdout line, and full gamma output at completion for the late joiner. All four Python scripts passed syntax compilation.

Both experiment TUIs were exited, and only the newly created `codex-stream-lab` tmux session was removed. The pre-existing daemon and user tmux sessions were left running. Normal Codex session-history and workspace-trust records created by the test remain; the report records the test thread IDs. No shared daemon restart, remote-control enablement, or global configuration edit was performed.

Official documentation cross-check: [Codex App Server](https://learn.chatgpt.com/docs/app-server) documents WebSocket-over-Unix transport, the initialize handshake, resume/read distinctions, deltas, and version-specific schema generation. The measurements and failure cases above come from local experiments. Its WebSocket interface is marked experimental; pin and test supported versions.
