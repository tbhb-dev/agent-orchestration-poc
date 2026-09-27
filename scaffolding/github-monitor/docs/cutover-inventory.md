# Account, owner, and Project cutover inventory

[observed] This partial #215 delivery compares `origin/main` at `5ef1861694c3c9ad5be7154ece9533f22a79ffcf` with the worktree on 2026-09-27. The account scan below ran before this inventory file was added, so its literal search terms do not count themselves. The authenticated REST reader was `tbhb-agent`, verified by `gh api user --jq .login` with exit 0. No credential value was captured.

## Account names

| Role | Before | After this delivery | Remaining reason |
| --- | --- | --- | --- |
| Worker account `tbhbagent` to `tbhb-agent` | 54 | 52 | Dated records, generated guidance awaiting #148, and the #201 rank client. |
| Reviewer account `tbhbbot` to `tbhb-agent-reviewer` | 232 | 215 | Dated records, shared worker guidance awaiting #86, #148, and #156, plus two negative test cases. |
| Operator `tbhb` | Retained | Retained | Coordinator arbitration and operator authority still belong to this account. |

`git grep -o -E 'tbhbagent|tbhbbot' | sed 's/.*://' | sort | uniq -c` exited 0. Before: `54 tbhbagent`, `232 tbhbbot`. After: `52 tbhbagent`, `215 tbhbbot`.

`git grep -l -E 'tbhbagent|tbhbbot'` exited 0 and returned 37 files after the edits, before this file was added. Every remaining file and its raw occurrence count follows. The negative test rows deliberately reject the retired reviewer account.

| File | Worker | Reviewer | Reason |
| --- | ---: | ---: | --- |
| `AGENTS.md` | 0 | 4 | Shared active instructions after #86 and #156. |
| `docs/src/content/docs/decisions/0007-github-event-monitor.md` | 0 | 1 | Historical decision. |
| `docs/src/content/docs/decisions/0015-agent-identity.md` | 12 | 7 | Historical decision. |
| `docs/src/content/docs/decisions/0131-assisted-by-provenance.md` | 2 | 1 | Historical decision. |
| `docs/src/content/docs/guides/workflow-reference.md` | 1 | 1 | Generated guidance after #148 from `core/workflow_forms.py`. |
| `docs/src/content/docs/project/handoff-2026-09-26-prompt.md` | 0 | 7 | Dated handoff. |
| `docs/src/content/docs/project/plan.md` | 0 | 4 | Approved dated plan text. |
| `docs/src/content/docs/workflow/index.md` | 0 | 6 | Shared active workflow page after #148. |
| `reports/inputs/agent-identity-design.md` | 13 | 5 | Dated report. |
| `reports/inputs/bus-26-evidence-2026-09-26.md` | 0 | 1 | Dated report. |
| `reports/inputs/retro-2026-09-27-claims.md` | 1 | 1 | Dated report. |
| `reports/inputs/reviewer-account-evidence.md` | 0 | 4 | Dated report. |
| `research/gates/agent-identity/gh-identity-probes.md` | 5 | 1 | Research record. |
| `research/gates/agent-identity/security-cross-check.md` | 2 | 0 | Research record. |
| `research/gates/assisted-by/evidence.md` | 1 | 1 | Research evidence. |
| `research/gates/assisted-by/examples.md` | 4 | 1 | Research example. |
| `research/gates/github-events/evidence/issue-83-comments.txt` | 0 | 10 | Retained capture |
| `research/gates/github-events/evidence/issue-83.txt` | 0 | 6 | Retained capture |
| `research/gates/github-events/evidence/issue-89-comments.txt` | 0 | 14 | Retained capture |
| `research/gates/github-events/evidence/issue-89.txt` | 0 | 3 | Retained capture |
| `research/gates/github-events/evidence/issue-90-comments.txt` | 0 | 15 | Retained capture |
| `research/gates/github-events/evidence/issue-90.txt` | 0 | 5 | Retained capture |
| `research/gates/github-events/evidence/pr-82-comments.txt` | 0 | 72 | Retained capture |
| `research/gates/github-events/evidence/pr-82-reviews.txt` | 0 | 36 | Retained capture |
| `research/gates/github-events/evidence/review-reproduction.txt` | 0 | 1 | Retained capture |
| `research/gates/github-events/evidence/validation.txt` | 0 | 1 | Retained capture |
| `research/gates/github-events/notes.md` | 0 | 1 | Dated research notes. |
| `research/gates/retro-2026-09-27/evidence/issue-164-comments.jsonl` | 4 | 2 | Retained capture |
| `research/gates/retro-2026-09-27/evidence/pr-113.json` | 0 | 1 | Retained capture |
| `scaffolding/github-monitor/docs/project-feasibility.md` | 1 | 0 | Dated feasibility report. |
| `scaffolding/github-monitor/evidence/project-feasibility.md` | 2 | 0 | Retained capture |
| `scaffolding/github-monitor/evidence/repair.md` | 1 | 0 | Retained capture |
| `src/agent_orchestration_poc/core/workflow_forms.py` | 1 | 1 | Source of generated guidance after #148. |
| `src/agent_orchestration_poc/shell/project_rank.py` | 1 | 0 | Deferred #201 client for old Project. Do not use on the organization Project. |
| `tests/fixtures/review_identity/test_policy.py` | 0 | 1 | Negative test for the retired reviewer name. |
| `tests/fixtures/review_identity/wrapper.json` | 0 | 1 | Negative wrapper test for the retired reviewer name. |
| `tests/test_project_rank_shell.py` | 1 | 0 | Deferred #201 rank fixture. |

## Repository owner

| Reference | Before | After this delivery | Remaining reason |
| --- | ---: | ---: | --- |
| `github.com/tbhb/agent-orchestration-poc` matching lines | 268 | 237 | Historical links and shared Go module, imports, tooling, and workflow pages. Active monitor receiver and repair files are outside #215's allowed paths. |
| Current owner | `tbhb/agent-orchestration-poc` | `tbhb-dev/agent-orchestration-poc` in edited paths | Fixed repository ID `1389534135` is unchanged. |

`git grep -n 'github.com/tbhb/agent-orchestration-poc'` exited 0 and returned 237 matching lines after the edits. The Go module in `go.mod`, Go imports in `cmd/**` and `internal/**`, `.golangci.yml`, and build flags in `mise.toml` wait for #86, #97, #148, and #156 to land. `scaffolding/github-monitor/state.py`, `repair.py`, their tests, and the receiver fixture still use the old owner but are outside the allowed paths. Dated reports, research, evidence, and decision text remain unchanged. Current links in the independent site pages and guides now use the moved owner.

## Project location and fields

| Reference | Before | After this delivery | Remaining reason |
| --- | ---: | ---: | --- |
| Old Project path or web URL matching lines | 34 | 22 | Historical records, backfill source, #201 rank client, and shared current guidance. |
| Current Project REST path | `users/tbhb/projectsV2/9` | `orgs/tbhb-dev/projectsV2/1` in `project_probe.py` | The old Project remains the backfill source. |

`git grep -n -E 'users/tbhb/projectsV2/9|users/tbhb/projects/9'` exited 0 and returned 22 matching lines after the edits. The old path in the negative cursor test is deliberate. Current worker guidance and workflow pages wait for their upstream shared changes. The #201 GraphQL rank client still targets the personal Project and must not run on the organization Project before its own cutover is verified. Verification used REST reads and local tests only.

[schema] `github/docs@18945a31a4f2d97beb6c5c1a7479102e23c25727` at `$TMPDIR/github-events-98/github-docs/src/rest/data/fpt-2026-03-10/projects.json` defines organization Project, field, and item GET paths. [verified] `gh api 'orgs/tbhb-dev/projectsV2/1/fields?per_page=100'` exited 0 as `tbhb-agent` on 2026-09-27. The response exposed Status `417711744`, Area `417711771`, Harness `417711772`, Size `417711774`, Worker `417711775`, built-in Type `417711749`, Priority `417752960`, Severity `417752961`, Work type `417752962`, Validation `417753546`, and Validation detail `417753617`. Priority, Severity, and Work type had `issue_field_id` values `42589940`, `47483845`, and `47483934` respectively. These Project columns use their corresponding native issue field values. The former draft Priority ID `417711773` was absent. Phase `417711770` and the reported Stub class `417753887` were absent from this read, despite the issue's snapshot. No replacement ID was invented.

[observed] `mise run monitor:project-probe -- --rest-matrix` exited 0 with REST API version `2026-03-10`, HTTP 200 for the organization fields, organization items, and repository issue read. It reported `unknown/incomplete` because required Phase is absent from the field definitions. Its one-page sample and field counts do not prove a complete Project snapshot.

## Verification and size

[verified] `mise exec -- uv run pytest -q tests/fixtures/review_identity/test_policy.py tests/fixtures/review_identity/test_wrapper.py tests/test_project_probe.py` exited 0 with 74 passed and six integration cases skipped. `mise exec -- uv run pytest -q --run-integration tests/fixtures/review_identity/test_wrapper.py` exited 0 with six passed. `mise run worker:test-launcher` exited 0 with 169 passed. The wrapper fixture explicitly rejects the old reviewer name. The command test checks both Git author and committer names.

[verified] `mise run check` exited 0 after the inventory wording was corrected and a separate retry cleared a timeout in the unchanged relay integration test. Its coverage gates reported Python core lines 99.75%, branches 97.30%, shell lines 85.13%, Go core statements 96.43%, shell statements 74.58%, and core branches 94.74%. `mise run check:mutation` exited 0 with Go mutation score 97.32%, Go mutant coverage 100%, and Python core score 91.07%. `mise run build` and `mise run docs:build` exited 0. `git diff --check` and `git diff --cached --no-ext-diff | mise exec -- gitleaks stdin --redact --no-banner` exited 0, with no leaks found in the staged diff.

[observed] `mise run docs:check-links` exited 1 on this sandbox with a Chromium `browserType.launch` closure and seven invalid-link reports. The reported link targets are unchanged from `origin/main`. The normal docs build completed successfully. The link-check outcome remains unverified on CI at this point.

[verified] `mise run scc:version` reported scc 4.1.0. A merge-base `git diff --cached --unified=0 origin/main` count using the #84 nonblank prose and changed code-line rules measures 192 included units after this report update. Excluded fixture raw changes are `tests/fixtures/review_identity/policy.json` 24, `test_policy.py` 15, and `wrapper.json` 15. Changed Python docstrings contribute two excluded lines. This count is below the 400-unit target and the 800-unit limit. The PR body records the final recount if the staged diff changes again.
