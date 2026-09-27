# Reviewer account evidence

## Sources and versions

The installed GitHub CLI is 2.100.0. Its source was cloned under `/private/tmp/gh-cli-83` at `cli/cli@45437bc7eeeb3359bbfddd1742f79de7652fd3e2`. The versioned `docs/multiple-accounts.md` describes `gh auth token --user` with a per-command `GH_TOKEN`, and `pkg/cmd/auth/token/token.go` selects that user's token or fails when none exists. Python 3.14.6, uv 0.12.10, pytest 9.1.1, Hypothesis 6.168.1, Ruff 0.16.9, ShellCheck 0.11.0, and shfmt 3.14.0 follow the repository pins and the Python and shell conventions pages.

## Ruleset reads

| Command | Exit | Result |
| --- | --- | --- |
| `gh api repos/tbhb/agent-orchestration-poc/rulesets/24053242 --jq '{id,name,enforcement,bypass_actors,rules}'` | 0 | Active `main`, empty bypass list, squash only, one approval, stale dismissal, resolved threads, latest-push approval, extra approval for unattributed changes, five checks, strict up-to-date policy, deletion and force-push blocks |
| `gh api repos/tbhb/agent-orchestration-poc/rulesets/24056095 --jq '{id,name,enforcement,bypass_actors,rules}'` | 0 | Active `all-branches`, empty bypass list, non-fast-forward block |
| `gh api repos/tbhb/agent-orchestration-poc/collaborators/tbhbbot/permission --jq '{user:.user.login,permission,role_name}'` | 0 | `tbhbbot` has `write` permission |

The live `main` status check contexts are `check`, `docs`, `pr-body`, `imported-research`, and `mutation`, with `strict_required_status_checks_policy=true`. Its pull request parameters set `dismiss_stale_reviews_on_push=true`, `require_last_push_approval=true`, `required_review_thread_resolution=true`, `required_approving_review_count=1`, and `require_extra_approval_for_unattributed_changes=true`. The operator's [before and after account and ruleset record](https://github.com/tbhb/agent-orchestration-poc/issues/83#issuecomment-5851065479) gives the earlier zero-approval, no-dismissal, no-thread-resolution, and no-last-push state. The [later hardening record](https://github.com/tbhb/agent-orchestration-poc/issues/83#issuecomment-5851173956) records the five-check, up-to-date, and all-branch force-push changes.

## Identity and review observations

| Command | Exit | Output |
| --- | --- | --- |
| `gh api user --jq .login` | 0 | `tbhb` |
| `scripts/reviewer-gh.sh api user --jq .login` | 0 | `tbhbbot` |
| `mise exec -- uv run pytest tests/fixtures/review_identity/test_policy.py` | 0 | 32 passed |
| `mise exec -- uv run pytest tests/fixtures/review_identity/test_wrapper.py --run-integration` | 0 | 5 passed |
| `mise run check` | 0 | 84 passed, 7 integration skips, all aggregate gates passed |
| `mise run check:mutation` | 0 | Go 85 of 85 mutants killed, Python 241 of 282 killed, 85.46 percent score, 100 percent Python core line coverage |
| `mise run check:review-identity` | 1 | No task found because issue #83's allowed paths omit `mise.toml` |
| `mise run build` | 0 | `bin/agentd` and `bin/agentctl` built |
| `mise run docs:check-links` | 1 | Sandboxed Chromium failed its macOS Mach port registration, then the validator reported three existing `/workflow/` links |

The wrapper fixtures cover a successful review command and expected exits 90 or 91 for failed token lookup, empty token, wrong effective identity, and failed identity lookup. In every failing fixture, the review command did not run, and no fixture token appeared in captured output. The successful sandboxed identity probe printed only account names. The operator's [account setup record](https://github.com/tbhb/agent-orchestration-poc/issues/83#issuecomment-5850989497) confirms Project write access, default account, and git credential helper without disclosing a token.

The first commit attempt could not write `/Users/tony/.cache/prek/prek.log` under the filesystem sandbox. Repeating the normal hooks with `XDG_CACHE_HOME=/private/tmp/issue83-cache` passed without changing sandbox permissions. The local docs failure matches the Chromium Mach port denial and three `/workflow/` link reports recorded by [PR #95](https://github.com/tbhb/agent-orchestration-poc/pull/95). The hosted `docs` check will decide this PR's site result.

The [issue review comment](https://github.com/tbhb/agent-orchestration-poc/issues/83#issuecomment-5851629136) asks for the exact test modules and mise task path to be added to the allowed scope before dispatch. The issue body was not updated to allow `mise.toml`, so the dedicated task is still absent. The fixture tests run through the pinned tools with the exact commands above.

The [PR #80 request-changes review](https://github.com/tbhb/agent-orchestration-poc/pull/80#pullrequestreview-5328147939) at `83b0fca` and [approval review](https://github.com/tbhb/agent-orchestration-poc/pull/80#pullrequestreview-5328205815) at `0cfbc62` are both by `tbhbbot`. The [operator's trial record](https://github.com/tbhb/agent-orchestration-poc/issues/83#issuecomment-5851166383) reports implementer thread replies, reviewer thread resolution, and a successful squash merge after approval. The issue body reports that clean updates retain approval and hand-resolved merges dismiss it. Those update outcomes and the blocked merge without approval were not independently reproduced in this worktree, so they remain operator-recorded observations without a new raw trace here.

## Fixture outcomes

`tests/fixtures/review_identity/policy.json` records passing and failing cases for reviewer identity, active and dismissed approval, clean and hand-resolved updates, last pusher, three review rounds and arbitration, five checks, and published-branch merge versus unpublished rebase. `tests/fixtures/review_identity/wrapper.json` records expected exit codes and whether the review command may run. The tests check these plain values without mocks. The process fixtures use a temporary fake `gh` executable and bind no network address.
