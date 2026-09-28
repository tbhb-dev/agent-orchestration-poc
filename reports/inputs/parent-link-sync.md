# Parent link synchronization evidence

## Inputs and source contract

[Verified] The approved assignments, parents, and edges were read with `parse_tables` in `src/agent_orchestration_poc/core/work_model_backfill.py` at repository commit `0d04ae5`. The parser returned 191 assignment rows, 22 parent rows, and 387 edge rows. Filtering native parent rows through the parser's accepted action and execution contract yields 18 links, comprising 16 epic links and 2 initiative links. The older counts in issue #202 do not match this committed table. The exact source and committed file digests are in `reports/inputs/work-model-tables/manifest.md`.

[Documented] [GitHub REST issue dependency endpoints](https://docs.github.com/en/rest/issues/issue-dependencies) define `GET` and `POST` on `/repos/tbhb-dev/agent-orchestration-poc/issues/<dependent>/dependencies/blocked_by`, with a numeric `issue_id` in the add body, and `DELETE` on the same path with the blocking issue ID appended. [GitHub REST sub-issue endpoints](https://docs.github.com/en/rest/issues/sub-issues) define `GET /issues/<number>/parent`, including a 404 for an absent parent. The shell pins `X-GitHub-Api-Version: 2022-11-28`. These docs were read on 2026-09-27 and document endpoint shape, not a successful live write.

[Schema] The installed `gh` is version 2.100.0. Its source was cloned at `/tmp/gh-cli-202-source`, tag `v2.100.0`, commit `45437bc7eeeb3359bbfddd1742f79de7652fd3e2`. `pkg/cmd/api/api.go` describes `--paginate --slurp` and rejects pagination for non-GET calls. The shell uses those flags only for REST collection reads.

## Comparison and fixture results

[Verified] `mise exec -- uv run python -m agent_orchestration_poc.shell.parent_link_sync --snapshot tests/fixtures/parent_link_sync/missing-parents.json` exited 0 and reported 18 missing, 0 extra, and no cycle. `--ongoing --snapshot tests/fixtures/parent_link_sync/approved.json` exited 0 with no delta. `--ongoing --snapshot tests/fixtures/parent_link_sync/obsolete-derived.json` exited 0 with two obsolete derived links eligible for removal. `--ongoing --snapshot tests/fixtures/parent_link_sync/cycle-160-27.json` exited 2, and both Kahn and depth-first search found the added #160 to #27 cycle. The fixture parent IDs are synthetic and are never sent to GitHub.

[Observed] The initial live default dry run, `mise exec -- uv run python -m agent_orchestration_poc.shell.parent_link_sync`, exited 0 on 2026-09-27 and reported 18 missing, 0 actual, 0 extra, and no cycle. The command made one paginated `GET repos/tbhb-dev/agent-orchestration-poc/issues?state=all&per_page=100` invocation. No parent or issue blocker endpoint was called after the complete parent-title set was absent. No `--apply` command was run against GitHub.

[Verified] `mise exec -- uv run pytest -q tests/test_parent_link_sync.py tests/test_parent_link_sync_shell.py --run-integration` exited 0 with 12 passing tests. The shell process test uses a local executable and no network. It covers an add, read-back, second no-op apply, and removal. Core tests use plain values, including changed accepted links, incomplete reads, ownership, and cycle properties.

[Verified] After the final focused core assertions, the same targeted command exited 0 with 13 passing tests. `mise run check:imports`, `mise run check:ruff`, and `mise run check:pyrefly` each exited 0. `mise run check` exited 0 with Python core line coverage 97.98%, Python core branch coverage 94.41%, and Python shell line coverage 80.28%. `mise run check:mutation` exited 0 with Go core 145 of 149 mutants killed and Python core 3,137 of 3,479 killed, a 90.17% Python score.

[Verified] `git diff --cached --numstat` measured 793 added code and test lines across the two Python modules, their two test files, and the command wrapper. This excludes the approved fixture copies and this report under the issue's size rule.

## Review corrections

[Verified] The review regression tests exclude the audit-only #3 to #1 issue pair before cross-epic projection, order a reversed parent-link replacement as DELETE then POST, and reconcile a second time with no operations. The replacement shell test uses a local simulated REST endpoint that rejects an intermediate two-node cycle; it performs no live GitHub writes. The dry-run ownership test rejects a planning report as a managed ledger.

[Verified] After these corrections, `mise exec -- uv run pytest -q tests/test_parent_link_sync.py tests/test_parent_link_sync_shell.py --run-integration` exited 0 with 19 passing tests. `mise run check` exited 0 with Python core line coverage 98.03%, branch coverage 94.62%, and shell line coverage 81.03%. The first aggregate attempt found an untyped test helper; the helper was typed and the complete aggregate then passed.

[Verified] The synchronization policy now lives in pure core functions: operation planning checks cycles, apply eligibility, and unowned extras; it removes obsolete owned edges before additions. Ownership changes are computed from read-back-completed operations. A dry-run report keeps its observed managed set and records `applied: false`; `read_managed` accepts only a report with `applied: true` as a later ownership receipt. The REST shell collects values and executes the planned operations.

[Verified] `mise run check:mutation` exited 0 after the first review regression tests: Go core killed 145 of 149 mutants, and Python core killed 3,182 of 3,530 mutants (90.14%). The first mutation run scored 89.75%; the added plain-value tests for apply eligibility, cycles, and ownership transitions raised it above the 90% floor.

[Verified] The later command-level regression reproduced `JSONDecodeError: Extra data` when it saved a nonempty successful apply's stdout and parsed it as one managed ledger. Per-operation read-back receipts now go to stderr, while stdout contains one JSON report. The full `main()` test saves that report, passes it to a second apply with `--managed` and observes no operations, then removes the issue dependency and verifies an owned DELETE. Its REST and identity functions are simulated; it performs no live GitHub writes. `mise run check` exited 0 after this fix, with Python core lines 98.03%, branches 94.62%, and shell lines 81.06%.

[Verified] The final `mise run check:mutation` exited 0: Go core killed 145 of 149 mutants, and Python core killed 3,206 of 3,530 mutants (90.82%).

[Verified] The PR size contract uses scc-classified added and deleted code lines, not `git diff --numstat`. `mise run scc:version` reported scc 4.1.0. All five included code paths are new against the `origin/main` merge base, so `mise exec 'go:github.com/boyter/scc/v4@4.1.0' -- scc --by-file --format json src/agent_orchestration_poc/core/parent_link_sync.py src/agent_orchestration_poc/shell/parent_link_sync.py tests/test_parent_link_sync.py tests/test_parent_link_sync_shell.py scripts/sync-parent-links` counts the changed code directly: 207 core, 243 shell, 223 core tests, 235 shell tests, and 2 script code units, totaling 910. This exceeds the 800-unit limit, so the PR still requests a size exception. The 999 count in the earlier PR body measured raw added lines and was not the contract's count.

[Verified] `mise exec -- gitleaks dir --redact --no-banner --log-level error reports/inputs/parent-link-sync.md tests/fixtures/parent_link_sync` exited 0. The commit hook also scanned the staged code and fixtures without a finding. A sandboxed `ps -eo pid,etime,args` read was denied with `operation not permitted`, so process-list inspection was unavailable. The mutation task's own session and log supplied completion evidence.

## Contract and pending live acceptance

[Verified] The default command is a dry run. `--ongoing` derives from current native issue blocked-by reads and parent memberships, while preserving the explicit native parent rows and excluding audit-only dispositions. The step 13 operator confirmation remains a separate milestone predicate and is not a native blocked-by link. An epic link states completion order. An initiative link states roadmap order. Dispatch evaluates issue blockers separately.

[Untested] Coordinator-only `--ongoing --apply` requires a fresh complete read, a second unchanged read, the `tbhb-agent` identity, an acyclic desired graph, and no unowned extra link. Each add or remove is followed by a fresh blocker read and emits a local operation ID. A live apply and its idempotence remain untested because #200 step 11 has not created the native parents or links.

[Untested] The after-step-11 live comparison, final counts, and command exits remain pending on #200. The documentation page for the work model also remains pending because the approved allowed paths for #202 do not include a site page. This pull request is a partial delivery and issue #202 stays open.
