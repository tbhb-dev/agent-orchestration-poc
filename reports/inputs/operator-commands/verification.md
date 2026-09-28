# Operator command verification

## Scope and versions

**Verified.** This branch started from `cb7fdd7811f09a8ae5864ff40b9bb01ba34889d9` on 2026-09-28. The local interpreter is Python 3.14.6, uv is 0.12.10, and `scc` is 4.1.0, as read through mise. The workflow pins `actions/checkout` at `3d3c42e5aac5ba805825da76410c181273ba90b1` and `jdx/mise-action` at `c2a87611a18de5b3828c5652fe268e992400cb5c`. The repository's existing `issue-form.yml` carries the same pins. The REST client sends `X-GitHub-Api-Version: 2026-03-10`.

**Documented.** GitHub's [issue comment REST reference](https://docs.github.com/en/rest/issues/comments) describes the shared issue and pull request timeline endpoint and its `per_page` parameter. The [labels reference](https://docs.github.com/en/rest/issues/labels) defines additive issue labels, and the [reactions reference](https://docs.github.com/en/rest/reactions/reactions) defines issue comment reactions. These pages were read on 2026-09-28. The exact repository version is the base commit above.

## Local fixtures

**Verified.** `tests/fixtures/operator-commands/issue.json` and `pr.json` exercise all eight forms with the same numbered ask. The pure tests cover invalid grammar, source identity, edited delivery, open state, labels, missing and ambiguous asks, latest ask order, hostile literal text, and line selection. The loopback REST tests exercise comment pagination, additive label requests, both reaction types, fixture gates, and repeated delivery. No fixture text is passed to a shell command.

**Verified.** `mise exec -- uv run pytest tests/test_operator_commands.py tests/test_operator_command_shell.py --run-integration -q` passed 52 tests after the reaction replay fix. `mise run check:imports` passed both core and shell contracts. `mise run check:ruff`, `mise run check:pyrefly`, `mise run check:workflow-forms`, `mise run check:vale`, and `mise run docs:build` passed after local corrections. A final Python integration coverage run passed 600 tests with core lines 96.95 percent, core branches 93.03 percent, and shell lines 76.44 percent. An earlier full coverage gate passed with Go core statements 96.43 percent and branches 94.74 percent. The final `mise run check:mutation:python` passed at 90.23 percent, with 7,354 of 8,150 mutants killed. The Go core mutation gate passed at 97.32 percent before the replay fix, which changed no Go code.

**Observed.** The final `mise run check` completed every earlier subcheck, but its Go branch coverage subprocess produced no output for more than eight minutes after starting `scripts/check-coverage.py`. A serial `mise run -j 1 check` reached the same point and was interrupted after six minutes without output. The separate `mise run check:coverage` completed successfully before these attempts. The sandbox denied `ps -eo pid,etime,args` with `operation not permitted`, so the stalled child process could not be inspected here. CI must supply the final aggregate readback.

**Observed.** `mise run build` passed. `mise run docs:check-links` failed when Playwright Chromium could not register its macOS rendezvous port under the sandbox. The validator then listed seven links in existing pages, including `/workflow/` and `/design/github-event-monitor/`. It did not list a link in the new guide. `mise run docs:build` had passed earlier without link validation.

## Fixture-only gate and pending live evidence

**Untested.** The issue and pull request fixture numbers are currently `0` and `0`, which match no GitHub item. Issue #254 does not provide disposable IDs, and this dispatch forbids creating issues. The workflow therefore remains inert until two existing reviewed fixture numbers are supplied. There is no live `tbhb` author association readback, workflow run link, or live label and reaction readback yet. Broad activation is outside this pull request.

**Untested.** The coordinator's external digest script and its fixture result are not present in this repository. The [event contract](/guides/operator-commands/#coordinator-digest-handoff) specifies the targeted REST reads, delayed-label pending record, and comment-ID deduplication. The coordinator must attach its external handoff and verification before this issue can close.

## Safety boundary

**Verified.** The workflow handles only `issue_comment` `created`, uses `GITHUB_TOKEN` with `contents: read` and `issues: write`, and checks out the workflow's own repository revision rather than pull request code. The shell validates the fixture item marker and number before any REST call. It changes only `operator/replied` and the source comment reaction. It never removes an attention label or executes an operator decision.

## Change size

**Verified.** `scc` 4.1.0 counted 670 Python code lines and 25 YAML code lines in the five new code and workflow files. The handwritten guide has 18 nonblank prose lines. The size contract therefore counts 713 added units, excluding the two JSON fixture payloads and this evidence file. There are no deleted lines.
