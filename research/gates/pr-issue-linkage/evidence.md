# Pull request and issue linkage evidence

## Review correction, 2026-10-08

[Verified] The three research citations in decision 0014 pointed to `blob/decision/124-pr-closing-links/`, while the repository setting `delete_branch_on_merge` was `true`. A search for that branch URL in the decision page returned three occurrences and exit 1 under the assertion below. Commit `6309b8cd416e948cadb142f783e53f75c279e096` contains both research artifacts, so the decision now cites that immutable revision.

```sh
if rg -n 'blob/decision/124-pr-closing-links/' docs/src/content/docs/decisions/0014-pr-issue-linkage.md; then exit 1; fi
git show 6309b8cd416e948cadb142f783e53f75c279e096:research/gates/pr-issue-linkage/notes.md >/dev/null
git show 6309b8cd416e948cadb142f783e53f75c279e096:research/gates/pr-issue-linkage/evidence.md >/dev/null
/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api -i 'repos/tbhb-dev/agent-orchestration-poc?per_page=100' --jq '{delete_branch_on_merge}'
```

The first assertion exited 1 before the fix, and both `git show` commands exited 0. The single read-only REST request exited 0 with HTTP 200 and `delete_branch_on_merge: true` at the GitHub response `Date` of 2026-10-08 02:03:32 UTC. Its selected API version was `2022-11-28`; `X-Ratelimit-Resource` was `core`, `X-Ratelimit-Limit` was `5000`, `X-Ratelimit-Remaining` was `4204`, and `X-Ratelimit-Reset` was `1791426163`. This request is separate from the 31-request original capture below.

[Verified] After the fix, the branch-URL assertion and `git diff --check` exited 0. `mise run fmt`, `mise run docs:build`, and `mise run check:mutation` exited 0. Go mutation scored 97.32% and Python mutation scored 90.36%. `mise run docs:check-links` exited 1 on seven links in seven unchanged files; the changed decision page was not listed. Chromium also logged a macOS permission denial while rendering existing pages. The first `mise run check` exited 1 when `gobco` returned an error during Go branch coverage. A separate `mise run check:coverage` and the final `mise run check` both exited 0, including Go core branches at 94.74% against the 90% floor.

## Capture boundaries

Captured 2026-10-07 from 20:05:31 through 20:08:01 UTC with read-only REST requests to `tbhb-dev/agent-orchestration-poc`. The GitHub CLI request wrapper was `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api`. All 31 REST requests exited 0 with HTTP 200. The GitHub response selected API version `2022-11-28`, with `X-Ratelimit-Resource: core` and `X-Ratelimit-Limit: 5000`. No rate-limit error occurred. Seventeen requests used `-i` to inspect response headers, and fourteen earlier contextual requests did not. No authorization header, token, or full private response was retained here.

The request count covers two issue/refinement reads, twelve linked issue reads, an initial PR #196 read, five PR reads, two commit reads, four issue timeline reads, three repository or repeated timeline reads, and two final ruleset or timeline reads. This totals 31 requests. Concurrent repository activity means the changing `X-Ratelimit-Remaining` header cannot be used as a request counter.

| Response | GitHub `Date` header | Remaining | Reset | Exit |
| --- | --- | ---: | ---: | ---: |
| First header sample, PR #196 | 2026-10-07 20:06:17 UTC | 4177 | 1791404499 | 0 |
| PR #80 | 2026-10-07 20:06:40 UTC | 4138 | 1791404499 | 0 |
| Issue #176 closure timeline | 2026-10-07 20:07:08 UTC | 4105 | 1791404499 | 0 |
| Main ruleset | 2026-10-07 20:08:00 UTC | 4095 | 1791404499 | 0 |
| Issue #59 timeline | 2026-10-07 20:08:01 UTC | 4094 | 1791404499 | 0 |

## Exact REST commands and paths

The wrapper path below is literal and the `--jq` expressions select the recorded fields. All commands used the worktree as their working directory. `-i` supplied the headers in the table above. The first two commands were the assigned issue and its review history.

```sh
/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api repos/tbhb-dev/agent-orchestration-poc/issues/124 --jq '{body: .body, labels: [.labels[].name], state: .state, title: .title}'
/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api repos/tbhb-dev/agent-orchestration-poc/issues/124/comments --paginate --jq '.[] | {user: .user.login, created_at: .created_at, body: .body}'
```

Each linked issue in the following list was read once through the exact command form below with its literal number substituted for `N`. This yielded twelve requests, all exit 0. The issue descriptions established ownership and integration boundaries. The direct #124 links are #84 and #120, while the refinement comments name the other owners and scheduling dependencies.

```sh
/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api repos/tbhb-dev/agent-orchestration-poc/issues/N --jq '{number, title, state, body, html_url}'
```

`N` values in request order were `84`, `120`, `92`, `89`, `123`, `125`, `128`, `129`, `115`, `121`, `117`, and `176`. The first PR #196 read used `api -i repos/tbhb-dev/agent-orchestration-poc/pulls/196 --jq '{number,merged_at,merge_commit_sha,body,updated_at}'` with the same wrapper path.

The five PR reads used the full wrapper followed by `-i repos/tbhb-dev/agent-orchestration-poc/pulls/N --jq '{number,created_at,updated_at,merged_at,merge_commit_sha,base: .base.ref,body,html_url}'` for `N` values `80`, `81`, `85`, `192`, and `196`. The two commit reads used `-i repos/tbhb-dev/agent-orchestration-poc/commits/SHA --jq '{sha,commit:{message: .commit.message},html_url}'` for `af9716f7445f168dfc942f81d3c8be624314c9e6` and `ee61cb093bcb229bfdab498183ae5f22e595fc14`.

The four timeline reads used the full wrapper followed by `-i 'repos/tbhb-dev/agent-orchestration-poc/issues/N/timeline?per_page=100' --jq '[.[] | {event,created_at,commit_id,source: .source.issue.number,changes,actor: .actor.login}]'` for `N` values `176`, `84`, `132`, and `109`. The query was limited to the first 100 events per issue. A returned page without a connection event is not proof one never existed outside that page.

The three repository and repeated timeline reads were:

```sh
/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api -i 'repos/tbhb-dev/agent-orchestration-poc/issues/176/timeline?per_page=100' --jq '[.[] | select(.event == "project_v2_item_status_changed") ]'
/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api -i 'repos/tbhb-dev/agent-orchestration-poc/issues/176/timeline?per_page=100' --jq '[.[] | select(.event == "closed" or .event == "reopened" or .event == "cross-referenced" and .source.issue.number == 196) | {event,created_at,commit_id,source: .source.issue.number,actor: .actor.login}]'
/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api -i 'repos/tbhb-dev/agent-orchestration-poc' --jq '{default_branch,allow_squash_merge,squash_merge_commit_title,squash_merge_commit_message,delete_branch_on_merge,html_url}'
```

The final two reads were:

```sh
/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api -i 'repos/tbhb-dev/agent-orchestration-poc/rulesets/24053242' --jq '{name,enforcement,bypass_actors,rules}'
/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/gh-as-agent api -i 'repos/tbhb-dev/agent-orchestration-poc/issues/59/timeline?per_page=100' --jq '[.[] | select(.event == "cross-referenced" or .event == "closed" or .event == "project_v2_item_status_changed") | {event,created_at,commit_id,source: .source.issue.number,actor: .actor.login}]'
```

## Versioned documentation and local sources

The following GitHub documentation was read on 2026-10-07 between 20:06 and 20:08 UTC. The living GitHub.com articles expose no immutable revision in these reads, so the access date and URL are the source timestamp. The REST timeline endpoint uses the selected `2022-11-28` API version.

- [Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) defines supported keywords, default-branch targeting, pre-merge linking, merge closure, and the different effect of a keyword in a commit message. [Documented] as read 2026-10-07.
- [Configuring commit squashing](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-squashing-for-pull-requests) defines the selectable PR title and body squash format. [Documented] as read 2026-10-07.
- [REST timeline events](https://docs.github.com/en/rest/issues/timeline?apiVersion=2022-11-28) defines the issue timeline endpoint. [Documented] at API version `2022-11-28`.
- [Using built-in Project automations](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations) defines event-driven Status changes. [Documented] as read 2026-10-07.
- `scripts/check-pr-body.sh` at repository head `d32e4f4` requires `^Refs: #[0-9]+` and does not inspect a closing line. [Schema] read 2026-10-07.
- `docs/src/content/docs/workflow/index.md` at `d32e4f4` lists the five required checks and merge policy. [Documented] read 2026-10-07.

## Observations and unavailable captures

[Observed] PR #80 currently lists three references, merged at 2026-09-27 00:11:18 UTC, and its squash commit `ee61cb0` retained the three `Refs:` lines. Issue #59 has a `cross-referenced` event from #80 at 23:20:57 UTC and a `closed` event at 00:11:25 UTC with no commit ID. No retained PR-body-at-merge capture or closure-operation record was found. Its closure mechanism is [untested].

[Observed] PR #196 currently describes a partial delivery, merged at 2026-09-27 13:48:09 UTC, and its squash commit `af9716f` contains a closing keyword directly before `#176` in a sentence about omission. Issue #176 has a `cross-referenced` event at 13:31:44 UTC, a `closed` event naming `af9716f` at 13:48:11 UTC, and a `reopened` event at 13:54:27 UTC. The current PR body is not a retained body-at-merge capture. The squash commit is a durable capture of the resulting default-branch message. Keyword-caused closure is a strong [inference] from the matching commit and GitHub documentation, without a parser trace.

[Observed] The #176 timeline has Project status-change events at 2026-09-27 04:43:33, 05:21:10, and 18:33:20 UTC. The #59 timeline has events at 2026-09-26 21:56:48 and 2026-09-27 18:26:57 UTC. The REST records lack old and new Status values and the workflow identity. There is no retained Project transition capture tying a linked PR to `In review`, so that outcome is [untested]. The current repository response reports default branch `main`, squash merge enabled, `squash_merge_commit_title: PR_TITLE`, and `squash_merge_commit_message: PR_BODY`. The current [ruleset](https://github.com/tbhb-dev/agent-orchestration-poc/rules/24053242) response reports the five required checks, strict current-branch policy, one approval, latest-push approval, resolved threads, and squash-only merge.

## Validator fixture execution

These commands ran against `scripts/check-pr-body.sh` through the pinned mise task on 2026-10-07. They are shell fixture checks, with no GitHub mutation.

```sh
mise run check:pr-body -- 'decision(workflow): record choice of PR closing links and issue closure' <<'EOF'
## What
Complete the issue.

## Evidence
A recorded example.

Closes #124
Refs: #124
EOF
```

[Verified] Exit 0, `PR body ok`. The completed issue can appear in both lines without changing the current validator.

```sh
mise run check:pr-body -- 'decision(workflow): record choice of PR closing links and issue closure' <<'EOF'
## What
This is a partial delivery and issue #124 stays open.

Refs: #124
EOF
```

[Verified] Exit 0, `PR body ok`.

```sh
mise run check:pr-body -- 'decision(workflow): record choice of PR closing links and issue closure' <<'EOF'
## What
Complete the issue.

Closes #124
EOF
```

[Verified] Exit 1, `missing 'Refs: #<issue>' trailer`. The validator migration, if any, belongs to #84 rather than this decision PR.

## Validation

| Command | Exit | Result and limit |
| --- | ---: | --- |
| `mise run vale:sync` | 0 | Synced the pinned prose styles once in this worktree. |
| `mise run fmt` | 0 | No tracked files outside the four allowed paths changed. |
| `mise run docs:build` | 0 | Generated 58 pages, including decision 0014. Chromium launch was denied by a macOS Mach port sandbox error, so browser rendering was not verified locally. |
| `mise run docs:check-links`, first run | 1 | Eight invalid links were reported, including one `/workflow/` link in the new decision page. |
| `mise run docs:check-links`, after correcting the new link | 1 | Seven invalid links remain in seven unchanged files: `design/index.md`, `index.md`, `decisions/0007-github-event-monitor.md`, `project/coordinator-operations.md`, `project/history.md`, `project/plan-extraction.md`, and `workflow/tooling.md`. None is in the #124 changed paths. Chromium launch was denied again. |
| `mise run check`, first run | 123 | Vale found two wording alerts in decision 0014. Both were corrected. |
| `mise run check:vale` | 0 | Zero alerts in 208 files after the corrections. |
| `mise run check:mutation` | 0 | Go core killed 145 of 149 mutants, score 97.32%. Python core killed 8387 of 9292 mutants, score 90.26%. No production code changed in this PR. |
| `mise run check`, final run | 0 | All tasks passed. Python tests had 619 passed and 93 skipped in the default suite, and 712 passed in the coverage run. Core and shell coverage floors passed. |
| `mise exec -- gitleaks dir --no-banner --redact=100 --log-level error research/gates/pr-issue-linkage` | 0 | No finding in the research evidence directory. The commit hook also scanned the staged docs and notes. |

The remaining link-check failures and Chromium denial are local validation limits, not evidence that GitHub linkage or Project transitions work.
