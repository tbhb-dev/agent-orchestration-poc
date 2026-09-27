---
title: Embedded bus
description: The phase 2 NATS subject layout, account boundary, streams, and credentials.
---

## Bootstrap server

[Inference] `agentd serve --state-dir DIR --agent alice` starts NATS with JetStream on the literal IPv4 address `127.0.0.1`. It creates the `build` account and writes broker state below `DIR/store` (`internal/bus/bus.go`, `internal/bus/bus_test.go`). The `--agent` flag may be repeated. `--port` defaults to `4222`. The daemon prints the listener URL and state directory, then runs until interrupted (`cmd/agentd/main.go`).

[Verified] The bus creates one account for each group passed to `bus.Start`. The group account has one file-backed JetStream stream with limits retention and publish acknowledgments enabled. Only the operator credential can publish to it. Each initial agent has a durable pull consumer with explicit acknowledgments and two filters (`internal/core/layout/layout.go`, `internal/core/perms/perms.go`, `internal/bus/bus.go`, `internal/bus/bus_test.go`).

## Subjects

| Subject | Purpose |
| --- | --- |
| `grp.<group>.msg.all.<from>` | Group broadcast |
| `grp.<group>.msg.dm.<to>.<from>` | Direct message |
| `grp.<group>.msg.op.<from>` | Message to the operator |
| `grp.<group>.evt.<kind>.<agent>` | Lifecycle event |
| `grp.<group>.relay.req.<operation>.<agent>` | Authenticated agent request |
| `grp.<group>.relay.reply.<agent>.<request-id>` | Private relay response |

[Verified] A group stream captures `grp.<group>.msg.>` and `grp.<group>.evt.>`. Each agent's consumer filters `grp.<group>.msg.all.*` and `grp.<group>.msg.dm.<agent>.*` (`internal/core/layout/layout.go`, `internal/bus/bus.go`). Group and agent names are single lowercase tokens beginning with a letter. The agent name `operator` is reserved. Later characters may be lowercase letters, digits, `-`, or `_` (`internal/core/layout/layout.go`).

[Inference] The event subject moves `<agent>` to the final token. The [messaging sketch](https://github.com/tbhb/agent-orchestration-poc/blob/main/design-sketch/04-messaging-and-shared-context.md) placed `<kind>` last while also requiring every agent publication to end in its own name. The implemented order lets the server enforce the sender rule with a literal allow list.

## Credentials and isolation

[Verified] The bus uses per-agent user nkeys. The seed for each identity is stored at `DIR/credentials/<group>/<agent>.seed` with mode `0600`. The group operator uses `operator.seed`. The bus exposes credential file paths to callers and never prints seeds (`internal/bus/bus.go`, `internal/bus/bus_test.go`).

[Verified] An agent may publish only to the five relay request operations with its literal final token and may subscribe only to its own relay reply prefix. The operator credential manages the group stream, publishes relay responses, and can observe messages and events (`internal/core/perms/perms.go`, `internal/bus/relay_test.go`).

[Documented] Static nkey users are bound to an account and literal permission lists in server options. The NATS `{{name()}}` permission template applies to scoped JWT users or auth callout, not static nkey users (`experiments/00-system-assessment/nats-research.md` sections 7 and 8, `nats-server/server/auth.go` at source commit `3e8ddaa7`). User JWTs were rejected for bootstrap because they add issuer and account signing infrastructure without improving the required per-agent subject boundary. A later decision record can revisit the choice when credentials must be issued across machines.

[Verified] Agent credentials cannot publish under `$JS.API.`, `$JS.ACK.`, `$KV.`, message, or event subjects and cannot subscribe to `_INBOX.>`. The operator connection uses its own broker reply address for publish, pull, confirmed ack, and KV reads (`internal/core/perms/perms.go`, `internal/bus/relay.go`, `internal/bus/relay_test.go`).

[Verified] Agent `send` publishes through `agentd`, which derives the sender subject from the authenticated request and reports `stored` or `duplicate` only from a matching JetStream acknowledgment. A client message ID is scoped to that sender subject. `receive` fetches from that agent's durable consumer, and `ack` accepts only an outstanding opaque token. Restart clears tokens and later redelivery gets a fresh one. `status` and `roster` return `not-provisioned` for an absent bucket and `not-found` for an absent key. Production buckets and writes belong to issue #29. Dynamic agent registration and its relay grant test belong to issue #28 (`internal/core/relay/relay.go`, `internal/bus/relay.go`, `internal/bus/relay_test.go`).

## Relay request and response

An agent publishes a JSON object on `grp.<group>.relay.req.<operation>.<agent>` and subscribes to `grp.<group>.relay.reply.<agent>.<id>` before sending. `id` is a safe single subject token. The daemon ignores the NATS reply field. `send` accepts `destination` as `all`, `dm`, or `operator`, a `to` token only for `dm`, a JSON object in `envelope`, and optional `message_id`. `receive` accepts `timeout_ms` from 1 through 5000, with 1000 as the default. `ack` accepts `token`. `status` and `roster` accept `key`. Payload identity fields are ignored.

The response includes a `result` string. Send returns `stored`, `duplicate`, `rejected`, or `unknown`, with `sequence` only for a confirmed stored or duplicate result. Receive returns `delivered` with `sequence`, `subject`, `envelope`, and an opaque `token`, or `empty`, `rejected`, or `unknown`. Ack returns `acked`, `unknown-token`, or `unknown`. Reads return `found` with base64 encoded `value`, `not-provisioned`, `not-found`, `rejected`, or `unknown`. The encoded value preserves arbitrary KV bytes. A response timeout leaves the caller uncertain, so it may retry `send` with the same `message_id` inside the server's deduplication window.
