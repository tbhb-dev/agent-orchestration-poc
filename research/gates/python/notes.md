# Python research gate notes

Raw notes for issue #5, gathered on 2026-09-26 in the `research/5-python-gate` worktree. Codex writes the conventions page and `.claude/rules/python.md` from these; nothing here changes `pyproject.toml`.

Every paragraph opens with an evidence label. `[verified]` means a command was run here and its output is quoted. `[observed]` means behaviour seen without a dedicated test. `[documented]` means a claim read in a cloned source at the SHA in `versions.md`. `[inference]` means a judgement drawn from the evidence. `[untested]` means a claim nobody checked. Citations are `path:line` relative to the clone root, or a command with its output.

Clones and versions are listed in `versions.md`. In short: cpython at tag `v3.14.6` (`c63aec69`), uv at `136ef973` (tag 0.12.19, nine patch releases ahead of the installed 0.12.10), ruff at `94e46ca1` (tag 0.16.9, the installed version), pytest at `87211735` (latest release tag 9.1.1), ty at `8e4aef29` (tag 0.0.84), mise at `fdfa0efe`. The worktree interpreter that `uv run` uses is the uv-managed CPython 3.14.3, not the mise-installed 3.14.6, for reasons covered under "uv and mise-managed Python".

## Summary

- Keep the `uv init` scaffold as one packaged project with the `src/` layout and `uv_build`; drop `main` and `[project.scripts]`; no workspace.
- Experiment scripts under `experiments/<NN-slug>/` are plain files run with `uv run path/to/script.py` from the repository root; they must not carry inline script metadata, and should run with `PYTHONSAFEPATH=1`.
- Development tools live in `[dependency-groups]`, not extras; `uv lock --check` and `uv sync --locked` are the check and CI commands.
- uv prefers its own managed CPython over the mise one. Pin `python = "3.14"` in `mise.toml` and export `UV_PYTHON` to the mise interpreter path, or the venv silently runs a different patch release than mise reports.
- Python 3.14 changes that matter most: no `from __future__ import annotations`, no asyncio policies or `get_event_loop`, no `return` inside `finally`, and warnings-as-errors in tests to surface pending removals. The free-threaded build is out of scope.
- ruff 0.16.9 enables 413 rules by default; the proposal extends that set rather than replacing it, disables `S603`, `S607`, `D105`, `D107`, and excludes `*.md` so Markdown stays with rumdl and guard-markdown.
- pytest 9.1: `strict_markers`, `strict_config`, `strict_xfail` as confvals (the `--strict-*` flags in `addopts` were silently ignored in 9.0.x), `--import-mode=importlib`, `filterwarnings = ["error"]`, and a `--run-integration` conftest gate for process and socket tests.
- Type checking: ty 0.0.84 is beta with `0.0.x` versioning and no stable API, but it runs clean on the scaffold, reads `requires-python`, understands the `src/` layout, and mise can pin it. Recommendation: adopt ty as a non-blocking check now, decide at the phase 1 checkpoint whether it gates.

## 1. Project layout, uv, and mise

### The scaffold and the src layout

[documented] `uv init` creates a packaged application by default with source under `src/<project_name>/`, a `uv_build` build system, and a `[project.scripts]` entry; before uv 0.12 applications had no build system. `docs/concepts/projects/init.md:5-18`, `docs/concepts/projects/init.md:38-69`. The worktree `pyproject.toml` matches that template (`uv_build>=0.12.10,<0.13.0`, `agent-orchestration-poc = "agent_orchestration_poc:main"`).

[documented] uv uses the presence of a `[build-system]` table to decide whether the project itself is installed into the environment; without one only the dependencies are installed. `docs/concepts/projects/config.md:104-107`. `uv_build` expects a single root module at `src/<package_name>/__init__.py`, with the name normalised from the project name, and `src/` as the default module root. `docs/concepts/build-backend.md:64-79`. The backend is pure Python only. `docs/concepts/build-backend.md:17-19`.

[verified] `mise exec -- uv build --wheel` in the worktree built `agent_orchestration_poc-0.1.0-py3-none-any.whl` containing `agent_orchestration_poc/__init__.py` and an `entry_points.txt`, so the layout is already a valid `uv_build` package; removing `[project.scripts]` drops the entry point file and nothing else.

[verified] The project is installed editable. `uv pip show agent-orchestration-poc` reports `Editable project location: <worktree>` and site-packages holds `agent_orchestration_poc.pth`, so edits under `src/` are visible without a re-sync. `docs/concepts/projects/sync.md:78-85` documents editable installation as the default for the project and workspace members.

[inference] Keep the packaged layout and the `uv_build` pin with its upper bound (`docs/concepts/build-backend.md:38-42` says the bound keeps builds working across uv releases). Removing `main` and `[project.scripts]` needs no `[tool.uv]` or `[tool.uv.build-backend]` setting; the defaults cover this structure.

### How experiment scripts import the helper package

[verified] A plain script outside the project root, run from the worktree with `mise exec -- uv run <scratch>/01-demo/probe.py`, imported `agent_orchestration_poc` from `src/` and printed `sys.path[0]` as the script's own directory. `uv run` discovers the project from the working directory, not from the script's location, so `uv run experiments/01-slug/script.py` from the repository root sees the package. `docs/concepts/projects/run.md:3-13`.

[verified] A script carrying inline metadata (`# /// script` ... `# ///`) run the same way failed with `ModuleNotFoundError: No module named 'agent_orchestration_poc'`. `docs/concepts/projects/run.md:42-65` and `docs/guides/scripts.md:197` say scripts with inline metadata run isolated from the project even when invoked inside one, and `--no-project` is not required. Rule: experiment scripts never carry a `# /// script` block; their dependencies go in the project.

[verified] `sys.path[0]` being the script directory means `experiments/01-slug/a.py` can `import b` from a sibling `b.py`. With `PYTHONSAFEPATH=1 mise exec -- uv run <script>` or `uv run python -P <script>` the sibling import fails with `ModuleNotFoundError: No module named 'sibling'`. `Doc/using/cmdline.rst:345-356` (cpython) documents `-P`, and `PYTHONSAFEPATH` at `Doc/using/cmdline.rst:766`. Recommendation: the mise task that runs an experiment script sets `PYTHONSAFEPATH=1`, so scripts only import the installed helper package and the stdlib, and a stray `json.py` next to a script cannot shadow the stdlib.

[documented] `uv run` forwards most Unix signals to the child, but forwards `SIGINT` only when it arrives more than once or when the child's process group differs from uv's, because a terminal already delivers Ctrl-C to the foreground group. `docs/concepts/projects/run.md:88-97`. A script that itself spawns harnesses must handle its own child cleanup; uv will not do it.

[inference] Scripts do not need `[tool.uv]` settings to import the package. `experiments/` stays outside the package and outside `testpaths`; shared code moves into `src/agent_orchestration_poc/`.

### Dependency groups versus extras

[documented] `[project.optional-dependencies]` are published extras; `[dependency-groups]` (PEP 735) are local development dependencies. `docs/concepts/projects/dependencies.md:8-16`. `uv add --dev` writes to the `dev` group, which has `--dev`, `--only-dev`, and `--no-dev` flags and is synced by default. `docs/concepts/projects/dependencies.md:657-676`. Other groups are added with `--group <name>` and included by `--all-groups`, `--group`, `--only-group`, or `tool.uv.default-groups`. `docs/concepts/projects/dependencies.md:679-757`.

[verified] `uv sync --locked --no-dev --dry-run` reports `Would uninstall 1 package - ruff==0.16.9`, confirming ruff sits in the default `dev` group and a runtime-only sync drops it.

[inference] This project publishes nothing, so no extras. One `dev` group holding `ruff`, `pytest`, the async pytest plugin, and (if adopted) `ty` is enough; split into `lint` and `test` groups only if a CI job wants a smaller install. Runtime dependencies that a helper module needs (a WebSocket client, say) go in `project.dependencies` because scripts import the package through the project environment.

### Locking and syncing in checks and CI

[documented] `uv run` and `uv sync` lock and sync automatically; `--locked` makes them fail instead of updating a stale lockfile; `--frozen` uses the lockfile without checking it. `docs/concepts/projects/sync.md:9-26`. `uv lock --check` is the standalone equivalent of `--locked`. `docs/concepts/projects/sync.md:44-50`.

[verified] In the worktree `mise exec -- uv lock --check` exited 0 (`Resolved 2 packages`) and `mise exec -- uv sync --locked` exited 0 (`Checked 2 packages`), so the committed lockfile matches `pyproject.toml`.

[documented] The uv GitHub Actions guide installs with `uv sync --locked --all-extras --dev` and runs `uv run pytest tests`. `docs/guides/integration/github.md:185-197`. `UV_PYTHON` can replace `setup-uv`'s `python-version` input. `docs/guides/integration/github.md:154-168`. The `astral-sh/uv-pre-commit` repository ships a `uv-lock` hook that keeps `uv.lock` current. `docs/guides/integration/pre-commit.md:11-24`.

[inference] Proposed check tasks, each run through mise: `uv lock --check` (lockfile matches manifest), `uv sync --locked` (environment matches lockfile; CI's install step), `uv run ruff check`, `uv run ruff format --check`, `uv run pytest`. Every tool invocation in a task or hook is `uv run <tool>` so the locked version runs, never a global install. A `prek` local hook running `uv lock --check` catches a manifest edit without a lock update before it is committed. `UV_LOCKED=1` in the CI environment (`crates/uv-static/src/env_vars.rs:382`) makes every `uv run` there strict without editing each command.

### uv and mise-managed Python

[verified] The repository `mise.toml` pins `uv = "latest"` and no Python. `mise which python` still resolves to `~/.local/share/mise/installs/python/3.14/bin/python` (CPython 3.14.6) because the user's global mise config sets `idiomatic_version_file_enable_tools = ["python", "node"]`, so mise reads the repository's `.python-version` (`3.14`). `docs/lang/python.md:73-83` in the mise clone documents that opt-in. A machine without that global setting gets no mise Python at all from this repository.

[verified] `mise exec -- uv run python --version` printed `Python 3.14.3` and created `.venv` from `~/.local/share/uv/python/cpython-3.14-macos-aarch64-none`. `uv python list` shows both the uv-managed 3.14.3 and the mise 3.14.6. `uv python find` with `UV_PYTHON_PREFERENCE=system` returns the mise interpreter instead.

[documented] uv treats every interpreter it did not install as a "system" Python, explicitly including ones managed by tools like pyenv. `docs/concepts/python-versions.md:6-18`. The `python-preference` setting defaults to `managed`, which prefers uv-managed installations over system ones; `system` and `only-system` invert that. `docs/concepts/python-versions.md:401-417`, `crates/uv-settings/src/settings.rs:342-352`. `UV_PYTHON` and `UV_PYTHON_PREFERENCE` are the environment forms. `crates/uv-static/src/env_vars.rs:107`, `crates/uv-static/src/env_vars.rs:222`.

[documented] The mise docs say the legacy `python.uv_venv_auto = true` exported `UV_PYTHON` as a bare version number, which does not guarantee uv picks the mise interpreter, and recommend `UV_PYTHON = { value = "{{ tools.python.path }}", tools = true }` under `[env]` with `python` pinned under `[tools]`. `docs/lang/python.md:196-212`. The `python.uv_venv_auto = "source"` setting activates uv's `.venv` for `mise exec`, and needs a `uv.lock` to find the project. `docs/lang/python.md:162-176`.

[verified] With `UV_PYTHON=$(mise which python)`, `uv sync --locked --dry-run` reports `Using CPython 3.14.6 interpreter at: .../mise/installs/python/3.14/bin/python` and `Would replace project environment at: .venv`. With `UV_PYTHON_PREFERENCE=system` alone it keeps the existing 3.14.3 venv (`Would make no changes`), because an existing venv is found before discovery runs.

[documented] For 3.14 and later uv allows free-threaded interpreters without an explicit request and still prefers the GIL build, but a free-threaded interpreter earlier on `PATH` wins; `3.14+gil` forces the GIL variant. `docs/concepts/python-versions.md:329-343`. The uv-managed `3.14.3+freethreaded` build is installed on this machine (`uv python list`), so the ordering caveat is live here.

[inference] Recommendation for #3: add `python = "3.14"` to `mise.toml` `[tools]` and `UV_PYTHON = { value = "{{ tools.python.path }}", tools = true }` to `[env]`, so uv, mise, and CI agree on one interpreter and `mise ls` reports the version that actually runs. Existing worktrees need one `uv sync` to rebuild `.venv` on that interpreter. Do not set `python-preference` in `pyproject.toml`; the env route keeps the manifest tool-neutral. `mise ls-remote python` lists 3.14.7 as the newest patch, so the pin move from 3.14.6 is a separate, deliberate change.

### Workspace verdict

[documented] Workspaces share one lockfile across several `pyproject.toml` members and are meant for a codebase split into multiple packages; they enforce a single `requires-python` and cannot isolate imports between members. `docs/concepts/projects/workspaces.md:11`, `docs/concepts/projects/workspaces.md:160-178`, `docs/concepts/projects/workspaces.md:202-209`.

[inference] One helper package and some scripts do not warrant a workspace. Revisit only if a second Python package appears (for example an in-image hook package that must not depend on the experiment helpers).

## 2. Python 3.14 and 3.13 changes that matter

Citations in this section are relative to the cpython clone at tag `v3.14.6`. Commands ran on the worktree's uv-managed CPython 3.14.3.

### Deferred annotation evaluation

[documented] Annotations are no longer evaluated eagerly; they are stored as annotate functions and evaluated on demand, so forward references no longer need quoting. `Doc/whatsnew/3.14.rst:148-160`. The new `annotationlib` module exposes `get_annotations(obj, format=...)` with `VALUE`, `FORWARDREF`, and `STRING` formats. `Doc/whatsnew/3.14.rst:161-183`.

[documented] The porting notes say code that supports only 3.14 and newer "may well be able to remove" `from __future__ import annotations`, and that reading `__annotations__` directly off a class namespace or instance no longer works; use `annotationlib.get_annotations` with `FORWARDREF`, as `dataclasses` now does. `Doc/whatsnew/3.14.rst:3348-3358`, `Doc/whatsnew/3.14.rst:3364-3400`.

[verified] `annotationlib.get_annotations(f, format=Format.STRING)` on a function annotated with an undefined name returned `{'x': 'Undefined', 'return': 'None'}` without a `NameError`.

[inference] With `requires-python = ">=3.14"` the rules forbid `from __future__ import annotations` and quoted forward references in new code. The stdlib-only helper package has no third-party annotation reader to worry about.

### Syntax changes

[documented] `except A, B:` and `except* A, B:` without parentheses are allowed when there is no `as` clause (PEP 758). `Doc/whatsnew/3.14.rst:913-930`. Template strings (`t"..."`, PEP 750) return a `string.templatelib.Template` instead of a `str`. `Doc/whatsnew/3.14.rst:301-383`. Neither is needed here; JSON goes through `json` and commands are argv lists. The ruff 0.16.9 formatter removes exception-tuple parentheses on py314 (see section 3), so the bracketless form is what the tree will contain.

[documented] `return`, `break`, or `continue` leaving a `finally` block now emits a `SyntaxWarning` at compile time (PEP 765), which `-W error` turns into a `SyntaxError`. `Doc/whatsnew/3.14.rst:933-957`. With `filterwarnings = ["error"]` in pytest (section 4) such a function fails at import. Rule: never leave a `finally` block early.

[documented] `python -c` dedents its argument (`Doc/whatsnew/3.14.rst:899-902`); `int()` no longer calls `__trunc__` (`Doc/whatsnew/3.14.rst:855-859`); `NotImplemented` in a boolean context raises `TypeError` (`Doc/whatsnew/3.14.rst:872-875`); docstrings have common leading whitespace stripped by the compiler since 3.13, which changes `__doc__` and doctest expectations (`Doc/whatsnew/3.13.rst:495-513`).

### asyncio

[documented] `asyncio.get_event_loop()` now raises `RuntimeError` when there is no current loop instead of creating one; the replacements are `asyncio.run(main())`, `asyncio.run` with `await asyncio.Event().wait()` for serve-forever, and `asyncio.Runner` for interleaving with blocking code. `Doc/whatsnew/3.14.rst:2399-2500`.

[documented] The whole event loop policy system (`AbstractEventLoopPolicy`, `DefaultEventLoopPolicy`, `get_event_loop_policy`, `set_event_loop_policy`) is deprecated for removal in 3.16; pass `loop_factory=` to `asyncio.run` or `asyncio.Runner` instead. `Doc/whatsnew/3.14.rst:2630-2652`, `Doc/deprecations/pending-removal-in-3.16.rst:24-41`. `asyncio.iscoroutinefunction` is deprecated for 3.16; use `inspect.iscoroutinefunction`. `Doc/whatsnew/3.14.rst:2624-2628`.

[verified] `python -W error -c 'import asyncio; asyncio.get_event_loop_policy()'` fails with `DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16`.

[documented] All child watcher classes and `get_child_watcher`/`set_child_watcher` are removed in 3.14; asyncio subprocesses need no watcher setup. `Doc/whatsnew/3.14.rst:2384-2397`. `create_task` now forwards arbitrary keyword arguments to the task factory. `Doc/whatsnew/3.14.rst:1100-1116`. `python -m asyncio ps PID` and `pstree PID` print a task table or await tree for a running Python process, and `asyncio.capture_call_graph` and `print_call_graph` do the same in-process. `Doc/whatsnew/3.14.rst:691-800`, `Doc/whatsnew/3.14.rst:1118-1124`.

[documented] 3.13: `loop.create_unix_server` removes the socket file when the server closes (`Doc/whatsnew/3.13.rst:683-685`); `asyncio.Queue.shutdown` and `QueueShutDown` (`Doc/whatsnew/3.13.rst:693-695`); `Server.close_clients` and `abort_clients` (`Doc/whatsnew/3.13.rst:702-704`); `StreamReader.readuntil` accepts a tuple of separators (`Doc/whatsnew/3.13.rst:706-708`); `as_completed` yields the original tasks as an async iterator (`Doc/whatsnew/3.13.rst:675-681`). Neither whatsnew changes `asyncio.open_unix_connection`, `start_unix_server`, `TaskGroup`, `asyncio.timeout`, or `asyncio.run` signal handling.

[inference] Helper-library rule: enter asyncio only through `asyncio.run` or `asyncio.Runner`; use `TaskGroup` and `asyncio.timeout`; open Unix sockets with `asyncio.open_unix_connection` and `start_unix_server`; keep every `create_task` result or use a `TaskGroup` (ruff `RUF006`).

### Processes, paths, and JSON

[documented] Since 3.13 `subprocess` uses `posix_spawn` in more cases, including the default `close_fds=True` on libcs with `posix_spawn_file_actions_addclosefrom_np`. `Doc/whatsnew/3.13.rst:1255-1274`. `os.popen` and `os.spawn*` are soft deprecated in 3.14; use `subprocess`. `Doc/whatsnew/3.14.rst:2706-2711`. `subprocess.Popen`, `os.fork`, and thread starts raise `PythonFinalizationError` during interpreter shutdown. `Doc/whatsnew/3.13.rst:577-587`.

[documented] On Unix other than macOS, `multiprocessing` and `ProcessPoolExecutor` default to `forkserver` in 3.14 instead of `fork`; macOS stays on `spawn`. `Doc/whatsnew/3.14.rst:1602-1622`, `Doc/whatsnew/3.14.rst:3281-3292`. This matters only if code inside the Linux agent image reaches for a process pool. `os.process_cpu_count()` (3.13) and `PYTHON_CPU_COUNT` report cores usable by this process. `Doc/whatsnew/3.13.rst:1039-1049`. `threading.Thread.start` sets the OS thread name from `Thread.name`. `Doc/whatsnew/3.14.rst:1946-1948`.

[documented] pathlib in 3.14 adds `Path.copy`, `copy_into`, `move`, `move_into`, and `Path.info` with cached stat results. `Doc/whatsnew/3.14.rst:1690-1709`. 3.13 adds `Path.from_uri`, `PurePath.full_match`, `recurse_symlinks=` on `glob`/`rglob`, and `glob("**")` now returns files as well as directories. `Doc/whatsnew/3.13.rst:1104-1138`. Removed: extra keyword arguments to `Path(...)`, extra positional arguments to `relative_to` (`Doc/whatsnew/3.14.rst:2534-2545`), and `Path` as a context manager (3.13, `Doc/whatsnew/3.13.rst:1733-1738`). `PurePath.is_reserved` is pending removal in 3.15. `Doc/deprecations/pending-removal-in-3.15.rst:44-48`.

[verified] `Path.copy`, `Path.move`, `Path.info`, `Path.from_uri`, and `Path.full_match` exist on 3.14.3.

[documented] `python -m json` replaces `python -m json.tool` (soft deprecated) and colours output by default; serialisation errors carry notes naming the offending value. `Doc/whatsnew/3.14.rst:1485-1503`. [verified] `python -m json --help` lists `--json-lines`, `--compact`, `--indent`, `--sort-keys`, and `--no-ensure-ascii`, so the CLI validates and pretty-prints JSON lines evidence files. No `json.loads` or `json.dumps` semantic change is listed in either whatsnew; JSON lines parsing stays one `json.loads` per line.

### The free-threaded build

[documented] PEP 779: the free-threaded build is officially supported and no longer experimental as of 3.14, "phase II" where it is supported but optional. `Doc/whatsnew/3.14.rst:3214-3241`. Single-threaded overhead is about 5 to 10 percent (`Doc/whatsnew/3.14.rst:478-490`), or about 1 percent on macOS aarch64 to 8 percent on x86-64 Linux per the howto (`Doc/howto/free-threading-python.rst:137-143`). Thread safety of `dict`, `list`, and `set` is "a description of the current implementation, not a guarantee"; the howto recommends explicit locks. `Doc/howto/free-threading-python.rst:78-125`.

[documented] Free-threaded builds flip `thread_inherit_context` and `context_aware_warnings` to true, changing contextvar inheritance and `catch_warnings` scope. `Doc/whatsnew/3.14.rst:495-517`, `Doc/howto/free-threading-python.rst:146-172`. Memory use is higher. `Doc/howto/free-threading-python.rst:174-296`. The JIT is unavailable there. `Doc/whatsnew/3.14.rst:3265-3266`. `sysconfig.get_config_var("Py_GIL_DISABLED") == 1` is the build-time check; `PYTHON_GIL=1` re-enables the GIL; importing a C extension not marked safe re-enables it with a warning. `Doc/howto/free-threading-python.rst:44-70`.

[verified] The worktree interpreter is a GIL build (`Py_GIL_DISABLED` is 0). `uv python list` shows `cpython-3.14.3+freethreaded-macos-aarch64-none` installed, so uv can supply `3.14t`; `mise ls-remote python` lists plain 3.14.x versions and free-threaded mise support was not checked here [untested].

[inference] Recommendation: do not use `3.14t`. The scripts are asyncio, I/O bound, one process each. Free threading buys nothing, costs a few percent, changes warnings and contextvar semantics, and any wheel without a free-threaded build re-enables the GIL silently. Keep `.python-version` at `3.14` and, given the uv ordering caveat above, request `3.14+gil` if a free-threaded build ever lands earlier on `PATH`.

### REPL, command line, and environment

[documented] 3.13 replaced the REPL with PyREPL and 3.14 added syntax highlighting and import completion; `PYTHON_BASIC_REPL=1` restores the old one. `Doc/whatsnew/3.13.rst:213-234`, `Doc/whatsnew/3.14.rst:995-1020`. Colour in tracebacks, `argparse` help, `json`, `unittest`, and the REPL is on by default and controlled by `PYTHON_COLORS`, `NO_COLOR`, and `FORCE_COLOR`. `Doc/whatsnew/3.13.rst:116-120`, `Doc/whatsnew/3.14.rst:1069-1072`, `Doc/whatsnew/3.14.rst:1499-1503`.

[inference] Evidence scripts that capture a child Python's stderr or `--help` output should set `NO_COLOR=1` in the child's environment so recorded output has no ANSI escapes, and `PYTHONUNBUFFERED=1` (`Doc/using/cmdline.rst:844`) so partial output survives a kill.

[documented] `-X importtime=2` reports cached imports (`Doc/whatsnew/3.14.rst:887-897`); `PYTHON_JIT=1` enables the experimental JIT in macOS and Windows binaries and is not recommended for production (`Doc/whatsnew/3.14.rst:3244-3269`); `sys.remote_exec(pid, path)` (PEP 768) and `python -m pdb -p PID` attach to a running Python, disabled by `PYTHON_DISABLE_REMOTE_DEBUG` (`Doc/whatsnew/3.14.rst:385-437`). `-O` no longer hides certain syntax errors. `Doc/whatsnew/3.14.rst:824-831`. [verified] `sys._jit.is_available()` is `True` on the uv-managed build; leave `PYTHON_JIT` unset.

[documented] 3.14.0 through 3.14.4 shipped an incremental garbage collector; 3.14.5 reverted to the 3.13 generational one after memory-pressure reports. `Doc/whatsnew/3.14.rst:960-993`, `Doc/whatsnew/3.14.rst:3486-3497`. Only relevant to experiments recording memory across patch releases.

### Typing, dataclasses, and other additions

[documented] 3.13: PEP 696 defaults for `TypeVar`, `ParamSpec`, and `TypeVarTuple`; `warnings.deprecated`; `typing.ReadOnly`; `typing.TypeIs`; `typing.NoDefault`. `Doc/whatsnew/3.13.rst:161-169`, `Doc/whatsnew/3.13.rst:1388-1412`. 3.14: `types.UnionType` and `typing.Union` are the same runtime type, `repr` is `int | str`, old-style unions are no longer cached so compare with `==` not `is`. `Doc/whatsnew/3.14.rst:1979-2036`. `typing.io` and `typing.re` were removed in 3.13. `Doc/whatsnew/3.13.rst:1766-1777`. `typing.no_type_check_decorator` is pending removal in 3.15 and `typing.ByteString` in 3.17. `Doc/deprecations/pending-removal-in-3.15.rst:76-92`, `Doc/deprecations/pending-removal-in-3.17.rst:4-22`.

[documented] `copy.replace()` and `__replace__` (3.13) work on dataclasses, namedtuples, `datetime`, and `SimpleNamespace`. `Doc/whatsnew/3.13.rst:786-804`. `functools.partial` is now a method descriptor; wrap in `staticmethod` for the old class-attribute behaviour. `Doc/whatsnew/3.14.rst:3294-3296`.

[documented] Also new in 3.14: `compression.zstd` (`Doc/whatsnew/3.14.rst:648-689`), `concurrent.interpreters` and `InterpreterPoolExecutor` (`Doc/whatsnew/3.14.rst:202-299`), `uuid.uuid6/7/8` (`Doc/whatsnew/3.14.rst:2111-2125`), `argparse` `suggest_on_error=` and `color=` with `argparse.FileType` deprecated (`Doc/whatsnew/3.14.rst:1054-1072`, `Doc/whatsnew/3.14.rst:2612-2616`), `map(strict=True)` (`Doc/whatsnew/3.14.rst:861-863`), `datetime.date.strptime` (`Doc/whatsnew/3.14.rst:1273-1278`), `logging.handlers.QueueListener` as a context manager (`Doc/whatsnew/3.14.rst:1513-1522`). [verified] `compression.zstd`, `concurrent.interpreters`, `uuid.uuid7`, and `sys.remote_exec` all import on 3.14.3.

[inference] `uuid.uuid7()` is the right choice for time-ordered run and evidence identifiers.

### Removals and deprecations a worker might still write

[documented] Removed in 3.13 (PEP 594): `aifc`, `audioop`, `cgi`, `cgitb`, `chunk`, `crypt`, `imghdr`, `mailcap`, `msilib`, `nis`, `nntplib`, `ossaudiodev`, `pipes`, `sndhdr`, `spwd`, `sunau`, `telnetlib`, `uu`, `xdrlib`, plus `lib2to3`. `Doc/whatsnew/3.13.rst:1508-1660`. `pipes` and `telnetlib` are the ones a process script might reach for.

[documented] Removed in 3.14: `ast.Num`, `ast.Str`, `ast.Bytes`, `ast.NameConstant`, `ast.Ellipsis`, asyncio child watchers, `pkgutil.get_loader` and `find_loader`, `pty.master_open` and `slave_open`, `sqlite3.version`, `urllib.request.URLopener`, `itertools` pickling. `Doc/whatsnew/3.14.rst:2331-2597`.

[documented] Pending removal in 3.15: `typing.no_type_check_decorator`, `PurePath.is_reserved`, `platform.java_ver`, `locale.getdefaultlocale`, `http.server.CGIHTTPRequestHandler`, `threading.RLock(args)`, `CodeType.co_lnotab`, importlib `load_module()`. `Doc/deprecations/pending-removal-in-3.15.rst:1-111`. Pending removal in 3.16: asyncio policies, `asyncio.iscoroutinefunction`, `shutil.ExecError`, `logging` `strm=`, `array` `'u'`, `~True`, `functools.reduce(function=, sequence=)`. `Doc/deprecations/pending-removal-in-3.16.rst:1-105`, `Doc/whatsnew/3.14.rst:2676-2679`.

[documented] Deprecated without a date: `datetime.utcnow()` and `utcfromtimestamp()` (use `datetime.now(tz=UTC)`), `logging.warn`, `codecs.open`, `shutil.rmtree(onerror=)` (use `onexc=`), the `sre_*` modules, `typing.Text`, the camelCase `threading` aliases, `os.register_at_fork` in a multithreaded process. `Doc/deprecations/pending-removal-in-future.rst:1-156`. [verified] `python -W error -c 'import datetime; datetime.datetime.utcnow()'` fails with the deprecation, so pytest's warnings-as-errors will catch it.

[documented] Other traps: passing a `bool` as a file descriptor warns (`Doc/whatsnew/3.13.rst:592-595`); `urllib.request.urlopen` lost `cafile`, `capath`, and `cadefault` in 3.13 (`Doc/whatsnew/3.13.rst:1802-1812`); `sys.platform` on FreeBSD is bare `freebsd` (`Doc/whatsnew/3.14.rst:1884-1887`).

## 3. Proposed ruff configuration

Citations are relative to the ruff clone at `94e46ca1` (tag 0.16.9). Commands ran with the worktree's ruff 0.16.9 through `mise exec -- uv run ruff`. The scratch configuration used to test the proposal carried `target-version = "py314"` only because `--config <file>` disables inference.

### Target version

[verified] Ruff infers `target-version` from `requires-python` when no discovered configuration sets it; a configuration file passed with `--config` disables the inference. `docs/configuration.md:305-314`. In the worktree `uv run ruff check --show-settings src` reports `linter.unresolved_target_version = 3.14` with no `[tool.ruff]` table present, while `--isolated` reports `none`.

[documented] The setting defaults to `py310` and an explicit `target-version` takes precedence over `requires-python`. `crates/ruff_workspace/src/options.rs:363-394`. Recommendation: omit `target-version` and let `requires-python` be the single source of truth.

[verified] On py314 the formatter removes parentheses around exception tuples: `ruff format --isolated --target-version py314 --diff` rewrote `except (ValueError, TypeError):` to `except ValueError, TypeError:`, while `--target-version py313` left it alone. The 2026 style change is listed at `changelogs/0.15.x.md:82-83`. Template strings became a parse target in 0.12 and a syntax error before 3.14. `changelogs/0.12.x.md:103`.

[documented] `FA100` only flags annotations that need the future import for the target version, so on py314 it stays quiet; `UP037` removes unnecessary quotes and only adds the future import under preview with `lint.future-annotations = true`, which defaults to `false`. `ruff rule FA100`, `ruff rule UP037`, `crates/ruff_workspace/src/options.rs:606-613`, `changelogs/0.13.x.md:9-15`. Ruff does not model PEP 649; it simply stops asking for the import. Leave `future-annotations` off and set no `isort.required-imports`.

### The 0.16 default set

[documented] ruff 0.16.0 enables 413 rules by default, up from 59, organised by the categories correctness, suspicious, complexity, performance, and style, while dropping 18 opinionated `E` and `F` rules (`E401`, `E402`, `E701` to `E703`, `E711` to `E714`, `E721`, `E731`, `E741` to `E743`, `F403`, `F405`, `F406`, `F722`). `CHANGELOG.md:424-428`. The `security`, `formatting`, `pedantic`, and `restriction` categories are off by default and category selectors work only in preview. `docs/linter.md:147-150`, `docs/linter.md:205-208`.

[observed] `ruff check --isolated --show-settings src` lists 413 enabled rules. Membership is not purely by category: `ASYNC212`, `ASYNC240`, and `ASYNC250` carry the `suspicious` category yet are absent, so check `--show-settings` rather than the category when in doubt.

[inference] `docs/linter.md:66-70` still recommends an explicit `lint.select`, but a 413-rule default makes that impractical. The proposal uses `extend-select` on top of the defaults and relies on the exact pin: `uv.lock` records `ruff 0.16.9`, so the enabled set changes only when the pin moves, and PLAN.md already makes the pin-moving PR update the rules.

### Rule selection

[documented] Added on top of the defaults: `I` (isort; only `I001` is default), `D` scoped by the google convention (`docs/faq.md:461-552`), `ANN` for a typed helper package (`ANN401` flags bare `Any`), `S` because the security category is off by default and `docs/linter.md:205-207` names it as a category worth enabling whole, `T20` to keep `print` out of the library, `N`, `PT` (`fixture-parentheses` defaults to `false`, so `@pytest.fixture` without parentheses is the enforced form, `crates/ruff_workspace/src/options.rs:1838-1848`), `ARG`, `ERA` (commented-out code, a habit of models), `PTH` (pathlib over `os.path`), `PGH` (blanket `noqa` and `type: ignore`), `INP` (implicit namespace packages, with scripts and tests exempted), `A` (builtin shadowing), `LOG` and `G` (root logger and f-string logging), `RET`, plus single rules `TC006`, `RUF006` (dangling `asyncio.create_task`), `ASYNC110` (busy wait), `PLC0415` (import outside top level), `PLR0913` (more than five arguments, `crates/ruff_workspace/src/options.rs:3652-3656`), `B904` (`raise ... from` inside `except`), and `TRY400` (`logging.exception` in handlers).

[documented] Excluded: `COM812` and `COM819`, all of `Q`, `W191`, `E111`, `E114`, `E117`, `D206`, `D300`, and `ISC002` without `ISC001` conflict with the formatter. `docs/formatter.md:426-440`. `E501` is only best-effort compatible because the formatter wraps by best effort. `docs/formatter.md:442-445`. `D203` and `D213` are disabled by the google convention and the formatter removes the blank line `D203` wants (`ruff rule D203`). `EM` and `TRY003` force message variables before every raise; `FBT` is noisy for script flags; `TC001` to `TC003` move imports under `TYPE_CHECKING`, which changes what `annotationlib` can resolve at runtime for no gain on 3.14; `C901` and the other pylint size limits stay off; `lint.preview` and `format.preview` stay off (`docs/preview.md:3-8`, `docs/versioning.md:83`).

[documented] `lint.ignore`: `S603` is "prone to false positives" per its own Known problems section (`ruff rule S603`) and `S607` flags partial executable paths, but the harness binaries `claude`, `codex`, and `agy` resolve on `PATH` through mise, so absolute paths would be wrong here; `D105` and `D107` (docstrings on magic methods and `__init__`). Everything else in `S` stays on, including `S108` (hardcoded `/tmp`), `S110` (`try`/`except`/`pass`), and the `S6xx` shell rules.

### Per-file ignores, isort, and pydocstyle

[documented] `lint.per-file-ignores` maps globs relative to the project root to rule selectors, and the built-in example exempts script directories from `INP001`. `crates/ruff_workspace/src/options.rs:1100-1111`. Proposal: `"tests/**" = ["S101", "PLR2004", "ANN", "D", "ARG", "INP001"]` and `"experiments/**" = ["T20", "INP001", "D", "ANN"]`.

[documented] No `__init__.py` entry: `ignore-init-module-imports` is deprecated since 0.4.4, `F401` still reports unused imports in `__init__.py`, and the recommended pattern is an explicit `__all__`. `crates/ruff_workspace/src/options.rs:876-887`, `ruff rule F401`.

[verified] Ruff resolves first-party imports through `src`, which defaults to the project root and its `src/` subdirectory (`crates/ruff_workspace/src/options.rs:415-425`), and since 0.13.0 checks that the module path exists on disk (`changelogs/0.13.x.md:16-22`). `known-first-party = ["agent_orchestration_poc"]` is therefore redundant in the repository but keeps sorting stable when ruff runs from a subdirectory.

[verified] `convention = "google"` enables `D` then disables the rules outside the convention; with the proposal `--show-settings` lists `D200` to `D202`, `D205` to `D212`, `D214`, `D402`, `D403`, `D405`, `D410` to `D412`, `D414` to `D419`, and none of `D203`, `D213`, `D400`, `D401`, `D404` to `D409`, `D413`. The `D1xx` undocumented-public rules stay active for `src/`.

### Formatter, excludes, and Markdown

[documented] Defaults: `line-length` 88 (`crates/ruff_workspace/src/options.rs:472-483`), `indent-style = "space"`, `quote-style = "double"`, `skip-magic-trailing-comma = false`, `line-ending = "auto"`, `docstring-code-format = false` (`crates/ruff_workspace/src/options.rs:3946-4139`). Proposal: `docstring-code-format = true` so fenced examples in helper docstrings are formatted (`docs/formatter.md:137-160`) and `line-ending = "lf"` so macOS and Linux CI agree; leave the rest at defaults. F-string formatting has been stable since 0.9.0 (`docs/formatter.md:505-508`); t-string formatting is [untested].

[verified] Since 0.16.0 `ruff format` formats Python fenced blocks in `.md` files by default. `CHANGELOG.md:431`, `docs/formatter.md:228-330`. In the worktree `ruff format --check .` with no configuration reported `29 files already formatted` while only two Python files exist; the other 27 are Markdown. With `extend-exclude = ["*.md"]` the count drops. Recommendation: exclude `*.md`, because `research/imported/` is a verbatim copy, evidence transcripts must not be rewritten, and Markdown is owned by rumdl and guard-markdown; narrow the exclusion later if formatting examples under `docs/` is wanted.

[documented] The default `exclude` already lists `.venv`, `.git`, `build`, `dist`, `node_modules`, and the cache directories (`crates/ruff_workspace/src/options.rs:212-219`), and `respect-gitignore` defaults to `true` (`crates/ruff_workspace/src/options.rs:304-311`), so the gitignored `.worktrees/` is skipped already. `extend-exclude = [".worktrees", "research/imported", "design-sketch", "*.md"]` keeps the PLAN.md rule true even under `--no-respect-gitignore`.

### Check tasks and hooks

[documented] `ruff check` exits 0 clean, 1 on violations, 2 on bad configuration (`docs/linter.md:687-705`); `ruff format --check` exits 1 when any file would change (`docs/formatter.md:466-482`). Since 0.16.0 `format --check` shows the diff inline and accepts the linter's `--output-format` values including `github`. `CHANGELOG.md:443-465`. [verified] `ruff format --check --output-format github` on a scratch `x=1` emitted a `::error title=ruff (unformatted),file=...` annotation.

[documented] `--fix` applies safe fixes only; unsafe fixes need `--unsafe-fixes` (`docs/linter.md:270-300`). With `--fix`, the lint hook runs before the format hook because fixes can need reformatting (`docs/integrations.md:151-156`). Proposal: mise tasks `uv run ruff check` and `uv run ruff format --check`, CI adds `--output-format=github` to both, and a `prek` local hook runs `uv run ruff check --fix` then `uv run ruff format` on staged Python files.

[documented] Removed or deprecated codes a model may still emit (`ruff rule --all --output-format json`, 17 entries): `ANN101`, `ANN102`, `S320`, `S410`, `PT004`, `PT005`, `PD901`, `E999`, `PGH001`, `PGH002`, `PLR1701`, `PLR1706`, `UP027`, `UP038`, `RUF011`, `RUF035`, `TRY200`. Since 0.13.0 a deprecated rule is selected only by its exact code, never by prefix (`changelogs/0.13.x.md:27-32`). The flake8-type-checking prefix is `TC`, not `TCH`. 0.15.0 added block suppression `# ruff: disable[...]` / `# ruff: enable[...]` (`changelogs/0.15.x.md:10-20`) and 0.16.0 added `# ruff: ignore[CODE]` on the line or the line before (`CHANGELOG.md:434-439`).

### Proposed configuration

[verified] Run against the worktree `src/` through a scratch copy of this configuration, `ruff check` reported `D104`, `D103`, and `T201` on the placeholder `main()` (which the plan removes) and `ruff format --check` reported `1 file already formatted`; `--show-settings` lists 614 enabled rules. A scratch tree mirroring the intended layout produced findings only in `src/` and `tests/` (`D103`, `ANN001`, `PTH123`, `T201`, `ERA001`, `ASYNC221`, `PLW1510`, `RUF006`, `PTH118`, `BLE001`, `B904`, `PT001`), and nothing for the experiment script's `print`, missing `__init__.py`, or PATH-resolved `subprocess.run(["claude", ...])`.

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

## 4. Proposed pytest configuration

Citations are relative to the pytest clone at `87211735`. pytest is not installed in the project; `uv run --with pytest` resolved 9.1.1 for the observations below.

### Which table

[documented] pytest 9.0 added a native `[tool.pytest]` table in `pyproject.toml` with real TOML types, while `[tool.pytest.ini_options]` remains supported as INI compatibility mode where every value is a string or list of strings; the two cannot be combined. `doc/en/reference/customize.rst:78-98`, `doc/en/changelog.rst:526-545`.

[inference] The coordinator asked for `[tool.pytest.ini_options]`, and that form is shown below. Since pytest is pinned by `uv.lock` at 9.1.1, the native `[tool.pytest]` table with `addopts = ["-ra", "--import-mode=importlib"]` is the better choice for #6; the keys are identical.

### Strictness

[documented] 9.0 re-purposed `--strict` as "strict mode", which enables `strict_config`, `strict_markers`, `strict_parametrization_ids`, `strict_xfail`, and any future strictness option; the docs advise enabling it only with a pinned pytest. `doc/en/reference/reference.rst:2421-2457`. `strict_markers`, `strict_config`, and `strict_xfail` (renamed from `xfail_strict`, kept as an alias) exist as individual confvals. `doc/en/reference/reference.rst:2458-2506`, `doc/en/reference/reference.rst:2559-2587`.

[documented] pytest 9.0.0 through 9.0.3 silently ignored `--strict-markers` and `--strict-config` given through `addopts`; 9.1.0 fixed it and recommends the confvals or strict mode on 9.x. `doc/en/changelog.rst:288-290`. Recommendation: set the three confvals individually, not `strict = true`, so a lock bump cannot switch on a new strictness option unannounced.

### Paths and import mode

[documented] `testpaths` restricts collection when no paths are given on the command line. `doc/en/reference/reference.rst:2588-2599`. `pythonpath` prepends to `sys.path` and is the documented workaround when the package is not installed. `doc/en/reference/reference.rst:2373-2381`, `doc/en/explanation/goodpractices.rst:127-142`.

[inference] `pythonpath` is not needed: `uv run` installs the project editable (section 1), and `pythonpath = ["src"]` would mask a packaging error that `uv sync --locked` should catch.

[documented] The good-practices page recommends `--import-mode=importlib` with a `src/` layout for new projects; `prepend` stays the default for historical reasons and the maintainers say `importlib` will not become the default. `doc/en/explanation/goodpractices.rst:95-110`, `doc/en/explanation/pythonpath.rst:99-100`. Under `importlib` test modules cannot import each other and helpers under `tests/` are not importable; shared helpers belong in the application package or in `conftest.py` fixtures. `doc/en/explanation/pythonpath.rst:56-70`.

[inference] `tests/` gets no `__init__.py`; shared test helpers (a fake harness process, a socket server factory) live in `src/agent_orchestration_poc/testing.py` or as `conftest.py` fixtures.

### Markers and the skip-by-default gate

[documented] With `strict_markers` on, any marker not registered under `markers` is an error on tests and in `-m` expressions. `doc/en/reference/reference.rst:2186-2210`, `doc/en/how-to/mark.rst:34-105`. The `--runslow` example registers an option in `pytest_addoption` and, in `pytest_collection_modifyitems`, adds `pytest.mark.skip` to marked items unless the option was given. `doc/en/example/simple.rst:251-277`.

[verified] A scratch project mirroring the layout, run with `mise exec -- uv run --no-project --with pytest pytest`, produced: default run `1 passed, 1 skipped` with `SKIPPED [1] tests/test_basic.py:8: needs --run-integration` in the `-ra` summary; `--run-integration` gave `2 passed`; a test marked `integraton` failed collection with `'integraton' not found in `markers` configuration option`; an unknown key in the table failed with `ERROR: Unknown config option: bogus_key`.

[inference] Markers: `integration` (needs a spawned process or a running harness), `socket` (needs a Unix socket or WebSocket endpoint), `slow` (informational, deselect with `-m "not slow"`). `integration` and `socket` skip unless `--run-integration` is passed; CI runs the default job now and a second `--run-integration` step once the harness image exists.

```python
# tests/conftest.py
import pytest

RUN_FLAG = "--run-integration"
GATED = ("integration", "socket")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(RUN_FLAG, action="store_true", default=False, help="run tests marked integration or socket")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption(RUN_FLAG):
        return
    skip = pytest.mark.skip(reason=f"needs {RUN_FLAG}")
    for item in items:
        if any(item.get_closest_marker(name) for name in GATED):
            item.add_marker(skip)
```

### Warnings, xfail, logging, and output

[documented] `filterwarnings = ["error", ...]` turns every unlisted warning into a failure, with `ignore:` entries as escapes. `doc/en/reference/reference.rst:1677-1695`, `doc/en/how-to/capture-warnings.rst:84-106`. [verified] A scratch test calling `warnings.warn("x", DeprecationWarning)` failed with `DeprecationWarning: x`.

[inference] Recommend `filterwarnings = ["error"]` from day one: the 3.15 and 3.16 pending removals from section 2 surface as failures while the code is small, and each third-party escape becomes a commented `ignore:` line that documents itself.

[documented] `strict_xfail = true` makes an unexpectedly passing xfail fail (`doc/en/reference/reference.rst:2559-2565`); `minversion` fails the run under an older pytest (`doc/en/reference/reference.rst:2215-2218`); `log_level` sets the captured log level and `log_cli` streams logs live (`doc/en/reference/reference.rst:1904-1910`, `doc/en/reference/reference.rst:2159-2168`); `-r a` reports everything except passes and `-ra` is the docs' own example (`doc/en/how-to/output.rst:429`); `console_output_style` defaults to `progress` and `junit_family` to `xunit2`, so neither needs setting. 9.0 added `faulthandler_exit_on_timeout` so a deadlocked run can be killed after `faulthandler_timeout`; worth adding once process tests exist.

### Async tests

[documented] pytest has no native async support; `src/_pytest/python.py:167-175` builds the message "async def functions are not natively supported. You need to install a suitable plugin for your async framework, for example: anyio, pytest-asyncio, pytest-tornasync, pytest-trio, pytest-twisted". [verified] A scratch `async def test_coro()` failed with exactly that message under 9.1.1. Since 9.0 a sync test requesting an async fixture is an error. `doc/en/deprecations.rst:522-577`.

[inference] The helper library is asyncio-based, so the dev group needs one plugin. `pytest-asyncio` with `asyncio_mode = "auto"` is the conventional choice for pure-asyncio code; `anyio` is the alternative pytest lists first. Neither was cloned or run [untested]; the #6 worker verifies against the plugin's docs at a recorded commit. `asyncio_mode` is the plugin's key, and `strict_config` rejects it if the plugin is absent.

### Fixtures for processes and sockets

[documented] Yield fixtures run teardown after the `yield` in reverse order and are the recommended finalisation form; `module`, `package`, and `session` scopes exist for expensive resources. `doc/en/how-to/fixtures.rst:497-499`, `doc/en/how-to/fixtures.rst:553-575`. `tmp_path` is a per-test `pathlib.Path`; `monkeypatch.setenv` and `delenv` scope environment changes to one test. `doc/en/how-to/tmp_path.rst:8-14`, `doc/en/how-to/monkeypatch.rst:21-50`.

[verified] Binding an `AF_UNIX` socket to a 110-character path under `tempfile.mkdtemp()` raised `OSError: AF_UNIX path too long` on macOS, while a 71-character path bound fine. pytest's `tmp_path` lives under `/private/var/folders/...`, so socket fixtures create their socket under a short directory (`tempfile.mkdtemp(dir="/tmp")`) and remove it in teardown, not under `tmp_path`. Note that `S108` then needs a per-line `noqa` with the reason.

[inference] Process fixture pattern: a `module` or `session` scoped yield fixture starts the child with `subprocess.Popen` (or `asyncio.create_subprocess_exec` under the plugin), polls the socket path for readiness with a deadline, yields the handle, then terminates, waits with a timeout, and kills. Mark such tests `integration`, and `socket` when readiness is a socket connect.

### Deprecated and removed things a worker might still write

[documented] Removed in 8.0: nose-style `setup`/`teardown` and `with_setup` (`doc/en/deprecations.rst:676-690`). Removed in 8.4: `yield` tests (`doc/en/deprecations.rst:640-648`). 9.0: `PytestRemovedIn9Warning` deprecations became errors, Python 3.9 dropped. Deprecated in 9.1 for removal in 10: class-scoped fixtures as instance methods without `@classmethod`, `request.getfixturevalue()` during teardown, generators as `parametrize` argvalues, `config.inicfg`, `--pastebin`. `doc/en/changelog.rst:53-120`. `pytest.importorskip` now raises on `ImportError` subclasses other than `ModuleNotFoundError`. `doc/en/deprecations.rst:457-480`.

### Proposed configuration

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

[verified] That table drove the scratch runs above. On pytest 9.1 the same keys under `[tool.pytest]` with a list-valued `addopts` are preferred; never keep both tables. Add `asyncio_mode = "auto"` only after `pytest-asyncio` joins the dev group, and `faulthandler_timeout` once process tests exist.

## 5. Typing and ty

[documented] ty is "currently in beta", uses `0.0.x` versioning, and "does not yet have a stable API; breaking changes, including changes to diagnostics, may occur between any two versions". `README.md:24`, `README.md:72-78` in the ty clone. Release 0.0.84 (2026-09-24) fixed a use-after-free during incremental checking that could execute code when analysing a crafted project, so anyone running ty on untrusted code must be on 0.0.84 or newer. `CHANGELOG.md:3-7`. Support for Python 3.14 was declared earlier (`CHANGELOG.md:3683`) and 3.15 recently (`CHANGELOG.md:355`); the default target when nothing is configured is 3.14 (`docs/python-version.md:38`).

[documented] Configuration lives in `[tool.ty]` in `pyproject.toml` or a `ty.toml`, with `ty.toml` taking precedence. `docs/configuration.md:5-30`. `python-version` is inferred from `project.requires-python` (minimum of the range), then from the environment, then the default. `docs/reference/configuration.md:433-455`. First-party roots default to the project root plus `./src` when it exists and is not itself a package. `docs/reference/configuration.md:484-497`, `docs/modules.md:5-12`. ty discovers `.venv` in the project root when `VIRTUAL_ENV` is unset. `docs/modules.md:55-60`. Installation as a dev dependency is `uv add --dev ty` then `uv run ty`. `docs/installation.md:13-37`.

[verified] `mise exec -- uv run --with ty ty check src` in the worktree printed `ty 0.0.84 (8dd9a7f7f 2026-09-24)` and `All checks passed!` with no configuration. `mise exec -- uv run --with mypy mypy --version` printed `mypy 2.3.1 (compiled: yes)`. pyright was not tried because it needs Node [untested].

[verified] mise can pin ty: `mise registry` lists `ty` with the `aqua:astral-sh/ty` and `github:astral-sh/ty` backends and `mise ls-remote ty` ends at `0.0.84`. Pinning through the `dev` group with `uv.lock` is the alternative the ty docs describe, and it keeps ty on the same `uv run` path as ruff and pytest.

[inference] Recommendation for the coordinator: adopt ty 0.0.84 as the type checker, installed in the `dev` group (so `uv.lock` pins it and `uv run ty check` is the task), with the check reported in CI but not blocking until the phase 1 checkpoint retro confirms it is stable across a few pin moves. The reasons: it shares ruff's configuration style and Astral's release cadence, it is the only checker whose upstream ships in the same repository as the linter already adopted, it reads `requires-python` and the `src/` layout without configuration, and the helper package is small enough that a diagnostic change between `0.0.x` releases costs minutes. The reasons against, for the decision issue: the explicit beta status and no-stable-API statement, and the fact that mypy 2.3.1 and pyright are mature. If the coordinator prefers a stable tool, mypy through the `dev` group with `strict = true` under `[tool.mypy]` is the fallback [untested here]. Whichever is chosen, the rule is `uv run <checker>` through a mise task, never a global install.

## Draft rules for .claude/rules/python.md

Each line names the version it was written for. Codex finalises the wording.

- Python 3.14: target `>=3.14` only. Do not write `from __future__ import annotations` and do not quote forward references. Read annotations only through `annotationlib.get_annotations`.
- Python 3.14: enter asyncio through `asyncio.run` or `asyncio.Runner`. Never call `asyncio.get_event_loop`, `get_event_loop_policy`, or `set_event_loop_policy`; pass `loop_factory=` if a custom loop is needed.
- Python 3.14: use `asyncio.TaskGroup` and `asyncio.timeout` for concurrency and deadlines. Keep every `create_task` result. Use `inspect.iscoroutinefunction`, not `asyncio.iscoroutinefunction`.
- Python 3.14: spawn processes with `asyncio.create_subprocess_exec` or `subprocess.run` with an argv list and an explicit `check=`. Never `os.system`, `os.popen`, `os.spawn*`, `shell=True`, or the removed `pipes` module.
- Python 3.14: never `return`, `break`, or `continue` from inside a `finally` block.
- Python 3.14: use `datetime.now(tz=UTC)` and `uuid.uuid7()` for timestamps and run identifiers. Never `datetime.utcnow()`.
- Python 3.14: use `pathlib.Path` everywhere, including `Path.copy`, `Path.move`, and `Path.info`; use `copy.replace` for modified copies of dataclasses.
- Python 3.14: write `int | str` unions and compare union types with `==`. Do not import `typing.Text`, `typing.ByteString`, `typing.io`, or `typing.re`.
- Python 3.14: do not use `logging.warn`, `codecs.open`, `shutil.rmtree(onerror=)`, camelCase `threading` aliases, or any name listed under pending removal; tests run with warnings as errors so they surface.
- Python 3.14: use the default GIL build, not `3.14t`. Do not set `PYTHON_JIT`. Do not rely on `multiprocessing` `fork` semantics; Linux now defaults to `forkserver`.
- Python 3.14: when capturing a child Python's output as evidence, set `NO_COLOR=1` and `PYTHONUNBUFFERED=1` in its environment.
- uv 0.12: run every Python tool as `uv run <tool>` from the repository root through a mise task; never install tools globally. Add dependencies with `uv add` (`--dev` for tools) so `uv.lock` moves with `pyproject.toml`; never edit `uv.lock` by hand.
- uv 0.12: experiment scripts under `experiments/<NN-slug>/` are plain files run as `uv run experiments/<NN-slug>/<script>.py` with `PYTHONSAFEPATH=1`. They never carry a `# /// script` block, never import sibling files, and put shared code in `src/agent_orchestration_poc/`.
- uv 0.12: development tools go in the `dev` dependency group, never in `[project.optional-dependencies]`. Run `uv lock --check` before committing a `pyproject.toml` change; CI installs with `uv sync --locked`.
- uv 0.12: the interpreter is the mise-pinned Python exported through `UV_PYTHON`; do not set `python-preference` in `pyproject.toml`, and request `3.14+gil` if a free-threaded build ever shadows it.
- ruff 0.16.9: run `uv run ruff check` and `uv run ruff format --check` before every commit; hooks apply `ruff check --fix` (safe fixes only) before `ruff format`.
- ruff 0.16.9: do not set `target-version`; `requires-python` supplies it. Pass `--target-version py314` only when running with an explicit `--config` file.
- ruff 0.16.9: write `except A, B:` without parentheses; the formatter emits that form on py314.
- ruff 0.16.9: re-export from `__init__.py` through `__all__`; never add an `F401` ignore for it.
- ruff 0.16.9: use `logging`, not `print`, in `src/`; `print` is allowed only under `experiments/`.
- ruff 0.16.9: write google-style docstrings on public modules, classes, and functions in `src/`; tests and experiment scripts are exempt.
- ruff 0.16.9: never call blocking `subprocess`, `open`, or `time.sleep` inside `async def`; the `ASYNC2xx` rules are defaults.
- ruff 0.16.9: suppress with `# noqa: CODE` or `# ruff: ignore[CODE]` and a reason; blanket `noqa` and blanket `type: ignore` fail `PGH004` and `PGH003`.
- ruff 0.16.9: do not enable `preview`, `COM`, `Q`, `E501`, `D203`, or `D213`; do not select `ANN101`, `ANN102`, `TRY200`, `UP027`, `UP038`, `PGH001`, `PGH002`, `PLR1701`, `S320`, `S410`, `PT004`, `PT005`, `E999`, or the `TCH` prefix.
- pytest 9.1: put tests under `tests/` with no `__init__.py`; tests run in `importlib` mode, so test modules never import each other and shared helpers live in the package or in `conftest.py` fixtures.
- pytest 9.1: register every marker in `pyproject.toml`; `strict_markers` and `strict_config` are on, so a misspelled marker or an unknown key fails collection.
- pytest 9.1: mark tests that spawn a process or open a socket with `integration` or `socket`; they skip by default and run with `--run-integration`.
- pytest 9.1: warnings are errors; add a commented `ignore:` entry to `filterwarnings` rather than silencing a warning in code.
- pytest 9.1: use `@pytest.fixture` without parentheses and yield fixtures for process and socket lifecycle; terminate, wait with a timeout, then kill in teardown. Create Unix socket paths under a short directory, not `tmp_path`, because macOS rejects `sun_path` over about 104 bytes.
- pytest 9.1: do not write `async def` tests until the async plugin is in the dev group. Do not add `pythonpath` or `sys.path` tweaks. Do not pass `--strict-markers` or `--strict-config` through `addopts`, and do not set `strict = true`.
- ty 0.0.84 (if adopted): run `uv run ty check` before every commit; configure under `[tool.ty]` only, never a `ty.toml`; suppress with `# ty: ignore[rule]` and a reason.
