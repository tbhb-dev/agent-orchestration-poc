---
title: agentctl reference
description: Relay-backed agent messaging commands and their JSON output.
---

## Connection

Set `AGENTCTL_GROUP`, `AGENTCTL_AGENT`, and `AGENTCTL_CREDS_FILE` to the assigned group, agent, and nkey seed file path. Set `AGENTCTL_PORT` if `agentd serve` does not use port `4222`. The corresponding flags after a command override these values. The seed is read from the file. Keep its contents out of the command line.

## Commands

| Command | Result |
| --- | --- |
| `agentctl send bob "hello"` | Publish to Bob through the daemon relay |
| `agentctl send '*' "hello"` | Publish to the group |
| `agentctl send operator "hello"` | Publish to the operator |
| `agentctl receive --timeout 30` | Wait up to 30 seconds for one durable message |
| `agentctl ack '<id>'` | Confirm a received delivery using its opaque token |

`send --id same` supplies an idempotency key for retries. A confirmed send reports `stored` or `duplicate` with the stream sequence. The relay scopes this key to the authenticated sender and message subject. `receive` waits in pulls of at most five seconds until the requested timeout, then exits with code 3. The timeout range is 1 to 3600 seconds.

## Output

Each command prints one compact JSON object and a newline on stdout. `--help` documents the format and exit codes. The following exchange reflects the fields checked by `TestRelayCLIExchange`. IDs and the token are illustrative.

```json
{"ok":true,"command":"send","result":"stored","id":"same","to":"bob","sequence":1}
{"ok":true,"command":"send","result":"duplicate","id":"same","to":"bob","sequence":1}
{"ok":true,"command":"receive","result":"delivered","id":"<opaque-token>","from":"alice","sequence":1,"message":{"body":{"text":"hello"}}}
{"ok":true,"command":"ack","result":"acked","id":"<opaque-token>"}
{"ok":false,"command":"ack","result":"unknown-token","error":"unknown-token"}
{"ok":false,"command":"receive","result":"empty"}
```

Pass the receive result's `id` directly to `ack`. It is a daemon-held token. Exit code 0 means success, 1 means a relay or connection error, 2 means invalid usage, and 3 means no message before the receive timeout. The embedded-server integration test verifies the exchange, duplicate send, reused-token rejection, and timeout at the pinned broker versions in `go.mod`.

## Deferred commands

This size-bounded part of issue #27 leaves `join`, `status`, and `roster` for a follow-up. Registration belongs to issue #28. Production status and roster bucket writes and group-scoped visibility also need the follow-up. Agent grants remain exactly as defined by the [relay decision](/decisions/0010-agent-bus-relay/).
