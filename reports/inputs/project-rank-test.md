# Project rank script evidence

## Scope and source

Verified: issue #201's reviewed body and the ready verdict at issue comment 5856425062 define this worker's scope. The approved work model section 4 at `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/reorg/2026-09-27-work-model.md` defines `move`, a complete issue order, and `replace <item id> with <issue>`. The `replace` plan positions the replacement issue before the old Standard draft. The intake workflow owns deletion of the draft.

Schema: the [GitHub.com Projects GraphQL reference](https://docs.github.com/en/graphql/reference/projects), read 2026-09-27, defines `ProjectV2.items(orderBy: ProjectV2ItemOrder)`, `ProjectV2ItemOrderField.POSITION`, `fieldValueByName`, `updateProjectV2ItemPosition(input:)`, its payload's `clientMutationId`, and its `projectId`, `itemId`, and nullable `afterId` inputs. Its schema text says null `afterId` moves an item to the top. The [GitHub.com Meta GraphQL reference](https://docs.github.com/en/graphql/reference/meta), read 2026-09-27, lists `rateLimit` on Query, not Mutation. The [GitHub.com GraphQL rate limit reference](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api), read 2026-09-27, defines response `x-ratelimit-remaining` and Query `rateLimit { remaining cost }`. It describes five secondary points for a mutation, which this script uses only as a planning estimate. These are live GitHub.com documentation pages as accessed on that date, without a stable release tag. No GraphQL request was made for this implementation.

Documented: Python 3.14.6, uv 0.12.10, ruff 0.16.9, pytest 9.1.1, Hypothesis 6.168.1, mutmut 3.8.0, and pyrefly 1.3.1 are pinned in `mise.toml`, `pyproject.toml`, and the repository's Python conventions. The repository's Python research gate records source commits at `research/gates/python/versions.md`.

## Request and response shapes

[Observed] The current query uses `organization(login:$owner)` for `tbhb-dev` Project 1 and requests each item's node `id`, `fullDatabaseId`, type, issue content, Priority, and Type, plus position ordering, pagination, and `rateLimit`. A read-only live call returned Project data, but local validation refused blank Priority fields before a plan. The shell requires `data.organization.projectV2.items`, `data.rateLimit`, and the `x-ratelimit-remaining` header and refuses missing pages, fields, cursors, header budget, and GraphQL errors.

Untested runtime mutation shape: `mutation($project:ID!,$item:ID!,$after:ID){updateProjectV2ItemPosition(input:{projectId:$project,itemId:$item,afterId:$after}){clientMutationId}}`. The response supplies `data.updateProjectV2ItemPosition` and the `x-ratelimit-remaining` header. The shell records the decrease from the preceding query or mutation response header as observed interval cost; concurrent use of the same rate-limit bucket can make this value an upper bound, and a nonpositive difference is refused. The coordinator alone supplies the GitHub account and runs `--apply` under the host lock. The default command only prints a plan.

## Fixture observations

Verified: `mise exec -- uv run pytest tests/test_project_rank.py tests/test_project_rank_shell.py --run-integration -q` exited 0 with 32 tests. Core table cases cover a move, complete ordered list, draft replacement, non-Standard item, closed item, parent, changed order, planned and pending cost, and low budget. Hypothesis explores all permutations of five Standard issues, move relations, and pending-budget thresholds. Shell process cases use a local fake `gh` executable for failed reads, pagination, changed order, low budget, and a successful read-back. The fake rejects a mutation selecting Query-only `rateLimit`, and its mutation response contains only the schema-supported payload. A missing issue fails in the dry-run process fixture. The fake executable made no network request.

Verified: `mise exec -- uv run python -m agent_orchestration_poc.shell.project_rank --fixture /tmp/project-rank-201-fixture.json move 3 above 1` exited 0 with `planned mutations: 1`, `planned requests: 3`, `estimated points: 9`, and `itemId=I3 afterId=None`. The temporary fixture held three invented open Standard issues with Project item IDs `I1`, `I2`, and `I3`, remaining budget 500, and read cost 2. This command did not contact GitHub.

Verified: `mise run check:imports`, `mise run check:ruff`, `mise run check:pyrefly`, `mise run check:deadcode`, and `mise run check:dupl` exited 0. After the review changes, `mise run check` exited 0 with 240 Python tests in its integration coverage pass. Python core lines and branches reached 99.73 and 96.77 percent, and aggregate Python shell lines reached 85.13 percent. The rank shell module reached 84 percent line coverage. `check:secrets` reported no leaks in the committed history.

Verified: after the review changes, `mise run check:mutation` exited 0 with 1227 killed of 1338 Python core mutants, a 91.70 percent score, and 145 killed of 149 Go core mutants, a 97.32 percent score. The rank core was included in the Python mutation run.

## Coordinator runtime observations

Untested order: the coordinator must move one Standard item and restore it, then compare `POSITION` reads before, after, and after restoration.

Untested board columns: the coordinator must check that the native order holds within each Status column after the move and restoration.

Untested view reach: the coordinator must compare at least two Project views to determine whether they share one native order.

Untested REST read: the coordinator must compare `GET orgs/tbhb-dev/projectsV2/1/items` with the position order after the move and restoration.

## Project 1 and draft-order correction

[Verified from source] The 2026-10-01 target is organization Project 1 (`tbhb-dev`), and the effective agent login is `tbhb-agent`. The command now routes GitHub reads and writes through the repository's `.holding/bin/gh-as-agent` wrapper, uses `gh query` for read-only requests, and reserves `gh api` for a requested position mutation. The [GitHub Projects GraphQL schema](https://docs.github.com/en/graphql/reference/projects) defines `ProjectV2Item.fullDatabaseId` and `updateProjectV2ItemPosition` with item node IDs. `order-items ID...` accepts each open Standard issue or draft exactly once, with either its REST numeric Project item ID or GraphQL node ID, and resolves each planned mutation to a node ID. The existing numbered `order N...` command remains for issue-only use.

[Verified] `mise exec -- uv run pytest -q tests/test_project_rank.py tests/test_project_rank_shell.py --run-integration` passed 34 tests. The fixtures cover a mixed issue-and-draft order, duplicate or missing identifiers, the organization response shape, account check, re-read, budget refusal, and mutation read-back. `mise run check` and `mise run build` exited 0. A read-only live invocation, `scripts/project-rank order-items x`, reached the current Project and exited 2 with `item field read is incomplete`, as expected before native Priority values are populated; it made no mutation. No step 7 move or restoration has run, so native position behavior remains untested.

[Verified] `mise run check:mutation:python` exited 0 with a 90.25 percent Python core score (8,427 killed of 9,337 mutants). The first `mise run check` exited 0 with 715 integration-coverage tests. Two later aggregate retries stopped at the unrelated synthetic Quarto notebook test because this sandbox denied a log write under `/Users/tony/Library/Application Support/quarto/logs/`; the remaining rank fixtures passed after the process-test correction. No host permission change was made.

Untested point cost: the coordinator must record each query's `rateLimit.cost`, each mutation's before-and-after `x-ratelimit-remaining` headers, remaining points, and sanitized response headers during the move and restoration. No live cost is inferred from schema support or the fixture values.

Inference: if native position fails any required runtime behavior, the operator must decide whether to adopt the work model's Rank number-field fallback. This PR does not implement or select that fallback.

## Size and gates

Verified: `mise exec go:github.com/boyter/scc/v4@4.1.0 -- scc --by-file --format json` over the two Python modules, script, and two test files counted 684 code-line units: 126 core, 222 shell, 2 script, 136 core tests, and 198 shell tests. This is below the 800-unit split limit. `reports/inputs/` is excluded. The earlier conservative estimate was 659 units before the review changes.

Verified: `mise run check` final exit code 0.

Verified: `mise run build` exited 0.

Verified: `mise exec -- gitleaks dir --redact --no-banner <file>` exited 0 for each of the six new files and reported no leaks. The code commit's staged gitleaks hook passed. The report contains invented fixture IDs and request shapes only, with no token or key.

Untested: live GraphQL behavior and the work model site page, which awaits the coordinator's runtime test and is outside issue #201's allowed paths.
