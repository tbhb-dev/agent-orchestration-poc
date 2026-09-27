# Bus issue 26 evidence

## Versions and source

- [Verified] `go.mod` pins `github.com/nats-io/nats-server/v2 v2.15.0`, `github.com/nats-io/nats.go v1.54.0`, `github.com/nats-io/nkeys v0.4.16`, and `pgregory.net/rapid v1.3.0` (`go.mod`, `go mod verify`).
- [Observed] The server source read was `nats-io/nats-server` commit `3e8ddaa7fcdf2c6a0688f8872ca465eab08f1221`. The client source read was `nats-io/nats.go` commit `5adc9d5d34ce8e3b7b8b002c5bd502a8b7a323d3` (`git -C <clone> rev-parse HEAD`). The implemented versions are released tags, while these source commits are later snapshots.
- [Verified] The credential and authorization calls were checked in `nats-server/server/auth.go`, `server/server.go`, `server/jetstream.go`, `nats.go/nats.go`, and `nats.go/jetstream/jetstream.go` at the commits above.

## Credential decision notes

[Inference] User nkeys are the bootstrap choice. The server accepts static nkey users with an account and per-user `SubjectPermission` lists, while `nats.go` reads a user seed from a file with `NkeyOptionFromSeed`. This needs no JWT issuer or resolver (`nats-server/server/auth.go`, `nats.go/nats.go`, research sections 7 and 8).

[Inference] User JWTs were rejected for this phase. Their portable claims could support future provisioning, but they require account and user signing machinery that the one-host bootstrap does not yet need. Static nkeys still let the broker enforce the requested subjects and account boundary. The future VM path should reconsider this decision.

## Effective server configuration

[Verified] `internal/bus/bus.go` constructs `server.Options` in memory. The following is the redacted effective option set when `bus.Start` receives `<STATE>` and agent `alice`. No credentials or public keys are included. After issue #28 mounted the provisioner, `agentd serve --state-dir <STATE>` passes `<STATE>/bus` to `bus.Start`.

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

[Observed] After merging `origin/main` as `6711b42`, this branch has `mise run check:mutation`; the preliminary scores above cover the pre-merge core packages only. The post-merge result is recorded below.

## Relay decision raw notes

[Observed] On the merged branch, temporary failing tests run with `mise exec -- go test -run '^TestReviewProbe' -count=1 -v ./internal/bus` reproduced both open blocking findings. `TestReviewProbePublishConfirmation` used the group operator credential and a 300 ms context; `js.Publish` returned `context deadline exceeded`. `TestReviewProbeAgentPullAccess` used Alice's credential on `$JS.API.CONSUMER.MSG.NEXT.GROUP_BUILD.alice`; the server reported `Permissions Violation for Publish to "$JS.API.CONSUMER.MSG.NEXT.GROUP_BUILD.alice"`. The temporary probe file was removed after the run. These results describe the intentional bootstrap limitation, not an implemented relay.

[Observed] The `tbhbbot` second review of PR #82 reports a live probe at nats-server v2.15.0: when Alice was hypothetically granted her own `$JS.API.CONSUMER.MSG.NEXT.GROUP_BUILD.alice` route, she supplied `grp.build.msg.all.bob` as its reply subject, and the broker delivered stored content on Bob's subject without a permission error. The review cites `server/consumer.go` pull-request reply handling and `server/stream.go` `jsOutQ`. This is the same sender-attribution failure class as the earlier publish acknowledgment finding. The second review did not probe every other API route, so those routes remain unverified individually.

[Inference] The safe boundary for this bootstrap PR is to keep agents without any `$JS.API.` or `$JS.ACK.` publish grant, keep stream acknowledgments disabled, and let the operator credential alone make JetStream requests. A private inbox prefix alone does not constrain a malicious reply subject placed on a JetStream request. A broader agent grant would reopen the demonstrated pull-delivery flaw. The coordinator's [PR #82 decision](https://github.com/tbhb/agent-orchestration-poc/pull/82#issuecomment-5851224406) assigns an authenticated `agentd` relay to [issue #96](https://github.com/tbhb/agent-orchestration-poc/issues/96) and blocks #27 on it. This departs from the messaging sketch's direct agent pull-consumer path. Issue #96 owns the decision record and the tests for the mediated operations; this file provides the raw notes for that record.

[Observed] `TestAgentCannotPublishJetStreamControlSubjects` uses Alice's real credential against the embedded server and receives permission errors for stream, consumer, direct-get, generic future-shaped API, and ack subjects. This checks concrete representatives of both denied prefixes; the literal `grp.<group>...<agent>` allow list in `internal/core/perms/perms.go` excludes the entire `$JS.API.` and `$JS.ACK.` namespaces by construction. The targeted test command and result are recorded below.

```text
XDG_CACHE_HOME=/tmp/agent-26-cache GOCACHE=/tmp/agent-26-go-cache GOPATH=/tmp/agent-26-gopath mise exec -- go test -run '^TestAgentCannotPublishJetStreamControlSubjects$' -count=1 -v ./internal/bus
--- PASS: TestAgentCannotPublishJetStreamControlSubjects (0.02s)
PASS
ok github.com/tbhb/agent-orchestration-poc/internal/bus 0.382s
```

[Verified] `credential()` now clears the seed byte slice after deriving the public key, including error returns after a read. `createCredential()` clears the original slice returned by `pair.Seed()` after writing the file and returning a separate copy. The caller clears that copy. The key pair is still wiped with `pair.Wipe()` (`internal/bus/bus.go`). This is a source inspection claim; no heap-forensics test was run.

[Observed] After merging `origin/main`, `mise run check` passed with zero Go lint issues, race-enabled bus and core tests, 31 Python tests passed and one integration test skipped, zero Vale alerts, and all other required repository checks. `mise run check:mutation` passed: the Go core run killed 85 of 85 viable mutants with zero survivors, uncovered mutants, or timeouts; the Python core run killed 74 of 83 mutants for 89.16%, with 100% line coverage. The command used temporary cache paths under `/tmp` because the sandbox denied writes to default user caches.

[Observed] `mise run build` passed. `mise run docs:build` exited zero and emitted the bus page, but Chromium could not register a Mach port in this sandbox during Mermaid rendering. `mise run docs:check-links` then failed because `workflow/index.md` did not render and three existing links to `/workflow/` were reported invalid. No changed file contains those links. The docs site and links need the unsandboxed CI check before they can be called green.
