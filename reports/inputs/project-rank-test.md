# Project rank script evidence

## Scope and source

Verified: issue #201's reviewed body and the ready verdict at issue comment 5856425062 define this worker's scope. The approved work model section 4 at `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/reorg/2026-09-27-work-model.md` defines `move`, a complete issue order, and `replace <item id> with <issue>`. The `replace` plan positions the replacement issue before the old Standard draft. The intake workflow owns deletion of the draft.

Schema: the [GitHub.com Projects GraphQL reference](https://docs.github.com/en/graphql/reference/projects), read 2026-09-27, defines `ProjectV2.items(orderBy: ProjectV2ItemOrder)`, `ProjectV2ItemOrderField.POSITION`, `fieldValueByName`, `updateProjectV2ItemPosition(input:)`, and its `projectId`, `itemId`, and nullable `afterId` inputs. Its schema text says null `afterId` moves an item to the top. The [GitHub.com GraphQL rate limit reference](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api), read 2026-09-27, defines response `x-ratelimit-remaining` and `rateLimit { remaining cost }`. It describes five secondary points for a mutation, which this script uses only as a planning estimate. These are live GitHub.com documentation pages as accessed on that date, without a stable release tag. No GraphQL request was made for this implementation.

Documented: Python 3.14.6, uv 0.12.10, ruff 0.16.9, pytest 9.1.1, Hypothesis 6.168.1, mutmut 3.8.0, and pyrefly 1.3.1 are pinned in `mise.toml`, `pyproject.toml`, and the repository's Python conventions. The repository's Python research gate records source commits at `research/gates/python/versions.md`.

## Request and response shapes

Untested runtime query shape: `query($owner:String!,$number:Int!,$after:String){user(login:$owner){projectV2(number:$number){id items(first:100,after:$after,orderBy:{field:POSITION,direction:ASC}){totalCount pageInfo{hasNextPage endCursor} nodes{id type content{... on Issue{number state}} priority:fieldValueByName(name:"Priority"){... on ProjectV2ItemFieldSingleSelectValue{name}} workType:fieldValueByName(name:"Type"){... on ProjectV2ItemFieldSingleSelectValue{name}}}}}} rateLimit{remaining cost}}`. The response supplies `data.user.projectV2.items`, `data.rateLimit`, and the `x-ratelimit-remaining` header. The shell refuses missing pages, fields, cursors, header budget, and GraphQL errors.

Untested runtime mutation shape: `mutation($project:ID!,$item:ID!,$after:ID){updateProjectV2ItemPosition(input:{projectId:$project,itemId:$item,afterId:$after}){clientMutationId} rateLimit{remaining cost}}`. The response supplies `data.updateProjectV2ItemPosition`, `data.rateLimit`, and the `x-ratelimit-remaining` header. The coordinator alone supplies the GitHub account and runs `--apply` under the host lock. The default command only prints a plan.

## Fixture observations

Verified: `mise exec -- uv run pytest tests/test_project_rank.py tests/test_project_rank_shell.py --run-integration` exited 0 with 23 tests. Core table cases cover a move, complete ordered list, draft replacement, non-Standard item, closed item, parent, changed order, and low budget. Hypothesis explores all permutations of five Standard issues and move relations. Shell process cases use a local fake `gh` executable for failed reads, pagination, changed order, low budget, and a successful read-back. A missing issue fails in the dry-run process fixture. The fake executable made no network request.

Verified: `mise exec -- uv run python -m agent_orchestration_poc.shell.project_rank --fixture /tmp/project-rank-201-fixture.json move 3 above 1` exited 0 with `planned mutations: 1`, `planned requests: 3`, `estimated points: 9`, and `itemId=I3 afterId=None`. The temporary fixture held three invented open Standard issues with Project item IDs `I1`, `I2`, and `I3`, remaining budget 500, and read cost 2. This command did not contact GitHub.

Verified: `mise run check:imports`, `mise run check:ruff`, `mise run check:pyrefly`, `mise run check:deadcode`, and `mise run check:dupl` exited 0. The final `mise run check` exited 0 with 231 Python tests in its integration coverage pass. Python core lines and branches reached 99.72 and 96.77 percent, and aggregate Python shell lines reached 85.13 percent. The rank shell module reached 80 percent line coverage. `check:secrets` reported no leaks in the committed history.

Verified: `mise run check:mutation` exited 0 with 1204 killed of 1314 Python core mutants, a 91.63 percent score, and 145 killed of 149 Go core mutants, a 97.32 percent score. The rank core was included in the Python mutation run.

## Coordinator runtime observations

Untested order: the coordinator must move one Standard item and restore it, then compare `POSITION` reads before, after, and after restoration.

Untested board columns: the coordinator must check that the native order holds within each Status column after the move and restoration.

Untested view reach: the coordinator must compare at least two Project views to determine whether they share one native order.

Untested REST read: the coordinator must compare `GET users/tbhb/projectsV2/9/items` with the position order after the move and restoration.

Untested point cost: the coordinator must record each query and mutation `rateLimit.cost`, remaining points, and sanitized response headers during the move and restoration. No live cost is inferred from schema support or the fixture values.

Inference: if native position fails any required runtime behavior, the operator must decide whether to adopt the work model's Rank number-field fallback. This PR does not implement or select that fallback.

## Size and gates

The full #84 estimate is 659 changed code-line units across the two Python modules, script, and two test files. The per-file conservative count is 130 core, 224 shell, 2 script, 111 core tests, and 192 shell tests. The command `awk 'NF && $0 !~ /^[[:space:]]*#/ { count[FILENAME]++ } END { for (path in count) print path, count[path] }'` over those five files counted nonblank, non-comment lines. This is an upper bound on the pending `scc` classification and below the 800-unit split limit. `reports/inputs/` is excluded. `mise exec -- scc --version` exited 1 because the `scc` binary is absent in this worktree. No shared `mise.toml` edit or installation was attempted.

Verified: `mise run check` final exit code 0.

Verified: `mise run build` exited 0.

Verified: `mise exec -- gitleaks dir --redact --no-banner <file>` exited 0 for each of the six new files and reported no leaks. The code commit's staged gitleaks hook passed. The report contains invented fixture IDs and request shapes only, with no token or key.

Untested: live GraphQL behavior and the work model site page, which awaits the coordinator's runtime test and is outside issue #201's allowed paths.
