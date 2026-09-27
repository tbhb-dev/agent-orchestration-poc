---
paths: ["**/*.py", "pyproject.toml", "uv.lock"]
---

See [Python conventions](../../docs/src/content/docs/guides/python-conventions.md).

## Interpreter and uv

- Python 3.14.6: use the mise-pinned default GIL build with `UV_PYTHON_PREFERENCE=only-system`. Do not select `3.14t` or set `PYTHON_JIT`.
- uv 0.12.10: run Python tools as `uv run <tool>` through mise tasks from the repository root. Do not install global tools.
- uv 0.12.10: add dependencies with `uv add` (`--dev` for tools) and commit `uv.lock` with `pyproject.toml`. Run `uv lock --check`, then install in CI with `uv sync --locked`.
- uv 0.12.10: keep tools in the `dev` group and shared code in `src/agent_orchestration_poc/`. Do not use extras or a Python workspace.
- uv 0.12.10: run plain `experiments/<NN-slug>/*.py` files with `PYTHONSAFEPATH=1`. Do not use `# /// script` metadata or sibling imports.

## Code rules

- Python 3.14: omit `from __future__ import annotations` and quoted forward references. Inspect annotations with `annotationlib.get_annotations`.
- Python 3.14: enter asyncio with `asyncio.run` or `asyncio.Runner`. Use `TaskGroup`, `asyncio.timeout`, and `loop_factory=`, and retain every created task.
- Python 3.14: avoid `asyncio.get_event_loop` and loop policies. Avoid `asyncio.iscoroutinefunction`. Use `inspect.iscoroutinefunction`.
- Python 3.14: spawn with `asyncio.create_subprocess_exec` or `subprocess.run` using argv and explicit `check=`. Avoid `shell=True`, `os.system`, `os.popen`, `os.spawn*`, and `pipes`.
- Python 3.14: never leave `finally` with `return`, `break`, or `continue`.
- Python 3.14: use `datetime.now(tz=UTC)`, `uuid.uuid7()`, `pathlib.Path`, and `copy.replace`. Avoid `datetime.utcnow()`.
- Python 3.14: write `int | str` unions and compare union types with `==`. Avoid removed and pending-removal `typing` names.
- Python 3.14: avoid deprecated `logging.warn`, `codecs.open`, `shutil.rmtree(onerror=)`, and camelCase `threading` aliases.
- Python 3.14: do not assume `fork` inheritance on Linux, which defaults to `forkserver`. Set `NO_COLOR=1` and `PYTHONUNBUFFERED=1` for captured child Python evidence.

## Ruff

- ruff 0.16.9: run `uv run ruff check` and `uv run ruff format --check`. Apply safe lint fixes before formatting.
- ruff 0.16.9: infer the target from `requires-python`. Do not set `target-version`, except `--target-version py314` for an explicit standalone config.
- ruff 0.16.9: use Google-style public docstrings, `logging` instead of `print` in `src/`, explicit `__all__` for re-exports, and formatter-produced `except A, B:` syntax.
- ruff 0.16.9: avoid blocking calls in `async def`. Suppress a specific finding with `# noqa: CODE` or `# ruff: ignore[CODE]` and a reason.
- ruff 0.16.9: do not enable preview, `COM`, `Q`, `E501`, `D203`, `D213`, or removed rule codes listed on the conventions page.

## Pytest

- pytest 9.1.1: put tests under `tests/` without `__init__.py`. Use `importlib` mode, `conftest.py` fixtures, and no `pythonpath` or test-module imports.
- pytest 9.1.1: register every marker and use individual `strict_markers`, `strict_config`, and `strict_xfail` confvals. Do not set broad `strict` or strict flags in `addopts`.
- pytest 9.1.1: mark process and socket tests `integration` or `socket`. Skip them by default and run them with `--run-integration`.
- pytest 9.1.1: treat warnings as errors and document any exception in `filterwarnings`.
- pytest 9.1.1: use `@pytest.fixture` without parentheses and yield fixtures for child processes. In teardown, call `terminate()` and wait with a timeout. Call `kill()` if necessary. Place Unix socket paths under a short temporary directory, not `tmp_path`.
- pytest 9.1.1: add the verified async plugin before writing `async def` tests.
- hypothesis 6.168.1: test properties of pure functions with `@given`. Keep the built-in `ci` profile for required CI and use random seeds in local and nightly runs.
- mutmut 3.8.0, pytest-cov 7.0.0: run `mise run check:mutation:python` for core changes. Delete `mutants/` before scoring, require at least 80 percent mutation score and 90 percent line coverage.

## Core and shell

- Python 3.14, import-linter 2.15: put pure decisions in `agent_orchestration_poc.core` and I/O in `agent_orchestration_poc.shell`. The core cannot import the shell or the forbidden I/O modules listed in `[tool.importlinter]`.
- Python 3.14: core functions take and return values. They may use `pathlib` for path values but cannot call file system methods or receive an open file, socket, or process. Experiment scripts are shell code.
- import-linter 2.15: run `mise run check:imports` and move a prohibited import into the shell. Never add `ignore_imports` to bypass a contract.
- ruff 0.16.9: the core's nested `ruff.toml` enables `TID251` for qualified I/O calls. It cannot resolve every `Path` method call, so review the actual behavior.
- pytest 9.1.1: test core functions with plain values and no mocks or markers. Mark shell process and socket tests `integration` or `socket`.

## Quality gates

- ruff 0.16.9: keep McCabe complexity at 10 with `C901`. `PLR0912` allows 12 branches, `PLR0911` allows 6 returns, and `PLR0915` allows 50 statements.
- ruff 0.16.9: keep signatures to 5 arguments and 5 positional arguments with `PLR0913` and `PLR0917`. Leave preview complexity rules off.
- vulture 2.16: `check:deadcode` checks `src`, `tests`, `experiments`, and `scripts` at confidence 60. Pytest hooks and fixtures are exempt. Give a reason in a whitelist for any other false positive.
- jscpd 5.3.2: move repeated blocks of at least 50 tokens and 5 lines into the helper package. Explain any deliberate repeat marked with `jscpd:ignore-start` and `jscpd:ignore-end`.

## Typing

- pyrefly 1.3.1: run `mise run check:pyrefly` from the repository root. It gates `mise run check`, CI, and prek. Pass no file names because per-file mode ignores `project-excludes`.
- pyrefly 1.3.1, ruff 0.16.9: strict typing applies to source, tests, and experiments after the operator's 2026-09-26 decision. Annotate parameters and returns everywhere, use `typing.override` for overrides, and list re-exports in `__all__` or alias imports to themselves. Suppress a named kind only with `# pyrefly: ignore[kind]` and a same-line reason. Move the exact pin in a PR with run evidence.
