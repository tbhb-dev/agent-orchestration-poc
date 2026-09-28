# Host harness confinement baseline

## Scope and result

**Observed:** a disposable same-UID shell baseline connected to A's peer socket and B's peer, enrollment, management, queue, `cc-socks`, and oversight socket stubs. It read and used B's canary bytes and replaced B's wrapper configuration. The [raw trace](evidence/baseline.jsonl) records these operations. The stubs identify each contacted endpoint. They handle no real protocol or authorization.

**Inference:** owner-only files and sockets under a shared UID cannot by themselves separate A from B. The result describes only the fixture baseline. Because the current worker's effective Codex sandbox policy was not captured, this report doesn't claim arbitrary same-UID isolation.

**Unresolved blocker:** issue #242 requires four managed harness cells and M-001. Running a harness with the approved fake-credential pattern is not authorized for this issue. No real provider credential, operator socket, agentd, local kit, trust store, or live peer service was used. [The operator proposal](operator-proposal.md) identifies the gated next run.

The imported [BV-02 definition](../../research/imported/design-wiki-8384ca7/backend-validation-spikes.md#bv-02-managed-harness-confinement-and-credential-custody), [host trust boundary](../../research/imported/design-wiki-8384ca7/spiffe-mtls-authentication.md#host-mode-trust-boundary), and [supervisor validation matrix](../../research/imported/design-wiki-8384ca7/supervisor-protection.md#validation-plan-and-caveat-format) set the question. [BV-01's local result](../02-host-socket-attribution/README.md#attribution-finding) found a descriptor attribution gap in its fixture, so a reachable socket does not establish authenticated workload identity.

## Reproduce the local baseline

Run from the repository root after `mise run vale:sync`. The two `serve` children are independent disposable wrapper processes. Each binds six Unix sockets below its own `/private/tmp/bv02-242-*` directory. The parent connects from the current shell path and removes the children and directory on exit. A and B are one-incarnation processes with no resume or SVID binding. No operator control socket is used, so no peer-UID check or operator authentication is claimed.

```sh
PYTHONSAFEPATH=1 PYTHONPATH=experiments/05-host-harness-confinement mise exec -- uv run python experiments/05-host-harness-confinement/fixture.py baseline > experiments/05-host-harness-confinement/evidence/baseline.jsonl
PYTHONPATH=experiments/05-host-harness-confinement mise exec -- uv run pytest -q experiments/05-host-harness-confinement/test_fixture_core.py
```

**Observed:** the baseline command exited 0. The local table and property tests passed, and the fixture's exact-path cleanup check returned true. A broader `/private/tmp` search was denied while traversing an unrelated daemon directory and was not retried. `evidence/commands.txt` records the exact invocations and exit codes. `fixture_core.py` transforms values without I/O. `fixture.py` owns process, socket, and file operations. Python imports from the hyphenated experiment directory need an explicit `PYTHONPATH` for the standalone test command.

**Verified:** `mise run check` exited 0 with all repository gates green. Python core line and branch coverage were 97.64% and 94.08%, and Go core statement and branch coverage were 96.43% and 94.74%. `mise run check:mutation` exited 0 with a Go mutant kill rate of 97.32% and a Python score of 90.21%. Those repository gates score product core code. The experiment's pure functions have standalone table and property tests. The complete command outputs are compressed in `evidence/check.txt.gz` and `evidence/mutation.txt.gz`.

## Case matrix

| Required case | Expected for a qualified profile | Actual in this run | Evidence and classification |
| --- | --- | --- | --- |
| 1. Peer and workspace positive, B socket, enrollment, renewal, management negative | Own peer and workspace allowed, all foreign and management paths blocked | Disposable own and B socket stubs were reachable. No workspace edit, renewal, real API, or harness path was tested | [Trace](evidence/baseline.jsonl), observed allowed baseline, integrated cells inconclusive |
| 2. Canary, key use, replacement, writable parents, symlinks, project settings, launch inputs, shell and native tools | Protected reads, use, and edits blocked by every path | The shell baseline read and used fake canary bytes and replaced a configuration file. Native tools and the other variants were not run | [Trace](evidence/baseline.jsonl), observed allowed baseline, integrated cells inconclusive |
| 3. Process observation, signal, debugger | Separate secrecy, integrity, and availability outcomes | No process-control attempt was run against a managed harness wrapper | Untested |
| 4. Helper, MCP, plugin, interactive/headless, hostile project config, sandbox startup failure | Every loaded path preserves the same restrictions and startup fails closed | No real harness was launched. The queue and `cc-socks` names are Unix-socket stubs with no protocol handling | [Trace](evidence/baseline.jsonl), observed reachability baseline, M-001 untested |
| 5. Policy relaxation and unsandboxed path | Unprompted escape blocked | No relaxation or escalation was attempted | Untested |

M-001 remains **untested** for `thread/queue/add` and a real `cc-socks` write from shell, MCP child, hook, and project-config-added server. Hook settings edits, helper replacement, operator key/socket access, and oversight-route access remain untested. The disposable names in the trace prove only socket reachability. Another workload's queue and Claude messaging socket require separate protocol tests. Operator authority also requires its own test.

## Profile protection and caveats

| macOS host profile | Secrecy | Integrity | Availability | Minimal supported settings |
| --- | --- | --- | --- | --- |
| Codex 0.157.1 interactive | Unknown | Unknown | Unknown | None qualified |
| Codex 0.157.1 headless | Unknown | Unknown | Unknown | None qualified |
| Claude Code 2.1.283 interactive | Unknown | Unknown | Unknown | None qualified |
| Claude Code 2.1.283 headless | Unknown | Unknown | Unknown | None qualified |

**Schema:** the local Codex source at the [recorded revision](versions.md) exposes `permissions.<name>.network.unix_sockets`. It is a candidate key for a future profile. The alternate `features.network_proxy.unix_sockets` key appears in a different schema branch and has not been selected for the installed CLI. **Documented:** the Claude settings offer `sandbox.enabled`, `failIfUnavailable`, `allowUnsandboxedCommands`, `allowUnixSockets`, and loaded permission scopes. Their effective values were not measured here. The fake-credential proposal for #228 provides a pattern. It doesn't authorize a run for #242.

**Proposed startup capability check:** require a trusted configuration source that fixes the sandbox and loaded hook/helper/plugin policy. Resolve effective settings for the selected harness and mode, then run an isolated canary suite through shell, native file, configured MCP, hooks, and project-added servers. Require own-peer and workspace positives and every protection negative, including M-001. Record every prompt as `prompted`, never `blocked`. Mark any unavailable tool path `unsupported` or `incomplete`. Refuse the qualified profile unless all required observations match. An operator may explicitly select a weaker profile that reports which secrecy, integrity, and availability guarantees are absent.

`fixture_core.profile_status` encodes the conservative allow/deny subset for that proposal. Its `incomplete` and `unsupported` outcomes must be treated as nonqualified. Its `qualified` return is a value-level check only and cannot replace the additional effective-settings and topology checks described above. Product startup integration remains outside this issue's allowed paths.

## Decision

**Observed:** the disposable same-UID baseline has no confinement. **Untested:** every integrated harness profile on macOS. The investigation is a partial delivery. The issue remains open for the gated four-profile run and M-001. A prompt, a schema key, or a fixture-only result supplies no denial or supported configuration claim.
