# Skipscan review evidence for #300

The round 4 regressions for #300 reproduced nine failures on reviewed commit `6466a3f` with `mise run check:pytest -- tests/test_skipscan.py -q`: comment and ordinary-string triple markers, a marker 20 lines before executable code, three lines mixing code patterns with prose, and three mixed-clause negations. The uncertain quote-state and repeated-word regressions were added while fixing those cases.

At the current worktree state for #300, `mise run check:pytest -- tests/test_skipscan.py -q` passed 151 scanner tests. `mise run check` passed, including 1,021 standard tests, 1,146 coverage tests, Python core line coverage 97.67%, and Python core branch coverage 94.36%. `mise run check:mutation` passed: Go core 97.32% (145 killed of 149) and Python core 90.01% (11,763 killed of 13,068). `mise run build` passed.

The runnable workflow and CI probe for #300 are in PR #315. The [earlier CI probe](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37755429626/job/113238668457) rejected an untracked indicator and passed after an issue reference was placed beside it.

In the stacked #315 worktree before the main merge, 150 targeted scanner tests, `mise run check`, `mise run docs:build`, and `mise run build` passed. `mise run check:mutation` passed with Go core 97.32% and Python core 90.08% (11,746 killed of 13,039). Local `mise run docs:check-links` failed twice because Chromium could not register its macOS rendezvous server in this sandbox; the Linux CI docs job passed on `d57f412`.

GitHub [runs comment workflows from the default branch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#issue_comment). The comment workflow checks out that branch and [creates a check run on the PR head](https://docs.github.com/en/rest/checks/runs#create-a-check-run). Live comment edits and deletions remain untested until #315 lands on the default branch; local tests cover event routing and head check publication through a loopback API.

## Main merge and pass/fail policy

PR #315 merged `origin/main` as `d245549`, retaining #312's round-4 scanner fixes and the #315 event routing. The 160 focused scanner and event tests passed after the merge; the core-policy tests then failed at collection because `head_result` was absent, and 163 focused scanner, event, and shell tests passed after the policy moved into the pure core.

`mise run fmt` and `mise run build` passed. `mise run check` stopped at `check:secrets`: a redacted gitleaks report identified rule `private-key` in `tests/test_skipscan.py` at main commit `dcfec5c1d132dbdc6d1fb4c396e797f4cbbfb3d2` (lines 110-128). No secret value was printed or committed in this report. This historical finding is outside #315's new code and persists when the already merged commit is in history; the full aggregate check did not complete.

`mise run check:mutation` passed after the policy change: Go core 97.32% (145 killed of 149), Python core 90.04% (11,813 killed of 13,119). `mise run check:gate-changes` passed after the PR body was updated with the two suppression IDs changed by the main merge.
