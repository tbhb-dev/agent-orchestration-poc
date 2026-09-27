---
title: Generated coordinator state, 2026-09-26
description: Verbatim archive of the phase 2 coordinator rollover on 2026-09-26.
---

Generated state beside the historical prompt when incoming session `26834c4f-a585-4314-bb86-c1f6141aa9ee` started.

# Generated coordinator state

Generated 2026-09-26 22:31:36 EDT. Regenerate at takeover with `bash .holding/bin/handoff-state.sh`.

## Main

`8296340` docs(design): design a webhook-fed monitor for pull request state (#99)

Checks: check=success, docs=success, mutation=success

## Open pull requests

| PR | Branch | Draft | Reviewer verdict at head | Merge state | Refs |
| --- | --- | --- | --- | --- | --- |
| #122 | `research/104-data-analysis-stack` | false | none | dirty | #104  |
| #121 | `research/100-document-size-limits` | false | none | dirty | #100  |
| #119 | `docs/114-handoff-phase-2-rollover` | false | CHANGES_REQUESTED at head | behind | #114  |
| #115 | `feat/96-bus-relay` | false | CHANGES_REQUESTED at head | dirty | #96  |
| #113 | `process/83-review-process` | false | CHANGES_REQUESTED at older head | behind | #83  |
| #97 | `feat/28-registry-tmux` | false | APPROVED at head | dirty | #28  |
| #86 | `feat/27-agentctl` | true | none | dirty | #27  |

## Merged today

- #99 docs(design): design a webhook-fed monitor for pull request state (2026-09-27T02:25:35Z)
- #105 tooling(testing): gate branch and line coverage and raise the mutation floors (2026-09-27T02:17:09Z)
- #112 fix(tooling): resolve lodash-es alerts in Mermaid check (2026-09-27T02:03:44Z)
- #95 research(shell): add the shell-scripting conventions gate (2026-09-27T01:38:06Z)
- #81 tooling(workflow): add the commit trailer, ignore collision, and handoff checks (2026-09-27T00:56:42Z)
- #82 feat(bus): embed the NATS server in agentd with JetStream, per-group accounts, and per-agent credentials (2026-09-27T00:50:01Z)
- #85 tooling(workflow): add the review preflight, check waiter, closure audit, and docs brief template (2026-09-27T00:35:58Z)
- #80 tooling(testing): add property and mutation testing gates and strict typing everywhere (2026-09-27T00:11:18Z)
- #79 docs(handoff): refresh the coordinator handoff after phase 1 approval (2026-09-26T23:09:16Z)
- #76 tooling(gates): enforce the functional core boundary and add duplication, dead-code, and complexity gates (2026-09-26T22:56:47Z)
- #75 docs(checkpoint): add the phase 1 retro, report, devlog entry, and handoff (2026-09-26T22:37:21Z)
- #68 research(testing): property and mutation testing gate notes for Go and Python (2026-09-26T22:22:57Z)
- #65 tooling(python): switch type checking to strict pyrefly (2026-09-26T22:20:20Z)
- #67 research(tooling): duplicate-code, dead-code, and complexity gate notes (2026-09-26T22:19:01Z)
- #66 research(boundaries): compare the core and shell boundary tools for Go and Python (2026-09-26T22:14:18Z)
- #64 docs(workers): add AGENTS.md, CLAUDE.md, and the first docs pages (2026-09-26T22:05:15Z)
- #57 chore(skeleton): create the monorepo skeleton and the Go module (2026-09-26T21:49:40Z)
- #55 chore(docs): build the Astro Starlight site with Mermaid and the devlog (2026-09-26T21:48:51Z)
- #56 workflow(project): configure the Project fields and views and file the phase 2 and 3 issues (2026-09-26T21:48:16Z)
- #25 chore(ci): run the mise checks and the pull request rules in GitHub Actions (2026-09-26T21:44:34Z)
- #23 docs(research): Python 3.14, uv, ruff, and pytest gate notes (2026-09-26T21:41:30Z)
- #22 research(docs): record the Astro, Starlight 0.42, and starlight-blog gate (2026-09-26T21:38:55Z)
- #24 research(import): import the peering and session research folders with a manifest (2026-09-26T21:38:08Z)
- #21 chore(tooling): pin tools, configure linters, add prek hooks and the first mechanical checks (2026-09-26T21:33:59Z)
- #20 research(go): Go 1.27 conventions gate notes and versions (2026-09-26T21:29:28Z)
- #19 docs(retro): add the phase 0 retrospective and first devlog entry (2026-09-26T21:26:02Z)
- #2 docs: mark phase 0 approved in the coordinator handoff (2026-09-26T20:55:44Z)
- #1 docs: add the phase 0 plan, checkpoint report, and assessment evidence (2026-09-26T20:53:18Z)

## Open issues by Project status

- Backlog: #18, #29, #31, #32, #33, #34, #35, #36, #37, #38, #39, #40, #41, #42, #43, #44, #45, #46, #47, #48, #49, #50, #51, #52, #53, #54, #74, #114, #117, #118, #120, #123
- Done: #3, #4, #5, #6, #7, #8, #9, #10, #11, #12, #13, #14, #15, #16, #17, #26, #30, #58, #59, #60, #61, #62, #63, #69, #70, #71, #72, #73, #77, #78, #87, #98, #102
- In progress: #27, #28, #83, #84, #96, #100, #104
- Ready: #89, #88, #90, #91, #92, #93, #94, #101, #103, #106, #107, #108, #109, #110, #111, #116

## Running Codex runs

- process-83-review-process, running 14:16
- tooling-84-conventions-reference, running 20:09
- research-104-data-analysis-stack, running 20:08
- research-100-document-size-limits, running 20:06
- feat-96-bus-relay, running 12:33
- docs-114-handoff-phase-2-rollover, running 12:33
- feat-28-registry-tmux, running 10:11
- review-121, running 01:12
- review-122, running 01:10
- review-113, running 01:08
- review-issues-b, running 01:06

## Worktrees

- /Users/tony/Code/github.com/tbhb/agent-orchestration-poc [main]
- .worktrees/docs-114-handoff-phase-2-rollover [docs/114-handoff-phase-2-rollover]
- .worktrees/docs-98-github-event-monitor-design [docs/98-github-event-monitor-design]
- .worktrees/feat-26-embedded-nats [feat/26-embedded-nats]
- .worktrees/feat-27-agentctl [feat/27-agentctl]
- .worktrees/feat-28-registry-tmux [feat/28-registry-tmux]
- .worktrees/feat-96-bus-relay [feat/96-bus-relay]
- .worktrees/fix-102-lodash-es-alerts [fix/102-lodash-es-alerts]
- .worktrees/issue-author (detached
- .worktrees/issue-author-channel (detached
- .worktrees/issue-author-handoff (detached
- .worktrees/issue-author-obs (detached
- .worktrees/process-83-review-process [process/83-review-process]
- .worktrees/research-100-document-size-limits [research/100-document-size-limits]
- .worktrees/research-104-data-analysis-stack [research/104-data-analysis-stack]
- .worktrees/research-30-shell-conventions [research/30-shell-conventions]
- .worktrees/review-105 (detached
- .worktrees/review-112 (detached
- .worktrees/review-113 (detached
- .worktrees/review-115 (detached
- .worktrees/review-119 (detached
- .worktrees/review-121 (detached
- .worktrees/review-122 (detached
- .worktrees/review-80 (detached
- .worktrees/review-81 (detached
- .worktrees/review-82 (detached
- .worktrees/review-85 (detached
- .worktrees/review-95 (detached
- .worktrees/review-97 (detached
- .worktrees/review-99 (detached
- .worktrees/review-issues (detached
- .worktrees/review-issues-b (detached
- .worktrees/tooling-15-16-17-retro-checks [tooling/15-16-17-retro-checks]
- .worktrees/tooling-59-60-77-testing-and-strict [tooling/59-60-77-testing-and-strict]
- .worktrees/tooling-70-73-coordinator-preflight [tooling/70-73-coordinator-preflight]
- .worktrees/tooling-84-conventions-reference [tooling/84-conventions-reference]
- .worktrees/tooling-87-coverage-floors [tooling/87-coverage-floors]

## Infrastructure

- Funnel on: no
- Webhook receiver listening on 8787: yes
- Docs server on 4322: 200
- Merge train running: no
- Default gh account: tbhb
- Rulesets: all-branches 24056095 active, main 24053242 active
- Required checks on main: check, docs, pr-body, imported-research, mutation
