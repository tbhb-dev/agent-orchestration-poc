# Strict typing check, 2026-09-26

Issue #77 removes pyrefly's test and experiment sub-configs and ruff's matching `ANN` exemptions. Existing tests now annotate their parameters and returns. The strict configuration still uses pyrefly 1.3.1 and ruff 0.16.9.

## Before the change

The first baseline attempt ran `mise run check:pyrefly` before editing. It stopped before type checking because uv tried to write its user cache outside the worktree sandbox:

```text
[check:pyrefly] $ uv run pyrefly check
error: Failed to initialize cache at `/Users/tony/.cache/uv`
  Caused by: failed to open file `/Users/tony/.cache/uv/sdists-v9/.git`: Operation not permitted (os error 1)
[check:pyrefly] ERROR task failed
```

That output is an environment failure, not evidence of a typing failure. The old config's two sub-configs and `ANN` exemptions are visible in the parent revision of `pyproject.toml`.

## After the change

With disposable mise, Go, and uv caches under `/private/tmp/aop-testing-gates`, `mise run check` completed successfully. Its type and Python test lines were:

```text
[check:pyrefly]  INFO 0 diagnostics
[check:pytest] ======================== 16 passed, 1 skipped in 1.10s =========================
[check:ruff] All checks passed!
```

The check also completed the Go, import, formatting, and repository guard tasks. This proves the revised tree passes the configured strict checks locally. It does not supply a passing baseline run under the old exemptions.
