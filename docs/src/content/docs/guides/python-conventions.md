---
title: Python conventions
description: Python 3.14.6 layout, execution, linting, testing, and typing conventions with uv 0.12.10, ruff 0.16.9, and pytest 9.1.1.
---

## Versions and sources

This page records the Python research gate from 2026-09-26. The interpreter choice and tool configurations below are coordinator decisions for the skeleton item, while the current scaffold has not yet received them (research/gates/python/versions.md, research/gates/python/notes.md §§1, 3 through 5).

| Tool | Target version | Source read |
| --- | --- | --- |
| Python | mise-pinned CPython 3.14.6, default GIL build | `~/Code/github.com/python/cpython` at `c63aec69` (`v3.14.6`). `Doc/whatsnew/3.13.rst`, `Doc/whatsnew/3.14.rst`, and related docs (research/gates/python/versions.md) |
| uv | installed 0.12.10 | `~/Code/github.com/astral-sh/uv` at `136ef973` (`0.12.19`). The source checkout is nine patch releases newer than installed (research/gates/python/versions.md) |
| ruff | 0.16.9 | `~/Code/github.com/astral-sh/ruff` at `94e46ca1` (`0.16.9`) (research/gates/python/versions.md) |
| pytest | 9.1.1 | `~/Code/github.com/pytest-dev/pytest` at `87211735` (9.2.0 development snapshot, latest release tag 9.1.1) (research/gates/python/versions.md) |
| ty | 0.0.84 | `~/Code/github.com/astral-sh/ty` at `8e4aef29` (`0.0.84`) (research/gates/python/versions.md) |
| mise | installed 2026.8.6 | `~/Code/github.com/jdx/mise` at `fdfa0efe` (research/gates/python/versions.md) |

## Layout and uv

Keep one `uv_build` project with its editable helper package under `src/agent_orchestration_poc/`. Remove the scaffold's `main` function and `[project.scripts]` entry, and put shared experiment code in that package rather than making a workspace (uv/docs/concepts/projects/{init,config,sync,workspaces}.md, uv/docs/concepts/build-backend.md, research/gates/python/notes.md §1, PLAN.md, Repository layout).

Run plain files under `experiments/<NN-slug>/` from the repository root with `uv run experiments/<NN-slug>/<script>.py` and `PYTHONSAFEPATH=1`. Inline `# /// script` metadata isolates a script from the project, while safe path prevents sibling imports and module shadowing (uv/docs/concepts/projects/run.md, uv/docs/guides/scripts.md, cpython/Doc/using/cmdline.rst, research/gates/python/notes.md §1).

Put development tools, including ruff 0.16.9, pytest 9.1.1, the async test plugin once verified, and ty 0.0.84, in the `dev` dependency group. Use `project.dependencies` for helper runtime imports and no published extras (uv/docs/concepts/projects/dependencies.md, research/gates/python/notes.md §§1, 4 through 5).

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
"tests/**" = ["S101", "PLR2004", "ANN", "D", "ARG", "INP001"]
"experiments/**" = ["T20", "INP001", "D", "ANN"]

[tool.ruff.lint.isort]
known-first-party = ["agent_orchestration_poc"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
docstring-code-format = true
line-ending = "lf"
```

The added families enforce imports, Google-style public docstrings, annotations, subprocess security checks, quiet library output, naming, pytest style, unused arguments, pathlib, precise suppressions, package boundaries, logging, and straightforward control flow. The individual rules catch lost tasks, busy waits, hidden imports, large signatures, and exception handling errors (ruff/docs/linter.md, ruff/crates/ruff_workspace/src/options.rs, research/gates/python/notes.md §3).

Tests may use assertions, literals, untyped fixtures, and no package initializer. Experiment scripts may print and omit docstrings or type annotations, while `src/` keeps the full checks (ruff/crates/ruff_workspace/src/options.rs, research/gates/python/notes.md §3).

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

Add ty 0.0.84 to the `dev` group with a `check:ty` mise task running `uv run ty check`. Keep it outside the `check` aggregate, and decide whether it gates at the phase 1 checkpoint, with mypy as the fallback (ty/docs/installation.md, ty/README.md, research/gates/python/notes.md §5).

ty 0.0.84 is beta with no stable diagnostic API, but it reads `requires-python` and the `src/` layout without extra configuration and passed the scaffold check. Configure it under `[tool.ty]` only if needed, and use specific `# ty: ignore[rule]` suppressions with reasons (ty/README.md, ty/docs/{configuration,modules,python-version,suppression}.md, research/gates/python/notes.md §5).
