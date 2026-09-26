# Go research gate: versions and clones

Recorded 2026-09-26 for issue #4. Tool versions come from commands run inside the worktree through mise; clone SHAs are `git rev-parse HEAD` in each clone. The three linter and formatter installs below were made with `mise exec <tool>@<version>` for the trial runs in `notes.md` and are not pinned in `mise.toml` by this item.

## Tools

| Tool | Version | How obtained | Evidence |
| --- | --- | --- | --- |
| mise | 2026.8.6 macos-arm64 | already installed | `mise --version` |
| go | 1.27.1 darwin/arm64 | mise `go = "1.27"` in `mise.toml`, GOROOT `/Users/tony/.local/share/mise/installs/go/1.27.1` | `mise exec -- go version`, `mise exec -- go env GOROOT GOVERSION GOTOOLCHAIN` (GOTOOLCHAIN `auto`) |
| gofmt | ships with go 1.27.1 | GOROOT | `mise exec -- gofmt -h` |
| go vet | ships with go 1.27.1, 36 analyzers | GOROOT | `mise exec -- go tool vet help` |
| staticcheck | 2026.2.1 (module v0.8.1, built with go1.27.0) | `mise exec staticcheck@2026.2.1`, backend `aqua:dominikh/go-tools/staticcheck` | `staticcheck -version`, `staticcheck -debug.version` |
| golangci-lint | 2.14.0 (built with go1.27.0 from 114493f9 on 2026-09-24) | `mise exec golangci-lint@2.14.0`, backend `aqua:golangci/golangci-lint`, GitHub artifact attestation verified by mise | `golangci-lint version` |
| gofumpt | v0.12.0 (go1.27.1) | `mise exec gofumpt@0.12.0`, backend `aqua:mvdan/gofumpt` | `gofumpt -version` |
| agy | 1.2.11 | already installed | `agy --version`, `agy help`, `agy changelog` |
| guard-markdown | from `~/go/bin` | already installed | `guard-markdown research/gates/go/notes.md` |

Latest versions mise offered on 2026-09-26 (`mise ls-remote`): staticcheck `2026.2.1`, golangci-lint `2.14.0`, gofumpt `0.12.0`, revive `1.17.0`.

## Clones

All under `~/Code/github.com/<owner>/<repo>`. New clones used `git clone --filter=blob:none`; `golang/go` also used `--sparse` with `doc`, `src/cmd/go`, `src/cmd/vet`, `src/testing`, `src/cmd/gofmt`, `src/log/slog`, `src/encoding/json`, `src/os`, and `src/net` checked out, then `git checkout go1.27.1` so the source read matches the installed toolchain.

| Path | Remote | Checked out | HEAD SHA | Commit date | Nearest tag | Status |
| --- | --- | --- | --- | --- | --- | --- |
| ~/Code/github.com/golang/go | https://github.com/golang/go.git | tag `go1.27.1` (detached) | 862c888e612ac346c7c4d99c9392bdfd265f33b0 | 2026-09-01 | go1.27.1 | cloned, sparse |
| ~/Code/github.com/golang/website | https://github.com/golang/website.git | master | f2661d967b28530da480f0a1da9a4279026d34ca | 2026-09-25 | none | cloned |
| ~/Code/github.com/dominikh/go-tools | https://github.com/dominikh/go-tools.git | master | 6cb65e58a558452b52f57cb43267ff9df669a77a | 2026-08-24 | v0.7.0-0.dev-143-g6cb65e5 (release tag v0.8.1 = 1285a6a5ec1e0ebb658f49e82b6c566a878cc3cb, 2026-08-21) | cloned |
| ~/Code/github.com/golangci/golangci-lint | https://github.com/golangci/golangci-lint.git | main | 032d962e0399070bc72d32925e778deaaf2213b9 | 2026-09-25 | v2.14.0-4-g032d962e (release tag v2.14.0 = 114493f9b3e7257d29e4130f2b4a4aadefbb6845, 2026-09-24) | cloned |
| ~/Code/github.com/mvdan/gofumpt | https://github.com/mvdan/gofumpt.git | master | 3e0cc4edc39797c8ed123f4e0a60e3ad1cdcd3b0 | 2026-09-23 | v0.12.0-33-g3e0cc4e (release tag v0.12.0 = 3e07e7e70ac93761d8e79ca0083a19e3d59f753d, 2026-09-07) | cloned |
| ~/Code/github.com/openai/codex | https://github.com/openai/codex.git | main | a6bd19261c30ce0a0225fe90e646822d29916f11 | 2026-09-26 | voice-cygwin-108b38cf67cbb731 | existing clone from `experiments/00-system-assessment/dependency-clones.md`, not updated |

## Files read

- `golang/website`: `_content/doc/go1.24.md` (grep only), `go1.25.md`, `go1.26.md`, `go1.27.md`, `toolchain.md`, `modules/gomod-ref.md`, `modules/layout.md`.
- `golang/go` at go1.27.1: `doc/godebug.md`, `src/testing/testing.go`, `src/testing/benchmark.go`, `src/testing/synctest/synctest.go`, `src/cmd/go/internal/modload/init.go`, `src/cmd/go/internal/gover/version.go`.
- `dominikh/go-tools`: `go.mod`, `config/example.conf`, `config/config.go`, `staticcheck.conf`, `lintcmd/cmd.go`, `website/content/changes/2025.1.md`, `2026.1.md`, `2026.2.md`, `website/content/docs/getting-started.md`, `website/content/docs/configuration/_index.md`, and the `staticcheck`, `simple`, `stylecheck`, `quickfix` analyzer directories.
- `golangci/golangci-lint`: `go.mod`, `CHANGELOG.md`, `.golangci.reference.yml`, `pkg/golinters/staticcheck/staticcheck.go`, `pkg/lint/lintersdb/builder_linter.go`, `docs/content/docs/configuration/file.md`, `docs/content/docs/configuration/cli.md`, `docs/content/docs/welcome/install/local.md`.
- `mvdan/gofumpt`: `README.md`, `gofmt.go`, `go.mod`.
- `openai/codex`: `codex-rs/core/src/agents_md.rs`, `codex-rs/core/src/agents_md_tests.rs`, `codex-rs/config/src/config_toml.rs`, `codex-rs/core/src/config/mod.rs`, `docs/agents_md.md`, `docs/execpolicy.md`.
- Installed toolchain help: `go help packages`, `go help test`, `go help testflag`, `go help build`, `go help buildconstraint`, `go help tool`, `go help get`, `go help work`, `go help mod tidy`, `go help mod verify`, `go tool vet help`, `$GOROOT/go.env`.

## Trial module

`notes.md` section 5 reports runs against a two-package throwaway module in the session scratchpad (`go 1.27.0`, one `cmd/d` binary, one `internal/svc` package with seven seeded issues). It is not committed.
