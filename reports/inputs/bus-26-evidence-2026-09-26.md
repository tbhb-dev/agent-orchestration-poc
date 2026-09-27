# Bus issue 26 evidence

## Versions and source

- [Verified] `go.mod` pins `github.com/nats-io/nats-server/v2 v2.15.0`, `github.com/nats-io/nats.go v1.54.0`, `github.com/nats-io/nkeys v0.4.16`, and `pgregory.net/rapid v1.3.0` (`go.mod`, `go mod verify`).
- [Observed] The server source read was `nats-io/nats-server` commit `3e8ddaa7fcdf2c6a0688f8872ca465eab08f1221`. The client source read was `nats-io/nats.go` commit `5adc9d5d34ce8e3b7b8b002c5bd502a8b7a323d3` (`git -C <clone> rev-parse HEAD`). The implemented versions are released tags, while these source commits are later snapshots.
- [Verified] The credential and authorization calls were checked in `nats-server/server/auth.go`, `server/server.go`, `server/jetstream.go`, `nats.go/nats.go`, and `nats.go/jetstream/jetstream.go` at the commits above.

## Credential decision notes

[Inference] User nkeys are the bootstrap choice. The server accepts static nkey users with an account and per-user `SubjectPermission` lists, while `nats.go` reads a user seed from a file with `NkeyOptionFromSeed`. This needs no JWT issuer or resolver (`nats-server/server/auth.go`, `nats.go/nats.go`, research sections 7 and 8).

[Inference] User JWTs were rejected for this phase. Their portable claims could support future provisioning, but they require account and user signing machinery that the one-host bootstrap does not yet need. Static nkeys still let the broker enforce the requested subjects and account boundary. The future VM path should reconsider this decision.

## Effective server configuration

[Verified] `internal/bus/bus.go` constructs `server.Options` in memory. The following is the redacted effective option set for `agentd serve --state-dir <STATE> --agent alice`. No credentials or public keys are included.

```text
Host: 127.0.0.1
Port: 4222
JetStream: true
StoreDir: <STATE>/store
NoLog: true
NoSigs: true
Accounts: [build]
Nkeys: [build/operator: <redacted>, build/alice: <redacted>]
Stream: GROUP_BUILD
Subjects: [grp.build.msg.>, grp.build.evt.>]
Storage: file
Retention: limits
Publish acknowledgments: disabled
Consumer: alice
Consumer filters: [grp.build.msg.all.*, grp.build.msg.dm.alice.*]
Consumer ack policy: explicit
Credential paths: <STATE>/credentials/build/{operator,alice}.seed
Credential file mode: 0600
```

## Permission test output

[Observed] `GOCACHE=/tmp/bus-26-go-cache GOPATH=/tmp/bus-26-gopath mise exec -- go test -v -count=1 ./internal/bus` ran on 2026-09-26. The test started the embedded server on a random IPv4 loopback port and checked server permission errors. The output contains no seeds or JWTs.

```text
=== RUN   TestPublishPermissions
=== RUN   TestPublishPermissions/alice_as_bob
=== RUN   TestPublishPermissions/bob_as_alice
=== RUN   TestPublishPermissions/other_account
--- PASS: TestPublishPermissions (0.12s)
    --- PASS: TestPublishPermissions/alice_as_bob (0.00s)
    --- PASS: TestPublishPermissions/bob_as_alice (0.00s)
    --- PASS: TestPublishPermissions/other_account (0.00s)
=== RUN   TestSubscribePermissions
=== RUN   TestSubscribePermissions/other_direct
=== RUN   TestSubscribePermissions/other_group
--- PASS: TestSubscribePermissions (0.02s)
    --- PASS: TestSubscribePermissions/other_direct (0.00s)
    --- PASS: TestSubscribePermissions/other_group (0.00s)
=== RUN   TestStreamProvisioning
--- PASS: TestStreamProvisioning (0.01s)
=== RUN   TestRestartKeepsCredentialsAndStream
--- PASS: TestRestartKeepsCredentialsAndStream (0.01s)
PASS
ok  	github.com/tbhb/agent-orchestration-poc/internal/bus	0.565s
```

## Review regressions

[Observed] Before the fix, `GOCACHE=/tmp/bus-26-go-cache GOPATH=/tmp/bus-26-gopath mise exec -- go test -run '^TestAgentCannotUseBrokerRepliesAsAnotherSender$' -count=1 -v ./internal/bus` failed for five Bob-attributed reply subjects: broadcast, direct to Alice, direct to Bob, operator, and event. Alice published an allowed broadcast with each reply subject; the operator observed a broker-generated JetStream acknowledgment under Bob's name. The payload was a stream acknowledgment, not arbitrary agent data.

[Verified] The pure `layout.Stream` value now sets `NoAck: true`, and `internal/bus/bus.go` passes it to the JetStream stream config. In the pinned nats-server v2.15.0 module source, `server/stream.go:6483,6494` gates stream replies on `!mset.cfg.NoAck`. The later server source clone inspected was commit `3e8ddaa7fcdf2c6a0688f8872ca465eab08f1221`; the client source clone was commit `5adc9d5d34ce8e3b7b8b002c5bd502a8b7a323d3`.

[Observed] After the fix, the same targeted command passed. For each of the five Bob-attributed reply subjects, Alice tried all four allowed publish patterns and 41 JetStream control, pull, ack, and snapshot routes drawn from the v2.15.0 server API subject list; no Bob-attributed publication arrived. Every tested `$JS.API.>` and `$JS.ACK.>` publication produced a permission error. The concrete route samples cover the API families in the pinned source; literal account and agent permissions exclude the entire `$JS.API.>` and `$JS.ACK.>` prefixes.

```text
--- PASS: TestAgentCannotUseBrokerRepliesAsAnotherSender (7.37s)
    --- PASS: TestAgentCannotUseBrokerRepliesAsAnotherSender/grp.build.msg.all.bob (1.47s)
    --- PASS: TestAgentCannotUseBrokerRepliesAsAnotherSender/grp.build.msg.dm.alice.bob (1.47s)
    --- PASS: TestAgentCannotUseBrokerRepliesAsAnotherSender/grp.build.msg.dm.bob.bob (1.47s)
    --- PASS: TestAgentCannotUseBrokerRepliesAsAnotherSender/grp.build.msg.op.bob (1.47s)
    --- PASS: TestAgentCannotUseBrokerRepliesAsAnotherSender/grp.build.evt.ready.bob (1.47s)
PASS
```

[Observed] The strengthened restart test published a message, pulled and acknowledged it through the operator credential, restarted the embedded server, then checked the saved payload and consumer ack floor. It passed with the intact store. A temporary Go overlay that inserted `os.RemoveAll(state + "/store")` immediately after `first.Close()` caused `TestRestartKeepsCredentialsAndStream` to fail with `nats: API error: code=404 err_code=10037 description=message not found`. The overlay lived under `/tmp` and did not change the checkout.

[Verified] `UV_CACHE_DIR=/tmp/bus-26-uv-cache GOCACHE=/tmp/bus-26-go-cache GOPATH=/tmp/bus-26-gopath GOLANGCI_LINT_CACHE=/tmp/bus-26-golangci-cache mise run check` passed after the changes, including race-enabled shuffled Go tests. The temporary cache paths were needed because the sandbox denied writes to the default user caches.

## Preliminary core mutation run

[Observed] Before PR #80 merged, the Go core was mutation tested with gremlins v0.6.0 through `mise exec -- go run github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0 unleash ./internal/core --output-statuses lct --output /tmp/bus-26-gremlins.json`. The temporary configuration matched PR #80's `.gremlins.yaml` with two workers, a timeout coefficient of 200, and score floors of 80. The run used `RAPID_NOFAILFILE=1` and `RAPID_SHRINKTIME=1s`. It covered this branch's `internal/core/layout` and `internal/core/perms` before the incoming `internal/core/subject` package exists here.

```text
Mutation testing completed in 47 seconds 971 milliseconds
Killed: 71, Lived: 0, Not covered: 0
Timed out: 0, Not viable: 0, Skipped: 0
Test efficacy: 100.00%
Mutator coverage: 100.00%
```

[Untested] `mise run check:mutation` is absent from this branch's `mise tasks ls --no-header`; no post-merge mutation run was possible without rebasing, which this review run excludes. The preliminary scores above cover only this branch's core packages.
