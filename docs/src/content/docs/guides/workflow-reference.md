---
title: Workflow reference
description: Checked types, scopes, labels, forms, and pull request size rules.
---

<!-- do not edit: generated from config/workflow-reference.toml -->

## Titles and branches

Types: `feat`, `fix`, `docs`, `exp`, `research`, `tooling`, `process`, `decision`, `chore`, `refactor`, `test`.

Scopes: `bus`, `containers`, `daemon`, `desktop`, `docs`, `experiment`, `remote`, `research`, `security`, `terminal`, `tooling`, `ui`, `workflow`, `go`, `python`, `shell`, `github`, `git`, `ci`, `testing`, `coverage`, `mutation`, `gates`, `review`, `preflight`, `handoff`, `project`, `workers`, `checkpoint`, `retro`, `sync`, `import`, `subject`, `skeleton`, `boundaries`, `design`, `process`.

Subject verbs: `add`, `allow`, `audit`, `build`, `check`, `clarify`, `define`, `detect`, `document`, `enforce`, `fix`, `gate`, `keep`, `make`, `measure`, `move`, `pin`, `record`, `refine`, `reject`, `remove`, `report`, `require`, `resolve`, `restore`, `retire`, `run`, `split`, `sync`, `test`, `track`, `update`, `validate`, `verify`.

Titles use `type(scope): verb object` without a final period. Commit subjects have at most 72 characters. Branches use `<type>/<issue>[-<issue>...]-<slug>`. A new scope needs a reference edit in the same PR.

`workflow` remains an area and scope, but is retired as a commit type because `process` and `tooling` describe the two kinds of workflow changes without a separate overlapping type.

## Labels

| Name | Description | Color |
| --- | --- | --- |
| `area/bus` | Area: bus | `#1d76db` |
| `area/containers` | Area: containers | `#1d76db` |
| `area/daemon` | Area: daemon | `#1d76db` |
| `area/desktop` | Area: desktop | `#1d76db` |
| `area/docs` | Area: docs | `#1d76db` |
| `area/experiment` | Area: experiment | `#1d76db` |
| `area/remote` | Area: remote | `#1d76db` |
| `area/research` | Area: research | `#1d76db` |
| `area/security` | Area: security | `#1d76db` |
| `area/terminal` | Area: terminal | `#1d76db` |
| `area/tooling` | Area: tooling | `#1d76db` |
| `area/ui` | Area: ui | `#1d76db` |
| `area/workflow` | Area: workflow | `#1d76db` |
| `blocked` | Blocked on another item or a finding | `#b60205` |
| `harness/agy` | Intended harness: agy | `#fbca04` |
| `harness/any` | Intended harness: any | `#fbca04` |
| `harness/claude` | Intended harness: claude | `#fbca04` |
| `harness/codex` | Intended harness: codex | `#fbca04` |
| `needs-operator` | Needs the operator's decision or approval | `#d93f0b` |
| `phase/0` | Phase 0 | `#5319e7` |
| `phase/1` | Phase 1 | `#5319e7` |
| `phase/2` | Phase 2 | `#5319e7` |
| `phase/3` | Phase 3 | `#5319e7` |
| `phase/4` | Phase 4 | `#5319e7` |
| `phase/5` | Phase 5 | `#5319e7` |
| `phase/6` | Phase 6 | `#5319e7` |
| `type/bug` | Type: bug | `#0e8a16` |
| `type/decision` | Type: decision | `#0e8a16` |
| `type/docs` | Type: docs | `#0e8a16` |
| `type/experiment` | Type: experiment | `#0e8a16` |
| `type/feature` | Type: feature | `#0e8a16` |
| `type/process` | Type: process | `#0e8a16` |
| `type/research` | Type: research | `#0e8a16` |
| `type/tooling` | Type: tooling | `#0e8a16` |

Each issue and PR has exactly one `area/`, `type/`, `phase/`, and `harness/` label. Type-to-label mapping:

| Type | Label |
| --- | --- |
| `feat` | `type/feature` |
| `fix` | `type/bug` |
| `docs` | `type/docs` |
| `exp` | `type/experiment` |
| `research` | `type/research` |
| `tooling` | `type/tooling` |
| `process` | `type/process` |
| `decision` | `type/decision` |
| `chore` | `type/tooling` |
| `refactor` | `type/tooling` |
| `test` | `type/tooling` |

## Forms and references

Issue fields: `Goal`, `Context and links`, `Dependencies and paths`, `Acceptance criteria`, `Evidence required`, `Docs impact`, `Out of scope`. `Allowed paths` is a separate form field.

Allowed paths use repo-relative literals or anchored globs. `*` matches one segment and `**` matches zero or more segments. Absolute paths, `..`, and negation are invalid.

Evidence requires named repository paths and exact commands. PR sections: `What`, `Why`, `Evidence`, `Docs`, `Checklist`, `Size justification`, `Gate justifications`. A PR ends with one or more `Refs: #<n>` lines naming open issues.

## Pull request size

Pin `github.com/boyter/scc/v4` at 4.1.0. Code counts scc-classified changed code lines, added plus deleted, excluding blanks and comment-only lines. Prose counts each added or deleted nonblank line, including Markdown comments. Compare from the merge base of PR target, including upstream target for a stacked PR.

Target 400 and limit 800 units. Project Size S is at most 200, M at most 400, and L at most 800. Split larger estimates during refinement.

Excluded paths: `go.sum`, `uv.lock`, `pnpm-lock.yaml`, `**/pnpm-lock.yaml`, `**/*-checksum*`, `**/vendor/**`, `tests/fixtures/**`, `reports/inputs/**`, `experiments/**/evidence/**`, `research/imported/**`, `**/*.svg`, `**/*.excalidraw`. Also exclude `scc` detected generated and minified files, vendored code, test fixtures, evidence directories, and exported diagrams. Keep excluded files in per-file output with raw added and deleted counts and a reason.

The counter and CI enforcement are separate work. Issue #93 owns enforcement.

## Agent provenance

[Decision 0131](/decisions/0131-assisted-by-provenance/) defines the proposed provenance contract for issue #131. It remains inactive until [#134](https://github.com/tbhb/agent-orchestration-poc/issues/134). Current hooks still prohibit attribution trailers. This generated page preserves the provenance section reserved by #131.

Use this exact line format after cutover:

```text
Assisted-by: <harness>/<version> model=<model> effort=<effort> agent=<agent>
```

The [admitted combinations](/decisions/0131-assisted-by-provenance/#admitted-combinations) define the complete catalog by exact harness/version and the Cartesian product of each row's model and effort lists. The [reference values](/decisions/0131-assisted-by-provenance/#reference-values) show literal examples for Codex Sol and Astra, Claude Fable and Sonnet, and agy. Catalog lookup rejects unknown tuples, including every use of `unavailable`, while launch permission and runtime verification remain separate requirements.

Use one line per contributing agent ID, freeze that ID's configuration, sort complete lines by ASCII bytes, and reject duplicates within each artifact. The PR body contains the exact set union of its selected commits' lines. Preserve that union when deriving the squash body. Reviews, inline comments, implementer replies, issue bodies, and coordinator notes each carry their own contributors. Project draft bodies include trailers. Typed field edits use the separate provenance record defined in the decision.

After cutover, ordinary agent communication and Project edits use `tbhbagent`, and reviews use `tbhbbot`. The coordinator is subject to the same rule. Attribution is separate from operator authority, account verification, and signing. The decision records the #132/#134/#135 coordinator clarifications and keeps today's `tbhb` implementer workflow intact.

Keep `Refs:` as issue references. Closing keywords, if selected by #124, belong before the final trailer block and apply only to completed issues. The proposed cases in `research/gates/assisted-by/examples.md` cover both #124 options, completed-issue-only and multiple-reference bodies, an issue that remains open, and squash propagation. Policy selection remains with #124. Closure behavior remains inactive here.
