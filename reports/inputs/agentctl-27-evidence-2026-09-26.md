# agentctl relay exchange evidence

## Setup

[Observed] `mise exec -- go test -tags integration -count=1 -v ./cmd/agentctl` exited 0 in the issue #27 worktree after the branch merged `origin/main` at `734985cf312c3fa1002e33595bec3c1633f9bf6e`. `TestRelayCLIExchange` started the embedded server with two static agent credentials in the `build` group and called the CLI's `run` entry point with each agent's own credential file. The test used the versions pinned in `go.mod`: nats-server v2.15.0 and nats.go v1.54.0. The following stdout values came from the test log; the daemon-held delivery token is redacted.

```text
alice send: {"ok":true,"command":"send","result":"stored","id":"same","to":"bob","sequence":1}
alice send: {"ok":true,"command":"send","result":"duplicate","id":"same","to":"bob","sequence":1}
bob receive: {"ok":true,"command":"receive","result":"delivered","id":"<redacted>","from":"alice","sequence":1,"message":{"body":{"text":"hello"}}}
bob ack: {"ok":true,"command":"ack","result":"acked","id":"<redacted>"}
bob ack: {"ok":false,"command":"ack","result":"unknown-token","error":"unknown-token"}
bob receive: {"ok":false,"command":"receive","result":"empty"}
```

[Verified] The test checked the confirmed first send, duplicate sequence, sender attribution, body, confirmed ack, rejection of a reused token, and one-second empty timeout. The separate relay suite in `internal/bus/relay_test.go` covers redelivery, foreign tokens, and restart behavior. The CLI test calls `run` with a real embedded socket; it does not execute the built binary as a subprocess.
