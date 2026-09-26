# Phase 1 checkpoint collection

Collection date: 2026-09-26. Repository: tbhb/agent-orchestration-poc. Worker: Codex. The runtime did not expose the launch model or effort to this writer. JSON outputs use `.json.txt` to preserve command output without JSON formatter changes. The required commit hooks trim trailing whitespace and add final newlines to text outputs. No credentials were requested. GitHub masks the token value in the CI log as `***`.

## Initial requested commands

| Command | Output |
| --- | --- |
| `git log --format='%h %ad %s' --date=iso main` | `git-log.txt` |
| `gh pr list --state merged --limit 40 --json number,title,createdAt,mergedAt,additions,deletions,changedFiles` | `merged-prs.json.txt` |
| `gh pr list --state open` | `open-prs.txt` |
| `gh issue list --state all --limit 100 --json number,title,state,labels` | `issues.json.txt` |
| `gh run list --limit 40 --json workflowName,conclusion,headBranch,createdAt,databaseId` | `runs.json.txt` |
| `git worktree list` | `worktrees.txt` |

## Additional queries

- `gh run list --limit 100 --json workflowName,conclusion,headBranch,createdAt,databaseId` produced `runs-expanded.json.txt`, with 62 runs.
- `gh pr list --state all --limit 40 --json number,headRefName,state,reviews,createdAt,mergedAt` produced `reviews.json.txt`.
- The merged and pending PR commands were repeated into `merged-prs-refresh.json.txt` and `open-prs-refresh.txt` after PR #68 merged.
- `gh pr view 68 --json number,state,mergedAt,headRefName` produced `pr-68.json.txt`.
- `gh query repos/tbhb/agent-orchestration-poc/rulesets/24053242` produced `main-ruleset.json.txt`.
- `gh query repos/tbhb/agent-orchestration-poc/issues/6/events` produced `issue-6-events.json.txt`.
- `gh run view 36273718796 --log-failed` produced `ci-failure.txt`.
- `filed-issues.json.txt` records the five follow-up issue URLs and where their checks will run. Each was added to Project 9 with `gh project item-add 9 --owner tbhb --url <url>`.

## Derivations and limits

Filter merged PRs to numbers at least 19, sort by `mergedAt`, and subtract `createdAt` from `mergedAt` in UTC. The refreshed sample has 15 phase 1 PRs. Minimum 73 seconds, median 264 seconds, maximum 688 seconds. All 15 review arrays are empty. These durations measure creation to merge, not review turnaround. No first-review latency can be calculated.

The initial 40-run sample has 37 successes and three cancellations. The expanded 62-run sample has 56 successes, three cancellations, two unfinished runs, and one failure. The failure log identifies rumdl MD057 at HANDOFF.md:27 for a local git metadata link. The phase 1 merge sequence is #19, #20, #21, #24, #22, #23, #25, #56, #55, #57, #64, #66, #67, #65, #68. The timestamps correct the raw input's order for #65 through #67.

The initial worktree and issue records precede the refresh. Worktree presence does not establish worker liveness. Formal reviews do not capture coordinator shell activity. The issue snapshot cannot reconstruct historical Project status transitions. Session duration, permission denials, usage meters, and worker silence are coordinator inputs, not independently timed experiments here.

## Final worktree check and local validation

The final `git worktree list` is in `worktrees-final.txt`. The research worktree was removed after PR #68 merged. `open-prs-final.txt` is the repeated pending-PR query before creating the checkpoint PR.

`mise run fmt`, `mise run check`, and `mise run build` passed. The check and build logs are committed here. `gitleaks dir --redact --no-banner reports/inputs`, run through `mise exec`, passed and its log is `input-secret-scan.txt`. The normal staged secret hook also runs on each commit.

The first formatter attempt could not write the default uv cache. Local validation used `UV_CACHE_DIR=/tmp/phase1-uv-cache`, `GOCACHE=/tmp/phase1-go-cache`, and `GOMODCACHE=/tmp/phase1-go-modcache`. These writable temporary caches leave the sandbox policy unchanged. Docs rendering and link validation are delegated to the PR docs job because the recorded Codex environment blocks Chromium.
