# Workflow forms evidence for issue #84

## Source and versions

Documented: I read the GitHub Docs source at `github/docs@18945a31a4f2d97beb6c5c1a7479102e23c25727`, including `content/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms.md`, `syntax-for-githubs-form-schema.md`, and `content/actions/reference/workflows-and-actions/events-that-trigger-workflows.md`. Those files define issue form keys, textarea validation, and the issue, PR, and schedule triggers used here.

Documented: `reports/inputs/pr-size-research.md` records `boyter/scc` v4.1.0 source at `/tmp/scc-84-source`, commit `c651b07a7d3aa6e97a476380eef0f478a53719a3`. The pinned tool and reference size rules are included in this PR. The counter and its fixtures are proposed for a dependent item because the staged estimate exceeded 800 units when they shared this PR with form validation.

## Commands and results

- Verified: `mise trust` exited 0, and `mise run vale:sync` exited 0 once in this worktree.
- Verified: `mise run check:workflow-forms` exited 0 with 24 passing tests and matching generated forms and page.
- Observed: the pre-split `mise run check:label-drift` exited 1 and reported ten unused GitHub default labels. The task was removed to keep this PR under 800 units. `mise run check:label-drift` now exits 1 with `no task check:label-drift found`. The source snapshot is `reports/inputs/workflow-labels/before.tsv`.
- Untested: `WORKFLOW_LABEL_SYNC=coordinator mise run labels:sync` was not invoked because label mutation belongs to the coordinator and the sync task moved to the dependent item. `reports/inputs/workflow-labels/after-pending.md` records that no after-sync state exists.
- Observed: `mise run check:pr-size-contract` exited 1 with `no task check:pr-size-contract found`. The counter, edge fixtures, and fixture command are proposed for the dependent item.
- Verified: the latest `mise run check` exited 0 with 76 passing Python tests, two default integration skips, two kept import contracts, and zero duplicate blocks. Earlier runs exited 2 when `gofumpt` encountered a pnpm directory being populated by the parallel Mermaid check and exited 3 when another `golangci-lint` process held its lock. Complete reruns passed after each transient conflict.
- Verified: the final `mise run check:mutation` exited 0. Go killed 85 of 85 mutants with 100% mutator coverage. Python killed 689 of 822 mutants, or 83.82%.
- Observed: `mise run docs:build` exited 0 and built 39 pages. Chromium logged a macOS Mach bootstrap permission denial during content sync. The site still built, and hosted CI must verify links.
- Observed: `mise run docs:check-links` exited 1 after the same Chromium denial. It reported three `/workflow/` links in unchanged pages during the incomplete render. No browser or sandbox setting was changed.
- Verified: `mise run build` exited 0 and produced both Go binaries.
- Verified: `mise exec -- gitleaks dir --redact --no-banner reports/inputs` exited 0 with no leaks found.
- Observed: `mise run scc:version` exited 1 because the sandbox denied creation of `~/.local/share/mise/installs/go-github-com-boyter-scc-v4/4.1.0`. The tool is scoped to its task. No alternate install path was used.

## Fixtures and migration

Verified: `tests/fixtures/workflow_forms/issue_cases.json` and `pr_cases.json` cover passing and failing titles, required sections, labels, single and multiple final `Refs` trailers, and closed references. `tests/test_workflow_forms.py` checks removal of a trailer on body edit. `migration_cases.json` covers an old branch used by a new PR, a pre-cutoff PR, missing creation metadata, and a local-only ref. The remote predicate uses the activation PR's retained `merged_at` timestamp. Before that PR merges, it reports valid PRs and fails closed on missing creation time. After merge, it enforces PRs created at or after the timestamp, regardless of branch age.

Observed: `mise run workflow:issue -- 84` exited 0 with `#84 [enforce] valid`. The remote PR report and activation PR number remain pending because the commit hook is blocked. The separate `reports/inputs/workflow-local-ref-migration.md` lists local-only refs and has no CI gate.

## Size split

Observed: `git diff --cached --shortstat` reported 33 files, 1,824 additions, and three deletions before this evidence update. A conservative nonblank-line diff count over the staged change, excluding generated forms and page, fixtures, and `reports/inputs/`, estimated 797 units. This is an estimate because the pinned `scc` binary could not install in the sandbox. The 800-unit limit caused two proposed dependent slices: a pure `scc` diff counter and fixtures before #93 CI enforcement, and read-only label drift plus coordinator-only sync with before and after artifacts. The reference retains the size and label contract for those items. No issue, PR, label, or Project field was edited by the validators.

Observed: `git diff --cached --check` exited 0. Two normal `git commit` attempts with subject `tooling(workflow): add issue and pull request form validation` and `Refs: #84` exited 1 before running hooks because prek could not open `/Users/tony/.cache/prek/prek.log` under the sandbox. The second attempt followed the final green `mise run check` and `mise run check:mutation`. No hook bypass or alternate cache path was used. No commit was created, and no push or PR was attempted. The proposed code and documentation remain staged for the operator to resume after the sandbox grants prek cache access.
