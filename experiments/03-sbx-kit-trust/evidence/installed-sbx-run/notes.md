# Installed sbx run notes, 2026-09-28

These are raw executor notes for Codex. They record the third BV-05 attempt against the operator's installed sbx under operator decision item 15, after the operator signed the operator sbx in to Docker at 15:40 EDT. The executor was Claude Code 2.1.284 with `claude-opus-5-5`, dispatched by the coordinator as the BV-05 executor. The checkout was `exp/229-sbx-kit-trust-3` from `main` at `cb7fdd7`. Every time below is EDT on 2026-09-28 and comes from `date` or the ledger's own `date` call.

## Environment

| Item | Value | Label |
| --- | --- | --- |
| Host | macOS 26.5.1 (25F80), arm64 | observed, `sw_vers` and `uname -m` |
| sbx | v0.45.1, `9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb`, `/opt/homebrew/Caskroom/sbx/0.45.1/Sbx.app/Contents/MacOS/sbx` | observed, `sbx version` and `realpath` |
| Docker documentation | `dvdksn/docs@75d1ee312280c2028be294e043edeaf35f2fe1bb`, 12 pages under `content/manuals/ai/sandboxes/` read through `gh query` contents API | documented |
| Kit schema | `schemaVersion: "2"`, `kind: mixin`, validated `VALID` by the installed `sbx kit validate` | observed |
| OpenSSL for the disposable PKI | OpenSSL 3.6.3, Homebrew | observed |
| Python for the fixture | 3.14.6 through `mise exec` | observed |

[`ledger.txt`](ledger.txt) records every command with its timestamp, output, and exit code, plus the three denied commands. The record at 15:44:57 is an empty invocation of the ledger helper, which ran `bash -c ''` and executed nothing.

## Operator sbx state

| Surface | Before (15:42 to 15:44) | After (15:52 to 15:54) | Label |
| --- | --- | --- | --- |
| Daemon | `Status: stopped`, socket not connected, at 15:42:54 and 15:43:06 | `Status: running` at 15:53:55 | observed |
| Sandboxes | `{"sandboxes": []}` at 15:43:06 | `{"sandboxes": []}` at 15:52:44 | observed |
| `kit.allowLocalKits` | `value: true`, `source: default` | `value: true`, `source: default` | observed |
| All settings | 32 records, all `source: default`, SHA-256 of `sbx settings list --json` output `0477633d...af0f4` | Same SHA-256, `jq -S` diff empty | observed, [before](settings-before.json) and [after](settings-after.json) |
| Global network policy | `error: global network policy has not been initialized` | Same error | observed |
| Stored secrets | Not recorded, read denied | Not recorded | denied |
| Credential bindings file | Not recorded, metadata read denied | Not recorded | denied |
| Trust stores | Not read or changed | Not read or changed | inference, no trust command ran |

The first `sbx ls --json` at 15:43:06 printed `Starting sandboxd daemon...`, so the daemon ran from then on. The executor's `sbx daemon stop` at 15:53:55 was denied. The daemon still runs, but it was stopped at the start. Nothing else the executor could read changed. Stored secrets and the bindings file could not be compared because both reads were denied.

## Approved probes and undo ledger

| Probe | Commands and exits | Undo | Result |
| --- | --- | --- | --- |
| Local-kit setting | `sbx settings set kit.allowLocalKits false` exit 0, `source=override` at 15:50:21, then `sbx settings set kit.allowLocalKits true` exit 0 at 15:50:42 | `sbx settings unset kit.allowLocalKits` exit 0 at 15:50:43 | Restored, `source: default` and the full settings hash match the start |
| `bv05-kit` sandbox | `sbx create --name bv05-kit shell --kit /private/tmp/bv05-kit < /dev/null` exit 1 at 15:50:29 (setting false) and 15:51:23 (default) | `sbx rm` not needed | No sandbox created, `sbx ls --json` empty at 15:50:29, 15:51:24, and 15:52:44 |
| `bv05-clean` sandbox | `sbx create --name bv05-clean shell < /dev/null` exit 1 at 15:51:22 | `sbx rm` not needed | No sandbox created |
| Process-scoped host bundle | Not run, no kit-only failure hop was reached | `sbx daemon stop` and bundle removal not needed | The executor didn't create a bundle |

Both creates failed with `error: global network policy has not been initialized` and `try: sbx policy init <allow-all|balanced|deny-all>` before any kit, image, or sandbox work was visible. `sbx policy init` changes the operator's global policy store and is not among the approved probes. The sandbox-dependent cases stop at this point.

## Denied commands

| Time | Command | Classifier reason | Consequence |
| --- | --- | --- | --- |
| 15:44:36 | `sbx secret ls -q`, count and a 16-hex SHA-256 of the sorted `-q` output | Credential Exploration | Secret inventory not recorded before or after |
| 15:50:11 | `stat` of `~/.config/sbx` and `~/.config/sbx/credentials.yaml` | Credential Exploration | Bindings file existence and metadata not recorded |
| 15:53:55 | `sbx daemon stop` | Interfere With Workloads | Daemon left running, the start state was stopped |

No alternate route was tried for any of them. The last one is the only undo left incomplete.

## Required cases

| Case | Expected evidence | Actual | Classification |
| --- | --- | --- | --- |
| 1. Headless creation, disabled setting, binding, reuse | Disabled-setting rejection, enabled creation, required binding, repeat setup count | With the setting false, `sbx kit validate /private/tmp/bv05-kit` exit 1: `local kit sources are disabled (kit.allowLocalKits=false); the reference "/private/tmp/bv05-kit" points at a local directory or ZIP file; artifact validation failed` and `try: sbx settings set kit.allowLocalKits true`. The same validate exits 0 `VALID` with the setting at default. `sbx create` under both setting values stopped earlier, at the uninitialized global policy, with an explicit remedy and no silent preset. Binding untested. The fixture reused its CA on a second setup run (`ca_issued` false, same fingerprint), but sbx-side reuse is untested. | Blocked, with the disabled-setting rejection observed through `kit validate` only |
| 2. Clean versus kit, CA and leaf matrix | Proxy path, receiver TLS and SNI, injection, valid, unrelated, wrong-host, and expired leaves | Leaves issued and checked on the host (`openssl verify`: valid OK, expired and unrelated fail, wrong-host chains to the CA). No sandbox existed. | Blocked |
| 3. `https://host.docker.internal:<agentd-port>` route | Guest URL, DNS and dial, policy target, injection match, upstream name | `sbx policy check network localhost:18443` exit 1: `412 Precondition Failed: global network policy has not been initialized`, and without a sandbox the guest side went unobserved. | Blocked |
| 4. Proxy trust, public-only kit, renewal, restart | Kit holds the public CA only, Docker proxy trust retained, renewal and restart without a new root | Kit files are `spec.yaml` and `files/home/bv05/bv05-ca.crt`, and a `PRIVATE KEY` scan of the kit found nothing. The `renewed` leaf was issued from the unchanged CA. Guest trust, renewal, and restart need a sandbox. | Blocked, kit contents verified |
| 5. Optional client certificate with bearer | Same listener asks for an optional certificate while the proxy sends bearer | Host-only simulation: with `CERT_OPTIONAL`, curl with a fake bearer and no client certificate got 200. A `clientAuth` leaf also got 200, and the receiver logged its fingerprint. The sbx proxy took no part. | Blocked for sbx, fixture simulated |
| 6. M-003 bounded non-consuming wait | Hold duration, transport behavior, support status, timeout and reconnection traces, delivery state around each wait | Host-only simulation: a 5 s hold returned after 5.071 s, a curl `--max-time 2` against a 10 s hold was seen by the receiver as `peer_closed` at 2.0 s, and a reconnection wait returned after 3.038 s. The delivery store held 1 line, SHA-256 `627d1dcb...28e11e8`, from one positive-control POST, and was unchanged after all three waits. The sbx hold ceiling, timeout, and reconnection behavior are unmeasured. | Blocked and inconclusive for sbx, fixture simulated |

This is a partial delivery because no required case has an sbx runtime answer, and it doesn't accept any security property, backend profile, or harness cell. The host-bundle configuration is untested because its precondition, an identified kit-only failure hop, needs a running kit sandbox. The run didn't use an interim operator control path, provisional exact-path binding, or workload wrapper.

## Fixture

[`fixture.py`](../../fixture.py) has three subcommands. `pki` creates or reuses a disposable CA, an unrelated CA, and a client CA, then issues the leaf set, and appends public fingerprints to a manifest. `kit` writes the public-only mixin kit. `serve` runs a loopback HTTPS receiver on `127.0.0.1:18443` that logs SNI, TLS version, client-certificate fingerprint, header names, and a 16-hex SHA-256 of any `Authorization` value, never the value. Its `/wait` endpoint holds without consuming anything and logs `hold_elapsed` or `peer_closed`. Its `POST /deliver` endpoint is the delivery-store positive control. The first client-certificate simulation failed with `alert unsupported certificate` because the fixture gave the client leaf `serverAuth` only. The fix gives client-CA leaves `clientAuth` and the rerun passed.

After the run, strict pyrefly rejected the fixture's typing. The committed version adds annotations and `@override` and reads the receiver through a checked property. It also records SNI in a receiver-side map keyed by connection instead of an attribute set on the socket. At 15:57 the committed version was re-run host-only against a fresh scratch PKI, with these results:

- The second setup reused the CA.
- The kit spec matched apart from the port.
- Bearer requests passed with and without a client certificate.
- The untrusted client reset the connection.
- One positive-control delivery was written to the store.
- A client timeout showed as `peer_closed` at 1.998 s.
- A full 2 s hold returned normally.

[`reverify-receiver.jsonl`](reverify-receiver.jsonl) records that log. The scratch PKI was then removed.

The repository YAML linter then rejected the as-run `spec.yaml` for a 130-character line and a missing `---`. The fixture now writes `---` first and folds the install command with `>-`. That is the only difference from the spec `sbx` saw during the run. PyYAML parsed the as-run and committed specs to equal objects, and the installed `sbx kit validate` returned `VALID` for a kit regenerated with the committed fixture at 15:59:26 (last ledger entry). The committed [`kit/spec.yaml`](kit/spec.yaml) is that regenerated form.

The public artifacts are the [kit](kit/spec.yaml), its [CA certificate](kit/files/home/bv05/bv05-ca.crt), the [PKI manifest](pki-manifest.json), the [receiver log](receiver.jsonl), and the [delivery store](deliveries.jsonl). Private keys stayed under `/private/tmp/bv05-pki` and are not committed. The ledger replaces the fake bearer string in three curl commands with `<fake-bearer-redacted>` because gitleaks matches any bearer header. The receiver log keeps only its fingerprint, `f1b2c1b863c9c988`, and the string authenticates nothing.

The kit declares `credentials[].service: bv05-agentd` with `required: true`, `apiKey.name: BV05_TOKEN`, `proxyManaged: true`, and bearer injection for `host.docker.internal`. It allows `localhost:18443` and `host.docker.internal:18443`, and installs the CA with `update-ca-certificates` without replacing the guest bundle. Both allow entries exist because the pinned host-services page says the proxy translates `host.docker.internal` to `localhost` for policy. Which one matches remains a case 3 question.

## Operator proposals

These are unexecuted. Each needs the operator's explicit approval before a later run.

1. Initialize the global policy for the run: `sbx policy init deny-all`. It creates the global network policy store, which is uninitialized now, with the Locked Down preset, so only the kit's per-sandbox allow rules open egress for `bv05-kit`. Undo after `sbx rm bv05-clean bv05-kit`: `sbx policy reset --force`. Help-text says reset deletes the local policy store and stops the daemon. The next command then prompts for initialization, matching the uninitialized start. That return to uninitialized is help-text only until observed. Reset stops running sandboxes, and the operator had none at 15:52:44.
2. Bind a fake credential so injection is observable: `printf %s <fake value> | sbx secret set bv05-agentd --sandbox bv05-kit`, plus a `bindings.bv05-agentd.apiKey.domains: [host.docker.internal]` entry in `~/.config/sbx/credentials.yaml`. Undo: `sbx rm bv05-kit` removes sandbox-scoped secrets per earlier help-text, and the binding entry is removed by hand. Whether `sbx secret set` accepts a custom service identifier is untested, since its help lists built-in services only while the pinned credentials page says custom kits use the same flow. Because the executor could not read or stat the bindings file, the operator would make or approve that edit. Answering the first-run approval prompt in an interactive `sbx create` is the alternative.
3. Restore the daemon to its starting state: `sbx daemon stop`. It doesn't need an undo. It stops only sandboxes that are running, and none were at 15:52:44.
