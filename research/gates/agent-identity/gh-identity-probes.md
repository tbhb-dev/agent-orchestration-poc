# GitHub account selection evidence

Read on 2026-09-27 UTC for issue #132. Harness is Codex CLI 0.157.1, model `gpt-6-astra`, medium. Baseline: `734985cf312c3fa1002e33595bec3c1633f9bf6e`. No login, account switch, token inspection, credential-file copy, or key operation was performed.

## Versions and source

| Source | Version and exact commit | Material read |
| --- | --- | --- |
| Installed gh | 2.100.0, release date 2026-09-03 | `mise exec -- gh --version` |
| Installed Git | 2.55.0 | `mise exec -- git --version` |
| gh source | `45437bc7eeeb3359bbfddd1742f79de7652fd3e2` | Existing clone `/private/tmp/gh-cli-83`, inspected without modifying it |
| Project wrapper | Baseline above | `scripts/reviewer-gh.sh`, shell/core `review_identity.py`, `reports/inputs/reviewer-account-evidence.md` |

[Documented] [Multiple-account documentation](https://github.com/cli/cli/blob/45437bc7eeeb3359bbfddd1742f79de7652fd3e2/docs/multiple-accounts.md) describes additive login and a newly logged-in active account. The active account also affects git operations when gh is the credential helper. It does not change Git author configuration. New-account runtime behavior remains untested here.

[Schema] [token.go](https://github.com/cli/cli/blob/45437bc7eeeb3359bbfddd1742f79de7652fd3e2/pkg/cmd/auth/token/token.go) selects `TokenForUser` when `--user` is present and errors when the result is empty. [config.go](https://github.com/cli/cli/blob/45437bc7eeeb3359bbfddd1742f79de7652fd3e2/internal/config/config.go) uses `gh:` plus hostname as its keyring service and username as the account. `TokenForUser` tries that keyring entry before the file value for that user. This differs from `ActiveToken`, which consults environment/config first and can use a legacy keyring fallback.

[Help-text and schema] [help_topic.go](https://github.com/cli/cli/blob/45437bc7eeeb3359bbfddd1742f79de7652fd3e2/pkg/cmd/root/help_topic.go) defines `GH_TOKEN` before `GITHUB_TOKEN`, ahead of stored credentials. `GH_CONFIG_DIR` selects a configuration directory. `GH_DEBUG=api` enables HTTP detail logging. These conclusions use source without reading actual environment values or credential files.

## Safe probe results

| Exact command | Exit | Identity-only observation |
| --- | --- | --- |
| `mise exec -- gh --version` | 0 | gh 2.100.0 |
| `mise exec -- git --version` | 0 | Git 2.55.0 |
| `gh api user --jq .login` | 0 | `tbhb` |
| `mise exec -- env -u GH_TOKEN -u GITHUB_TOKEN gh api --hostname github.com user --jq .login` | 0 | `tbhb` |
| `mkdir -p "$TMPDIR/issue-132-empty-gh"` | 0 | Empty task-owned directory, no credentials copied |
| `mise exec -- env -u GH_TOKEN -u GITHUB_TOKEN GH_CONFIG_DIR="$TMPDIR/issue-132-empty-gh" GH_PROMPT_DISABLED=1 gh api --hostname github.com user --jq .login` | 4 | Authentication required, no login returned |
| `git -C /private/tmp/gh-cli-83 rev-parse HEAD` | 0 | Source commit above |

[Observed] The empty-directory command printed gh's standard instruction to authenticate. That text was not followed. It establishes refusal in this invocation, not that a same-host process cannot retrieve another named account from the keyring. The worker did not execute explicit-account credential lookups because the assignment restricts probes to the default identity and prohibits token inspection.

## Comparison and risks

| Candidate | Selection and failure behavior | Security limit |
| --- | --- | --- |
| Process-local named-account wrapper, selected | Resolve one account internally, verify `/user`, then use the same credential for one validated operation. Refuse any failure. | Prevents compliant callers from using the wrong default, but cannot isolate a reachable credential from arbitrary same-user code |
| Separate `GH_CONFIG_DIR` | Separate file settings and active-account metadata, verify effective identity on every operation | Environment overrides still apply, and keyring lookup still uses hostname and user. It is not a credential boundary |
| Dedicated OS principal or isolated broker | Operator owns credentials and typed authorized operations | Requires host setup, access tests, and operator approval. Prepared response for accidental `tbhb` use |

Selection risks include inherited environment tokens, host overrides, mutable executable/configuration lookup, arbitrary authorization headers, a generic API escape, credentials in shell tracing, diagnostics, HTTP logs, child environments, crash dumps, and disk-backed fallback storage. The future wrapper rejects generic commands and controls these inputs. It suppresses lookup output and raw errors, and keeps credentials out of temporary files. The current reviewer wrapper is a model for lookup and identity checking, not proof that the proposed endpoint restrictions already exist.

## Login order and deferred probes

The operator stops dispatch and drains workers that might use the shared default or credential helper. Workers commit and push their work before stopping. Stage dormant wrappers first. The operator then logs in `tbhbagent` on `github.com` over HTTPS in the existing configuration, preserving `tbhb` and `tbhbbot`. The proposed command is `gh auth login --hostname github.com --git-protocol https --web`. It is not run here. Do not use plaintext storage or copy authentication files. If secure storage is unavailable, stop.

Source predicts that login makes `tbhbagent` active. Verify with token overrides removed and `/user` returning `tbhbagent`. If a different account is active, the operator selects `tbhbagent` during the drained window and verifies again. Workers never select the default account themselves. The operator later reaches `tbhb` through a separate process-local operator wrapper, without changing the shared default. Keeping `tbhb` as default would turn a missing wrapper into an apparent operator action, which the operator rejected.

[Untested] At cutover, verify the default identity, each named-account wrapper, reviewer continuity, git credential-helper push identity, wrong-account refusal, Project 9 read access as `tbhbagent`, and the authorized Project write path in fixtures. A Project read does not prove write permission. Do not infer Project access from repository write access. If it is missing, the operator grants only the required Project role and credential scope. A read-only command is `gh project view 9 --owner tbhb --format json`, executed through the selected agent wrapper. Record only Project identity and access outcome, not item contents.
