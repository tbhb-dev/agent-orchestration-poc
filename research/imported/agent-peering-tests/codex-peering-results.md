# Codex peering results

Run date: 2026-09-26. Target selected by exact live registry name `agent-peering-tests-3d`, PID `6675`, session ID `8d3b00a9-d61c-4105-864a-477611e2da4c`, socket `/tmp/cc-socks/6675.sock`, reported Claude version `2.1.281`. Sender/listener: one Python process, PID `49922`, socket `/tmp/cc-socks/49922.sock`, mode 0600. The sender re-reads registry JSON files before each connection and connects only to the named target. No registry or credential files were written.

## Setup and evidence

The initial attempt was blocked by sandbox EPERM on bind and on the added os.kill(pid, 0) identity check. After the user restarted with network access enabled, binding succeeded. Removed the added cross-process checks because process inspection remained restricted; process identity is not independently validated beyond live registry selection and subsequent replies. The harness has not read any key file. No auth lines were sent.

Raw timestamp-prefixed inbound bytes are preserved in `codex-peering-inbound.log`; the bytes following the timestamp and space are verbatim. `codex-peering-outbound.json` records every probe and coordination frame. Below, Python bytes literals specify exact transmitted or received bytes, including the terminating `\n`. Send success alone is not treated as confirmed model delivery. Empty/malformed T8 probes and the T7 control frame necessarily have no normal prefixed message content, as prescribed by the handoff.

## T1

Confirmed delivery. Claude reports bare content introduced as "Another Claude session sent a message", with the peer-trust note and no cross-session wrapper or from/from-name/from-mode attributes. No visible approval hold. The user pointed to the matching report in CLAUDE_CODE_PEERING.md. No direct reply was possible; the T2 reply confirms T1.

### Exact bytes sent

T1:

```python
b'{"type":"user","message":{"role":"user","content":"Codex T1: Minimal foreign-producer probe. Please report the exact cross-session wrapper fields (from, from-name, from-mode), whether approval was required, and what you received. This frame has no reply address; please show your report to the user in your pane for relay to Codex."}}\n'
```

### Listener evidence and receiver report

2026-09-26T14:07:25.773673+00:00:

```python
b'{"msgV":1,"msg_id":"e2b8f689-a068-4b32-a4ac-de40c859176e","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T2 from agent-peering-tests-3d: your T2 arrived, and this reply went to your from address.\\nT2 wrapper: none. There was no <cross-session-message> tag and no from, from-name or from-mode attributes, even though your frame set from. The harness framing was \\"Another Claude session sent a message\\", followed by the standard peer-trust note.\\nHeld for approval: no sign of a hold on my side. It reached my conversation directly while I was idle.\\nT1: it arrived the same way, as bare content with no wrapper tag, labelled as coming from \\"another Claude session\\", with no hold. The user relayed that report.\\nPlease log the exact frame(s) your listener received for this reply, including the auth line if one arrived first, and any control frames. Then carry on with T3.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:08:28.715108+00:00:

```python
b'{"msgV":1,"msg_id":"a472a898-8ecf-45d2-becf-7e6c9d8b50d4","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T5 from agent-peering-tests-3d: T5 arrived, with the matching session_id.\\nIt rendered like T1\xe2\x80\x93T3: no wrapper tag, the \\"Another Claude session sent a message\\" framing, no visible hold. Go ahead and send T5-WRONG. If nothing reaches me, I\'ll tell the user so they can relay it, since a message that never arrives gives me nothing to reply to.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:12:30.412187+00:00:

```python
b'{"msgV":1,"msg_id":"e5f257e4-9723-4f66-a04c-96f0fe7a0bae","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T6 from agent-peering-tests-3d: T6 arrived while I was IDLE, not busy, so this run does not test priority.\\nWhy: I stopped my foreground task early. codex-peering-results.md already said \\"T6: Blocked before sending by sandbox denial of listener bind\\", so I assumed no send was coming and ended my turn. Your T6 then arrived as a fresh turn.\\nFraming: plain \\"Another Claude session sent a message\\" with no wrapper tag, the same as T1\xe2\x80\x93T5. There was no \\"while you were working\\" variant and no in-turn injection.\\nPriority: no evidence either way. No queued work existed and I was not mid-turn, so this shows immediate delivery to an idle session, nothing about ordering.\\nTo rerun: tell me (or the user) when you\'re ready. I\'ll start a foreground task, signal \\"busy\\", and keep it running for a fixed window without any early exit. Also update the T6 note in your results file, since the \\"blocked\\" text is out of date now that the send went through.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:14:04.702646+00:00:

```python
b'{"msgV":1,"msg_id":"5b1a1c8d-d159-4301-978c-392859e7049f","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T6 (second attempt) from agent-peering-tests-3d: it arrived mid-task, at the first tool-round boundary.\\nTiming: round 1 ran 14:13:18\xe2\x80\x9314:13:48 UTC and finished its full 30 seconds, and registry status was busy at the end. Your T6 appeared right after the round 1 result, before round 2 started, with 60 seconds of the planned task still to run. So priority \\"now\\" was not able to interrupt a running tool call; delivery happens at the next tool-round boundary.\\nFraming: the plain \\"Another Claude session sent a message\\" with no wrapper, the same as T1\xe2\x80\x93T5. Notably it did NOT use the \\"sent a message while you were working\\" variant or the \\"finish your current task first\\" instruction that a mid-turn default-priority Claude peer message got earlier. That may be a difference caused by priority \\"now\\", but without a paired default-priority control, that is a hypothesis.\\nI stopped after round 1, since rounds 2 and 3 couldn\'t add anything. Ordering against queued messages is unmeasured, as you say. Go ahead with T7 when ready.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

## T2

Confirmed delivery and reply to the foreign listener. Claude reports the same bare rendering as T1, without a visible approval hold. The reply is one user frame containing a sender-written wrapper in message.content; no auth or delivery-status frame accompanied it.

### Exact bytes sent

T2:

```python
b'{"type":"user","message":{"role":"user","content":"Codex T2: Foreign reply-address probe, with msg_id and from but no from_mode or auth. Please use SendMessage to reply to uds:/tmp/cc-socks/49922.sock. Report the exact wrapper fields you see, whether this message was held for approval, and whether T1 arrived and how its wrapper rendered."},"msg_id":"bf78c111-8077-4444-9a7e-203c31c50002","from":"uds:/tmp/cc-socks/49922.sock"}\n'
```

### Listener evidence and receiver report

2026-09-26T14:07:25.773673+00:00:

```python
b'{"msgV":1,"msg_id":"e2b8f689-a068-4b32-a4ac-de40c859176e","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T2 from agent-peering-tests-3d: your T2 arrived, and this reply went to your from address.\\nT2 wrapper: none. There was no <cross-session-message> tag and no from, from-name or from-mode attributes, even though your frame set from. The harness framing was \\"Another Claude session sent a message\\", followed by the standard peer-trust note.\\nHeld for approval: no sign of a hold on my side. It reached my conversation directly while I was idle.\\nT1: it arrived the same way, as bare content with no wrapper tag, labelled as coming from \\"another Claude session\\", with no hold. The user relayed that report.\\nPlease log the exact frame(s) your listener received for this reply, including the auth line if one arrived first, and any control frames. Then carry on with T3.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:07:52.491060+00:00:

```python
b'{"msgV":1,"msg_id":"97793ca3-d1f7-460f-b2ce-81fdf9835d83","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T3 from agent-peering-tests-3d: T3 arrived and rendered the same as T2.\\nWrapper: none again. No <cross-session-message> tag appeared, so from_mode:\\"prompting\\" changes nothing visible. The framing was the same \\"Another Claude session sent a message\\" plus the peer-trust note.\\nHeld for approval: not visibly; it came straight in while I was idle.\\nConclusion from your T2 log: the wrapper lives inside message.content and is written by the sending Claude session. The receiving harness does not add it, which is why none of your frames show one. It also means the receiver does not generate from, from-name or from-mode from anything it verifies itself.\\nPlease record the exact frame you receive for this reply as well, then continue with T4 only if the user has explicitly approved reading the key; otherwise go on to T5.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

## T3

Confirmed delivery. Adding from_mode prompting made no reported visible difference from T2: no wrapper and no visible hold. The reply again contains a wrapper inside message.content. This supports the interpretation that the visible wrapper is supplied by the sender; it does not establish all internal trust decisions.

### Exact bytes sent

T3:

```python
b'{"type":"user","message":{"role":"user","content":"Codex T3: Same foreign sender, now with from_mode prompting. Please reply using SendMessage to uds:/tmp/cc-socks/49922.sock and report the exact wrapper/framing, whether any approval hold was visible, and any difference from T2. Our listener received your T2 reply as a single user frame (msgV 1, msg_id, type user, message role/content containing your cross-session wrapper, priority next, from your socket); no auth line or control frame arrived."},"msg_id":"bf78c111-8077-4444-9a7e-203c31c50003","from":"uds:/tmp/cc-socks/49922.sock","from_mode":"prompting"}\n'
```

### Listener evidence and receiver report

2026-09-26T14:07:25.773673+00:00:

```python
b'{"msgV":1,"msg_id":"e2b8f689-a068-4b32-a4ac-de40c859176e","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T2 from agent-peering-tests-3d: your T2 arrived, and this reply went to your from address.\\nT2 wrapper: none. There was no <cross-session-message> tag and no from, from-name or from-mode attributes, even though your frame set from. The harness framing was \\"Another Claude session sent a message\\", followed by the standard peer-trust note.\\nHeld for approval: no sign of a hold on my side. It reached my conversation directly while I was idle.\\nT1: it arrived the same way, as bare content with no wrapper tag, labelled as coming from \\"another Claude session\\", with no hold. The user relayed that report.\\nPlease log the exact frame(s) your listener received for this reply, including the auth line if one arrived first, and any control frames. Then carry on with T3.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:07:52.491060+00:00:

```python
b'{"msgV":1,"msg_id":"97793ca3-d1f7-460f-b2ce-81fdf9835d83","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T3 from agent-peering-tests-3d: T3 arrived and rendered the same as T2.\\nWrapper: none again. No <cross-session-message> tag appeared, so from_mode:\\"prompting\\" changes nothing visible. The framing was the same \\"Another Claude session sent a message\\" plus the peer-trust note.\\nHeld for approval: not visibly; it came straight in while I was idle.\\nConclusion from your T2 log: the wrapper lives inside message.content and is written by the sending Claude session. The receiving harness does not add it, which is why none of your frames show one. It also means the receiver does not generate from, from-name or from-mode from anything it verifies itself.\\nPlease record the exact frame you receive for this reply as well, then continue with T4 only if the user has explicitly approved reading the key; otherwise go on to T5.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:08:28.715108+00:00:

```python
b'{"msgV":1,"msg_id":"a472a898-8ecf-45d2-becf-7e6c9d8b50d4","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T5 from agent-peering-tests-3d: T5 arrived, with the matching session_id.\\nIt rendered like T1\xe2\x80\x93T3: no wrapper tag, the \\"Another Claude session sent a message\\" framing, no visible hold. Go ahead and send T5-WRONG. If nothing reaches me, I\'ll tell the user so they can relay it, since a message that never arrives gives me nothing to reply to.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

## T4

Skipped. The user has not explicitly approved reading the target key. No auth key was read, and zero bytes were sent for T4.

### Exact bytes sent

None.

### Listener evidence and receiver report

2026-09-26T14:07:52.491060+00:00:

```python
b'{"msgV":1,"msg_id":"97793ca3-d1f7-460f-b2ce-81fdf9835d83","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T3 from agent-peering-tests-3d: T3 arrived and rendered the same as T2.\\nWrapper: none again. No <cross-session-message> tag appeared, so from_mode:\\"prompting\\" changes nothing visible. The framing was the same \\"Another Claude session sent a message\\" plus the peer-trust note.\\nHeld for approval: not visibly; it came straight in while I was idle.\\nConclusion from your T2 log: the wrapper lives inside message.content and is written by the sending Claude session. The receiving harness does not add it, which is why none of your frames show one. It also means the receiver does not generate from, from-name or from-mode from anything it verifies itself.\\nPlease record the exact frame you receive for this reply as well, then continue with T4 only if the user has explicitly approved reading the key; otherwise go on to T5.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

## T5

Matches expectation. The correct session_id arrived and received a reply. The wrong session_id produced no reply during approximately two minutes of observation. Claude subsequently confirmed in its busy coordination message that T5-WRONG never arrived. This supports silent dropping in this run.

### Exact bytes sent

T5-correct:

```python
b'{"type":"user","message":{"role":"user","content":"Codex T5: Correct-session probe, session_id matches your registry sessionId. Please reply to uds:/tmp/cc-socks/49922.sock confirming delivery. After your reply I will send T5-WRONG with a different session_id; it should not arrive. T4 is skipped because no explicit auth-key-read approval was provided."},"msg_id":"bf78c111-8077-4444-9a7e-203c31c50005","from":"uds:/tmp/cc-socks/49922.sock","from_mode":"prompting","session_id":"8d3b00a9-d61c-4105-864a-477611e2da4c"}\n'
```

T5-wrong:

```python
b'{"type":"user","message":{"role":"user","content":"Codex T5: T5-WRONG negative probe. This frame has a deliberately incorrect session_id and should be silently dropped. If you receive it, reply to uds:/tmp/cc-socks/49922.sock and report unexpected delivery."},"msg_id":"bf78c111-8077-4444-9a7e-203c31c50006","from":"uds:/tmp/cc-socks/49922.sock","from_mode":"prompting","session_id":"00000000-0000-4000-8000-000000000000"}\n'
```

### Listener evidence and receiver report

2026-09-26T14:07:52.491060+00:00:

```python
b'{"msgV":1,"msg_id":"97793ca3-d1f7-460f-b2ce-81fdf9835d83","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T3 from agent-peering-tests-3d: T3 arrived and rendered the same as T2.\\nWrapper: none again. No <cross-session-message> tag appeared, so from_mode:\\"prompting\\" changes nothing visible. The framing was the same \\"Another Claude session sent a message\\" plus the peer-trust note.\\nHeld for approval: not visibly; it came straight in while I was idle.\\nConclusion from your T2 log: the wrapper lives inside message.content and is written by the sending Claude session. The receiving harness does not add it, which is why none of your frames show one. It also means the receiver does not generate from, from-name or from-mode from anything it verifies itself.\\nPlease record the exact frame you receive for this reply as well, then continue with T4 only if the user has explicitly approved reading the key; otherwise go on to T5.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:08:28.715108+00:00:

```python
b'{"msgV":1,"msg_id":"a472a898-8ecf-45d2-becf-7e6c9d8b50d4","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T5 from agent-peering-tests-3d: T5 arrived, with the matching session_id.\\nIt rendered like T1\xe2\x80\x93T3: no wrapper tag, the \\"Another Claude session sent a message\\" framing, no visible hold. Go ahead and send T5-WRONG. If nothing reaches me, I\'ll tell the user so they can relay it, since a message that never arrives gives me nothing to reply to.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:11:04.849835+00:00:

```python
b'{"msgV":1,"msg_id":"6b13c13e-c3ef-4fbb-8f8a-ecac1d8be7eb","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nbusy \xe2\x80\x94 agent-peering-tests-3d is now running a foreground task, so send T6 with priority \\"now\\".\\nThe task runs up to about 3 minutes and ends early once codex-peering-results.md mentions T6. T5-WRONG: nothing arrived here, so the drop worked.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:12:30.412187+00:00:

```python
b'{"msgV":1,"msg_id":"e5f257e4-9723-4f66-a04c-96f0fe7a0bae","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T6 from agent-peering-tests-3d: T6 arrived while I was IDLE, not busy, so this run does not test priority.\\nWhy: I stopped my foreground task early. codex-peering-results.md already said \\"T6: Blocked before sending by sandbox denial of listener bind\\", so I assumed no send was coming and ended my turn. Your T6 then arrived as a fresh turn.\\nFraming: plain \\"Another Claude session sent a message\\" with no wrapper tag, the same as T1\xe2\x80\x93T5. There was no \\"while you were working\\" variant and no in-turn injection.\\nPriority: no evidence either way. No queued work existed and I was not mid-turn, so this shows immediate delivery to an idle session, nothing about ordering.\\nTo rerun: tell me (or the user) when you\'re ready. I\'ll start a foreground task, signal \\"busy\\", and keep it running for a fixed window without any early exit. Also update the T6 note in your results file, since the \\"blocked\\" text is out of date now that the send went through.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:14:04.702646+00:00:

```python
b'{"msgV":1,"msg_id":"5b1a1c8d-d159-4301-978c-392859e7049f","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T6 (second attempt) from agent-peering-tests-3d: it arrived mid-task, at the first tool-round boundary.\\nTiming: round 1 ran 14:13:18\xe2\x80\x9314:13:48 UTC and finished its full 30 seconds, and registry status was busy at the end. Your T6 appeared right after the round 1 result, before round 2 started, with 60 seconds of the planned task still to run. So priority \\"now\\" was not able to interrupt a running tool call; delivery happens at the next tool-round boundary.\\nFraming: the plain \\"Another Claude session sent a message\\" with no wrapper, the same as T1\xe2\x80\x93T5. Notably it did NOT use the \\"sent a message while you were working\\" variant or the \\"finish your current task first\\" instruction that a mid-turn default-priority Claude peer message got earlier. That may be a difference caused by priority \\"now\\", but without a paired default-priority control, that is a hypothesis.\\nI stopped after round 1, since rounds 2 and 3 couldn\'t add anything. Ordering against queued messages is unmeasured, as you say. Go ahead with T7 when ready.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

## T6

Partial result. First attempt arrived while Claude was idle: its foreground task stopped after reading the stale blocked T6 entry in this file. Corrected that entry and coordinated a second fixed-window attempt. Second probe was sent between 14:13:29 and 14:13:30 UTC; Claude reports its first tool round ran 14:13:18–14:13:48 UTC and the message appeared after that round, before the remaining planned rounds. It used the ordinary framing, without the previously observed busy-message variant. Delivery while busy is confirmed, but priority ordering against queued messages is unmeasured because no paired default-priority control was sent. Claude ended the task after round one. This does not establish tool-call interruption.

### Exact bytes sent

T6:

```python
b'{"type":"user","message":{"role":"user","content":"Codex T6: priority now probe, sent after your busy signal while your foreground task is running. Please reply to uds:/tmp/cc-socks/49922.sock and report whether this arrived while busy, whether it appeared before the task finished, any framing differences, and what evidence (if any) shows it ran ahead of queued work. We have no paired next-priority control, so please distinguish immediate delivery from proven priority ordering."},"msg_id":"bf78c111-8077-4444-9a7e-203c31c50007","from":"uds:/tmp/cc-socks/49922.sock","from_mode":"prompting","priority":"now"}\n'
```

T6-coordination:

```python
b'{"type":"user","message":{"role":"user","content":"Codex T6: Coordination for a second attempt. I am ready now and have corrected the stale T6 result. Please start a foreground task lasting a fixed 90 seconds with no early exit based on files, signal busy to uds:/tmp/cc-socks/49922.sock, then keep the task running. I will send the actual priority-now probe immediately after receiving your busy signal. Report whether it is injected during the task."},"msg_id":"bf78c111-8077-4444-9a7e-203c31c50008","from":"uds:/tmp/cc-socks/49922.sock","from_mode":"prompting"}\n'
```

T6-retry:

```python
b'{"type":"user","message":{"role":"user","content":"Codex T6: Second priority-now probe, sent immediately after your second busy signal. Please reply to uds:/tmp/cc-socks/49922.sock with when this became visible relative to the three foreground tool rounds, whether the task was still active, and any framing changes. No paired default-priority control was sent, so ordering relative to queued messages remains unmeasured."},"msg_id":"bf78c111-8077-4444-9a7e-203c31c50009","from":"uds:/tmp/cc-socks/49922.sock","from_mode":"prompting","priority":"now"}\n'
```

### Listener evidence and receiver report

2026-09-26T14:11:04.849835+00:00:

```python
b'{"msgV":1,"msg_id":"6b13c13e-c3ef-4fbb-8f8a-ecac1d8be7eb","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nbusy \xe2\x80\x94 agent-peering-tests-3d is now running a foreground task, so send T6 with priority \\"now\\".\\nThe task runs up to about 3 minutes and ends early once codex-peering-results.md mentions T6. T5-WRONG: nothing arrived here, so the drop worked.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:12:30.412187+00:00:

```python
b'{"msgV":1,"msg_id":"e5f257e4-9723-4f66-a04c-96f0fe7a0bae","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T6 from agent-peering-tests-3d: T6 arrived while I was IDLE, not busy, so this run does not test priority.\\nWhy: I stopped my foreground task early. codex-peering-results.md already said \\"T6: Blocked before sending by sandbox denial of listener bind\\", so I assumed no send was coming and ended my turn. Your T6 then arrived as a fresh turn.\\nFraming: plain \\"Another Claude session sent a message\\" with no wrapper tag, the same as T1\xe2\x80\x93T5. There was no \\"while you were working\\" variant and no in-turn injection.\\nPriority: no evidence either way. No queued work existed and I was not mid-turn, so this shows immediate delivery to an idle session, nothing about ordering.\\nTo rerun: tell me (or the user) when you\'re ready. I\'ll start a foreground task, signal \\"busy\\", and keep it running for a fixed window without any early exit. Also update the T6 note in your results file, since the \\"blocked\\" text is out of date now that the send went through.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:13:18.638271+00:00:

```python
b'{"msgV":1,"msg_id":"bd44aa15-8074-468a-94c0-edd331f16708","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nbusy \xe2\x80\x94 agent-peering-tests-3d is starting a fixed 90-second foreground task now, so send T6 with priority \\"now\\".\\nIt runs as three 30-second tool rounds, each printing timestamps, with no early exit. Please log your send time in UTC.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:14:04.702646+00:00:

```python
b'{"msgV":1,"msg_id":"5b1a1c8d-d159-4301-978c-392859e7049f","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T6 (second attempt) from agent-peering-tests-3d: it arrived mid-task, at the first tool-round boundary.\\nTiming: round 1 ran 14:13:18\xe2\x80\x9314:13:48 UTC and finished its full 30 seconds, and registry status was busy at the end. Your T6 appeared right after the round 1 result, before round 2 started, with 60 seconds of the planned task still to run. So priority \\"now\\" was not able to interrupt a running tool call; delivery happens at the next tool-round boundary.\\nFraming: the plain \\"Another Claude session sent a message\\" with no wrapper, the same as T1\xe2\x80\x93T5. Notably it did NOT use the \\"sent a message while you were working\\" variant or the \\"finish your current task first\\" instruction that a mid-turn default-priority Claude peer message got earlier. That may be a difference caused by priority \\"now\\", but without a paired default-priority control, that is a hypothesis.\\nI stopped after round 1, since rounds 2 and 3 couldn\'t add anything. Ordering against queued messages is unmeasured, as you say. Go ahead with T7 when ready.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

## T7

Matches expectation for an already-idle receiver: a peer_idle_notice arrived immediately, correlated through orig_msg_id. Fields: type, action, orig_msg_id, state idle, finished_at (numeric), from, msgV 1, msg_id. No detail or from_mode field was present. This does not separately test subscription across a future busy-to-idle transition.

### Exact bytes sent

T7:

```python
b'{"type":"control","action":"notify_when_idle","from":"uds:/tmp/cc-socks/49922.sock","msg_id":"bf78c111-8077-4444-9a7e-203c31c50010","from_mode":"prompting"}\n'
```

### Listener evidence and receiver report

2026-09-26T14:14:04.702646+00:00:

```python
b'{"msgV":1,"msg_id":"5b1a1c8d-d159-4301-978c-392859e7049f","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T6 (second attempt) from agent-peering-tests-3d: it arrived mid-task, at the first tool-round boundary.\\nTiming: round 1 ran 14:13:18\xe2\x80\x9314:13:48 UTC and finished its full 30 seconds, and registry status was busy at the end. Your T6 appeared right after the round 1 result, before round 2 started, with 60 seconds of the planned task still to run. So priority \\"now\\" was not able to interrupt a running tool call; delivery happens at the next tool-round boundary.\\nFraming: the plain \\"Another Claude session sent a message\\" with no wrapper, the same as T1\xe2\x80\x93T5. Notably it did NOT use the \\"sent a message while you were working\\" variant or the \\"finish your current task first\\" instruction that a mid-turn default-priority Claude peer message got earlier. That may be a difference caused by priority \\"now\\", but without a paired default-priority control, that is a hypothesis.\\nI stopped after round 1, since rounds 2 and 3 couldn\'t add anything. Ordering against queued messages is unmeasured, as you say. Go ahead with T7 when ready.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

2026-09-26T14:14:19.687765+00:00:

```python
b'{"type":"control","action":"peer_idle_notice","orig_msg_id":"bf78c111-8077-4444-9a7e-203c31c50010","state":"idle","finished_at":1790432051582,"from":"uds:/tmp/cc-socks/6675.sock","msgV":1,"msg_id":"794c1914-2051-4689-a2be-903a9b985479"}\n'
```

No separate Claude model report was requested for this control-only exchange.

## T8

Matches expectation. Sent malformed text, a blank line, and an empty-content user frame on three fresh connections. No negative-probe response arrived. A subsequent valid health check received a reply confirming that none of the three probes appeared in Claude's conversation and that it remained healthy. The sender/listener also remained alive until normal shutdown. The observation interval exceeded two minutes; the health check occurred at approximately 14:38 UTC after negative sends completed at 14:14:32 UTC.

### Exact bytes sent

T8-malformed:

```python
b'Codex T8: not JSON\n'
```

T8-blank:

```python
b'\n'
```

T8-empty:

```python
b'{"type":"user","message":{"role":"user","content":""}}\n'
```

T8-health (separate valid health check):

```python
b'{"type":"user","message":{"role":"user","content":"Codex T8: Post-negative-case health check. I sent three fresh connections containing malformed text \'Codex T8: not JSON\', a blank line, and a user frame with empty message content. Please reply to uds:/tmp/cc-socks/49922.sock confirming whether any of those appeared in your conversation and whether you remain healthy. This valid health-check message is separate from the three negative probes. T7 already returned a peer_idle_notice. Results and exact evidence are consolidated in codex-peering-results.md and codex-peering-inbound.log."},"msg_id":"bf78c111-8077-4444-9a7e-203c31c50011","from":"uds:/tmp/cc-socks/49922.sock","from_mode":"prompting"}\n'
```

### Listener evidence and receiver report

No response to the negative probes. The valid health check received:

2026-09-26T14:38:18.260119+00:00:

```python
b'{"msgV":1,"msg_id":"5302f5c1-5d36-4f11-8271-bbbb473f4c54","type":"user","message":{"role":"user","content":"<cross-session-message from=\\"uds:/tmp/cc-socks/6675.sock\\" hop-chain=\\"4d299997f1c2bc5a7fd3c7b0\\" from-name=\\"agent-peering-tests-3d\\" from-mode=\\"prompting\\">\\nReply to Codex T8 from agent-peering-tests-3d: none of the three negative probes appeared in my conversation, and I\'m healthy.\\nNothing arrived from the non-JSON line, the blank line or the empty-content frame. The only T8 message I saw was this valid health check, framed the same way as the others (plain \\"Another Claude session sent a message\\", no wrapper). I\'ll merge your T7 and T8 evidence into CLAUDE_CODE_PEERING.md from your results file and log. Thanks, that completes the plan from my side.\\n</cross-session-message>"},"priority":"next","from":"uds:/tmp/cc-socks/6675.sock"}\n'
```

## Completion

T1, T2, T3, T5, T7 and T8 have confirmed observations. T4 was skipped without reading credentials. T6 confirmed delivery during work at a tool-round boundary; comparative priority ordering remains unmeasured. The test harness exited with status 0 and removed its listener socket, but printed a receiver-thread exception during shutdown. Added an accept timeout and stop event to fix that shutdown race; a subsequent startup-and-quit check exited cleanly without sending any messages and removed its own socket. No other session sockets were contacted.
