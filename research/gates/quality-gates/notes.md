# Quality gates research notes

Raw notes for the research halves of issue #62 (duplicate code and dead code) and issue #63 (complexity), gathered on 2026-09-26 in the `research/62-63-quality-gates` worktree. Codex writes the conventions page sections and the rules from these; nothing here changes `.golangci.yml`, `pyproject.toml`, `biome.json`, or `mise.toml`.

Every paragraph opens with an evidence label. `[verified]` means a command was run here and its output is quoted. `[documented]` means a claim read in a cloned source at the SHA in `versions.md`. `[inference]` means a judgement drawn from the evidence. `[untested]` means a claim nobody checked. Citations are `path:line` relative to the clone root, or a command with its output. Trial runs used a scratch copy of the worktree made with `git archive HEAD | tar -x -C "$(mktemp -d)"`, referred to below as the scratch copy; ruff ran read-only against the worktree itself.

The issues name `research/gates/duplicate-and-dead-code/` and `research/gates/complexity/` as the notes directories. The coordinator assigned both items to one worker and one directory, `research/gates/quality-gates/`, so the acceptance criteria paths need that substitution when the issues close.

## Summary

- Duplicate code: adopt jscpd 5.3.2 as the single gate for Go, Python, and TypeScript, at its defaults of 50 tokens and 5 lines, exact clones only. Leave golangci-lint's `dupl` off: it compares files inside one package at a time and missed the only clone in the tree.
- Dead code, Go: keep `unused` and add `deadcode` from golang.org/x/tools v0.50.0 as `deadcode -test ./...`, wrapped so any output fails, because the command exits 0 with findings.
- Dead code, Python: adopt vulture 2.16 at `min_confidence = 60` with `ignore_names = ["pytest_*"]` and `ignore_decorators = ["@pytest.fixture"]`. At 80 it reports only what ruff already reports.
- Complexity, Go: enable `gocognit` at 15, `gocyclo` at 15, `funlen` at its defaults of 60 lines and 40 statements with `_test.go` excluded, and `nestif` at its default of 5. Skip `cyclop` as a duplicate of `gocyclo` and `maintidx` as experimental.
- Complexity, Python: add ruff `C901`, `PLR0911`, `PLR0912`, `PLR0915`, and `PLR0917` at their defaults beside the existing `PLR0913`. Do not add radon or xenon to the gate.
- Complexity, TypeScript: enable Biome's `noExcessiveCognitiveComplexity` at 15, `noExcessiveLinesPerFunction` at 60, and `useMaxParams` at 5, each at level `error`, before the first UI slice.
- First run: every recommended gate passes on the current tree. The tree holds four Go functions and four Python functions, so the thresholds rest on tool defaults and documented guidance, not on a distribution from this code.
- CI shape: everything recommended joins the `check` aggregate. The measured added wall time on the skeleton is under three seconds.

## Duplicate code

### Go: golangci-lint dupl

[documented] `dupl` serializes each file's syntax tree and finds repeated sequences with a suffix tree. It compares node types and ignores node values, so `if a == 13 {}` and `if x == 100 {}` match once the sequence is long enough. The README states that this produces false positives. `golangci/dupl/README.md:3-11`.

[documented] The threshold is a token count, meaning a minimum length of the serialized node sequence. golangci-lint's default is 150 and the standalone command's default is 100. `golangci-lint/.golangci.reference.yml` under `linters.settings.dupl`; `golangci/dupl/README.md:40-41`.

[documented] golangci-lint runs `dupl` once per package. The linter passes `internal.GetGoFileNames(pass)` to the library, and that helper iterates `pass.Files`, which holds one package. `golangci-lint/pkg/golinters/dupl/dupl.go:52-53`; `golangci-lint/pkg/golinters/internal/util.go:20-28`.

[verified] That scope hides clones across packages. `cmd/agentd/main.go` and `cmd/agentctl/main.go` differ only in one string literal. golangci-lint with `dupl` at threshold 20 reported nothing for them, while the standalone command at the same threshold reported the pair:

```console
$ mise exec -- go run github.com/golangci/dupl@c99c5cf5c202c7e5bb1292e1212e7de4038324c8 -t 20 cmd internal
found 2 clones:
  cmd/agentctl/main.go:3,19
  cmd/agentd/main.go:3,19

Found total 1 clone groups.
```

[verified] The pair stops matching between 45 and 50 tokens, so neither default would report it: `dupl -t 45` printed two clone lines and `dupl -t 50`, `-t 60`, `-t 100`, and `-t 150` printed none.

[inference] Table tests are the main false-positive risk for `dupl`, because it ignores values: two table tests with the same row shape and loop body are structurally identical. The reference configuration's own example excludes `dupl` from `_test.go`. `golangci-lint/.golangci.reference.yml:4695-4702`.

[documented] `dupl` loads syntax only, so it adds no type-checking cost. `golangci-lint/pkg/golinters/dupl/dupl.go:49`.

### Python: pylint duplicate-code

[documented] Pylint's similarities checker (`duplicate-code`, R0801) hashes runs of consecutive stripped lines. The threshold is a line count, `min-similarity-lines`, default 4. Comments, docstrings, imports, and signatures are removed before comparison by default. `pylint/checkers/symilar.py:1-30`, `pylint/checkers/symilar.py:56`, `pylint/checkers/symilar.py:763-804`.

[verified] Pylint 4.0.9 ran on Python 3.14 and found nothing in `src` and `tests`. It took 1.88 seconds for three files, the slowest tool in this study:

```console
$ mise exec -- uv run --no-project --with pylint pylint --disable=all --enable=duplicate-code src tests
------------------------------------
Your code has been rated at 10.00/10
```

[inference] Adopting pylint for one checker brings a second Python linter, its astroid dependency, and a second suppression syntax beside ruff. A four-line threshold with signatures and imports stripped is also loose enough to flag short repeated argparse or fixture blocks. Neither cost buys anything jscpd lacks.

### Cross-language: jscpd

[documented] jscpd 5 is a Rust engine shipped as a self-contained binary through npm, PyPI, crates.io, and Homebrew. The PyPI wheel supports `uvx jscpd`. `jscpd/README.md:13`, `jscpd/README.md:42-48`, `jscpd/README.md:76`.

[documented] Go, Python, TypeScript, and TSX are all supported formats. `jscpd/FORMATS.md:55`, `jscpd/FORMATS.md:102`, `jscpd/FORMATS.md:130`, `jscpd/FORMATS.md:135`.

[documented] Thresholds are `--min-tokens`, default 50, and `--min-lines`, default 5; a clone must meet both. Mode `mild`, the default, drops whitespace tokens; `weak` also drops comments; `strict` keeps every token. `jscpd/docs/rust.md:76-81`, `jscpd/docs/rust.md:506`.

[documented] By default a clone is an exact token match, so identifiers and literal values must be equal. Matching renamed identifiers or changed literals requires the opt-in flags `--ignore-identifiers` and `--ignore-literals`. `jscpd/docs/rust.md:88-89`, `jscpd/docs/rust.md:447-448`.

[documented] Exit codes: 0 when no gate fired even if clones were reported, 1 when `--threshold` (a duplication percentage) is exceeded, and the `--exit-code` value, default 1, when at least one clone was found. `jscpd/docs/rust.md:334-343`.

[documented] Exclusions: `--ignore` takes comma-separated file globs, `.gitignore` is respected unless `--no-gitignore` is given, and `jscpd:ignore-start` and `jscpd:ignore-end` comments exclude a region. `jscpd --help`; `jscpd/docs/rust.md:506`, `jscpd/docs/rust.md:894`.

[documented] Options can live in `.jscpd.json` with camelCase keys. The documented example shows `path`, `reporters`, `minLines`, `minTokens`, `threshold`, `format`, `ignore`, and `ignorePattern`. `jscpd/docs/rust.md:372-386`.

[verified] At the defaults jscpd reports nothing on the tree and takes 9 milliseconds of its own time, 0.05 seconds of wall time through `uvx`:

```console
$ CI=1 mise exec -- uvx jscpd==5.3.2 --format go,python --ignore '**/research/imported/**,**/node_modules/**,**/.venv/**' --reporters console .
No duplicates found.
go      3 files   69 lines  316 tokens  0 clones
python  1 file    25 lines  113 tokens  0 clones
Found 0 clones.
time: 9.014ms
```

[verified] The table above is condensed from the console reporter's box drawing. Files shorter than `--min-tokens` are not counted as analyzed: lowering the threshold to 30 raised the file count from four to five.

[verified] jscpd sees across packages. At `--min-tokens 30` it reported the two `main.go` files as an exact clone of 13 lines and 40 tokens, ending just before the differing string literal:

```console
$ CI=1 mise exec -- uvx jscpd==5.3.2 --format go,python --min-tokens 30 --min-lines 5 --ignore '...' --reporters console .
Clone found (go)
 - cmd/agentctl/main.go [2:1 - 14:15] (13 lines, 40 tokens)
   cmd/agentd/main.go [2:1 - 14:15]
Found 1 clones.
```

[verified] With `--ignore-identifiers --ignore-literals` the same pair is reported at the default threshold as a `renamed` clone covering the whole file, 18 lines and 67 tokens. That is the behaviour `dupl` has all the time.

[verified] Both gating flags exit nonzero on a finding. `--exit-code` printed the summary line and failed; `--threshold 0` also printed `ERROR: jscpd found too many duplicates (11.8%) over threshold (0.0%)`.

[inference] Exact matching keeps the false-positive burden on table tests low. Two table tests share a loop body but differ in row values, field names, and the function under test, and an exact matcher stops at the first differing token. The only table test in the tree, `internal/version/version_test.go`, produced no finding at 30 tokens.

[inference] Experiment scripts are where exact clones will appear first, since each script repeats argument parsing and evidence recording. That repetition is what `src/agent_orchestration_poc/` exists to absorb, so the gate should cover `experiments/` and the fix should be a move into the helper package. A deliberate repeat gets `jscpd:ignore-start` and `jscpd:ignore-end` with a reason.

[untested] No experiment script exists yet, so the burden on them is a prediction. The first retro after phase 2 scripts land should check it.

### One tool or one per language

[inference] One tool is better here. jscpd covers all three languages with one threshold, one configuration, one suppression syntax, and one task; it found the cross-package Go clone that `dupl` inside golangci-lint cannot see; and it costs milliseconds. The per-language pair of `dupl` and pylint has two threshold units (tokens and lines), two matching semantics, a Go blind spot, and no TypeScript coverage.

[inference] The trade is that jscpd at its defaults misses renamed clones, which `dupl` catches. Turning on `--ignore-identifiers` later recovers that at the price of `dupl`'s false positives, so it should wait for retro evidence.

### Recommendation and configuration

[inference] Adopt jscpd 5.3.2, pinned in `mise.toml` as `"pipx:jscpd" = "5.3.2"`. `mise ls-remote pipx:jscpd` lists 5.3.2 as newest, and the repository already uses the `pipx:` backend for `ryl`. Add a `check:dupl` task:

```toml
[tasks."check:dupl"]
description = "Fail on duplicated code in Go, Python, and TypeScript with jscpd"
run = "jscpd --config .jscpd.json --exit-code cmd internal src tests experiments scripts apps packages"
```

[inference] Proposed `.jscpd.json`, using only keys the documentation shows:

```json
{
  "reporters": ["console"],
  "minLines": 5,
  "minTokens": 50,
  "format": ["go", "python", "typescript", "tsx", "javascript"],
  "ignore": [
    "**/research/imported/**",
    "**/node_modules/**",
    "**/.venv/**",
    "**/.worktrees/**",
    "**/testdata/**"
  ]
}
```

[verified] The equivalent command line ran clean in the scratch copy in 0.14 seconds of wall time: `jscpd --format go,python --min-tokens 50 --min-lines 5 --mode mild --exit-code --ignore '<globs>' --reporters console cmd internal src tests experiments scripts` printed `Found 0 clones.`

[untested] The `.jscpd.json` file itself was not loaded in a trial, and the `apps` and `packages` paths hold no source yet. The implementing item should run the task once and record the output.

[inference] Thresholds stay at the defaults of 50 tokens and 5 lines. The one known clone is 40 tokens, so the defaults pass today, and the gate first fires when a repeated block is roughly one and a half times the size of the skeleton's `main`.

## Dead code

### Go: unused

[documented] `unused` is in golangci-lint's `standard` set, which `.golangci.yml` already enables, and it needs type information. `golangci-lint/pkg/golinters/unused/unused.go` (`LoadModeTypesInfo`).

[documented] `unused` treats every exported function, type, variable, and constant as used by its package, and every exported method as used by its type. `go-tools/unused/unused.go:50-62`.

[documented] golangci-lint's defaults are lenient on top of that: field writes count as uses, and exported fields, function parameters, and local variables are all marked used. `golangci-lint/.golangci.reference.yml` under `linters.settings.unused`.

[verified] `unused` catches an unexported orphan. Adding `func orphan() string` to `internal/version` produced `internal/version/orphan.go:3:6: func orphan is unused (unused)`.

[verified] `unused` misses an exported function that nothing in the program calls. Adding `func Exported()` with a test that calls it produced `0 issues.` Every package here sits under `internal/`, so exported names are the normal way code is shared, and this blind spot covers most of the future code.

### Go: deadcode

[documented] `deadcode` loads the program, builds a call graph from each `main` function with Rapid Type Analysis, and reports every function not reachable. Only `main` packages are starting points. `golang/tools/cmd/deadcode/doc.go:6-18`.

[documented] `-test` adds test executables as starting points. The default `-filter` limits the report to the modules of the listed packages. Generated files and marker interface methods are not reported by default. `golang/tools/cmd/deadcode/doc.go:20-51`.

[documented] Limits: it does not follow `//go:linkname`, the result holds for one `GOOS`, `GOARCH`, and build tag set only, and a function reported dead may still be needed to satisfy an interface. `golang/tools/cmd/deadcode/doc.go:34-63`.

[verified] Both forms run clean on the skeleton, in about 1.5 seconds of wall time through `go run`. Each of these printed nothing:

```sh
mise exec -- go run golang.org/x/tools/cmd/deadcode@v0.50.0 ./cmd/...
mise exec -- go run golang.org/x/tools/cmd/deadcode@v0.50.0 -test ./...
```

[verified] `deadcode` exits 0 when it reports findings. With the orphan function present it printed `internal/version/orphan.go:3:6: unreachable func: orphan` and the exit status was 0. A gate has to fail on non-empty output.

[verified] The two forms treat test-only code differently. With `Exported()` called only from a test, `deadcode -test ./...` printed nothing and `deadcode ./cmd/...` printed `internal/version/exported.go:4:6: unreachable func: Exported`.

### What each one misses

| Case | `unused` | `deadcode ./cmd/...` | `deadcode -test ./...` |
| --- | --- | --- | --- |
| Unexported function nothing references | reported (verified) | reported (verified) | reported (verified) |
| Exported function only a test calls | missed (verified) | reported (verified) | missed (verified) |
| Exported function nothing calls | missed (documented) | reported (documented) | reported (documented) |
| Unused type, constant, variable, or struct field | reported (documented) | missed: functions only (documented) | missed: functions only (documented) |
| Code behind a build tag such as `integration` | analyzed for the active tags | one configuration per run (documented) | one configuration per run (documented) |

[inference] The tools are complements. `unused` covers non-function identifiers inside a package; `deadcode` covers exported functions across the program.

### Treating test-only code

[inference] Gate on `deadcode -test ./...`. Phase 2 builds packages such as `internal/bus` and `internal/registry` with tests before `cmd/agentd` calls them. The stricter form without `-test` would fail every one of those pull requests for code that is about to be wired in.

[inference] Run `deadcode ./cmd/...` without `-test` as a report at each checkpoint retro. Its output is the list of functions the binaries do not reach, which is the question a checkpoint asks. Promote it to the gate once the daemon reaches each package.

[untested] Integration tests behind `//go:build integration` are outside the default run. If helpers used only by those tests appear, add a second run with `-tags integration`.

### Python: vulture

[documented] Vulture parses each file, records defined and used names, and reports names defined but never used. It ignores scopes and matches on names alone. `vulture/README.md` under "How does it work?".

[documented] Each finding carries a fixed confidence by kind: 100 percent for unused arguments and unreachable code, 90 percent for imports, and 60 percent for attributes, classes, functions, methods, properties, and variables. The default minimum is 60. `vulture/README.md` under "Types of unused code"; `vulture/vulture/core.py:15`.

[documented] Built-in exemptions: in files matching `*/test/*`, `*/tests/*`, `*/test*.py`, or `*[-_]test.py`, functions and methods named `test_*`, the xunit-style setup and teardown names, and classes with `Test` in the name are ignored. Imports in `__init__.py` and names listed in `__all__` are treated as used. `vulture/vulture/core.py:18-28`, `vulture/vulture/core.py:60-100`.

[documented] Suppression options, in the README's order of preference: a whitelist module added to the scanned paths, which `--make-whitelist` generates; `--ignore-names` and `--ignore-decorators`; and `# noqa: F401` or `# noqa: F841`. Configuration lives under `[tool.vulture]` in `pyproject.toml`. `vulture/README.md` under "Handling false positives" and "Configuration".

[documented] Vulture 2.15 added Python 3.14 support and 2.16 is the current release. `vulture/CHANGELOG.md:7-20`.

[verified] At the default confidence vulture reports the two pytest hooks in `tests/conftest.py` and exits 3:

```console
$ mise exec -- uv run --no-project --with vulture==2.16 vulture src tests experiments scripts
tests/conftest.py:8: unused function 'pytest_addoption' (60% confidence)
tests/conftest.py:17: unused function 'pytest_collection_modifyitems' (60% confidence)
```

[verified] Both are false positives: pytest calls the hooks by name. `--min-confidence 80` and `--min-confidence 100` each printed nothing, and `--ignore-names 'pytest_*'` at confidence 60 also printed nothing and exited 0.

[inference] Pytest fixtures will be reported the same way. A fixture is requested through a parameter name, and vulture counts a parameter as a definition, not a use, so a fixture that no code calls directly looks unused. `--ignore-decorators "@pytest.fixture"` covers it; vulture reduces `@pytest.fixture(scope="module")` to `@pytest.fixture` before matching. `vulture/README.md` under "Ignoring names".

[untested] No fixture exists in the tree, so the fixture case was not reproduced.

[inference] Entry points: the package has no `[project.scripts]` entry, and `tests/test_package.py` asserts there is no `main`. Experiment scripts that define `main()` and call it under `if __name__ == "__main__":` use the name in the same file, so vulture counts it as used. A future console script entry needs its function added to `ignore_names` or a whitelist.

[inference] A minimum confidence of 80 is not worth running. It leaves only imports, arguments, and unreachable code, and ruff already reports unused imports (`F401`, on by default) and unused arguments (`ARG`, selected in `pyproject.toml`). The findings ruff cannot produce, unused functions and classes, all sit at 60.

### Recommendation and configuration

[inference] Go: keep `unused`; pin `"go:golang.org/x/tools/cmd/deadcode" = "0.50.0"` in `mise.toml`, which `mise ls-remote` lists; and add a wrapper script because of the exit status:

```sh
#!/usr/bin/env sh
# Fail when deadcode reports any function unreachable from the binaries or the tests.
set -eu
cd "$(dirname "$0")/.."
out=$(deadcode -test ./...)
if [ -n "$out" ]; then
    printf '%s\n' "$out"
    exit 1
fi
```

[inference] Python: add `vulture==2.16` to the `dev` dependency group and configure it in `pyproject.toml`:

```toml
[tool.vulture]
paths = ["src", "tests", "experiments", "scripts"]
exclude = ["research/imported/"]
min_confidence = 60
ignore_names = ["pytest_*"]
ignore_decorators = ["@pytest.fixture"]
```

[verified] The equivalent command line, `vulture --min-confidence 60 --ignore-names 'pytest_*' --ignore-decorators '@pytest.fixture' src tests experiments scripts`, exited 0 in 0.33 seconds.

[inference] One `check:deadcode` task runs both: `scripts/check-deadcode.sh` and `uv run vulture`. When a real false positive appears that the two ignore settings do not cover, add `vulture_whitelist.py` to `paths` with the name and a comment giving the reason.

[documented] TypeScript, for later: Biome's `noUnusedVariables`, `noUnusedImports`, `noUnusedFunctionParameters`, and `noUnusedPrivateClassMembers` are all in the recommended preset that `biome.json` enables. `biome/crates/biome_js_analyze/src/lint/correctness/no_unused_variables.rs:204-216` and the three sibling files. Those work inside one file. For unused exports and files across a program, jscpd's `--dead-code` mode covers JavaScript, TypeScript, and Python from entry points. `jscpd/README.md:97`; `jscpd/docs/rust.md:562-637`.

[verified] `jscpd --dead-code --format python src tests` printed `No dead code found. Analyzed 3 files, 8 declarations, 2 entry points.` It did not flag the pytest hooks.

[inference] jscpd's dead-code mode is new in the 5.x line and is not recommended for the Python gate over vulture yet. It is the candidate to evaluate for TypeScript when the first UI slice lands, since the tool will already be pinned.

## Complexity

### Go metrics and defaults

| Linter | Metric | Setting | golangci-lint default | Source |
| --- | --- | --- | --- | --- |
| `gocyclo` | Cyclomatic: 1, plus 1 for each `if`, `for`, `case`, `&&`, `\|\|` | `min-complexity` | 30, "we recommend 10-20" | `gocyclo/README.md`; `.golangci.reference.yml` under `linters.settings.gocyclo` |
| `cyclop` | Cyclomatic per function, plus an optional package average | `max-complexity`, `package-average` | 10, and 0.0 (off) | `cyclop/README.md`; `.golangci.reference.yml` under `linters.settings.cyclop` |
| `gocognit` | Cognitive: increments for branches, jumps to labels, and recursion, plus a nesting increment | `min-complexity` | 30, "we recommend 10-20" | `gocognit/README.md`; `.golangci.reference.yml` under `linters.settings.gocognit` |
| `funlen` | Function length in lines and in statements | `lines`, `statements`, `ignore-comments` | 60, 40, true | `funlen/README.md`; `.golangci.reference.yml` under `linters.settings.funlen` |
| `nestif` | Nesting of `if` statements, scored by the cognitive nesting rules | `min-complexity` | 5 | `nestif/README.md`; `.golangci.reference.yml` under `linters.settings.nestif` |
| `maintidx` | Maintainability index from cyclomatic complexity, Halstead volume, and lines | `under` | 20 | `maintidx/README.md`; `.golangci.reference.yml` under `linters.settings.maintidx` |

[documented] All six load syntax only. `golangci-lint/pkg/golinters/{gocyclo,gocognit,cyclop,funlen,nestif,maintidx}/*.go` each call `WithLoadMode(goanalysis.LoadModeSyntax)`.

[documented] Cyclomatic and cognitive scores diverge on the shapes Go uses most. A `switch` with three cases scores 4 cyclomatic and 1 cognitive; nested loops score more cognitive than cyclomatic. `gocognit/README.md` under "Comparison with cyclomatic complexity".

[documented] The maintainability index is described as experimental by its own linter's README and by radon's documentation. `maintidx/README.md` under "What is maintainability index"; `radon/docs/intro.rst` in the note closing the "Maintainability Index" section.

[documented] golangci-lint cannot vary a threshold by path. Exclusion rules switch a linter off for a path, a message text, or a source pattern. `golangci-lint/.golangci.reference.yml:4671-4735`.

[verified] golangci-lint reports one issue per line by default, which hides all but one linter's finding for a function. The distribution run below needed `--uniq-by-line=false`, `--max-same-issues=0`, and `--max-issues-per-linter=0` to show every metric.

### Go thresholds

[inference] Cognitive complexity is the primary metric, at 15. It tracks nesting, which is what makes orchestration code hard to follow, and it does not punish a flat `switch` over message kinds. Fifteen sits inside golangci-lint's recommended 10 to 20 and equals Biome's default for the same metric, so Go and TypeScript share one number.

[inference] Cyclomatic complexity is the secondary metric, at 15, through `gocyclo`. Each `if err != nil` adds a point, so shell code that makes several fallible calls scores higher in Go than the same logic does in Python. Ten, ruff's default, would flag ordinary shell functions; 15 leaves room for about five error checks on top of real branching.

[inference] `cyclop` is skipped. It measures the same thing as `gocyclo`, and its one extra, the package average, is off by default and has no evidence behind any value yet.

[inference] `funlen` runs at its defaults of 60 lines and 40 statements, the tool's one-screen rule, with `_test.go` excluded. The Go rules require named table tests, and a table test grows by rows without growing in logic. `gocognit` and `gocyclo` still cover tests.

[inference] `nestif` runs at its default of 5. It overlaps `gocognit` but reports the specific `if` statement, which makes the finding faster to act on.

[inference] `maintidx` is skipped as a gate. Two sources call the metric experimental, and its inputs are already gated one by one.

[inference] Functional core and imperative shell (#58): the thresholds apply everywhere to start. If the shell proves noisy, the available lever is an exclusion rule that drops `funlen` or `gocyclo` for the shell paths, such as `^cmd/` and `^internal/backend/`. The core never gets an exclusion. No evidence supports loosening anything today.

### Go configuration

[verified] This configuration passed `golangci-lint config verify` and reported `0 issues.` in the scratch copy:

```yaml
version: "2"

linters:
  default: standard
  enable:
    - funlen
    - gocognit
    - gocyclo
    - nestif
  settings:
    funlen:
      lines: 60
      statements: 40
    gocognit:
      min-complexity: 15
    gocyclo:
      min-complexity: 15
    nestif:
      min-complexity: 5
  exclusions:
    rules:
      - path: _test\.go
        linters:
          - funlen

formatters:
  enable:
    - gofumpt
  settings:
    gofumpt:
      module-path: github.com/tbhb/agent-orchestration-poc
```

### Python: what ruff covers

| Rule | Measures | Setting | Default | Status in ruff 0.16.9 | Selected today |
| --- | --- | --- | --- | --- | --- |
| `C901` | McCabe cyclomatic complexity | `lint.mccabe.max-complexity` | 10 | stable | no |
| `PLR0911` | Return statements | `lint.pylint.max-returns` | 6 | stable | no |
| `PLR0912` | Branches | `lint.pylint.max-branches` | 12 | stable | no |
| `PLR0913` | Arguments | `lint.pylint.max-args` | 5 | stable | yes |
| `PLR0915` | Statements, a length proxy | `lint.pylint.max-statements` | 50 | stable | no |
| `PLR0917` | Positional arguments | `lint.pylint.max-positional-args` | 5 | stable | no |
| `PLR0904` | Public methods | `lint.pylint.max-public-methods` | 20 | preview | no |
| `PLR0914` | Local variables | `lint.pylint.max-locals` | 15 | preview | no |
| `PLR0916` | Boolean expressions | `lint.pylint.max-bool-expr` | 5 | preview | no |
| `PLR1702` | Nested blocks | `lint.pylint.max-nested-blocks` | 5 | preview | no |

[documented] Defaults come from `ruff/crates/ruff_workspace/src/options.rs:3193-3202` for mccabe and `ruff/crates/ruff_workspace/src/options.rs:3645-3705` for the pylint settings.

[verified] Stability comes from `mise exec -- uv run ruff rule <CODE>` for each code. The four preview rules print "This rule is in preview and is not stable. The `--preview` flag is required for use." Selecting `PLR1702` without preview printed `warning: Selection PLR1702 has no effect because preview is not enabled.`

[inference] Python has no cognitive complexity metric and no stable nesting metric among the candidates. Ruff's nesting rule is preview, the Python rules forbid preview, and radon measures cyclomatic complexity and the maintainability index only. Cyclomatic complexity, branches, and statements together are the available substitute.

### Python: what radon and xenon add

[documented] Radon computes cyclomatic complexity with letter ranks (A is 1 to 5, B is 6 to 10, C is 11 to 20, up to F at 41 and over), the maintainability index with ranks (A is 20 to 100), raw line counts, and Halstead metrics. `radon/docs/commandline.rst:69-77`, `radon/docs/commandline.rst:252-256`; `radon/docs/intro.rst`.

[documented] Xenon wraps radon as a gate with three thresholds given as ranks: `--max-absolute` per block, `--max-modules` per module, and `--max-average` across the code base. `xenon/README.rst` under "The command line".

[documented] Radon counts differently from ruff's mccabe: `assert`, `with`, and each comprehension add a point. `radon/docs/intro.rst` in the "Cyclomatic Complexity" table. `--no-assert` removes the first. `radon/docs/commandline.rst:174`.

[verified] The difference is visible on the tree. Radon scored `pytest_collection_modifyitems` at 5 and `test_package_is_a_library_without_an_entry_point` at 3; ruff's `C901` scored the first at 4 and the second at 1:

```console
$ mise exec -- uv run --no-project --with radon==6.0.1 radon cc -s -a --total-average src tests
tests/conftest.py
    F 17:0 pytest_collection_modifyitems - A (5)
    F 8:0 pytest_addoption - A (1)
tests/test_package.py
    F 8:0 test_package_is_a_library_without_an_entry_point - A (3)
    F 14:0 test_integration_marker_is_registered_and_gated - A (2)

4 blocks (classes, functions, methods) analyzed.
Average complexity: A (2.75)
$ mise exec -- uv run ruff check --select C901 --config 'lint.mccabe.max-complexity=1' --output-format concise .
tests/conftest.py:17:5: C901 `pytest_collection_modifyitems` is too complex (4 > 1)
```

[documented] Maintenance: radon's last commit is 2024-10-20 and xenon's is 2024-10-21. Radon's `setup.py` lists classifiers up to Python 3.9, and xenon's README says it is tested up to 3.12. `radon/setup.py:51-55`; `xenon/README.rst` under "Installation".

[verified] Both still run on Python 3.14. `radon mi -s src tests` ranked all three files A, and `xenon --max-absolute B --max-modules A --max-average A src tests` exited 0.

[inference] Radon and xenon add three things over ruff: the maintainability index, a per-module aggregate, and a code-base average. The first is experimental by radon's own word, and the other two are aggregates with no evidence behind a threshold. Against that, the tools have had no commits in two years, declare no support for the pinned Python, and would put a second cyclomatic number beside ruff's that disagrees with it on every test function.

[inference] Do not add radon or xenon to the gate. Run `radon cc -a` and `radon mi` ad hoc at a retro if a distribution is wanted, through `uv run --with radon==6.0.1` so nothing is pinned.

### Python configuration

[inference] Add five codes to `extend-select` in `pyproject.toml` and leave every threshold at its default. Writing the defaults out makes the numbers visible where retros will edit them:

```toml
[tool.ruff.lint]
extend-select = [
  # ...existing entries...
  "C901",  # mccabe cyclomatic complexity
  "PLR0911",  # too many return statements
  "PLR0912",  # too many branches
  "PLR0915",  # too many statements
  "PLR0917",  # too many positional arguments
]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-args = 5
max-branches = 12
max-positional-args = 5
max-returns = 6
max-statements = 50
```

[verified] `mise exec -- uv run ruff check --extend-select C901,PLR0911,PLR0912,PLR0915,PLR0917 .` printed `All checks passed!` against the worktree in 0.10 seconds.

[inference] Ten is ruff's default and the top of radon's rank B, "well structured and stable". Python has no `if err != nil` inflation, so the default needs no allowance. Experiment scripts keep the same thresholds: `experiments/**` is exempt from docstring, annotation, and print rules today, but a script too complex to read is weak evidence.

### TypeScript: Biome's complexity group

[documented] The rules in the group that measure complexity, by name: `noExcessiveCognitiveComplexity` (default maximum 15, options key `maxAllowedComplexity`, range 1 to 254), `noExcessiveLinesPerFunction` (default 50, key `maxLines`, with `skipBlankLines` and `skipIifes`, since 2.0.0), `useMaxParams` (default 4, key `max`, since 2.2.0), and `noExcessiveNestedTestSuites` (maximum `describe` depth 5). `biome/crates/biome_js_analyze/src/lint/complexity/no_excessive_cognitive_complexity.rs:28-73`, `no_excessive_lines_per_function.rs:18-127`, `use_max_params.rs:71-79`, `no_excessive_nested_test_suites.rs:57-105`; `biome/crates/biome_rule_options/src/`.

[documented] None of the four is in the recommended preset, and `noExcessiveCognitiveComplexity` has severity `Information`. Each has to be enabled by name at level `error` to fail `biome check`. `no_excessive_cognitive_complexity.rs:72-73`.

[documented] The other 45 rules in the group are simplification rules such as `noUselessCatch`, `noForEach`, and `useOptionalChain`, not metrics. Directory listing of `biome/crates/biome_js_analyze/src/lint/complexity/`.

[inference] Proposed addition to `biome.json` before the first UI slice. The cognitive threshold matches Go's 15, the length threshold matches `funlen`'s 60, and the parameter limit matches ruff's 5:

```json
{
  "linter": {
    "enabled": true,
    "rules": {
      "preset": "recommended",
      "complexity": {
        "noExcessiveCognitiveComplexity": {
          "level": "error",
          "options": { "maxAllowedComplexity": 15 }
        },
        "noExcessiveLinesPerFunction": {
          "level": "error",
          "options": { "maxLines": 60 }
        },
        "useMaxParams": {
          "level": "error",
          "options": { "max": 5 }
        }
      }
    }
  }
}
```

[untested] This Biome configuration was not run. The tree's only JavaScript outside `docs/` is `scripts/mermaid-check/check.mjs`, and the implementing item should run `biome check` with the rules on and record what that file scores.

## First run

[verified] Surface measured: the Go files under `cmd/` and `internal/` and the Python files `src/agent_orchestration_poc/__init__.py`, `tests/conftest.py`, and `tests/test_package.py`. `git ls-files '*.py'` shows no Python under `experiments/` or `scripts/`. `research/imported/` was excluded from every run.

### Recommended gates

| Gate | Command | Result | Wall time |
| --- | --- | --- | --- |
| Go complexity, with `standard` | `golangci-lint run -c <recommended config> ./...` | `0 issues.` | 1.35 s cold, 0.36 s warm |
| Go dead code | `go run golang.org/x/tools/cmd/deadcode@v0.50.0 -test ./...` | no output | 1.48 s |
| Go dead code, report form | `go run golang.org/x/tools/cmd/deadcode@v0.50.0 ./cmd/...` | no output | not timed separately |
| Duplicates, all languages | `jscpd --format go,python --min-tokens 50 --min-lines 5 --mode mild --exit-code ...` | `Found 0 clones.` | 0.14 s |
| Python dead code | `vulture --min-confidence 60 --ignore-names 'pytest_*' --ignore-decorators '@pytest.fixture' src tests experiments scripts` | no output, exit 0 | 0.33 s |
| Python complexity | `ruff check --extend-select C901,PLR0911,PLR0912,PLR0915,PLR0917 .` | `All checks passed!` | 0.10 s |

[verified] Times are wall clock on macOS arm64 around `mise exec`, measured with `date +%s.%N` before and after. The cold golangci-lint figure followed `golangci-lint cache clean`.

### Go distribution

[verified] With every threshold at its floor, the four Go functions score as follows. The command was `golangci-lint run -c .golangci.dist.yml --max-same-issues=0 --max-issues-per-linter=0 --uniq-by-line=false --output.json.path=stdout ./...`:

| Function | Cyclomatic | Cognitive | Statements | Maintainability index |
| --- | --- | --- | --- | --- |
| `cmd/agentd` `main` | 3 | 2 | 5 | 64 |
| `cmd/agentctl` `main` | 3 | 2 | 5 | 64 |
| `internal/version` `String` | 1 | below 2 | below 2 | 80 |
| `internal/version` `TestString` | 3 | 4 | 3 | 51 |
| `internal/version` `TestDefaultIsDev` | 2 | below 2 | 2 | 71 |

[verified] The floor configuration, `.golangci.dist.yml` in the scratch copy, was:

```yaml
version: "2"
linters:
  default: none
  enable: [dupl, gocyclo, gocognit, cyclop, funlen, nestif, maintidx]
  settings:
    dupl: { threshold: 20 }
    gocyclo: { min-complexity: 1 }
    gocognit: { min-complexity: 1 }
    cyclop: { max-complexity: 1 }
    funlen: { lines: 1, statements: 1 }
    nestif: { min-complexity: 1 }
    maintidx: { under: 100 }
```

[verified] `nestif` and `dupl` reported nothing at their floors. "Below 2" means the linter stayed silent with its threshold at 1.

[inference] The table test has the lowest maintainability index in the tree, 51, while being the simplest code to read. That supports leaving `maintidx` out.

### Python distribution

| Function | ruff `C901` | radon cyclomatic |
| --- | --- | --- |
| `pytest_collection_modifyitems` | 4 | 5 |
| `pytest_addoption` | 1 | 1 |
| `test_package_is_a_library_without_an_entry_point` | 1 | 3 |
| `test_integration_marker_is_registered_and_gated` | 1 | 2 |

[verified] Radon's maintainability index was 100.00 for `__init__.py` and `conftest.py` and 90.75 for `test_package.py`.

### What the first run does and does not show

[inference] The highest scores in the tree are cyclomatic 4, cognitive 4, and 5 statements, against proposed limits of 10 or 15, 15, and 40. The thresholds cannot be calibrated from eight functions. They start from tool defaults and documented recommendations, and the first retro with phase 2 code should rerun the two distribution commands and adjust.

[verified] One finding is worth an issue under the out-of-scope rule of #62: `cmd/agentd/main.go` and `cmd/agentctl/main.go` are a 40-token exact clone, under the gate's threshold today. It will cross 50 tokens as soon as both gain a second shared subcommand.

## CI shape

[verified] CI runs one job, `check`, which calls `mise run check` on `ubuntu-latest` after restoring the mise cache. `.github/workflows/check.yml`. The three most recent runs on 2026-09-26 took 75, 78, and 104 seconds from creation to completion, by `gh run list --workflow=check.yml`.

[inference] Everything recommended joins the `check` aggregate. No tool here needs a pull request context, a network call, or more than about a second.

| Task | Change | Measured here | Estimate at 50 times the code |
| --- | --- | --- | --- |
| `check:go` | four linters added to `.golangci.yml`; no new command | no measurable change: 1.35 s cold with them, 1.04 s cold in the earlier all-linters trial | under 1 s added; the four load syntax only, and type checking for `standard` dominates |
| `check:ruff` | five codes added to `extend-select`; no new command | 0.10 s total | under 0.5 s |
| `check:dupl` | new: jscpd | 0.14 s | under 1 s; the engine reported 19 ms and runs on all cores |
| `check:deadcode` | new: `deadcode -test ./...` and vulture | 1.48 s and 0.33 s | 5 to 15 s for `deadcode`, which type-checks and builds a call graph; under 1 s for vulture |

[inference] The 50-times column is an estimate, not a measurement. `deadcode` is the one to watch, since it loads the whole program including test executables, and the Go build cache that `go test` fills in the same job will cover most of the loading.

[inference] Install cost: `deadcode` through the `go:` backend compiles once and then lives in the mise cache that `jdx/mise-action` restores. jscpd through `pipx:` downloads a 6.2 MiB wheel. Vulture arrives with `uv sync` from `uv.lock`.

[inference] Pre-commit: leave the new tasks out of `prek.toml`. `golangci-lint` and `ruff` hooks already run there and pick up the new rules from configuration. jscpd and `deadcode` are whole-tree checks, and the `check` aggregate is where whole-tree checks run.

[inference] Runs outside the gate, on demand or at checkpoint retros: `deadcode ./cmd/...` without `-test`, the two distribution commands under "First run", and `radon cc -a` if a second opinion on Python is wanted.

## Draft rules

Each line names the tool version, in the style of the existing rules files. Codex owns the final wording.

### For `.claude/rules/go.md`

- Go 1.27, golangci-lint 2.14.0: keep functions under cognitive complexity 15 (`gocognit`) and cyclomatic complexity 15 (`gocyclo`); split the function when either fires.
- Go 1.27, golangci-lint 2.14.0: keep functions within 60 lines and 40 statements (`funlen`); `_test.go` files are exempt so table tests can grow by rows.
- Go 1.27, golangci-lint 2.14.0: keep nested `if` complexity under 5 (`nestif`); return early or extract a function.
- Go 1.27, golangci-lint 2.14.0: do not enable `dupl`, `cyclop`, or `maintidx`; jscpd covers duplication, `gocyclo` covers cyclomatic complexity, and the maintainability index is experimental.
- Go 1.27, deadcode from golang.org/x/tools 0.50.0: every function must be reachable from `cmd/agentd`, `cmd/agentctl`, or a test; `check:deadcode` runs `deadcode -test ./...` and fails on any output.
- Go 1.27, deadcode 0.50.0: delete a function the check reports; do not keep code for later use.
- Go 1.27, jscpd 5.3.2: do not repeat a block of 50 tokens and 5 lines; move shared code into an `internal/` package. Mark a deliberate repeat with `// jscpd:ignore-start` and `// jscpd:ignore-end` and a reason.
- Go 1.27, golangci-lint 2.14.0: complexity limits apply to the functional core without exception; request a shell exclusion in the pull request with the finding quoted.

### For `.claude/rules/python.md`

- ruff 0.16.9: keep functions at McCabe complexity 10 or less (`C901`), 12 branches (`PLR0912`), 6 returns (`PLR0911`), and 50 statements (`PLR0915`).
- ruff 0.16.9: keep signatures to 5 arguments (`PLR0913`) and 5 positional arguments (`PLR0917`); group related values in a dataclass or make them keyword-only.
- ruff 0.16.9: do not select `PLR0904`, `PLR0914`, `PLR0916`, or `PLR1702`; they are preview rules.
- vulture 2.16: every function, class, and variable must be used; `check:deadcode` runs vulture at confidence 60 over `src`, `tests`, `experiments`, and `scripts`.
- vulture 2.16: pytest hooks named `pytest_*` and functions decorated with `@pytest.fixture` are exempt by configuration; add any other false positive to `vulture_whitelist.py` with a reason, not a `noqa` comment.
- jscpd 5.3.2: do not repeat a block of 50 tokens and 5 lines across scripts or tests; move shared code into `src/agent_orchestration_poc/`. Mark a deliberate repeat with `# jscpd:ignore-start` and `# jscpd:ignore-end` and a reason.
- radon 6.0.1, xenon 0.9.3: not part of the gate; run `uv run --with radon==6.0.1 radon cc -a` by hand for a distribution.

### For the TypeScript rules, when they exist

- Biome 2.5.14: keep functions at cognitive complexity 15 or less (`noExcessiveCognitiveComplexity`), 60 lines (`noExcessiveLinesPerFunction`), and 5 parameters (`useMaxParams`).
- jscpd 5.3.2: the same 50-token, 5-line duplicate rule covers `.ts` and `.tsx`.
