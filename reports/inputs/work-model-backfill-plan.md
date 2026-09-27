# Work model backfill input contract and partial delivery

[Verified] This partial delivery exports pure `parse_tables`, `complete`, `cycle_nodes`, and `validate_cp1` functions from `agent_orchestration_poc.core.work_model_backfill`. They accept TSV text and immutable plain-value records. The three table paths are supplied by the caller. No count, assignment row, Project field ID, or option ID is embedded in the module. The synthetic fixtures cover a numbered issue, a planned closure, a new draft, an existing draft, an unrelated held draft, a parent, and accepted and excluded edge dispositions.

[Verified] `parse_tables` requires the assignment, parent, and edge columns used by this contract, preserves every supplied column, rejects duplicate issue numbers and draft or parent titles, rejects key collisions across numbered issues, drafts, and parents, rejects unknown native types or options, and refuses unresolved accepted parent or blocker references. Native issue types are Feature, Defect, Chore, Spike, Incident, Epic, and Initiative. Priority accepts Expedite, Standard, and Intangible, Severity accepts SEV1 through SEV3, and Work type accepts Planned and Unplanned. Blank Priority and Severity remain possible. Experiment is not an issue type.

[Verified] `complete` checks a snapshot version, branch SHA, contiguous page indexes, consistent totals, and the counts of issues, drafts, and Project items. The caller must supply receipts for `issues`, `project`, `drafts`, `native`, `parents`, and `blockers`. `validate_cp1` requires an initial run, exact numbered issue coverage, unchanged source titles and states, the old Project's saved Status, Phase, Priority, Size, Area, Harness, and Worker values, no existing parent for a numbered child, and exact matching of every row marked existing draft. Null old Project values match empty snapshot strings; rows without saved old Project fields match an empty source field tuple. A uniquely matched draft already present at CP1 can be reused, and unrelated held drafts remain snapshot items. The target Project columns describe planned values and do not set the CP1 source expectation. `cycle_nodes` traverses accepted native and deferred edges together with numbered-to-epic and epic-to-initiative membership. Audit-only `judgment`, `open`, `no link`, and `cut` rows remain in `Tables.edges` but cannot become accepted links through this function.

[Documented] The separate #207 shell must read source files, use complete REST pagination and native issue-field reads, construct the `Snapshot` values, and save the source hash before step 0. The versioned [Python 3.14 CSV documentation](https://docs.python.org/3.14/library/csv.html) defines the TSV reader used by the pure parser. The [REST Project item reference](https://docs.github.com/en/rest/projects/items?apiVersion=2026-03-10) and [REST issue field value reference](https://docs.github.com/en/rest/issues/issue-field-values?apiVersion=2026-03-10) were read for the shell handoff. No I/O call sits in the core module.

## Deferred contract

[Untested] This PR does not create an operation plan, final CP13 comparison, rollback values, numbered closed-title exemption manifest, scope-changing title verdict gate, PR #97 closure record, rank sequence, or enforcement checkpoints. Those transformations must be completed after the final version 3 tables are integrated and their draft field behavior is verified. The plan will keep step order 1, 0, 2–6, 6T, and 7–15. #207 will collect CP1 and CP13 and execute REST writes with per-result journaling. #209 owns rank planning, while configuration, operator confirmation, and enforcement stay external checkpoints. The separate work model documentation issue owns the site guide.

[Inference] The next pure plan should resolve existing issue and draft IDs from CP1, require returned IDs for later creations, retain per-row existing or created identity, and stop on stale values or incomplete nested pages. A partial run must enter reviewed recovery rather than masquerade as an initial CP1. These are handoff requirements, not implemented behavior in this PR.

## Verification record

[Verified] Before splitting, `mise run check:imports` exited 0 and `mise run check:ruff` exited 0 on the larger prototype. `mise run check` exited 3 when `check:deadcode` found two unreferenced dataclass fields. A later `mise run check:coverage` exited 1 on that prototype with Python core lines 94.68% and branches 86.58%. The implementation was reduced to the 504-code-line snapshot and parser slice measured by `mise exec -- go run github.com/boyter/scc/v4@v4.1.0 --by-file` on the two changed Python files. Verification below records the final slice's results.

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

## Review-fix verification on 2026-09-27

[Verified] Before the fix, `mise exec -- uv run pytest tests/test_work_model_backfill.py -q` exited 1: three synthetic cross-category edge-key collisions were accepted or reached the later parent check, and a proposed new draft already present in CP1 was accepted. With the fix, the same command exited 0 with 25 passed. The collision tests cover draft-to-parent, draft-to-number, and parent-to-number cases. The CP1 test changes an unrelated held draft into the proposed new draft while retaining its IDs and page counts. Existing unmatched held drafts remain valid in the original fixture.

[Verified] `mise run check:imports` exited 0 with both boundary contracts kept. `mise run check:ruff` first exited 1 on the new draft logic's complexity; after extracting a pure draft validator, the Ruff portion of the aggregate passed. `mise run check` was interrupted with exit 130 after the Go branch instrumenter remained silent; `mise run --jobs=1 check` then exited 0. Its coverage report showed Python core lines 98.60%, Python core branches 95.34%, Python shell lines 85.13%, Go core statements 96.43%, Go core branches 94.74%, and Go shell statements 74.58%. `mise run check:mutation` exited 0: Go killed 145 of 149 mutants (97.32%), and Python killed 1,861 of 2,037 (91.36%).

[Observed] A path-supplied `parse_tables` call on `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/reorg/2026-09-27-work-model-v3-final.tsv` and its `-parents.tsv` and `-edges.tsv` companions raised `ValueError: table header is incomplete`. The final assignment header uses `size` and omits `project phase`, while the current partial contract requires `project size` and `project phase`. Integrating the final table schema is deferred with the approved-table and plan slice of #199; this review fix does not treat the failed call as evidence of a title-key collision.

[Verified] After merging `origin/main` at `36e64a1`, `mise run check` exited 0. Its coverage floors passed: Python core lines 98.60%, branches 95.34%, shell lines 85.13%; Go core statements 96.43%, branches 94.74%, shell statements 74.58%. `mise run check:mutation` exited 0: Go killed 145 of 149 mutants (97.32%) and Python killed 1,847 of 2,037 (90.67%). No code changed after the merge.

[Verified] A newer main commit required a second clean merge at `e47da35`. On that head, `mise run check` and `mise run check:mutation` both exited 0. Coverage floors and mutation scores matched the preceding merged-head run. No backfill code changed after `22f3185`.

## Second slice on the approved final tables

[Verified] The assignment parser requires the exact final header with `size` and without `project phase`. Under Python 3.14.6, the committed tables parse as 191 assignments, 22 parents, and 387 edge audit rows. The cycle check finds no accepted cycle. The approved work model, sanitized change record, source digests, and bounded live counts are in [the final manifest](work-model-tables/manifest.md). The source checkout was `6448b1175dbc2c8f22f68fa126b5b344db9b74b0`. The pinned parser's versioned source remains CPython `c63aec69` at 3.14.6, recorded in [Python conventions](../../docs/src/content/docs/guides/python-conventions.md).

[Verified] CP1 validation accepts a numbered issue whose proposed title was already applied, including #155's part B retitle. It matches a proposed draft already in the Project by exact title and checks a supplied existing draft item ID. The parser still preserves `judgment`, `open`, `no link`, and `cut` edge rows, rejects identity collisions, and detects accepted cycles. No Project write is in this slice.

[Observed] The bounded REST read returned 161 issues and 169 new-Project items. Issue #155 already has its proposed title. These observations are consistent with the operator's report that issue copying and the part B retitle are done. They do not establish a complete CP1 because field, body, label, hierarchy, blocker, and nested page values were not collected. Request counts in version 3 remain estimates, and a changed count alone is not treated as a defect.

[Untested] This is a partial delivery. The ordered operation plan, complete CP13 read-back comparison, numbered exemption derivation from CP1, and safe rollback actions remain on #199. The separate #207 runner must wait for that contract. A larger plan prototype passed `mise run check` with Python core line coverage 96.01 percent and branch coverage 91.27 percent, but `mise run check:mutation` scored 82.51 percent against a 90 percent floor. Completing its tests and missing acceptance cases would exceed this PR's 800-unit limit, so the prototype was removed before the final checks.

| Second-slice command | Exit code | Evidence |
| --- | --- | --- |
| `mise run vale:sync` | 0 | Pinned prose styles synced once in this worktree |
| `mise exec -- uv run pytest tests/test_work_model_backfill.py -q` | 0 | 27 focused tests passed |
| `mise run check:imports` | 0 | Both core boundary contracts kept |
| `mise run check:ruff` | 0 | Lint and format checks passed |
| `mise run check` | 0 | Python core lines 98.60 percent, branches 95.34 percent, and every aggregate check passed |
| `mise run check:mutation` | 0 | Go killed 145 of 149 and Python killed 1,864 of 2,061 mutants |

[Verified] The final change record in the repository redacts eight embedded issue-body values. The work model Markdown and parent TSV match their holding inputs byte for byte. The assignment and edge TSV copies quote terminal empty cells while preserving every parsed value, as the manifest records. `mise exec -- gitleaks dir --redact --no-banner --log-level error reports/inputs/work-model-tables` exited 0. No GitHub write or Project field edit was made during this implementation.

[Verified] The merge-base diff has 97 changed Python code units measured with `mise exec -- go run github.com/boyter/scc/v4@v4.1.0 --by-file` on added and deleted Python lines. The manifest, approved copies, and fixture TSV are excluded by the checked size contract. This partial slice is below the 400-unit target and 800-unit limit. The separate plan and comparison work needs a fresh review and size estimate before implementation.

## CP1 source-value review fix

[Verified] After merging `origin/main` at `1454561`, the approved #168 assignment row reproduced the review finding: its saved old Project Status is `Refinement`, its target Project Status is `Done`, and the pre-fix `validate_cp1` raised `changed source Project values` on a complete initial snapshot. The new regression uses that committed row and fixed source values; it accepts the saved pre-closure Status and rejects a changed source Status. The source comparison now reads the seven scalar old Project fields from `old project fields`, while target columns remain planned values.

[Verified] `mise exec -- uv run pytest tests/test_work_model_backfill.py -q` passed 28 tests. `mise run check:imports` and `mise run check:ruff` exited 0. `mise run check:mutation` exited 0: Go killed 145 of 149 mutants (97.32 percent), and Python killed 1,867 of 2,057 (90.76 percent). The first mutation run stopped before scoring because mutmut's copied test path could not locate the committed report inputs. The regression now finds those inputs from either the ordinary test path or the mutmut copy, and the second mutation run passed.

[Verified] `mise run check` exited 0 after the final source, test, and documentation edits. Its coverage floors passed: Python core lines 98.61 percent, Python core branches 95.34 percent, Python shell lines 85.13 percent, Go core statements 96.43 percent, Go core branches 94.74 percent, and Go shell statements 74.58 percent. No Project field or issue value was changed by this fix.
