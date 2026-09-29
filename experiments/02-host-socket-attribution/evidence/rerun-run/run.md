# BV-01 stage B harness rerun

The Codex executor ran the four stage B cells for issue #228 on 2026-09-28, beginning after the operator reported that the filtered `eslogger open` capture and its positive control were running. The one-time gate found the control in the new capture, and its error file was empty. The direct Codex binary reported `codex-cli 0.157.1`, while Claude reported `2.1.284 (Claude Code)`. The worktree was `exp/228-harness-rerun` at `94a3b90` before this evidence edit. [Readiness](../rerun-ready/readiness.md) records macOS 26.5.1 build 25F80 on arm64.

The [prepared command list](../rerun-ready/stage-b-commands.md) supplied the launch order, fresh responder, Codex port update, and root/listener barrier. Each harness used its own disposable home and workspace, a fake provider key, a loopback model endpoint, and one per-workload Unix socket. The Codex configs selected the `bv01` permissions profile and trusted only their disposable workspaces. Both disabled the update check and plugins. The Claude settings allowed only the cell's Unix socket and disabled local binding. No SVID was issued or bound, and no operator control socket was used. The mutable Claude `.claude.json` files stayed in the disposable homes because the headless run added state to one of them. Startup JSON and settings snapshots use `.raw.txt` suffixes to preserve their exact bytes under the repository formatters.

## Attempt reconciliation

The first pass launched the listeners from short lived supervisor commands. Their socket files appeared, but the listener processes were gone at later checks. The live socket barrier was unverified for that pass. Its raw files and audit excerpt are retained under [attempt 1](attempt-1/). I moved its launch markers and logs to each home's `rerun-attempt-1/`. The capture file and homes stayed in place. For [attempt 2](attempt-2/), I repeated each cell in literal order with responder and listener jobs owned by one persistent supervisor shell. `lsof -nP -U` showed each listener holding its exact `gateway.sock` immediately before the `go` marker released its wrapper and again after the harness outcome. The listener handled zero native connector requests in both passes.

## Corrected cell results

| Cell | Launch root, responder, listener PIDs | Fake model requests: method, raw path, status | Harness and connector result |
| --- | --- | --- | --- |
| Codex headless | 50563, 47378, 51498 | Zero requests. `model.jsonl` was not created. | Exit 1 before a model request. `harness.err` records `sandbox-exec: sandbox_apply: Operation not permitted` while loading local `AGENTS.md` instructions. The listener did not log a connection. Unsupported in this sandbox. |
| Codex interactive | 59360, 57077, 61136 | Zero requests. `model.jsonl` was not created. | tmux pane died with status 1 at the same sandbox helper error, before a prompt or connector command. The pane also reported a restricted filesystem profile warning. The listener did not log a connection. Unsupported in this sandbox. |
| Claude headless | 68385, 66890, 69497 | `HEAD /api/hello` 403, followed by two `POST /v1/messages?beta=true` 200 requests. | Exit 0 with stdout `Done.` and empty stderr. The responder sent its fixed tool frame, while the live listener did not log a connection. The refused `/api/hello` startup request triggered the runbook's path-mismatch stop condition. Attribution remains untested. |
| Claude interactive | 75802, 74781, 76528 | `HEAD /api/hello` 403 only. | Stopped at the workspace trust prompt without answering it or sending the native-tool prompt. The dedicated tmux window was ended. The live listener did not log a connection. Unsupported with the prepared first-run settings. |

The raw responder logs contain only method, raw request path, and status. The 403 `/api/hello` requests and the `?beta=true` Messages paths are observed behavior. The runbook's proposed `HEAD /v1/messages` shape did not occur. The Claude headless harness made both Messages requests before the supervisor could stop the cell after the refused startup path. The cells ran sequentially. The fixed final frame accounts for `Done.` but does not prove that the shell tool ran. The empty listener logs and live-socket checks show that the listener handled zero connector requests. The Codex announcement request was not independently instrumented, and these bootstrap failures do not establish whether it was attempted.

## File-open capture

The operator's new capture remained running throughout both passes. It was read only. [The control excerpt](attempt-2/capture-control.json) records one `/bin/cat` open event for `/private/tmp/bv01-228-codex-headless/audit-positive-rerun` at `2026-09-29T01:32:35.819389763Z`. [The corrected excerpt](attempt-2/capture-excerpt.jsonl) retains the selected original event fields for the four recorded root process trees through `01:49:00Z`, and [the process list](attempt-2/observed-processes.json) records the PIDs, parent PIDs, executables, and start times used for attribution. This is a filtered extract, not the operator's full raw capture.

| Cell | Disposable configuration open events | Keychain open events | 1Password open events attributed to the cell |
| --- | --- | --- | ---: |
| Codex headless | `codex` PID 50563: 7 at `/private/tmp/bv01-228-codex-headless/codex/config.toml`. | None. | 0 |
| Codex interactive | `codex` PID 59360: 14 at `/private/tmp/bv01-228-codex-interactive/codex/config.toml`. | None. | 0 |
| Claude headless | Claude 2.1.284 PID 68385: 5 at `/private/tmp/bv01-228-claude-headless/settings.json` and 6 at `/private/tmp/bv01-228-claude-headless/claude/.claude.json`. | Claude PID 68385: 47 at `/Library/Keychains/System.keychain`, and its `security` child PID 69567: 43 at the same path. | 0 |
| Claude interactive | Claude 2.1.284 PID 75802: 4 at `/private/tmp/bv01-228-claude-interactive/settings.json` and 1 at `/private/tmp/bv01-228-claude-interactive/claude/.claude.json`. | Claude PID 75802: 47 at `/Library/Keychains/System.keychain`, and its `security` child PID 76598: 43 at the same path. | 0 |

The selected events from these process trees omit the operator's `.codex/config.toml`, `.claude` configuration, and 1Password paths. The system-wide capture also contains unrelated 1Password CLI events, which are not attributed to these roots. The `eslogger open` events establish path and process at request time while leaving actual byte reads and open completion unverified. Inherited descriptors, mappings, or capture gaps could hide other access.

## End state and bounds

The Codex headless and interactive processes exited 1. Claude headless exited 0. Claude interactive was stopped at its unanswered trust prompt. Each corrected-pass responder and listener was sent `SIGTERM` and its supervisor job reported exit 143. `lsof` found zero open files for the four corrected launch-root PIDs, responder PIDs, and listener PIDs. It found zero live owners for their loopback ports and Unix socket paths. The dedicated tmux server was killed and its stale socket file removed. The operator's capture and all four disposable homes remain for the operator's later stop and teardown decisions. The default tmux server and session 0 were never addressed.

The corrected pass establishes startup and file-open observations only. It does not qualify any of the four harness profiles for per-workload socket attribution, and it does not answer the two-workload, lifecycle, stale-record, or connection-lifetime cases in issue #228. No unauthenticated TCP fallback was used. The inherited-descriptor attribution gap remains open. The operator can stop the privileged capture after receiving this all-ended report.

## Repository checks

`mise run fmt` completed, and the original bytes of raw startup and settings files were restored afterward under `.raw.txt` names. `mise run check:vale` passed. The final `mise run check` exited 1 after 697 coverage tests passed and the synthetic Quarto notebook test failed because this sandbox denied a write to `/Users/tony/Library/Application Support/quarto/logs/jupyter-kernel.log`. The other reported checks, including prose, secrets, and the regular pytest suite, passed. The complete [check output](check.raw.gz) and [exit code](check.exit) are retained. [Readiness](../rerun-ready/readiness.md) records a passing targeted run of that notebook test with a disposable `HOME`.
