---
title: Temporary GitHub receiver evidence
description: Versioned sources, local commands, and bounded receiver and store results for issue 167.
---

## Sources and versions

[documented] GitHub webhook signature guidance and best practices were read from `github/docs` commit `18945a31a4f2d97beb6c5c1a7479102e23c25727` at `$TMPDIR/github-events-98/github-docs/content/webhooks/using-webhooks/validating-webhook-deliveries.md` and `best-practices-for-using-webhooks.md`. The checkout was verified with `git -C "$TMPDIR/github-events-98/github-docs" rev-parse HEAD` (exit 0). The GitHub.com REST schema version in the existing [source record](https://github.com/tbhb/agent-orchestration-poc/blob/main/research/gates/github-events/versions.md) is `2026-03-10`. GitHub documents the `sha256=` HMAC over payload bytes, constant-time comparison, event and action checks, redelivery GUID reuse, and a ten-second response deadline.

[documented] Python conventions in `docs/src/content/docs/guides/python-conventions.md` pin Python 3.14.6, uv 0.12.10, pytest 9.1.1, Ruff 0.16.9, and Pyrefly 1.3.1. `mise run monitor:test-receiver` reported CPython 3.14.6 and pytest 9.1.1. The Python source checkout read for the conventions page is `/Users/tony/Code/github.com/python/cpython` at `c63aec69bd59c55314c06c23f4c22c03de76fe45`, verified with `git -C /Users/tony/Code/github.com/python/cpython rev-parse HEAD` (exit 0).

## Signature and response fixtures

[verified] `mise run monitor:test-receiver` exited 0 with 25 tests after the final receiver changes. `tests/fixtures/receiver/pull_request.json` is synthetic and contains repository ID `1389534135`, installation ID `42`, and PR number `7`. The configured fixture installation ID is also `42`, and ID `43` is rejected. The tests compute HMAC signatures from a synthetic test phrase at run time. No live webhook payload or credential was used or recorded.

| Request case | Expected result in `tests/test_receiver.py` |
| --- | --- |
| No `X-Hub-Signature-256` | HTTP 401 and missing count 1 |
| Malformed signature | HTTP 401 and malformed count 1 |
| Wrong 64-hex digest | HTTP 401 and invalid count 1 |
| Valid signature and wrong path | HTTP 404 |
| GET on the hook path | HTTP 405 with local schema marker |
| Valid signed delivery | HTTP 202 after receipt transaction |
| Duplicate GUID and identical bytes | HTTP 202 without revision change |
| Reused GUID and changed signed bytes | HTTP 409 without revision change |

[verified] The property test varies payload bytes and the synthetic test phrase, then checks that changing one body byte invalidates the computed signature. Table cases cover missing, malformed, wrong, and valid signatures. Core classification tests cover repository rejection, installation ID rejection, unsupported event and action, and named PR and issue invalidations. No test attempts to execute payload text.

## Store and race fixtures

[verified] `tests/test_store.py` simulates a crash before receipt commit with a rolled-back SQLite transaction and verifies zero receipts after reopening. A committed receipt remains after the file is reopened. The duplicate and changed-GUID cases preserve the original revision. This tests SQLite transaction behavior in one local process and a reopened connection. Power-loss filesystem behavior remains untested.

[verified] Restart marks stored components stale and advances revision. A new database has a different store-instance UUID, and a token from the prior database returns `unavailable`. A repair with a captured generation older than an intervening invalidation cannot clear dirty, while the current generation can. Table and property tests cover the pure generation predicate.

[verified] The watch test starts a writer thread behind an event, calls `register_watch()`, then releases the writer. The token and snapshot report the same revision, and `watch_state()` reports the later change. This controlled local ordering fixture covers the read/register race. Cross-process stress remains untested.

## Commands and limits

| Command | Exit | Result |
| --- | --- | --- |
| `mise run vale:sync` | 0 | Pinned Vale styles synchronized in this worktree |
| `mise run fmt` | 0 | Formatters applied, with only issue files changed |
| `mise run monitor:test-receiver` | 0 | 25 tests passed |
| `env -u GITHUB_WEBHOOK_SECRET mise run monitor:start` | 2 | Startup refused the missing secret |
| `mise run monitor:track -- issue 167` | 0 | Revision advanced in the ignored local store |
| `mise run monitor:status` | 0 | Schema 1 and local store metadata returned, listener reported `other_process` |
| `git check-ignore -v .local-cache/github-monitor/state.sqlite3` | 0 | `.gitignore:16:.local-cache/` matched |
| `mise run check:imports` | 0 | Product Python contracts remained intact |
| `mise run check:mutation` | 0 | Go 145/149 killed, Python 454/467 killed, both above 90 percent |
| `mise run check` after the prose correction | 0 | Full aggregate passed, including coverage, docs prose, and repository guards |
| `mise run build` | 0 | `bin/agentd` and `bin/agentctl` built |
| `mise exec -- gitleaks dir --redact --no-banner scaffolding/github-monitor` | 0 | No leaks found in the scaffold |

[observed] The first `mise run check` exited 123 on six Vale findings in `docs/start.md`. The prose was corrected before the successful aggregate run. A separate `mise run check:vale` found four findings in this evidence page, which were corrected before completion.

[observed] The first code commit attempt failed because `prek.toml` called Pyrefly without the scaffold search path. The hook now runs `mise run check:pyrefly`, matching the aggregate task. The real commit passed every applicable hook without bypass.

[observed] A local Python tokenizer and AST count measured 773 nonblank Python code lines after excluding comments and docstrings. The branch changed 12 nonblank TOML code lines in `mise.toml` and `prek.toml`, for 785 measured code lines. The start note adds 20 nonblank Markdown lines. Pinned `scc` was unavailable, so this measurement uses Python tokenizer and AST.

[observed] Another process occupied `127.0.0.1:8787` during `monitor:status`, so no fixed-port receiver was started or Funnel cutover attempted. The focused HTTP integration fixture bound an ephemeral port on `127.0.0.1` only. The coordinator must free 8787 and own the local listener cutover.

[untested] No live App delivery, real secret injection, public Funnel request, host restart, or power-loss durability test was performed. Issue #179 must collect authoritative state before any component can become fresh. The real monitor replacement issues are [#189](https://github.com/tbhb/agent-orchestration-poc/issues/189) and [#190](https://github.com/tbhb/agent-orchestration-poc/issues/190).
