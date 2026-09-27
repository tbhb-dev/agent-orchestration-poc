# GitHub issue relationship evidence

## Sources and environment

Read on 2026-09-27. `github/docs` commit `18945a31a4f2d97beb6c5c1a7479102e23c25727` was sparse-cloned at `/tmp/github-docs-125`, and `github/rest-api-description` commit `c6721f32a17a71397ae46be21be90d7f1a173b6e` was sparse-cloned at `/tmp/github-rest-api-description-125`. The API file was `descriptions/api.github.com/api.github.com.2026-03-10.json`. Its `paths` section includes both relationship families, and its changelog was read for the version change. The live API selected `2026-03-10` from the explicit header. The `gh` token value was neither displayed nor retained.

## Read-only REST commands and responses

All paths below use the `repos/tbhb/agent-orchestration-poc` prefix. Each direct command used `gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' '<path>' --jq '<filter>'`. The shell exit codes refer to the direct command, not a diagnostic pipeline. The retained fields omit issue bodies and account metadata.

| Path | Filter | HTTP and exit | Selected body | Date UTC | `X-Ratelimit-Remaining` |
| --- | --- | --- | --- | --- | --- |
| `/issues/109/sub_issues?per_page=100` | `[.[] \| {id,number,state}]` | `200`, `0` | `[]` | 04:20:37 | 4943 |
| `/issues/110/parent` | `{id,number,state}` | `404`, `1` | `No parent issue found` | 04:20:37 | 4944 |
| `/issues/111/dependencies/blocked_by?per_page=100` | `[.[] \| {id,number,state}]` | `200`, `0` | `[]` | 04:20:37 | 4942 |
| `/issues/110/dependencies/blocking?per_page=100` | `[.[] \| {id,number,state}]` | `200`, `0` | `[]` | 04:20:37 | 4803 |
| `/issues/125/dependencies/blocked_by?per_page=100` | `[.[] \| {id,number,state}]` | `200`, `0` | `[]` | 04:20:37 | 4941 |
| `/issues/109/sub_issues/summary` | `.` | `404`, `1` | `Not Found` | 04:20:37 | header absent |
| `/issues/100/dependencies/blocked_by?per_page=100` | `[.[] \| {id,number,state}]` | `200`, `0` | `[]` | 04:24:26 | 4919 |
| `/issues/104/dependencies/blocked_by?per_page=100` | `[.[] \| {id,number,state}]` | `200`, `0` | `[]` | 04:24:26 | 4918 |
| `/issues/110/sub_issues?per_page=100` | `[.[] \| {id,number,state}]` | `200`, `0` | `[]` | 04:24:26 | 4920 |
| `/issues/116/parent` | `{id,number,state}` | `404`, `1` | `No parent issue found` | 04:24:26 | 4921 |

These are the exact direct invocations. The four 04:24:26 requests were also rerun directly at 04:31:51 to confirm their `gh` exit codes. The reruns returned the same bodies and statuses, with remaining counts 4880, 4879, 4877, and 4878 in table order.

```sh
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/109/sub_issues?per_page=100' --jq '[.[] | {id,number,state}]'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/110/parent' --jq '{id,number,state}'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/111/dependencies/blocked_by?per_page=100' --jq '[.[] | {id,number,state}]'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/110/dependencies/blocking?per_page=100' --jq '[.[] | {id,number,state}]'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/125/dependencies/blocked_by?per_page=100' --jq '[.[] | {id,number,state}]'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/109/sub_issues/summary' --jq '.'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/100/dependencies/blocked_by?per_page=100' --jq '[.[] | {id,number,state}]'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/104/dependencies/blocked_by?per_page=100' --jq '[.[] | {id,number,state}]'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/110/sub_issues?per_page=100' --jq '[.[] | {id,number,state}]'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/116/parent' --jq '{id,number,state}'
```

All successful responses reported `X-Ratelimit-Limit: 5000`, `X-Ratelimit-Resource: core`, and `X-Github-Api-Version-Selected: 2026-03-10`. The first five had `X-Ratelimit-Reset: 1790486105`. The second set had the same reset. The first set's `X-Ratelimit-Used` values were 57, 56, 58, 197, and 59 in table order. The second set's values were 81, 82, 80, and 79. These values are response snapshots and reflect other concurrent API traffic. Ten listed probes and four reruns made fourteen requests. Earlier issue, PR, comment, and source reads were additional requests and are not included in that fourteen-request count.

The `404` from `/parent` was a targeted observation for children with no parent. The `/sub_issues/summary` probe was an unsupported path, so it is not used as a progress read. No GraphQL polling was used. REST cannot read the current Project board's rendered parent or progress fields.

## Direction check after review

[Observed] #104's Dependencies and paths section, read with `gh api repos/tbhb/agent-orchestration-poc/issues/104 --jq '{number,body,updated_at}'`, says this research precedes #107; its `updated_at` was `2026-09-27T02:44:42Z`. The earlier `/issues/104/dependencies/blocked_by` read tested whether #104 had a blocker, so it could not support an inference about #104 blocking #107. [Observed] The following direction-matched reads at `2026-09-27T04:46:35Z` both returned HTTP `200`, exit `0`, and `[]` under API version `2026-03-10`:

| Path | `X-Ratelimit-Remaining` | `X-Ratelimit-Used` | `X-Ratelimit-Reset` |
| --- | --- | --- | --- |
| `/issues/104/dependencies/blocking?per_page=100` | 4710 | 290 | 1790487275 |
| `/issues/107/dependencies/blocked_by?per_page=100` | 4952 | 48 | 1790487266 |

```sh
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/104/dependencies/blocking?per_page=100' --jq '[.[] | {id,number,state}]'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/107/dependencies/blocked_by?per_page=100' --jq '[.[] | {id,number,state}]'
```

Both responses reported `X-Ratelimit-Limit: 5000`, `X-Ratelimit-Resource: core`, and `X-Github-Api-Version-Selected: 2026-03-10`; neither had a next-page link. These are two additional relationship requests beyond the fourteen counted above. [Inference] The present body declaration and native edges disagree in the direction #104 to #107. The coordinator's account of the earlier dispatch and arbitration is historical context, not an outcome measured by these reads.

## UI and live trial

The UI attempt used `cua.createBrowserTab('chrome', 'https://github.com/users/tbhb/projects/9', {sessionName:'🔎 Issue 125 research'})` and then `cua.createBrowserTab('iab', 'https://github.com/users/tbhb/projects/9', {visible:true})`. Both returned `Browser is not available`. No screenshot or structured Project 9 observation exists. Project 9 field visibility, grouping, filter, progress, and dependency icon are untested.

No coordinator comment supplied exact parent and child numbers at the time of the read. Before snapshot: not captured for a selected trial. After snapshot: not applicable. Rollback snapshot: not applicable. Restoration: untested because no link was changed. The following commands are a procedure, not observed results. Replace `PARENT`, `CHILD`, and `CHILD_ID` only after the coordinator's selection, and record every exit code and rate-limit header.

```sh
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/PARENT/sub_issues?per_page=100' --jq '[.[] | {id,number,state}]'
gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/CHILD/parent' --jq '{id,number,state}'
gh api -i -X POST -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/PARENT/sub_issues' -F sub_issue_id=CHILD_ID --jq '{id,number,state}'
gh api -i -X DELETE -H 'X-GitHub-Api-Version: 2026-03-10' 'repos/tbhb/agent-orchestration-poc/issues/PARENT/sub_issue' -F sub_issue_id=CHILD_ID --jq '{id,number,state}'
```

Repeat the first two GETs after adding and after removing, following every `Link: rel="next"`. Compare the restored snapshots with the before snapshots by sorted issue ID and number. Stop on a pre-existing parent, incomplete read, unexpected link, or failed restoration, and report the discrepancy. Do not edit bodies, labels, Project fields, or issue state.

## Validation

`mise run vale:sync` exited `0` at setup. `mise run fmt` exited `0` and changed no unrelated tracked path. `mise run docs:build` exited `0` and generated `/decisions/0015-sub-issues/`. `mise run docs:check-links` exited `1`. Its five reported broken links were in unchanged `index.md`, `decisions/0007-github-event-monitor.md`, `design/index.md`, `project/history.md`, and `workflow/tooling.md`. It reported no link in the new decision page. The build also logged Chromium Mach registration `Permission denied (1100)` under this sandbox, then generated the site. These are observed local limits, not a passing link check.

The first `mise run check` exited `123` because Vale reported seven alerts in the new decision and workflow text. Those sentences were revised. `mise run check:vale` then exited `0` with zero alerts. The second `mise run check` exited `0`, with Python core line and branch coverage 100.00% and 94.00%, and Go core statement and branch coverage 96.43% and 94.74%.

`mise run check:mutation` exited `0`. Go core mutation efficacy was 97.32% with 145 killed of 149, and Python core scored 97.22% with 454 killed of 467. This PR changed documentation and evidence only, so these scores cover the existing core.

After the revisions, `mise run docs:build`, `mise run check:rumdl`, `mise run check:guard-markdown`, `mise run check:vale`, and `mise run build` each exited `0`. The final `mise run docs:check-links` again exited `1` on the same five unchanged-page links, with no new-page link reported. The browser launch denial also recurred. No sandbox permission was changed.

For the direction correction above, `mise run fmt`, `git diff --check`, `mise run check`, `mise run check:vale`, `mise run check:mutation`, `mise run build`, and `mise run docs:build` exited `0`. The aggregate check took 372.33 seconds, with Python core lines and branches at 100.00% and 94.00%, and Go core statements and branches at 96.43% and 94.74%. Mutation scored 97.32% for Go core and 97.22% for Python core. `mise run docs:check-links` exited `1` on the same five links in unchanged pages listed above, and the same Chromium Mach registration denial occurred. The link checker reported no link in a file changed by this correction.
