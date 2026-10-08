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

The final local `mise run check`, `mise run check:mutation`, documentation checks, secret scan, and changed-line measurement are recorded below when completed. No service credentials were read or used.
