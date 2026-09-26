# Go 1.27 research gate: raw notes

Recorded 2026-09-26 for issue #4, with the linter comparison that issue #14 decides from. Every claim carries an evidence label from the standing rules (verified, observed, help-text, schema, documented, inference, untested) and either a clone path at the SHA recorded in `versions.md` or a command run from the worktree with its output. Go ran through mise from the worktree (`mise exec -- go version` printed `go version go1.27.1 darwin/arm64`, GOROOT `/Users/tony/.local/share/mise/installs/go/1.27.1`, `GOTOOLCHAIN=auto`). Codex writes the conventions page and `.claude/rules/go.md` from these notes; this file is not either of those.

Clone shorthand used below: `website` is `~/Code/github.com/golang/website` at `f2661d967b28530da480f0a1da9a4279026d34ca`, `go` is `~/Code/github.com/golang/go` checked out at tag `go1.27.1` (`862c888e612ac346c7c4d99c9392bdfd265f33b0`), `go-tools` is `~/Code/github.com/dominikh/go-tools` at `6cb65e58a558452b52f57cb43267ff9df669a77a` (tag `v0.8.1` is `1285a6a5ec1e0ebb658f49e82b6c566a878cc3cb`), `golangci-lint` is `~/Code/github.com/golangci/golangci-lint` at `032d962e0399070bc72d32925e778deaaf2213b9` (tag `v2.14.0` is `114493f9b3e7257d29e4130f2b4a4aadefbb6845`), `gofumpt` is `~/Code/github.com/mvdan/gofumpt` at `3e0cc4edc39797c8ed123f4e0a60e3ad1cdcd3b0` (tag `v0.12.0` is `3e07e7e70ac93761d8e79ca0083a19e3d59f753d`), and `codex` is `~/Code/github.com/openai/codex` at `a6bd19261c30ce0a0225fe90e646822d29916f11`.

## 1. Modules

### Layout for one root module with several binaries

- Documented: the module layout guide's "Packages and commands in the same repository" and "Server project" sections put every binary under `cmd/<name>/main.go` and every non-exported package under `internal/`, with one `go.mod` at the repository root (`website/_content/doc/modules/layout.md` lines 184 to 270). That is exactly the `PLAN.md` layout (`cmd/agentd`, `cmd/agentctl`, `internal/`), so nothing in the plan departs from the official guidance.
- Documented: `go install github.com/tbhb/agent-orchestration-poc/cmd/agentd@latest` is the install form for a binary in a mixed repository (same file, lines 246 to 250).
- Help-text: `./...` skips files and directories whose names begin with `_` or `.`, directories that contain their own `go.mod`, and directories matched by an `ignore` directive (`mise exec -- go help packages`, lines 40 to 42 of the output), so `.worktrees/` never leaks into `go build ./...` or `go test ./...` from the repository root.
- Documented: the `ignore` directive (Go 1.25) excludes directories from package patterns while keeping them in the module zip; `ignore ./apps` and `ignore ./docs` style entries only take effect in the main module (`website/_content/doc/modules/gomod-ref.md` lines 671 to 730; `website/_content/doc/go1.25.md` lines 41 to 45). Inference: worth adding for `apps/`, `docs/`, and `node_modules` once the frontend exists so `./...` stays fast and `gofumpt`, which also obeys `ignore`, skips them (`gofumpt/README.md` lines 24 to 26).

### The `go` directive at 1.27

- Documented: since Go 1.21 the `go` line is a mandatory minimum, toolchains refuse to load a module that declares a newer version, and a module's `go` line must be at least the `go` line of every required module (`website/_content/doc/modules/gomod-ref.md` lines 160 to 214; `website/_content/doc/toolchain.md` lines 122 to 160).
- Documented: the `go` line sets the language version the compiler enforces, and a `//go:build go1.NN` constraint can raise it per file (`toolchain.md` lines 150 to 160).
- Observed: with `go 1.28.0` in `go.mod` and `GOTOOLCHAIN=local`, `mise exec -- go build ./...` fails with `go: go.mod requires go >= 1.28.0 (running go 1.27.1; GOTOOLCHAIN=local)`.
- Observed: `go mod init` under go1.27.1 wrote `go 1.27.1`. Verified in source: `CreateModFile` calls `addGoStmt(modFile, ..., gover.Local())` (`go/src/cmd/go/internal/modload/init.go` line 1214), so at 1.27.1 the default is the running toolchain's full version. The Go 1.26 release note said `go mod init` would default to `1.(N-1).0` (`website/_content/doc/go1.26.md` lines 98 to 108); that behaviour is not what 1.27.1 does, so do not rely on the note.
- Documented: for modules at `go 1.27` or later, `go mod tidy` merges duplicate `require` blocks into at most two, one direct and one indirect (`website/_content/doc/go1.27.md` lines 113 to 132).
- Inference: write `go 1.27.0` (the release family, patch `.0`) rather than `go 1.27.1`, so a patch bump of the mise pin never forces a `go.mod` edit and so contributors on 1.27.0 are not refused. Pin the exact patch in `mise.toml`, not in `go.mod`.

### The `toolchain` directive and switching under mise

- Documented: `toolchain goV` is a suggestion that only takes effect when the module is the main module and the default toolchain is older than `V`; a missing line is treated as `toolchain go<go line>`; `toolchain default` disables switching (`gomod-ref.md` lines 219 to 251; `toolchain.md` lines 133 to 145 and 216 to 271).
- Documented: `GOTOOLCHAIN` comes from the environment, then `go env -w`, then `$GOROOT/go.env`; the standard distribution ships `GOTOOLCHAIN=auto` (`toolchain.md` lines 191 to 214). Observed: the mise-installed GOROOT's `go.env` contains `GOTOOLCHAIN=auto` and `mise exec -- go env GOTOOLCHAIN` prints `auto`.
- Documented: under `auto`, when `go.mod` names a newer `toolchain` or `go` line, the `go` command first searches `$PATH` for a binary named `go1.NN.P`, then downloads `golang.org/toolchain@v0.0.1-go1.NN.P.darwin-arm64` into the module cache with checksum-database verification; `GOSUMDB=off` makes that download fail; `path` disables the download (`toolchain.md` lines 216 to 271 and 355 to 370).
- Observed: with `toolchain go1.27.2` (no such release yet) and `GOPROXY=off`, `mise exec -- go version` printed `go: downloading go1.27.2 (darwin/arm64)` then `toolchain not available`. With `GOTOOLCHAIN=local` the same file ran the installed 1.27.1 silently.
- Observed: with `go 1.26.0` plus `toolchain go1.27.1`, build and `go mod tidy` both left the line in place; with `go 1.27.0` plus `toolchain go1.27.0`, `go build` reported `updates to go.mod needed` and `go mod tidy` removed the redundant line.
- Observed: `GODEBUG=toolchaintrace=1 mise exec -- go version` with a plain `go 1.27.0` line prints `go: using local toolchain go1.27.1`.
- Inference: a toolchain download bypasses mise. It lands in `GOMODCACHE`, not in `~/.local/share/mise/installs/go`, so the repository would silently run a Go that `mise.toml` never pinned. The safe shape is: no `toolchain` line in `go.mod`, `go 1.27.0`, and `GOTOOLCHAIN=local` set in the `[env]` table of `mise.toml` so a mismatch fails loudly with the message observed above instead of downloading. Moving the Go pin then means editing `mise.toml` (and `go.mod` only for a new minor).
- Documented: Go 1.25 stopped adding a `toolchain` line whenever the `go` command updates the `go` line (`go1.25.md` lines 74 to 76), so `go get` on a dependency with a newer `go` line updates `go` only.

### The `tool` directive versus mise

- Documented: since Go 1.24 `tool <package>` in `go.mod` plus a `require` makes `go tool <name>` build and run the tool from the module's own graph; `go get -tool pkg@v` adds it; the `tool` meta-pattern matches those packages (`gomod-ref.md` lines 349 to 394; `website/_content/doc/go1.24.md` lines 33 to 45; `mise exec -- go help tool` and `go help get`).
- Documented: tools "are built using the same module graph as the module itself" and `replace` and `exclude` apply to them (`gomod-ref.md` lines 386 to 391). Inference: a linter pinned this way drags its dependency graph into the daemon's `go.mod` and `go.sum`, and a `go get -u` on the daemon can move the linter's dependencies.
- Documented: golangci-lint's install page warns that `go install`, the tools pattern, and `tool` directive installs "aren't guaranteed to work" and recommends binary installation, giving the shared-dependency problem as reason 3 (`golangci-lint/docs/content/docs/welcome/install/local.md` lines 116 to 124).
- Observed: mise carries both linters and the formatter as binary backends: `mise registry` lists `staticcheck` as `aqua:dominikh/go-tools/staticcheck`, `golangci-lint` as `aqua:golangci/golangci-lint`, `gofumpt` as `aqua:mvdan/gofumpt`, and `revive` as `aqua:mgechev/revive`. `mise ls-remote` shows `staticcheck` up to `2026.2.1`, `golangci-lint` up to `2.14.0`, `gofumpt` up to `0.12.0`.
- Inference: install linters and formatters through mise (matching the standing rule "mise for everything") and keep the `tool` directive for a later code generator that is already a library dependency, if one appears. Nothing in phase 1 needs the `tool` directive.

### `go work`

- Help-text: a `go.work` file names several local modules as root modules; workspaces exist for multi-module development (`mise exec -- go help work`). Documented: in workspace mode `go tool` runs tools declared in any workspace module (`gomod-ref.md` lines 381 to 385), and the `work` package pattern (Go 1.25) matches the work modules (`go1.25.md` lines 63 to 65).
- Inference: with one root module there is nothing for `go work` to join. Do not commit a `go.work`; if a phase 3 experiment needs a throwaway module next to the root one, `go.work` stays local and gitignored (`go.work` and `go.work.sum`).

## 2. What changed in Go 1.25, 1.26, and 1.27

Source for this section unless stated otherwise: `website/_content/doc/go1.25.md`, `go1.26.md`, and `go1.27.md`, and `go/doc/godebug.md` (the same file ships in the mise GOROOT at `doc/godebug.md`).

### Language

- Documented: Go 1.25 has no language changes (`go1.25.md` lines 16 to 23).
- Documented: Go 1.26 lets `new` take an expression (`new(yearsSince(born))` for optional pointer fields) and allows a generic type to refer to itself in its own constraint (`go1.26.md` lines 16 to 70).
- Documented: Go 1.27 adds generic methods (a method may declare its own type parameters; interface methods may not, and generic methods cannot implement interface methods), allows any field selector as a struct literal key, and generalises function type inference when a generic function is assigned or converted to a matching function type (`go1.27.md` lines 17 to 43).
- Observed: staticcheck 2026.2 and golangci-lint v2.13.0 both state support for the 1.27 language additions (`go-tools/website/content/changes/2026.2.md` lines 6 to 12; `golangci-lint/CHANGELOG.md` line 65).

### Go command and vet

- Documented (1.25): `go vet` gained `waitgroup` (misplaced `WaitGroup.Add`) and `hostport` (`fmt.Sprintf("%s:%d")` addresses that break IPv6; use `net.JoinHostPort`) (`go1.25.md` lines 78 to 92). Observed: `go vet ./...` on the trial module flagged exactly that Sprintf: `address format "%s:%d" does not work with IPv6`.
- Documented (1.26): `go fix` is now the home of modernizers built on the same analysis framework as `go vet`; `go tool doc` and `cmd/doc` were deleted in favour of `go doc` (`go1.26.md` lines 72 to 113).
- Documented (1.27): `go test` now runs the `stdversion` vet check by default, so a symbol newer than the `go` line fails the test build; `go test -json` output lines gain `OutputType`; `go doc pkg@version` and `go doc -ex`; `go fix` gained `atomictypes`, `embedlit`, `slicesbackward`, `unsafefuncs`, dropped `fmtappendf`, and renamed `waitgroup` to `waitgroupgo`; `go mod tidy` merges require blocks; `bzr` support removed (`go1.27.md` lines 53 to 132).
- Documented (1.27): the `go` command accepts a removed `GODEBUG` setting in `go.mod` or `//go:debug` only at its final default value and fails otherwise (`go1.27.md` lines 60 to 72).
- Observed: `mise exec -- go tool vet help` at 1.27.1 lists 36 analyzers: appends, asmdecl, assign, atomic, bools, buildtag, cgocall, composites, copylocks, defers, directive, errorsas, framepointer, hostport, httpresponse, ifaceassert, loopclosure, lostcancel, nilfunc, printf, shift, sigchanyzer, slog, stdmethods, stdversion, stringintconv, structtag, testinggoroutine, tests, timeformat, unmarshal, unreachable, unsafeptr, unusedresult, waitgroup. All run by default.
- Help-text: `go test` itself runs only the high-confidence subset atomic, bools, buildtag, directive, errorsas, ifaceassert, nilfunc, printf, stdversion, stringintconv, tests (`mise exec -- go help test`), which is why a separate `go vet ./...` step belongs in `check`.

### Runtime and garbage collector

- Documented (1.25): `GOMAXPROCS` defaults to the cgroup CPU bandwidth limit on Linux and is updated periodically on every OS; setting `GOMAXPROCS` manually or `GODEBUG=containermaxprocs=0,updatemaxprocs=0` disables that (`go1.25.md` lines 96 to 121). Inference: this matters for `agentd` inside the Apple `container` guest, where a CPU limit may apply.
- Documented (1.25): the Green Tea collector shipped as `GOEXPERIMENT=greenteagc`; `runtime/trace.FlightRecorder` records a ring buffer trace for post-hoc snapshots; repanicked panics print `[recovered, repanicked]` once; Linux anonymous mappings get `[anon: Go: ...]` names, `GODEBUG=decoratemappings=0` disables (`go1.25.md` lines 123 to 189).
- Documented (1.26): Green Tea is the default collector, opt-out `GOEXPERIMENT=nogreenteagc` was expected to be removed in 1.27; cgo call overhead down about 30 percent; heap base address randomised on 64-bit, opt-out `GOEXPERIMENT=norandomizedheapbase64`; goroutine leak profile shipped as an experiment (`go1.26.md` lines 121 to 245).
- Documented (1.27): the `goroutineleak` profile is generally available in `runtime/pprof` and at `/debug/pprof/goroutineleak`; size-specialised allocation routines cut small allocations by up to 30 percent, opt-out `GOEXPERIMENT=nosizespecializedmalloc` until 1.28; tracebacks in modules at `go 1.27` include `runtime/pprof` goroutine labels, `GODEBUG=tracebacklabels=0` disables; the `asynctimerchan` setting is gone and timer channels are always unbuffered (`go1.27.md` lines 145 to 208; `go/doc/godebug.md` lines 157 to 197).
- Documented (godebug history): Go 1.26 added `httpcookiemaxnum=3000`, `urlmaxqueryparams=10000`, `urlstrictcolons=1`, `cryptocustomrand=0`; Go 1.27 removed `gotypesalias`, `tlsunsafeekm`, `tlsrsakex`, `tls3des`, `tls10server`, `x509keypairleaf`, `asynctimerchan`, and added `htmlmetacontenturlescape`, `x509sslcertoverrideplatform`, `fips140ems` (`go/doc/godebug.md` lines 157 to 234).
- Inference: for a daemon the two settings to remember are `tracebacklabels` (goroutine labels show up in crash output, so never put secrets in pprof labels) and the always-synchronous timer channels (a `time.After` in a `select` no longer buffers a stale tick).

### Standard library

- Documented (1.25): `testing/synctest` is generally available with `synctest.Test` and `synctest.Wait`; `encoding/json/v2` and `encoding/json/jsontext` shipped behind `GOEXPERIMENT=jsonv2`; `sync.WaitGroup.Go`; `testing.T.Attr`, `T.Output`, and `AllocsPerRun` panicking under parallel tests; `log/slog.GroupAttrs` and `Record.Source`; `os.Root` gained Chmod, Chown, Chtimes, Lchown, Link, MkdirAll, ReadFile, Readlink, RemoveAll, Rename, Symlink, WriteFile; `os.DirFS` and `Root.FS` implement `io/fs.ReadLinkFS`; `net.LookupMX` keeps IP-shaped names (`go1.25.md` lines 264 to 319, 498 to 574, 621 to 653).
- Documented (1.26): `errors.AsType[T]` generic version of `errors.As`; `fmt.Errorf` on plain strings allocates like `errors.New`; `io.ReadAll` about twice as fast; `log/slog.NewMultiHandler`; `net.Dialer.DialTCP`, `DialUDP`, `DialIP`, `DialUnix` with context; `os.Process.WithHandle` (pidfd on Linux 5.4 or later); `os/signal.NotifyContext` cancels with a cause naming the signal; `testing.T.ArtifactDir` with `go test -artifacts`; `B.Loop` no longer blocks inlining; `testing/cryptotest.SetGlobalRandom`; `reflect` field and method iterators; new `/sched/goroutines*` runtime metrics (`go1.26.md` lines 501 to 705).
- Documented (1.27): `encoding/json/v2` and `encoding/json/jsontext` are generally available, `encoding/json` v1 is now backed by the v2 implementation with preserved behaviour but possibly different error text, `GOEXPERIMENT=nojsonv2` restores the old code, and v2 rejects invalid UTF-8 and duplicate object names by default; several v2 options were removed or renamed during the experiment (`format` and `unknown` tag options, `DiscardUnknownMembers`, `SkipFunc`; `inline` renamed to `embed`) (`go1.27.md` lines 249 to 312).
- Documented (1.27): `net.UnixConn` read methods return `io.EOF` directly instead of wrapped in `net.OpError` (`go1.27.md` lines 573 to 577). Inference: this is the one change most likely to bite `agentd`, which speaks over Unix sockets; compare with `errors.Is(err, io.EOF)` and never with a type assertion on `*net.OpError`.
- Documented (1.27): `net/http` `Response.Body.Close` drains unread content up to a limit; HTTP/2 server honours RFC 9218 client priority (`Server.DisableClientPriority` to opt out); `Server.MaxHeaderValueCount`; `httptest.NewTestServer` builds a server on an in-memory network for `synctest`; `net/url.URL.Clone` and `Values.Clone`; `strings.CutLast`; `testing/synctest.Sleep` combines `time.Sleep` and `Wait`; new `uuid` package; new `crypto/mldsa`; `math/rand/v2.Rand.N` generic method; Unicode 17 (`go1.27.md` lines 314 to 332, 565 to 668).
- Documented: no `os` or `log/slog` changes are listed for 1.27 (heading list of `go1.27.md` lines 370 to 668).
- Inference for JSON: new code in this repository should import `encoding/json/v2` for the daemon's protocol encoding, since it is generally available at the pinned toolchain and its strict defaults (reject duplicate names, reject invalid UTF-8) are what a protocol wants. Existing v1 call sites keep working. Tests that assert on `encoding/json` error strings are fragile across 1.26 and 1.27.
- Inference for the `uuid` package: use the standard library `uuid` (1.27) rather than `github.com/google/uuid` for new identifiers.

## 3. Testing conventions

- Documented (source): `T.Context` returns a context cancelled just before `Cleanup` functions run (`go/src/testing/testing.go` lines 1737 to 1742; added in Go 1.24, `go1.24.md` line 784).
- Documented (source): `T.Chdir` calls `os.Chdir`, restores it in `Cleanup`, sets `PWD` on Unix, and cannot be used in parallel tests or tests with parallel ancestors (`go/src/testing/testing.go` lines 1695 to 1701 and 2010 to 2016). `Setenv` carries the same parallel restriction (lines 2004 to 2008).
- Documented (source): `for b.Loop() { ... }` resets the timer on first call, stops it on exit, keeps call arguments and results alive, requires the condition to be written exactly `b.Loop()`, and must not be mixed with a `b.N` loop (`go/src/testing/benchmark.go` lines 480 to 502; inlining fix in 1.26, `go1.26.md` lines 682 to 690).
- Documented (source): `synctest.Test(t, func(t *testing.T))` runs a bubble with a fake clock starting at 2000-01-01 UTC; time advances only when every goroutine is durably blocked; `Wait` blocks until all others are durably blocked; channel, timer, and ticker operations on bubbled objects from outside the bubble panic; a package-level `var wg sync.WaitGroup` cannot join a bubble; mutex locking, I/O, and syscalls are not durably blocking; guidelines say avoid the network, external processes, and goroutines not started in the bubble (`go/src/testing/synctest/synctest.go` lines 1 to 140). Inference: `synctest` fits the registry, lease, and timeout logic in `internal/`, not the tmux or NATS integration paths.
- Documented: `T.Attr` and `T.Output` (1.25) and `T.ArtifactDir` (1.26) exist for structured test logs and output files (`go1.25.md` lines 626 to 652; `go1.26.md` lines 662 to 681). Inference: `ArtifactDir` is the right home for captured tmux panes or NATS logs in an integration test, since `go test -artifacts -outputdir` keeps them.
- Documented (source): test functions are `func TestXxx(*testing.T)` where `Xxx` does not start with a lowercase letter; benchmarks `BenchmarkXxx(*testing.B)` (`go/src/testing/testing.go` lines 9 to 17 and 64). Help-text: `_test.go` files, a `_test` package suffix for external tests, `testdata` ignored by the go tool, and files starting with `_` or `.` ignored (`mise exec -- go help test`).
- Documented: the `tests` vet analyzer (in the `go test` default subset) reports malformed test names and signatures (`go help test`; vet list above).
- Help-text: `-race` is supported on darwin/arm64 and linux/arm64 (`mise exec -- go help build` lines 48 to 52); `-shuffle on` seeds from the clock, `-shuffle N` fixes the seed, and the seed is printed so a failure can be replayed; `-count=1` disables test caching; `-parallel n` caps `t.Parallel` tests; `-failfast`; `-timeout` defaults to 10m; `-artifacts` (`mise exec -- go help testflag`).
- Inference on table tests: the idiom is a slice of named cases and `t.Run(tc.name, ...)` subtests. Because `T.Chdir` and `Setenv` refuse parallel tests, a table test that touches the working directory or environment cannot call `t.Parallel()` in its subtests.
- Inference on integration tests that need tmux or a NATS server: keep them in the package they exercise as `*_test.go` files guarded by `//go:build integration` (build constraints, `mise exec -- go help buildconstraint`), and skip at runtime with `t.Skip` when `exec.LookPath("tmux")` fails so a developer without tmux still gets a green unit run. A NATS server embedded in-process (the PLAN assumption the phase 2 bus experiments verify) needs no tag and no external binary, so bus tests can be ordinary unit tests using `t.Context()` for lifetime. `mise run test` runs `go test -race -shuffle=on ./...`; `mise run test-integration` adds `-tags integration -count=1`. Tests that spawn processes must not use `synctest`.

## 4. Formatting and vetting

- Observed: `gofmt` ships in the mise GOROOT and `mise exec -- gofmt -l .` on the trial module listed nothing.
- Documented: gofumpt "enforces a stricter format than gofmt, while being backwards compatible": it accepts a subset of what gofmt accepts, running gofmt afterwards changes nothing, v0.12.0 is a fork of gofmt as of Go 1.27.0 and requires Go 1.26 or later, it vendors `go/printer` so output does not depend on the local Go version, `-s` is always on, `-r` is removed in favour of `gofmt -r`, and `-extra` enables three optional rules (`gofumpt/README.md` lines 1 to 31, 41 to 525, 682 to 692). The flags are `-l`, `-w`, `-d`, `-e`, `-lang`, `-modpath`, `-extra`, `-version` (`gofumpt/gofmt.go` lines 50 to 74).
- Observed: `mise exec gofumpt@0.12.0 -- gofumpt -version` prints `v0.12.0 (go1.27.1)`. On a fixture with unsorted imports, a blank line after `func f() {`, and `var a = 0o10`, `gofmt -d` only sorted the imports while `gofumpt -d` also split standard imports into their own group, removed the blank lines at the start and end of the body, and rewrote `var a = 0o10` as `a := 0o10`.
- Observed: golangci-lint v2.14.0 bundles `gofumpt` 0.12.0 as a formatter (`golangci-lint/CHANGELOG.md` line 20; `.golangci.reference.yml` lines 4739 to 4748 list `gci`, `gofmt`, `gofumpt`, `goimports`, `golines`, `swaggo`).
- Inference: adopt gofumpt as the formatter (`gofumpt -l` in `check`, `gofumpt -w` in `fmt`), pinned in `mise.toml` at `0.12.0`. Its output is gofmt-clean, so editors running plain gofmt on save never fight it, and the stricter rules remove a class of style nits from review. Do not enable `-extra`.
- Help-text: `go vet ./...` runs all 36 analyzers (`go tool vet help`: "By default all analyzers are run"), a superset of what `go test` runs, and it is the only place `hostport`, `lostcancel`, `sigchanyzer`, `slog`, `waitgroup`, `copylocks`, `unusedresult`, and `httpresponse` run without a third-party linter.
- Help-text: `go mod tidy -diff` prints the changes as a unified diff without writing and exits non-zero when the diff is not empty; `go mod verify` checks the downloaded module cache against `go.sum` and exits non-zero on modification (`mise exec -- go help mod tidy`, `go help mod verify`). Observed: `go mod tidy -diff` on the tidy trial module printed nothing and exited 0.
- Inference for `check`: `gofumpt -l .` (fail on output), `go vet ./...`, `go mod tidy -diff`, `go mod verify`, the chosen linter, then `go build ./...` and `go test -race -shuffle=on ./...`. `go mod verify` needs the module cache populated, so CI runs it after `go mod download`.

## 5. Linter comparison for #14

### Versions and support

| Item | staticcheck | golangci-lint |
| --- | --- | --- |
| Latest release read | `2026.2.1`, module `v0.8.1`, tagged 2026-08-21 (`go-tools` tag `v0.8.1`; `staticcheck -version` prints `staticcheck 2026.2.1 (0.8.1)`, built with go1.27.0) | `v2.14.0`, tagged 2026-09-24 (`golangci-lint version` prints `2.14.0 built with go1.27.0 from 114493f9`) |
| mise backend | `aqua:dominikh/go-tools/staticcheck` (prebuilt binary; also `go:honnef.co/go/tools/cmd/staticcheck`) | `aqua:golangci/golangci-lint` (prebuilt binary, GitHub artifact attestation verified during install) |
| mise pin syntax | `staticcheck = "2026.2.1"` | `golangci-lint = "2.14.0"` |
| Go 1.27 support | 2026.2 "Added support for Go 1.27": deprecation database and both new language features (`go-tools/website/content/changes/2026.2.md` lines 6 to 12); version mismatch check ignores patch level since 2026.1 (`2026.1.md` lines 13 to 16) | v2.13.0 (2026-08-19) "go1.27 support" (`CHANGELOG.md` lines 61 to 65); `go.mod` minimum is latest minus one, currently `go 1.26.0` (`golangci-lint/go.mod` lines 1 to 6) |
| Minimum Go to run | binary release, no local Go needed to run; module says `go 1.26.0` | binary release; module says `go 1.26.0` |

Evidence labels: the mise rows are observed (`mise registry`, `mise ls-remote`, and the install logs from `mise exec staticcheck@2026.2.1` and `mise exec golangci-lint@2.14.0`); the rest is documented at the clone paths shown.

### Rule coverage

- Verified (source): golangci-lint's `staticcheck` linter concatenates `staticcheck.Analyzers`, `stylecheck.Analyzers`, `simple.Analyzers`, and `quickfix.Analyzers` from `honnef.co/go/tools` and applies a staticcheck config whose default is `["all", "-ST1000", "-ST1003", "-ST1016", "-ST1020", "-ST1021", "-ST1022"]` (`golangci-lint/pkg/golinters/staticcheck/staticcheck.go` lines 28 to 72). Its `go.mod` requires `honnef.co/go/tools v0.8.1` (line 157), the same code as staticcheck 2026.2.1.
- Verified (source): the standalone `staticcheck` command defaults to `all` minus checks marked `NonDefault` (`go-tools/lintcmd/cmd.go` lines 330 to 337); the only `NonDefault` checks in the tree are `SA9003` (empty branch) and `ST1016` (`grep NonDefault` over `staticcheck`, `simple`, `stylecheck`, `quickfix`). The standalone binary does not run the `QF` quickfix analyzers at all; they are gopls-facing. Counts at v0.8.1: 96 `SA`, 35 `S`, 18 `ST`, 12 `QF` check directories.
- Verified (source): golangci-lint's `standard` default group is exactly `errcheck`, `govet`, `ineffassign`, `staticcheck`, `unused` (`golangci-lint/pkg/lint/lintersdb/builder_linter.go` lines 231, 433, 460, 634, 698, each tagged `WithGroups(config.GroupStandard)`). Observed: `golangci-lint help linters` prints those five under "Enabled by default linters" and lists 115 linters in total.
- Verified (source): `gosec` (since v1.0.0) and `revive` (since v1.37.0) are available but not in the default group (`builder_linter.go` lines 423 and 607). `revive` 1.17.0 and `gosec` 2.29.0 are the bundled versions at v2.14.0 (`CHANGELOG.md` lines 20 to 25). `unused` in golangci-lint is staticcheck's `U1000` run as its own linter.
- Documented: golangci-lint's `govet` runs the x/tools analyzers plus extras such as `inline`, and can enable `atomicalign`, `fieldalignment`, and others that `go vet` does not ship (`.golangci.reference.yml` lines 1901 to 1931).
- Observed on the trial module (`internal/svc/svc.go` seeded with a deprecated `io/ioutil` import, `defer Start()` where `Start` returns a func, an unchecked `f.Close()`, an empty `if err != nil {}` branch, a `%s:%d` dial address, `strings.Replace(..., -1)`, and an unused function):
  - `go vet ./...`: one finding, `hostport`.
  - `staticcheck ./...` (defaults): three findings, `SA1019`, `SA9010`, `U1000`.
  - `staticcheck -checks all ./...`: adds `SA9003`; still no finding for the unchecked `Close`.
  - `golangci-lint run ./...` with no config: eight findings, `errcheck` on `f.Close()`, `govet` `hostport` and `inline`, `staticcheck` `SA1019`, `SA9010`, `SA9003`, `QF1004`, and `unused`.
- Inference: the unchecked `Close` is the daemon bug class that matters most (a dropped write or close error on a socket or a state file), and only golangci-lint's `errcheck` reports it. staticcheck alone never will; its `SA` set has no unchecked-error check by design.

### Speed

- Observed on the trial module (two packages, macOS arm64, wall clock from `/usr/bin/time -p` around `mise exec`): staticcheck cold 0.85 s, warm 0.13 s; golangci-lint cold 2.46 s, warm 0.29 s. Both cache to the user cache directory (golangci-lint documents `GOLANGCI_LINT_CACHE`, `golangci-lint/docs/content/docs/configuration/cli.md` lines 61 to 67; staticcheck 2026.2 added `GOCACHEPROG` support, `2026.2.md` lines 13 to 17).
- Inference: the difference is the extra linters and process startup, and on a repository of this size neither number matters against `go test -race`.

### Configuration file shape

- Documented: staticcheck reads TOML `staticcheck.conf` files that apply per package subtree and merge downward, with `"inherit"` and `"all"` sentinels and `-` prefixes; the example config is `checks = ["all", "-SA9003", "-ST1000", ...]` plus `initialisms`, `dot_import_whitelist`, and `http_status_code_whitelist` (`go-tools/website/content/docs/configuration/_index.md`; `go-tools/config/example.conf`). Everything else is a CLI flag: `-checks`, `-go` (defaults to `module`, reading the `go` line), `-tests`, `-f stylish|text|json`, `-fail`, `-explain` (`staticcheck -h`). Inline suppression is `//lint:ignore CHECK reason`.
- Documented: golangci-lint v2 reads `.golangci.yml`, `.golangci.yaml`, `.golangci.toml`, or `.golangci.json` from the working directory or any parent of the first analysed path; linter settings live only in the file (`golangci-lint/docs/content/docs/configuration/file.md` lines 6 to 18). The file starts with `version: "2"`, then `linters.default` (`standard`, `all`, `none`, `fast`), `linters.enable`, `linters.settings.<name>`, `linters.exclusions` with presets `comments`, `std-error-handling`, `common-false-positives`, `legacy`, a separate `formatters` block, and `run` (`timeout`, `relative-path-mode`, `tests`, `build-tags`, `modules-download-mode: readonly`) (`.golangci.reference.yml` lines 1 to 20, 4669 to 4696, 4739 to 4748, 5013 to 5057). Inline suppression is `//nolint:name // reason`.
- Inference: a minimal `.golangci.yml` for this repository is `version: "2"`, `linters: {default: standard}`, `formatters: {enable: [gofumpt]}`, `run: {modules-download-mode: readonly, relative-path-mode: gomod}`, with `linters.settings.staticcheck.checks` left at the default. Adding `gosec` and `revive` is rule tuning, which #14 puts out of scope.

### False-positive burden

- Documented: staticcheck's stance is that "great care is taken to minimize the number of false positives and subjective suggestions" and `ST` style checks that are opinionated are off by default in golangci-lint's default set (`configuration/_index.md`; `staticcheck.go` line 60). 2026.2 lists `U1000` and `SA4023` false-positive fixes and disables `SA5011` for internal reasons (`2026.2.md` lines 40 to 75 and the 2026.2.1 section).
- Observed: golangci-lint's default run added only `inline` (a modernizer style suggestion with a fix) and `QF1004` beyond what a strict reading of the seeded bugs asked for; both were correct. Nothing in the eight findings was a false positive.
- Inference: with `default: standard` the burden is the same staticcheck set plus `errcheck`, whose known noise (unchecked `Close` on read-only files, `fmt.Fprint` to buffers) is covered by its built-in exclusion list and the `std-error-handling` preset. Enabling `all` is where golangci-lint earns its noisy reputation; the default group does not.

### Recommendation

Adopt `golangci-lint` `2.14.0` through mise with `linters.default: standard`, and do not install standalone staticcheck. It runs the identical staticcheck v0.8.1 analyzers, adds `errcheck` (the only tool in the comparison that caught the unchecked `Close` in the trial), `unused`, `ineffassign`, and a superset of `go vet`, carries `gofumpt` as its formatter so one config file governs both, supports Go 1.27 since v2.13.0, installs as an attested binary from mise's aqua backend so the `tool` directive dependency problem never arises, and costs about 0.3 s warm on a module this size. The coordinator makes the decision; if it prefers the smaller tool, staticcheck `2026.2.1` is equally pinnable and Go 1.27 ready, but `check` would then need a second linter for unchecked errors.

## 6. How other harnesses load per-path rules

### Codex

- Verified (source): Codex finds the project root by walking up from the working directory to the nearest directory containing a `project_root_markers` entry (default `.git`), then collects every instruction file from the root down to the working directory inclusive and concatenates them in that order; it never walks above the root; with no marker only the working directory is read (`codex/codex-rs/core/src/agents_md.rs` lines 1 to 18 and 192 to 270).
- Verified (source): in each directory it takes the first present of `AGENTS.override.md`, then `AGENTS.md`, then each `project_doc_fallback_filenames` entry, so an override file replaces `AGENTS.md` for that directory rather than adding to it (`agents_md.rs` lines 43 to 45 and 272 to 300).
- Verified (source): the total budget is `project_doc_max_bytes`, default 32 KiB (`codex/codex-rs/config/src/config_toml.rs` line 74; `core/src/config/mod.rs` line 252), applied across all files root-first, truncating the later, deeper file and logging a warning (`agents_md.rs` lines 125 to 190; the test `total_byte_limit_truncates_later_project_docs` in `agents_md_tests.rs` lines 683 to 716 shows `root` kept whole and the nested file cut to fit).
- Verified (source): untrusted projects load no project docs at all (`agents_md.rs` lines 65 to 68).
- Documented: `docs/agents_md.md` in the clone is three lines and links to the hosted guide; the size and fallback options are not described in the clone's `docs/config.md`.
- Inference: Codex has directory-scoped instruction files, not path-pattern rules. A nested `internal/AGENTS.md` is only loaded when the worker's working directory is inside `internal/`; a Codex worker started at the repository root sees only the root `AGENTS.md`. There is no glob-scoped equivalent of `.claude/rules/go.md`. The `.codex/rules` directory that exists in Codex is execution policy for command approval, not instructions (`codex/docs/execpolicy.md`; `core/src/exec_policy.rs`). So the Go rules for Codex belong in the root `AGENTS.md` (a short section) or in a `cmd/AGENTS.md` and `internal/AGENTS.md` pair that only helps when the worker runs from those directories.

### agy

- Help-text: `agy help` (agy 1.2.11) documents no instructions file, rules directory, or context file flag. Its subcommands are `agent`, `changelog`, `help`, `install`, `mcp`, `mic-serve`, `models`, `plugin`, `remote-control`, `update`; the flags include `--add-dir`, `--agent`, `--mode`, `--sandbox`, and `--dangerously-skip-permissions`.
- Help-text: `agy changelog` documents a rules system without naming a file layout in the help output: "user and workspace rules" share a dedicated 20,000-token budget and oversized rules are cut on newline boundaries and listed by path and description; a `rules.json` declares rule files with `include_only` and exclusion lists, and its directory entries load only items directly inside a directory; a Markdown agent can name rule files with a `rules:` frontmatter key; rules are discovered as `.md` rule files, sorted deterministically, and deduplicated through symlinks; workspace-local hooks live in `<workspace>/.agents/hooks.json` and project agents in `.agents/agents/`. Whether `.agents/rules/` is the discovery directory and whether rules can be path-scoped is not stated in the help text or changelog lines read; untested here. The operator's settings were not read.
- Untested: whether agy reads `AGENTS.md`; the harness research item owns that question.

## Draft rules for .claude/rules/go.md

Each line names the version it was written for. Codex finalises the wording.

- Go 1.27.1 through mise: run every Go command as `mise exec -- go ...` or through a `mise run` task; never call a globally installed `go`, `staticcheck`, `golangci-lint`, or `gofumpt`.
- Go 1.27: `go.mod` says `go 1.27.0` and has no `toolchain` line; `mise.toml` pins the patch (`go = "1.27.1"`) and sets `GOTOOLCHAIN=local` so a mismatch fails instead of downloading a toolchain outside mise.
- Go 1.27: one root module `github.com/tbhb/agent-orchestration-poc`; binaries under `cmd/<name>/main.go`, packages under `internal/`; no `go.work` committed; no `tool` directives for linters or formatters.
- Go 1.27: format with gofumpt 0.12.0 (`gofumpt -l` must print nothing); do not use `-extra`.
- Go 1.27: `check` runs `gofumpt -l`, `go vet ./...`, `go mod tidy -diff`, `go mod verify`, the linter, `go build ./...`, and `go test -race -shuffle=on ./...`; a PR is not done until all pass locally.
- Go 1.27: `go test` runs the `stdversion` vet check, so a symbol newer than the `go` line breaks the test build; keep the `go` line honest.
- Go 1.27: build dial addresses with `net.JoinHostPort`, never `fmt.Sprintf("%s:%d")` (vet `hostport`).
- Go 1.27: on `net.UnixConn` reads compare with `errors.Is(err, io.EOF)`; EOF is no longer wrapped in `*net.OpError`.
- Go 1.27: use `encoding/json/v2` for new protocol encoding; never assert on `encoding/json` error strings.
- Go 1.27: use the standard `uuid` package for new identifiers.
- Go 1.26: use `errors.AsType[T]` over `errors.As`; use `signal.NotifyContext` and read `context.Cause` to learn which signal arrived.
- Go 1.26: use `log/slog` for all daemon logging; `slog.NewMultiHandler` when output must fan out; the vet `slog` analyzer catches malformed key-value calls.
- Go 1.25: use `sync.WaitGroup.Go` instead of `Add` and `Done` pairs; `wg.Add` placement is vet-checked (`waitgroup`).
- Go 1.25: never put secrets in `runtime/pprof` labels; Go 1.27 prints them in tracebacks.
- Go 1.25: `GOMAXPROCS` follows cgroup limits; do not set it by hand in `agentd`.
- Go 1.24: use `t.Context()` for test lifetimes, `t.Chdir` and `t.Setenv` only in non-parallel tests, and `for b.Loop()` in benchmarks.
- Go 1.25: test time-dependent logic with `synctest.Test`; never use `synctest` around real network, tmux, or subprocesses.
- Go 1.27: integration tests that need tmux or an external NATS binary carry `//go:build integration` and `t.Skip` when `exec.LookPath` fails; the embedded NATS server needs neither.
- Go 1.27: tests are `TestXxx` in `_test.go`, table-driven with `t.Run`; fixtures under `testdata/`; captured logs go to `t.ArtifactDir()`.
- Go 1.27: suppress a linter finding only with `//nolint:name // reason` (golangci-lint) or `//lint:ignore CHECK reason` (staticcheck), with the reason mandatory.
- Go 1.27: timer channels are always unbuffered; `time.After` in a `select` never delivers a stale value, and `asynctimerchan` no longer exists.
