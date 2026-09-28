# Operator sbx before-state attempt, 2026-09-28

The operator's decision at `.holding/reorg/2026-09-27-bv-seed-operator-decisions.md` item 15 authorized only probes of the local-kit setting, clean and kit sandboxes, and a conditional host bundle on the installed sbx. This attempt stopped before the first mutation because the worker could not establish the initial setting or sandbox inventory. The CLI was `sbx` v0.45.1 at revision `9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb` on macOS 26.5.1 arm64. The checkout started at `6b5188bda7402b45a6d6792d2b049a8e62909988`. No interim operator control path, provisional exact-path binding, or workload wrapper was used.

## Exact command ledger

Commands ran in `exp/229-sbx-kit-trust-2`. Selected output below is verbatim, apart from omitting the absolute current directory. The sbx invocations requested reads. `sbx settings get` attempted daemon startup internally, but could not open its log.

| Order | Command | Exit | Output |
| --- | --- | --- | --- |
| 1 | `date` | 0 | `Mon Sep 28 12:06:11 EDT 2026` |
| 2 | `sbx version` | 0 | `sbx version: v0.45.1 9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb` |
| 3 | `sbx daemon status` | 0 | `Status: stopped` and `Socket: /Users/tony/Library/Application Support/com.docker.sandboxes/sandboxes/sandboxd/sandboxd.sock (not connected)` |
| 4 | `sbx ls --json` | 1 | `error: Not authenticated to Docker` and `try: sbx login` |
| 5 | `sbx settings get --json kit.allowLocalKits` | 1 | `Starting sandboxd daemon...` then `error: ensure daemon: open daemon stderr log: open /Users/tony/Library/Application Support/com.docker.sandboxes/sandboxes/sandboxd/daemon-stderr.log: operation not permitted` |
| 6 | `sbx daemon status` | 0 | `Status: stopped` with the same socket path marked `(not connected)` |
| 7 | `stat -c '%n|%F|%s bytes|mtime %y' '/Users/tony/Library/Application Support/com.docker.sandboxes/sandboxes/sandboxd' '/Users/tony/Library/Application Support/com.docker.sandboxes/sandboxes/sandboxd/daemon-stderr.log'` | 1 | Directory existed with mtime `2026-09-27 20:48:06.807093610 -0400`; log path did not exist |
| 8 | `sbx settings get --json proxy.daemon` | 1 | Same daemon-start log access denial as order 5 |
| 9 | `sbx daemon status` | 0 | `Status: stopped` with the same socket path marked `(not connected)` |
| 10 | `test -e /private/tmp/bv05-kit` | 1 | No output; the proposed kit path was absent |

The recorded metadata check did not read daemon files. `mise run vale:sync` exited 0. The installed CLI's `create`, `exec`, `run`, `secret set-custom`, `kit validate`, and `policy log` help was inspected without a daemon. None of those help reads proves runtime behavior. The command attempt `test -e /private/tmp/bv05-kit; printf ... "$?"` was rejected by the shell PreToolUse hook before execution because a trailing exit-status echo masks the first command's status. The standalone `test` above supplied the result.

## Before and after operator state

| Surface | Before | After | Scope of comparison |
| --- | --- | --- | --- |
| Installed CLI | v0.45.1, build revision above | No installation command ran | Binary version was read before the attempted probes |
| Daemon | Stopped, socket not connected | Stopped, socket not connected after both failed settings reads | Observable daemon status matches |
| Sandboxes | `sbx ls --json` failed for missing Docker authentication | No sandbox command ran | Existing names and count remain unknown |
| `kit.allowLocalKits` | Settings read failed at daemon log access | No setting command ran | Effective value and override source remain unknown |
| Proxy setting | `proxy.daemon` read failed at the same log access | No setting command ran | Effective proxy configuration remains unknown |
| Trust and credentials | No values read | No trust or credential command ran | Trust and credential content remained uninspected |
| Disposable artifacts | `/private/tmp/bv05-kit` absent | No kit, receiver, CA, or bundle was created | The worker had nothing to remove |

**Observed:** daemon status was stopped before and after the attempted reads. **Inference:** no approved mutation occurred because none was invoked. Full installation equivalence is unverified because the sandbox list, setting values, credential store, and trust inputs could not be read. The failed settings reads did not create the log file at the inspected path.

## Required-case result

| Case | Expected runtime evidence | Actual result | Classification |
| --- | --- | --- | --- |
| 1. Headless creation and binding | Disabled-setting rejection, enabled creation, required binding, and repeat setup count | Initial setting unreadable; no mutation or creation | Blocked |
| 2. CA and leaf matrix | Clean and kit sandbox TLS, SNI, injection, and negative controls | Sandbox inventory unavailable; no sandbox or receiver | Blocked |
| 3. Host route | Guest URL, DNS and dial, policy target, injection match, upstream name | Pinned documentation only; no guest | Blocked |
| 4. Trust and restart | Public-only kit, retained Docker proxy trust, renewal and restart | No kit or sandbox; host-bundle condition never reached | Blocked |
| 5. Optional client certificate | Same listener negotiates optional certificate and bearer request | No receiver or proxy request | Blocked |
| 6. Bounded non-consuming wait | Measured hold, timeout and reconnection traces, delivery evidence before and after | No sbx transport, wait endpoint, or delivery store exists in this fixture; duration and support status are unmeasured | Blocked and inconclusive |

The case 6 absence of delivery rows is not evidence that delivery records remain unchanged after a timeout or reconnection. No security property or integrated harness cell is accepted. The specific kit-only failure hop required before the process-scoped host-bundle probe was not reached.

## Undo ledger

| Approved probe | Mutation | Undo result |
| --- | --- | --- |
| `kit.allowLocalKits` false, then true | Not started | `sbx settings unset kit.allowLocalKits` not run or needed |
| `bv05-clean` and `bv05-kit` creation | Not started | `sbx rm bv05-clean bv05-kit` not run or needed |
| Conditional process-scoped bundle daemon | Condition not met; not started | `sbx daemon stop` and bundle removal not run or needed |

The next attempt needs a worker sandbox that can open the installed sbx daemon's state paths and an operator-approved way to use Docker authentication. It must first establish the initial `kit.allowLocalKits` source and sandbox-name inventory, then record an undo that restores that exact state. Changing Docker sign-in, host state permissions, a setting, or a credential is outside this decision's three approved probes.

## Repository checks

After a Vale wording correction, `mise run check` exited 0. Its exact output is in [check-continuation.txt.gz](check-continuation.txt.gz). `mise run check:mutation` exited 0, with exact output in [mutation-continuation.txt.gz](mutation-continuation.txt.gz). The Go mutation run classified 149 mutants and killed 97.32% of them. The Python core mutation score was 90.18%. Both archives passed `gzip -t`.
