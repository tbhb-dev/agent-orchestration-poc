# BV-01 rerun readiness

Stage A for issue #228 began on 2026-09-28 at 21:04:05 EDT in `exp/228-harness-rerun` at `a33139b`. The operator's capture ask at `/Users/tony/Code/github.com/tbhb/agent-orchestration-design-poc/poc/asks/2026-09-28T2018-bv01-rerun.md` requires a new capture and positive control before any harness cell. Stage B follows the [merged runbook](../../stage-two-runbook.md) and [stage-two record](../stage-two/run.md). The focused tests started isolated loopback responder processes that exited. I did not launch a harness cell, cell responder, listener, tmux server, `eslogger`, or `sudo` command.

## Home reconciliation

The runbook's fresh-home test, `for name in codex-interactive codex-headless claude-interactive claude-headless; do test ! -e "/private/tmp/bv01-228-$name" || exit 1; done`, exited 1 because all four homes from the earlier stage-two attempt still exist. This is an expected mismatch with the operator's instruction to preserve them, not evidence that the homes should be removed. This rerun reuses all four homes and recreates none.

| Home | Decision | Reason and preparation |
| --- | --- | --- |
| `bv01-228-codex-headless` | Reuse | Mode 700. Previous capture files retained. Stale launch artifacts archived. Copied core refreshed. Config and launch script prepared. |
| `bv01-228-codex-interactive` | Reuse | Mode 700. Stale launch artifacts archived. Copied core refreshed. Config and launch script prepared. |
| `bv01-228-claude-headless` | Reuse | Mode 700; stale launch artifacts archived; copied core refreshed; onboarding, theme, and launch script prepared. |
| `bv01-228-claude-interactive` | Reuse | Mode 700; stale launch artifacts archived; copied core refreshed; onboarding, theme, and launch script prepared. |

Before the archive, `kill -0` found each recorded launch-root PID inactive: 62657, 80701, 767, and 14780 for Codex headless, Codex interactive, Claude headless, and Claude interactive respectively. `lsof -nP -U` found zero open `bv01-228` sockets. Each home's previous `go`, `root.pid`, `gateway.sock`, model and listener output, harness output where present, and prior `launch.sh` were moved into that home's mode-700 `rerun-prior-stage-two/`. Prior configs and the old copied core file were copied there. The previous `file-opens.json`, `file-opens.err`, and `file-opens.raw` in the Codex headless home remain at their original paths. I retained every capture file and home. The rerun capture names in the operator ask remain absent.

The copied `host_socket_attribution.py` had SHA-256 `ad8de2891c07921d177d3d6643477e3388ab1274aee54d803e3081b202cee1ab` in all four homes, while the merged source is `d15c8c2169ff24c823c324f9dc0afa4824c38df6fc68b3211a391de4bbaa3c9b`. Each copy now matches the merged source. The copied `probe.py` matched its source at `783c711f9bc2806b943cee6170d7fce2be2e37e4d95571bdbf2218490a2820e0` throughout.

## OP-33 checks

1. **Verified in tests, untested in a harness:** `model_responder.py` and the pure `responder_reply` decision accept `HEAD /v1/messages` with an empty 200 and `POST /v1/messages?beta=true` with the fixed Messages frame. They log method, raw path, and status for refusals too, and reject `/` and a wrong `Host`. The focused `mise exec -- uv run pytest tests/test_host_socket_attribution.py --run-integration -q` run passed 43 tests. No stage A responder instance was left running.
2. **Verified static configuration, untested launch:** the direct binary exists and reports `codex-cli 0.157.1`. Both prepared Codex launch scripts name `/Users/tony/.codex/packages/standalone/releases/0.157.1-aarch64-apple-darwin/bin/codex` directly. `sh -n` accepted all four launch scripts.
3. **Verified static settings, prompt behavior untested:** both Codex configs now mark only their own workspace `trusted`. Both Claude `claude/.claude.json` files now set `hasCompletedOnboarding` to `true` and `theme` to `dark`. Their earlier state is archived. The Claude sandbox settings still permit only each profile's own gateway socket and disallow all Unix sockets and local binding.
4. **Verified static settings, network behavior untested:** both Codex configs now set `check_for_update_on_startup = false` and `[features] plugins = false`. The merged runbook records that no announcement-fetch disabling key was found at the pinned source revision. Any announcement request is a stage B finding.

Each Codex config still contains the old responder port until the cell's new responder supplies a port. Stage B must update `base_url` before launching that Codex cell. The [stage B command list](stage-b-commands.md) makes this an explicit gate.

## Preflight results

| Command or check | Exit | Result |
| --- | ---: | --- |
| `date` before recording times | 0 | `Mon Sep 28 21:04:05 EDT 2026`. |
| `test -x` pinned Codex binary | 0 | Executable exists. |
| Pinned Codex binary `--version` | 0 | `codex-cli 0.157.1`. A sandbox warning said PATH aliases could not be created. |
| `sw_vers` and `uname -m` | 0 each | macOS 26.5.1, build 25F80, arm64. |
| `claude --version` | 0 | `2.1.284 (Claude Code)`. |
| `mise exec -- python --version` | 0 | Python 3.14.6. |
| `mise exec -- uv --version` | 0 | uv 0.12.10. |
| `git status --short` before evidence edit | 0 | Clean. |
| Runbook's homes-absent test | 1 | All retained homes exist. Reconciled above. |
| `stat -c '%a %n'` for four homes | 0 | All four are mode 700. |
| Copied file hashes | 0 | `probe.py` matched. Copied core differed and was refreshed. |
| Prepared launch scripts, `sh -n` | 0 | All parse. None was executed. |
| Post-preparation config, source, marker, and capture-name assertions | 0 | All homes prepared. Stale launch markers absent. Old capture retained. New capture names absent. |
| `mise run vale:sync` | 0 | Pinned prose styles synchronized once for this worktree. |
| Focused responder and fixture suite | 0 | 43 passed in 1.71 seconds. |
| `mise run fmt` | 0 | Tracked files remained unchanged after formatting. |
| `mise run check`, attempt 1 | 123 | Vale rejected prose in this record. The prose was revised. The exact output is in `check-attempt-1.raw.gz`. |
| `mise run check:vale` and `mise run check:rumdl` | 0 each | Both prose checks passed. |
| `mise run check`, attempt 2 | 1 | Vale passed. The Quarto notebook integration test failed because this sandbox denied a log write under `~/Library/Application Support/quarto/logs/`. The exact output is in `check-attempt-2.raw.gz`. |
| Targeted Quarto notebook test with disposable `HOME` | 0 | The same integration test passed in 17.08 seconds with `HOME=/private/tmp/quarto-228-check-home` and the pinned uv cache. |
| `mise run check`, attempt 3 with disposable `HOME` | 1 | mise stopped before checks because the project config is not trusted for that HOME. I did not change mise trust. The exact output is in `check.raw.gz`. |
| `/usr/bin/pgrep -x eslogger` | 3 | This sandbox cannot query `sysmond`. The operator's capture preflight must check it in the Full Disk Access terminal. |

The process-list limitation does not replace the operator's capture preflight. The aggregate check is not green because the notebook renderer's default log path and mise's alternate-HOME trust state are outside this worker's writable roots. The focused responder suite, prose checks, and targeted notebook test passed. The operator starts the new capture and confirms its positive control before the stage B commands run. No profile is qualified by these readiness checks.
