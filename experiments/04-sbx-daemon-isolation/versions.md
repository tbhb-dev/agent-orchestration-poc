# Versions and source pins

| Item | Pin or observation | Evidence |
| --- | --- | --- |
| Host | macOS 26.5.1, build 25F80, arm64 | [`sw_vers`](evidence/sw_vers.txt) and [`uname -m`](evidence/uname-m.txt), exit 0 |
| Installed CLI | `sbx` v0.45.1, build revision `9d79d90ee4c5d297fb3d36b75384e8cea7a4fbcb` | [`sbx version`](evidence/sbx-version.txt), exit 0, `/opt/homebrew/bin/sbx` resolves to `/opt/homebrew/Caskroom/sbx/0.45.1/Sbx.app/Contents/MacOS/sbx` |
| Release | `docker/sbx-releases` v0.45.1, published 2026-09-22 | [Release record](https://github.com/docker/sbx-releases/releases/tag/v0.45.1) read through REST, release target `main` |
| Docker documentation | `dvdksn/docs@75d1ee312280c2028be294e043edeaf35f2fe1bb` | [Pinned files and commands](evidence/source-inspection.md) |
| Product source | Unavailable from the public release repository | `gh api repos/docker/sbx` returned HTTP 404, so the CLI revision is not a reviewed source commit |
| Imported BV-05 design | `8384ca71d1ecc8ff590878fc4351954dbadd06d4` | [Frozen BV-05 page](../../research/imported/design-wiki-8384ca7/backend-validation-spikes.md#bv-05-sbx-kit-routing-and-server-trust) |
| Requester provenance | Codex CLI 0.157.1, `gpt-6-sol`, high effort for the source BV-05 work | [PR #236](https://github.com/tbhb-dev/agent-orchestration-poc/pull/236), distinct from this worker's assignment |
| Implementer | Codex CLI 0.157.1, `gpt-6-sol`, high effort | Coordinator dispatch for issue #237 |

The issue review [comment 5873150644](https://github.com/tbhb-dev/agent-orchestration-poc/issues/237#issuecomment-5873150644) also notes that #229 already lists #237 as a blocker. The existing dependency link is the one this experiment uses.
