# Work model backfill input contract and partial delivery

[Verified] This partial delivery exports pure `parse_tables`, `complete`, `cycle_nodes`, and `validate_cp1` functions from `agent_orchestration_poc.core.work_model_backfill`. They accept TSV text and immutable plain-value records. The three table paths are supplied by the caller. No count, assignment row, Project field ID, or option ID is embedded in the module. The synthetic fixtures cover a numbered issue, a planned closure, a new draft, an existing draft, an unrelated held draft, a parent, and accepted and excluded edge dispositions.

[Verified] `parse_tables` requires the assignment, parent, and edge columns used by this contract, preserves every supplied column, rejects duplicate issue numbers and draft or parent titles, rejects unknown native types or options, and refuses unresolved accepted parent or blocker references. Native issue types are Feature, Defect, Chore, Spike, Incident, Epic, and Initiative. Priority accepts Expedite, Standard, and Intangible, Severity accepts SEV1 through SEV3, and Work type accepts Planned and Unplanned. Blank Priority and Severity remain possible. Experiment is not an issue type.

[Verified] `complete` checks a snapshot version, branch SHA, contiguous page indexes, consistent totals, and the counts of issues, drafts, and Project items. The caller must supply receipts for `issues`, `project`, `drafts`, `native`, `parents`, and `blockers`. `validate_cp1` requires an initial run, exact numbered issue coverage, unchanged source titles and states, saved source Project values, no existing parent for a numbered child, and exact matching of every row marked existing draft. It preserves unmatched drafts as snapshot items. `cycle_nodes` traverses accepted native and deferred edges together with numbered-to-epic and epic-to-initiative membership. Audit-only `judgment`, `open`, `no link`, and `cut` rows remain in `Tables.edges` but cannot become accepted links through this function.

[Documented] The separate #207 shell must read source files, use complete REST pagination and native issue-field reads, construct the `Snapshot` values, and save the source hash before step 0. The versioned [Python 3.14 CSV documentation](https://docs.python.org/3.14/library/csv.html) defines the TSV reader used by the pure parser. The [REST Project item reference](https://docs.github.com/en/rest/projects/items?apiVersion=2026-03-10) and [REST issue field value reference](https://docs.github.com/en/rest/issues/issue-field-values?apiVersion=2026-03-10) were read for the shell handoff. No I/O call sits in the core module.

## Deferred contract

[Untested] This PR does not create an operation plan, final CP13 comparison, rollback values, numbered closed-title exemption manifest, scope-changing title verdict gate, PR #97 closure record, rank sequence, or enforcement checkpoints. Those transformations must be completed after an approved version 3 author round establishes the actual rows and draft field behavior. The plan will keep step order 1, 0, 2–6, 6T, and 7–15. #207 will collect CP1 and CP13 and execute REST writes with per-result journaling. #209 owns rank planning, while configuration, operator confirmation, and enforcement stay external checkpoints. The separate work model documentation issue owns the site guide.

[Inference] The next pure plan should resolve existing issue and draft IDs from CP1, require returned IDs for later creations, retain per-row existing or created identity, and stop on stale values or incomplete nested pages. A partial run must enter reviewed recovery rather than masquerade as an initial CP1. These are handoff requirements, not implemented behavior in this PR.

## Verification record

[Verified] Before splitting, `mise run check:imports` exited 0 and `mise run check:ruff` exited 0 on the larger prototype. `mise run check` exited 3 when `check:deadcode` found two unreferenced dataclass fields. A later `mise run check:coverage` exited 1 on that prototype with Python core lines 94.68% and branches 86.58%. The implementation was reduced to the 502-code-line snapshot and parser slice measured by `mise exec -- go run github.com/boyter/scc/v4@v4.1.0 --by-file` on the two changed Python files. Verification below records the final slice's results.

| Final command | Exit code | Result |
| --- | --- | --- |
| `mise run check:imports` | 0 | Both core boundary contracts kept |
| `mise run check:ruff` | 0 | Lint and format checks passed |
| `mise run check` | 130 | Parallel run interrupted after its Go branch instrumenter waited without output |
| `mise run --jobs=1 check` | 0 | All aggregate checks passed on the final code and fixtures |
| `mise run check:mutation` | 0 | Go killed 145 of 149 and Python killed 1,822 of 2,013 mutants |

[Verified] The final single-job aggregate check exited 0 with Python core lines 98.58%, Python core branches 95.22%, Python shell lines 85.13%, Go core statements 96.43%, Go core branches 94.74%, and Go shell statements 74.58%. `mise run check:mutation:python` exited 0 after exact-message and pagination tests, killing 1,825 of 2,013 core mutants for 90.66%. The first Python mutation attempt generated invalid syntax from a multiline subset expression, so the core now uses `issubset`. The first scored run was 88.87%, and a later run was 89.67% before the final targeted fixtures.

[Verified] The final `mise run check:mutation` exited 0. Go mutation efficacy was 97.32% from 145 killed and four lived mutants with none uncovered, timed out, or skipped. Python core mutation score was 90.51% from 1,822 killed of 2,013 mutants. The synthetic fixture's added provenance column was present in this final run.

[Observed] The first parallel aggregate stopped on unformatted new property tests. After formatting, the next parallel run reached the Go branch instrumenter and remained silent. The worker interrupted it with exit 130 and reran the aggregate serially, which passed in 236.86 seconds. The sandbox denied `ps` process inspection with `operation not permitted`. No sandbox setting was changed.

[Observed] The only GitHub operations for this slice were REST GET requests. No live Project write, GraphQL request, or issue creation was performed. The [candidate manifest](work-model-tables/manifest.md) records digests, the bounded live read, and the round-three blocking review. No credential or unredacted issue body is included.
