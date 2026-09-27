---
title: Embedded bus
description: The phase 2 NATS subject layout, account boundary, streams, and credentials.
---

## Bootstrap server

[Inference] `agentd serve --state-dir DIR --agent alice` starts NATS with JetStream on the literal IPv4 address `127.0.0.1`. It creates the `build` account and writes broker state below `DIR/store` (`internal/bus/bus.go`, `internal/bus/bus_test.go`). The `--agent` flag may be repeated. `--port` defaults to `4222`. The daemon prints the listener URL and state directory, then runs until interrupted (`cmd/agentd/main.go`).

[Verified] The bus creates one account for each group passed to `bus.Start`. The group account has one file-backed JetStream stream with limits retention and publish acknowledgments disabled, so the broker does not publish a stream acknowledgment to a caller-selected reply subject. Each initial agent has a durable pull consumer with explicit acknowledgments and two filters (`internal/core/layout/layout.go`, `internal/bus/bus.go`, `internal/bus/bus_test.go`).

## Subjects

| Subject | Purpose |
| --- | --- |
| `grp.<group>.msg.all.<from>` | Group broadcast |
| `grp.<group>.msg.dm.<to>.<from>` | Direct message |
| `grp.<group>.msg.op.<from>` | Message to the operator |
| `grp.<group>.evt.<kind>.<agent>` | Lifecycle event |

[Verified] A group stream captures `grp.<group>.msg.>` and `grp.<group>.evt.>`. Each agent's consumer filters `grp.<group>.msg.all.*` and `grp.<group>.msg.dm.<agent>.*` (`internal/core/layout/layout.go`, `internal/bus/bus.go`). Group and agent names are single lowercase tokens beginning with a letter. The agent name `operator` is reserved. Later characters may be lowercase letters, digits, `-`, or `_` (`internal/core/layout/layout.go`).

[Inference] The event subject moves `<agent>` to the final token. The [messaging sketch](https://github.com/tbhb/agent-orchestration-poc/blob/main/design-sketch/04-messaging-and-shared-context.md) placed `<kind>` last while also requiring every agent publication to end in its own name. The implemented order lets the server enforce the sender rule with a literal allow list.

## Credentials and isolation

[Verified] The bus uses per-agent user nkeys. The seed for each identity is stored at `DIR/credentials/<group>/<agent>.seed` with mode `0600`. The group operator uses `operator.seed`. The bus exposes credential file paths to callers and never prints seeds (`internal/bus/bus.go`, `internal/bus/bus_test.go`).

[Verified] An agent may publish on its own broadcast, direct, operator, and event subjects only when the subject ends in its own name. Those publications are stored without a JetStream publish acknowledgment. It may subscribe to group broadcasts and direct messages addressed to it. The operator credential manages the group's stream and can observe its messages and events (`internal/core/perms/perms.go`). Integration tests at NATS server v2.15.0 reject cross-agent publication, another agent's direct subscription, another group's subjects, and attempts to use reply addresses or JetStream API routes to publish under another agent's name (`internal/bus/bus_test.go`, `reports/inputs/bus-26-evidence-2026-09-26.md`).

[Documented] Static nkey users are bound to an account and literal permission lists in server options. The NATS `{{name()}}` permission template applies to scoped JWT users or auth callout, not static nkey users (`experiments/00-system-assessment/nats-research.md` sections 7 and 8, `nats-server/server/auth.go` at source commit `3e8ddaa7`). User JWTs were rejected for bootstrap because they add issuer and account signing infrastructure without improving the required per-agent subject boundary. A later decision record can revisit the choice when credentials must be issued across machines.

[Verified] Agent credentials cannot publish under `$JS.API.` or `$JS.ACK.` and cannot subscribe to `_INBOX.>`. A test against the embedded server checks stream, consumer, direct-get, generic API, and ack routes under both prefixes (`internal/core/perms/perms.go`, `internal/bus/bus_test.go`). The group operator credential can issue JetStream requests and subscribe to their replies. The restart test uses it to pull and acknowledge a saved message. An agent cannot directly use its provisioned durable consumer.

[Observed] With stream publish acknowledgments disabled, JetStream returns no storage or deduplication confirmation to a direct publisher. This and the lack of direct pull access depart from the [messaging sketch](https://github.com/tbhb/agent-orchestration-poc/blob/main/design-sketch/04-messaging-and-shared-context.md), which has agents use their own durable pull consumers. A narrowly scoped agent pull grant is unsafe: a caller-controlled reply subject can make the broker deliver the fetched message under another agent's name, bypassing sender attribution (PR #82 review). Subject permissions alone cannot secure that route. [Untested] The authenticated `agentd` relay for receive, ack, publish confirmation, and status and roster reads belongs to [issue #96](https://github.com/tbhb/agent-orchestration-poc/issues/96). Issue #27 depends on that relay. Direct agent receive, ack, and publish confirmation remain unavailable until it is implemented.
