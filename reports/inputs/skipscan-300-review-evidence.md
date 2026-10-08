# Skipscan review evidence for #300

The round 4 regressions for #300 reproduced nine failures on reviewed commit `6466a3f` with `mise run check:pytest -- tests/test_skipscan.py -q`: comment and ordinary-string triple markers, a marker 20 lines before executable code, three lines mixing code patterns with prose, and three mixed-clause negations. The uncertain quote-state and repeated-word regressions were added while fixing those cases.

At the current worktree state for #300, `mise run check:pytest -- tests/test_skipscan.py -q` passed 151 scanner tests. `mise run check` passed, including 1,021 standard tests, 1,146 coverage tests, Python core line coverage 97.67%, and Python core branch coverage 94.36%. `mise run check:mutation` passed: Go core 97.32% (145 killed of 149) and Python core 90.01% (11,763 killed of 13,068). `mise run build` passed.

The runnable workflow and CI probe for #300 are in PR #315. The [earlier CI probe](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37755429626/job/113238668457) rejected an untracked indicator and passed after an issue reference was placed beside it.

In the stacked #315 worktree before the main merge, 150 targeted scanner tests, `mise run check`, `mise run docs:build`, and `mise run build` passed. `mise run check:mutation` passed with Go core 97.32% and Python core 90.08% (11,746 killed of 13,039). Local `mise run docs:check-links` failed twice because Chromium could not register its macOS rendezvous server in this sandbox; the Linux CI docs job passed on `d57f412`.

GitHub [runs comment workflows from the default branch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#issue_comment). The discussion-comment workflow checks out that branch and [creates a check run on the PR head](https://docs.github.com/en/rest/checks/runs#create-a-check-run). Live comment edits and deletions remain untested until #315 lands on the default branch; local tests cover event routing and head check publication through a loopback API.

## Main merge and pass/fail policy

PR #315 merged `origin/main` as `d245549`, retaining #312's round-4 scanner fixes and the #315 event routing. The 160 focused scanner and event tests passed after the merge; the core-policy tests then failed at collection because `head_result` was absent, and 163 focused scanner, event, and shell tests passed after the policy moved into the pure core.

`mise run fmt` and `mise run build` passed. `mise run check` stopped at `check:secrets`: a redacted gitleaks report identified rule `private-key` in `tests/test_skipscan.py` at main commit `dcfec5c1d132dbdc6d1fb4c396e797f4cbbfb3d2` (lines 110-128). No secret value was printed or committed in this report. This historical finding is outside #315's new code and persists when the already merged commit is in history; the full aggregate check did not complete.

`mise run check:mutation` passed after the policy change: Go core 97.32% (145 killed of 149), Python core 90.04% (11,813 killed of 13,119). `mise run check:gate-changes` passed after the PR body was updated with the two suppression IDs changed by the main merge.

## PR 315 review round 1

For #300, merge `9205554` brings `origin/main` at `90ae436` into the branch with normal hooks. The post-merge baseline `mise run check` passed 1,046 standard tests and 1,173 coverage tests before these review fixes.

Verified for #300: the new regressions first failed because the workflow lacked a trusted continuation and because a 251-commit PR returned success when the API supplied only 250 messages. The commit-count policy now rejects incomplete collections before reporting success. The workflow regression checks that review events enter the read-only workflow and its completion triggers the trusted default-branch workflow.

Documented for #300: GitHub gives fork review events [read-only tokens](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_review) and permits a [workflow_run continuation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run) to obtain write permission. The continuation runs default-branch code without upstream artifacts or caches. It queries open PRs and matches the event's head repository and branch, including when the event's PR array is empty. The [PR commits endpoint](https://docs.github.com/en/rest/pulls/pulls#list-commits-on-a-pull-request) has a 250-commit ceiling.

Verified for #300: the focused suite passed 180 tests with `mise run check:pytest -- tests/test_skipscan.py tests/test_skipscan_events.py tests/test_skipscan_shell.py --run-integration -q`. The socket-marked test independently makes each artifact surface untracked and checks its source and line. Paginated surfaces place that finding on page two. A fork workflow payload changes the loopback check on the current head from failure to success after the reference is restored. This verifies scanner behavior, not GitHub event delivery or token issuance.

Live fork review/comment delivery remains untested under #300 until the trusted workflow exists on the default branch. The coordinator must retain that verification item: create or edit an untracked fork review comment, record the current-head failure, add an adjacent issue reference, and record the current-head success. This worker does not merge or change repository permissions.

Verified for #300: the explicit gate comparison against `origin/main` reproduced four missing and four orphan suppression IDs. Replacing the stale IDs with the eight reported selector and suppression IDs made the local body comparison pass. Historical CI claims above apply only to their named heads.

Verified for #300 after the review fixes: `mise run check` passed 1,057 standard tests and 1,190 coverage tests. The default suite gated off 133 integration cases, which the coverage run included. Python core lines reached 97.65%, core branches 94.38%, and shell lines 77.35%. `mise run check:mutation` passed with Go 97.32% and Python 90.10% (11,848 killed of 13,150). `mise run build`, `mise run fmt`, and `mise run docs:build` passed.

Coordinator-run evidence for #300: after the worker's `mise run docs:check-links` failed because Chromium's macOS `bootstrap_check_in` returned `Permission denied (1100)`, the coordinator ran the same command outside the sandbox on the review-fix working tree. The coordinator reported exit 0; `/private/tmp/claude-501/links315.log` records 62 pages built and completion in 17.51 seconds. This result unblocked the worker's commit and publication steps.
