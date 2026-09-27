# Workflow forms evidence for issue #84

## Source and versions

Documented: I read the GitHub Docs source at `github/docs@18945a31a4f2d97beb6c5c1a7479102e23c25727`, including `content/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms.md`, `syntax-for-githubs-form-schema.md`, and `content/actions/reference/workflows-and-actions/events-that-trigger-workflows.md`. Those files define issue form keys, textarea validation, and the issue, PR, and schedule triggers used here.

Documented: `reports/inputs/pr-size-research.md` records `boyter/scc` v4.1.0 source at `/tmp/scc-84-source`, commit `c651b07a7d3aa6e97a476380eef0f478a53719a3`. The pinned tool and reference size rules are included in this PR. The counter and its fixtures are proposed for a dependent item because the staged estimate exceeded 800 units when they shared this PR with form validation.

## Commands and results

- Verified: `mise trust` exited 0, and `mise run vale:sync` exited 0 once in this worktree.
- Verified: `mise run check:workflow-forms` exited 0 with 37 passing core tests and matching generated forms and page after the review changes.
- Observed: the pre-split `mise run check:label-drift` exited 1 and reported ten unused GitHub default labels. The task was removed to keep this PR under 800 units. `mise run check:label-drift` now exits 1 with `no task check:label-drift found`. The source snapshot is `reports/inputs/workflow-labels/before.tsv`.
- Untested: `WORKFLOW_LABEL_SYNC=coordinator mise run labels:sync` was not invoked because label mutation belongs to the coordinator and the sync task moved to the dependent item. `reports/inputs/workflow-labels/after-pending.md` records that no after-sync state exists.
- Observed: `mise run check:pr-size-contract` exited 1 with `no task check:pr-size-contract found`. The counter, edge fixtures, and fixture command are proposed for the dependent item.
- Observed: the first review-fix `mise run check` exited 1 on ten strict pyrefly diagnostics in new shell tests. After that fix, `mise run check` exited 2 when Go scanned a pnpm directory during concurrent docs setup; standalone `mise run check:go` exited 0. The next aggregate run exited 3 on vulture findings in the new tests; `mise run check:deadcode` exited 0 after those were corrected. The final `mise run check` ran 165 Python tests and its Go race tests, then was interrupted after 223 seconds because `gobco -branch` had not returned. The hosted check must confirm the aggregate result for this head.
- Verified: `mise run check:coverage` ran all 165 Python tests and reported Python core lines 100.00%, branches 97.00%, and shell lines 82.59%; Go core statements were 100.00% and shell statements 72.12%. The task was interrupted after its `gobco -branch` subprocess remained silent for several minutes, so Go branch coverage was not confirmed locally. The hosted check at ea4d24b had failed the pre-fix Python floors of 89.00% core branches and 42.80% shell lines.
- Observed: hosted mutation at ea4d24b failed with 943 of 1049 Python mutants killed, or 89.90%, below 90%. The first local review-fix `mise run check:mutation` killed 89 of 89 Go mutants, then exited 1 when mutmut's core-only test copy could not import the new shell test module. The shell test now skips collection when that package is absent from mutmut's copy. The complete `mise run check:mutation` rerun exited 0: Go killed 89 of 89 mutants, and Python killed 993 of 1068, or 92.98%.
- Observed: `mise run docs:build` exited 0 and built 39 pages. Chromium logged a macOS Mach bootstrap permission denial during content sync. The site still built, and hosted CI must verify links.
- Observed: `mise run docs:check-links` exited 1 after the same Chromium denial. It reported three `/workflow/` links in unchanged pages during the incomplete render. No browser or sandbox setting was changed.
- Verified: `mise run build` exited 0 and produced both Go binaries after the review fixes.
- Verified: `mise exec -- gitleaks dir --redact --no-banner reports/inputs` exited 0 with no leaks found.
- Observed: `mise run scc:version` exited 1 because the sandbox denied creation of `~/.local/share/mise/installs/go-github-com-boyter-scc-v4/4.1.0`. The tool is scoped to its task. No alternate install path was used.

## Fixtures and migration

Verified: `tests/fixtures/workflow_forms/issue_cases.json` and `pr_cases.json` cover passing and failing titles, required sections, labels, single and multiple final `Refs` trailers, and closed references. `tests/test_workflow_forms.py` checks removal of a trailer on body edit. `migration_cases.json` covers an old branch used by a new PR, a pre-cutoff PR, missing creation metadata, and a local-only ref. The remote predicate uses the activation PR's retained `merged_at` timestamp. Before that PR merges, it reports valid PRs and fails closed on missing creation time. After merge, it enforces PRs created at or after the timestamp, regardless of branch age.

Verified: `mise run workflow:issue -- 84`, `-- 151`, and `-- 152` each exited 0 with `[enforce] valid`. `config/workflow-reference.toml` records PR #137 as the activation PR. Before PR #137 merges, `mise run workflow:pr -- 137` exited 0 with `#137 [report] valid` after the body and labels were corrected. The live PR was created at `2026-09-27T03:18:11Z`, targets `main`, and has the four required label families. Its `merged_at` is still null, so it has no enforcement cutoff yet. The separate `reports/inputs/workflow-local-ref-migration.md` lists local-only refs and has no CI gate.

## Current main integration

Observed: after the review-fix push, `main` advanced through cd6e4c1. `git fetch origin && git merge --no-ff origin/main` found one add/add conflict in the generated workflow reference page. The pure renderer now preserves the Agent provenance section added by #131, and `mise run forms:write` regenerated the page. `mise run check:workflow-forms` exited 0 with 37 core tests and matching generated artifacts.

Verified: `mise run check:go` exited 0 after the merge. `mise run docs:build` exited 0 and built 48 pages. `mise run docs:check-links` exited 1 after sandboxed Chromium failed to launch and the validator reported five links in unchanged pages: two `/workflow/`, two `/design/github-event-monitor/`, and one `/workflow/#ci-jobs`. No link in the merged reference page was reported invalid.

Observed: post-merge `mise run check` first exited 2 on the same transient Go scan of a pnpm directory while the parallel Mermaid task prepared dependencies; standalone `check:go` passed. The rerun completed 165 Python tests and Go race tests, then was interrupted after 121 seconds in `gobco -branch`. Its floor output was Python core lines 100.00%, branches 97.00%, shell lines 82.59%, Go core statements 96.43%, and Go shell statements 74.58%. Go branch coverage and the complete aggregate remain for hosted CI to confirm. Post-merge `mise run check:mutation` exited 0: Go killed 145 of 149 mutants, or 97.32%, and Python killed 993 of 1068, or 92.98%.

## Size split

Observed: `git diff --cached --shortstat` originally reported 33 files, 1,824 additions, and three deletions. A conservative nonblank-line diff count over that staged change, excluding generated forms and page, fixtures, and `reports/inputs/`, estimated 797 units. The review adds necessary tests and likely pushes the PR above 800 units. `mise run scc:version` still exits 1 because the sandbox denies the pinned tool's install directory, so this is not a measured `scc` count. A PR comment proposes splitting the reference and generated artifacts into a base PR, with the validator and regression tests stacked in #137. Issues #151 and #152 now track the deferred counter and label tooling; #93 depends on #151. The reference retains both contracts, while #84 remains incomplete until those items land. No Project fields were edited.

Observed: the earlier pre-commit narrative described the initial worktree state before PR #137 existed. PR #137 now exists, and `git fetch origin && git merge origin/main` fetched successfully but stopped at the repository's fast-forward-only merge setting. `git merge --no-ff origin/main` completed after a normal merge commit with `Refs: #84`. The hosted pr-body job 108540964421 at ea4d24b exited 2 with `ValueError: validator PR number is not recorded`; the new activation value and shell regression cover that failure.
