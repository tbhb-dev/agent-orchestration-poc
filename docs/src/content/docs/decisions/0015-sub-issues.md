---
title: Issue hierarchy and dependencies in Project 9
description: Proposed use of sub-issues for grouping and native blocked-by links for dispatch dependencies.
---

## Status

Proposed on 2026-09-27 for [issue #125](https://github.com/tbhb/agent-orchestration-poc/issues/125). The live sub-issue trial and Project 9 UI observation await coordinator-selected issue IDs and an available browser. Dependency enforcement belongs to [#158](https://github.com/tbhb/agent-orchestration-poc/issues/158).

## Context

[Observed] Issue bodies name work that must precede #111 and #100, but read-only REST probes found empty native blocker lists for the sampled issues. A script cannot treat those lists as complete until body declarations and native records agree. The [evidence record](https://github.com/tbhb/agent-orchestration-poc/blob/research/125-sub-issues-and-dependencies/research/gates/github-sub-issues/evidence.md) records the paths and responses.

[Documented] GitHub offers separate REST families for [sub-issues](https://docs.github.com/en/rest/issues/sub-issues) and [issue dependencies](https://docs.github.com/en/rest/issues/issue-dependencies). Its [Project field guide](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-parent-issue-and-sub-issue-progress-fields) describes parent grouping, filtering, and child progress, while its [dependency guide](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies) describes a blocked icon on boards. Project 9's actual settings remain untested.

## Decision

[Inference] Use native blocked-by edges as the machine-readable record of execution dependencies. Require a matching numbered declaration in the issue's Dependencies and paths section. Refinement compares both directions and all pages of REST results with the declaration. Unknown, missing, or conflicting data fails closed. [#158](https://github.com/tbhb/agent-orchestration-poc/issues/158) adds parity checks and dispatch blocking to [#90](https://github.com/tbhb/agent-orchestration-poc/issues/90)'s preflight, including its specified override rule.

[Inference] Limit parent-child links to grouping related work if the reversible Project 9 trial confirms useful display and complete rollback. A parent summarizes a group. Each executable child retains one issue, fresh review, separate dependency gate, branch, PR, and the closing-link rule selected by [#124](https://github.com/tbhb/agent-orchestration-poc/issues/124). Parent membership alone never authorizes dispatch or closure. Keep #116 blocked by #110 and #111 blocked by #109, #110, and #116 as separate edges when recorded.

## Consequences

The coordinator must select exact trial IDs before live linking. The worker first snapshots the original links, then adds only selected links and captures Project 9. After removing the links added for the trial, the worker compares the same read-only REST snapshots. A failed restoration remains unresolved. The trial leaves every issue open. Automatic parent closure and Project Status changes remain [untested]. Ongoing automation, Project field changes, and editing existing issue bodies are outside this decision.

Revisit this proposal after the trial and [#124](https://github.com/tbhb/agent-orchestration-poc/issues/124)'s closing-link decision. Reject parent grouping if its Project 9 display is not useful or rollback cannot be proven. Native dependency edges remain the recommended representation because they have direct REST reads.

## Evidence

The [research notes](https://github.com/tbhb/agent-orchestration-poc/blob/research/125-sub-issues-and-dependencies/research/gates/github-sub-issues/notes.md) identify the GitHub Docs and REST OpenAPI commits and distinguish schema, documented, observed, inference, and untested claims. The [evidence record](https://github.com/tbhb/agent-orchestration-poc/blob/research/125-sub-issues-and-dependencies/research/gates/github-sub-issues/evidence.md) retains exact commands, exit codes, rate headers, empty live lists, UI access failure, and the trial hold.
