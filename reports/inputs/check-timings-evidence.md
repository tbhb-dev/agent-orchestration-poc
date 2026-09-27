# Check timings capture evidence

## Scope and sources

This branch implements the local capture and SQLite schema slice of #109. The full issue now exceeds its 800-unit limit after counting task and hook integration, REST and webhook ingestion, fixtures, notebook analysis, and prose. The dependent slice is GitHub Actions REST and captured-delivery ingestion against this schema, followed by the benchmark notebook after #107 supplies runnable gates. No collector or notebook result is claimed here.

The assigned implementer is Codex CLI 0.157.1 using `gpt-6-sol` at high effort.

The pinned runtime is mise 2026.8.6, prek 0.5.1, Python 3.14.6, and SQLite 3.53.1. The versioned mise source read was `jdx/mise@71212d424cd07189b22027f496c01ccad76e8b6d` under `/tmp/check-timings-mise-source`, including `docs/hooks.md` and task execution source. The prek source read was `j178/prek@10a896eb63d60dd1175cc7b10ff0798e7070e56f` under `/tmp/check-timings-prek-source`, including builtin hook definitions and `run_hook`. The [Python 3.14 sqlite3 reference](https://docs.python.org/3.14/library/sqlite3.html) and [monotonic clock reference](https://docs.python.org/3.14/library/time.html#time.monotonic_ns) were read for parameterized inserts, transactions, and duration measurement. The Python documentation page served patch 3.14.7 when read, while the tested interpreter was 3.14.6.

## Schema and records

The intended store is the main clone's ignored `.local-cache/check-timings/timings.sqlite3`. `local_checks` has `id INTEGER PRIMARY KEY`, `name TEXT NOT NULL`, `started_at TEXT NOT NULL`, `duration_ns INTEGER NOT NULL`, `exit_status INTEGER NOT NULL`, `commit_sha TEXT`, `branch TEXT`, `origin TEXT NOT NULL`, `actor TEXT`, and `host TEXT NOT NULL`. The source is `src/agent_orchestration_poc/shell/check_timings.py`. `duration_ns` is sampled with `time.monotonic_ns()` around the child process. Git metadata is read after completion and can reflect a ref that changed during a long running check.

These are synthetic schema examples, not records read from the blocked store:

```json
{"name":"task:check:actions","started_at":"2026-09-27T03:00:00+00:00","duration_ns":12000000,"exit_status":0,"commit_sha":null,"branch":null,"origin":"local","actor":null,"host":"synthetic-host"}
{"name":"task:check:actions","started_at":"2026-09-27T03:01:00+00:00","duration_ns":13000000,"exit_status":7,"commit_sha":null,"branch":null,"origin":"local","actor":null,"host":"synthetic-host"}
{"name":"hook:trailing-whitespace","started_at":"2026-09-27T03:02:00+00:00","duration_ns":5000000,"exit_status":1,"commit_sha":null,"branch":null,"origin":"local","actor":null,"host":"synthetic-host"}
```

Observed: a read-only query found 41 local task rows. One passing row had `name=task:check:ruff`, `exit_status=0`, and `duration_ns=139945417`. One failing row had `name=task:check:coverage`, `exit_status=1`, and `duration_ns=19523202708`. These selected fields omit host, actor, and repository metadata. They show partial persistence, while the current sandbox cannot append reliably.

## Verification and limits

Verified: `git rev-parse --path-format=absolute --git-common-dir` resolved to the main clone's `.git` directory, and `git check-ignore -v .local-cache/check-timings/timings.sqlite3` matched `.gitignore:16:.local-cache/`. The core rejects a nonabsolute or non-main common directory. The test fixture writes two rows to a temporary SQLite store and checks the allowed columns. Integration tests compare wrapped and unwrapped stdout, stderr, and status for exit codes 0 and 7, test SIGINT forwarding, and test a missing store. Passing and failing outputs and statuses are retained in `tests/fixtures/check_timings/`.

Observed: `mise run vale:sync`, `mise run fmt`, `mise run check:shell`, `mise run check:tombi`, `mise run check:ruff`, `mise run check:imports`, `mise run check:pyrefly`, `mise run check`, `mise run build`, and `mise run docs:build` exited 0. The full check measured Python core lines 100.00%, core branches 95.95%, shell lines 76.84%, Go core statements and branches 100.00%, and Go shell statements 72.12%. `mise exec -- uv run pytest tests/test_check_timings.py --run-integration` exited 0 with 35 passing tests. `mise run check:timing-inventory` exited 1 with 49 configured tasks, 24 hooks, and 45 missing records. A direct append to the intended path raised `sqlite3.OperationalError: attempt to write a readonly database`. The wrapper keeps that failure out of the check status and streams.

Observed: `mise exec -- prek run trailing-whitespace --files AGENTS.md` exited 2 before running the hook because prek could not open its cache log outside this sandbox. No hook pass or failure is claimed from that command. `ps` was also denied by the sandbox during a long coverage run. No cache location, sandbox rule, or host setting was changed.

Observed: `mise run docs:check-links` exited 1 when sandbox restrictions prevented Playwright Chromium from launching. `mise run docs:build` succeeded before the link check. No browser or sandbox setting was changed.

Observed: the final `mise run check` exited 0. `git commit -m 'tooling(perf): capture local check durations'` exited 1 before any hook ran because prek could not open its cache log outside the sandbox. No hook was bypassed, no commit was created, and no branch was pushed.

Verified: `mise run check:mutation` exited 0 after the test module's shell probes were isolated from mutmut's core-only package copy. The Go core killed 89 of 89 classified mutants with 100.00% efficacy and coverage. The Python core killed 548 of 587 mutants for a 93.36% score.

Observed: a 30-pair no-op probe on the macOS arm64 host using `true` and `scripts/record-check.sh ad-hoc -- true` with the store unavailable had median added wall time 84.37 ms and nearest-rank p95 added wall time 98.52 ms in one run. A later run under changing host load measured 105.70 ms median and 135.16 ms p95. These are diagnostic probes without committed row data or the #104 notebook protocol, and neither establishes the required p95 acceptance bound for a successful append.

Untested: reliable main-clone append, execution of every hook, GitHub Actions records and request counts, late completion and rerun reconciliation, and a fully verified benchmark. Issue #107 remained open when this report was written, and its `notebooks:render` and `notebooks:verify` tasks were absent from this branch.

## Review corrections

The [failed check job at 240213a](https://github.com/tbhb/agent-orchestration-poc/actions/runs/36292166025/job/108544217067) was read through the GitHub Actions REST job-log endpoint. It reported 1 failed and 151 passed tests because the store-path test asserted that a normal clone's store parent could not equal its current directory. The test now creates an ignored main clone and a linked worktree in a temporary directory and verifies that both resolve the same main-clone store.

The new configuration test initially failed with 21 missing wrappers when supplied synthetic records for every configured task and hook. The Vale child-command probe initially received no filenames. After wrapping the remaining 20 hooks and `check:review-identity`, and invoking the Vale script directly, `mise exec -- uv run pytest tests/test_check_timings.py --run-integration -k 'configured_tasks_and_hooks or vale_task_forwards or store_path_is_ignored'` exited 0 with 3 passing tests. The existing wrapper tests cover exit status and streams; the new wrappers retain each hook's filename and stage settings.

Observed: `mise run fmt` initially exited 1 on a new unnecessary list literal; after simplifying it, the task exited 0. `mise run check:go` exited 0. An aggregate `mise run check` stopped once in `check:review-identity`, which passed alone on retry, and once in `check:go` after a `node_modules` path disappeared during the parallel scan; `check:go` passed alone. A third aggregate run passed its visible task checks and Python integration tests, then made no progress beyond Go coverage package output for more than eight minutes and was interrupted with exit 130. No conclusion about the full aggregate is claimed from that run.

Observed: the first `mise run check:mutation` exited 1 because mutmut copied the configuration test without the repository's `mise.toml`. Marking the configuration and process probes as integration tests kept them in `check:coverage` and out of mutmut's core-only copy. The second `mise run check:mutation` exited 0: Go classified and killed 89 of 89 mutants, and Python killed 585 of 627 for 93.30%. `mise run build`, `mise run docs:build`, and `mise exec -- prek run shellcheck --files scripts/record-check.sh` each exited 0. The local sandbox still prevents reliable append to the main clone outside this worktree, so the hook probe validates execution and status, not a persisted record.
