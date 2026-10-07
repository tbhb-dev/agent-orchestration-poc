# Gate change evidence for issue 88

Recorded 2026-10-07 UTC in `tooling/88-gate-weakenings` with Codex CLI 0.157.1 and `gpt-6-sol` at high. The comparison base is `d32e4f4052323d10d25a354a5e0e9a13fc4c4d44`. The pinned tools include Python 3.14.6, uv 0.12.10, Ruff 0.16.9, mutmut 3.8, and jscpd 5.3.2.

## Source basis

Documented: The local gate implementation and check contracts were read at base commit `d32e4f4052323d10d25a354a5e0e9a13fc4c4d44`, including `mise.toml`, `.github/workflows/check.yml`, the supported lint configurations, `research/gates/testing/versions.md`, and `research/gates/quality-gates/versions.md`. CPython source was read at `c63aec69bd59c55314c06c23f4c22c03de76fe45` for tokenized Python comment handling. GitHub's [pull request event documentation](https://docs.github.com/en/actions/reference/events-that-trigger-workflows#pull_request) describes `edited`, and its [context documentation](https://docs.github.com/en/actions/reference/contexts-reference#runner-context) describes `runner.temp`.

## Local checks

Verified: `mise run check:pytest -- tests/test_gate_changes.py --run-integration` exited 0 with 76 passed cases after the latest test additions. The case table and passing and failing PR bodies are in `tests/fixtures/gate_changes/`.

Verified: `mise run check:gate-changes -- --base d32e4f4052323d10d25a354a5e0e9a13fc4c4d44 --head 91e5c52 --body-file tests/fixtures/gate_changes/pr-body-pass.txt` exited 0 and reported the workflow and `mise.toml` selector IDs. The same command with `pr-body-fail.txt` exited 1, reporting a missing reason for `mise.toml` and a partial reason for the workflow.

Verified: `mise run check:gate-changes -- --base d32e4f4052323d10d25a354a5e0e9a13fc4c4d44 --head 78d2943 --body-file tests/fixtures/gate_changes/pr-body-pass.txt` exited 0 with those two IDs. The same command with `pr-body-fail.txt` exited 1 with the expected missing and partial diagnostics after the final code commit.

Observed: An earlier `mise run check:coverage` could not write `~/Library/Application Support/quarto/logs/jupyter-kernel.log` under the sandbox. A full `mise run check` retry exited 0 without a change to the sandbox. It reported Python core lines 97.25%, branches 93.86%, shell lines 74.20%, Go core statements 96.43%, branches 94.74%, and shell statements 74.58%. The final post-change runs are recorded below.

Observed: The post-change `mise run check` exited 1 because Quarto 1.10.18 again attempted to write that log outside the writable roots during `tests/test_analysis_notebooks.py::test_render_synthetic_notebook`. The coverage run recorded 787 passes and one failure. No sandbox escape or system setting was changed. The PR CI run provides the complete check result in its runner environment.

Observed: An intermediate `mise run check:mutation` exited 1 with Go 145/149 killed (97.32%) and Python 9123/10175 killed (89.66%). The Python score was 35 kills below its 90% floor. Focused tests were added for the surviving gate comparison branches before the final run.

Verified: The final `mise run check:mutation` exited 0 with Go 145/149 killed (97.32%) and Python 9175/10176 killed (90.16%). The Python run had one timed out mutant, which is counted in the exported total.

## Open PR audit

Observed: A single REST list of open PRs and fetched head refs was compared against the base on 2026-10-07 UTC. The sanitized IDs and diagnostic labels are in `tests/fixtures/gate_changes/open-pr-audit.txt`. Nine open PR heads were inspected. Three had missing gate reasons and six had no findings or justification diagnostics. No PR body or credential was retained in the fixture.

## PR body edit trigger

Observed: PR #287 at head `61e9e0d92063af2e89b66103a06953e8a4a55456` first had a [successful `check` run](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37691180358). Removing the `gate:selector:mise.toml:file:changed` reason from its body triggered a new [failed `check` run](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37691615473). Restoring the body with both reasons triggered a [successful `check` run](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37691857251). The local missing-reason fixture exits 1 with the corresponding diagnostic. The GitHub log download was denied at `~/.cache/gh`, so the live failure cause is an inference from the controlled single-line edit and the check conclusion. The [PR mutation check](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37691180343) also concluded success.

## Review round 1

Verified: `git fetch origin && git merge origin/main` fetched the current main. The merge needed `git merge --no-ff origin/main` because this checkout has fast-forward-only merge configuration. The merge had no content conflicts and was committed as `69be445` after directing the hook cache to `/private/tmp/prek-task650`.

Verified: `mise run check:pytest -- tests/test_gate_changes.py --run-integration -q` exited 0 with 81 passed cases. New tests use the actual Biome, jscpd, and golangci configurations to probe selector weakenings, compare a disabled registry entry against the baseline, and distinguish repeated and moved Python suppressions.

Verified: `mise run check` exited 0 after review fixes. It reported Python core lines 97.24%, branches 93.92%, shell lines 74.21%, Go core statements 96.43%, branches 94.74%, and shell statements 74.58%.

Observed: The first review-round `mise run check:mutation` exited 1. Go passed at 145/149 killed (97.32%), while Python scored 9368/10511 (89.13%), below the 90% floor. Exact identity and stronger-setting assertions were added for the surviving registry and selector branches before the retry.

Observed: After those assertions, a `mise run check` retry failed strict pyrefly on an untyped empty list in a new test. `mise run check:pyrefly` exited 0 after the test fixture received an explicit `list[str]` annotation. Two later `mise run check` attempts reached 800 passed tests and failed only when Quarto attempted to write `/Users/tony/Library/Application Support/quarto/logs/jupyter-kernel.log`, outside the sandbox writable roots. A previous full check in this review round had exited 0. The sandbox settings and host files were not changed.

## Review round 2

Verified: `git fetch origin && git merge origin/main` fetched current main, then the fast-forward-only setting required `git merge --no-ff origin/main`. The merge had no content conflicts and was committed as `bb86f1d` with `PREK_HOME=/private/tmp/prek-issue-88` so the hooks could use a writable cache.

Verified: Before the fixes, `mise exec -- uv run pytest -q tests/test_gate_changes.py -k 'golangci_selector_findings_have_exact_identity or existing_unclassified_gate_controls_fail_closed'` exited 1 with both tests failing. The actual configuration probes produced no finding for Biome `error` to `warn` and golangci `generated: lax`; the removed `nestif` finding ID contained a space. After the fixes and additional registry integration coverage, `mise exec -- uv run pytest -q tests/test_gate_changes.py --run-integration` exited 0 with 94 passed cases.

Observed: The first `mise run check` attempt reached 803 passing coverage tests and passed Python core line 97.33%, core branch 93.88%, shell line 74.23%, Go core statement 96.43%, and Go shell statement 74.58% floors. It exited 1 when the `gobco -branch internal/core/relay` subprocess returned 1 without stderr in the wrapper. A direct `mise exec -- gobco -branch internal/core/relay` retry exited 0 with 34/38 branches. The mutation task was running concurrently with the failed aggregate attempt.

Observed: `mise run check:mutation` exited 1 with Go 145/149 killed (97.32%) and Python 9591/10662 killed (89.95%). Exact Biome severity transition tests were added for the surviving branches before the next Python mutation run.

Verified: `mise run check:mutation:python` then exited 0 with 9627/10662 killed (90.29%). The earlier full mutation task's Go result remained 145/149 (97.32%).

Observed: A full `mise run check` retry after formatting exited 1 in the unrelated notebook integration test because Quarto tried to write `/Users/tony/Library/Application Support/quarto/logs/jupyter-kernel.log` outside this sandbox. It ran 807 passing tests and one failing notebook test before stopping coverage. No sandbox escape or host setting was changed. The focused gate suite passed all 94 tests, including its shell integration case.
