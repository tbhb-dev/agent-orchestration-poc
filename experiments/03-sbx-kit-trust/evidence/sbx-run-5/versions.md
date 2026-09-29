# Fifth-run versions and scope

| Item | Version or state | Evidence |
| --- | --- | --- |
| Host | macOS 26.5.1 (25F80), arm64 | `sw_vers` and `uname -m` in [ledger](ledger.txt) |
| sbx CLI | v0.45.1, `9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb` | `sbx version` in ledger |
| Executor | Codex CLI 0.157.1, `gpt-6-sol` at high | `codex --version` in ledger, dispatch brief for model and effort |
| Checkout | `5bc761c689aa9997cf0b97ea382a543bbc04ba45` before this run's commit | `git rev-parse HEAD` in ledger |
| Fixture runtime | Python 3.14.6 through mise | `python --version` in ledger |
| Public kit | Schema 2, mixin 0.1.0, byte-identical to committed spec | `cmp` and kit file list in ledger |
| Disposable CA | SHA-256 `08:FE:84:2E:8D:C7:34:BD:79:D7:EA:9F:BE:0D:CD:5E:91:5E:E8:93:0A:80:42:D7:72:F2:31:AE:F4:6B:81:D4` | `openssl x509` in ledger |
| Transport | TLSv1.3, receiver loopback port 18443 | [Receiver log](receiver.jsonl) and ledger |
| Sandbox template | `docker/sandbox-templates:shell-docker`, cached image layers | `sbx env create` output in ledger, no immutable digest recorded |
| Docker documentation | `dvdksn/docs@75d1ee312280c2028be294e043edeaf35f2fe1bb` | Existing [experiment versions](../../versions.md), not re-fetched in this run |
| Imported design | `8384ca71d1ecc8ff590878fc4351954dbadd06d4` | Existing [experiment versions](../../versions.md), not re-fetched in this run |

Only the installed sbx, receiver, and guest shell were exercised. No real harness ran inside the sandbox. The operator's fake credential was not read by the executor.
