---
title: agentctl reference
description: Agent commands for the build group's embedded message bus.
---

## Connection

[Verified] `agentctl` connects to the literal IPv4 loopback address `127.0.0.1` and reads a per-agent nkey seed from the file named by `AGENTCTL_CREDS_FILE` or `--creds-file` (`internal/bus/client/client.go`, `cmd/agentctl/main.go`). Set `AGENTCTL_GROUP` and `AGENTCTL_AGENT` to the assigned identity. Set `AGENTCTL_PORT` when `agentd serve` uses a port other than `4222`. Flags placed after the command override the corresponding environment values.

```sh
export AGENTCTL_GROUP=build
export AGENTCTL_AGENT=alice
export AGENTCTL_CREDS_FILE=/path/to/alice.seed
agentctl join
```

[Verified] The credential seed is read from the file, not passed as an argument or environment value (`internal/bus/client/client.go`). Give each worker only its own file path.

## Commands

| Command | Result |
| --- | --- |
| `agentctl join` | Record the agent in the roster, initialize idle status, and return the roster and receive instructions |
| `agentctl send bob "text"` | Publish a direct message with a generated `Nats-Msg-Id` |
| `agentctl send '*' "text"` | Publish a group broadcast |
| `agentctl send operator "text"` | Publish to the operator |
| `agentctl send bob "question" --wait 30` | Wait up to 30 seconds for an answer with the question's correlation ID |
| `agentctl receive --timeout 30` | Fetch one message from the agent's durable pull consumer |
| `agentctl ack '<id>'` | Acknowledge the receive result's `id` |
| `agentctl status --set working --detail "reviewing"` | Write and return the agent's status |
| `agentctl status` | Read the agent's status |
| `agentctl roster` | Read the joined agents |

[Verified] `send --id ID` supplies an idempotency key for retries. A reply uses `--correlation-id ID --reply-to-id ID`, where `ID` is the original message header ID (`internal/core/command/command.go`, `internal/bus/client/client.go`). [Untested] `send --wait` uses a live subscription and matches only answer messages with that correlation ID. It is intended to leave the durable consumer available to a concurrent `receive` (`internal/bus/client/client.go`).

```sh
agentctl send bob "Can you review #27?" --wait 30
agentctl receive --timeout 30
agentctl send alice "Review complete" --correlation-id QUESTION_ID --reply-to-id QUESTION_ID
agentctl ack '$JS.ACK.GROUP_BUILD.alice.EXAMPLE'
```

## Output and exit codes

[Verified] Each command result is one JSON object followed by a newline on stdout. A short summary goes to stderr. The stable top-level field names are `ok`, `command`, `id`, `from`, `to`, `message`, `role`, `instructions`, `status`, `detail`, `roster`, and `error`. Empty optional fields are omitted (`internal/core/render/render.go`, `cmd/agentctl/main.go`).

```json
{"ok":true,"command":"send","id":"example-id","to":"bob"}
{"ok":true,"command":"receive","id":"$JS.ACK.GROUP_BUILD.bob.EXAMPLE","from":"alice","message":{"body":{"text":"hello"},"headers":{"id":"example-id","kind":"message","timestamp":"2026-09-26T00:00:00Z"}}}
{"ok":false,"command":"receive","error":"no message before timeout"}
```

[Verified] `receive.id` is the broker acknowledgment token. Pass that exact string to `ack`. The envelope header `message.headers.id` is the sender's idempotency key and is the value used for reply correlation (`internal/bus/client/client.go`, `internal/core/envelope/envelope.go`).

| Exit code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Bus or credential error |
| `2` | Usage error |
| `3` | No message or answer before the timeout |

## Current dependency

[Observed] At the #82 stacked revision, agent credentials cannot use JetStream publish acknowledgments, pull consumers, acknowledgments, or key-value buckets. The embedded-server permission probe and exact denied subjects are in `reports/inputs/agentctl-27-evidence-2026-09-26.md`. The commands above describe the #27 code, while end-to-end agent exchange awaits a reviewed #82 permission or broker-mediation change.
