# Skipscan review evidence for #300

## Reproduction

- Verified: Five new core regression cases failed against the reviewed code for #300: an unrelated URL counted as tracking, three real threshold reductions produced no hit, and executable calls beside triple-quoted strings produced no hit.
- Verified: The event trigger test failed against the restored workflow for #300 because `issue_comment` was absent.
- Verified: The [earlier CI probe](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37755429626/job/113238668457) for #300 rejected an untracked indicator and passed after an issue reference was placed beside it.

## Local checks

- Verified on `6466a3f` for #300: `mise run check`, `mise run build`, and `mise run check:mutation` passed. Go core mutation efficacy was 97.32%; Python core mutation score was 90.06% (11,706 killed of 12,998).
- Verified in the stacked worktree for #300: 150 targeted scanner tests, `mise run check`, `mise run docs:build`, and `mise run build` passed before the stacked commit.
- Verified in the stacked worktree for #300: `mise run check:mutation` passed after the workflow test was made compatible with mutmut's copied test directory. Go core efficacy was 97.32%; Python core score was 90.08% (11,746 killed of 13,039).
- Observed for #300: `mise run docs:check-links` failed twice in this macOS sandbox because Chromium could not register its rendezvous server (permission denied). The resulting seven internal-link errors followed pages that could not render; the Linux CI docs job remains the validation run.

## Event delivery boundary

- Documented for #300: GitHub [runs comment workflows from the default branch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#issue_comment). The comment workflow checks out that branch and [creates a check run on the PR head](https://docs.github.com/en/rest/checks/runs#create-a-check-run).
- Untested for #300: A live comment edit or deletion can only exercise the new workflow after it lands on the default branch. Local tests cover the event types, PR-number selection, and head check publication through a loopback API.
