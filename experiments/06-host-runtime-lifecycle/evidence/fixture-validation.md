# Host harness fixture validation

**Verified.** `PYTHONPATH=experiments/06-host-runtime-lifecycle PYTHONSAFEPATH=1 mise exec -- uv run pytest -q experiments/06-host-runtime-lifecycle/fixture` exited 0 with 58 passing tests. The [focused log](fixture-tests.log) includes four loopback responder exchanges, process-query regressions, and a stand-in that identifies the listener's socket owner and waits on the launching job for its exit status.

**Verified.** `mise run check` exited 0 after the review fixes. The [aggregate log](fixture-check.log) records all repository gates, including Vale, Ruff, Pyrefly, imports, 521 tests in the coverage run, and coverage floors. Hosted CI must check the pushed head.

**Verified.** `mise run check:mutation` exited 0 after the review fixes. Go core mutation score was 97.32 percent, with 145 killed and 4 lived mutants. Python core score was 90.19 percent, with 4890 killed out of 5422 mutants. The fixture core is outside the product mutation task and has table and property tests in this directory.

**Verified.** `mise run build` exited 0 for both Go binaries. `mise run vale:sync` exited 0 once in this worktree. `mise run fmt` exited 0, and the final diff was inspected.

**Verified.** `mise exec -- gitleaks dir --redact --no-banner experiments/06-host-runtime-lifecycle` exited 0 with no leaks after the review edits. A direct `ps` check was denied by this sandbox, so denial handling was verified with a simulated subprocess result and process-creation failure. The stand-in loopback listener and job wait ran without a live harness.

**Untested.** No harness launch, privileged audit, controller process, provider route, or native conversation resume ran in this delivery. Codex interactive and headless plus Claude interactive and headless remain subject to the reviewed later host procedure.
