# Coordinator preflight evidence for issues #70 through #73

Verified on 2026-09-26 in worktree `tooling/70-73-coordinator-preflight` at base `be4bc24` with mise pins from `mise.toml`, Python 3.14.6, Vale 3.22.0, and GitHub CLI 2.100.0. The local runs used writable uv, Go, and golangci-lint caches under `/private/tmp` because the shared caches were outside the sandbox.

## Review workflow fixtures

The committed `tests/fixtures/coordinator_preflight/workflows.json` contains an outdated branch with an old `check.yml` and a missing `docs.yml`, and a current branch that intentionally edits `check.yml` after the merge base has reached main. The pure decision function produced:

```text
workflow outdated: FAIL: .github/workflows/check.yml, .github/workflows/docs.yml
workflow current: PASS: current
```

Observed live output from `mise run review:preflight -- 80`:

```text
PR #80: workflows include current origin/main revisions
```

## Documentation brief

The committed `docs/briefs/documentation-brief-template.md`, `docs/briefs/documentation-brief-sample.md`, and `docs/src/content/docs/workflow/documentation-brief-sample.md` passed `mise run check:vale --` on those files plus the two updated workflow pages:

```text
✔ 0 errors, 0 warnings and 0 suggestions in 5 files.
```

Before the wording corrections, the same command failed with four `ai-tells` errors, including `BareNames` on “Name the”, `NounString` on “use sentence case headings”, `AnthropomorphicCognition` on “The sample brief asks for”, and `NamedAdjective` on “the named check concludes”. The passing output is from the corrected committed prose.

## Named check fixtures and live outcomes

The committed `tests/fixtures/coordinator_preflight/checks.json` produced these outcomes from the pure function with expected head `abc`:

```text
check missing: wait
check queued: wait
check running: wait
check successful: success
check failed: fail
check cancelled: fail
check changed-head: changed-head
```

Observed live success with `mise run pr:wait-check -- 80 check 0`:

```text
PR #80: check succeeded on 7bb09bfe7ed6e60fa097854342e3fd6343609487
```

Observed live failure with `mise run pr:wait-check -- 80 nonexistent-check 0`, exit 1:

```text
PR #80: nonexistent-check did not succeed on 7bb09bfe7ed6e60fa097854342e3fd6343609487 within 0s
```

The zero-second live success above records the original implementation. After review, the deadline starts before the first GitHub call, so a zero-second wait now expires without querying GitHub. The core regression cases cover a queued check with no start time alongside an older success, tied start times, and a later completed run. The shell integration test used a temporary `gh` executable that sleeps two seconds; before the fix, a one-second wait took 4.69 seconds and failed its time assertion. After the fix, `mise exec -- uv run pytest tests/test_coordinator_preflight.py tests/test_coordinator_preflight_shell.py --run-integration -q` passed all 22 tests in 1.17 seconds, including that test.

## Closure fixtures and live audit

The committed `tests/fixtures/coordinator_preflight/closures.json` produced these outcomes. The legacy decision case uses issue #14's recorded decision-record closure sentence:

```text
closure unmerged PR: REVIEW
closure merged PR: PASS
closure reopened issue: PASS
closure recorded non-code closure: PASS
closure legacy decision record: PASS
closure legacy decision record: PASS
```

Observed live output from `mise run checkpoint:closure-audit` after the legacy decision case was included:

```text
Audited 18 closed work-item issues; 0 need review
```

The audit reads closed issues and merged PRs through standard `gh` list commands. It matches `Refs: #<issue>` trailers and GitHub closing references, and never changes issue state. It fails if either list reaches its 10,000-item query limit.

The review fix moved rollup normalization and work-item selection, count, and flag decisions into pure core functions. Value-based tests cover the normalized queued record and a mix of work-item, non-work-item, and recorded non-code closures.

## Repository gates and limits

Verified `mise run check` exit 0 with 16 Python tests passed, one existing integration test skipped, two import contracts kept, zero Vale alerts across 89 Markdown files, 7 Mermaid blocks valid, no gitleaks findings in 30 commits, and Go vet, lint, build, and race tests passing. `mise run build` also exited 0. `mise run fmt` made no changes outside this work item.

After the review fixes, `mise run fmt` exited 0 and `mise run check` exited 0 with 22 Python tests passed, two integration tests skipped, both import contracts kept, zero Vale alerts, and no secret findings. The stalled CLI integration test was also run explicitly with `--run-integration` and passed. The local Go build printed a stat-cache write warning for `/Users/tony/go/pkg/mod` outside this sandbox; the aggregate still exited 0.

After merging `origin/main` at `ee61cb0`, the tooling inventory conflict in `docs/src/content/docs/workflow/tooling.md` retained this branch's coordinator module entries and main's two mutation-script entries. Main's strict test annotations required an explicit return type on the fixture loader. With `UV_CACHE_DIR`, `GOCACHE`, and `GOLANGCI_LINT_CACHE` under `/private/tmp`, `mise run check` exited 0: 52 Python tests passed, two integration tests skipped, both import contracts kept, zero Vale alerts, and no secret findings. `mise run check:mutation` exited 0: Go killed 14 of 14 covered mutants with no timeouts, and Python reached 100 percent core line coverage and killed 200 of 240 mutants for an 83.33 percent score. Go still printed a stat-cache write warning for `/Users/tony/go/pkg/mod`, but the aggregate succeeded.

Observed `mise run docs:check-links` rendered the sample page but exited 1 in the local sandbox after Chromium failed with `MachPortRendezvousServer: Permission denied (1100)`. The link validator reported three links under `index.md`, `project/history.md`, and `workflow/tooling.md`. The GitHub `docs` job will be the render and link gate for this PR.
