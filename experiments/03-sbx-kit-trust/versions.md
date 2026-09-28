# BV-05 versions and source pins

## Fourth sbx run, 2026-09-28

| Item | Recorded version or revision | Evidence and limit |
| --- | --- | --- |
| Host | macOS 26.5.1, build `25F80`, arm64 | Observed with `sw_vers; uname -m` in the [fourth-run ledger](evidence/sbx-run-4/ledger.txt). |
| Docker Sandboxes CLI | v0.45.1, `9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb` | Observed by `sbx version` before and after in the [ledger](evidence/sbx-run-4/ledger.txt); the revision identifies the binary, not reviewed source. |
| Executor and checkout | Claude Code with `claude-opus-5-5`, from `main` at `14e63e4` on `exp/229-sbx-kit-trust-4` | Recorded in the [fourth-run notes](evidence/sbx-run-4/notes.md); this run did not record a Claude Code CLI version or effort, and no harness ran inside sbx. |
| Sandbox template | `docker/sandbox-templates:shell-docker` | The first create pulled this tag and the second reused it in the [ledger](evidence/sbx-run-4/ledger.txt). The run did not record an immutable image digest. |
| Kit | `schemaVersion: "2"`, `kind: mixin`, kit version `0.1.0` | The [fourth-run notes](evidence/sbx-run-4/notes.md) report an exit-0 byte comparison with the committed [kit spec](evidence/installed-sbx-run/kit/spec.yaml). The run did not record a new documentation or source revision check. |
| Receiver and guest client | Python 3.14.6 receiver, `curl/8.18.0` guest | Observed in the HTTP server header and verbose guest request in the [ledger](evidence/sbx-run-4/ledger.txt). This run did not record the host curl or OpenSSL versions. |
| Transport | TLSv1.3 for receiver requests | Observed in the [receiver log](evidence/sbx-run-4/receiver.jsonl). This is the negotiated protocol. |
| Disposable PKI | BV-05 CA fingerprint `0F:36:FD:3C:48:DD:10:BA:8C:F9:4E:0D:33:3A:70:82:73:B3:1E:B1:13:03:C4:C7:98:B1:4D:B0:32:69:47:27`; second invocation reported all `ca_issued` values false | Observed in the [manifest](evidence/sbx-run-4/pki-manifest.json) and [ledger](evidence/sbx-run-4/ledger.txt). The manifest lists leaf fingerprints and issuance times. |
| Prior source pins | Imported design `8384ca71d1ecc8ff590878fc4351954dbadd06d4`; Docker documentation `dvdksn/docs@75d1ee312280c2028be294e043edeaf35f2fe1bb` | The table below records these earlier documentation pins, and the [fourth-run notes](evidence/sbx-run-4/notes.md) and [ledger](evidence/sbx-run-4/ledger.txt) do not record another source check. |

## Earlier attempts and source pins

| Item | Recorded version or revision | Evidence |
| --- | --- | --- |
| Host | macOS 26.5.1 (25F80), arm64 | `sw_vers` and `uname -m`, exit 0 |
| Docker Sandboxes CLI | v0.45.1, `9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb` | `sbx version`, exit 0 |
| Imported design | `8384ca71d1ecc8ff590878fc4351954dbadd06d4` | [BV-05](../../research/imported/design-wiki-8384ca7/backend-validation-spikes.md#bv-05-sbx-kit-routing-and-server-trust) and [authentication](../../research/imported/design-wiki-8384ca7/spiffe-mtls-authentication.md) |
| Docker documentation | `dvdksn/docs@75d1ee312280c2028be294e043edeaf35f2fe1bb` | Read pinned [kit reference](https://github.com/dvdksn/docs/blob/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes/customize/kit-reference.md), [kit example](https://github.com/dvdksn/docs/blob/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes/customize/kit-examples.md), [credentials](https://github.com/dvdksn/docs/blob/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes/configuration/credentials.md), [host services](https://github.com/dvdksn/docs/blob/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes/workflows/development.md), and [troubleshooting](https://github.com/dvdksn/docs/blob/75d1ee312280c2028be294e043edeaf35f2fe1bb/content/manuals/ai/sandboxes/troubleshooting.md) through GitHub REST |
| Docker kit schema | Version 2 is documented for sbx 0.36 and later | Pinned kit reference, lines 34 to 42 |
| Executor | Claude Code 2.1.284, `claude-opus-5-5`, medium effort | [Third-run notes](evidence/installed-sbx-run/notes.md); no integrated harness ran |
| Fixture runtime | Python 3.14.6 through mise, Homebrew OpenSSL 3.6.3 | [Third-run notes](evidence/installed-sbx-run/notes.md); [host replay](evidence/installed-sbx-run/host-replay.txt) |
| Kit on installed sbx | Schema version 2, `kind: mixin`; `sbx kit validate` returned `VALID` at default `kit.allowLocalKits=true` | [Third-run ledger](evidence/installed-sbx-run/ledger.txt) and [kit](evidence/installed-sbx-run/kit/spec.yaml) |

The 2026-09-28 continuation rechecked `sbx version`, `sw_vers`, and `uname -m` and observed the same CLI and host versions. It read the pinned kit reference again through `gh query` at the Docker documentation revision above. The checkout began at `6b5188bda7402b45a6d6792d2b049a8e62909988`. [The operator-state ledger](evidence/operator-state-attempt.md) records the failed daemon and authentication prerequisites.

The sbx source was unavailable from the public release repository. The CLI revision above identifies the installed binary, not a reviewed source checkout. No dependency source was cloned. Pinned documentation was read through GitHub REST, and the local checkout was `c7b0fa9c17cbf255986b20863ac93d9bf2de717e` before this work.

The third attempt began from `cb7fdd7` on `exp/229-sbx-kit-trust-3` after Docker sign-in. The installed-sbx setting probe ran and was undone. Clean and kit sandbox creation stopped at the uninitialized global policy. The fixture ran only on the host. Its first as-run kit and receiver observations are in [the notes and ledger](evidence/installed-sbx-run/notes.md), and a corrected fixture was re-verified host-only. [The fresh replay](evidence/installed-sbx-run/host-replay.txt) uses a separate disposable PKI and port 18453 to record receiver lifecycle and certificate-verification commands that were absent from the original ledger. The original receiver launch and the output from OpenSSL verification cannot be reconstructed as observed history. The daemon was stopped before the third attempt, started by `sbx ls --json`, and left running because its stop command was denied.
