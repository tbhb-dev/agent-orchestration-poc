# Sandbox run notes, 2026-09-28

These are raw executor notes for Codex. They record the fourth BV-05 attempt against the operator's installed sbx, the first one that created sandboxes. The executor was Claude Code with `claude-opus-5-5`, dispatched by the coordinator as the BV-05 executor under operator decision BV-23. The checkout was `exp/229-sbx-kit-trust-4` from `main` at `14e63e4`. Every time below is EDT on 2026-09-28 and comes from `date` or the ledger's own timestamps. Line numbers refer to [`ledger.txt`](ledger.txt).

## Environment

| Item | Value | Label |
| --- | --- | --- |
| Host | macOS 26.5.1 (25F80), arm64 | observed, ledger line 2 |
| sbx | v0.45.1, `9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb` | observed, line 10 |
| Template image | `docker/sandbox-templates:shell-docker`, pulled by the first create | observed, line 175 |
| Kit | `schemaVersion: "2"`, `kind: mixin`, byte-identical to [the committed spec](../installed-sbx-run/kit/spec.yaml) | observed, `diff` exit 0 |
| Receiver | [`fixture.py`](../../fixture.py) `serve`, bound to `127.0.0.1:18443`, restarted per leaf by [`serve.sh`](serve.sh) | observed |
| Ledger helper | [`rec.sh`](rec.sh) wraps each command with a timestamp, output, and exit code | observed |

Commands piped through `tail` or `grep` show the pipeline's exit code. For guest curl results, read the explicit `curl_exit=` line or curl's own error text instead.

## Operator sbx state

The brief expected an uninitialized policy and a stopped daemon. The read-only record at 17:13 to 17:14 found otherwise, and the executor held before any change and asked the coordinator. The coordinator answered that no other agent used sbx, that the operator most likely ran the init before approving, and that the observed state is the starting state. It told the executor not to run `sbx policy init`, `sbx policy reset`, or `sbx daemon stop`.

| Surface | Start (17:13 to 17:14) | End (17:29) | Label |
| --- | --- | --- | --- |
| Daemon | running, `sbx daemon start` pid 61775 started 17:09:55 | running, same pid and start time | observed, lines 15, 61, 1324, 1373 |
| Sandboxes | `{"sandboxes": []}` | `{"sandboxes": []}` | observed, lines 29, 1331 |
| Global policy | `default-deny-all`, which denies tcp and udp to `**`, and the `local-policy` filesystem allows | same rows | observed, lines 36, 68, 1338, 1345 |
| Settings | SHA-256 of `sbx settings list --json` `0477633d...af0f4` | same | observed, lines 43, 1355 |
| `kit.allowLocalKits` | `value: true`, `source: default` | same | observed, lines 48, 1360 |
| Template image cache | not checked | holds `docker/sandbox-templates:shell-docker` | inference from the pull at line 175, no removal ran |
| Stored secrets, bindings file, trust stores | not read | not read | not recorded |

While `bv05-kit` existed, `sbx policy ls` listed its kit policy and no `default-deny-all` row (line 1161), yet `sbx policy check network` still reported an implicit default deny for the global context (line 1259). The row was listed again once the sandboxes were gone (line 1338). The daemon was the same process throughout. Every policy command the executor ran was a read (`ls`, `check`, `log`).

## Changes and undo ledger

| Change | Command and exit | Undo | Result |
| --- | --- | --- | --- |
| `kit.allowLocalKits` false | `sbx settings set kit.allowLocalKits false` exit 0, line 134 | `sbx settings unset kit.allowLocalKits` exit 0, line 152 | `source: default` and the settings hash match the start, lines 157 and 170 |
| `bv05-clean` | `sbx create --name bv05-clean shell < /dev/null` exit 0, line 175 | `sbx rm --force bv05-clean bv05-kit` exit 0, line 1304 | Removed, `sbx ls --json` empty at line 1312 |
| `bv05-kit` | `sbx create --name bv05-kit shell --kit /private/tmp/bv05-kit < /dev/null` exit 0, line 234 | same `sbx rm` | Removed |
| Receiver | `fixture.py serve` on loopback, line 113 and `serve.sh` calls | `pkill -f 'fixture.py serve'`, line 1270 | No listener on 18443 |
| Global policy | not changed, already deny-all | none | Unchanged |
| Process-scoped host bundle | not run, no kit-only failure hop found | none | No bundle created |

`sbx rm bv05-clean bv05-kit < /dev/null` exited 1 with `stdin is not a terminal; use --force to skip confirmation` (line 1275). The executor reran it with `--force`, which only skips the prompt. No command was denied by permissions or the auto mode classifier in this run.

## Topology

The guest has `HTTPS_PROXY=http://gateway.docker.internal:3128` and `NO_PROXY=localhost,127.0.0.1,::1,gateway.docker.internal` (lines 300 and 334). `getent hosts host.docker.internal` returns `fe80::1` in both guests. The proxy logs every `host.docker.internal:18443` request under the resource `localhost:18443` (line 501). The receiver bound to host loopback only and still received the kit guest's requests, so the proxy's upstream dial reached `127.0.0.1:18443` on the host (inference from the bind address and receiver log).

The kit sandbox's allowed requests show `proxy_type: forward-bypass` for proxied requests and `transparent` for a direct dial (line 768). In both, the guest completed TLS with the receiver's own BV-05 leaf. The proxy tunneled the bytes and did not end TLS itself. The clean sandbox's denied request got a Docker-issued leaf, `O=Docker Sandboxes; CN=localhost` from `Docker Sandboxes Proxy CA`, and curl failed on the hostname (line 407). On the deny path the proxy answered TLS itself and never opened a connection to the receiver.

## Required cases

| Case | Expected evidence | Actual | Classification |
| --- | --- | --- | --- |
| 1. Headless creation, disabled setting, binding, reuse | Disabled-setting rejection and enabled creation, then the required binding and a repeated setup | With the setting false, `sbx create --kit` exited 1 before any image work with `resolve kits: ... local kit sources are disabled (kit.allowLocalKits=false)` and `try: sbx settings set kit.allowLocalKits true`. `sbx ls --json` still returned `{"sandboxes": []}` (lines 139 and 145). With the setting at default, headless create from `/dev/null` exited 0 (line 234). The kit declares `bv05-agentd` as `required: true` with no stored secret or binding. sbx printed `WARN: required credential has no binding; sandbox will start without it` and `Note: no binding authorizes bv05-agentd — the credential was not injected` and created the sandbox anyway. It added the kit's own two allows and no other network rule (line 1115). The fixture reused its CA on a later PKI run (`ca_issued` all false, line 856). Repeated sbx setup and duplicate bindings are untested, since the approval covers one kit sandbox and binding needs the unapproved fake credential. | Disabled setting: blocked as designed, observed. Enabled headless create: allowed, observed. Unbound required credential: warns and proceeds instead of failing, with no policy broadening, observed. Binding and duplicate bindings: blocked on the fake credential. |
| 2. Clean versus kit, CA and leaf matrix | Proxy path, receiver TLS and SNI, injection, valid, unrelated, wrong-host, and expired leaves | Clean: the proxy denied `localhost:18443` by default deny (line 501). The guest saw a Docker proxy leaf for `CN=localhost` and curl exited 60 (line 407). The receiver log has no entry for the clean sandbox (line 495). Kit, all through `forward-bypass`: the `valid` leaf returned 200 with receiver SNI `host.docker.internal`, TLSv1.3, and no `Authorization` header (line 451). `hdi-only` returned 200 (line 693). `wrong-host` and `localhost-only` failed with curl 60 on the hostname, `expired` failed with verify result 10, and `unrelated` failed with verify result 20 (lines 628 to 677). No injection occurred, since no credential was bound. | Leaf matrix in the kit sandbox: verified, the guest enforces CA, name, and validity end to end. Clean: blocked by policy, observed. Injection: blocked on the fake credential. |
| 3. `https://host.docker.internal:18443` route | Guest URL, DNS and dial, policy target, injection match, upstream name | Guest URL `https://host.docker.internal:18443/...`. Guest DNS `fe80::1`. Proxied dial to `gateway.docker.internal` at `fd61:8f11:ddb2::2` port 3128 (line 451). Direct dial with `--noproxy '*'` tried `[fe80::1]:18443`, then `169.254.1.1:18443`, and was caught by the transparent proxy with the same policy decision: denied for clean with TLS EOF, allowed for kit (lines 743 to 768). The policy target in the proxy log is `localhost:18443`. `sbx policy check network --sandbox bv05-kit` allows both `host.docker.internal:18443` and `localhost:18443`, and both are denied for `bv05-clean` (lines 570 to 601). The upstream verification name was `host.docker.internal`, checked by the guest because the `localhost-only` leaf failed and `hdi-only` passed. Injection match is untested. Which of the kit's two allow entries is required is untested, since a single-entry kit needs another sandbox. | Route: allowed through the kit's own rules with no extra rule, observed. Policy target translation to `localhost`: observed. Injection match: blocked on the fake credential. |
| 4. Proxy trust, public-only kit, renewal, restart | Kit holds the public CA only, Docker proxy trust retained, renewal and restart without a new root | The kit tree has `spec.yaml` and `files/home/bv05/bv05-ca.crt` only, and a `PRIVATE KEY` scan found nothing (line 104). The kit guest bundle holds `CN=BV-05 disposable ca` (`0F:36:FD:3C...`) and `Docker Sandboxes Proxy CA`. The clean guest bundle lists the Docker proxy CA only (lines 394 and 400). The proxy CA fingerprint differs per sandbox. A `renewed` leaf from the unchanged CA returned 200 before and after `sbx stop bv05-kit` and a restart through `sbx exec` (lines 877 to 910). After the restart, the CA symlinks kept their create-time dates and the startup log showed only the shell kit's startup command, so the install did not run again. | Verified for the tunnel path. |
| 5. Optional client certificate with bearer | Same listener asks for an optional certificate while the proxy sends bearer | Receiver with `CERT_OPTIONAL` and the client CA (line 917). From the kit guest through the tunnel, each of three requests got 200 (lines 927 and 995). They were a plain request, a request with a guest-supplied fake bearer, and a request with a guest-supplied client certificate plus bearer, which the receiver logged with fingerprint `f29b808ea1aac905`. The first certificate attempt failed with curl 43 because `sbx cp` wrote the key with uid 501 and mode 0600, which the guest `agent` user cannot read. The retry ran as root, and the copied key was deleted in the guest. Proxy bearer injection is untested. | Optional client certificate on the tunnel path: does not break the listener, observed. With proxy injection: blocked on the fake credential. |
| 6. M-003 bounded non-consuming wait | Hold duration, transport behavior, support status, timeout and reconnection traces, delivery state around each wait | Transport: HTTPS through the `forward-bypass` tunnel from `bv05-kit`. The delivery store went from 0 lines to 1 line on one positive-control POST, SHA-256 `70e03a57...21d3c` (lines 1014 to 1026). Holds of 5 s, 60 s, and 300 s returned after 5.057 s, 60.24 s, and 300.238 s (lines 1032, 1045, 1097). A curl `--max-time 2` against a 10 s hold was seen by the receiver as `peer_closed` at 1.957 s (line 1058). A reconnecting 3 s wait returned after 3.043 s (line 1071). The store stayed at 1 line with the same hash after every wait. | Supported within a 300 s bound, observed. Hold times beyond 300 s are untested. |

## Kit-only failure hop and host bundle

No kit-only failure hop appeared. In every allowed request the proxy tunneled TLS, and the guest trusted the BV-05 CA from the kit. The host proxy never had to verify the receiver's leaf, so the process-scoped host bundle had no hop to fix and was not run. Credential injection needs the proxy to end the guest's TLS and open its own upstream TLS to the receiver. Whether that upstream check accepts a leaf from the BV-05 CA is the one hop that could still fail kit-only. It stays untested until a fake credential is bound (inference).

## Other observations

- Idle sandboxes stopped on their own. `bv05-clean` was `stopped` at 17:20:59 after its last use at 17:19:50, and `sbx exec` started a stopped sandbox again with `Sandbox ... started successfully` (lines 719 and 743). Observed, idle timeout not measured.
- The shell kit's startup tries `ports.ubuntu.com:80` and `download.docker.com:443`, and deny-all blocks both (line 501). Sandbox creation still succeeded. Observed.
- Both guests set proxy-managed environment variables for several built-in services, and `bv05-kit` also sets `BV05_TOKEN`. The executor printed only their names and redacted the values inside the guest. Their contents were not inspected.

## Blocked and open

- Fake credential for injection: not approved (BV-23 item 2). This blocks the binding part of case 1, injection in case 2, injection match in case 3, proxy bearer in case 5, and the upstream hop above.
- Single-entry kit to show which allow entry is required: needs a sandbox beyond the two approved.
- Repeated sbx setup and duplicate bindings: needs a second kit create and a bound credential.
