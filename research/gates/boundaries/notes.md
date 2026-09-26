# Boundary tools research gate: raw notes

Raw notes for the research half of issue #58, gathered 2026-09-26 in the `research/58-boundaries` worktree. The operator requires that every target language has a tool that enforces the functional core, imperative shell boundary, like import-linter in Python. Codex writes the decision record, the `AGENTS.md` section, the rules, and the conventions page updates from these notes, and an implementation worker wires the tools in; this file changes no configuration.

Every claim carries a label. `[verified]` means a command was run here and its output is quoted, or a line was read in a clone at the SHA recorded in `versions.md`. `[documented]` means a claim read in a tool's own documentation at that SHA. `[inference]` means a judgement drawn from the evidence. `[untested]` means nobody checked it. Citations are `path:line` relative to the clone root, or a command with its output.

Clone shorthand: `import-linter` is `~/Code/github.com/seddonym/import-linter` at `31927f14` (tag v2.15), `depguard` is `~/Code/github.com/OpenPeeDeeP/depguard` at `af89c287` (one commit past v2.2.1), `golangci-lint` is `~/Code/github.com/golangci/golangci-lint` at `8920f7a7` (five commits past v2.14.0), `go-arch-lint` is `~/Code/github.com/fe3dback/go-arch-lint` at `bf473afb` (tag v1.19.0), `arch-go` is `~/Code/github.com/arch-go/arch-go` at `6cb436f8` (seven commits past v2.1.2), `ruff` is `~/Code/github.com/astral-sh/ruff` at `51f3437d`.

## Summary

- Go: use `depguard` through golangci-lint 2.14.0, which the `check` task and CI already run. It denies `os`, `net`, `syscall`, the NATS client, and `internal/backend/*` from the core packages with one rule and no new binary. Neither alternative earns a second tool: go-arch-lint 1.19.0 cannot see standard-library imports at all, and arch-go 2.1.2 can, but only duplicates what depguard does at the cost of a second config and a second tool pin.
- Python: use import-linter 2.15 with `include_external_packages = true`, one `layers` contract (shell above core) and one `forbidden` contract that lists the standard-library and third-party modules the core may not import. The forbidden list works for standard-library modules because grimp squashes every non-root import, standard library included, into an external node.
- Both tools check imports, not calls. Neither can tell `pathlib.Path.write_text` from `pathlib.Path.name`, or `os.remove` from `os.environ`. The honest boundary is at the module: the core imports none of `os`, `subprocess`, `socket`, `asyncio`, `sys`, `websockets`, `nats`, and writes nothing; ruff's `TID251` in a nested `ruff.toml` catches the qualified names it can resolve, which is a partial supplement, not a second gate.
- Layout: a dedicated core tree (`internal/core/...` in Go, `agent_orchestration_poc/core/` in Python) with everything else as the shell. One glob, one contract, and no per-package edits when a package is added. The per-package alternative is recorded in section 1 with its costs.
- Tests: core tests are plain functions with values in and out, no mocks, no markers, no build tags. Shell tests carry `integration` (the pytest marker and `--run-integration` gate already in `tests/conftest.py`; the `//go:build integration` tag already in `.claude/rules/go.md`).

## 1. The boundary for this repository

### What the plan's packages actually are

`[verified]` `PLAN.md` lines 28 and 29 list `cmd/` (`agentd`, `agentctl`) and `internal/` with `bus`, `registry`, `backend/tmux`, `backend/container`, `term`, `api`. The `doc.go` files in the skeleton describe them: `bus` is "the message bus embedded in agentd", `registry` "tracks agents and their worktrees", `tmux` and `container` are the backends "for running harnesses", `term` "handles terminal sessions and captures", `api` is "the daemon API served to agentctl and the web app" (`internal/*/doc.go`, `internal/backend/*/doc.go`). `PLAN.md` line 15 says `agentd` in phase 2 is "the bootstrap provisioner plus the embedded NATS broker plus a SQLite registry with the host-tmux backend".

`[inference]` Every one of those six packages is a shell package by its stated job: an embedded broker, a SQLite store, two process backends, a terminal capturer, and a served API all exist to do I/O. The functional core does not yet have a home in the layout. That is the first decision: where the pure code lives, because "functional core" cannot mean "the packages that happen to have no I/O today"; the tools need a name for it.

`[inference]` What belongs in the core, from the sketch and the plan: the roster and its transitions (join, claim, ack, status changes), message and envelope encoding and validation, subject naming, the provisioning plan (what to spawn, with which environment, from which worktree), capture parsing, and every decision the daemon makes from a snapshot of state. Each is a function from values to values. The shell owns NATS connections, SQLite, tmux and container processes, file and socket I/O, signals, clocks, and the CLI.

### Go option A: a dedicated core tree

`[inference]` Layout: `internal/core/<topic>` holds every pure package (`internal/core/roster`, `internal/core/envelope`, `internal/core/plan`, and so on as they appear). Everything else is the shell: `cmd/*`, `internal/bus`, `internal/registry`, `internal/backend/*`, `internal/term`, `internal/api`. The dependency direction is one way: shell packages import `internal/core/...`; nothing under `internal/core` imports anything outside `internal/core` and the allowed standard library.

`[verified]` depguard expresses this with one rule whose `files` glob is `**/internal/core/**` and whose deny list names the packages and prefixes the core may not import; the trial in section 3 shows the exact output. Adding a new core package needs no configuration change. `[inference]` The shell side needs no rule at all: shell packages may import anything, and the `internal/` convention already stops other modules from importing them.

`[inference]` Cost: the names in `PLAN.md` stay as the shell, and pure code that a package like `registry` would naturally hold moves under `internal/core/registry` or a better name, so two packages can share a topic name with different import paths. That is normal Go (compare `net` and `net/netip`) but it needs the conventions page to say which one a worker writes first.

### Go option B: the shell as a subpackage of each feature

`[inference]` Layout: `internal/<pkg>` is pure and `internal/<pkg>/<driver>` is its shell, for example `internal/registry` (pure roster transitions) and `internal/registry/sqlite` (the store), `internal/bus` (subjects and envelopes) and `internal/bus/nats` (the connection). `cmd/*` and `internal/backend/*` are shell outright.

`[inference]` Cost: the depguard `files` list must name every pure package explicitly (`**/internal/registry/*.go`, `**/internal/bus/*.go`, and so on), because a glob like `**/internal/*/*.go` also matches the shell's top-level files in `internal/backend/`, and a new feature package is silently unguarded until someone adds its glob. The lead's suggested `internal/<pkg>/io` naming has the same property. Option B also puts the boundary inside each package's directory, where a worker adding one file to the wrong level breaks it without a directory rename to warn them.

`[inference]` Recommendation: option A. The whole point of a mechanical check is that it never needs to be remembered; option A's single glob does that, option B's list does not. If the coordinator prefers the plan's names to stay meaningful for pure code, option B is workable with the enumerated `files` list, and the notes in section 3 show that the list is the only thing that changes.

### Python option 1: `core` and `shell` subpackages

`[inference]` Layout: `src/agent_orchestration_poc/core/` for pure modules (evidence record shapes and their validation, harness discovery decisions from a listing, protocol framing) and `src/agent_orchestration_poc/shell/` for I/O (the WebSocket-over-Unix client, process spawning, file writes, the evidence writer). Anything at the package top level is a thin re-export or nothing at all.

`[verified]` import-linter expresses this with one `layers` contract, `layers = ["shell", "core"]` with `containers = ["agent_orchestration_poc"]`, and one `forbidden` contract from `agent_orchestration_poc.core` to the I/O modules; section 2 shows both breaking and both kept.

### Python option 2: per-feature `core` modules

`[inference]` Layout: `src/agent_orchestration_poc/<feature>/core.py` next to `<feature>/io.py`, guarded by wildcard expressions (`agent_orchestration_poc.*.core` as `source_modules`), which the forbidden contract supports (`import-linter`, `docs/contract_types/index.md`, "Wildcards"). The layers contract cannot use wildcards in `layers`, only in `containers`, so the layering would become a `containers = ["agent_orchestration_poc.*"]` contract with `layers = ["io", "core"]` per feature.

`[inference]` Recommendation: option 1. The helper package is small (one file today), the wildcard form makes each feature directory carry the boundary, and the layers contract with a container list is exactly as easy to break by a new module named neither `core` nor `io` (which the contract ignores unless `exhaustive = true` is set, which then needs `exhaustive_ignores` maintenance).

### What sits outside every tool

`[verified]` import-linter analyses the root package only; `root_package` "must be importable" (`import-linter`, `docs/get_started/configure.md`, "Top level configuration"). The experiment scripts under `experiments/<NN-slug>/` are plain files run with `PYTHONSAFEPATH=1` (`.claude/rules/python.md`, "Interpreter and uv") and are not a package, so no contract sees them. `[inference]` That is correct: scripts are shell by construction. The rule for them is prose, not a contract: a script calls into `agent_orchestration_poc.core` for decisions and does its own I/O.

`[verified]` depguard, arch-go, and go-arch-lint all classify imports by path; none of them inspects calls (`depguard/settings.go:139-159`; `arch-go/internal/verifications/dependencies/check_restricted.go:13-33`; `go-arch-lint/internal/services/checker/checker_imports.go:74-96`). A core package that receives an `io.Writer` or an `*os.File` through a parameter and writes to it is invisible to all three. `[inference]` The convention page has to say so: the core takes values and returns values; interfaces from `io` are shell concerns.

## 2. Python: import-linter 2.15

### Contract types and what each does here

`[documented]` Five contract types ship: `forbidden`, `protected`, `layers`, `independence`, `acyclic_siblings` (`import-linter`, `docs/contract_types/index.md`). `forbidden` checks that a set of source modules does not import a set of forbidden modules, descendants included, indirect chains included, and the forbidden modules "may include root level external packages (i.e. `django`, but not `django.db.models`)" when `include_external_packages = True` is set (`docs/contract_types/forbidden.md`, "Configuration options"). `layers` orders modules high to low and fails any import, direct or indirect, from a lower layer to a higher one; `containers` prefixes the layer names; `(name)` makes a layer optional; `a | b` makes siblings in one layer independent and `a : b` lets them import each other (`docs/contract_types/layers.md`). `independence` forbids imports in any direction among a set (`docs/contract_types/independence.md`). `protected` allows a module to be imported only by an allow-list (`docs/contract_types/protected.md`).

`[inference]` For this repository: `layers` states the direction (`shell` above `core`), `forbidden` names the I/O the core may not touch. `independence` is not needed with two layers. `protected` would suit a later rule like "only `shell.nats` may import `nats`", which restricts the shell too; not proposed now. Every contract takes `broken_contract_guidance` since 2.14 (`docs/release_notes.md`, "2.14"), which puts the fix instruction in the failure output where a worker reads it.

### Standard-library modules can be forbidden

`[verified]` With `include_external_packages = true`, a `forbidden` contract from `aop.core` to `["subprocess", "socket", "asyncio", "os", "sys", "websockets", "nats"]` broke on all seven in the trial, including the four standard-library modules, and it did so without `websockets` or `nats` being installed; the graph just records the import target. Quoted from `uv run lint-imports --no-logo` (exit status 1, checked with `|| echo`):

```text
The core does no I/O
--------------------

aop.core is not allowed to import asyncio:

-   aop.core.decide -> asyncio (l.3)

aop.core is not allowed to import nats:

-   aop.core.decide -> nats (l.11)

aop.core is not allowed to import os:

-   aop.core.decide -> os (l.4, l.9)

aop.core is not allowed to import socket:

-   aop.core.decide -> socket (l.6)

aop.core is not allowed to import subprocess:

-   aop.core.decide -> aop.shell.runner (l.14)
    aop.shell.runner -> subprocess (l.3)

-   aop.core.decide -> subprocess (l.7)

aop.core is not allowed to import sys:

-   aop.core.decide -> sys (l.8)

aop.core is not allowed to import websockets:

-   aop.core.decide -> websockets (l.12)

Core modules take values and return values. Move the call to aop.shell and pass
its result in.
```

`[verified]` Line 9 of the trial module was `from os import path`; it is reported under `os` (`l.4, l.9`), so the `from` form is caught and `os.path` needs no separate entry. `[verified]` The indirect chain through `aop.shell.runner` is reported as a second route to `subprocess`, which is the documented "indirect imports will also be checked" behaviour (`docs/contract_types/forbidden.md`, first paragraph); `allow_indirect_imports = true` would suppress it and is not proposed. `[verified]` The `layers` contract broke on the same file: `aop.core is not allowed to import aop.shell: aop.core.decide -> aop.shell.runner (l.14)`.

`[verified]` The forbidden contract validates that external forbidden modules are root level: `tests/unit/contracts/test_forbidden.py:721-731` expects "subpackages of external packages are not valid", and `test_forbidden.py:208-222` expects "The top level configuration must have include_external_packages=True when there are external forbidden modules". So `os.path` or `asyncio.subprocess` cannot be listed; `os` and `asyncio` can, which is what the core needs anyway.

### What import-linter cannot see

`[inference]` Import graphs do not see calls. A core module that imports `pathlib` (which it should, for path values) can call `Path.write_text`; one that receives an open file can write to it. The question asked for `pathlib` write methods and `os` process and file APIs specifically; the honest answer is that no import checker covers method calls, and the module-level rule that `os` is forbidden entirely is the strongest thing the tool expresses. `pathlib` stays allowed because the core needs `Path` as a value type, and the rule against writing is prose plus the ruff supplement below.

`[verified]` ruff 0.16.9 has `TID251` (`banned-api`) and `TID253` (`banned-module-level-imports`) under `flake8-tidy-imports` (`ruff`, `crates/ruff_linter/src/rules/flake8_tidy_imports/rules/banned_api.rs` and `banned_module_level_imports.rs`), and ruff uses the closest configuration file per directory with `extend` to inherit the parent (`ruff/docs/configuration.md:254-289`). A `src/agent_orchestration_poc/core/ruff.toml` that extends the root and bans `os.remove` and `pathlib.Path.write_text` fired in the trial on `os.remove("x")` (`TID251 os.remove is banned: core packages delete nothing`) and on a module-level `subprocess` import, but `TID251` did not fire on `p.write_text("x")` where `p: pathlib.Path` is a parameter, nor on `pathlib.Path("y").write_text("z")`; output was `All checks passed!`. `[inference]` ruff resolves qualified names of imported symbols, not the types of expressions, so a banned method reaches only the `pathlib.Path.write_text` spelling nobody writes. `TID251` is worth adding for `os.remove`-style function bans if the coordinator wants belt and braces; it is not a substitute for import-linter and it is not a gate on `pathlib` methods.

`[inference]` The repository's root `pyproject.toml` is the only ruff configuration today, and a nested `ruff.toml` in `core/` is a second file for one directory. That is the price of a per-directory ban list in ruff; the `[tool.ruff.lint.per-file-ignores]` table only removes rules, it cannot add settings per path. Not proposed for the first slice.

### Python 3.14 support, pinning, and run time

`[verified]` `pyproject.toml` in the clone declares `requires-python = ">=3.10"`, a `Programming Language :: Python :: 3.14` classifier, and depends on `grimp>=3.17`, `click>=6`, `rich>=14.2.0`, `typing-extensions` (`import-linter/pyproject.toml:1-30`). `[documented]` Release notes: 2.5.1 "Officially support Python 3.14" and 2.9 "Bugfix: support Python 3.14 syntax" (`docs/release_notes.md`). `[verified]` The trial ran under CPython 3.14.6 from mise (`sys.version` printed `3.14.6 (main, Jun 11 2026, 03:55:33) [Clang 22.1.3 ]`) with import-linter 2.15 and grimp 3.17.

`[verified]` `uv add --dev import-linter` resolved import-linter 2.15 and grimp 3.17 into `uv.lock` in 0.6 s (the wheels were cached), and the `dev` group entry it wrote is `import-linter>=2.15`, matching the repository's existing `pytest>=9.1.1` style; the exact version lives in the lockfile, which the Python rules already require to be committed and installed with `uv sync --locked` (`.claude/rules/python.md`, "Interpreter and uv"). `[inference]` The `ui` extra (FastAPI and uvicorn for `import-linter explore`) stays out; `docs/get_started/install.md` documents it as optional since 2.11.

`[verified]` Run time on the trial (16 files): `Building graph took 0.005s.`; the whole `uv run lint-imports --no-logo` was 1.3 s on first run including uv's build of the editable package, and 0.15 s wall on a warm run. A cache directory `.import_linter_cache` is written by default (`docs/get_started/run.md`, `--cache-dir` and `--no-cache`). `[inference]` Add `.import_linter_cache/` to `.gitignore`, or run with `--no-cache` in the mise task since the package is tiny; the trial did not measure a difference.

### Proposed `[tool.importlinter]` block

`[inference]` For option 1 (`core` and `shell` subpackages), appended to `pyproject.toml`:

```toml
[tool.importlinter]
root_package = "agent_orchestration_poc"
include_external_packages = true
exclude_type_checking_imports = true

[[tool.importlinter.contracts]]
id = "core-shell-layers"
name = "The shell imports the core; the core never imports the shell"
type = "layers"
layers = ["shell", "core"]
containers = ["agent_orchestration_poc"]

[[tool.importlinter.contracts]]
id = "core-no-io"
name = "The core does no I/O"
type = "forbidden"
source_modules = ["agent_orchestration_poc.core"]
forbidden_modules = [
  "asyncio",
  "multiprocessing",
  "nats",
  "os",
  "select",
  "selectors",
  "shutil",
  "signal",
  "socket",
  "subprocess",
  "sys",
  "threading",
  "websockets",
]
broken_contract_guidance = """
Core modules take values and return values. Move the call into agent_orchestration_poc.shell and pass its result in.
"""
```

`[inference]` `exclude_type_checking_imports = true` lets a core module import a shell type under `if TYPE_CHECKING:` for an annotation without breaking the layer contract (`docs/get_started/configure.md`, "Top level configuration"); Python 3.14's deferred annotations make that guard rarer, but a `TypeAlias` to a shell type still needs it. Drop the line if the coordinator wants annotations counted as dependencies. `[inference]` `shutil`, `signal`, `select`, `selectors`, `threading`, and `multiprocessing` are added beyond the question's list because each is an I/O or process module a pure package has no use for; remove any the coordinator considers noise. `pathlib`, `json`, `dataclasses`, `datetime`, `uuid`, `re`, `typing`, and `collections` stay allowed.

`[verified]` The same shape with `aop` in place of `agent_orchestration_poc` and the seven-module list ran in the trial: two contracts broken with the violating module present, and `Analyzed 9 files, 5 dependencies. Contracts: 2 kept, 0 broken.` after it was removed (exit status 0, 0.15 s).

### Proposed mise task and hook

`[inference]` A `check:imports` task with `run = "uv run lint-imports --no-logo"`, added to the `check` aggregate's `depends` list next to `check:ruff` (`mise.toml`, "Aggregates"), and a `prek.toml` local hook mirroring the ruff one: `entry = "mise exec -- uv run lint-imports --no-logo"`, `types = ["python"]`, `pass_filenames = false`, because the linter takes no file arguments (`docs/get_started/run.md`, "Running using pre-commit", which uses `language: system` and `pass_filenames: false` for the same reason). `[documented]` The `--no-logo` flag exists since 2.14 (`docs/release_notes.md`) and keeps the ASCII art out of CI logs.

## 3. Go: depguard, go-arch-lint, and arch-go

### depguard through golangci-lint 2.14.0

`[verified]` golangci-lint 2.14.0 vendors `github.com/OpenPeeDeeP/depguard/v2 v2.2.1` (`golangci-lint/go.mod:33`) and its changelog records go1.27 support in v2.13.0 (`CHANGELOG.md:65`, already cited in `research/gates/go/notes.md`). The repository's `check:go` task and the `golangci-lint` prek hook run `golangci-lint run ./...` already (`mise.toml`, `prek.toml`), so enabling depguard is a `.golangci.yml` edit and nothing else: no new binary, no new pin.

`[documented]` Configuration shape: `linters.settings.depguard.rules.<name>` with `list-mode` (`original`, `strict`, `lax`), `files` (globs; `$all`, `$test`, `!` negation; `${base-path}` and `${config-path}` placeholders), `allow` (prefixes, `$gostd`, `$` suffix for exact), and `deny` as a list of `{pkg, desc}` (`golangci-lint/.golangci.reference.yml:352-392`). `[verified]` The golangci-lint adapter turns the `deny` list into depguard's map and compiles the analyzer with syntax-only loading (`pkg/golinters/depguard/depguard.go:13-53`), which is why the linter is cheap.

`[verified]` List-mode semantics from source (`depguard/settings.go:139-159`): `lax` allows an import unless it matches the deny list, or the matching allow entry is longer than the matching deny entry; `strict` denies unless it matches the allow list, with the same longer-wins tie-break. `[inference]` `lax` is the right mode for a core rule: the core may use any standard-library package except the ones named, and listing every allowed package in `strict` mode would need maintenance on every new import.

### Two prefix-matching traps, verified

`[verified]` Prefix lookup uses a sorted list and a binary search that compares the import against the single nearest entry (`depguard/settings.go:224-248`). Listing both `os` and `os/exec` in `deny` made `os/signal` and `os/user` escape: with `deny: [os, os/exec, net, syscall, ...]`, the trial reported `os` and `os/exec` and stayed silent on lines 10 and 11 (`os/signal`, `os/user`), because the nearest sorted entry for `os/user` is `os/exec`, which is not its prefix. With `os` alone in the list, all four were reported:

```text
internal/core/core.go:8:2: import 'os' is not allowed from list 'core': core packages do no I/O; move it to cmd/ or internal/backend/
internal/core/core.go:9:2: import 'os/exec' is not allowed from list 'core': core packages do no I/O; move it to cmd/ or internal/backend/
internal/core/core.go:10:2: import 'os/signal' is not allowed from list 'core': core packages do no I/O; move it to cmd/ or internal/backend/
internal/core/core.go:11:2: import 'os/user' is not allowed from list 'core': core packages do no I/O; move it to cmd/ or internal/backend/
```

`[inference]` Rule: never list a prefix and one of its own subpackages in the same `deny` list; list the shortest prefix only. The question's list (`os`, `os/exec`, `net`, `net/http`) must collapse to `os` and `net`.

`[verified]` `files` entries are OR'd, not AND'd (`depguard/settings.go:133-137`: a file matches if any glob matches and no negated glob matches). A second rule with `files: ["**/internal/core/**", "$test"]` meant to cover core tests matched every core file, and the non-test `core.go` was reported under both rule names. The working form for test files is a glob that ends in `_test.go`: `**/internal/core/**_test.go`, which in the trial reported only `core_test.go:5:2: import 'os/exec' is not allowed from list 'core-tests'`.

`[verified]` `allow` entries longer than a deny prefix win in `lax` mode: with `deny: net` and `allow: [net/netip, net/url]`, the trial reported `net/http` and stayed silent on `net/netip` and `net/url`. `[inference]` That is how the core keeps the pure `net/netip` and `net/url` value types while `net` itself and `net/http` stay out.

### go-arch-lint 1.19.0

`[verified]` `go.mod` says `go 1.25.0`; the release workflow builds with Go 1.25 (`.github/workflows/release.yml:30`); the mise `go:` backend built v1.19.0 with the local go1.27.1 (`go version -m` printed `go1.27.1`). Its config is a components-and-vendors model: `components` map names to directory globs, `vendors` map names to module import paths, `deps` say which components may depend on which and which vendors they `canUse`, and `depOnAnyVendor: false` makes unlisted vendors an error (`docs/syntax/README.md`; the project's own `.go-arch-lint.yml`).

`[verified]` Standard-library imports are always allowed: `checkImport` returns `true, nil` for `models.ImportTypeStdLib` before any rule is consulted (`internal/services/checker/checker_imports.go:107-108`; the type is set at `internal/models/resolved_file.go:38`). On the trial tree with `core` allowed to depend only on `registry` and no vendors, the run reported exactly one notice, the `internal/backend/tmux` import, and said nothing about `os`, `os/exec`, `net/http`, or `syscall`:

```text
Component core shouldn't depend on example.com/gotrial/internal/backend/tmux in .../internal/core/core.go:14

--
total notices: 1
```

`[inference]` go-arch-lint cannot express "core may not import `os`". It fails the operator's requirement on its own; its `deepScan` (method-call and dependency-injection analysis) and graph output are nice but do not compensate. Not recommended.

### arch-go 2.1.2

`[verified]` `go.mod` says `go 1.24.0` with `toolchain go1.25.7`; CI builds with 1.25.7 (`.github/workflows/ci.yml:55`); the mise `go:` backend built v2.1.2 with go1.27.1. Dependency rules take `shouldOnlyDependsOn` and `shouldNotDependsOn`, each with `internal`, `standard`, and `external` lists of `**.pkg.**` patterns (`README.md`, "Configuration"). A package is "standard" when its path has no dot or starts with `golang.org/x` (`internal/utils/packages/is_standard.go`). Packages are loaded with `golang.org/x/tools/go/packages` and `go/build` (`internal/utils/packages/get_packages.go`).

`[verified]` It does express the rule. With `shouldNotDependsOn.standard: ["os", "os.**", "net", "net.**", "syscall"]`, `internal: ["**.internal.backend.**"]`, and `external: ["github.com/nats-io/nats.go"]` for `**.internal.core`, the run reported every violation (`net/http`, `net/netip`, `net/url`, `os`, `os/exec`, `os/signal`, `os/user`, `syscall`, and the backend import), then failed the module at `COMPLIANCE RATE 75% [FAIL]` in 0.24 s. Note that `os` and `os.**` are both needed because the patterns are anchored regular expressions, not prefixes.

`[inference]` Against depguard: arch-go has no per-import allow override (the `net/netip` exception has to be expressed by not listing `net.**` and listing `net`, `net.http`, `net.mail`, and so on by hand), its `coverage` threshold of 100 percent demands that every package be matched by some rule, so every new shell package needs a rule or the threshold must drop, its output is a compliance report rather than file and line diagnostics (the `Package ... fails` block names the package, not the line), and it is a second tool with a second pin and its own config file. `[verified]` The project has had no feature release since 2.1.0 on 2025-11-27 (`CHANGELOG.md`). Nothing here is a defect; it is just redundant next to a linter the repository already runs.

### Comparison

| | depguard v2.2.1 (in golangci-lint 2.14.0) | go-arch-lint v1.19.0 | arch-go v2.1.2 |
| --- | --- | --- | --- |
| Denies standard-library packages | yes, by prefix (`[verified]`) | no, stdlib always allowed (`[verified]`) | yes, by pattern (`[verified]`) |
| Denies third-party modules | yes, by prefix | yes, via `vendors` and `canUse` | yes, `external` patterns |
| Denies in-module packages | yes, by prefix | yes, via `components` and `mayDependOn` | yes, `internal` patterns |
| Allow override inside a denied prefix | yes, longer allow wins in `lax` | not applicable | no |
| Scopes rules to test files | yes, `$test` or `**_test.go` globs | `excludeFiles` regex only | no |
| Diagnostics | file and line, with a suggestion string | file and line | package name and report table |
| Go 1.27 | built with go1.27.0 inside golangci-lint | binary built locally with go1.27.1; upstream targets 1.25 | binary built locally with go1.27.1; upstream targets 1.25 |
| Pin | already `golangci-lint = "2.14.0"` | new `"go:github.com/fe3dback/go-arch-lint" = "1.19.0"` | new `"go:github.com/arch-go/arch-go/v2" = "2.1.2"` |
| Wall time on the trial | 1.5 s for the whole `golangci-lint run ./...` | 1.3 s | 0.24 s |

### Recommended configuration

`[inference]` For option A (`internal/core/...` as the core tree), the `.golangci.yml` becomes:

```yaml
version: "2"

linters:
  default: standard
  enable:
    - depguard
  settings:
    depguard:
      rules:
        core:
          # Functional core: internal/core/... takes values and returns values.
          list-mode: lax
          files:
            - "**/internal/core/**"
            - "!$test"
          allow:
            - net/netip
            - net/url
          deny:
            - pkg: os
              desc: core packages do no I/O; the caller in cmd/ or an internal/ shell package passes values in
            - pkg: net
              desc: core packages open no sockets
            - pkg: syscall
              desc: core packages make no system calls
            - pkg: github.com/nats-io/nats.go
              desc: only internal/bus talks to the NATS client
            - pkg: github.com/nats-io/nats-server
              desc: only internal/bus embeds the NATS server
            - pkg: github.com/tbhb/agent-orchestration-poc/internal/backend
              desc: core packages never import a backend
            - pkg: github.com/tbhb/agent-orchestration-poc/internal/bus
              desc: core packages never import the bus
            - pkg: github.com/tbhb/agent-orchestration-poc/internal/registry
              desc: core packages never import the registry store
            - pkg: github.com/tbhb/agent-orchestration-poc/internal/term
              desc: core packages never import the terminal layer
            - pkg: github.com/tbhb/agent-orchestration-poc/internal/api
              desc: core packages never import the API server
        core-tests:
          # Core tests may read testdata through os but still spawn and connect nothing.
          list-mode: lax
          files:
            - "**/internal/core/**_test.go"
          deny:
            - pkg: os/exec
              desc: core tests spawn nothing
            - pkg: net
              desc: core tests open no sockets
            - pkg: github.com/nats-io
              desc: core tests need no broker
            - pkg: github.com/tbhb/agent-orchestration-poc/internal/backend
              desc: core tests never import a backend

formatters:
  enable:
    - gofumpt
  settings:
    gofumpt:
      module-path: github.com/tbhb/agent-orchestration-poc
```

`[inference]` Notes on the shape. The in-module deny entries name the shell packages individually rather than a prefix on `internal/`, because `internal/core` itself sits under that prefix and the longer-allow trick would need every core package listed. `net` is denied as a prefix and `net/netip` and `net/url` are allowed back as the pure value types; add `net/mail` the same way if a core package ever parses addresses. `os/exec`, `os/signal`, and `os/user` are covered by `os` and must not be listed separately (the trap above). The NATS module paths are those the NATS research recorded, `github.com/nats-io/nats.go` and `github.com/nats-io/nats-server/v2` (`experiments/00-system-assessment/nats-research.md:25`); `github.com/nats-io/nats-server` as a prefix covers the `/v2` path. `syscall` is denied outright; `golang.org/x/sys` is not in the module today and can be added when it is. `time` stays allowed for `time.Duration` values; a core function that needs "now" takes it as a parameter, which is prose, not a rule.

`[inference]` For option B, the same two rules apply with `files` enumerating the pure packages (`**/internal/registry/*.go`, `**/internal/bus/*.go`, ...) and `!$test`, and the in-module deny list naming each package's shell subpackage. Nothing else changes.

`[verified]` The trial's version of this config (module `example.com/gotrial`, `internal/core` plus `internal/registry` as core, one backend) produced these diagnostics on the seeded file, exit status 1, in 1.5 s wall for the whole `golangci-lint run ./...` (the `standard` linters ran as well):

```text
internal/core/core.go:5:2: import 'net/http' is not allowed from list 'core': core packages open no sockets (depguard)
internal/core/core.go:8:2: import 'os' is not allowed from list 'core': core packages do no I/O; move it to cmd/ or internal/backend/ (depguard)
internal/core/core.go:9:2: import 'os/exec' is not allowed from list 'core': core packages do no I/O; move it to cmd/ or internal/backend/ (depguard)
internal/core/core.go:10:2: import 'os/signal' is not allowed from list 'core': core packages do no I/O; move it to cmd/ or internal/backend/ (depguard)
internal/core/core.go:11:2: import 'os/user' is not allowed from list 'core': core packages do no I/O; move it to cmd/ or internal/backend/ (depguard)
internal/core/core.go:12:2: import 'syscall' is not allowed from list 'core': core packages make no syscalls (depguard)
internal/core/core.go:14:2: import 'example.com/gotrial/internal/backend/tmux' is not allowed from list 'core': core packages never import a backend (depguard)
internal/core/core_test.go:5:2: import 'os/exec' is not allowed from list 'core-tests': core tests spawn nothing (depguard)
```

`[verified]` With the core rewritten to import only `net/netip` and `strings`, and `cmd/d` importing `os`, `fmt`, the backend, and the core, the same config printed `0 issues.` and exited 0. `[verified]` The skeleton's `cmd/agentd/main.go` and `cmd/agentctl/main.go` import `os` (`cmd/*/main.go:7`) and are shell, so nothing in the current tree would fail the rule; the deliberately failing example the issue asks for has to be a throwaway file, as in the trial.

### Does depguard alone suffice

`[inference]` Yes, for the boundary the operator described. It denies every package in the question (`os`, `os/exec`, `net`, `net/http`, `syscall`, the NATS client, `internal/backend/*`) from a glob-defined core, with file and line diagnostics, in the linter the `check` task and CI already run, at Go 1.27, with no new pin. What it does not do: it does not check that the shell stays thin (no tool here does), it does not see I/O reaching the core through an interface parameter (no import checker does), and it does not draw a dependency graph (go-arch-lint's `graph` command does, and can be run by hand without adopting it as a gate). If the coordinator wants a positive statement of the architecture as a document rather than a deny list, arch-go's `describe` output is the closest thing, but that is a documentation want, not an enforcement gap.

## 4. Testing consequence

`[inference]` Core tests are plain: build the input value, call the function, compare the output value. There is nothing to mock because the core holds no connection, no clock, no file handle, no process; anything it would have needed is a parameter. In Go that is `internal/core/**/*_test.go` with table cases, `t.Run`, and `testdata/` for golden inputs, untagged, run by `go test -race -shuffle=on ./...` in `check:go` (`mise.toml`; `.claude/rules/go.md`, "Testing rules"). The `core-tests` depguard rule above lets those tests read `testdata/` through `os` while still refusing `os/exec`, `net`, and NATS. In Python that is `tests/core/` (or `tests/test_core_*.py`; pytest needs no `__init__.py` under `importlib` mode, `.claude/rules/python.md`, "Pytest") with no markers, run by the default `uv run pytest`.

`[inference]` Shell tests live next to their shell: `internal/bus`, `internal/backend/*`, `internal/term`, `internal/api`, and `cmd/*` in Go; `tests/shell/` in Python. They need real processes, sockets, or a broker, and the repository already has the gates for that: Go tests needing tmux or an external NATS executable go behind `//go:build integration` and `exec.LookPath` skips, with in-process embedded NATS tests untagged (`.claude/rules/go.md`, "Testing rules"; `research/gates/go/notes.md` section 3); Python process and socket tests carry `integration` or `socket` and are skipped unless `--run-integration` (`tests/conftest.py:1-25`; `pyproject.toml`, `[tool.pytest.ini_options].markers`). `[inference]` The consequence worth writing into the conventions pages: a test that needs a mock is a test of shell code that has core logic trapped in it. Move the logic into the core, test it there with values, and let the shell test be an integration test of the real thing.

`[inference]` One boundary the tools do not enforce and the pages should: shell tests may import the core (they exercise the real decision), but core tests never import a shell package, which the `core-tests` depguard rule and the `layers` contract (tests are outside the root package, so import-linter does not see them) only partly cover. In Python, `tests/core/` importing `agent_orchestration_poc.shell` is invisible to import-linter; a second `root_packages = ["agent_orchestration_poc", "tests"]` entry would make `tests` a root package and allow a `forbidden` contract from `tests.core` to `agent_orchestration_poc.shell`, which `docs/get_started/configure.md` permits for importable top-level directories. `[untested]` Whether `tests/` without `__init__.py` under `importlib` mode counts as importable for grimp was not tried; if it does not, the rule stays prose.

## 5. Draft rule lines

### `AGENTS.md`, cross-harness, five lines

- Functional core, imperative shell is binding (operator requirement, 2026-09-26): decisions and data transformations are pure functions in the core, side effects live in a thin shell at the edges, and a PR that puts I/O in the core or logic in the shell is not mergeable.
- Go: `internal/core/...` is the core; `cmd/`, `internal/bus`, `internal/registry`, `internal/backend/*`, `internal/term`, and `internal/api` are the shell. golangci-lint 2.14.0 `depguard` enforces the import boundary in `mise run check`.
- Python: `agent_orchestration_poc.core` is the core and `agent_orchestration_poc.shell` is the shell; `experiments/` scripts are shell. import-linter 2.15 enforces the layers and the forbidden I/O modules in `mise run check`.
- Core tests take values and return values with no mocks; a test that needs a mock is testing shell code that has core logic trapped in it. Shell tests are `integration` tests (the pytest marker; the Go build tag).
- The tools check imports, not calls: a core function that receives a writer, a connection, or a process handle is a boundary violation the reviewer catches, not the linter.

### `.claude/rules/go.md`, new section

- Go 1.27, golangci-lint 2.14.0: Put pure decision and data code under `internal/core/<topic>`; `depguard` denies `os`, `net` (except `net/netip` and `net/url`), `syscall`, `github.com/nats-io/*`, and every shell package there.
- Go 1.27: Write the shell in `cmd/*`, `internal/bus`, `internal/registry`, `internal/backend/*`, `internal/term`, and `internal/api`; a shell package calls into `internal/core` and passes values, never an `io.Writer`, `*os.File`, or connection.
- Go 1.27, golangci-lint 2.14.0: Fix a `depguard` finding by moving the I/O to the shell, never with `//nolint:depguard`; when editing the deny list, list only the shortest prefix (never `os` and `os/exec` together) and scope test rules with `**_test.go` globs.
- Go 1.27: Core tests are untagged table tests with values in and out and `testdata/` inputs; they never import `os/exec`, `net`, NATS, or a backend. Shell tests that need tmux, a socket, or an external NATS go behind `//go:build integration`.

### `.claude/rules/python.md`, new section

- Python 3.14, import-linter 2.15: Put pure code in `agent_orchestration_poc.core` and I/O in `agent_orchestration_poc.shell`; the `layers` contract forbids `core` importing `shell` and the `forbidden` contract forbids the core importing `os`, `sys`, `subprocess`, `socket`, `asyncio`, `shutil`, `signal`, `select`, `selectors`, `threading`, `multiprocessing`, `websockets`, and `nats`.
- Python 3.14: Core functions take values and return values; they may import `pathlib` for path values but never call a `Path` method that touches the file system, and they never receive an open file, socket, or process. Experiment scripts are shell: they call the core and do their own I/O.
- import-linter 2.15: Run `uv run lint-imports --no-logo` through the `check:imports` mise task; fix a broken contract by moving the import to the shell, never with `ignore_imports`.
- pytest 9.1.1: Core tests under `tests/core/` carry no markers and use no mocks; shell tests under `tests/shell/` carry `integration` or `socket` and run with `--run-integration`.

## 6. TypeScript candidates for phase 5, by name only

`[untested]` Not cloned or run, per the brief. `dependency-cruiser` (rule file with `forbidden` and `allowed` dependency rules over path regexes, including `core` may not depend on `node:fs`-style built-ins), Biome's `noRestrictedImports` lint rule (per-path allow and deny of import specifiers; Biome 2.5.14 is already pinned in `mise.toml`, which makes it the zero-install candidate if its rule can be scoped to a directory through Biome's `overrides`), and `eslint-plugin-boundaries` (element types by path glob and rules between them; needs ESLint, which the repository does not run). `[inference]` The phase 5 gate should try Biome first for the same reason depguard wins here: it is already in `check`.
