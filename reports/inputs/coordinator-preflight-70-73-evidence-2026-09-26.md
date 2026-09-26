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

## Repository gates and limits

Verified `mise run check` exit 0 with 16 Python tests passed, one existing integration test skipped, two import contracts kept, zero Vale alerts across 89 Markdown files, 7 Mermaid blocks valid, no gitleaks findings in 30 commits, and Go vet, lint, build, and race tests passing. `mise run build` also exited 0. `mise run fmt` made no changes outside this work item.

Observed `mise run docs:check-links` rendered the sample page but exited 1 in the local sandbox after Chromium failed with `MachPortRendezvousServer: Permission denied (1100)`. The link validator reported three links under `index.md`, `project/history.md`, and `workflow/tooling.md`. The GitHub `docs` job will be the render and link gate for this PR.
