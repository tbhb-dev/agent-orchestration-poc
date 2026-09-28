# Work model backfill plan and comparison contract

[Verified] The first merged slice exported pure `parse_tables`, `complete`, `cycle_nodes`, and `validate_cp1` functions from `agent_orchestration_poc.core.work_model_backfill`. They accept TSV text and immutable plain-value records. The three table paths are supplied by the caller. No count, assignment row, Project field ID, or option ID is embedded in the module. The synthetic fixtures cover a numbered issue, a planned closure, a new draft, an existing draft, an unrelated held draft, a parent, and accepted and excluded edge dispositions.

[Verified] `parse_tables` requires the assignment, parent, and edge columns used by this contract, preserves every supplied column, rejects duplicate issue numbers and draft or parent titles, rejects key collisions across numbered issues, drafts, and parents, rejects unknown native types or options, and refuses unresolved accepted parent or blocker references. Native issue types are Feature, Defect, Chore, Spike, Incident, Epic, and Initiative. Priority accepts Expedite, Standard, and Intangible, Severity accepts SEV1 through SEV3, and Work type accepts Planned and Unplanned. Blank Priority and Severity remain possible. Experiment is not an issue type.

[Verified] `complete` checks a snapshot version, branch SHA, contiguous page indexes, consistent totals, and the counts of issues, drafts, and Project items. The caller must supply receipts for `issues`, `project`, `drafts`, `native`, `parents`, and `blockers`. `validate_cp1` requires an initial run, exact numbered issue coverage, unchanged source titles and states, the old Project's saved Status, Phase, Priority, Size, Area, Harness, and Worker values, the copied target Status, Size, Area, Harness, and Worker values, no existing parent for a numbered child, and exact matching of every row marked existing draft. A supplied reviewed Status disposition can override the copied Status expectation; the other copied fields must match the saved source. Null old Project values match empty snapshot strings; rows without saved old Project fields match an empty source field tuple. A uniquely matched draft already present at CP1 can be reused, and unrelated held drafts remain snapshot items. The target table columns describe planned post-backfill values and do not set the CP1 copied-value expectation. `cycle_nodes` traverses accepted native and deferred edges together with numbered-to-epic and epic-to-initiative membership. Audit-only `judgment`, `open`, `no link`, and `cut` rows remain in `Tables.edges` but cannot become accepted links through this function.

[Documented] The separate #207 shell must read source files, use complete REST pagination and native issue-field reads, construct the `Snapshot` values, and save the source hash before step 0. The versioned [Python 3.14 CSV documentation](https://docs.python.org/3.14/library/csv.html) defines the TSV reader used by the pure parser. The [REST Project item reference](https://docs.github.com/en/rest/projects/items?apiVersion=2026-03-10) and [REST issue field value reference](https://docs.github.com/en/rest/issues/issue-field-values?apiVersion=2026-03-10) were read for the shell handoff. No I/O call sits in the core module.

## Deferred contract after the first slice

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

[Verified] CP1 validation accepts a numbered issue whose proposed title was already applied, including #155's part B retitle. It matches a proposed draft already in the Project by exact title and checks supplied existing draft item and content IDs. The parser still preserves `judgment`, `open`, `no link`, and `cut` edge rows, rejects identity collisions, and detects accepted cycles. No Project write is in this slice.

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

## Third slice: ordered plan, comparison, exemptions, and reversal values

[Verified] `operation_plan` accepts the approved parsed tables and a complete immutable CP1. It emits steps 1, 0, 2–6, 6T, and 7–15 in that order. Each `Step` has table-derived targets, call templates, saved inputs, a checkpoint condition, and reversal instructions. The checked [operation fixture](../../tests/fixtures/work_model_backfill/plan/operations.json) freezes every stage. Step 1 describes collection by the separate #207 shell and the function refuses to plan later writes until CP1 exists. Steps 2 and 14 are external code and enforcement checkpoints with no metadata call. Steps 7 and 8 retain GraphQL rank operations as external execution under #209. Step 13 requires the operator's explicit confirmation. The caller resolves CP1 issue and draft identities before writing, then journals IDs returned by draft, parent, and incident creation.

[Verified] The call templates use `R` for `repos/tbhb-dev/agent-orchestration-poc`, `P` for `orgs/tbhb-dev/projectsV2/1`, and `OLD` for `users/tbhb/projectsV2/9`. They specify REST reads, separate native type and field writes, Project item writes, the copied D2 draft body correction through GraphQL, hierarchy and dependency writes, targeted issue label removal, and complete read-back. The plan derives 13 step-0 closure targets, 70 title targets, 88 Standard rank targets, 22 parent targets in initiative-then-epic order, 98 hierarchy targets, 99 step-11 link changes including the one deletion, 2 incident targets, and 156 issue type-label cleanup targets from the final inputs. These are row counts in the current approved revision, not hard-coded request budgets. The step-11 read-back compares existing accepted links as well as new writes, while `judgment`, `open`, `no link`, and `cut` edges remain audit rows.

[Verified] `title_exemptions` derives numbers from target-closed rows whose saved CP1 titles fail the checked workflow title rule or exceed 72 characters. It refuses to emit the manifest until every planned step-0 closure is confirmed. A persisted reopen revocation removes that number permanently, including after another closure. The approved-input fixture derives 45 numbers, including overlength closed titles #3, #10, #16, #84, and #87; the corrected model section 8 lists all 45. `title_repairs` validates every replacement against the checked reference and 72-character limit, yielding 70 targets. It flags exactly 18 changed scope tokens for new refinement verdicts. A verb or form repair with unchanged scope retains its prior verdict under the separate body-unchanged check in step 6T.

[Verified] `expected_cp13` constructs the read-back target from CP1, the approved rows, successful closure proof, the revocation set, returned creation identities, newly added Project item IDs for every assigned existing issue missing membership, and reviewed body inputs. It refuses missing or colliding created IDs, an invalid non-exempt title, and missing reviewed bodies. It compares original or migrated titles, states and reasons, native issue type and field values, derived linked Project display values, Status, Size, Area, Harness, Worker, applicable retained Validation values, draft blank native columns, parent membership, accepted native blockers, draft identities, and held unrelated drafts. The reviewed body map must specify an exact target for every matched existing draft, including D2; an already-correct body is a no-op. `compare_cp13` refuses incomplete pages and reports every different identity or value keyed by stable issue number or draft key, plus a changed retained branch SHA. The [expected-value fixture](../../tests/fixtures/work_model_backfill/plan/expected-cp13.json) includes an existing draft, a created draft, a created parent, and an unrelated held draft.

[Verified] `rollback_values` returns the exact prewrite CP1 Items, full original Project order, saved PR state, retained branch SHA, supplied exemption manifest, created issue or draft identities even when their Project addition has not succeeded, and separately added Project memberships for existing issues. Each ordered step names its selective inverse, including native fields before the saved issue type. This supplies saved titles, closures, native fields, Project values, draft bodies and identity, parents, blockers, issue bodies, and labels without guessing deleted schema values. Step 14 separately saves the permanent revocation record. A later partial run uses a distinct `Snapshot.run_state` and cannot pass `validate_cp1` as an initial run. The #207 shell retains per-call results and chooses reviewed rollback or safe resume.

[Documented] The pure implementation follows Python 3.14 `dataclasses.replace` behavior in the [versioned dataclasses reference](https://docs.python.org/3.14/library/dataclasses.html). The endpoint templates match the versioned [issue field values](https://docs.github.com/en/rest/issues/issue-field-values?apiVersion=2026-03-10), [Project items](https://docs.github.com/en/rest/projects/items?apiVersion=2026-03-10), [sub-issues](https://docs.github.com/en/rest/issues/sub-issues?apiVersion=2026-03-10), and [issue dependencies](https://docs.github.com/en/rest/issues/issue-dependencies?apiVersion=2026-03-10) references read on 2026-09-27. The local interpreter is Python 3.14.6, the workflow validator source is `src/agent_orchestration_poc/core/workflow_forms.py` at baseline commit `6e635b636e6c1fac377deba59319ffe9a5388d2a`, and the five final source digests are recorded in the [manifest](work-model-tables/manifest.md). The online Python page currently labels itself 3.14.7, so runtime claims remain limited to the pinned local interpreter.

[Observed] No live CP1 or CP13 has been collected in this slice and no GitHub mutation was made. The separate runner #207 owns those reads, execution journals, retries, and rollback writes. #200 owns the operator-confirmed live run. The work model site guide belongs to the separate documentation issue. A difference from the section-10 request estimates alone is not a defect.

## Third-slice verification

[Verified] The first third-slice `mise exec -- uv run pytest tests/test_work_model_backfill.py -q --tb=short` exited 0 with 56 passing focused tests. Those tests covered the ordered plan, then-published 40-number exemption manifest, closure gating, permanent reopen revocation, 70 replacements, 18 changed scopes, CP13 values and incomplete reads, creation identity collisions, and saved rollback values. The complete CP1 used in the final-revision test is synthetic and built from saved assignment fields. It is not a live CP1. The review-fix test record below supersedes the manifest count and checks.

| Final command | Exit code | Result |
| --- | --- | --- |
| `mise run vale:sync` | 0 | Pinned styles synced in this worktree |
| `mise run fmt` | 0 | Formatters applied before final checks |
| `mise run check:imports` | 0 | Core boundary contracts kept |
| `mise run check:ruff` | 0 | Lint and format checks passed |
| `mise run check` | 0 | All aggregate tasks passed, with Python core lines 98.32 percent and branches 94.93 percent |
| `mise run check:mutation` | 0 | Go efficacy 97.32 percent and Python core 90.28 percent from 2,611 of 2,892 killed |
| `mise run build` | 0 | Go binaries built |
| `mise exec -- gitleaks dir --redact --no-banner --log-level error tests/fixtures/work_model_backfill/plan` | 0 | No fixture leak found |

[Verified] A preliminary mutation run on the larger operation-plan representation scored 82.55 percent and failed the 90 percent floor. The plan was compacted into a reviewed inline contract, complete fixture assertions were added, and the final gate above passed. A preliminary aggregate run stopped on a formatter finding after a later source edit. `mise run fmt` corrected that line, and the final aggregate run passed. Both preliminary failures are resolved on this head.

[Verified] For the initial third slice before this review fix, pinned `scc` 4.1.0 classified the merge-base diff fragments from `src/agent_orchestration_poc/core/work_model_backfill.py` and `tests/test_work_model_backfill.py` as 788 changed Python code units, with 387 and 389 added code units and 1 and 11 deleted code units respectively. The two JSON fixtures and this report were excluded by the workflow size contract. `git diff --check` exited 0 on that slice. The review fix adds code and tests, so 788 is no longer the current PR size. The final staged secret scan and hosted checks are recorded at pull request handoff.

## Reviewer change request on 2026-09-27

[Verified] Against head `f0b39ca`, six failure-oriented tests first failed: copied target Project drift passed CP1, no per-type native write contract existed, an existing issue's new Project item ID could not be supplied to CP13, the D2 draft correction was optional, revoking a closed-title exemption still accepted the invalid title, and rollback rejected a created issue before Project addition. `mise exec -- uv run pytest tests/test_work_model_backfill.py -q --tb=short` exited 1 with 6 failed and 56 passed before the implementation change. After the pure-core changes and fixture updates, it exited 0 with 71 passed.

[Verified] CP1 now checks copied Status, Size, Area, Harness, and Worker against the saved OLD values when a numbered issue has a Project item. The caller supplies an explicit reviewed Status override keyed by issue identity. Step 6 records per-row native write payloads, with Priority only for Feature, Chore, and Spike, Severity only for Defect and Incident, and Work type for all seven types. Steps 9 and 12 explicitly include native type at issue creation. Step 6 reverses saved native fields before restoring the old type. These payload rules match the corrected model file and the operator's 17:27 confirmation.

[Verified] CP13 accepts a separate returned Project-item mapping for existing issues that lacked membership at CP1, requires an explicit reviewed body target for each matched existing draft, and refuses invalid non-exempt titles after revocation. Rollback takes the parsed tables to validate each planned creation kind, retains a successfully created issue or draft identity even if later field or Project writes fail, and records newly added Project membership separately. The synthetic tests compare complete CP13 pages and retain the original issue identity for a newly added item. No live CP1 or CP13 was collected, and no backfill mutation was made.

| Review-fix command | Exit code | Result |
| --- | --- | --- |
| `mise run fmt` | 0 | Ruff and repository formatters applied |
| `mise run check:imports` | 0 | Both core boundary contracts kept |
| `mise run check:ruff` | 0 | Lint and format checks passed |
| `mise run check` | 0 | Python core lines 97.79 percent, branches 93.75 percent; all aggregate checks passed |
| `mise run check:mutation` | 0 | Go killed 145 of 149; Python killed 2,822 of 3,132 for 90.10 percent |

[Observed] The formatter could not save optional Tombi schema cache files outside this worktree (`Operation not permitted`), but exited 0 and formatted the checked files. The corrected holding model now records 45 closed-title exemptions and pins Priority to Feature, Chore, and Spike. The pure backfill never edits source files or Project fields.

[Verified] The current merge-base Python diff, split into added and deleted fragments, has 1,151 changed code units under pinned `scc` 4.1.0 (`mise exec -- go run github.com/boyter/scc/v4@v4.1.0 --by-file /private/tmp/pr223-added.py /private/tmp/pr223-deleted.py`). This exceeds the workflow's 800-unit limit. Fixtures and `reports/inputs/` remain excluded by the size rule. [Coordinator disposition](https://github.com/tbhb-dev/agent-orchestration-poc/pull/223#issuecomment-5860337409) accepts the overage without a split because the contract is one pure module with dependent parts and review findings added required guarantees. No live backfill mutation was made.

## Second reviewer change request on 2026-09-27

[Verified] Three new failure-oriented tests first failed against `cabecbe`: `title_exemptions` could not receive a reviewed Status override, CP13 accepted an omitted Project membership for an assigned existing issue, and an already-correct D2 body raised an error. `mise exec -- uv run pytest tests/test_work_model_backfill.py -q -k 'cp1_rejects_copied_drift or added_membership_uses_existing_issue_identity or existing_d2_draft_requires_corrected_body' --tb=short` exited 1 with 3 failed and 68 deselected before the fix. The full focused file then passed with 71 tests.

[Verified] `title_exemptions` now validates CP1 with the caller's reviewed Status dispositions, as planning and CP13 already do. CP13 requires exactly the returned Project item IDs for assigned numbered issues whose CP1 items lacked membership. Matched existing drafts each require an explicit reviewed body target, which can equal the saved body. The D2 test covers missing target, incorrect old Planned read-back, and an already-correct Unplanned no-op. Saved CP1 values remain immutable, and rollback still accepts partial added-item mappings.

| Second review-fix command | Exit code | Result |
| --- | --- | --- |
| `mise run fmt` | 0 | Formatters applied after resolving the initial lint findings |
| `mise run check` | 0 | Python core lines 97.92 percent and branches 94.06 percent; all aggregate gates passed |
| `mise run check:mutation` | 0 | Go killed 145 of 149; Python killed 2,831 of 3,137 for 90.25 percent |

[Observed] The first `mise run fmt` exited 1 on a six-argument manifest signature and a broad `pytest.raises` block. The manifest override is now keyword-only with a documented targeted lint suppression, the test setup moved outside the exception block, and the final format and aggregate checks passed.

## Third reviewer change request on 2026-09-27

[Verified] Five focused cases first failed against head `542dca2`: a complete independently constructed read-back of two open numbered incident issues disagreed with `proposed` target state; the draft creation path accepted an issue resource; the incident and parent wrong-kind probes reached only a generic identity collision; and a changed D2 draft content ID passed the preclosure plan. `mise exec -- uv run pytest tests/test_work_model_backfill.py -q -k 'approved_incidents_are_open_numbered_issues_at_cp13 or cp13_rejects_wrong_creation_kind or cp1_rejects_changed_existing_draft_content_id' --tb=short` exited 1 with five failed and 71 deselected before the core fix. After the fix, the same command exited 0 with five passed and 71 deselected.

[Verified] CP13 translates `backfill mode=issue` planning rows to open runtime issues. Its creation map requires numbered issue identities without draft IDs for incident and parent creations, and draft identities without issue IDs for draft creations. The approved-input helper now returns numbered incident issues. CP1 compares both the approved Project item ID and draft content ID before returning the closure plan. The complete approved-input test supplies independently constructed incident Item values for read-back and retains the other target rows; it is a synthetic fixture, not a live CP13.

| Third review-fix command | Exit code | Result |
| --- | --- | --- |
| `mise exec -- uv run pytest tests/test_work_model_backfill.py -q --tb=short` | 0 | 76 focused tests passed |
| `mise run fmt` | 0 | Formatters applied to the changed Python files |
| `mise run check:imports` | 0 | Both core boundary contracts kept |
| `mise run check:ruff` | 0 | Lint and format checks passed before the final test edits; aggregate reran them afterward |
| `mise run check` | 0 | All aggregate gates passed; Python core lines 97.93 percent and branches 94.10 percent |
| `mise run check:mutation` | 0 | Go killed 145 of 149 mutants; Python killed 2,880 of 3,189 for 90.31 percent |

[Observed] An initial aggregate run exited 1 because two newly edited test lines needed Ruff formatting. `mise run fmt` corrected them, and the next aggregate run exited 0. No live backfill mutation or Project edit was made.

## Coordinator arbitration fixes on 2026-09-27

[Verified] A pure probe loaded the baseline `071bfad` core from `git show` and confirmed that `rollback_values` accepted both a created parent mapped to CP1 issue #1 and a draft identity for a planned parent. The new failure fixtures cover CP1 key, issue, draft, and Project item collisions; duplicate identities across two creations; and wrong draft, parent, and incident resource kinds. Rollback now rejects these before returning reversal values, while a valid partial creation without a Project item remains reversible. The focused file passed 87 tests after the fix.

[Verified] The corrected holding model and change file were copied from the 18:42 revision named by the coordinator. The model copy is byte identical to its source. The change copy redacts eight embedded issue bodies and applies three Markdown whitespace fixes; its source and sanitized digests are in the [manifest](work-model-tables/manifest.md). The three TSVs were unchanged. `mise exec -- gitleaks dir --redact --no-banner --log-level error reports/inputs/work-model-tables` exited 0. The corrected model records 45 closed-title exemptions and the confirmed three-type Priority pin, so the earlier reconciliation statements no longer apply.

| Arbitration-fix command | Exit code | Result |
| --- | --- | --- |
| `mise run vale:sync` | 0 | Pinned prose styles synced |
| `mise run fmt` | 0 | Ruff and rumdl formatted changed files |
| `mise run check:imports` | 0 | Both core boundary contracts kept |
| `mise run check:ruff` | 0 | Lint and format checks passed |
| `mise run check` | 0 | 373 ordinary tests passed; Python core lines 97.97 percent and branches 94.21 percent; all aggregate gates passed |
| `mise run check:mutation` | 0 | Go killed 145 of 149 mutants (97.32 percent); Python killed 2,940 of 3,260 (90.18 percent) |

[Observed] The first formatter pass exited 1 because adding required parsed tables made `rollback_values` exceed Ruff's five-argument limit. The tables remain explicit and `extras` is keyword-only, with one justified argument-count suppression. The next formatter pass exited 0. Both aggregate runs exited 0; the final run included the incident-kind fixture and this report.
