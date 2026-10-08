---
title: Workflow reference
description: Checked types, scopes, labels, forms, and pull request size rules.
---

<!-- do not edit: generated from config/workflow-reference.toml -->

## Titles and branches

Types: `feat`, `fix`, `docs`, `exp`, `research`, `tooling`, `process`, `decision`, `chore`, `refactor`, `test`, `inc`.

Scopes: `bus`, `containers`, `daemon`, `desktop`, `docs`, `experiment`, `remote`, `research`, `security`, `terminal`, `tooling`, `ui`, `workflow`, `go`, `python`, `shell`, `github`, `git`, `ci`, `testing`, `coverage`, `mutation`, `gates`, `review`, `preflight`, `handoff`, `project`, `workers`, `checkpoint`, `retro`, `sync`, `import`, `subject`, `skeleton`, `boundaries`, `design`, `process`.

Subject verbs: `add`, `allow`, `audit`, `bound`, `build`, `check`, `clarify`, `define`, `detect`, `document`, `enforce`, `fix`, `flag`, `gate`, `keep`, `make`, `measure`, `move`, `pin`, `record`, `refine`, `reject`, `remove`, `repair`, `report`, `require`, `resolve`, `restore`, `retire`, `run`, `skip`, `split`, `sync`, `test`, `track`, `update`, `validate`, `verify`.

Titles use `type(scope): verb object` without a final period. Commit subjects have at most 72 characters. Branches use `<type>/<issue>[-<issue>...]-<slug>`. A new scope needs a reference edit in the same PR.

Issues also admit `inc: summary` and `inc(scope): summary` with no imperative verb. Parent issues use `initiative: summary` or `epic: summary` without a key or ordinal. PR titles keep the conventional pattern.

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
| `invalid/acceptance-criteria` | Invalid acceptance-criteria | `#b60205` |
| `invalid/allowed-paths` | Invalid allowed-paths | `#b60205` |
| `invalid/area` | Invalid area | `#b60205` |
| `invalid/context-and-links` | Invalid context-and-links | `#b60205` |
| `invalid/dependencies-and-paths` | Invalid dependencies-and-paths | `#b60205` |
| `invalid/docs-impact` | Invalid docs-impact | `#b60205` |
| `invalid/evidence-required` | Invalid evidence-required | `#b60205` |
| `invalid/goal` | Invalid goal | `#b60205` |
| `invalid/harness` | Invalid harness | `#b60205` |
| `invalid/out-of-scope` | Invalid out-of-scope | `#b60205` |
| `invalid/parent` | Invalid parent | `#b60205` |
| `invalid/priority` | Invalid priority | `#b60205` |
| `invalid/review` | Invalid review | `#b60205` |
| `invalid/severity` | Invalid severity | `#b60205` |
| `invalid/status` | Invalid status | `#b60205` |
| `invalid/stub-record` | Invalid stub-record | `#b60205` |
| `invalid/title` | Invalid title | `#b60205` |
| `invalid/type` | Invalid type | `#b60205` |
| `invalid/work-type` | Invalid work-type | `#b60205` |
| `needs-operator` | Needs the operator's decision or approval | `#d93f0b` |
| `review/approved` | Review: approved | `#c5def5` |
| `review/changes-requested` | Review: changes-requested | `#c5def5` |
| `review/pending-review` | Review: pending-review | `#c5def5` |
| `review/rejected` | Review: rejected | `#c5def5` |
| `type/bug` | Type: bug | `#0e8a16` |
| `type/chore` | Type: chore | `#0e8a16` |
| `type/decision` | Type: decision | `#0e8a16` |
| `type/defect` | Type: defect | `#0e8a16` |
| `type/docs` | Type: docs | `#0e8a16` |
| `type/epic` | Type: epic | `#0e8a16` |
| `type/experiment` | Type: experiment | `#0e8a16` |
| `type/feature` | Type: feature | `#0e8a16` |
| `type/incident` | Type: incident | `#0e8a16` |
| `type/initiative` | Type: initiative | `#0e8a16` |
| `type/process` | Type: process | `#0e8a16` |
| `type/research` | Type: research | `#0e8a16` |
| `type/spike` | Type: spike | `#0e8a16` |
| `type/tooling` | Type: tooling | `#0e8a16` |

Each issue and PR has exactly one `area/`, `type/`, and `harness/` label. Type-to-label mapping:

Parent issues require one `type/initiative` or `type/epic` label and are exempt from form, `area/`, and `harness/` checks. An old and new label for the same class count as one during migration.

| Type | Label |
| --- | --- |
| `feat` | `type/feature` |
| `fix` | `type/defect` |
| `docs` | `type/chore` |
| `exp` | `type/experiment` |
| `research` | `type/spike` |
| `tooling` | `type/chore` |
| `process` | `type/chore` |
| `decision` | `type/spike` |
| `chore` | `type/chore` |
| `refactor` | `type/chore` |
| `test` | `type/chore` |
| `inc` | `type/incident` |

The relabel-only exceptions are keyed by their exact issue titles in the reference. These issues keep their titles. The migration table remains until the final read-back in issue #200:

| Old label | New label |
| --- | --- |
| `type/bug` | `type/defect` |
| `type/tooling` | `type/chore` |
| `type/process` | `type/chore` |
| `type/docs` | `type/chore` |
| `type/research` | `type/spike` |
| `type/decision` | `type/spike` |

## Forms and references

Issue fields: `Goal`, `Context and links`, `Dependencies and paths`, `Acceptance criteria`, `Evidence required`, `Docs impact`, `Out of scope`. `Allowed paths` is a separate form field.

Allowed paths use repo-relative literals or anchored globs. `*` matches one segment and `**` matches zero or more segments. Absolute paths, `..`, and negation are invalid.

Evidence requires named repository paths and exact commands. PR sections: `What`, `Why`, `Evidence`, `Docs`, `Checklist`, `Size justification`, `Gate justifications`. A PR ends with one or more `Refs: #<n>` lines naming open issues.

## Pull request size

Pin `github.com/boyter/scc/v4` at 4.1.0. Code counts scc-classified changed code lines, added plus deleted, excluding blanks and comment-only lines. Prose counts each added or deleted nonblank line, including Markdown comments. Compare from the merge base of PR target, including upstream target for a stacked PR.

Target 400 and limit 800 units. Project Size S is at most 200, M at most 400, and L at most 800. Split larger estimates during refinement.

Excluded paths: `go.sum`, `uv.lock`, `pnpm-lock.yaml`, `**/pnpm-lock.yaml`, `package-lock.json`, `**/package-lock.json`, `yarn.lock`, `**/yarn.lock`, `Cargo.lock`, `**/Cargo.lock`, `**/*-checksum*`, `**/vendor/**`, `tests/fixtures/**`, `reports/inputs/**`, `experiments/**/evidence/**`, `research/imported/**`, `**/*.svg`, `**/*.excalidraw`. Also exclude `scc` detected generated and minified files, vendored code, test fixtures, evidence directories, and exported diagrams. Keep excluded files in per-file output with raw added and deleted counts and a reason.

Run `mise run pr:size -- origin/main` for a PR targeting `main`, or pass the upstream target of a stacked PR. The command emits JSON with `total_units` and per-file raw added, raw deleted, counted units, and exclusion reason. `mise run check:pr-size-contract` prints passing and over-limit fixture results.

The counter classifies removed and added fragments with `scc`. A fragment inside a multiline comment can be counted as code because its enclosing delimiters are absent. Subtracting full-file code counts avoids that error but loses equal-count replacements, so the fragment method is the recorded contract. Issue #93 owns CI enforcement.

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
