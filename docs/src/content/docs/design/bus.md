---
title: Embedded bus
description: The phase 2 NATS subject layout, account boundary, streams, and credentials.
---

## Bootstrap server

[Inference] `agentd serve --state-dir DIR --agent alice` starts NATS with JetStream on the literal IPv4 address `127.0.0.1`. It creates the `build` account and writes broker state below `DIR/store` (`internal/bus/bus.go`, `internal/bus/bus_test.go`). The `--agent` flag may be repeated. `--port` defaults to `4222`. The daemon prints the listener URL and state directory, then runs until interrupted (`cmd/agentd/main.go`).

[Verified] The bus creates one account for each group passed to `bus.Start`. The group account has one file-backed JetStream stream with limits retention. Each initial agent has a durable pull consumer with explicit acknowledgments and two filters (`internal/core/layout/layout.go`, `internal/bus/bus.go`, `internal/bus/bus_test.go`).

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

[Verified] An agent may publish on its own broadcast, direct, operator, and event subjects only when the subject ends in its own name. It may subscribe to group broadcasts and direct messages addressed to it. The operator credential manages the group's stream and can observe its messages and events (`internal/core/perms/perms.go`). Integration tests at NATS server v2.15.0 reject cross-agent publication, another agent's direct subscription, and another group's subjects (`internal/bus/bus_test.go`, `reports/inputs/bus-26-evidence-2026-09-26.md`).

[Documented] Static nkey users are bound to an account and literal permission lists in server options. The NATS `{{name()}}` permission template applies to scoped JWT users or auth callout, not static nkey users (`experiments/00-system-assessment/nats-research.md` sections 7 and 8, `nats-server/server/auth.go` at source commit `3e8ddaa7`). User JWTs were rejected for bootstrap because they add issuer and account signing infrastructure without improving the required per-agent subject boundary. A later decision record can revisit the choice when credentials must be issued across machines.

[Untested] The phase 2 `agentctl` receive and ack path remains to be designed under the strict publication rule. Pull requests and acknowledgments use JetStream API subjects, and acknowledgments do not end in the agent's name. The current agent credentials cannot issue those requests directly. Issue #27 must use a daemon-mediated path or a separately justified permission change. The durable consumer configuration here prepares the server state, but does not claim end-to-end receive and ack behavior.
