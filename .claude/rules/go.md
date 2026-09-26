---
paths: ["**/*.go", "go.mod", "go.sum"]
---

See [Go conventions](../../docs/src/content/docs/guides/go-conventions.md).

## Toolchain and modules

- Go 1.27.1: Run Go commands through mise or `mise run` tasks; use no global Go tools.
- Go 1.27: Set `go 1.27.0` in `go.mod`, omit `toolchain`, pin Go 1.27.1 in mise, and set `GOTOOLCHAIN=local`.
- Go 1.27: Keep one root module with binaries under `cmd/` and packages under `internal/`; commit no `go.work` or linter `tool` directives.

## Formatting and checks

- Go 1.27, gofumpt 0.12.0: Format with gofumpt without `-extra`; require an empty `gofumpt -l .` result.
- Go 1.27: Run `check`: gofumpt, `go vet ./...`, `go mod tidy -diff`, `go mod verify`, golangci-lint, `go build ./...`, and `go test -race -shuffle=on ./...`.
- Go 1.27, golangci-lint 2.14.0: Use `linters.default: standard`; let `go test` enforce `stdversion` against the `go` line.

## Code rules

- Go 1.27: Build dial addresses with `net.JoinHostPort`; compare `net.UnixConn` EOF with `errors.Is(err, io.EOF)`.
- Go 1.27: Use `encoding/json/v2` for new protocol encoding and standard `uuid` for new identifiers; do not assert JSON error strings.
- Go 1.27: Expect unbuffered timer channels and no `asynctimerchan` setting.
- Go 1.26: Use `errors.AsType[T]`, `signal.NotifyContext` with `context.Cause`, and `slog.NewMultiHandler` for logging fanout.
- Go 1.25: Use `sync.WaitGroup.Go`; let cgroup limits set daemon `GOMAXPROCS`.
- Go 1.27: Keep secrets out of `runtime/pprof` labels because tracebacks include them.

## Testing rules

- Go 1.24: Use `t.Context()` for test lifetimes; call `t.Chdir` and `t.Setenv` only in nonparallel tests; benchmark with `for b.Loop()`.
- Go 1.25: Use `synctest.Test` for internal time logic, never real I/O or subprocesses.
- Go 1.27: Put external tmux or NATS tests behind `//go:build integration` and skip when the executable is missing; keep embedded NATS tests untagged.
- Go 1.27: Use named table tests with `t.Run`, `_test.go`, `testdata/`, and Go 1.26 `t.ArtifactDir()` for captured logs.

## Core and shell

- Go 1.27, golangci-lint 2.14.0: put pure decisions and data transformations under `internal/core/<topic>`. `depguard` denies `os`, `net` except `net/netip` and `net/url`, `syscall`, NATS modules, and shell packages there.
- Go 1.27: Put side effects in `cmd/*`, `internal/bus`, `internal/registry`, `internal/backend/*`, `internal/term`, and `internal/api`. Pass values into the core, never an `io.Writer`, `*os.File`, or connection.
- Go 1.27, golangci-lint 2.14.0: fix a depguard finding by moving the I/O. Never use `//nolint:depguard`. Deny only the shortest prefix, and scope test rules with `**_test.go`.
- Go 1.27: keep core tests untagged, with values in and out and no mocks. Core tests never spawn processes or connect to a broker. Mark shell tests needing external tools with `//go:build integration`.

## Quality gates

- Go 1.27, golangci-lint 2.14.0: keep cognitive and cyclomatic complexity below 15 with `gocognit` and `gocyclo`. Keep functions within 60 lines and 40 statements with `funlen`, except in `_test.go` files. Keep nested `if` complexity below 5 with `nestif`.
- Go 1.27, golangci-lint 2.14.0: apply complexity limits to the core without exception. Quote a finding in the PR when requesting a shell exclusion. Leave `dupl`, `cyclop`, and `maintidx` disabled.
- Go 1.27, deadcode 0.50.0: every function must be reachable from a binary or a test. `check:deadcode` fails on output from `deadcode -test ./...`. Delete reported functions.
- Go 1.27, jscpd 5.3.2: move repeated blocks of at least 50 tokens and 5 lines into a shared package. Mark a deliberate repeat with `jscpd:ignore-start` and `jscpd:ignore-end` and explain why.

## Linter suppression

- Go 1.27, golangci-lint 2.14.0: Suppress only a specific finding with `//nolint:name // reason`.
