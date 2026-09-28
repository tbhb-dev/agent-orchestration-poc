# Host harness fixture validation

**Verified.** `PYTHONPATH=experiments/06-host-runtime-lifecycle PYTHONSAFEPATH=1 mise exec -- uv run pytest -q experiments/06-host-runtime-lifecycle/fixture` exited 0 with 52 passing tests. The [focused log](fixture-tests.log) includes four loopback responder exchanges that received the committed tool and final bytes and then HTTP 409.

**Verified.** `mise run check` exited 0. The [aggregate log](fixture-check.log) records all repository gates, including Vale, Ruff, Pyrefly, imports, tests, and coverage. The final A/B home-path edit occurred while the aggregate was running, then the focused tests, `mise run check:ruff`, `mise run check:pyrefly`, and a targeted Vale invocation exited 0 on that edit. Hosted CI must check the pushed head.

**Verified.** `mise run check:mutation` exited 0. Go core mutation score was 97.32 percent, with 145 killed and 4 lived mutants. Python core score was 90.19 percent, with 4890 killed out of 5422 mutants. The fixture core is outside the product mutation task and has table and property tests in this directory.

**Verified.** `mise run build` exited 0 for both Go binaries. `mise run vale:sync` exited 0 once in this worktree. `mise run fmt` exited 0, and the final diff was inspected.

**Untested.** No harness launch, privileged audit, controller process, provider route, or native conversation resume ran in this delivery. Codex interactive and headless plus Claude interactive and headless remain subject to the reviewed later host procedure.
