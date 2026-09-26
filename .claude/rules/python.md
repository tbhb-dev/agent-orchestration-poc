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

## Typing

- ty 0.0.84: run the separate `check:ty` mise task. Keep it outside `check` until the phase 1 checkpoint decides whether it gates.
- ty 0.0.84: configure under `[tool.ty]` if needed and suppress only a named rule with `# ty: ignore[rule]` and a reason. Use mypy if ty is rejected at the checkpoint.
