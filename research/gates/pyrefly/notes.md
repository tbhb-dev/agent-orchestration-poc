# Pyrefly research notes

Raw notes for issue #61, gathered on 2026-09-26 in the `tooling-61-pyrefly` worktree. They replace section 5 of `research/gates/python/notes.md`, which evaluated ty; the operator required strict pyrefly on 2026-09-26. Codex rewrites the Typing sections of the conventions page and `.claude/rules/python.md` from these and writes the decision record.

Every paragraph opens with an evidence label. `[verified]` means a command was run here and its output is quoted. `[observed]` means behaviour seen without a dedicated test. `[documented]` means a claim read in the pyrefly clone at the SHA in `versions.md`. `[inference]` means a judgement drawn from the evidence. `[untested]` means a claim nobody checked. Citations are `path:line` relative to the clone root at HEAD `a778c3bc`, or `path@1.3.1:line` for source read at the `1.3.1` tag (`3e3177d0`) through `git show`.

## Summary

- pyrefly 1.3.1 (PyPI, 2026-09-14) is the newest stable release; the docs at HEAD describe 1.4.0-dev.1 plus 477 commits, and the configuration sections used here are unchanged since the 1.3.1 tag.
- Strict mode is the `preset = "strict"` configuration option. It turns six off-by-default error kinds to errors and enables strict callable and partial subtyping. The proposal adds four more kinds and `min-severity = "warn"` so warnings gate too.
- pyrefly does not read `requires-python`; `python-version = "3.14"` is set explicitly. The interpreter that `uv run` puts first on `PATH` is what pyrefly queries, so the mise-pinned 3.14.6 in `.venv` supplies the site-package path.
- The `src/` layout is understood without configuration (import root heuristic) and `search-path = ["src"]` pins it. `tests/` and `experiments/` are checked with the annotation-completeness kinds relaxed through sub-configs, mirroring the ruff `ANN` per-file-ignores. `research/imported/` and `design-sketch/` are excluded.
- Python 3.14 syntax that ruff's py314 formatter emits (`except A, B:`) and template strings parse cleanly; the bundled typeshed carries the 3.14 stdlib.
- The strict run on the helper package and tests reports `0 diagnostics`; a throwaway probe file produced the expected strict errors and a warning alone made the check exit 1.

## 1. Version, installation, and the uv route

[verified] `mise exec -- uv run --with pyrefly pyrefly --version` printed `pyrefly 1.3.1`, so 1.3.1 is what PyPI resolves for the default index. `mise exec -- npm view pyrefly version` printed `0.0.1-security`, a placeholder package, confirming npm is not the route. The clone's `git tag --sort=-v:refname | head -3` lists `1.4.0-dev.1`, `1.3.1`, `1.3.0`; `version.bzl:27` at HEAD reads `VERSION = "1.4.0-dev.1"`.

[documented] Releases are on PyPI "with a new minor release intended every ~2 months" (`website/docs/installation.mdx:13`). Dev releases "don't carry the same stability or compatibility guarantees as a stable release — don't pin production projects to a dev version" (`release_notes/release-notes-v1.4.0-dev.1.md:3-5`). 1.3.1 is a one-fix patch on 1.3.0 for a startup panic with empty or relative base paths (`release_notes/release-notes-v1.3.1.md:1-9`). 1.3.0 (2026-09-10) added `# type: ignore[pyrefly:<code>]`, `type-ignore-unknown-tag-behavior`, `replace-untyped-imports-with-any`, `required-version`, and `python-interpreter-find-command` (`release_notes/release-notes-v1.3.0.md:23-27,86-101`).

[verified] `mise exec -- uv remove --dev ty` removed `ty==0.0.84`; `mise exec -- uv add --dev "pyrefly==1.3.1"` added `pyrefly==1.3.1` to the `dev` group as an exact pin, and `uv.lock` now carries `{ name = "pyrefly", specifier = "==1.3.1" }`. `mise exec -- uv lock --check` printed `Resolved 9 packages`. `mise exec -- uv run pyrefly --version` prints `pyrefly 1.3.1`.

[inference] An exact pin rather than `>=` because the helper package is small enough that a diagnostic change between minor releases costs minutes, but a silent minor bump inside `uv lock` would move the gate under a PR that touched something else. Move the pin deliberately, in a PR that records the new version, the same rule `mise.toml` states for its tools. `required-version` (`website/docs/configuration.mdx:663-685`) could restate the pin inside `[tool.pyrefly]`, but the lockfile already fixes the CLI version and the VS Code extension prefers the environment's pyrefly over its bundled binary (`website/docs/IDE.mdx:70-82`), so it is not set.

## 2. Configuration discovery and the CLI

[documented] Configuration lives in `pyrefly.toml` at the project root or a `[tool.pyrefly]` section of `pyproject.toml`; other names need `--config` and are not found automatically (`website/docs/configuration.mdx:21-27`). Without either, pyrefly migrates a nearby mypy or pyright config in memory, or falls back to the `basic` preset, which enables only high-confidence kinds (`website/docs/configuration.mdx:34-40`). Precedence is CLI flags, then the config file, then defaults (`website/docs/configuration.mdx:75-83`).

[documented] Two modes. Project mode (no files on the command line) loads one config and expands its `project-includes` and `project-excludes`. Per-file mode (`pyrefly check FILES...`) ignores both from the config and uses the config only for the remaining options (`website/docs/configuration.mdx:86-99`). The project root is the directory of the first `pyrefly.toml`, `pyproject.toml`, `setup.py`, `mypy.ini`, or `pyrightconfig.json` found walking up from the working directory (`website/docs/configuration.mdx:101-113`).

[inference] The mise task and the prek hook both run `uv run pyrefly check` with no file arguments so that project mode applies and `project-excludes` is honoured. The prek hook sets `pass_filenames = false` for the same reason, the way the `golangci-lint` hook does; passing the staged files would switch pyrefly into per-file mode and drop the excludes.

[documented] Exit codes: 0 success, 1 problems found, 3 infrastructure error, 101 panic (`website/docs/configuration.mdx:1831-1838`). `--output-format` accepts `min-text`, `full-text` (default), `json`, `github`, `junit-xml`, `code-climate`, `sarif`, and `omit-errors` (`website/docs/configuration.mdx:645-661`). `pyrefly dump-config` prints the interpreter, covered files, and search paths pyrefly resolved, which is the debugging command (`website/docs/configuration.mdx:1466-1470`).

## 3. Strict mode

[documented] `preset` is "a named collection of error severities and behavior settings that serves as the base configuration. Any explicit settings you specify override the preset." Values are `off`, `basic`, `legacy`, `default`, `strict`, `all`; the flag is `-p`/`--preset` (`website/docs/configuration.mdx:687-694`). Strict "enables additional error codes on top of the default": `strict-callable-subtyping = true` and, as errors, `direct-abstract-base-instantiation`, `implicit-any` (covering every implicit-`Any` sub-kind), `missing-override-decorator`, `open-unpacking`, `potential-bad-keyword-argument`, and `unused-ignore` (`website/docs/configuration.mdx:724-729`). `all` promotes every kind to error, and the docs recommend `strict` plus individually enabled kinds instead, "for more stability and an opt-in experience for new errors" (`website/docs/configuration.mdx:731-741`).

[documented] The source at the 1.3.1 tag matches the doc list and adds one undocumented setting: `Preset::Strict` builds the six-kind error map, sets `strict_callable_subtyping: Some(true)` and `strict_partial_subtyping: Some(true)` (`crates/pyrefly_config/src/base.rs@1.3.1:183-198`). `strict_partial_subtyping` checks "the parameters of a `functools.partial(...)` residual when it is assigned to a callable" precisely instead of treating them as gradual (`crates/pyrefly_config/src/base.rs@1.3.1:314-317`). `preset` exists at the 1.3.1 tag (`git grep -n preset 1.3.1 -- website/docs/configuration.mdx` hits line 668), so the pinned release supports it.

[documented] Every error kind has a default severity of error except those listed in `ErrorKind::default_severity` (`crates/pyrefly_config/src/error_kind.rs@1.3.1:550-621`). Warn by default: `coverage-missing`, `coverage-partial`, `deprecated`, `direct-abstract-base-instantiation`, `division-by-zero`, `implicit-import`, `invalid-decorator`, `misplaced-ignore`, `missing-attribute-patch-target`, `name-mismatch`, `non-exhaustive-match`, `non-convergent-recursion`, `redundant-cast`, `redundant-condition`, `unnecessary-comparison`, `unnecessary-type-conversion`, `unreachable`, `unreachable-match-case`, `unresolvable-dunder-all`, `untyped-import`, `variance-mismatch`, `useless-overload-body`. Ignored by default and not in strict: `empty-body`, `explicit-any`, `implicit-abstract-class`, `implicit-bool`, `implicit-reexport`, `implicitly-defined-attribute`, `incompatible-comparison`, `invalid-abstract-method`, `invalid-cast`, `missing-super-call`, `missing-source`, `no-any-return` and its two sub-kinds, `non-exhaustive-match-open-type`, `not-required-key-access`, the `pytorch-efficiency-lint` family, `string-as-iterable`, `unannotated-attribute`, `unannotated-return`, `unknown-argument-type`, `unknown-attribute-type`, `unknown-variable-type`, `unsupported-dynamic-base`, `untyped-class-decorator`, `untyped-function-decorator`, `unused-call-result`, `unused-type-ignore`. `reveal-type` is info and is a directive.

[documented] `min-severity` is "the minimum severity level for diagnostics to be displayed by `pyrefly check`"; diagnostics at or above it "are displayed and cause a nonzero exit code — for example, `--min-severity warn` makes warnings cause a nonzero exit". The default is `error`; it is project-level and cannot be set in a sub-config (`website/docs/configuration.mdx:614-643`).

[documented] The kinds the proposal adds beyond the preset. `unannotated-return`: "a function is missing a return type annotation. This helps enforce fully-typed codebases" (`website/docs/error-kinds.mdx:1944-1956`). `no-any-return`: umbrella for `no-any-return-explicit` and `no-any-return-implicit`, "a returned expression is `Any` in a function declared to return a concrete type other than `object`" (`website/docs/error-kinds.mdx:1429-1438`). `implicit-reexport`: importing a name a module only imported itself, which the typing spec says is not part of its public interface; a name is re-exported when aliased to itself, listed in `__all__`, or brought in by a wildcard (`website/docs/error-kinds.mdx:776-800`). `unused-type-ignore`: a `# type: ignore` that suppresses nothing; separate from `unused-ignore` so multi-checker projects can keep comments for mypy, and "enable this rule if your project uses pyrefly exclusively" (`website/docs/error-kinds.mdx:2371-2375`).

[documented] Kinds considered and left off. `explicit-any` flags every written `typing.Any` (`website/docs/error-kinds.mdx:589-602`); the harness clients will parse JSON and subprocess output where `Any` at the boundary is honest, so ruff's `ANN401` stays the guard. `unused-call-result` reports any discarded informative return value (`website/docs/error-kinds.mdx:2333-2348`), which would flag ordinary `subprocess.run(..., check=True)` calls. `treat-all-caps-as-final` (`website/docs/configuration.mdx:969-990`) is opt-in and harmless but adds nothing ruff `N` and `PLW0603` do not; not set.

[documented] `implicit-any-parameter` excludes `self` and `cls` (`website/docs/error-kinds.mdx:702-712`). `implicit-any-empty-container` fires only when an empty literal "couldn't be inferred from context"; with `infer-with-first-use = true` (the default) `x = []` followed by `x.append(1)` infers `list[int]` (`website/docs/error-kinds.mdx:670-683`, `website/docs/configuration.mdx:862-885`). `missing-override-decorator` follows the typing spec's strict override enforcement and skips dunders inherited from `object` (`website/docs/error-kinds.mdx:1333-1352`). `check-unannotated-defs` defaults to `true` and `infer-return-types` to `"checked"`, so unannotated bodies are still checked; the `basic` and `legacy` presets turn those off (`website/docs/configuration.mdx:702-716,887-947`).

[verified] The strict configuration in section 8, with a throwaway `src/agent_orchestration_poc/_probe.py` exercising the kinds, produced these diagnostics under `mise exec -- uv run pyrefly check --summarize-errors --output-format=min-text` (paths shortened):

```text
ERROR _probe.py:18:5-25: `no_return_annotation` is missing a return annotation [unannotated-return]
ERROR _probe.py:22:19-20: `untyped_param` is missing an annotation for parameter `x` [implicit-any-parameter]
ERROR _probe.py:23:12-13: Returning implicit Any from function declared to return "int" [no-any-return-implicit]
ERROR _probe.py:27:12-13: Returning Any from function declared to return "int" [no-any-return-explicit]
 WARN _probe.py:40:5-8: `old` is deprecated [deprecated]
ERROR _probe.py:41:9-11: Cannot instantiate `Base` because the following members are abstract: `run` [bad-instantiation]
ERROR _probe.py:49:12-13: Unused `# pyrefly: ignore` comment for code(s): bad-assignment [unused-ignore]
 INFO 7 diagnostics
```

[verified] A second probe containing only a concrete `Base.run` overridden without `@override` and one call to a `@warnings.deprecated` function printed `ERROR ... [missing-override-decorator]`, `WARN ... [deprecated]`, `INFO 2 diagnostics`, and `pyrefly check` exited 1. The warning alone would also have failed the check under `min-severity = "warn"`, which is the intended gate. Both probe files were deleted before anything was committed.

[observed] In the first probe, `Child.run` implementing an abstract `Base.run` did not raise `missing-override-decorator`, while the concrete-base case in the second probe did. `xs = []; xs.append(1)` did not raise `implicit-any-empty-container` because first-use inference pinned it to `list[int]`. `cast(int, 1)` did not raise `redundant-cast`, presumably because the literal's type is `Literal[1]`, not `int` [untested].

## 4. Includes, excludes, and the repository layout

[documented] `project-includes` defaults to `["**/*.py*"]`; an include pattern that matches no files is an error (`website/docs/configuration.mdx:145-173`). `project-excludes` defaults to `["**/node_modules", "**/__pycache__", "**/venv/**", "**/.[!/.]*/**"]` plus the `site-package-path`, and the defaults are appended to whatever is configured unless `disable-project-excludes-heuristics` is set; dotfiles and non-`.py`/`.pyi` files are filtered at the glob layer (`website/docs/configuration.mdx:175-228`). `use-ignore-files` defaults to `true` and adds the nearest `.gitignore`, `.ignore`, and `.git/info/exclude` to the excludes (`website/docs/configuration.mdx:1005-1026`). Globs are relative to the config file; a bare directory such as `src` matches every `.py` and `.pyi` beneath it (`website/docs/configuration.mdx:1475-1506`).

[verified] `mise exec -- uv run pyrefly dump-config` before the `[tool.pyrefly]` block existed listed 25 covered files, all under `research/imported/`, plus the three repository files; after the block it lists exactly `src/agent_orchestration_poc/__init__.py`, `tests/conftest.py`, and `tests/test_package.py`. `git ls-files '*.py' '*.pyi' | grep -v '^research/imported/'` returns those same three, so `experiments/` and `scripts/` hold no Python yet.

[inference] The block keeps the default include (everything) and excludes `research/imported` and `design-sketch`, mirroring ruff's `extend-exclude`, rather than listing `src`, `tests`, and `experiments` as includes. An explicit `experiments` include would fail today because the pattern matches no file, and the default include means an experiment script or a Python helper under `scripts/` is checked the day it appears without anyone remembering to add a path. The gitignored `.venv`, `.worktrees`, and `node_modules` never reach the glob because `use-ignore-files` and the dotfile filter drop them; the `.worktrees` case matters because a worktree checkout nests inside the main checkout, and `dump-config` in the main checkout would otherwise cover every sibling branch [untested in the main checkout, observed through the worktree's own listing].

[documented] Sub-configs override `errors`, `replace-imports-with-any`, `replace-untyped-imports-with-any`, `check-unannotated-defs`, `infer-return-types`, and `ignore-errors-in-generated-code` for files matching a glob; `errors` merges over the root map, and options that change the file set, the environment, or import paths cannot appear (`website/docs/configuration.mdx:1534-1581`). The `[[tool.pyrefly.sub-config]]` form with a nested `[tool.pyrefly.sub-config.errors]` table is the documented `pyproject.toml` shape (`website/docs/configuration.mdx:1780-1829`).

[verified] A throwaway `tests/_probe_test.py` with `def helper(x): return x` and `def test_thing(tmp_path):` produced no diagnostics under the `tests/**` sub-config, while the same shapes in `src/` produced `implicit-any-parameter` and `unannotated-return`. The sub-config relaxes exactly those two kinds; every other strict kind still applies to tests.

[inference] The relaxation mirrors `[tool.ruff.lint.per-file-ignores]`, where `tests/**` and `experiments/**` drop `ANN`. If Codex or the operator later wants annotated tests, delete the two sub-config tables and the ruff `ANN` exemptions in the same PR so the two tools keep agreeing.

## 5. The `src/` layout, search paths, and the interpreter

[documented] `search-path` lists the roots imports resolve from, ahead of typeshed and `site-package-path`; its default is the import root (`website/docs/configuration.mdx:247-273`). The search-path heuristic adds "a `src/` directory in the same directory as a config file" as the import root, or the config directory itself (`website/docs/configuration.mdx:296-314`). `site-package-path` is filled from the queried interpreter's `sys.path`, minus the stdlib and zip entries (`website/docs/configuration.mdx:336-359,1426-1464`).

[documented] Interpreter discovery: flags first, then an active venv or conda, then the config's `python-interpreter-path`, `python-interpreter-find-command`, `fallback-python-interpreter-name`, or `conda-environment` (mutually exclusive), then a `pyvenv.cfg` under `.venv`, `venv`, or `env` walking up from the project root, then `which python3` and `which python` (`website/docs/configuration.mdx:1433-1456`). `python-version` and `python-platform` come from that interpreter when unset; the fallback without an interpreter is `3.13.0` and `linux` (`website/docs/configuration.mdx:361-391`).

[verified] `dump-config` reports `Using interpreter: <worktree>/.venv/bin/python`, `Search path (from config file): ["<worktree>/src"]`, `Import root (inferred from project layout): "<worktree>/src"`, and `Site package path queried from interpreter: ["<worktree>/.venv/lib/python3.14/site-packages", "<worktree>/src"]`. `mise exec -- uv run python --version` prints `Python 3.14.6` and `sys.version_info[:3]` is `(3, 14, 6)` with `Py_GIL_DISABLED` `0`, so the mise-pinned interpreter that `UV_PYTHON_PREFERENCE=only-system` selects is the one pyrefly queries.

[documented] Editable installs must use path-based `.pth` files rather than import hooks for static tools to find the sources, and "the `uv_build` backend always uses path-based `.pth` files" (`website/docs/import-resolution.mdx:168-192`). That is why `src` also appears in the queried site-package path above.

[inference] `search-path = ["src"]` is set even though the heuristic finds it, so the resolution does not depend on `disable-search-path-heuristics` staying false and so `dump-config` shows the root as coming from the config. `python-interpreter-path` is not set: `uv run` activates `.venv` so step 2 of the discovery finds it, and a hard-coded path would break in CI, where the venv lives at the same relative place anyway. `python-version = "3.14"` is set because pyrefly has no `requires-python` reading (`git grep -n requires-python 1.3.1 -- crates pyrefly` finds only unrelated script headers) and a missing venv would otherwise silently drop to 3.13.0.

## 6. Python 3.14 support

[documented] The PEP table lists PEP 649 deferred annotation evaluation as the 3.14 entry and PEP 698 `@override` at 3.13 (`website/docs/python-features-and-peps.mdx:35-36`). Template strings (PEP 750) landed in v0.52.0 (`release_notes/release_notes_archived.md:1179,1203`). The bundled typeshed's `stdlib/VERSIONS` carries the 3.14 modules, for example `annotationlib: 3.14-` and `_zstd: 3.14-` (`crates/pyrefly_bundled/third_party/typeshed/stdlib/VERSIONS:79,82`).

[verified] The first probe file contained `except ValueError, TypeError:` (PEP 758, the form ruff's py314 formatter emits) and `t = t"hello {name}"`, and pyrefly reported no `parse-error` or `invalid-syntax` for either; the seven diagnostics above are the whole output. `from warnings import deprecated` resolved and drove the `deprecated` warning, so the 3.13-and-later stdlib stubs are in use.

[untested] Nothing here exercised `annotationlib.get_annotations` or forward references under PEP 649 beyond parsing; the helper package has no such code yet.

## 7. Differences from ty that matter

[documented, inference] ty 0.0.84 is beta with `0.0.x` versioning and no stable diagnostic API (`research/gates/python/notes.md` section 5). pyrefly is at 1.3.1 with a two-month minor cadence and dev snapshots kept off the stable line (`website/docs/installation.mdx:13`, `release_notes/release-notes-v1.4.0-dev.1.md:3-5`). That removes the reason section 5 gave for keeping the check outside `check`.

[documented, verified] ty infers `python-version` from `requires-python`; pyrefly does not, so the version is set in the config (section 5). ty's first-party roots default to the project root plus `./src`; pyrefly's heuristic adds `src/` as the import root, so both understand the layout without configuration, and pyrefly's `search-path` pins it.

[documented] Suppression syntax differs. pyrefly honours `# pyrefly: ignore[kind]`, `# pyrefly: ignore`, and `# type: ignore` (with `[pyrefly:kind]` for a targeted suppression since 1.3.0); `# ty: ignore[rule]` is respected only under `permissive-ignores` or `enabled-ignores`, both off by default (`website/docs/error-suppressions.mdx:16-48`, `website/docs/configuration.mdx:1270-1287`). A file-level `# pyrefly: ignore-errors` or `# pyrefly: ignore-errors[kind]` is honoured only before the first line of code; later it is inert and raises `misplaced-ignore` (`website/docs/error-suppressions.mdx:71-75`). Strict makes unused `# pyrefly: ignore` comments errors, and the proposal adds `unused-type-ignore` because ruff `PGH003` already forbids a blanket `# type: ignore`; the rule for workers is `# pyrefly: ignore[kind]` with a reason, never `# ty: ignore`.

[documented] Strictness is opt-in by preset rather than a default. An unconfigured pyrefly falls back to the `basic` preset (`website/docs/configuration.mdx:34-40`), so a stray `pyrefly check` from a directory without the config would report far less; the mise task and the prek hook always run from the repository root where `pyproject.toml` governs.

[documented] Per-file mode ignores `project-excludes` (section 2), which ty did not distinguish. Any future task that passes file names must also pass `--project-excludes`, or rely on project mode as the task and hook do.

## 8. Proposed `[tool.pyrefly]` block

[verified] This is the block now in `pyproject.toml`, formatted by `tombi format`; `mise exec -- tombi lint` reports `6 files linted successfully`.

```toml
# Strict type checking for every Python file the repository tracks (research/gates/pyrefly/notes.md).
[tool.pyrefly]
# Everything except the verbatim research imports, the sketches, and gitignored trees (use-ignore-files
# defaults to true), so experiments/ and scripts/ join the check the day they gain a .py file.
project-excludes = ["research/imported", "design-sketch"]
search-path = ["src"]
# pyrefly does not read requires-python; without this it takes the version from the queried interpreter.
python-version = "3.14"
# The strict preset plus the off-by-default kinds that make the helper package fully typed.
preset = "strict"
# Warn-by-default kinds (deprecated, redundant-cast, unreachable, untyped-import, ...) fail the check too.
min-severity = "warn"

[tool.pyrefly.errors]
unannotated-return = true
no-any-return = true
implicit-reexport = true
unused-type-ignore = true

# tests/ and experiments/ are exempt from annotation completeness, mirroring the ruff ANN per-file-ignores.
[[tool.pyrefly.sub-config]]
matches = "tests/**"

[tool.pyrefly.sub-config.errors]
implicit-any-parameter = false
unannotated-return = false

[[tool.pyrefly.sub-config]]
matches = "experiments/**"

[tool.pyrefly.sub-config.errors]
implicit-any-parameter = false
unannotated-return = false
```

What each setting does, in one line each:

- `project-excludes`: filters the default `**/*.py*` include; the two entries mirror ruff's `extend-exclude` and the pyrefly defaults plus `.gitignore` are appended automatically.
- `search-path`: the import root for `agent_orchestration_poc`, pinned to `src` so resolution does not rest on the heuristic.
- `python-version`: the `sys.version_info` pyrefly assumes when evaluating version checks and stdlib availability; matches `requires-python = ">=3.14"`.
- `preset = "strict"`: six kinds to error plus strict callable and `functools.partial` subtyping, the documented strict mode.
- `min-severity = "warn"`: warn-by-default kinds such as `deprecated`, `redundant-cast`, `unreachable`, `untyped-import`, and `non-exhaustive-match` fail the check instead of scrolling past.
- `errors`: four kinds that are off even in strict and complete the fully-typed rule ruff `ANN` states for `src/`.
- `sub-config`: the two annotation-completeness kinds off under `tests/**` and `experiments/**`, matching the ruff per-file-ignores; nothing else is relaxed.

## 9. Run output

[verified] `mise exec -- uv run pyrefly check` on the helper package and tests:

```text
 INFO Checking project configured at `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-61-pyrefly/pyproject.toml`
 INFO 0 diagnostics
```

[verified] `mise run check` with `check:pyrefly` in the aggregate finished green; the pyrefly lines were:

```text
[check:pyrefly] $ uv run pyrefly check
[check:pyrefly]  INFO Checking project configured at `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/tooling-61-pyrefly/pyproject.toml`
[check:pyrefly]  INFO 0 diagnostics
[check:pyrefly] Finished in 331.4ms
```

## Draft rules for .claude/rules/python.md

Each line names the version it was written for. Codex finalises the wording and replaces the two `ty 0.0.84` lines.

- pyrefly 1.3.1: run `uv run pyrefly check` through the `check:pyrefly` mise task; it gates `mise run check`, CI, and the prek pre-commit hook. Never pass file names to the task, because per-file mode drops `project-excludes`.
- pyrefly 1.3.1: the configuration is `[tool.pyrefly]` in `pyproject.toml` with `preset = "strict"` and `min-severity = "warn"`; do not add a `pyrefly.toml`, and do not lower a severity to make a check pass.
- pyrefly 1.3.1: annotate every parameter and return in `src/`; `implicit-any`, `unannotated-return`, and `no-any-return` are errors there. Tests and experiment scripts may omit annotations, matching ruff's `ANN` exemption.
- pyrefly 1.3.1: decorate every overriding method with `typing.override`; re-export from `__init__.py` through `__all__` or `import x as x`, because `implicit-reexport` is an error.
- pyrefly 1.3.1: suppress with `# pyrefly: ignore[kind]` and a reason on the same line; never a bare `# pyrefly: ignore`, `# type: ignore`, or `# ty: ignore`. Unused suppressions of either form are errors.
- pyrefly 1.3.1: the pin is exact in the `dev` group; move it with `uv add --dev pyrefly==<version>` in a PR that records the new version and the run output.
