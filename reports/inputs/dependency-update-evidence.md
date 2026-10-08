# Dependency update research evidence for issue #91

## Source and repository reads

[verified] On 2026-10-07, `git rev-parse HEAD` in `/private/tmp/codex-91-renovate` exited 0 and printed `0dfb75020092789b7dc3f398e31259173f24b69f`. The clone uses `--filter=blob:none --depth=1 --sparse` and contains the five manager documentation files and `docs/usage/configuration-options.md` named in the [research note](dependency-update-research.md). The source package identifies its version as `0.0.0-semantic-release`, so the commit is the precise version used here.

[verified] On 2026-10-07, `git rev-parse HEAD` in `/private/tmp/codex-91-dependabot-core` exited 0 and printed `328836263e30e52540e77f0595a6b87b319271ce`. The clone has sparse `uv/`, `go_modules/`, `npm_and_yarn/`, `github_actions/`, and `python/` source. GitHub's [Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference), read 2026-10-07, supplies the documented ecosystem matrix and limit behavior. Neither source checkout was executed as a dependency updater.

[verified] The issue body was read with `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api repos/tbhb-dev/agent-orchestration-poc/issues/91 --jq .body`, exit 0. The comments were read through the corresponding `/comments --paginate` endpoint, exit 0. The issue labels were `area/tooling`, `type/tooling`, `phase/2`, and `harness/codex`. The branch began clean on `research/91-dependency-updates` against `origin/main`. `mise run vale:sync` exited 0 in this worktree.

[verified] The repository snapshot pins Go 1.27.1, uv 0.12.10, pnpm 12.7.0, and mise-managed tools in `mise.toml`. The full SHA Action references in `.github/workflows/*.yml` lack same-line version comments. The repository has no `.github/dependabot.yml` at this branch head. These are file observations, not updater behavior.

## Deferred acceptance evidence

[untested] The implementation validator and its passing and failing fixtures do not exist in this research delivery. `mise run check:dependency-updates` therefore has no meaningful validation exit to report. The later configuration item must record exact exits for a passing fixture, an over-limit fixture, an unsupported or unowned ecosystem fixture, and the task itself. It must keep pure decisions in the core and I/O in the shell.

[untested] No real update proposal or coordinator-owned implementation PR was produced in this research delivery. The later enablement evidence must link the generated proposal and the open issue, branch, committed versioned research, exact pins, lockfile and convention changes, PR, five successful checks, up-to-date branch, resolved threads, and current `tbhbbot` approval. This report will be extended only when those observations exist. Issue #91 remains open after the partial PR.

## Local verification

[verified] `mise run fmt` exited 0 and left only the six intended research and documentation paths changed. `mise run check:vale` exited 0 after edits to the new pages. `mise run check:rumdl`, `git diff --cached --check`, and `mise run check:secrets` exited 0. A staged-file-only `mise exec -- gitleaks dir --redact --no-banner <temporary staged copy>` exited 0 with no leaks. No service credentials were read or used.

[verified] `mise run check` exited 0 on 2026-10-07 local time. Its ordinary Python suite passed 728 tests with 117 integration skips, and its coverage suite passed 845 tests. Python core lines were 97.41%, core branches 94.06%, shell lines 75.77%, Go core statements 96.43%, core branches 94.74%, and shell statements 74.58%. No source code or dependency pin changed in this delivery.

[verified] `mise run pr:size -- origin/main` exited 0 before this evidence update and reported 22 counted units across the docs pages. Both `reports/inputs/` files were excluded by the repository size contract. The raw diff had 93 added lines across six files at that point.

[observed] `mise run docs:check-links` exited 1 locally. The sandbox denied Chromium's Mach port rendezvous at launch. The validator also listed seven links in existing pages, including `/workflow/`, `/design/github-event-monitor/`, and `/workflow/#ci-jobs`. None of the newly added `/decisions/0011-dependency-update-proposals/` links appeared in that list. Hosted `docs` CI is needed to establish the PR's site result. The sandbox also denied `ps` during diagnosis. The first commit attempt could not write `/Users/tony/.cache/prek/prek.log`, so the unchanged normal hooks were run with `PREK_HOME=/private/tmp/codex-91-prek` and passed. No sandbox escape was attempted.

[verified] `mise run check:mutation` exited 0. Go core mutation killed 145 of 149 classified mutants for 97.32% efficacy and 100.00% mutator coverage. Python core mutation killed 9,042 of 10,007 mutants for a 90.36% score.
