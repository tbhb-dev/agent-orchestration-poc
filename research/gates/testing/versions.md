# Property and mutation testing research gate versions

Every tool version and clone read for issues #59 and #60 on 2026-09-26. Clone SHAs come from `git rev-parse HEAD` in each clone, nearest tags from `git describe --tags`, and tag SHAs from `git rev-parse <tag>^{commit}`. Python package versions come from the PyPI JSON API (`https://pypi.org/pypi/<pkg>/json`) and from what `mise exec -- uv add --dev` resolved, because uv 0.12.10 has no `uv pip index versions` subcommand.

## Runtime and tools in this checkout

| Tool | Version | How obtained |
| --- | --- | --- |
| Go | go1.27.1 darwin/arm64 | `mise exec -- go version` |
| Python | 3.14.6 | `mise exec -- python --version` |
| uv | 0.12.10 (3c979abda 2026-09-04 aarch64-apple-darwin) | `mise exec -- uv --version` |
| golangci-lint | 2.14.0 | `mise exec golangci-lint@2.14.0 -- golangci-lint run ./...` in the scratch module |
| pytest | 9.1.1 | resolved in the scratch project's `uv.lock` from `pytest>=9.1.1` |
| mise | 2026.8.6 macos-arm64 | printed by mise in an error message |

## Candidate versions

| Candidate | Version trialed | Released | Declared minimum | Upstream test matrix | Pin route |
| --- | --- | --- | --- | --- | --- |
| `pgregory.net/rapid` | v1.3.0 | 2026-03-30 | `go 1.23` | Go 1.23 to 1.26 | `go.mod` |
| `github.com/leanovate/gopter` | v0.2.11 | 2024-04-03 | `go 1.20` | Go 1.20 to 1.22 | `go.mod` |
| `hypothesis` | 6.168.1 | 2026-09-23 | Python 3.10 | main jobs on Python 3.14 | uv `dev` group |
| `github.com/go-gremlins/gremlins` | v0.6.0 | 2025-12-06 | `go 1.25` | version from `go.mod` | mise `go:` backend, versions 0.4.0 to 0.6.0 listed |
| `github.com/zimmski/go-mutesting` | v0.0.0-20210610104036-6d9217011a00 | 2021-06-10 | `go 1.10` | none current | mise `go:` backend lists the pseudo-version only |
| `mutmut` | 3.8.0 | 2026-09-12 | Python 3.10 | Python 3.10 to 3.15 | uv `dev` group |
| `cosmic-ray` | 8.7.0 | 2026-08-09 | Python 3.9 | Python 3.9 to 3.13 | uv `dev` group |

`mise registry` has no entry for gremlins, go-mutesting, mutmut, or cosmic-ray.

## Clones read

All seven were cloned on 2026-09-26 with `git clone --filter=blob:none`.

| Repository | Path | Branch | HEAD SHA | Commit date | Nearest tag | Release tag SHA |
| --- | --- | --- | --- | --- | --- | --- |
| `flyingmutant/rapid` | `~/Code/github.com/flyingmutant/rapid` | master | `6706a6fd83736ba24aaf55ef2621fdf00c2c27e8` | 2026-09-04 | v1.3.0-1-g6706a6f | `v1.3.0` is `9bafe07343742c860ff53bf66075648f8ebb54a5` |
| `leanovate/gopter` | `~/Code/github.com/leanovate/gopter` | master | `967a5004fb702c153283a99f5a3908ee6570c066` | 2026-04-20 | v0.2.11-8-g967a500 | `v0.2.11` is `b641a797febee7a0bb8a44d40cec92f2c894297f` |
| `HypothesisWorks/hypothesis` | `~/Code/github.com/HypothesisWorks/hypothesis` | master | `9c55f97e507eae21677457e84737b386fd06e271` | 2026-09-25 | v6.168.1-2-g9c55f97e5 | `v6.168.1` is `6cee8ceb8635f82d1dc1e63fabd40801c3cf08e9` |
| `go-gremlins/gremlins` | `~/Code/github.com/go-gremlins/gremlins` | main | `b48a4aad17eff33dc7262e0d1487b1a4d6eec322` | 2026-03-30 | v0.6.0-8-gb48a4aa | `v0.6.0` is `e05b1d47b8c55748e50abc28ff6b132c536bacca` |
| `zimmski/go-mutesting` | `~/Code/github.com/zimmski/go-mutesting` | master | `6d9217011a005762bbcf4ac7a60237dc6a99887f` | 2021-06-10 | v1.2 | HEAD is the tag |
| `boxed/mutmut` | `~/Code/github.com/boxed/mutmut` | main | `14a7230049a5c8abd90c2bb0f7438e30da6471f5` | 2026-09-12 | 3.8.0 | HEAD is the tag |
| `sixty-north/cosmic-ray` | `~/Code/github.com/sixty-north/cosmic-ray` | master | `caf9a3193606ddd90cc37126b7fa95acefc47695` | 2026-08-09 | release/v8.7.0 | HEAD is the tag |

The gremlins documentation in the clone describes HEAD, eight commits after `v0.6.0`. One flag it documents, `--output-diff-statuses`, is not in `v0.6.0`.

## Files read, by clone

- `flyingmutant/rapid`: `go.mod`, `README.md`, `engine.go`, `data.go`, `persist.go`, `generator.go`, `combinators.go`, `collections.go`, `strings.go`, `integers.go`, `floats.go`, `make.go`, `shrink.go`, `statemachine.go`, `synctest_enabled.go`, `.github/workflows/ci.yml`.
- `leanovate/gopter`: `go.mod`, `README.md`, `CHANGELOG.md`, `gen.go`, `properties.go`, `test_parameters.go`, `prop/forall.go`, `prop/forall_no_shrink.go`, `gen/struct.go`, `.github/workflows/build.yml`.
- `HypothesisWorks/hypothesis`: `hypothesis/pyproject.toml`, `hypothesis/docs/changelog.rst`, `hypothesis/docs/tutorial/settings.rst`, `hypothesis/docs/reference/api.rst`, `hypothesis/src/hypothesis/_settings.py`, `hypothesis/src/hypothesis/database.py`, `hypothesis/src/hypothesis/version.py`, `hypothesis/src/_hypothesis_pytestplugin.py`, `.github/workflows/main.yml`, `tooling/src/hypothesistooling/__main__.py`.
- `go-gremlins/gremlins`: `go.mod` at HEAD and at `v0.6.0`, `mise.toml`, `cmd/unleash.go`, `internal/gomodule/gomodule.go`, `internal/coverage/coverage.go`, `internal/configuration/configuration.go`, `docs/docs/install.md`, `docs/docs/usage/configuration.md`, `docs/docs/usage/commands/unleash/index.md`, `docs/docs/usage/commands/unleash/workers.md`, `docs/docs/usage/mutations/index.md`, `docs/docs/usage/ci/github-action.md`, `.github/workflows/ci.yml`.
- `zimmski/go-mutesting`: `go.mod`, `README.md`, the `mutator/` directory listing.
- `boxed/mutmut`: `pyproject.toml`, `README.rst`, `HISTORY.rst`, `src/mutmut/__main__.py`, `src/mutmut/configuration.py`, `.github/workflows/tests.yml`.
- `sixty-north/cosmic-ray`: `pyproject.toml`, `CHANGELOG.md`, `docs/source/concepts.rst`, `docs/source/how-tos/filters.rst`, `src/cosmic_ray/tools/survival_rate.py`, the `src/cosmic_ray/operators/` directory listing, `.github/workflows/run-tests.yml`.

## Trial modules

All under one `mktemp -d` directory outside the repository, not kept.

| Module | Contents | Tools run |
| --- | --- | --- |
| `goprop` | `go 1.27.0` module, `subject` package with a pure validator, rapid and gopter tests | `go get`, `go test -race -shuffle=on -v ./...`, `go vet ./...`, golangci-lint 2.14.0 |
| `gomut` | `go 1.27.0` module, `internal/core` with the validator and a table test, `internal/shell` with an `os.Stat` wrapper and no test, `.gremlins.yaml` | gremlins v0.6.0, go-mutesting |
| `pyprop` | Python 3.14.6 project with this repository's pytest table, `tests/conftest.py`, and ruff configuration, a pure `subject` module, a parametrized test and a property test | `uv add --dev`, `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` |
| `pyprop-mutmut` | copy of `pyprop` with `[tool.mutmut]` | mutmut 3.8.0 and the score gate script |
| `pyprop-cr` | copy of `pyprop` with `cr.toml` | cosmic-ray 8.7.0, `cr-report`, `cr-rate` |
