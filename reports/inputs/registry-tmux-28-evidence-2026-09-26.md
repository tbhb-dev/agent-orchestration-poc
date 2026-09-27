# Registry and tmux evidence for issue #28

## Versions and source records

| Component | Pin or commit | Evidence |
| --- | --- | --- |
| Go | 1.27.1 from `mise.toml` | `mise exec -- go version` reported `go1.27.1 darwin/arm64` |
| `modernc.org/sqlite` | v1.59.0, source commit `c96a4e6cb22254bf70026502a781a54a053c2cf0` | `/private/tmp/agent28-modernc-sqlite` |
| `modernc.org/libc` | v1.75.7 | Exact matching pin in the SQLite v1.59.0 `go.mod` |
| `github.com/mattn/go-sqlite3` | v1.14.52, source commit `b0be46fa28d17ee0b65c79774ac0dad84b6db068` | `/private/tmp/agent28-mattn-sqlite3` |
| tmux | 3.7b | `mise exec -- tmux -V` and the private server test |
| Codex CLI | 0.157.1 | `mise exec -- codex --version`, worker harness for this change |
| Model and effort | `gpt-6-sol`, high | Coordinator assignment |

**Observed:** the sandbox blocked writes under `~/Code/github.com`, so both dependency sources were cloned under `/private/tmp`. The coordinator can clone the recorded commits in the standard dependency source location. The Go module cache also required a writable `GOPATH=/private/tmp/agent28gopath` for the local checks.

## Driver comparison and raw notes

**Documented:** `modernc.org/sqlite` v1.59.0 `README.md` calls the driver pure Go with no cgo. `doc.go` lines 5 and 56 to 69 describe a `database/sql` driver and list macOS arm64 and Linux arm64 with SQLite 3.53.4. `sqlite.go` lines 55 to 56 register the `sqlite` driver. `CHANGELOG.md` under v1.59.0 states the `modernc.org/libc` pin is v1.75.7 and says downstream modules must match it. The same release notes report higher CPU time than comparable C builds on three measured workloads. Source read at `c96a4e6cb22254bf70026502a781a54a053c2cf0`.

**Documented:** `github.com/mattn/go-sqlite3` v1.14.52 `README.md` says the package conforms to `database/sql` and requires cgo, `CGO_ENABLED=1`, and a C compiler. `sqlite3.go` imports `C` at line 307. The [v1.14.52 release](https://github.com/mattn/go-sqlite3/releases/tag/v1.14.52) changes the cached statement schema probe. Source read at `b0be46fa28d17ee0b65c79774ac0dad84b6db068`.

**Decision:** pin `modernc.org/sqlite` v1.59.0 and `modernc.org/libc` v1.75.7. This keeps the `agentd` binary and Linux CI independent of a C toolchain. The registry is a small roster store, so the CPU cost noted in the release is acceptable. [Decision 0005](/decisions/0005-sqlite-driver/) records the choice.

## Registry schema

**Schema:** `internal/registry/schema.sql` is embedded in the registry package and applied at `user_version = 0`. The schema at this commit is:

```sql
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS groups (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  repo_path TEXT NOT NULL,
  tmux_session TEXT NOT NULL UNIQUE,
  tmux_generation TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL CHECK (state IN ('requested','starting','running','stopping','stopped','failed')),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workers (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL REFERENCES groups(id),
  name TEXT NOT NULL,
  harness TEXT NOT NULL CHECK (harness IN ('claude','codex','agy')),
  model TEXT NOT NULL,
  effort TEXT NOT NULL,
  issue INTEGER NOT NULL,
  kind TEXT NOT NULL,
  slug TEXT NOT NULL,
  branch TEXT NOT NULL,
  worktree_path TEXT NOT NULL UNIQUE,
  brief_path TEXT NOT NULL,
  credential_path TEXT NOT NULL,
  window_id TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL CHECK (state IN ('requested','starting','running','stopping','stopped','failed')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (group_id, name)
);
PRAGMA user_version = 2;
```

**Verified:** the version 1 to version 2 migration adds the empty `tmux_generation` column to existing group records. An old live session has no ownership marker and must be stopped outside this API before its record can be reconciled. A newly started session receives a random generation stored in SQLite and in a tmux session option; each new window receives its worker ID as a tmux window option.

## Review regression evidence

**Observed:** before the fixes, `mise exec -- go test ./internal/core/launch -run TestClaudePromptAfterDirectoryOptions -count=1` failed because the Claude argv tail lacked `--` between `/repo/.git` and the prompt. The installed Claude Code 2.1.283 help advertises variadic `--add-dir <directories...>`; this is a parser-boundary check, not a real Claude launch.

**Observed:** before the fixes, `mise exec -- go test -tags integration -run 'TestRejectReusedWindowID|TestGroupStopAfterWindowExitAndRetry' -count=1 -v ./internal/provision` failed both private-server stand-in tests. `TestRejectReusedWindowID` captured a replacement window through a stale record. `TestGroupStopAfterWindowExitAndRetry` failed with `tmux kill-window: exit status 1: can't find window: @1`.

**Verified:** after the fixes, the two regression tests and `TestGroupOperationsOnPrivateServer` passed. The replacement-server test checks capture, nudge, and stop all reject the old record and that the replacement window remains alive. The exit test removes a window before group shutdown, then repeats the shutdown and confirms the group and worker are stopped. The tmux integration suite also distinguishes a missing server from an unexpected socket error. Core value tests cover the Claude settings artifact, shutdown eligibility, and generation and worker-marker comparisons. `TestMigrateV1Group` exercises the schema upgrade.

**Verified:** `GOLANGCI_LINT_CACHE=/private/tmp/agent28-golangci-cache mise run check:go` passed, including the race-enabled Go suite. The cache override was needed because this worker sandbox cannot write the default golangci-lint cache under `~/Library/Caches/golangci-lint`. No real harness session was started.

**Verified:** `GOLANGCI_LINT_CACHE=/private/tmp/agent28-golangci-cache mise run check` passed after the review fixes. The aggregate includes Go race tests, Python's 52 passing tests with two integration skips, lint, formatting, boundary checks, and repository guards. `mise run build` passed. `mise run check:mutation` passed with 149 of 153 Go mutants killed, four survivors, zero uncovered mutants, zero timeouts, 97.39% efficacy, and 100% mutant coverage. Python killed 200 of 240 mutants for 83.33% with 100% line coverage.

## Local checks and tmux capture

**Verified:** `GOPATH=/private/tmp/agent28gopath GOCACHE=/private/tmp/agent28gocache mise exec -- go test ./internal/core/launch ./internal/core/roster ./internal/registry` passed on this worktree. The file backed registry test inserted a group and worker, reopened the database, updated state, listed workers, and rejected a duplicate.

**Observed:** `GOPATH=/private/tmp/agent28gopath GOCACHE=/private/tmp/agent28gocache mise exec -- go test -tags integration -run TestPrivateServerStandIn -v ./internal/backend/tmux` used `tmux -L <unique-socket-name>` and only its own `build` session. It started a stand-in `sh` command, read a brief path containing a quote and a space, received its group environment value, pasted the fixed pointer, sent Enter, and cleaned up its window and server. No real harness ran.

```text
=== RUN   TestPrivateServerStandIn
    tmux_integration_test.go:66: stand-in capture: STANDIN BRIEF
        GROUP:build
        Check agentctl for pending messages.
        INPUT:Check agentctl for pending messages.
--- PASS: TestPrivateServerStandIn (0.57s)
PASS
ok   github.com/tbhb/agent-orchestration-poc/internal/backend/tmux 0.756s
```

**Verified:** `mise exec -- go test ./internal/bus -run TestRegisterAgent -count=1` passed with the embedded NATS server. The test reloaded a new worker identity, checked mode 0600 on its seed file, and authenticated with the new seed.

**Observed:** `mise exec -- go test -tags integration -run TestGroupOperationsOnPrivateServer -v ./internal/provision` exercised the local Unix socket and registry with a private tmux server. Group start and status, list, capture, nudge, worker stop, and group stop passed with a stand-in command. The service capture was:

```text
=== RUN   TestGroupOperationsOnPrivateServer
    provision_integration_test.go:103: provisioner capture: STANDIN SERVICE BRIEF
        Check agentctl for pending messages.
        INPUT:Check agentctl for pending messages.
--- PASS: TestGroupOperationsOnPrivateServer (0.75s)
PASS
ok   github.com/tbhb/agent-orchestration-poc/internal/provision 1.125s
```

**Verified:** `mise run check:vale`, `mise run check:rumdl`, `mise run check:guard-markdown`, and `mise run check:dupl` passed after formatting. `mise exec -- gitleaks dir --redact --no-banner reports/inputs/registry-tmux-28-evidence-2026-09-26.md` found no leaks in this evidence file.

**Observed:** `mise run docs:check-links` could not complete in this sandbox because Playwright's Chromium exited at `bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer: Permission denied (1100)`. The rendered route list included the new provisioner, decision, and build group pages, but the pre-existing Mermaid content in `workflow/index.md` failed to render and the link validator then reported missing `/workflow/` links. CI must confirm the full docs build outside this sandbox.

## Main merge and entry point

**Observed:** `git fetch origin && git merge origin/main` stopped because this branch has fast-forward-only merge configuration. `git merge --no-ff origin/main` reached add/add conflicts from the squash of PR #82. The resolution kept the merged `main` bus, layout, tests, and evidence, while retaining this branch's SQLite additions to `go.mod` and `go.sum`.

**Observed:** Before mounting the provisioner, `mise run check` failed at `check:deadcode`: `serveWithOperations`, `runOperation`, and the provisioner, registry, and tmux functions were unreachable from a binary. After `cmd/agentd/main.go` dispatched the provisioner commands and used `serveWithOperations`, the same aggregate check passed. Its Go boundary and dead code checks passed, the race-enabled Go tests passed, and Python reported 52 passed and two integration tests skipped.

**Observed:** `mise run build` passed. A temporary-directory smoke run started `bin/agentd serve` on a free loopback port, waited for `<state-dir>/agentd.sock`, then called `bin/agentd group status` and `bin/agentd list`. The first response reported the `build` group as stopped and included its private tmux socket; the second returned an empty worker list. The daemon printed its NATS URL and `<state-dir>/bus` credential root. The temporary state and process were removed at the end of the run. This checks the binary dispatch and local socket, not a real harness spawn.

**Observed:** `mise run check:mutation` passed at the then-configured floors. The Go core run killed 135 of 139 mutants, with four survivors, zero uncovered mutants, zero timeouts, 97.12% test efficacy, and 100% mutant coverage. The Python core run killed 200 of 240 mutants for 83.33% and reported 100% line coverage. The four Go survivors are in the launch and roster core.

**Observed:** `mise run docs:check-links` again failed in this sandbox. Chromium could not register `org.chromium.Chromium.MachPortRendezvousServer` (`Permission denied (1100)`), and the link validator reported three existing `/workflow/` links in `index.md`, `project/history.md`, and `workflow/tooling.md`. The edited bus and provisioner pages rendered; this local run does not establish a green docs check.

**Observed:** `origin/main` advanced again to `1c745ff` before push. Merge commit `83698b0` brought in its workflow checks without file conflicts. After that merge, `mise run check` passed, including the added ignore-collision and handoff-classifier checks. `mise run check:mutation` passed again with the same 135/139 Go and 200/240 Python killed-mutant results recorded above.

## Raised floors after PR #105

**Observed:** `git fetch origin && git merge origin/main` stopped at the branch's fast-forward-only merge setting. `git merge --no-ff origin/main` conflicted only in `cmd/agentd/main.go`. The resolution keeps this branch's provisioner operations and main's shared version and usage dispatcher.

**Observed:** The first completed `mise run check:coverage` after that resolution measured Python core lines 100.00% against 95%, Python core branches 93.75% against 90%, Python shell lines 75.93% against 70%, Go core statements 89.94% against 95%, Go core branches 85.94% against 90%, and Go shell statements 59.94% against 70%. The first direct task attempt could not install the newly pinned gobco tool under the sandbox-protected home directory. A disposable mise data directory and Go sum database under `/tmp` allowed the pinned task to run without changing repository configuration.

**Verified:** Added plain-value tests for invalid launch specifications and roster records, CLI operation argument tests, and a private-tmux stand-in test of worktree creation, brief and settings writes, bus registration, live window ownership, and registry update. The subsequent `mise run check:coverage` passed: Python core lines 100.00%, Python core branches 93.75%, Python shell lines 75.93%, Go core statements 98.32%, Go core branches 91.41%, and Go shell statements 70.55%. No real harness was launched.

**Verified:** `mise run check:mutation` passed with 155 of 157 Go mutants killed, two survivors, zero uncovered or timed-out mutants, 98.73% efficacy, and 100% mutant coverage. Python killed 418 of 427 mutants for 97.89%. Both core mutation scores exceed the raised 90% floor.

**Verified:** `mise run check` passed after formatting, including lint, import boundaries, race-enabled Go tests, Python tests, the repository guards, and the six coverage floors listed above. `mise run build` passed. The built binary printed `agentd dev` for `version`, and `agentd group` returned `group requires start, stop, or status`, confirming that the conflict resolution preserved both the shared version dispatcher and provisioner command routing.

**Observed:** While those checks ran, `main` advanced to `b041b06`. Merge commit `7e5e3ad` brought in the event monitor design, data analysis gate, and reviewer identity policy without another file conflict. The remote `main` tip still matched `b041b06` before the final push.

**Verified:** `mise run check` passed again after the second merge, including the new reviewer identity task. Coverage was Python core lines 100.00%, Python core branches 94.00%, Python shell lines 77.54%, Go core statements 98.32%, Go core branches 91.41%, and Go shell statements 70.55%. `mise run check:mutation` also passed again: Go killed 155 of 157 mutants for 98.73% efficacy and 100% mutant coverage, with no uncovered or timed-out mutants; Python killed 454 of 467 mutants for 97.22%.

**Observed:** The first pushed Linux `check` job failed before scoring Go coverage because the shared private-tmux integration helper created test state under macOS-only `/private/tmp`. The job log showed `stat /private/tmp: no such file or directory` for the provisioner integration tests. The helper now asks Go for the system temp directory. `go test -tags=integration -count=1 ./internal/provision` and the full `mise run check` passed locally with the portable path. The [next Linux check job](https://github.com/tbhb/agent-orchestration-poc/actions/runs/36291285299/job/108541740099) passed, as did docs, imported research, mutation, and PR body checks.

## Operator acceptance procedure

**Untested:** the following commands need the operator's subscriptions, user-scope sandbox settings, and a host location outside this worker sandbox. Run them from a trusted checkout of the feature branch. Use three prepared brief files that each ask the worker to read the file, make a small issue-scoped change, stage it, and commit it. The commands use distinct issue #28 acceptance branches so they cannot share a worktree.

```sh
STATE=/absolute/operator/state/agentd-28
mise run build
bin/agentd serve --state-dir "$STATE" --port 4222
```

In a second terminal:

```sh
STATE=/absolute/operator/state/agentd-28
bin/agentd group start --state-dir "$STATE"
bin/agentd spawn --state-dir "$STATE" --name claude-acceptance --harness claude --model claude-opus-5-5 --effort medium --issue 28 --type feat --slug claude-acceptance --brief "$STATE/claude-brief.md"
bin/agentd spawn --state-dir "$STATE" --name codex-acceptance --harness codex --model gpt-6-sol --effort high --issue 28 --type feat --slug codex-acceptance --brief "$STATE/codex-brief.md"
bin/agentd spawn --state-dir "$STATE" --name agy-acceptance --harness agy --model gemini-3.1-pro-high --effort high --issue 28 --type feat --slug agy-acceptance --brief "$STATE/agy-brief.md"
bin/agentd list --state-dir "$STATE"
bin/agentd capture --state-dir "$STATE" --name claude-acceptance --lines 100
bin/agentd capture --state-dir "$STATE" --name codex-acceptance --lines 100
bin/agentd capture --state-dir "$STATE" --name agy-acceptance --lines 100
bin/agentd group status --state-dir "$STATE"
```

**Untested:** verify the three captures show each harness reading its brief and the three worktrees can stage and commit. Verify the bus accepts each worker credential. After preserving the transcripts, stop each worker with `bin/agentd stop --state-dir "$STATE" --name <name>` and run `bin/agentd group stop --state-dir "$STATE"`. Review the worktrees before removing them.
