# Operator command verification

## Scope and versions

**Verified.** This branch started from `cb7fdd7811f09a8ae5864ff40b9bb01ba34889d9` on 2026-09-28. The local interpreter is Python 3.14.6, uv is 0.12.10, and `scc` is 4.1.0, as read through mise. The workflow pins `actions/checkout` at `3d3c42e5aac5ba805825da76410c181273ba90b1` and `jdx/mise-action` at `c2a87611a18de5b3828c5652fe268e992400cb5c`. The repository's existing `issue-form.yml` carries the same pins. The REST client sends `X-GitHub-Api-Version: 2026-03-10`.

**Documented.** GitHub's [issue comment REST reference](https://docs.github.com/en/rest/issues/comments) describes the shared issue and pull request timeline endpoint and its `per_page` parameter. The [labels reference](https://docs.github.com/en/rest/issues/labels) defines additive issue labels, and the [reactions reference](https://docs.github.com/en/rest/reactions/reactions) defines issue comment reactions. These pages were read on 2026-09-28. The exact repository version is the base commit above.

## Local fixtures

**Verified.** `tests/fixtures/operator-commands/issue.json` and `pr.json` exercise all eight forms with the same numbered ask. The pure tests cover invalid grammar, source identity, edited delivery, open state, labels, missing and ambiguous asks, explicit retirement of an older ask, hostile literal text, and line selection. The review follow-up adds negative probes for numbered prose outside the ask sections, two simultaneous active asks, and pure preflight authorization by event action, actor, item type and number, and comment ID. The loopback REST tests exercise comment pagination, additive label requests, both reaction types, fixture gates, and repeated delivery. No fixture text is passed to a shell command.

**Verified.** `mise exec -- uv run pytest tests/test_operator_commands.py tests/test_operator_command_shell.py --run-integration -q` passed 52 tests after the reaction replay fix. `mise run check:imports` passed both core and shell contracts. `mise run check:ruff`, `mise run check:pyrefly`, `mise run check:workflow-forms`, `mise run check:vale`, and `mise run docs:build` passed after local corrections. The final Python integration coverage run passed 600 tests with core lines 96.95 percent, core branches 93.03 percent, and shell lines 76.44 percent. An earlier full coverage gate passed with Go core statements 96.43 percent and branches 94.74 percent. The final `mise run check:mutation:python` passed at 90.25 percent, with 7,350 of 8,144 mutants killed. The Go core mutation gate passed at 97.32 percent before the replay fix, which changed no Go code.

**Observed.** The final `mise run check` completed every earlier subcheck, but its Go branch coverage subprocess produced no output for more than eight minutes after starting `scripts/check-coverage.py`. A serial `mise run -j 1 check` reached the same point and was interrupted after six minutes without output. The separate `mise run check:coverage` completed successfully before these attempts. The sandbox denied `ps -eo pid,etime,args` with `operation not permitted`, so the stalled child process could not be inspected here. CI must supply the final aggregate readback.

**Observed.** `mise run build` passed. `mise run docs:check-links` failed when Playwright Chromium could not register its macOS rendezvous port under the sandbox. The validator then listed seven links in existing pages, including `/workflow/` and `/design/github-event-monitor/`. It did not list a link in the new guide. `mise run docs:build` had passed earlier without link validation.

**Verified.** On the review follow-up, `mise exec -- uv run pytest tests/test_operator_commands.py tests/test_operator_command_shell.py --run-integration -q` passed 55 tests. `mise run fmt` and standalone `mise run check:go` passed. The serial `mise run -j 1 check` passed the regular and integration Python suites (603 tests in the latter); the coverage script printed Python core lines 97.02 percent, core branches 93.17 percent, shell lines 76.48 percent, Go core statements 96.43 percent, and Go shell statements 74.58 percent. **Observed.** The aggregate again stopped producing output in its `gobco` Go branch coverage child. It was interrupted after about five minutes in that subprocess, so the full local aggregate has no completion result. An earlier parallel aggregate attempt failed when the Go formatter briefly could not open a path in the generated Mermaid checker dependency tree; standalone `check:go` passed immediately afterward. Hosted CI remains the aggregate readback.

**Verified.** The review follow-up `mise run check:mutation` passed: Go core scored 97.32 percent (145 of 149 killed), and Python core scored 90.10 percent (7,396 of 8,209 killed).

## Fixture-only gate and pending live evidence

**Verified.** Operator decision OP-31 authorized two disposable items for #254. [Issue #262](https://github.com/tbhb-dev/agent-orchestration-poc/issues/262) has `needs-operator` and `operator/review`. Draft [pull request #263](https://github.com/tbhb-dev/agent-orchestration-poc/pull/263) has the same labels and comes from `fixture/254-operator-commands` at commit `56abc6d`, which adds only the empty `reports/inputs/operator-commands/fixture-pr-marker`. Each item has one active `Operator ask` comment with two approval lines, two options, a recommendation, `Unblocks: none`, and `Deadline: none`. The type-specific gate records issue `262` and pull request `263`.

**Verified.** A pure `preflight` probe with the configured IDs accepts issue `262` and pull request `263`, and rejects the swapped item types and item `999` for each. The 55 targeted parser and loopback REST tests passed. `mise run check:imports`, `mise run check:ruff`, and `mise run check:workflow-forms` passed. **Observed.** `mise run check` passed its earlier subchecks and printed coverage above the Python and Go statement floors, then failed because `gobco -branch` exited 1 for `internal/core/layout` in `scripts/check-coverage.py`. The sandbox denied `ps -eo pid,etime,args`, so the local child process could not be inspected.

**Verified.** `mise run check:mutation` passed after the fixture-ID change: Go core scored 97.32 percent (145 of 149 killed), and Python core scored 90.10 percent (7,396 of 8,209 killed). `mise run fmt` made no additional changes.

**Observed.** A separate `mise run check:coverage` again printed Python and Go statement coverage above their floors but produced no further output from `gobco -branch` for more than two minutes; it was interrupted. `mise run docs:build` passed with 56 pages.

**Untested.** There is no live `tbhb` author association readback, workflow run link, or live label and reaction readback yet. The operator will post positive fixture comments after merge through a separate ask. Broad activation is outside this pull request.

**Untested.** The coordinator's external digest script and its fixture result are not present in this repository. The [event contract](/guides/operator-commands/#coordinator-digest-handoff) specifies the targeted REST reads, delayed-label pending record, and comment-ID deduplication. The coordinator must attach its external handoff and verification before this issue can close.

## Safety boundary

**Verified.** The workflow handles only `issue_comment` `created`, uses `GITHUB_TOKEN` with `contents: read` and `issues: write`, and checks out the workflow's own repository revision rather than pull request code. The pure core validates event eligibility and the fixture marker and number before the shell makes any REST call. It changes only `operator/replied` and the source comment reaction. It never removes an attention label or executes an operator decision.

## Change size

**Verified.** `scc` 4.1.0 counted 673 Python code lines and 25 YAML code lines in the five new code and workflow files. The handwritten guide has 18 nonblank prose lines. The size contract therefore counts 716 added units, excluding the two JSON fixture payloads and this evidence file. There are no deleted lines.
