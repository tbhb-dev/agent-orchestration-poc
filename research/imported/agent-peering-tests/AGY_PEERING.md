# Antigravity (agy) Peering Reference

This document describes how to communicate with independent running Antigravity (`agy`) agent sessions.

## Architecture

Antigravity handles peer messaging asynchronously using a filesystem-backed queue. 

- **Discovery:** Sessions are identified by UUIDs. There is no central namespace of aliases; you must obtain the recipient's conversation UUID (e.g., from `~/.gemini/antigravity-cli/conversation_summaries.db`).
- **Topology:** There is no shared daemon listening on a local port for messages. Instead, the sender writes a message payload to the recipient's `brain` directory. The recipient's runtime process (the Language Server) discovers the payload.
- **Transport:** Filesystem. Messages are JSON payloads dropped into `~/.gemini/antigravity-cli/brain/<recipient-id>/.system_generated/messages/`. 
- **Message lifecycle:**
  1. **Pending:** The JSON file is created in the `messages/` queue.
  2. **Consumed:** The recipient reads the message at the start of a turn and records the message UUID in `read.json`.
  3. **Executing:** The message is presented to the recipient model wrapped in a `<SYSTEM_MESSAGE>` block containing authenticated header metadata.
- **Replies:** Native asynchronous callbacks do not exist. To reply, the recipient must use the `send_message` tool directed at the original sender's ID (provided in the system metadata).

## Verified Protocol & Permissions

While the transport uses standard JSON files in a directory, **the payloads are cryptographically signed** to prevent spoofing. 

- **Authentication:** The `send_message` tool injects a `sourceMetadata.tool.thinkingSignature` signed by the runtime environment.
- **Permissions:** If a third-party process or unauthorized script drops a perfectly formatted JSON message into the `messages/` queue without a valid signature, the Antigravity runtime will silently ignore it.
- **Access Boundary:** This signature enforcement prevents arbitrary local processes from impersonating agents or injecting context unless they go through an authorized `agy` runtime.

## Behavior Matrix

| State/Condition | Behavior |
| --- | --- |
| **Recipient Idle** | The message is queued on disk. It will be delivered as part of the next user-initiated turn (e.g., the next prompt). |
| **Recipient Busy (Tool active)** | The message is queued. It does not interrupt the active tool. It will be delivered together with other pending messages at the next turn boundary. |
| **Recipient Unloaded** | The message persists on disk in the `messages/` queue. It will be read as soon as the session is resumed and a new turn is triggered. |
| **Invalid Recipient ID** | The `send_message` tool synchronously validates the recipient ID and immediately returns an error. |
| **Multiple Messages** | Messages do not trigger separate turns; they are bundled chronologically into a single `<SYSTEM_MESSAGE>` block for the recipient's next turn. |

## External Integration (Codex / Claude)

Because Antigravity enforces cryptographic signatures on message files, external agents (like Claude or Codex) **cannot** simply write a JSON file to the `messages/` directory.

To send a message into an `agy` session, external agents should use the `agy` CLI to spawn a transient agent that has the native `send_message` tool available, or directly inject a turn.

### Method A: Direct Turn Injection (Takes over session)
If you want to forcibly wake the recipient and make them read your message immediately, use the `--print` command. 
*Note: This will fail with a conflict if the recipient's CLI UI is actively open.*
```bash
agy --conversation <recipient-id> --print "Message from Codex: Hello!"
```

### Method B: Asynchronous Queueing via Tool (Requires empty project)
If you want to enqueue a message asynchronously without taking over the recipient's runtime (to be read whenever they wake up), spawn a disposable `agy` agent to send it on your behalf:
```bash
agy --new-project --print "Use the send_message tool to send this exact text to <recipient-id>: 'Message from Claude!'"
```
This leverages the new agent's authorized access to the `send_message` tool, generating a valid `thinkingSignature` and queuing the message properly in the recipient's inbox.

## Observation / Polling Recipes

If you need to know when your asynchronously sent message was read by the recipient, you can poll the recipient's `read.json` file. 

1. Note the UUID of the message generated (if using a tool, you might need to inspect the sender's `messages/` outbox or trace the tool execution).
2. Periodically check:
```bash
cat ~/.gemini/antigravity-cli/brain/<recipient-id>/.system_generated/messages/read.json
```
If your message UUID appears with the value `true`, the recipient has processed it into their context.
