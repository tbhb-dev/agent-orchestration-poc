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
PRAGMA user_version = 1;
```

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
