# Versions and clones for the Python research gate

Recorded on 2026-09-26 for issue #5. Tool versions come from commands run through mise inside the `research/5-python-gate` worktree. Clone SHAs are what `git rev-parse HEAD` reported after cloning or checking out; the cpython clone is pinned to the `v3.14.6` tag rather than `main` (which was already 3.15 beta) so the documentation matches the installed interpreter.

## Tool versions

| Tool | Version | How observed | Note |
| --- | --- | --- | --- |
| mise | 2026.8.6 | `mise --version` | mise reports 2026.9.14 available; not updated here |
| uv | 0.12.10 | `mise exec -- uv --version` | `uv = "latest"` in `mise.toml`; `mise ls-remote uv` lists 0.12.19 as newest |
| Python (mise) | 3.14.6 | `mise which python` and `uv python list` | Installed at `~/.local/share/mise/installs/python/3.14`; resolved through the user's global `idiomatic_version_file_enable_tools` setting reading `.python-version`, not through `mise.toml` |
| Python (worktree `.venv`) | 3.14.3 | `mise exec -- uv run python --version` | uv-managed CPython at `~/.local/share/uv/python/cpython-3.14-macos-aarch64-none`; chosen because uv's `python-preference` defaults to `managed`; GIL build (`Py_GIL_DISABLED` is 0) |
| Python (free-threaded, unused) | 3.14.3+freethreaded | `uv python list` | Installed by uv on this machine; not used by the project |
| Python (newest available) | 3.14.7 | `mise ls-remote python` | Not installed; noted for the pin decision |
| ruff | 0.16.9 | `mise exec -- uv run ruff --version` | `dev` group, exact version in `uv.lock` |
| pytest | 9.1.1 | `mise exec -- uv run --with pytest python -c "import pytest; print(pytest.__version__)"` | Not in `pyproject.toml`; the version uv resolves today |
| ty | 0.0.84 | `mise exec -- uv run --with ty ty --version` | Not in `pyproject.toml`; `mise ls-remote ty` also ends at 0.0.84 |
| mypy | 2.3.1 | `mise exec -- uv run --with mypy mypy --version` | Not in `pyproject.toml`; observed only as the fallback candidate |
| guard-markdown | v0.3.0 | `guard-markdown --version` | Checked both documents in this directory |

## Clones

All under `~/Code/github.com/<owner>/<repo>`, cloned on 2026-09-26 with `git clone --filter=blob:none`. The mise clone predates this gate and is listed in `experiments/00-system-assessment/dependency-clones.md` at the same SHA.

| Path | HEAD SHA | Commit date | Tag or nearest tag | Checkout | What was read |
| --- | --- | --- | --- | --- | --- |
| `~/Code/github.com/python/cpython` | `c63aec69bd59c55314c06c23f4c22c03de76fe45` | 2026-06-10 | `v3.14.6` (exact) | Sparse, non-cone: `Doc/whatsnew/3.14.rst`, `Doc/whatsnew/3.13.rst`, `Doc/howto/free-threading-python.rst`, `Doc/deprecations/pending-removal-in-3.15.rst`, `pending-removal-in-3.16.rst`, `pending-removal-in-3.17.rst`, `pending-removal-in-future.rst`, `Doc/using/cmdline.rst`, a few `Doc/library/*.rst` | Whatsnew for 3.14 and 3.13, the free-threading howto, the pending-removal pages, `cmdline.rst` for `-P`, `PYTHONSAFEPATH`, `PYTHONUNBUFFERED` |
| `~/Code/github.com/astral-sh/uv` | `136ef97330781a0f5f2be6613aac4382ebbcecea` | 2026-09-26 | `0.12.19` (exact) | Full tree | `docs/concepts/projects/{init,layout,config,dependencies,sync,run,workspaces}.md`, `docs/concepts/build-backend.md`, `docs/concepts/python-versions.md`, `docs/guides/scripts.md`, `docs/guides/integration/{github,pre-commit}.md`, `crates/uv-settings/src/settings.rs`, `crates/uv-static/src/env_vars.rs` |
| `~/Code/github.com/astral-sh/ruff` | `94e46ca1ee3694bcd95b66d121f92654698c1f67` | 2026-09-26 | `0.16.9` (exact) | Full tree | `docs/{configuration,linter,formatter,preview,versioning,integrations,faq}.md`, `CHANGELOG.md`, `changelogs/0.12.x.md` through `0.15.x.md`, `crates/ruff_workspace/src/options.rs`, `crates/ruff_linter/src/codes.rs`, rule docs through `ruff rule <CODE>` |
| `~/Code/github.com/pytest-dev/pytest` | `8721173580390a9d297e5af06cac3f0b6841f425` | 2026-09-24 | `9.2.0.dev0` (nearest); latest release tag `9.1.1` | Full tree | `doc/en/reference/{customize,reference}.rst`, `doc/en/explanation/{goodpractices,pythonpath}.rst`, `doc/en/how-to/{mark,skipping,output,tmp_path,fixtures,monkeypatch,capture-warnings}.rst`, `doc/en/example/simple.rst`, `doc/en/deprecations.rst`, `doc/en/changelog.rst`, `src/_pytest/python.py` |
| `~/Code/github.com/astral-sh/ty` | `8e4aef298ab0e39007e59fb2cedcaddbebc34afc` | 2026-09-24 | `0.0.84` (exact) | Full tree | `README.md`, `CHANGELOG.md`, `docs/{installation,configuration,modules,python-version,suppression}.md`, `docs/reference/configuration.md` |
| `~/Code/github.com/jdx/mise` | `fdfa0efe7f94d9a7c06b477666cc82929959b2a7` | 2026-09-26 | `v2026.9.14` (nearest) | Full tree, pre-existing | `docs/lang/python.md`, `docs/mise-cookbook/python.md` |

## Not cloned

`pytest-asyncio`, `anyio`, `pyright`, and `mypy` were not cloned. The notes mark every claim about them `[inference]` or `[untested]`; the #6 worker records the plugin's commit when it is added.
