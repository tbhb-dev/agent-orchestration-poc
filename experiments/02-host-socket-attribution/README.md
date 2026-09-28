# Host socket attribution fixture

## Question and boundary

This BV-01 fixture tests whether a host gateway can bind each Unix-socket request to a wrapper-launched workload by reading macOS kernel peer identity and live process ancestry. The imported [BV-01 definition](../../research/imported/design-wiki-8384ca7/backend-validation-spikes.md#bv-01-host-socket-access-and-caller-attribution) and [local caller authentication design](../../research/imported/design-wiki-8384ca7/spiffe-mtls-authentication.md#local-caller-authentication) are proposals, while this report records a bounded result on the versions in [versions.md](versions.md).

The fixture uses two one-incarnation Python launch roots, A and B, separate short Unix socket paths under `/tmp`, and a third disposable server process for each socket. No SVID binding, issuance, credential, operator control socket, or interim peer-UID control path is exercised. There is no resume, relay, network listener, harness session, or agentd process. The exact full-path SVID registration rule remains a provisional fixture for BV-03 and BV-07. BV-01 does not test that binding.

`attribution_core.py` holds value-only membership and peer-change decisions. `probe.py`, `run_fixture.py`, and `edge_cases.py` read processes and sockets at the shell edge. The core tests pass plain process and peer values without mocks.

## Commands and cleanup

Run from the repository root with the mise-pinned environment. Each command below exited 0 in this run, and the raw output is retained in `evidence/`.

```sh
PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/run_fixture.py > experiments/02-host-socket-attribution/evidence/two-workload.jsonl
PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/edge_cases.py > experiments/02-host-socket-attribution/evidence/edge-cases.jsonl
for run in {1..10}; do PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/run_fixture.py > experiments/02-host-socket-attribution/evidence/churn-${run}.jsonl || exit 1; done
mise exec -- uv run pytest experiments/02-host-socket-attribution/test_probe.py
tmux -S /private/tmp/bv01-228-tmux.sock -f /dev/null new-session -d -s bv01 'cd /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/exp-228-host-gateway-attribution && PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/run_fixture.py > experiments/02-host-socket-attribution/evidence/tmux.jsonl'
```

`run_fixture.py` stops its child processes and removes its temporary directory. `edge_cases.py` uses context managers and a temporary directory. Both finish without a socket path or daemon left behind. The tmux session exited after the fixture, and the remaining dedicated server socket was removed. No pre-existing process, configuration, trust store, or daemon was changed. [Churn results](evidence/churn-summary.json) summarize 10 runs. The script uses only Unix sockets under `/tmp`, with no TCP fallback. The tmux cleanup commands and their exit status are recorded in [commands.txt](evidence/commands.txt).

## Case results

| Required case | Expected and actual | Evidence | Classification |
| --- | --- | --- | --- |
| 1. A descendants and B rejection | A direct and nested children were allowed at A, B's forged `A pid=1` claim was rejected, and A's forged `B pid=1` claim was still judged by ancestry. B was allowed at B. Under one disposable tmux session, A and B roots shared PID 65222 as their parent. A requests were allowed and B's forged A claim was rejected. | [Two-workload trace](evidence/two-workload.jsonl), [shared-tmux trace](evidence/tmux.jsonl) | Observed allowed and blocked in fixture, including shared tmux |
| 2. Connecting process and relay | `LOCAL_PEERTOKEN` identified the direct child PID in each fixture request. The nested path identified the final client, with the intermediate relay visible as its parent. No Codex or Claude execution path was started, so their actual connector and any authenticated relay binding are unknown. | [Two-workload trace](evidence/two-workload.jsonl) | Observed for fixture, integrated profiles inconclusive |
| 3. Process lifecycle | A fresh interpreter process and nested child were allowed. A new session detached child remained allowed while its parent lived. A child reparented to PID 1 after the launch root exited was rejected. An in-place exec across the same PID and harness helpers were not measured. | [Two-workload trace](evidence/two-workload.jsonl) | Observed allowed and blocked, exec and helpers inconclusive |
| 4. Stale records and churn | Repeated two-workload runs matched the expected decisions in all 10 attempts. Value-only table and Hypothesis tests reject a replaced root start time, a process born after acceptance, a missing link, and a parent cycle. No OS PID reuse event was observed. The token PID version lacks a validated comparison with the later `proc_pidinfo` lookup. | [Churn summary](evidence/churn-summary.json), [tests](test_probe.py) | Observed churn, simulated reuse, PID-reuse property inconclusive |
| 5. Descriptors, replacement, lifetime | An inherited connected descriptor wrote `held` after its original connector exited. A later `LOCAL_PEERTOKEN` read identified the successor PID and version. After a socket path was renamed and replaced, a client connected to the new listener. The descriptor was inherited by a child. Transfer to the separate B root remains untested. | [Edge cases](evidence/edge-cases.jsonl) | Observed inherited descriptor and replacement, foreign transfer inconclusive |

## Attribution finding

**Observed:** on build 25F80, the peer audit token changed from the original connector's PID and PID version to the inherited descriptor writer's PID and PID version while the same stream remained open. The original connector had exited before the successor wrote. The first version of the fixture read the token before `recv` and would have attributed those bytes to the wrong process. The fixture now compares token identities before and after each read and rejects a change.

**Documented source mechanism:** at XNU revision `f6217f8`, `LOCAL_PEERTOKEN` reads the peer socket's `last_pid` and looks up that process. It obtains the task audit token from that lookup. `so_update_last_owner_locked` updates socket ownership when a different process uses the socket. The installed SDK labels `LOCAL_PEERTOKEN` as option 6 and defines `audit_token_to_pid` and `audit_token_to_pidversion` as the supported token accessors. This source read explains the observed transition. The exact installed kernel source revision is unknown.

**Inference:** sampling `LOCAL_PEERTOKEN` before and after a request is insufficient to prove which process supplied every byte. A descriptor can change hands between reads, and the option describes the socket's last owner rather than an immutable connection creator or a per-byte author. A live ancestry walk also loses detached children after parent exit and does not compare the token PID version with the process table snapshot. The exact race and PID-reuse bounds need a stronger kernel binding or a separately authenticated per-request protocol.

## Bounded decision and handoffs

The direct socket plus live ancestry algorithm is **unsupported for security/property acceptance** on this evidence. The local fixture investigation found an attribution gap. None of the four macOS Codex and Claude host cells is qualified. This is a completed negative finding for the descriptor mechanism and a partial delivery for the issue's full required matrix, because integrated harnesses, in-place exec, helper processes, and foreign descriptor transfer remain untested. No unauthenticated TCP fallback is proposed.

BV-02 should treat the two harness socket keys as configuration candidates only and require actual native-tool connector traces before selecting either profile. BV-07 should fence new protected work when the launch root exits. It should reject missing or changed peer evidence and renew authorization on established streams. A token comparison around a read supplies diagnostic evidence with a known transfer race. The socket path needs a protected directory, and replacement behavior needs qualification with the eventual wrapper. These proposed rules await a destination design decision.
