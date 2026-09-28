# Host runtime lifecycle and storage

## Scope and topology

**Observed.** The [deterministic fixture](probe.py) launched Python stand-ins directly and in a tmux 3.7b server at a dedicated `/private/tmp/bv08-243-*/tmux.sock`. One disposable directory contained a shared workspace and mode 700 private A/B directories. The fixture didn't use a daemon, local kit, trust configuration, harness settings, provider credential, VM, or sandbox name. The worker ran inside an existing tmux client, but the fixture addressed only its dedicated socket and cleared inherited `TMUX` variables for its attach clients. [Raw results](evidence/host-probe.json) record each observed exit and marker. [Versions](versions.md) pin the host, tools, source revisions, and imported design snapshot.

**Proposed.** The [host harness runbook](host-harness-runbook.md) and [fixture package](fixture/) prepare the four later live cells approved conditionally by BV-20. They record native conversation ID, A-1 and A-2 process incarnation, private-state fingerprints, and a fresh controller observation separately from tmux attachment. The launcher computes its exact argv and environment in a pure function. The read-only observer compares PID and process start time. Table and property tests exercise validation, process identity, state retention, and launch selection. The resume responder adapter loads the merged experiment 02 responder with separate frames that ask A to test B's harmless private marker. Loopback integration tests check the frame bytes and two-request limit. Experiment 02 remains unchanged. The live harness commands did not run in this delivery.

**Documented.** The [BV-08 source](../../research/imported/design-wiki-8384ca7/backend-validation-spikes.md#bv-08-runtime-and-launcher-lifecycle-with-storage) supplies the required cases. The [mental model](../../research/imported/design-wiki-8384ca7/mental-model.md#task-lifecycle-and-backend-contracts) separates readiness, outcome, retained artifacts, and native conversation from process attachment. The [authentication design](../../research/imported/design-wiki-8384ca7/spiffe-mtls-authentication.md#launch-rotation-suspension-and-resume) places authority fencing in a later integration. Host mode has no VM or sandbox name, so those mapping fields are not applicable here.

## Reproduction

**Verified.** From the repository root, `mise run vale:sync` exited 0. `PYTHONSAFEPATH=1 mise exec -- python3 experiments/06-host-runtime-lifecycle/probe.py run > experiments/06-host-runtime-lifecycle/evidence/host-probe.json` exited 0 on 2026-09-28. The command creates a unique `/private/tmp/bv08-243-*` directory. It launches the stand-in Python process and a dedicated tmux server, then removes the directory on normal completion. It addresses only its dedicated tmux socket, and the JSON excludes environment values. The fixture has neither product core functions nor a network listener or provider calls. The executable is a fixed imperative probe, and all contract decisions below are documented outside its I/O path.

## Case results

| Case | Expected | Actual | Evidence | Classification |
| --- | --- | --- | --- | --- |
| Prepare and headless launch | Create shared/private paths, observe readiness, output, and exit | Direct A emitted ready and complete, exited 0, and wrote an outcome marker | `host-probe.json` `prepare`, `direct-headless` | observed, allowed |
| Cancel twice | Stop a live worker and make a second request harmless | Direct B exited -15 without a success marker. The fixture didn't signal the exited PID again | `host-probe.json` `direct-cancel-twice` | observed, allowed for this fixture |
| Interactive detach and reconnect | Dropping attach clients leaves the pane and worker running | Two dedicated-socket attach clients exited 1 after termination, and `has-session` returned 0 after each disconnect. Pane output still showed ready | `host-probe.json` `tmux-interactive-reconnect` | observed, allowed for this fixture |
| Stop tmux server | End this disposable terminal owner | `kill-server` exited 0. The socket pathname existed until the enclosing fixture directory was removed. No success marker was present | `host-probe.json` `tmux-server-stop`, `cleanup` | observed, allowed for this fixture |
| Collision and interrupted prepare | Reject a duplicate name and clean only the partially created path | Existing A name was rejected. Two concurrent `mkdir` calls returned 0 and 1. The partial provisioner created its owned marker, received SIGTERM and exited -15, and the controller removed that owned path. Second cleanup found it absent; an unrelated workspace file remained | `host-probe.json` `collision-and-interrupted-create` | observed, allowed for this fixture; controller crash rollback untested |
| Workspace and private state | Retain shared files and locate A/B state | A and B workspace files remained through their runs. After B wrote its marker, a new A worker read it and wrote the value to A's private path under the same host UID | `host-probe.json` `storage` | observed, no host same-UID privacy boundary |
| Controller restart | A new observer can inspect a live pane | Each `tmux has-session` call was a fresh client process after an attach client exited. No agentd controller restart was tested | `host-probe.json` `tmux-interactive-reconnect` | observed for tmux clients, untested for agentd |
| Native harness resume | Resume a native conversation in a new process | The fixture and exact commands are prepared, but no harness invocation ran | [Runbook](host-harness-runbook.md) | untested pending artifact review and the later host run |

## Capability and ownership table

| Backend and profile | Prepare and launch | Observe and output | Cancel and cleanup | Attach | Native resume | Storage owner and recovery limit |
| --- | --- | --- | --- | --- | --- | --- |
| Host direct stand-in, headless | observed | observed stdout and exit | observed signal and directory cleanup | not applicable | unsupported by stand-in | Fixture owns shared and A/B paths, and an exited process cannot be reattached |
| Host tmux stand-in, interactive | observed | observed pane output and live session | observed server stop and directory cleanup | observed two client reconnects | unsupported by tmux | Fixture owns tmux socket and pane, with output limited to retained pane history |
| Claude Code, interactive | untested | untested | untested | untested | untested | Harness state ownership and recovery need an authorized isolated-home run |
| Claude Code, headless | untested | untested | untested | not applicable | untested | Harness state ownership and recovery need an authorized isolated-home run |
| Codex, interactive | untested | untested | untested | untested | untested | Harness state ownership and recovery need an authorized isolated-home run |
| Codex, headless | untested | untested | untested | not applicable | untested | Harness state ownership and recovery need an authorized isolated-home run |

Claude Code and Codex harness rows remain unqualified. The probe didn't use a real provider credential or run a harness process. BV-20 conditionally approved a later fake-credential run after review of its exact fixtures and commands. The same-UID private-path read establishes only this fixture's host behavior.

## Proposed minimal host contract

**Proposed.** `prepare(workload_id, workspace, private_root)` reserves a unique incarnation and creates only owned paths. A collision fails without adopting an existing path. Rollback removes only paths created by that attempt. The host mapping is workload ID to incarnation to wrapper PID and optional tmux session/pane. `sandbox_name` and `vm_id` are not applicable in host mode. The harness conversation ID is a separate optional record scoped to its private state.

**Proposed.** `launch(incarnation, profile)` returns a process handle and optional terminal handle. `observe(handle)` reports readiness, live status, stdout or pane bytes, and an exit outcome separately. An absent outcome after a lost observer remains unknown until reconciliation. `cancel(handle)` signals only the recorded live process or dedicated tmux session and is idempotent at the API level after exit. `cleanup(incarnation)` removes only owned runtime artifacts. Shared workspace data remains under workspace ownership.

**Proposed.** `reattach(terminal_handle)` reconnects to a live terminal. `resume_native(conversation_id, new_incarnation)` invokes the harness's own supported resume operation with retained authorized state. It creates a new process and must not infer a native conversation ID from a tmux pane or exec call. Authorization, fencing, and renewal are deferred to BV-07-host and BV-10-host. A wrapper has one incarnation until those reports qualify managed resume.

**Inference.** A durable registry needs workload ID, incarnation, launch/terminal handles, harness conversation ID when known, owned path inventory, timestamps, and terminal outcome. Process PID alone cannot prove identity after a restart. A new observer must reconcile live processes and retained outcome files before reporting a final result. Registry and authority behavior remain untested.

## Retained artifacts and limits

**Observed.** Before cleanup, the fixture contained `workspace/unrelated.txt`, A/B shared output, A/B private markers, A's copy of B's marker, ready markers, a direct A outcome marker, and a dedicated tmux socket. Direct cancellation didn't produce a B outcome marker. The interrupted provisioner's partial marker existed before SIGTERM; the controller removed its owned path after the process exited, while the workspace sentinel remained. After cleanup, the fixture root was absent. Cleanup removed artifacts only within the unique fixture directory.

**Untested.** Harness conversation IDs, native resume, private harness-state retention across a harness stop/start, harness-mediated A-to-B state access, authenticated authority lifetime, controller crash rollback and recovery, and real wrapper cancellation remain open for Claude Code and Codex.

The new resume frames ask a live A harness to test B's private marker. The shared-file command remains a host probe because the model frames do not ask a harness to write the workspace file. The live four-profile run remains necessary to qualify the harness cells.

**Blocked.** `pgrep -fl 'bv08-243|tmux -S'` reported that the sysmond service was unavailable, and `ps -eo pid,etime,args` returned `operation not permitted`. The fixture used recorded child exit codes, marker files, and dedicated-socket tmux status instead. It cannot independently prove the tmux pane PID exited after server shutdown.

## Proposed decision

**Proposed.** Retain direct host launch and dedicated-socket tmux attachment as separate capabilities. Use a durable owner map and explicit outcome states before a production launcher can claim recovery. This is a partial delivery. Issue #243 remains open until the four harness cells and native conversation/storage cases have evidence or reproducible unsupported results.

## Validation

**Verified.** `mise run fmt`, `mise run check`, `mise run check:mutation`, and `mise run build` exited 0 on this worktree. The [check log](evidence/check.log) records the repository gates, and the [mutation summary](evidence/mutation-summary.txt) records both scores. Mutation testing killed 97.32% of Go core mutants and 90.14% of Python core mutants. `mise exec -- gitleaks dir --redact --no-banner experiments/06-host-runtime-lifecycle` exited 0 with no leaks found. The deterministic probe exited 0 and its JSON remained valid after formatting.

**Verified.** This fixture delivery's [validation record](evidence/fixture-validation.md) links the new aggregate log and 52 focused tests, including loopback checks of the resume frames. `mise run check` and `mise run check:mutation` exited 0. Python core mutation score was 90.19% at the newer checkout. These results validate the fixtures and repository gates, while the four live harness profiles remain untested.
