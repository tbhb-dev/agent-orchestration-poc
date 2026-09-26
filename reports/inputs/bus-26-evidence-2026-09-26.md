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
