# Docker Sandboxes daemon isolation

## Decision

**Partial delivery, blocked runtime verification.** The installed `sbx` v0.45.1 help has no local daemon state or configuration selector. Pinned Docker documentation names a macOS state root and separate credential binding and audit paths, but does not establish the exact settings file, daemon socket, sandbox disk paths, or a supported alternate-root selector. A separate macOS user is the smallest plausible disposable target, with isolation and cleanup **untested** because creating the account and running the daemon require an operator-approved host change. Qualification of the local sbx profile and the remaining [BV-05 probes](https://github.com/tbhb-dev/agent-orchestration-poc/issues/229) depends on that proof.

## Read-only result

The [command outputs](evidence/exit-codes.txt), [path inventory](evidence/operator-path-inventory.txt), and [pinned documentation excerpts](evidence/source-inspection.md) were collected on macOS 26.5.1 arm64. `sbx version`, `sbx settings --help`, `sbx daemon start --help`, `sbx create --help`, `sw_vers`, and `uname -m` all exited 0. `sbx settings --help` says even a settings read starts the local daemon if needed. No `sbx settings get`, `sbx daemon status`, `sbx ls`, daemon start, sandbox creation, or trust operation was run. The operator's state-root directory existed before this experiment's path inventory. Its content was not read.

**Documented:** at [Docker documentation commit `75d1ee3`](https://github.com/dvdksn/docs/tree/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes), macOS reset guidance names `~/Library/Application Support/com.docker.sandboxes/` as the state, configuration, and cached-image removal root. Credential bindings for third-party kits live separately at `~/.config/sbx/credentials.yaml`. macOS stored secrets use the system Keychain. Conditional audit records use `~/Library/Logs/com.docker.sandboxes/sandboxes/auditkit/`. `sbx rm` removes a persistent sandbox's VM and contents. The individual VM paths and local daemon socket path remain unspecified.

**Help-text:** the installed CLI advertises `environment variables > user overrides > defaults` for settings. It does not identify the effective `kit.allowLocalKits` environment variable, the override file, or a local state/configuration selector. `--cloud` dispatches to a cloud API and is a different backend. `sbx rm` removes a named local sandbox and its scoped secrets, while `sbx reset` removes all state, settings, secrets, and sign-in. Neither command is safe against the operator account here.

**Untested:** the binary reports build revision `9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb`. The public `docker/sbx-releases` repository supplies releases without reviewable source, and `docker/sbx` returned HTTP 404. The revision identifies the installed binary. Claims about `HOME`, XDG variables, `SSL_CERT_FILE`, socket placement, and Keychain access remain inferences.

## Candidate comparison

| Candidate | Daemon state and socket | Settings and precedence | Sandbox ownership and storage | Trust inputs | Result |
| --- | --- | --- | --- | --- | --- |
| CLI selector or environment override under the operator UID | No local selector advertised, macOS alternate-root behavior unspecified | Environment values take precedence over overrides, file path unspecified | Would still use the operator UID unless every path is redirected | Same macOS Keychain and system trust | Unsupported as an isolation recipe |
| `HOME` or XDG redirection under the operator UID | Pinned docs specify XDG roots only on Linux, macOS path resolution unverified | Binding path might move, overrides and daemon path unverified | Ownership remains UID 501 and existing host resources may remain shared | Keychain and OS trust stay shared | Unsupported as an isolation recipe |
| Separate macOS user `sbx-bv05-237` | Expected private home and UID, exact socket and temporary paths need observation | Expected separate override state and `~/.config/sbx/credentials.yaml`, precedence needs a live check | Expected user-owned state root and mountless VM, exact VM paths need observation | Separate login Keychain is plausible, OS trust stays shared, process trust inheritance untested | Proposed, operator authorization required |
| Disposable macOS VM | Guest state and sockets would be outside the operator host user | Guest settings would be separate | Guest sandbox storage would be contained in the VM | Guest trust store would be separate | Higher-cost fallback, nested virtualization and sbx support untested |

The separate-user candidate cannot be accepted from filesystem conventions alone. Before its first state-changing command, the operator must confirm the account's home path and login context. A successful run must prove that every sbx process and artifact is owned by the new UID and that none resolves into the operator's paths or Keychain. The operator's system trust and proxy configuration must remain unchanged.

## Conditional isolation and cleanup recipe

The [fixture proposal](evidence/operator-fixture.md) gives the exact user-qualified commands and comparison points. It is **unexecuted**. First capture metadata and hashes of the operator's known paths without reading secrets, plus the operator daemon's process and socket inventory if authorized. Create the disposable user interactively. In that user's login context, record `id`, `HOME`, its path inventory, daemon status, effective setting source, sandbox list, and trust inputs before the fixture. Stop if any path resolves to the operator account.

Start the disposable daemon, set `kit.allowLocalKits` to `false`, create and remove the mountless `bv05-clean` sandbox, then unset the override and stop the daemon. Test a public-only process-scoped trust file only if the installed daemon actually honors the selected input. Record the daemon PID, UID, executable, socket, state files, VM files, effective setting source, and trust source while the fixture runs. Capture before, during, and after inventories for both accounts. Remove the disposable account and home only after proving no daemon or VM remains. Record any Keychain item, audit log, temporary socket, launch agent, image, or other residue for operator cleanup.

The recipe is reusable for #229 only after an operator-authorized run observes isolation and cleanup across daemon, setting, sandbox, and trust surfaces. Its local-kit setting, clean/kit sandbox, and conditional host-bundle probes remain outside this issue. The process-scoped trust input is a candidate rather than a verified sbx feature. Do not use `sbx reset` or any `sbx settings` read against the operator account.

## Acceptance case status

The [case table](evidence/cases.md) records expected and actual results with evidence paths. The read-only source and CLI checks satisfy the investigation's first stage. No daemon, settings, sandbox, or trust changes were made, so the before/during/after and cleanup acceptance cases remain blocked. There is no disposable residue from this read-only work.

Local `mise run check` and `mise run check:mutation` passed after Vale corrections. The [check output](evidence/check.txt.gz), [mutation output](evidence/mutation.txt.gz), [mutation summary](evidence/mutation-summary.txt), and [exit ledger](evidence/exit-codes.txt) retain the results.
