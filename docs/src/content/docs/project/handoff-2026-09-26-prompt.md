---
title: Coordinator rollover prompt, 2026-09-26
description: Verbatim archive of the phase 2 coordinator rollover on 2026-09-26.
---

The historical prompt used to start incoming session `26834c4f-a585-4314-bb86-c1f6141aa9ee`; it supersedes the draft handoff page in this pull request.

# Coordinator handoff, live copy

Outgoing session `a8fde4b6-9f82-4188-b1f5-ccc20413cf6f`, 2026-09-26 about 22:35 America/New_York. The operator asked for an immediate rollover and is holding new items until the new session starts. Ask for them first.

This file has three parts. Part 1 is the outgoing coordinator's own addendum and wins where the parts disagree. Part 2 is generated state in `2026-09-26-a8fde4b6-state.md` beside this file. Regenerate it before acting with `bash .holding/bin/handoff-state.sh`. Part 3 is the Codex-written handoff page as it stood in its worktree, mid fix round and not yet approved. Its reviewed version is PR #119.

## Part 1: addendum from the outgoing coordinator

### First five minutes

1. Ask the operator for the items they have been holding.
2. Read the memory index `MEMORY.md`, then `coordinator-is-orchestrator-only.md`, `coordinator-heartbeat.md`, `reviews-as-pr-reviews.md`, `issue-refinement-required.md`, and `phase-2-in-progress.md`. Later updates inside a note win over earlier ones.
3. Run `bash .holding/bin/handoff-state.sh` once and work from its output. Do not poll GitHub by hand.
4. Before creating anything, call CronList and check for a running Monitor. Session cron jobs survive `/clear`: the outgoing session began after a `/clear` and inherited a heartbeat from the session before it, which ran as a costly duplicate for two hours. If this session was started with `/clear`, the hourly heartbeat `1c9f4837` and the digest Monitor may still be live. Keep one of each and delete any extra.
5. Arm Monitor on `bash /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/bin/coordinator-digest.sh 120` with a 30 minute timeout, and re-arm on expiry. Create one hourly cron heartbeat as a backstop. Never run two.
6. Restart the merge train, which the outgoing session paused: `nohup bash .holding/bin/merge-train.sh <scratchpad>/gh-as-reviewer 75 >/dev/null 2>&1 &`. Finish #119 first if it is still open.
7. Run `echo '{}' | bash .holding/bin/pull-transcripts.sh` unless the session hooks did it. Check `.holding/pull.log`.

### Rules the operator set this session

- The coordinator is an orchestrator only. It keeps decisions, arbitration, dispatch order, merges, and the conversation with the operator. It delegates everything else, including writing issues and briefs, research, reading long output, and browser work. Aim for one tool call per wake. Roll over well before 300 thousand tokens. This session reached 688 thousand, which was far too late.
- Every issue goes through a refinement review by the reviewer account before dispatch. Backlog means unrefined and Ready means approved. Verdicts carry a digest of the body. Three verdicts that request changes stop an item until the coordinator posts a comment starting `Arbitration:`.
- Reviews are real pull request reviews posted as `tbhbbot` through the fail-closed wrapper. Implementers reply in threads as `tbhb`. Only the reviewer resolves threads. The default `gh` account must stay `tbhb`.
- Rulesets: `main` requires one approval, stale dismissal, resolved conversations, approval of the last push, five checks (check, docs, pr-body, imported-research, mutation), and an up-to-date branch. `all-branches` blocks force pushes everywhere, so branches update by merge and never by rebase. A clean update keeps an approval. A hand-resolved merge dismisses it.
- The coordinator merges product code that handles credentials. The operator merges changes to this project's own credentials, security policy, egress, and host setup.
- Pull request size: target 400 changed lines of code, limit 800, counted with `scc`, excluding lockfiles, generated files, fixtures, and evidence. Oversized work found mid-build is a candidate for a stack (#106).
- Documents get limits in words and tokens (#100, #101). The operator will provide API keys for the three token counting APIs through 1Password and CI secrets.
- Data analysis is done in notebooks, Quarto first, with linted prose, DuckDB, Polars, and pyarrow considered, one visualization library, every number, claim, and chart double checked, and a summary on the docs site (#104).
- Observability is a local Grafana, Alloy, Tempo, Loki, and Mimir stack run as native processes through mise, with data under a git-ignored directory in the clone (#110). Then instrument everything, with conventions and backfill (#116). Toolchain timings are recorded from now on (#109, #111).
- Virtual machines and images may be created whenever needed, with rigorous utilization profiling.
- The host tmux backend is bootstrap scaffolding held to a lower bar. The product runs harnesses under shpool inside Apple Containers.
- Any work on session wake, messaging, harness behavior, or the bus starts from the imported research under `research/imported/` and cites it.
- The handoff moves to this local form: written by Codex, reviewed, state generated by script, archived to the docs site after takeover. An author run was drafting that issue at rollover.
- Codex concurrency is about six, with reviewers allowed to burst. Watch for rate limits. GitHub GraphQL ran out once this session, so use REST and never `--watch`.

### Dispatch queue, in order

Ready and not dispatched: #109 timing capture and #110 stack research first. After #84 merges: #89, #90, #88, #94 in parallel, then #92 and #93, then #91. Analysis track: #104 (PR #122), then #107, then #108 and the #100 measurements, then #103 the transcript retro with the coordinator self-evaluation. Then #116 after #110, #111 after #109 and #116, #106 after #113 and #84, #101 after #100, #84, #88, and #107. In refinement: #117 and #118 (coordinator wake and event channel), the merge automation item split from #118, and the handoff procedure item. Not yet filed: the implementation items listed at the end of the monitor design merged in #99. Have an author run file them, starting with the coordinator-owned loopback HTTP wait.

### In flight at rollover

- #119 handoff refresh: changes requested, fix round running. After takeover it becomes the archive entry.
- #115 bus relay for #96: changes requested on three findings, fix round running. Top priority. #86 (`agentctl`, draft) and #29 wait on it.
- #97 registry and tmux for #28: approved, then conflicted with main. A run is resolving conflicts and meeting the new floors. It needs a re-review after a hand-resolved merge. Registration must be joined with the relay after both land. The real spawn of one worker per harness is the coordinator's job, outside the sandbox.
- #113 review process for #83: fix round two pushed, re-review running.
- #121 (#100) and #122 (#104): first reviews running. Both conflict with main.
- #84 conventions reference: worker running.
- Background chains started with nohup keep running after this session: a refinement round that starts when the author runs finish, and the webhook capture probe on port 8787.

### Infrastructure

- Tailscale Funnel: `https://usdholt05.ibex-paradise.ts.net/hooks/github` proxies to `http://127.0.0.1:8787/hooks/github`. Check with `tailscale funnel status`.
- GitHub App credentials: 1Password, vault `tbhb.dev`, item `github-app-tbhb-monitor`, fields `webhook_secret`, `private_key`, `app_id`. Never read them until a receiver needs them.
- The capture probe does not verify signatures. It writes to `.holding/<date>/webhooks/`, so restart it with a new dated directory each day: `nohup python3 <old scratchpad>/webhook-capture.py <dir> &`.
- Codex launch: `codex exec -s workspace-write -c 'approval_policy="never"' -c sandbox_workspace_write.network_access=true --add-dir <repo>/.git` plus the writable roots in the operator's `.codex/config.toml`, which the launcher reads.

### Scripts

Durable, in `.holding/bin/`: `handoff-state.sh`, `coordinator-digest.sh`, `merge-ready.sh`, `merge-train.sh`, `pull-transcripts.sh`.

In the outgoing scratchpad, which is temporary storage, so copy them into `.holding/bin/` early: `launch-codex.sh`, `dispatch-issue.sh`, `review-as-bot.sh`, `fix-pr.sh`, `gh-as-reviewer`, `st.sh`, `ratecheck.sh`, `webhook-capture.py`, and `briefs/` with the issue, fix, reviewer, and issue review templates. They hold the old scratchpad path inside them.

### Gotchas from this session

- zsh does not split unquoted variables into words and aborts a command when a glob matches nothing. Two coordinator mistakes came from this, one of which wrote the wrong body to an issue. Use bash scripts and explicit arguments.
- `gh api --jq` takes no `--arg`. Pipe to `jq`.
- A brief that tells a worker to wait for another pull request makes it idle and hold a slot. Briefs say open the pull request and exit.
- A pull request is reviewable when it opens, not when its worker exits.
- A pull request that conflicts with main gets no CI runs.
- Editing an approved issue makes its approval stale. Put exceptions in a coordinator comment on the pull request.
- CI sometimes fails on a download error from the Python build. Rerun the failed job.

## Part 3: Codex-written handoff page, unapproved working copy

Copied from the worktree at 22:32:50. Frontmatter removed.


Snapshot: 2026-09-26 22:31 America/New_York (2026-09-27 02:31 UTC). Outgoing coordinator session: `a8fde4b6-9f82-4188-b1f5-ccc20413cf6f`. Start the new Fable session with `@HANDOFF.md`. **Verify live state before acting.** This page records the roster at the snapshot time.

### Phase 2 state

Embedded NATS, testing gates, retro checks, the shell gate, coordinator preflight, coverage floors, and the Monitor design merged in [#80](https://github.com/tbhb/agent-orchestration-poc/pull/80), [#81](https://github.com/tbhb/agent-orchestration-poc/pull/81), [#82](https://github.com/tbhb/agent-orchestration-poc/pull/82), [#85](https://github.com/tbhb/agent-orchestration-poc/pull/85), [#95](https://github.com/tbhb/agent-orchestration-poc/pull/95), [#105](https://github.com/tbhb/agent-orchestration-poc/pull/105), and [#99](https://github.com/tbhb/agent-orchestration-poc/pull/99). The bus relay, `agentctl`, and host provisioner remain in review or draft. The bus roster and status bucket are not yet usable.

**REST evidence:** the refresh at 2026-09-27 02:31 UTC found seven open PRs and 55 open issues, excluding PRs from the issues response. [PR #112](https://github.com/tbhb/agent-orchestration-poc/pull/112) merged at 02:03:44 UTC, [PR #105](https://github.com/tbhb/agent-orchestration-poc/pull/105) at 02:17:09 UTC, and [PR #99](https://github.com/tbhb/agent-orchestration-poc/pull/99) at 02:25:35 UTC. Issues #117, #118, #120, and #123 opened after the earlier snapshot. The refresh used `gh api 'repos/tbhb/agent-orchestration-poc/pulls?state=open&per_page=100'` and `gh api 'repos/tbhb/agent-orchestration-poc/issues?state=open&per_page=100'`. The issue count filters out entries with a `pull_request` field. PR details and reviews and `git worktree list --porcelain` were read immediately afterward. The ruleset statement below comes from the earlier 02:02 UTC REST read. Requery before merge or dispatch.

| Open PR | Branch and worktree under `.worktrees/` | Review at snapshot | Waits on |
| --- | --- | --- | --- |
| [#122](https://github.com/tbhb/agent-orchestration-poc/pull/122), data analysis research | `research/104-data-analysis-stack`, `research-104-data-analysis-stack` | No submitted review | Reviewer and required checks. |
| [#121](https://github.com/tbhb/agent-orchestration-poc/pull/121), document size research | `research/100-document-size-limits`, `research-100-document-size-limits` | No submitted review | Reviewer and required checks. |
| [#119](https://github.com/tbhb/agent-orchestration-poc/pull/119), this handoff | `docs/114-handoff-phase-2-rollover`, `docs-114-handoff-phase-2-rollover` | `tbhbbot` requested changes | Fix the heartbeat and delegation findings, re-review, then merge. |
| [#115](https://github.com/tbhb/agent-orchestration-poc/pull/115), relay | `feat/96-bus-relay`, `feat-96-bus-relay` | `tbhbbot` requested changes | Fix review findings, re-review and checks, then #86 integration. |
| [#113](https://github.com/tbhb/agent-orchestration-poc/pull/113), review process | `process/83-review-process`, `process-83-review-process` | `tbhbbot` requested changes | Fix scope and review findings, then re-review. |
| [#97](https://github.com/tbhb/agent-orchestration-poc/pull/97), host provisioner | `feat/28-registry-tmux`, `feat-28-registry-tmux` | `tbhbbot` approved after fixes | Real harness acceptance, checks, then merge. |
| [#86](https://github.com/tbhb/agent-orchestration-poc/pull/86), `agentctl` | `feat/27-agentctl`, `feat-27-agentctl` | Draft, no submitted review | #115 relay lands and CLI integration passes. |

The handoff itself is in PR #119. A clean update from main can preserve approval, while a changed PR diff requires another approval. Check effective review and check state each time.

### Open issues by status

REST found 55 open issues at 02:31 UTC. These groups describe observable work state and dependencies, not the Project 9 Status field, which the REST query does not expose. Verify the Project field separately before dispatch.

| Snapshot status | Open issues |
| --- | --- |
| Open PR or draft | [#27](https://github.com/tbhb/agent-orchestration-poc/issues/27), [#28](https://github.com/tbhb/agent-orchestration-poc/issues/28), [#83](https://github.com/tbhb/agent-orchestration-poc/issues/83), [#96](https://github.com/tbhb/agent-orchestration-poc/issues/96), [#100](https://github.com/tbhb/agent-orchestration-poc/issues/100), [#104](https://github.com/tbhb/agent-orchestration-poc/issues/104). |
| Rollover in this branch | [#114](https://github.com/tbhb/agent-orchestration-poc/issues/114). |
| Phase 2 queue, dependencies, or refinement | #18, #29, #31, #32, #33, #74, #84, #88, #89, #90, #91, #92, #93, #94, #101, #103, #106, #107, #108, #109, #110, #111, #116, #117, #118, #120, #123. #84 reached arbitration after three changes-needed verdicts. #88 through #93 depend on its contract. #101 and #110 need operator input. #117 and #118 cover wake research and the coordinator event channel. #120 covers automated merge passes, and #123 covers handoff review and archiving. |
| Phase 3 backlog | #34, #35, #36, #37, #38, #39, #40, #41, #42, #43, #44, #45, #46, #47, #48, #49, #50, #51, #52, #53, #54. |

### Operator decisions and process

The decisions below were made on 2026-09-26. The coordinator's local memory directory, beginning with `MEMORY.md` and `phase-2-in-progress.md`, holds the dated raw notes. Later updates supersede earlier ones. The [plan](/project/plan/) holds durable policy.

| Decision | Current instruction |
| --- | --- |
| Architecture and gates | “A guiding architectural principle that I want followed strictly here is functional core/imperative shell.” Pure decisions and transformations live in core, I/O in a thin shell. Use boundary, property, mutation, coverage, duplicate, dead-code, and complexity checks. Python typing is strict everywhere. |
| Coordinator-only role and usage | The operator's 2026-09-26 goal is a streamlined project orchestrator “delegating everything else.” The coordinator retains decisions, arbitration, dispatch order, merge authority, and conversation with the operator. Delegate issue and brief authoring to Codex instead of writing inline; delegate coding, research, first review, long-document and log reading, browser work, and routine investigation. Run mechanical GitHub work through compact scripts and seek decision-relevant summaries. Use `gpt-6-sol` high for code and `gpt-6-astra` medium for reviews and design, with Sonnet 5 cross-checks for bus and security. Later usage showed 73% above 150 thousand context tokens, so roll over before 300 thousand. |
| Concurrency | Codex may run about six jobs. Plan four coding slots, two review slots, and one docs or research slot. Reviewers may burst. Watch rate-limit logs. Earlier three-job guidance is superseded. |
| Issue refinement | “All issues should go through a refinement review and approval.” Backlog means unrefined, Ready requires a newer `Issue review: ready` verdict from `tbhbbot`. This time-bound handoff was dispatched without that review. |
| PR review | Reviews are real PR reviews by `tbhbbot`, with discussion in threads and a required approval. Keep default `gh` identity as `tbhb`. Use the fail-closed reviewer wrapper. Reviewer resolves threads. Limit to three review rounds before coordinator arbitration. |
| Merge authority | Coordinator merges PRs for the product, including credential handling. Operator merges changes to this project's credentials or security policy, egress, host setup, and installations outside the repository. Workers do not merge. |
| PR size and history | Target 400 changed code lines, limit 800, excluding lockfiles, generated files, fixtures, and evidence. Consider stacked PRs if a split appears mid-build. Never rebase or force push a pushed branch. The host tmux backend is bootstrap scaffolding. |
| Data and observability | “Choose a data viz library and stick to it.” Double-check every number, claim, and chart, use a linted notebook, and publish a docs summary. Research a local Grafana LGTM stack and track check duration. Keep raw transcripts out of Git. |
| Document size | Set page budgets in words and tokens after the research in #100, then add the check in #101. Token counting uses the Anthropic, OpenAI, and Gemini APIs with credentials held in 1Password and CI secrets. Keep the values out of briefs, logs, and commits. |
| Instrumentation | The operator requires telemetry for each new component and tool, plus planned backfill for existing code. Use consistent metric, trace, and log conventions after #110 establishes the local stack. Issue #116 records the conventions work. |
| VMs and Project views | The operator approved creating VMs and images as needed and required careful measurement of resource use. The coordinator may set Project views. The Phase, Ready, Blocked, and Experiments views were configured in this session. |
| Repo and writing | In-repo hooks and checks are authorized. Codex writes docs and devlog. Commit useful evidence after a secret scan. No attribution or co-author trailers. Permission requests to the operator use AskUserQuestion. |

**Verified rulesets:** REST reads of `rulesets/24053242` and `rulesets/24056095` after 02:02 UTC found both active with no bypass actors. `main` requires a PR, squash merge, one approval, stale dismissal, last-push approval, resolved threads, an up-to-date branch, and successful `check`, `docs`, `pr-body`, `imported-research`, and `mutation` checks. It blocks deletion and force push. `all-branches` blocks force push on every branch. Update branches by merging main, then inspect whether approval remains current.

### Infrastructure to verify or restart

| Component | Location and action |
| --- | --- |
| Coordinator wake | The operator's 22:20 update supersedes the 14-minute cron. Arm Monitor on the main checkout's `.holding/bin/coordinator-digest.sh 120`, re-arm at its 30-minute expiry, and keep one approximately hourly cron heartbeat as a fallback. Never run two fallback heartbeats. The digest reports changed worker, review, PR, check, or job state in compact output. The channel in #118 is still unbuilt. #117 must verify wake cost and cache retention before treating either as established. |
| Merge train | Check whether the main checkout's `.holding/bin/merge-train.sh` is already running, then run it in the background with the outgoing scratchpad's `gh-as-reviewer` wrapper and an optional duration. It calls `.holding/bin/merge-ready.sh` and writes `.holding/merge-train.log`. Inspect the scripts and their authority before reuse. The coordinator retains merge decisions. |
| Docs daemon | Check port 4322. Restart the Astro daemon after merges adding pages, then request the page before sharing it. |
| Funnel | Check `tailscale funnel status` for `https://usdholt05.ibex-paradise.ts.net/hooks/github`, forwarding to `127.0.0.1:8787/hooks/github`. Credentials are in the `tbhb.dev` 1Password item `github-app-tbhb-monitor`, with no values in this page. |
| Webhook capture | The temporary `webhook-capture.py` probe in the outgoing scratchpad writes into `.holding/2026-09-26/webhooks`. Its process ends with the session, so verify the receiver and restart it under the coordinator's existing authority. Captured data is unverified and remains local. |
| Holding area | Main checkout `.holding/` is mode 700 and locally ignored. It holds dated Claude and Codex transcripts and webhook payloads. Do not commit raw inputs. |
| Transcript pull | Main checkout `.holding/bin/pull-transcripts.sh` copies session material into the dated holding area. Verify `SessionStart` and `SessionEnd` hooks in local Claude settings. If absent, run the script manually at start and rollover with empty JSON on stdin. |
| Codex launcher | Outgoing scratchpad `launch-codex.sh` uses `-s workspace-write`, `approval_policy="never"`, network access, the worktree, common repository `.git`, and extra `--add-dir` roots from the operator's local `.codex/config.toml`. Confirm those roots before dispatch. |

The outgoing scratchpad is `/private/tmp/claude-501/-Users-tony-Code-github-com-tbhb-agent-orchestration-poc/a8fde4b6-9f82-4188-b1f5-ccc20413cf6f/scratchpad/`. Its `briefs/` directory contains issue, coding, fix, review, and reviewer templates. Inspect these scripts before reuse:

- `chain-channel.sh` waits for the channel issue author, then launches its follow-up author run.
- `chain-obs.sh` runs observability authoring followed by refinement.
- `dispatch-issue.sh` creates a worktree and brief from a refined issue.
- `fix-pr.sh` renders and launches a numbered PR fix round.
- `gh-as-reviewer` runs GitHub commands with a checked reviewer identity.
- `launch-codex.sh` starts a bounded detached Codex run with writable roots.
- `ratecheck.sh` summarizes Codex rate and API failures from logs.
- `review-as-bot.sh` checks out a PR head and starts a reviewer run.
- `review-codex.sh` starts a local `codex exec review` pass.
- `set-status.sh` updates Project status and worker fields by issue.
- `st.sh` sets Project status by issue URL.
- `webhook-capture.py` captures temporary webhook deliveries in the local holding area.

The digest and merge scripts are temporary local prototypes under the main checkout's `.holding/bin/`, separate from the still-unbuilt coordinator event channel in #118. Their source and log are outside this PR and are not durable repository infrastructure.

### Gotchas

- A worker brief that says to wait for an upstream merge can hold a Codex slot indefinitely. Have workers open the PR, report, and exit, then dispatch a short follow-up.
- Agent JetStream API grants allowed caller-chosen reply subjects to bypass attribution. #82 removed direct API access and #96 adds an authenticated relay. Do not widen agent grants to make #86 pass.
- `gh pr checks --watch` returned before a check concluded, and GraphQL polling exhausted the shared 5,000-point budget. Poll REST check runs no more than once a minute and require concluded success.
- The reviewer inline token form can fall back to the implementer account if token lookup fails. Use the fail-closed wrapper and never switch the default `gh` account.
- A clean update from main preserved a bot approval, while a changed PR diff dismisses it. Verify the latest review after each update.
- `gh stack` uses force push and conflicts with `all-branches`. Merge branches for updates. A squash-merged lower PR may leave upper PR conflicts.
- A linked Codex worktree needs the absolute common `.git` writable root. Project `.codex/config.toml` from the main checkout is not loaded in worktrees.
- `zsh` does not word-split shell variables. Use bash scripts or explicit argument arrays.
- The docs daemon may miss new pages after a pull. Sandboxed Chromium may deny a Mach port, so use the CI docs conclusion for rendering and links.
- The temporary webhook probe reached its first 1,000-file cap and refused deliveries. Its current cap is 40,000, and captured webhook data must stay in `.holding/`.
- `crontab -l` returned `operation not permitted`, `tailscale` was unavailable on this worker's PATH, and a local port 4322 probe returned no HTTP response. These observations apply only to this worktree. The coordinator must check its session cron, funnel, and daemon directly.

### Next three actions

1. Verify REST PR, issue, review, ruleset, and check state. Arm Monitor on `.holding/bin/coordinator-digest.sh 120`, re-arm after 30 minutes, check the background merge train, and retain one approximately hourly fallback heartbeat. Inspect the docs daemon, funnel, capture probe, holding area, and transcript hooks. Report discrepancies before dispatch.
2. Address #113 and #119 review findings and #97 real harness acceptance. Review new research PRs #121 and #122. The coordinator retains merge authority while delegating routine checks and issue or brief writing.
3. Address #115 review findings with a bus and security cross-check. Once the relay is approved and merged, resume #86 against it, then proceed with #29, #31 through #33, and the refined workflow queue in dependency order. Use #117, #118, and #120 to validate and replace the temporary wake and merge prototypes.

### Verify before acting

Run `git status`, `git worktree list`, REST queries for open PRs and issues, reviews, check runs, and rulesets, then inspect Project 9 status separately. Compare PR heads and outgoing scratchpad logs with this snapshot. A worktree or log is not proof of a live worker. Read memory beginning with `MEMORY.md` and `phase-2-in-progress.md`, using later updates when they conflict. Resume `claude --resume a8fde4b6-9f82-4188-b1f5-ccc20413cf6f` only if durable records cannot recover necessary context.
