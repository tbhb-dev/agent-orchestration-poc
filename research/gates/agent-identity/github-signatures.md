# Signature and merge source evidence

Read on 2026-09-27 UTC. The worker did not read key material or execute gpg, signing, or signature-verification commands. Signature cases below are documented semantics or untested project acceptance cases.

## Recorded sources

| Source | Exact revision | Local checkout |
| --- | --- | --- |
| Git 2.55.0 | `e9019fcafe0040228b8631c30f97ae1adb61bcdc` | `$TMPDIR/issue-132-git` |
| GitHub Docs | `18945a31a4f2d97beb6c5c1a7479102e23c25727` | `$TMPDIR/issue-132-github-docs` |

Both clones use the permitted temporary root because new `~/Code/github.com` directories are outside the writable roots. Here `$TMPDIR` resolves to `/var/folders/ns/cc4x7s5j5271ltrw1t08w7p40000gn/T/`. No host installation or permission change occurred. Successful clone, sparse-checkout, and revision commands exited 0.

```text
git clone --depth 1 --branch v2.55.0 --filter=blob:none --sparse https://github.com/git/git.git "$TMPDIR/issue-132-git"
git -C "$TMPDIR/issue-132-git" sparse-checkout set Documentation
git -C "$TMPDIR/issue-132-git" rev-parse HEAD
git clone --depth 1 --filter=blob:none --sparse https://github.com/github/docs.git "$TMPDIR/issue-132-github-docs"
git -C "$TMPDIR/issue-132-github-docs" sparse-checkout set content/authentication/managing-commit-signature-verification content/repositories/configuring-branches-and-merges-in-your-repository data/reusables/repositories
git -C "$TMPDIR/issue-132-github-docs" rev-parse HEAD
```

## Documented semantics

| Claim | Versioned source read | Implication |
| --- | --- | --- |
| Git author and committer fields can be overridden by environment and separate config keys | [Git user configuration](https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/config/user.adoc) | Account selection and `user.name` alone are insufficient |
| Git can use a custom OpenPGP program for signing and verification | [Git gpg configuration](https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/config/gpg.adoc) | A constrained adapter can forward a payload without forwarding the private key |
| `verify-commit --raw` validates a commit signature. Signature fields expose signing and primary fingerprints | [verify-commit](https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/git-verify-commit.adoc), [pretty formats](https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/pretty-formats.adoc) | Future verification binds both fingerprints and commit bytes, not display-name text |
| Merge signing covers the resulting merge commit. `--verify-signatures` checks the side tip only | [Merge options](https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/merge-options.adoc) | Verify every in-scope PR commit separately |
| GitHub persists verified status even after key revocation or expiry and records `verified_at` | [Signature verification](https://github.com/github/docs/blob/18945a31a4f2d97beb6c5c1a7479102e23c25727/content/authentication/managing-commit-signature-verification/about-commit-signature-verification.md) | A stored badge cannot establish current signer authorization |
| GitHub signs web-interface commits with its own key | Same signature document | Verify the GitHub squash result separately from agent branch commits |
| Rulesets check commits not reachable from other branches on creation, and the update range on updates | [Available rules](https://github.com/github/docs/blob/18945a31a4f2d97beb6c5c1a7479102e23c25727/content/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets.md) | A ruleset does not enforce the project's exact PR population or expected-account rule |
| GitHub checks commits introduced by a test merge, including the PR head branch. Unsigned commits can block squash | [Required signed commits reusable](https://github.com/github/docs/blob/18945a31a4f2d97beb6c5c1a7479102e23c25727/data/reusables/repositories/required-signed-commits.md) | A GitHub-signed squash does not cure unsigned branch history |

[Documented] The ruleset page permits some partially verified vigilant-mode commits. This project requires its stricter expected-signer check. The source suggests rewriting or bypassing unsigned history as remedies. This project's all-branches force-push prohibition and empty bypass lists forbid both remedies.

## Live ruleset read

Both commands exited 0. [Observed] `main` is active with no bypass actors, squash-only PRs, one approval, stale dismissal, latest-push approval, resolved threads, strict current-base checks, and required `check`, `docs`, `pr-body`, `imported-research`, and `mutation`. It has no `required_signatures` rule. `all-branches` is active with the non-fast-forward prohibition and no bypass actors.

```text
gh api repos/tbhb/agent-orchestration-poc/rulesets/24053242 --jq '{id,name,enforcement,conditions,bypass_actors,rules}'
gh api repos/tbhb/agent-orchestration-poc/rulesets/24056095 --jq '{id,name,enforcement,conditions,bypass_actors,rules}'
```

## Future verification cases

The cases below remain untested until #133/#140 and the operator's signing rehearsal. No fixture here claims cryptographic execution.

| Input | Expected result |
| --- | --- |
| Agent author/committer and approved fingerprints, good signature, mapped account, valid authorization | Accept signature policy, still require review and merge preflight |
| Good signature from unapproved key or wrong GitHub account | Refuse |
| GitHub badge persists but policy revokes signer | Refuse new use |
| Missing, bad, expired, revoked, unknown, or unverifiable signature | Refuse |
| Signed branch tip above an unsigned introduced commit | Refuse |
| New signed merge-main commit plus inherited unsigned main ancestors | Validate new commit, exclude inherited population, rehearse GitHub ruleset separately |
| New human-only merge without admitted human signer policy | Refuse pending operator decision |
| GitHub squash signed by approved web-flow key for the recorded authorized merge | Accept postmerge check only, not branch-signature evidence |
| GitHub squash with wrong actor, unexpected SHA/parents, or changed title/body union | Stop further merges and report |
| PR head/base changes or REST pagination is incomplete | Refuse and recollect |
| Signer timeout, replayed request, changed payload or parent, wrong repository | Refuse without unsigned fallback |
| Worker can read private material or request arbitrary signatures | Signing boundary fails, no cutover |

The operator chooses whether old PRs are enforced or receive a recorded exception. Enforced unsigned work moves to a fresh branch from current main with reviewed changes and newly signed commits, then a replacement PR with fresh review. Old published history is retained. A signed empty commit or merge cannot change an old commit's signature. Under a legacy exception, defer the required-signatures ruleset until all grandfathered unsigned work has drained. No ruleset bypass is proposed.
