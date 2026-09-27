# Testing gate failure probe, 2026-09-26

The local run used Go 1.27.1, rapid 1.3.0, gremlins 0.6.0, Python 3.14.6, Hypothesis 6.168.1, mutmut 3.8.0, and pytest-cov 7.0.0. The run used the pinned mise tools and a disposable cache under `/private/tmp/aop-testing-gates` because this worktree cannot write the user-level mise and uv caches.

## Passing baseline

`mise run check:mutation` completed successfully with the full test assertions. Gremlins printed `Killed: 14, Lived: 0, Not covered: 0`, `Test efficacy: 100.00%`, and `Mutator coverage: 100.00%`. Pytest-cov reported 100.00% line coverage for 10 Python core statements. Mutmut reported `Python core mutation score: 92.31% (24 killed of 26)`.

## Deliberately weakened test

I temporarily changed `test_valid_examples` to assert only the valid examples, while still calling the validator on invalid examples. I also removed the assertion from `test_empty_token_is_invalid` while leaving the call. This kept all validator lines covered and let invalid-input mutants survive. I ran `mise run check:mutation:python`, captured its output, and restored `tests/test_subject.py` from a byte-for-byte copy. `cmp` confirmed the restored file matched that copy.

The captured failing output was:

```text
TOTAL                                             10      0   100%
Required test coverage of 90% reached. Total coverage: 100.00%
16 passed, 1 skipped in 0.32s
Saved CI/CD stats to mutants/mutmut-cicd-stats.json
Python core mutation score: 65.38% (17 killed of 26)
[check:mutation:python] ERROR task failed
```

The exported stats contained `"killed": 17`, `"survived": 9`, `"total": 26`, `"no_tests": 0`, `"suspicious": 0`, and `"timeout": 0`. The task exited with status 1. This probe shows the mutation floor detects weakened assertions even while line coverage remains 100 percent.

## Timed-out mutant check

A repeat Go run with short coverage startup time classified six mutants as timed out but still printed 100.00% for both gremlins scores. The final task sets two workers, a timeout coefficient of 200, a one-second rapid shrink limit, and no rapid fail files. It checks the gremlins JSON output for timed-out mutants. The next run killed all 14 mutants with zero timeouts.

I copied the valid JSON output, changed one mutant status to `TIMED OUT`, and ran `scripts/check-gremlins-output.py` through the pinned Python. It printed `Go core mutation run incomplete: 1 timed out of 14` and exited 1. I restored the valid JSON output afterward. This probe confirms that a timed-out mutant cannot pass on gremlins' score alone.

## Review fixes

Verified against the installed mutmut 3.8.0 source at `.venv/lib/python3.14/site-packages/mutmut/__main__.py` (`save_cicd_stats`) and `stats.py` (`Stat`), matching the `boxed/mutmut` clone at tag 3.8.0, commit `14a7230049a5c8abd90c2bb0f7438e30da6471f5`: `export-cicd-stats` writes `killed`, `survived`, `total`, `no_tests`, `skipped`, `suspicious`, `timeout`, `check_was_interrupted_by_user`, and `segfault`. The internal `total` also includes `not_checked` and `caught_by_type_check`, which the export omits. The score decision now rejects unknown keys and runs where the five scored outcomes do not sum to `total`; plain-value tests cover one killed and 25 segfaults, a high-score crash, an interruption, a skip, an unknown key, and an unaccounted mutant.

Observed after the review fixes with the pinned tools and disposable caches: `mise run check` passed with 27 Python tests passed and one integration test skipped. `mise run check:mutation` passed: gremlins killed all 14 Go mutants with 100.00% efficacy and 100.00% mutant coverage, while pytest-cov measured 100.00% Python core line coverage and mutmut killed 51 of 54 mutants for 94.44%. The exported Python stats had three survivors and zero crashes, interruptions, or skips. An unpaired surrogate example and a Hypothesis property over arbitrary text passed. Source inspection of `internal/core/subject/subject.go` found no equivalent Go gap: invalid UTF-8 decodes to a rune outside the allowed ASCII characters and returns an error.

## Second review fixes

The new plain-value gremlins evaluation tests first failed during collection with `ModuleNotFoundError` for `agent_orchestration_poc.core.gremlins_output`. After moving status extraction and the completion decision into that core module, all four cases passed: one killed mutant, one timed-out mutant, no mutants, and a mixed run. The first full mutation run killed all 14 Go mutants but then failed because the Go task launched the checker with bare `python`, which could not import the installed package. Changing the task to `uv run python` made the shell script use the pinned project environment.

Observed after both fixes with the pinned tools and disposable caches: `mise run check` passed with 31 Python tests passed and one integration test skipped. `mise run check:mutation` passed: gremlins killed all 14 Go mutants with zero timeouts and both scores at 100.00%; its output checker reported 14 classified mutants. Pytest-cov measured 100.00% Python core line coverage, and mutmut killed 74 of 83 mutants for an 89.16% score. The Python conventions example now matches the `experiments/**` Ruff exemptions in `pyproject.toml`.
