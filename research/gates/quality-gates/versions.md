# Quality gates research: versions and clones

Recorded 2026-09-26 for issues #62 and #63. Tool versions come from commands run through mise inside the `research/62-63-quality-gates` worktree or a `mktemp -d` copy of its `HEAD` tree. Clone SHAs are `git rev-parse HEAD` after `git pull --ff-only` (existing clones) or `git clone --filter=blob:none` (new clones). Nothing here is pinned in `mise.toml` or `pyproject.toml` yet; the trial installs used `mise exec`, `uv run --with`, and `uvx` at the exact versions below.

## Tools

| Tool | Version | How obtained | Evidence |
| --- | --- | --- | --- |
| mise | 2026.8.6 macos-arm64 | already installed | `mise --version` |
| go | 1.27.1 darwin/arm64 | `go = "1.27.1"` in `mise.toml` | `mise exec -- go version` |
| golangci-lint | 2.14.0 | `golangci-lint = "2.14.0"` in `mise.toml` | `mise exec -- golangci-lint run` |
| deadcode | golang.org/x/tools v0.50.0 | `mise exec -- go run golang.org/x/tools/cmd/deadcode@v0.50.0` | `go: downloading golang.org/x/tools v0.50.0`; `mise ls-remote go:golang.org/x/tools/cmd/deadcode` ends at 0.50.0 |
| dupl (standalone) | github.com/golangci/dupl v0.0.0-20260401084720-c99c5cf5c202 | `mise exec -- go run github.com/golangci/dupl@c99c5cf5c202c7e5bb1292e1212e7de4038324c8` | the pseudo-version golangci-lint pins at `go.mod:67` |
| uv | 0.12.10 | `uv = "0.12.10"` in `mise.toml` | `mise exec -- uv --version` |
| ruff | 0.16.9 | `dev` group in `uv.lock` | `mise exec -- uv run ruff rule C901` |
| vulture | 2.16 | `mise exec -- uv run --no-project --with vulture==2.16 vulture` | printed `vulture.__version__`; `mise ls-remote pipx:vulture` ends at 2.16 |
| radon | 6.0.1 | `mise exec -- uv run --no-project --with radon==6.0.1 radon` | printed `radon.__version__`; `mise ls-remote pipx:radon` ends at 6.0.1 |
| xenon | 0.9.3 | `mise exec -- uv run --no-project --with radon==6.0.1 --with xenon==0.9.3 xenon` | printed `xenon.__version__`; `mise ls-remote pipx:xenon` ends at 0.9.3 |
| pylint | 4.0.9 | `mise exec -- uv run --no-project --with pylint pylint` | `pylint --version` |
| jscpd | 5.3.2 (Rust engine, PyPI wheel) | `mise exec -- uvx jscpd==5.3.2` | `jscpd --version`; `mise ls-remote pipx:jscpd` and `mise ls-remote npm:jscpd` both end at 5.3.2 |
| biome | 2.5.14 | `"npm:@biomejs/biome" = "2.5.14"` in `mise.toml` | not run; rules read from the clone at the tag below |
| guard-markdown | 0.9.0 | `"go:github.com/tbhb/repotools/cmd/guard-markdown"` in `mise.toml` | run on both documents in this directory |

## Clones

All under `~/Code/github.com/<owner>/<repo>`. The first three existed before this item and were pulled; the rest were cloned on 2026-09-26 with `git clone --filter=blob:none`. "Nearest tag" is `git describe --tags`.

| Path | HEAD SHA | Commit date | Nearest tag | Status | What was read |
| --- | --- | --- | --- | --- | --- |
| `~/Code/github.com/golangci/golangci-lint` | `8920f7a763476de3e0dc3d8e548641f1607aba91` | 2026-09-26 | v2.14.0-5-g8920f7a7 (release tag v2.14.0 is the installed version) | pulled | `.golangci.reference.yml` (linter settings, exclusions), `pkg/lint/lintersdb/builder_linter.go`, `pkg/golinters/{dupl,gocyclo,gocognit,cyclop,funlen,nestif,maintidx,unused}/*.go`, `pkg/golinters/internal/util.go`, `go.mod` |
| `~/Code/github.com/astral-sh/ruff` | `51f3437d0344b1909007acf42fe6b124369f8439` | 2026-09-26 | 0.16.9-23-g51f3437d0 (release tag 0.16.9 is the installed version) | pulled | `crates/ruff_workspace/src/options.rs` (`McCabeOptions`, `PylintOptions`), `crates/ruff_linter/src/codes.rs` |
| `~/Code/github.com/biomejs/biome` | `a62070a04bdbacfeb640cc946f1b96fab95af520` | 2026-09-26 | @biomejs/biome@2.5.14-76-ga62070a04b (release tag 2.5.14 is the installed version) | pulled | `crates/biome_js_analyze/src/lint/complexity/*.rs`, `crates/biome_js_analyze/src/lint/correctness/no_unused_*.rs` |
| `~/Code/github.com/golang/tools` | `d2d3de9f066e8af56688cbad392a9a502afef315` | 2026-09-25 | v0.50.0-52-gd2d3de9f0 (release tag v0.50.0 is the version run) | cloned | `cmd/deadcode/doc.go` |
| `~/Code/github.com/dominikh/go-tools` | `6cb65e58a558452b52f57cb43267ff9df669a77a` | 2026-08-24 | v0.7.0-0.dev-143-g6cb65e5 (release tag v0.8.1 is what golangci-lint 2.14.0 embeds) | existing, from the Go gate | `unused/unused.go` overview comment |
| `~/Code/github.com/jendrikseipp/vulture` | `a70cc9ed09d1b24162608cdf88959ebd9e6405ab` | 2026-09-25 | v2.16-6-ga70cc9e (release tag v2.16 is the version run) | cloned | `README.md`, `CHANGELOG.md`, `vulture/core.py`, `vulture/whitelists/` |
| `~/Code/github.com/rubik/radon` | `54b88e5878b2724bf4d77f97349588b811abdff2` | 2024-10-20 | v6.0.1-12-g54b88e5 (release tag v6.0.1 is the version run) | cloned | `docs/intro.rst`, `docs/commandline.rst`, `radon/__init__.py`, `setup.py` |
| `~/Code/github.com/rubik/xenon` | `c7364e23bb55ca515322eb9a260b5ebf4bf18c3b` | 2024-10-21 | v0.9.3 (exact) | cloned | `README.rst`, `requirements.txt` |
| `~/Code/github.com/pylint-dev/pylint` | `3fe8a8eea278554d081ac1261d3668a39a7860fd` | 2026-09-26 | v4.0.9-417-g3fe8a8ee (release tag v4.0.9 is the version run) | cloned | `pylint/checkers/symilar.py`, `doc/user_guide/checkers/features.rst`, `doc/user_guide/configuration/all-options.rst` |
| `~/Code/github.com/kucherenko/jscpd` | `44ffccbf616d182b2ff9fd069e4be98359f0fe91` | 2026-09-26 | v5-13-g44ffccb (latest release tag v5.3.2 is the version run) | cloned | `README.md`, `docs/rust.md`, `FORMATS.md`, `pyproject.toml`, `rust/jscpd/package.json` |
| `~/Code/github.com/golangci/dupl` | `c99c5cf5c202c7e5bb1292e1212e7de4038324c8` | 2026-04-01 | none (pseudo-version above) | cloned | `README.md`, `syntax/syntax.go`, `suffixtree/` |
| `~/Code/github.com/fzipp/gocyclo` | `7b6c7c5e29f1e2abfde310b3210309272745fc45` | 2025-12-27 | v0.6.0-15-g7b6c7c5 (golangci-lint pins v0.6.0) | cloned | `README.md` |
| `~/Code/github.com/uudashr/gocognit` | `5b8ec1cd6a28032e4e38356b6e913ea5fe7a8d63` | 2026-02-24 | v1.2.1 (exact; golangci-lint pins v1.2.1) | cloned | `README.md` |
| `~/Code/github.com/bkielbasa/cyclop` | `7d0b0a6286641bb3ef64c466dcf8c49c81f45a12` | 2024-10-16 | v1.2.3 (exact; golangci-lint pins v1.2.3) | cloned | `README.md` |
| `~/Code/github.com/nakabonne/nestif` | `1471aaea77d69c51b7786b519482f1a0021eaac9` | 2026-02-26 | v0.3.1-1-g1471aae (golangci-lint pins v0.3.1) | cloned | `README.md` |
| `~/Code/github.com/ultraware/funlen` | `955cef7e3e8d12c3f17141072ad57f7fec5a447a` | 2024-12-16 | v0.2.0 (exact; golangci-lint pins v0.2.0) | cloned | `README.md` |
| `~/Code/github.com/yagipy/maintidx` | `d4eb9bc0390bc3b943b3d045267c0e1a28b6de91` | 2026-05-15 | v1.0.0-18-gd4eb9bc (golangci-lint pins v1.0.0) | cloned | `README.md` |

The seven per-linter clones were added because golangci-lint vendors those modules rather than their documentation; `go.mod` lines 42, 58, 67, 105, 137, 139, and 143 record the pinned versions.
