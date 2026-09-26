# agentctl issue 27 evidence

## Versions and source

- [Verified] `go.mod` pins NATS server v2.15.0, nats.go v1.54.0, and rapid v1.3.0 (`go.mod`, `mise run check:go`).
- [Observed] The NATS server source clone was `3e8ddaa7fcdf2c6a0688f8872ca465eab08f1221`, and the nats.go source clone was `5adc9d5d34ce8e3b7b8b002c5bd502a8b7a323d3` (`git -C <clone> rev-parse HEAD`). These commits follow the pinned release tags.
- [Schema] The client API calls were checked in `nats.go/jetstream/publish.go`, `pull.go`, `message.go`, and `kv.go` at that nats.go clone commit. The static nkey grants and deny behavior were checked in `nats-server/server/auth.go` at the server clone commit.

## Embedded-server permission probe

[Observed] A temporary test started `bus.Start` on a random loopback port with group `build` and agents Alice and Bob. It connected as Alice with her own credential file and called each client path. The temporary test was removed after the probe. The broker rejected these subjects under the #82 permission set (`internal/core/perms/perms.go`). Random inbox suffixes and connection numbers are redacted.

```text
send:    denied subscription _INBOX.<redacted>.*
receive: denied publication $JS.API.CONSUMER.INFO.GROUP_BUILD.alice
status:  denied publication $JS.API.STREAM.INFO.KV_status
roster:  denied publication $JS.API.STREAM.INFO.KV_roster
All four client calls returned context deadline exceeded.
```

[Inference] A successful fetch also needs publication to `$JS.API.CONSUMER.MSG.NEXT.GROUP_BUILD.<agent>` and subscription to a reply inbox. Acknowledgment publishes to `$JS.ACK.GROUP_BUILD.<agent>.>`. Status and roster creation and writes need their bucket API subjects and per-agent `$KV.status.<agent>` and `$KV.roster.<agent>` publications. These requirements follow the nats.go calls in `jetstream/pull.go`, `message.go`, and `kv.go`. They were not reached by the probe because the first API request was denied.

## Two-agent CLI attempt

[Observed] `mise run build` built both binaries. `agentd serve --state-dir <redacted> --port 39427 --agent alice --agent bob` reported a listener on `nats://127.0.0.1:39427`. Alice and Bob each used only their own credential file path. The failed exchange below is the exact result after redacting the temporary directory, inbox suffix, and connection numbers. No credential contents were captured.

```text
alice$ agentctl send bob 'hello from alice' --id sample-27b
{"ok":false,"command":"send","error":"bus: nats: permissions violation: Permissions Violation for Subscription to \"_INBOX.<redacted>.*\""}
stderr: bus: nats: permissions violation: Permissions Violation for Subscription to "_INBOX.<redacted>.*"
exit 1

bob$ agentctl receive --timeout 1
{"ok":false,"command":"receive","error":"bus: nats: permissions violation: Permissions Violation for Subscription to \"_INBOX.<redacted>.*\""}
stderr: bus: nats: permissions violation: Permissions Violation for Subscription to "_INBOX.<redacted>.*"
exit 1
```

[Observed] A successful two-agent exchange could not be recorded with these per-agent credentials. This remains the acceptance blocker for #27. The broker must supply a reviewed mediation path or grant the required JetStream and bucket subjects without allowing an agent to consume another agent's inbox or write another agent's keys.

## Tests and output format

[Verified] `GOCACHE=/tmp/agentctl-27-go-cache GOPATH=/tmp/agentctl-27-gopath GOLANGCI_LINT_CACHE=/tmp/agentctl-27-lint-cache mise run check:go` passed after formatting. It ran formatting, vet, tidy diff, module verification, golangci-lint, build, and race-enabled shuffled tests. The core package results were:

```text
ok  internal/core/command
ok  internal/core/envelope
ok  internal/core/layout
ok  internal/core/perms
ok  internal/core/render
ok  internal/core/state
```

[Observed] `mise exec -- go test -tags integration -run TestSendReceiveAckAndDedup -count=1 ./internal/bus/client` failed at the first send with a denied `_INBOX.<redacted>.*` subscription and `context deadline exceeded`. The tagged suite also contains redelivery, timeout, concurrent send and receive, join, status, and roster cases. Those cases remain unverified against agent credentials until #82 resolves the permission gap.

[Verified] `agentctl --help` documents one JSON object per stdout line, a short stderr summary, and exit codes 0 for success, 1 for bus errors, 2 for usage errors, and 3 for no message before timeout (`cmd/agentctl/main.go`). The following format examples are illustrative values from the stable renderer schema (`internal/core/render/render.go`).

```json
{"ok":true,"command":"send","id":"example-id","to":"bob"}
{"ok":true,"command":"receive","id":"$JS.ACK.GROUP_BUILD.bob.EXAMPLE","from":"alice","message":{"body":{"text":"hello"},"headers":{"id":"example-id","kind":"message","timestamp":"2026-09-26T00:00:00Z"}}}
{"ok":false,"command":"receive","error":"no message before timeout"}
```

[Observed] `./bin/agentctl send` returned exit 2, stdout `{"ok":false,"command":"usage","error":"send requires <to> <text>"}`, and the short stderr summary `send requires <to> <text>`.

## Ownership for issue 29

[Inference] Issue #29 should take over creation and lifecycle of the `status` and `roster` key-value buckets, including their access policy, roster schema, status schema, and retention. This PR creates the buckets only when absent so `agentctl` can operate before #29. No files owned by #82 were changed.

## Documentation checks

[Observed] `mise run docs:build` emitted `/guides/agentctl/` and exited zero. Playwright Chromium could not start inside the sandbox because macOS denied `MachPortRendezvousServer` registration. Mermaid rendering therefore lacks a local visual check.

[Observed] `mise run docs:check-links` reported three existing invalid links in `docs/src/content/docs/index.md`, `docs/src/content/docs/project/history.md`, and `docs/src/content/docs/workflow/tooling.md`. It reported no link in the new `agentctl` page. Those unrelated pages were left untouched.
