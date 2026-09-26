---
paths: ["**/*.py", "pyproject.toml", "uv.lock"]
---

See [Python conventions](../../docs/src/content/docs/guides/python-conventions.md).

## Interpreter and uv

- Python 3.14.6: Use the mise-pinned default GIL build with `UV_PYTHON_PREFERENCE=only-system`; do not select `3.14t` or set `PYTHON_JIT`.
- uv 0.12.10: Run Python tools as `uv run <tool>` through mise tasks from the repository root; install no global tools.
- uv 0.12.10: Add dependencies with `uv add` (`--dev` for tools), commit `uv.lock` with `pyproject.toml`, run `uv lock --check`, and install in CI with `uv sync --locked`.
- uv 0.12.10: Keep tools in the `dev` group and shared code in `src/agent_orchestration_poc/`; use no extras or Python workspace.
- uv 0.12.10: Run plain `experiments/<NN-slug>/*.py` files with `PYTHONSAFEPATH=1`; use no `# /// script` metadata or sibling imports.

## Code rules

- Python 3.14: Omit `from __future__ import annotations` and quoted forward references; inspect annotations with `annotationlib.get_annotations`.
- Python 3.14: Enter asyncio with `asyncio.run` or `asyncio.Runner`; use `TaskGroup`, `asyncio.timeout`, and `loop_factory=`, and retain every created task.
- Python 3.14: Avoid `asyncio.get_event_loop`, loop policies, and `asyncio.iscoroutinefunction`; use `inspect.iscoroutinefunction`.
- Python 3.14: Spawn with `asyncio.create_subprocess_exec` or `subprocess.run` using argv and explicit `check=`; avoid `shell=True`, `os.system`, `os.popen`, `os.spawn*`, and `pipes`.
- Python 3.14: Never leave `finally` with `return`, `break`, or `continue`.
- Python 3.14: Use `datetime.now(tz=UTC)`, `uuid.uuid7()`, `pathlib.Path`, and `copy.replace`; avoid `datetime.utcnow()`.
- Python 3.14: Write `int | str` unions and compare union types with `==`; avoid removed and pending-removal `typing` names.
- Python 3.14: Avoid deprecated `logging.warn`, `codecs.open`, `shutil.rmtree(onerror=)`, and camelCase `threading` aliases.
- Python 3.14: Do not assume `fork` inheritance on Linux, which defaults to `forkserver`; set `NO_COLOR=1` and `PYTHONUNBUFFERED=1` for captured child Python evidence.

## Ruff

- ruff 0.16.9: Run `uv run ruff check` and `uv run ruff format --check`; apply safe lint fixes before formatting.
- ruff 0.16.9: Infer the target from `requires-python`; do not set `target-version`, except `--target-version py314` for an explicit standalone config.
- ruff 0.16.9: Use Google-style public docstrings, `logging` instead of `print` in `src/`, explicit `__all__` for re-exports, and formatter-produced `except A, B:` syntax.
- ruff 0.16.9: Avoid blocking calls in `async def`; suppress a specific finding with `# noqa: CODE` or `# ruff: ignore[CODE]` and a reason.
- ruff 0.16.9: Do not enable preview, `COM`, `Q`, `E501`, `D203`, `D213`, or removed rule codes listed on the conventions page.

## Pytest

- pytest 9.1.1: Put tests under `tests/` without `__init__.py`; use `importlib` mode, `conftest.py` fixtures, and no `pythonpath` or test-module imports.
- pytest 9.1.1: Register every marker and use individual `strict_markers`, `strict_config`, and `strict_xfail` confvals; do not set broad `strict` or strict flags in `addopts`.
- pytest 9.1.1: Mark process and socket tests `integration` or `socket`; skip them by default and run them with `--run-integration`.
- pytest 9.1.1: Treat warnings as errors and document any exception in `filterwarnings`.
- pytest 9.1.1: Use `@pytest.fixture` without parentheses and yield fixtures that terminate, wait, then kill children; place Unix socket paths under a short temporary directory, not `tmp_path`.
- pytest 9.1.1: Add the verified async plugin before writing `async def` tests.

## Typing

- ty 0.0.84: Run the separate `check:ty` mise task; keep it outside `check` until the phase 1 checkpoint decides whether it gates.
- ty 0.0.84: Configure under `[tool.ty]` if needed and suppress only a named rule with `# ty: ignore[rule]` and a reason; use mypy if ty is rejected at the checkpoint.
