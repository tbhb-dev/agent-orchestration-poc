---
title: Agent bus operations use an authenticated daemon relay
description: Why message publication, pull delivery, acknowledgments, and KV reads pass through agentd.
---

## Status

Accepted 2026-09-26 for issue #96. The operator must merge the permission change.

## Context

The first [PR #82 review](https://github.com/tbhb/agent-orchestration-poc/pull/82#pullrequestreview-5328211369) observed that `NoAck` suppresses stored and duplicate replies. The second [review](https://github.com/tbhb/agent-orchestration-poc/pull/82#pullrequestreview-5328225764) observed that a direct pull request can aim broker delivery at another agent's message subject. The server source at `nats-server` v2.15.0, commit `eb763679aa3c24a40dcd3012aa046ad1996d851c`, gates publish replies on `!NoAck` in `server/stream.go:6483-6494` and uses the pull caller's reply in `server/consumer.go:5522`. The nats.go v1.54.0 source at commit `7a8404ab9b1721cf1eddf3a26474e6925c322d73` uses a client request and waits for its reply in `jetstream/publish.go:181-275`.

## Decision

Agents publish only on their literal `grp.<group>.relay.req.<operation>.<agent>` subjects. The authenticated NATS account binds the group, and the credential's literal final token grant binds the agent. The daemon validates the entire subject and ignores payload identity. The reply is always `grp.<group>.relay.reply.<agent>.<request-id>`, under the exact agent token prefix. The client supplied NATS reply field is ignored. These namespaces are disjoint from stored messages and broker inboxes.

The agent `send` request contains the destination and a bounded JSON envelope. The daemon derives the raw message subject from the authenticated sender and scopes `Nats-Msg-Id` to that subject. It publishes through the operator connection, which constructs the broker reply address. A matching server acknowledgment with the expected stream and sequence yields `stored` or `duplicate` and the original sequence. A rejected request yields `rejected`, while a broker error or timeout yields `unknown`. The operator alone can publish to the message stream, which now returns acknowledgments.

The daemon creates each durable consumer. It fetches only the authenticated agent's consumer and returns a random delivery token held in daemon memory. The held record binds group, agent, consumer, stream sequence, and consumer delivery generation. An ack uses the held message only after all bindings match. An unknown or reused token returns `unknown-token` without an ack. Restart clears tokens, and redelivery gets a fresh token.

Status and roster reads use the operator connection. `not-provisioned` means the bucket is absent, and `not-found` means the key is absent. Issue #29 creates production buckets and writes their values. Issue #28 adds registration and must prove that a newly registered agent gets exact relay grants and can fetch and ack without widening existing grants.

## Consequences

Direct agent JetStream access is rejected because broker replies can bypass sender permissions. Auth callout could supply a different identity mechanism but does not make caller selected broker replies safe. A private inbox prefix narrows subscriptions but cannot constrain a reply aimed at a message subject. Reopen this decision only with versioned server evidence and an embedded attack test proving caller selected broker replies cannot publish to another agent's subjects or change its consumer state.

## Evidence

The [relay evidence](https://github.com/tbhb/agent-orchestration-poc/blob/feat/96-bus-relay/reports/inputs/bus-relay-evidence.md) records source versions, permission values, the embedded attack and restart suite, and local gate results. The tagged nats.go `jetstream/message.go:33-58` defines metadata and confirmed acknowledgment, and `jetstream/kv.go:39-99` defines bucket lookup and key reads.
