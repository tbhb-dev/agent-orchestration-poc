# Boundary tools research gate: versions and clones

Recorded 2026-09-26 for issue #58. Tool versions come from commands run through mise; the three boundary tools were installed only for the trials in `notes.md` and nothing here pins them in `mise.toml` or `pyproject.toml`. Clone SHAs are `git rev-parse HEAD` in each clone.

## Tools

| Tool | Version | How obtained | Evidence |
| --- | --- | --- | --- |
| mise | 2026.8.6 macos-arm64 | already installed | `mise --version` |
| go | 1.27.1 darwin/arm64 | `go = "1.27.1"` in `mise.toml`, `GOTOOLCHAIN=local` | `mise exec -- go version` |
| golangci-lint | 2.14.0, built with go1.27.0 from 114493f9 on 2026-09-24 | `golangci-lint = "2.14.0"` in `mise.toml`, aqua backend | `mise exec -- golangci-lint version` |
| depguard | v2.2.1, the version golangci-lint 2.14.0 vendors | inside golangci-lint | `golangci-lint/go.mod` line 33 at the clone SHA below |
| arch-go | v2.1.2, binary built with go1.27.1 | `mise exec "go:github.com/arch-go/arch-go/v2@2.1.2"` | `go version -m $(command -v arch-go)` |
| go-arch-lint | v1.19.0, binary built with go1.27.1 | `mise exec "go:github.com/fe3dback/go-arch-lint@1.19.0"` | `go-arch-lint version` and `go version -m` |
| python | 3.14.6 | `python = "3.14.6"` in `mise.toml`, `UV_PYTHON_PREFERENCE=only-system` | `mise exec -- python --version`; `sys.version` inside the trial venv |
| uv | 0.12.10 | `uv = "0.12.10"` in `mise.toml` | `mise exec -- uv --version` |
| import-linter | 2.15 | `uv add --dev import-linter` in the trial project | `uv.lock` entry and `importlinter.__version__` |
| grimp | 3.17 | import-linter's graph dependency, resolved by uv | `uv.lock` entry and `grimp.__version__` |
| ruff | 0.16.9 | `uv add --dev ruff` in the trial project, same version as the repository's `dev` group | `uv run ruff --version` |
| guard-markdown | v0.3.0 | already installed | `guard-markdown --version` |

Versions mise offered on 2026-09-26: `pipx:import-linter` up to 2.15, `go:github.com/fe3dback/go-arch-lint` up to 1.19.0, `go:github.com/arch-go/arch-go/v2` up to 2.1.2. `mise ls-remote arch-go` on the short name failed against the `aqua:arch-go/arch-go` registry entry with a version error under mise 2026.8.6, so the `go:` backend is the working install path for both Go tools; depguard needs no install of its own because it ships inside golangci-lint.

## Clones

All under `~/Code/github.com/<owner>/<repo>`. New clones used `git clone --filter=blob:none` on 2026-09-26. The golangci-lint and ruff clones predate this gate and had moved past the SHAs recorded in `research/gates/go/versions.md` and `research/gates/python/versions.md`; the files cited here were read at the SHAs below.

| Path | Remote | HEAD SHA | Commit date | Nearest tag | Status |
| --- | --- | --- | --- | --- | --- |
| ~/Code/github.com/seddonym/import-linter | <https://github.com/seddonym/import-linter.git> | 31927f1457e3df673912cb5efb0afa6dbc37585f | 2026-09-04 | v2.15 (exact) | cloned |
| ~/Code/github.com/OpenPeeDeeP/depguard | <https://github.com/OpenPeeDeeP/depguard.git> | af89c287010f242a2a6310fc5785ca9420fe2c4a | 2026-09-22 | v2.2.1-1-gaf89c28 (release tag v2.2.1) | cloned |
| ~/Code/github.com/fe3dback/go-arch-lint | <https://github.com/fe3dback/go-arch-lint.git> | bf473afb033c7c3eb7aba68dc399cf919287131e | 2026-09-07 | v1.19.0 (exact) | cloned |
| ~/Code/github.com/arch-go/arch-go | <https://github.com/arch-go/arch-go.git> | 6cb436f84fc8c3800ab9e4f014813c35e871b3d3 | 2026-02-13 | v2.1.2-7-g6cb436f (release tag v2.1.2) | cloned |
| ~/Code/github.com/golangci/golangci-lint | <https://github.com/golangci/golangci-lint.git> | 8920f7a763476de3e0dc3d8e548641f1607aba91 | 2026-09-26 | v2.14.0-5-g8920f7a7 (release tag v2.14.0) | existing clone, moved on since the Go gate |
| ~/Code/github.com/astral-sh/ruff | <https://github.com/astral-sh/ruff.git> | 51f3437d0344b1909007acf42fe6b124369f8439 | 2026-09-26 | after 0.16.9 | existing clone, moved on since the Python gate |

Not cloned, by instruction: `dependency-cruiser`, Biome's `noRestrictedImports`, and `eslint-plugin-boundaries` are named in `notes.md` for the phase 5 TypeScript gate only.

## Files read

- `seddonym/import-linter`: `pyproject.toml`, `docs/release_notes.md`, `docs/get_started/{install,configure,run}.md`, `docs/contract_types/{index,forbidden,layers,independence,protected}.md`, `src/importlinter/contracts/forbidden.py`, `src/importlinter/application/use_cases.py` (grep), `tests/unit/contracts/test_forbidden.py` (grep).
- `OpenPeeDeeP/depguard`: `README.md`, `go.mod`, `settings.go`, `settings_test.go` (grep).
- `golangci/golangci-lint`: `go.mod`, `CHANGELOG.md` (grep), `.golangci.reference.yml` depguard section, `pkg/golinters/depguard/depguard.go`, `docs/content/docs/linters/configuration.md` (grep).
- `fe3dback/go-arch-lint`: `README.md`, `go.mod`, `.go-arch-lint.yml`, `.goreleaser.yml`, `docs/syntax/README.md`, `internal/services/checker/checker_imports.go`, `internal/models/resolved_file.go` (grep), `.github/workflows/*.yml` (grep).
- `arch-go/arch-go`: `README.md`, `go.mod`, `arch-go.yml`, `CHANGELOG.md`, `internal/verifications/dependencies/check_restricted.go`, `internal/utils/packages/is_standard.go`, `internal/utils/packages/get_packages.go`, `.github/workflows/ci.yml` (grep).
- `astral-sh/ruff`: `docs/configuration.md` (hierarchical configuration and `extend`), `crates/ruff_linter/src/rules/flake8_tidy_imports/rules/` (listing).
- This repository: `PLAN.md`, `mise.toml`, `.golangci.yml`, `pyproject.toml`, `prek.toml`, `tests/conftest.py`, `cmd/*/main.go`, `internal/**/doc.go`, `.claude/rules/{go,python}.md`, `docs/src/content/docs/guides/{go,python}-conventions.md`, `research/gates/{go,python}/*.md`, `experiments/00-system-assessment/nats-research.md` (grep), `.github/workflows/check.yml` (grep).

## Trial projects

Four throwaway projects in the session scratchpad, not committed: `pytrial` (uv project, `aop.core` and `aop.shell` packages, import-linter and ruff), `gotrial` (one module, `internal/core` seeded with nine boundary violations, depguard through golangci-lint), and two copies of it for arch-go and go-arch-lint. `notes.md` quotes their output.
