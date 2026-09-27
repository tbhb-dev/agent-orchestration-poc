---
title: Python conventions
description: Python 3.14.6 conventions with uv 0.12.10, ruff 0.16.9, pytest 9.1.1, and pyrefly 1.3.1.
---

## Versions and sources

This page records the Python research gate from 2026-09-26 and the strict pyrefly decision for issue #61. The current scaffold uses the interpreter and tool configurations below (research/gates/python/versions.md, research/gates/pyrefly/versions.md).

| Tool | Target version | Source read |
| --- | --- | --- |
| Python | mise-pinned CPython 3.14.6, default GIL build | `~/Code/github.com/python/cpython` at `c63aec69` (`v3.14.6`). `Doc/whatsnew/3.13.rst`, `Doc/whatsnew/3.14.rst`, and related docs (research/gates/python/versions.md) |
| uv | installed 0.12.10 | `~/Code/github.com/astral-sh/uv` at `136ef973` (`0.12.19`). The source checkout is nine patch releases newer than installed (research/gates/python/versions.md) |
| ruff | 0.16.9 | `~/Code/github.com/astral-sh/ruff` at `94e46ca1` (`0.16.9`) (research/gates/python/versions.md) |
| pytest | 9.1.1 | `~/Code/github.com/pytest-dev/pytest` at `87211735` (9.2.0 development snapshot, latest release tag 9.1.1) (research/gates/python/versions.md) |
| pyrefly | 1.3.1 | `~/Code/github.com/facebook/pyrefly` at `a778c3bc8cf41398408498de3d10e99a76b9fdd2`, with the 1.3.1 tag at `3e3177d0f4755b56c2d5a710d830eed89b14c2e3` (research/gates/pyrefly/versions.md) |
| mise | installed 2026.8.6 | `~/Code/github.com/jdx/mise` at `fdfa0efe` (research/gates/python/versions.md) |

## Layout and uv

Keep one `uv_build` project with its editable helper package under `src/agent_orchestration_poc/`. Remove the scaffold's `main` function and `[project.scripts]` entry, and put shared experiment code in that package rather than making a workspace (uv/docs/concepts/projects/{init,config,sync,workspaces}.md, uv/docs/concepts/build-backend.md, research/gates/python/notes.md §1, PLAN.md, Repository layout).

Run plain files under `experiments/<NN-slug>/` from the repository root with `uv run experiments/<NN-slug>/<script>.py` and `PYTHONSAFEPATH=1`. Inline `# /// script` metadata isolates a script from the project, while safe path prevents sibling imports and module shadowing (uv/docs/concepts/projects/run.md, uv/docs/guides/scripts.md, cpython/Doc/using/cmdline.rst, research/gates/python/notes.md §1).

Put development tools, including ruff 0.16.9, pytest 9.1.1, and pyrefly 1.3.1, in the `dev` dependency group. Add the async test plugin once verified. Use `project.dependencies` for helper runtime imports and no published extras (uv/docs/concepts/projects/dependencies.md, research/gates/python/notes.md §§1, 4, research/gates/pyrefly/notes.md §1).

Add dependencies with `uv add` and commit `pyproject.toml` and `uv.lock` together. Run `uv lock --check` before committing and `uv sync --locked` in CI, then invoke locked tools as `uv run <tool>` through mise tasks (uv/docs/concepts/projects/sync.md, research/gates/python/notes.md §1).

The interpreter is mise-pinned Python 3.14.6 with `UV_PYTHON_PREFERENCE=only-system`, which selects mise's interpreter instead of uv's managed Python. The tooling item already sets those values, while the notes' `UV_PYTHON` path export remains an alternative it may adopt later (uv/docs/concepts/python-versions.md, uv/crates/uv-settings/src/settings.rs, research/gates/python/notes.md §1).

Use the default GIL build, not `3.14t`. Python 3.14 supports free threading but its context and warning behavior differs, and the experiments are asyncio and I/O bound (cpython/Doc/whatsnew/3.14.rst, cpython/Doc/howto/free-threading-python.rst, research/gates/python/notes.md §2).

## Python 3.14 and 3.13 changes that matter

Python 3.14 defers annotation evaluation: omit `from __future__ import annotations` and quoted forward references, and inspect annotations with `annotationlib.get_annotations` instead of reading a class namespace directly (cpython/Doc/whatsnew/3.14.rst, research/gates/python/notes.md §2).

Python 3.14 makes `asyncio.get_event_loop()` raise without a current loop and deprecates loop policies for removal in 3.16. Enter through `asyncio.run` or `asyncio.Runner`, pass `loop_factory=` when needed, and use `inspect.iscoroutinefunction` (cpython/Doc/whatsnew/3.14.rst, cpython/Doc/deprecations/pending-removal-in-3.16.rst, research/gates/python/notes.md §2).

Python 3.14 emits `SyntaxWarning` for `return`, `break`, or `continue` leaving `finally`. Pytest's warning filter makes that a failure (cpython/Doc/whatsnew/3.14.rst, pytest/doc/en/reference/reference.rst, research/gates/python/notes.md §§2, 4).

Python 3.13 expands `subprocess` use of `posix_spawn`, and Python 3.14 soft-deprecates `os.popen` and `os.spawn*`. Use subprocess argv lists and clean up spawned children explicitly (cpython/Doc/whatsnew/3.13.rst, cpython/Doc/whatsnew/3.14.rst, research/gates/python/notes.md §2).

Python 3.14 changes the Unix `multiprocessing` and `ProcessPoolExecutor` default to `forkserver` except on macOS, where it remains `spawn`. Process evidence must not assume `fork` inheritance (cpython/Doc/whatsnew/3.14.rst, research/gates/python/notes.md §2).

Python 3.14 adds `Path.copy`, `Path.move`, and `Path.info`. Since Python 3.13, `Path.glob("**")` includes files as well as directories, so evidence scans must filter the entries they need (cpython/Doc/whatsnew/3.13.rst, cpython/Doc/whatsnew/3.14.rst, research/gates/python/notes.md §2).

Python 3.14's `python -m json` accepts `--json-lines` for evidence files and replaces the soft-deprecated `python -m json.tool`. JSON-lines parsing in code remains one `json.loads` per line (cpython/Doc/whatsnew/3.14.rst, Python 3.14.3 `python -m json --help`, research/gates/python/notes.md §2).

Python 3.13 and 3.14 color command output by default. Set `NO_COLOR=1` and `PYTHONUNBUFFERED=1` in captured child Python environments so evidence has no ANSI escapes and retains partial output after a kill (cpython/Doc/whatsnew/3.13.rst, cpython/Doc/whatsnew/3.14.rst, cpython/Doc/using/cmdline.rst, research/gates/python/notes.md §2).

## Ruff

Adopt this ruff 0.16.9 configuration with the skeleton item. `requires-python` supplies the target version, and `extend-select` adds to the 413 default rules without replacing them (ruff/docs/configuration.md, ruff/CHANGELOG.md, research/gates/python/notes.md §3).

```toml
[tool.ruff]
line-length = 88
extend-exclude = [".worktrees", "research/imported", "design-sketch", "*.md"]

[tool.ruff.lint]
extend-select = [
    "I",        # isort
    "D",        # pydocstyle, scoped by the google convention below
    "ANN",      # flake8-annotations: the helper package is fully typed
    "S",        # flake8-bandit: the security category is off by default
    "T20",      # flake8-print: no print in the library, scripts exempted below
    "N",        # pep8-naming
    "PT",       # flake8-pytest-style
    "ARG",      # flake8-unused-arguments
    "ERA",      # eradicate: commented-out code
    "PTH",      # flake8-use-pathlib
    "PGH",      # pygrep-hooks: blanket noqa and type: ignore
    "INP",      # flake8-no-pep420: implicit namespace packages
    "A",        # flake8-builtins
    "LOG",      # flake8-logging
    "G",        # flake8-logging-format
    "RET",      # flake8-return
    "TC006",    # runtime-cast-value
    "RUF006",   # asyncio dangling task
    "ASYNC110", # async busy wait
    "PLC0415",  # import outside top level
    "PLR0913",  # too many arguments
    "B904",     # raise ... from inside except
    "TRY400",   # logging.exception inside handlers
]
ignore = [
    "S603", # subprocess without shell: spawning processes is the point
    "S607", # partial executable path: harness binaries resolve through PATH via mise
    "D105", # docstrings on magic methods
    "D107", # docstrings on __init__
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "PLR2004", "D", "ARG", "INP001"]
"experiments/**" = ["T20", "INP001", "D"]

[tool.ruff.lint.isort]
known-first-party = ["agent_orchestration_poc"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
docstring-code-format = true
line-ending = "lf"
```

The added families enforce imports, Google-style public docstrings, annotations, subprocess security checks, quiet library output, naming, pytest style, unused arguments, pathlib, precise suppressions, package boundaries, logging, and straightforward control flow. The individual rules catch lost tasks, busy waits, hidden imports, large signatures, and exception handling errors (ruff/docs/linter.md, ruff/crates/ruff_workspace/src/options.rs, research/gates/python/notes.md §3).

Tests may use assertions, literals, fixtures, and no package initializer. Experiment scripts may print and omit docstrings. Source, tests, and experiments require parameter and return annotations after the operator's 2026-09-26 strict-everywhere decision (ruff/crates/ruff_workspace/src/options.rs, research/gates/python/notes.md §3, decision 0002).

Suppress one finding with `# noqa: CODE` or `# ruff: ignore[CODE]` and a reason. Keep `S603` and `S607` off for intended PATH-resolved subprocesses, and `D105` and `D107` off for magic methods and initializers (ruff/CHANGELOG.md, `ruff rule S603`, `ruff rule S607`, research/gates/python/notes.md §3).

Do not enable formatter-conflicting `COM`, `Q`, `W191`, `E111`, `E114`, `E117`, `D206`, `D300`, or `ISC002`, or best-effort `E501`. Keep `D203` and `D213`, `EM`, `TRY003`, `FBT`, `TC001` through `TC003`, size limits, and preview modes off (ruff/docs/formatter.md, ruff/docs/preview.md, research/gates/python/notes.md §3).

Exclude Markdown because ruff 0.16 formats fenced Python blocks there by default, while this repository keeps imported research and evidence verbatim and checks Markdown separately (ruff/CHANGELOG.md, ruff/docs/formatter.md, research/gates/python/notes.md §3).

## Pytest

Adopt these pytest 9.1.1 settings with the skeleton item. Use individual strict confvals because pytest 9.0.0 through 9.0.3 ignored strict flags in `addopts`, and the broader `--strict` can gain new checks later (pytest/doc/en/reference/reference.rst, pytest/doc/en/changelog.rst, research/gates/python/notes.md §4).

```toml
[tool.pytest.ini_options]
minversion = "9.1"
testpaths = ["tests"]
addopts = "-ra --import-mode=importlib"
strict_markers = true
strict_config = true
strict_xfail = true
markers = [
    "integration: needs a spawned process or a running harness; skipped unless --run-integration",
    "socket: needs a Unix socket or WebSocket endpoint; skipped unless --run-integration",
    "slow: takes more than a few seconds; deselect with -m 'not slow'",
]
filterwarnings = ["error"]
log_level = "INFO"
```

With `--import-mode=importlib`, keep `tests/` without `__init__.py`, avoid test-module imports and `pythonpath` edits, and put shared helpers in the installed package or `conftest.py` fixtures (pytest/doc/en/explanation/{goodpractices,pythonpath}.rst, research/gates/python/notes.md §4).

Register all markers. In `tests/conftest.py`, add `--run-integration` with `pytest_addoption` and have `pytest_collection_modifyitems` skip `integration` and `socket` tests unless the flag is present, while `slow` only supports optional deselection (pytest/doc/en/how-to/mark.rst, pytest/doc/en/example/simple.rst, research/gates/python/notes.md §4).

Warnings fail tests, and unexpected xfail passes fail too. Document any third-party warning exception as a commented `ignore:` filter entry (pytest/doc/en/reference/reference.rst, pytest/doc/en/how-to/capture-warnings.rst, research/gates/python/notes.md §4).

Use yield fixtures for child processes and sockets. Wait for readiness with a deadline. In teardown, call `terminate()` and wait with a timeout. Call `kill()` if necessary. Use `tmp_path` for ordinary files but a short temporary directory under `/tmp` for Unix socket paths because macOS rejected a 110-character path in the research test (pytest/doc/en/how-to/{fixtures,tmp_path}.rst, research/gates/python/notes.md §4).

pytest 9.1.1 needs an async plugin for `async def` tests. Add and verify `pytest-asyncio` in the skeleton item before setting its `asyncio_mode`, since the plugin was not researched here (pytest/src/_pytest/python.py, research/gates/python/notes.md §4, research/gates/python/versions.md).

## Typing

Pyrefly 1.3.1 is pinned exactly in the `dev` group. Its strict preset turns six additional diagnostic kinds into errors and enables strict callable and `functools.partial` subtyping. The configuration enables four more error kinds. `min-severity = "warn"` makes warnings fail the check (research/gates/pyrefly/notes.md §§1, 3).

The following configuration is copied from `pyproject.toml`:

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

```

`python-version = "3.14"` is explicit because pyrefly does not read `requires-python`. `search-path = ["src"]` fixes the import root. The two `project-excludes` omit imported research and design sketches (research/gates/pyrefly/notes.md §§2, 4 through 5).

Run `mise run check:pyrefly` from the repository root. This task runs `uv run pyrefly check` with no file names and belongs to `mise run check` and CI. The prek hook also passes no file names because per-file mode ignores `project-excludes` (research/gates/pyrefly/notes.md §§2, 9).

Use `# pyrefly: ignore[kind]` with a reason on the same line for a necessary suppression. Strict mode rejects unused pyrefly suppressions, and the added `unused-type-ignore` kind rejects unused type ignores (research/gates/pyrefly/notes.md §§3, 7).

The operator decided "Strict everywhere" on 2026-09-26. Pyrefly and ruff require parameter and return annotations in source, tests, and experiments, with no test or experiment sub-config (decision 0002).

## Property testing

Use Hypothesis 6.168.1 `@given` tests for pure core functions. These run with ordinary pytest tests in `mise run check`. Keep the built-in `ci` profile for required CI, which derandomizes examples and disables the example database. Local runs use random examples. The nightly task selects the default profile with an explicit random seed, which its failure issue records (research/gates/testing/notes.md §2, decision 0005).

## Mutation testing

Run `mise run check:mutation:python` after changing the Python core or its tests. Mutmut 3.8.0 scores only `agent_orchestration_poc.core`. The task deletes `mutants/` before every run because mutmut otherwise reuses results after test edits. The score floor is 90 percent, and the task fails if the scored outcomes do not account for every mutant, including runs with crashes, interruptions, or skipped mutants. This task runs outside `mise run check` in the always-present mutation CI job (research/gates/testing/notes.md §4, decision 0005).

Run `mise run check:coverage` on every pull request. Coverage.py 7.16.1 measures branches through `[tool.coverage.run]`. The JSON checker separately requires 95 percent core lines, 90 percent core branches, and 70 percent shell lines when shell code exists. Its pytest run includes tests marked `integration` and `socket`. The separate counts matter because pytest-cov 7.0.0 `--cov-fail-under` checks one combined total (research/gates/testing/coverage-branches-87.md, decision 0005).

## Functional core and imperative shell

Put pure functions in `src/agent_orchestration_poc/core/` and side effects in `src/agent_orchestration_poc/shell/`. Experiment scripts are shell code. A core function can return a process specification from a listing of values, then a shell function starts the process. The dependency direction runs from shell to core (research/gates/boundaries/notes.md §1).

import-linter 2.15 checks a layers contract and a forbidden import contract with external packages included. The configured module list covers `os`, `sys`, `subprocess`, `socket`, `asyncio`, process helpers, `websockets`, and `nats`. Run `mise run check:imports`. Ruff 0.16.9 also enables `TID251` in the core directory (research/gates/boundaries/notes.md §2).

```toml
[tool.importlinter]
root_package = "agent_orchestration_poc"
include_external_packages = true

[[tool.importlinter.contracts]]
type = "layers"
layers = ["shell", "core"]
containers = ["agent_orchestration_poc"]

[[tool.importlinter.contracts]]
type = "forbidden"
source_modules = ["agent_orchestration_poc.core"]
forbidden_modules = ["os", "socket", "subprocess", "asyncio", "nats"]
```

Core tests pass plain values without mocks or markers. Shell process and socket tests use the registered integration markers. Import checkers cannot see `Path.write_text` on a parameter or I/O through a passed file handle, so review calls as well as imports. Property and mutation gates test the core (research/gates/boundaries/notes.md §§2, 4, decision 0005).

## Quality gates

Ruff 0.16.9 selects `C901`, `PLR0911`, `PLR0912`, `PLR0915`, and `PLR0917` alongside the existing `PLR0913`. Their limits are 10 McCabe complexity, 6 returns, 12 branches, 50 statements, 5 arguments, and 5 positional arguments. The thresholds are configured at the tool defaults in `pyproject.toml` (research/gates/quality-gates/notes.md §Complexity).

```toml
[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-args = 5
max-branches = 12
max-positional-args = 5
max-returns = 6
max-statements = 50
```

`check:dupl` uses jscpd 5.3.2 at 50 tokens and 5 lines across source, tests, and experiments. `check:deadcode` runs vulture 2.16 at confidence 60, ignoring pytest hooks and fixtures. Run both tasks through mise and recalibrate their thresholds at the first retro with phase 2 code (research/gates/quality-gates/notes.md §§Duplicate code, Dead code, First run).
