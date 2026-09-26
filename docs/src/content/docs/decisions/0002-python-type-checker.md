---
title: "0002: Python type checker is strict pyrefly"
description: Strict pyrefly gates Python type checking for issue 61.
---

## Status

Accepted 2026-09-26 for issue #61 as an operator requirement. This supersedes the same-day decision in PR #23 to run ty as a non-gating check (research/gates/pyrefly/notes.md).

## Context

The Python scaffold previously ran ty 0.0.84 outside the `check` aggregate. Its beta diagnostic API was the reason to defer a gate. The operator required strict pyrefly instead, and pyrefly 1.3.1 passed a trial on the helper package and tests (research/gates/python/notes.md §5, research/gates/pyrefly/notes.md §§1, 7, 9).

## Decision

Pin pyrefly 1.3.1 exactly in the `dev` group and configure `[tool.pyrefly]` in `pyproject.toml`. Set `preset = "strict"`, `min-severity = "warn"`, `python-version = "3.14"`, and `search-path = ["src"]`. Enable `unannotated-return`, `no-any-return`, `implicit-reexport`, and `unused-type-ignore` as errors. Exclude `research/imported` and `design-sketch` (research/gates/pyrefly/notes.md §§1 through 5, 8).

Run `uv run pyrefly check` with no file names through `check:pyrefly`. The prek hook also passes no file names because per-file mode ignores `project-excludes` (research/gates/pyrefly/notes.md §2).

## Consequences

`check:pyrefly` runs in the `check` aggregate and CI. Warnings fail under `min-severity = "warn"` (research/gates/pyrefly/notes.md §§3, 9).

The `tests/**` and `experiments/**` sub-configs turn off `implicit-any-parameter` and `unannotated-return` only, matching ruff's `ANN` per-file ignores. The operator may overturn this relaxation at the phase 1 checkpoint (research/gates/pyrefly/notes.md §4).

Reopen the decision if the operator changes the gate requirement, pyrefly loses timely Python support, or sustained false positives or runtime cost make the gate unsuitable. Review the annotation relaxation at the phase 1 checkpoint (research/gates/pyrefly/notes.md §§4, 7).

## Evidence

The installed CLI reports pyrefly 1.3.1. The source clone was read at `a778c3bc8cf41398408498de3d10e99a76b9fdd2`, with the 1.3.1 tag at `3e3177d0f4755b56c2d5a710d830eed89b14c2e3` (research/gates/pyrefly/versions.md).

`mise exec -- uv run pyrefly check` reported `0 diagnostics` on the helper package and tests. `mise run check` also completed with `check:pyrefly` in the aggregate (research/gates/pyrefly/notes.md §9).

A throwaway source probe raised the expected `unannotated-return`, `implicit-any-parameter`, `no-any-return`, and `unused-ignore` diagnostics. A second probe raised `missing-override-decorator` and a `deprecated` warning, and the check exited 1. A test probe confirmed that unannotated parameters and returns were allowed under `tests/**` but raised errors under `src/` (research/gates/pyrefly/notes.md §§3 through 4).
