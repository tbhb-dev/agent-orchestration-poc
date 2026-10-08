# Skipscan review evidence for #300

The round 4 regressions for #300 reproduced nine failures on reviewed commit `6466a3f` with `mise run check:pytest -- tests/test_skipscan.py -q`: comment and ordinary-string triple markers, a marker 20 lines before executable code, three lines mixing code patterns with prose, and three mixed-clause negations. The uncertain quote-state and repeated-word regressions were added while fixing those cases.

At the current worktree state for #300, `mise run check:pytest -- tests/test_skipscan.py -q` passed 151 scanner tests. `mise run check` passed, including 1,021 standard tests, 1,146 coverage tests, Python core line coverage 97.67%, and Python core branch coverage 94.36%. `mise run check:mutation` passed: Go core 97.32% (145 killed of 149) and Python core 90.01% (11,763 killed of 13,068). `mise run build` passed.

The runnable workflow and CI probe for #300 are in PR #315. The [earlier CI probe](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37755429626/job/113238668457) rejected an untracked indicator and passed after an issue reference was placed beside it.

In the stacked #315 worktree before the main merge, 150 targeted scanner tests, `mise run check`, `mise run docs:build`, and `mise run build` passed. `mise run check:mutation` passed with Go core 97.32% and Python core 90.08% (11,746 killed of 13,039). Local `mise run docs:check-links` failed twice because Chromium could not register its macOS rendezvous server in this sandbox; the Linux CI docs job passed on `d57f412`.

GitHub [runs comment workflows from the default branch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#issue_comment). The comment workflow checks out that branch and [creates a check run on the PR head](https://docs.github.com/en/rest/checks/runs#create-a-check-run). Live comment edits and deletions remain untested until #315 lands on the default branch; local tests cover event routing and head check publication through a loopback API.
