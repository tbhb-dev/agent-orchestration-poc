# Versions and clones for the pyrefly research

Recorded on 2026-09-26 for issue #61. Tool versions come from commands run through mise inside the `tooling-61-pyrefly` worktree. The clone SHA is what `git rev-parse HEAD` reported after cloning; the tag SHA is `git rev-parse 1.3.1^{commit}`.

## Tool versions

| Tool | Version | How observed | Note |
| --- | --- | --- | --- |
| mise | 2026.8.6 | `mise --version` | mise reports 2026.9.14 available; not updated here |
| uv | 0.12.10 | `mise exec -- uv --version` | `mise.toml` pin |
| Python (worktree `.venv`) | 3.14.6 | `mise exec -- uv run python --version`; `sys.version_info[:3]` is `(3, 14, 6)`, `Py_GIL_DISABLED` is `0` | The mise-pinned interpreter, selected by `UV_PYTHON_PREFERENCE=only-system`; this is what pyrefly queries |
| pyrefly | 1.3.1 | `mise exec -- uv run pyrefly --version` | `dev` group, exact pin `pyrefly==1.3.1` in `pyproject.toml` and `uv.lock`; PyPI release 2026-09-14 |
| pyrefly (npm) | 0.0.1-security | `mise exec -- npm view pyrefly version` | Placeholder package; npm is not the route |
| ty | 0.0.84 | previously in the `dev` group | Removed with `uv remove --dev ty` |
| tombi | 1.5.0 | `mise.toml` pin | Formatted the `[tool.pyrefly]` block |
| guard-markdown | v0.3.0 | `guard-markdown --version` | Checked both documents in this directory |

## Clones

Cloned on 2026-09-26 with `git clone --filter=blob:none` under `~/Code/github.com/<owner>/<repo>`.

| Path | HEAD SHA | Commit date | Tag or nearest tag | Checkout | What was read |
| --- | --- | --- | --- | --- | --- |
| `~/Code/github.com/facebook/pyrefly` | `a778c3bc8cf41398408498de3d10e99a76b9fdd2` | 2026-09-26 | `1.4.0-dev.1` (nearest, `git describe` gives `1.4.0-dev.1-477-ga778c3bc8`); latest stable tag `1.3.1` at `3e3177d0f4755b56c2d5a710d830eed89b14c2e3` (2026-09-14) | Full tree at HEAD; source at the `1.3.1` tag read through `git show 1.3.1:<path>` | `website/docs/configuration.mdx` (discovery, modes, `project-includes`, `project-excludes`, `search-path`, interpreter selection, `python-version`, `min-severity`, `output-format`, `required-version`, `preset`, `errors`, inference options, ignores, `use-ignore-files`, sub-configs, globbing, exit codes), `website/docs/error-kinds.mdx` (the strict and added kinds), `website/docs/error-suppressions.mdx`, `website/docs/import-resolution.mdx` (search path, editable installs), `website/docs/installation.mdx`, `website/docs/python-features-and-peps.mdx`, `website/docs/IDE.mdx` (binary selection), `release_notes/release-notes-v1.3.0.md`, `release-notes-v1.3.1.md`, `release-notes-v1.4.0-dev.1.md`, `release_notes/release_notes_archived.md` (v0.52.0, PEP 750), `version.bzl`, `crates/pyrefly_config/src/base.rs@1.3.1` (the preset definitions), `crates/pyrefly_config/src/error_kind.rs@1.3.1` (`default_severity`), `crates/pyrefly_bundled/third_party/typeshed/stdlib/VERSIONS` |

## Docs drift between the tag and HEAD

`git diff --stat 1.3.1 HEAD -- website/docs/{configuration,error-kinds,error-suppressions,import-resolution,python-features-and-peps}.mdx` touches only `configuration.mdx` (68 lines: `[tool.basedpyright]` migration, language-server config selection, typeshed `VERSIONS` filtering, build-system `default_config`) and `error-kinds.mdx` (95 lines: `incompatible-overload-argument` and `uninitialized-instance-variable` added, `incompatible-overload-residual` moved). None of the sections the notes cite changed, so the HEAD line numbers describe the 1.3.1 behaviour; the two new error kinds do not exist in 1.3.1 and are not configured.
