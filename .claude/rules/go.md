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

## Linter suppression

- Go 1.27, golangci-lint 2.14.0: Suppress only a specific finding with `//nolint:name // reason`.
