---
title: Go conventions
description: How Go is written, built, tested, and linted in this repository, at Go 1.27.1.
---

# Go conventions

## Versions and sources

This page targets Go 1.27.1 and the tools and source snapshots recorded on 2026-09-26 (research/gates/go/versions.md).

| Tool | Version | Source read |
| --- | --- | --- |
| Go, gofmt, go vet | Go 1.27.1; vet has 36 analyzers | `~/Code/github.com/golang/go` at `862c888e612ac346c7c4d99c9392bdfd265f33b0` (research/gates/go/versions.md) |
| golangci-lint | 2.14.0, aqua backend | `~/Code/github.com/golangci/golangci-lint` at `032d962e0399070bc72d32925e778deaaf2213b9`; release tag `114493f9b3e7257d29e4130f2b4a4aadefbb6845` (research/gates/go/versions.md) |
| gofumpt | 0.12.0, aqua backend | `~/Code/github.com/mvdan/gofumpt` at `3e0cc4edc39797c8ed123f4e0a60e3ad1cdcd3b0`; release tag `3e07e7e70ac93761d8e79ca0083a19e3d59f753d` (research/gates/go/versions.md) |
| staticcheck, comparison only | 2026.2.1, module v0.8.1 | `~/Code/github.com/dominikh/go-tools` at `6cb65e58a558452b52f57cb43267ff9df669a77a`; release tag `1285a6a5ec1e0ebb658f49e82b6c566a878cc3cb` (research/gates/go/versions.md) |
| Go documentation | Go 1.25–1.27 release notes and module guides | `~/Code/github.com/golang/website` at `f2661d967b28530da480f0a1da9a4279026d34ca` (research/gates/go/versions.md) |

## Modules and toolchain

Use one root module, `github.com/tbhb/agent-orchestration-poc`, with commands in `cmd/<name>/main.go` and private packages in `internal/`; Go's module layout guide uses this shape for server projects (golang/website/_content/doc/modules/layout.md; research/gates/go/notes.md §1).

Set `go 1.27.0` in `go.mod`, omit the `toolchain` line, pin the exact Go patch in `mise.toml`, and set `GOTOOLCHAIN=local` there; at Go 1.27.1, this makes a newer `go` requirement fail instead of downloading a toolchain outside mise (golang/website/_content/doc/toolchain.md; research/gates/go/notes.md §1).

Do not commit `go.work` for the single module, or use the Go 1.24 `tool` directive for linters and formatters: it puts tools into the daemon's module graph; install their binaries through mise (golang/website/_content/doc/modules/gomod-ref.md; golangci-lint/docs/content/docs/welcome/install/local.md; research/gates/go/notes.md §1).

Go 1.25 `ignore` directives can later exclude `apps/`, `docs/`, and `node_modules` from package patterns when those trees exist; `.worktrees/` is already skipped by `./...` because its name begins with a dot (golang/website/_content/doc/modules/gomod-ref.md; `go help packages`; research/gates/go/notes.md §1).

## Language and library changes that matter

- Go 1.25 adds cgroup-aware `GOMAXPROCS`, `sync.WaitGroup.Go`, the `waitgroup` and `hostport` vet analyzers, and stable `testing/synctest`; keep daemon CPU sizing automatic and use `net.JoinHostPort` for dial addresses (golang/website/_content/doc/go1.25.md; research/gates/go/notes.md §§2–3).
- Go 1.26 makes Green Tea the default collector and adds `errors.AsType[T]`, context-aware `net.Dialer.DialTCP`/`DialUDP`/`DialIP`/`DialUnix`, signal causes from `signal.NotifyContext`, `slog.NewMultiHandler`, and `testing.T.ArtifactDir` (golang/website/_content/doc/go1.26.md; research/gates/go/notes.md §2).
- Go 1.27 adds generic methods, general availability of `encoding/json/v2` with strict UTF-8 and duplicate-name handling, the standard `uuid` package, and a generally available `goroutineleak` profile; use v2 for new protocol encoding and keep secrets out of pprof labels because Go 1.27 tracebacks print them (golang/website/_content/doc/go1.27.md; research/gates/go/notes.md §2).
- Go 1.27 `net.UnixConn` reads return `io.EOF` directly, `net/http` drains unread response bodies up to a limit on `Close`, and timer channels are always unbuffered; compare Unix read errors with `errors.Is(err, io.EOF)` (golang/website/_content/doc/go1.27.md; go/doc/godebug.md; research/gates/go/notes.md §2).
- Go 1.27 `go test` enables `stdversion` vetting by default, and `go mod tidy` merges duplicate require blocks; keep the `go` line accurate and accept tidy's require-block layout (golang/website/_content/doc/go1.27.md; research/gates/go/notes.md §2).

## Formatting, vetting, and linting

Format with gofumpt 0.12.0 without `-extra`; its output is gofmt-compatible, and `gofumpt -l .` must print nothing (gofumpt/README.md; research/gates/go/notes.md §4).

Run `go vet ./...` separately: Go 1.27.1 has 36 analyzers, while `go test` runs a smaller subset; run `go mod tidy -diff` to detect changes without writing and `go mod verify` after downloading dependencies to check the module cache (Go 1.27.1 `go tool vet help`, `go help test`, `go help mod tidy`, `go help mod verify`; research/gates/go/notes.md §4).

Use golangci-lint 2.14.0 through mise with a v2 config and `linters.default: standard`, which enables `errcheck`, `govet`, `ineffassign`, `staticcheck`, and `unused`; its staticcheck integration uses the same v0.8.1 analyzer source as standalone staticcheck 2026.2.1, and golangci-lint has supported Go 1.27 since v2.13.0 (golangci-lint/pkg/lint/lintersdb/builder_linter.go; golangci-lint/pkg/golinters/staticcheck/staticcheck.go; golangci-lint/CHANGELOG.md; research/gates/go/notes.md §5).

The `check` task should run gofumpt, vet, `go mod tidy -diff`, `go mod verify`, golangci-lint, `go build ./...`, and race-enabled shuffled tests; suppress a specific finding only with `//nolint:name // reason` and a concrete reason (golangci-lint/docs/content/docs/configuration/file.md; research/gates/go/notes.md §§4–5).

## Testing

Use named table cases with `t.Run`, conventional `TestXxx` functions in `_test.go`, and fixtures under `testdata/`; Go 1.24 `t.Context()` ties work to test cleanup, while `t.Chdir` and `t.Setenv` cannot run in parallel tests (go/src/testing/testing.go; Go 1.27.1 `go help test`; research/gates/go/notes.md §3).

Use Go 1.25 `synctest.Test` for internal time and timeout logic whose goroutines stay in its bubble; real network I/O, tmux, and subprocesses do not fit its fake-clock blocking model (go/src/testing/synctest/synctest.go; research/gates/go/notes.md §3).

Guard tests needing tmux or an external NATS executable with `//go:build integration` and skip if `exec.LookPath` fails; in-process NATS tests can stay ordinary tests, subject to the bus experiment's result (Go 1.27.1 `go help buildconstraint`; research/gates/go/notes.md §3).

Run unit tests with `go test -race -shuffle=on ./...` and integration tests with `-tags integration -count=1`; store captured logs in Go 1.26 `t.ArtifactDir()` so `go test -artifacts -outputdir` can preserve them (Go 1.27.1 `go help testflag`; golang/website/_content/doc/go1.26.md; research/gates/go/notes.md §3).

## Harness rule loading

Codex loads `AGENTS.override.md`, `AGENTS.md`, or configured fallback files from the project root down to its working directory, in that priority per directory, within a default 32 KiB total budget; it has directory-scoped instructions rather than Claude Code path globs, so a Codex worker started at the root needs Go rules in root `AGENTS.md` (codex/codex-rs/core/src/agents_md.rs; codex/codex-rs/config/src/config_toml.rs; research/gates/go/notes.md §6).

agy 1.2.11 describes user and workspace Markdown rules and `rules.json` include and exclusion lists, but its help and changelog do not establish the discovery directory, path scoping, or whether it reads `AGENTS.md`; those behaviors still need testing before mirroring the Go rules (agy 1.2.11 `agy help`, `agy changelog`; research/gates/go/notes.md §6).
