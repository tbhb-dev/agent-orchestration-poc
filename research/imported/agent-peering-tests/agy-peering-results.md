# Antigravity Peering Results

## 1. Discover the installed surfaces
**[observed]** `send_message` built-in tool is available for agents to communicate with other sessions via their conversation IDs.
**[observed]** The delivery mechanism is filesystem-based. The tool creates a JSON file in `~/.gemini/antigravity-cli/brain/<recipient-id>/.system_generated/messages/`. 
**[observed]** Read state is tracked via a `read.json` dictionary in the same directory.
**[inference]** The payload includes a `sourceMetadata.tool.thinkingSignature` signed by the runtime, ensuring that arbitrary files placed in the queue without a valid signature are ignored.

## 2. Characterize behavior with bounded probes

### T01 — idle delivery
**[observed]** Sent `AGY-PEER-R1-T01` to idle recipient `c4602810-5341-409e-b26d-95d1527b224f`. The message was written to the `messages/` directory and remained queued. When the recipient session was activated with a new prompt, the message was delivered as part of the new turn, encapsulated in a `<SYSTEM_MESSAGE>` block with verified `sender` and `timestamp` metadata.

### T02 — addresses
**[observed]** Tested sending to an invalid ID (`invalid-id`). The `send_message` tool immediately rejected it with `recipient "invalid-id" not found`, confirming that resolution and validation happen synchronously at the sender side.

### T03 — active work & T04 — ordering
**[observed]** While the recipient session was active/sleeping, sent multiple messages (T03, T04-A, T04-B, T04-C) sequentially.
**[observed]** The producer does not block; `send_message` returns immediately. 
**[observed]** The messages are not interrupted or injected mid-turn. Instead, they accumulate in the `messages/` directory and are delivered together in chronological order at the start of the next turn.

### T05 — delivery modes
**[untested/blocked]** The `send_message` tool does not expose steering, interrupt, or priority mode arguments. All messages are enqueued and processed at the next turn boundary.

### T06 — pending-input controls
**[untested/blocked]** No built-in tool exists to list, edit, or delete pending messages. Since they are stored as JSON files on the filesystem, a sender on the same machine could theoretically remove their own unread message file, but no API is provided.

### T07 — retries
**[untested/blocked]** The `send_message` tool automatically generates a new UUID for each payload. There is no user-supplied idempotency key field available to test deduplication.

### T08 — content
**[observed]** Sent multiline text containing quotes and backticks. The recipient successfully received the exact characters without mangling, preserving the original formatting.

### T09 — notifications/history
**[inference]** There is no push notification for delivery or completion. A producer on the same machine can poll the recipient's `messages/read.json` to confirm when a message UUID has been processed.

### T10 — identity
**[observed]** The recipient model does not see the payload as a raw user message. It is encapsulated in `<SYSTEM_MESSAGE>` with explicit system-provided metadata (`timestamp`, `sender`, `priority`). The sender ID is strictly the conversation ID of the sender.

### T11 — explicit reply
**[observed]** Supplied the sender's conversation ID in the payload and requested a reply. The recipient successfully used its own `send_message` tool to dispatch a reply back. The reply arrived correctly in the sender's inbox (as an asynchronous notification).

### T12 — foreign producer
**[observed]** Attempted to drop a correctly formatted JSON message payload directly into the `messages/` directory using a Python script. 
**[observed]** The message was ignored by the recipient. 
**[inference]** The system enforces an access boundary by requiring a valid `thinkingSignature` in the tool metadata. Thus, an independent process cannot send messages by merely mimicking the JSON schema unless it holds the private keys or can invoke the local RPC to sign the message.

### T13 — disconnect/persistence
**[observed]** Messages are written to the filesystem before the recipient processes them. If the recipient is disconnected, the message persists across restarts and is read when the session is resumed.

### T14 — runtime ownership
**[observed]** Input can be accepted (queued to disk) without the recipient thread being awake or loaded. 

### T16 — access boundary
**[observed]** The access boundary is strongly enforced. The CLI and sandbox allow writing to the directory, but the recipient runtime rejects unsigned payloads. 
