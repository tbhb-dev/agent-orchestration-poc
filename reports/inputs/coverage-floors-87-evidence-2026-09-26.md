# Coverage floors for issue 87

Recorded 2026-09-26 in worktree `tooling/87-coverage-floors` with Codex CLI 0.157.1, `gpt-6-sol` at high, Go 1.27.1, Python 3.14.6, coverage.py 7.16.1, pytest-cov 7.0.0, gremlins 0.6.0, mutmut 3.8.0, and gobco 1.3.4. The first measurements precede the new floors and tests. The failed probes below used temporary test changes that were restored.

## First measurements

| Gate | First measurement | Issue floor | Evidence |
| --- | --- | --- | --- |
| Go core statements | 9/9, 100% | 95% | `go test -coverprofile=/tmp/coverage-87-go.out` and `go tool cover -func` |
| Go core branches | 6/6, 100% | 90% | gobco v1.3.4 `-branch` on `internal/core/subject` |
| Go shell statements | 1/11, 9.09% | 70% | Same Go profile, with `cmd/agentctl` and `cmd/agentd` at zero |
| Python core lines | 30/30, 100% | 95% | `pytest --cov-branch --cov-report=json` |
| Python core branches | 16/16, 100% | 90% | Same coverage.py 7.16.1 JSON report |
| Python shell lines | No executable shell code | 70% when code exists | `src/agent_orchestration_poc/shell/__init__.py` was empty |
| Go mutation efficacy | 14/14, 100% | 90% | `mise run check:mutation:go` gremlins output |
| Go mutant coverage | 14/14, 100% | 90% | Same gremlins output, zero uncovered |
| Python mutation score | 74/83, 89.16% | 90% | `mutants/mutmut-cicd-stats.json` and `mutmut results` |

Observed: The first Go shell measurement could not meet 70% with the existing placeholder command tests because neither command package had a test. The version package supplied the sole covered shell statement. A shared shell writer and a pure core version-command decision now allow ordinary shell tests to cover both outcomes while keeping I/O outside the core. The resulting shell score is 75%, so the issue floor remains 70%.

Observed: The first Python mutation score missed 90% by one mutant. Tests for a single-mutant total and rejected uppercase `X` and `Y` killed the three behavior-changing survivors. No floor was lowered.

Observed: PR #80 merged into `main` while this branch was in progress. Rebasing onto `main` also brought in the new bus and coordinator preflight packages. The first measurement against that updated base, before tests for those packages, was Go core statements 100% against 95%, Go core branches 100% against 90%, Go shell statements 61.82% against 70%, Python core lines 100% against 95%, Python core branches 93.75% against 90%, and Python shell lines 0/108 against 70%. Go mutation efficacy and coverage were each 89/89, 100% against 90%, and Python mutation was 390/427, 91.33% against 90%. The shell coverage deficits came from the newly added command and subprocess paths. Integration tests for those paths brought both shell groups above their issue floors.

## Failing gate probes

| Temporary test change | Captured gate output | Result |
| --- | --- | --- |
| Skipped `tests/test_coverage_floors.py` | Python core lines 51.35% below 95%, branches 53.33% below 90% | `check:coverage` exited 1, `/tmp/coverage-87-fail-python-core.log` |
| Skipped `internal/core/command/version_test.go` | Go core statements 75% below 95%, branches 75% below 90% | `check:coverage` exited 1, `/tmp/coverage-87-fail-go-core.log` |
| Skipped `internal/cli/run_test.go` before adding writer-error cases | Go shell statements 12.50% below 70% | `check:coverage` exited 1, `/tmp/coverage-87-fail-go-shell.log` |
| Added a temporary Python shell function and complete test, then skipped the test | Python shell lines fell from 100% to 25% below 70% | `check:coverage` exited 1, `/tmp/coverage-87-fail-python-shell.log` |

Verified: All temporary test edits and the Python shell probe files were restored or removed. Before the updated base, `check:coverage` reported Python core lines 100%, branches 93.33%, no Python shell code, Go core statements 100%, Go shell statements 80%, and Go core branches 100%.

## Mutant review

| Surviving mutant at first measurement | Equivalent? | Reason and resolution |
| --- | --- | --- |
| `mutation_score.x_evaluate__mutmut_12` | No | Changed the minimum total from one to two. A one-mutant complete run now has a test. |
| `subject.x_valid__mutmut_13` | No | Changed the lower character bound so uppercase `Y` passed. A rejected `a.Y` case kills it. |
| `subject.x_valid__mutmut_24` | No | Added uppercase `X` to the allowed punctuation string. A rejected `a.X` case kills it. |
| `gremlins_output.x_evaluate__mutmut_2` | Yes | Changed only the first `typing.cast` type argument. Cast returns its value unchanged at runtime. |
| `gremlins_output.x_evaluate__mutmut_6` | Yes | Changed only the first cast's string type spelling. Cast returns its value unchanged. |
| `gremlins_output.x_evaluate__mutmut_7` | Yes | Changed only the first cast's string type casing. Cast returns its value unchanged. |
| `gremlins_output.x_evaluate__mutmut_13` | Yes | Changed only the second cast's type argument. Cast returns its value unchanged. |
| `gremlins_output.x_evaluate__mutmut_17` | Yes | Changed only the second cast's string type spelling. Cast returns its value unchanged. |
| `gremlins_output.x_evaluate__mutmut_18` | Yes | Changed only the second cast's string type casing. Cast returns its value unchanged. |

The new coverage decision initially had 18 additional, non-equivalent survivors. All were killed by tests of aggregation across files, exact floor boundaries, one-count totals, and empty core or shell groups. The individual mutant identifiers and their test obligations follow.

| Mutants | Equivalent? | Missing behavior exercised by added test |
| --- | --- | --- |
| `coverage_floors.x_evaluate_python__mutmut_13`, `_17`, `_21`, `_25`, `_32`, `_36` | No | These replaced accumulation with assignment. `test_python_aggregates_files` requires every core and shell file to contribute. |
| `coverage_floors.x_evaluate_python__mutmut_59`, `_67`, `_75` | No | These changed the multiplier from 100 to 101. `test_python_rejects_just_below_each_floor` tests ratios just below each floor. |
| `coverage_floors.x_evaluate_python__mutmut_65`, `_73` | No | These changed an empty-group check from zero to one. Tests cover one uncovered branch and one uncovered shell statement. |
| `coverage_floors.x_evaluate_go__mutmut_36`, `_37`, `_38`, `_39` | No | These changed zero or one core and shell total checks. `test_go_rejects_empty_and_just_below` covers empty and one-statement groups. |
| `coverage_floors.x_evaluate_go__mutmut_46` | No | This changed the shell multiplier from 100 to 101. A 69/99 shell case stays below 70%. |
| `coverage_floors.x_evaluate_gobco__mutmut_31` | No | This required two outcomes instead of one. A complete 1/1 report must pass. |
| `coverage_floors.x_evaluate_gobco__mutmut_33` | No | This changed the multiplier from 100 to 101. An 89/99 report stays below 90%. |

Verified: The final Go run killed 20/20 mutants, with 100% efficacy and 100% mutant coverage. The final Python run killed 264/270 mutants, scoring 97.78%. The only six survivors are the equivalent `gremlins_output` cast mutations listed above. No mutmut exemption was added because the score passes and the source type hints remain useful.

The updated `main` base added 31 coordinator preflight survivors at its first mutation run. Tests killed these 28 behavior-changing mutants. The remaining three are equivalent and listed below.

| Mutants | Equivalent? | Reason and resolution |
| --- | --- | --- |
| `coordinator_preflight.x_outdated_workflows__mutmut_8` | No | Read the wrong head key. A test now requires no warning when head has the current main workflow revision. |
| `coordinator_preflight.x_check_outcome__mutmut_9` through `_14`, `_34`, `_35` | No | Altered accepted terminal statuses or the direct success outcome. Tests now cover `SUCCESS`, `FAILURE`, and `ERROR` without a conclusion. |
| `coordinator_preflight.x_normalize_checks__mutmut_15` through `_17`, `_23` through `_25`, `_30` through `_32`, `_39` through `_42` | No | Changed fallback keys for status rollup values. A test now requires `context`, `state`, and `createdAt` fallback data. |
| `coordinator_preflight.x_needs_closure_review__mutmut_12`, `_21`, `_34` through `_37` | No | Changed the decision label condition, case-insensitive decision note, or non-code explanation check. Tests now cover those cases. |
| `coordinator_preflight.x_check_outcome__mutmut_16` | Yes | Replacing `len(matches) > 1` with `>= 1` enters a conflict check for a single result, whose one outcome can never conflict. |
| `coordinator_preflight.x_needs_closure_review__mutmut_23`, `_24` | Yes | Only changed the regex pattern's letter case while `re.IGNORECASE` still applies. |

Verified: After the updated-base tests, Go killed 89/89 mutants, with 100% efficacy and coverage. Python killed 418/427 mutants, scoring 97.89%. The nine survivors are the six `gremlins_output` cast mutations and three coordinator preflight equivalents in these tables.

Verified: The final `mise run check:coverage` on the updated base passed with Go core statements 100% against 95%, Go core branches 100% against 90%, Go shell statements 72.12% against 70%, Python core lines 100% against 95%, Python core branches 93.75% against 90%, and Python shell lines 75.93% against 70%.

## Sandbox and source limits

Observed: Initial Go and uv runs failed to write their default caches under the user home. Local runs used `GOCACHE=/tmp/coverage-87-go-cache` and `UV_CACHE_DIR=/tmp/coverage-87-uv-cache`. Mise could not install the new gobco pin under its home data directory, returning `Operation not permitted`. A binary built from the v1.3.4 source clone in `/tmp/coverage-87-gobco` was used for local `mise run check:coverage` with `MISE_DISABLE_TOOLS` and `PATH` set. A second `mise install go:github.com/rillig/gobco@1.3.4` trial succeeded with its data, cache, and Go module paths under `/tmp`. CI's normal mise installation remains to be verified.

Observed: The `srvgit/gocove` source clone returned `Repository not found`, so that tool was not trialed. The Go branch comparison, source paths, commits, and gobco limitations are in `research/gates/testing/coverage-branches-87.md`.
