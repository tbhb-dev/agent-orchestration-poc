# BV-05: sbx kit routing and server trust

## Decision

**Partial investigation, blocked sbx profile.** The third attempt ran on the operator's installed sbx after Docker sign-in. The approved `kit.allowLocalKits=false` probe showed that `sbx kit validate` rejects a local kit, and the setting was restored to its default source. Both approved `sbx create` attempts failed before sandbox creation because the global network policy was uninitialized. Initializing it changes the operator's global policy store and was outside this run's authorization. No guest, proxy, injection, or sbx wait behavior was observed. Issue #229 remains open; no security property, backend profile, or harness cell is qualified. The [run notes](evidence/installed-sbx-run/notes.md) give the case table and bounded operator proposals.

## Attempts and topology

The [first read-only attempt](evidence/read-only.md) and [second operator-state attempt](evidence/operator-state-attempt.md) preceded Docker sign-in. The second could not read effective settings or authenticate and did not run a stateful probe. The [third command ledger](evidence/installed-sbx-run/ledger.txt) records the approved setting change, kit validation, blocked creates, and host-only requests. It does not contain the original receiver launch, restart, certificate-verification, or receiver-cleanup commands. Their exact historical invocations and output were not retained. The [fresh host-only replay](evidence/installed-sbx-run/host-replay.txt) supplies an independently executed recipe for those steps, not missing history from the sbx attempt.

The intended sbx profile is local sbx v0.45.1 on macOS 26.5.1 arm64, with no real harness, a disposable private CA, a loopback HTTPS receiver representing agentd, a dummy bearer, and disposable clean and kit sandboxes. The intended guest URL is exactly `https://host.docker.internal:<agentd-port>`. The proposed route has guest-to-Docker-proxy and host-proxy-to-receiver TLS hops. Host-only certificate validation and curl cannot establish the proxy route, its upstream verification name, credential injection, or preserved guest proxy trust.

## Required case outcomes

| Case | Observed or simulated evidence | sbx result |
| --- | --- | --- |
| 1. Headless setup, setting, binding, reuse | `kit validate` rejected the local kit under `kit.allowLocalKits=false` and accepted it at the default; the fixture reused its CA on a second run | Blocked before creation; binding and sbx reuse untested |
| 2. Clean versus kit and leaf controls | Host-only OpenSSL checks covered valid, wrong-host, expired, and unrelated leaves; curl rejected an untrusted receiver | Blocked; no proxy path, SNI, or injection observation |
| 3. Host-service route | `sbx policy check network localhost:18443` returned the uninitialized-policy error | Blocked; guest DNS, dial, policy target, and upstream name untested |
| 4. Proxy trust, public kit, renewal, restart | The kit contains a public CA certificate and no private key; a renewed leaf used the same CA | Blocked; guest proxy trust and sandbox restart untested |
| 5. Optional client certificate and bearer | The host receiver accepted a bearer without a client certificate and, after correcting the client leaf, accepted a client certificate; the replay confirms optional-certificate TLS without bearer | Blocked for sbx; host simulation only |
| 6. Non-consuming wake wait | Host-only fixture held 5 seconds, observed a client timeout and reconnection, and left delivery evidence unchanged after one positive-control delivery | Blocked and inconclusive for sbx transport |

The [receiver logs](evidence/installed-sbx-run/receiver.jsonl), [PKI manifest](evidence/installed-sbx-run/pki-manifest.json), and [public kit](evidence/installed-sbx-run/kit/spec.yaml) record the host observations, while the original ledger lacks the OpenSSL verification output behind the case-2 summary. The replay records fresh results with a separate PKI. Its fingerprints and port differ from the original run.

## Reproduce the host-only fixture

From the repository root, run:

```sh
mise exec -- bash experiments/03-sbx-kit-trust/host-replay.sh
```

The script creates a disposable `/private/tmp/bv05-host-replay.XXXXXX` directory, uses `PYTHONSAFEPATH=1` and `mise exec -- python` to issue the CA and leaves and generate a public kit, then runs `mise exec -- openssl verify` with `-CAfile` and `-verify_hostname localhost`. It launches `fixture.py serve` on `127.0.0.1:18453` with explicit `--root`, `--leaf`, `--port`, `--log`, and `--deliveries` flags. After trusted and untrusted curl requests, it restarts the receiver with `--client-ca` and sends requests with and without a client certificate. It prints the receiver log and removes the scratch directory on exit. The script never calls sbx or changes a trust store. The [captured replay](evidence/installed-sbx-run/host-replay.txt) records its output and exit results for expected verification failures. Port 18453 must be free.

The installed-sbx run used port 18443 and private material under `/private/tmp/bv05-pki`. Only public certificates, certificate fingerprints, and redacted request markers were committed. The [fixture](fixture.py) supplies `pki`, `kit`, and `serve` subcommands. Its `serve` mode records receiver SNI, TLS version, client-certificate fingerprint, header names, and a truncated digest of any authorization value. The `/wait` endpoint holds without consuming delivery state, while `POST /deliver` provides a positive control. The host replay focuses on the missing receiver lifecycle and certificate-verification record. The original [ledger](evidence/installed-sbx-run/ledger.txt) and [receiver log](evidence/installed-sbx-run/receiver.jsonl) retain the bearer and wait simulations.

## Cleanup and limits

The settings source and full settings hash matched the start, no sandbox was created, and the global policy remained uninitialized. The daemon was stopped at the start, but `sbx ls --json` started it. An attempted `sbx daemon stop` was denied by the auto mode classifier, so it remained running at the last observation. Secret-name inventory and bindings-file metadata reads were also denied. No alternate path was tried, and the state of those unread files cannot be compared. The host replay cleans up its own receiver and scratch files. It does not change the installed-sbx state.

The [versions record](versions.md) gives the tested runtime and source pins. The next sbx run requires a concrete operator decision on global policy initialization and the dummy credential binding in the [run notes](evidence/installed-sbx-run/notes.md). A process-scoped host bundle remains conditional on identifying where upstream trust fails with the kit alone.
