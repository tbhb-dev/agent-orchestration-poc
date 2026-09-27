# Observability source snapshot

Observed on macOS arm64 with mise 2026.8.6 on 2026-09-26. Source clones are under `/tmp/observability-110-*` because the sandbox does not permit writing to `~/Code/github.com`.

| Source | Release tag | Commit read | Versioned material read |
| --- | --- | --- | --- |
| [Grafana](https://github.com/grafana/grafana/tree/3db12332b66497c31f8ad2a5fb0eb0fe0ca05a7e) | `v13.2.2` | `3db12332b66497c31f8ad2a5fb0eb0fe0ca05a7e` | `CHANGELOG.md`, `docs/sources/setup-grafana/installation/mac/index.md`, [13.2.2 download page](https://grafana.com/grafana/download?edition=oss&platform=mac) |
| [Alloy](https://github.com/grafana/alloy/tree/352ab819cf06611640a7e82048aa0671d24bbfb3) | `v1.20.0` | `352ab819cf06611640a7e82048aa0671d24bbfb3` | `CHANGELOG.md`, `docs/sources/release-notes.md`, `docs/sources/set-up/install/binary.md` |
| [Tempo current](https://github.com/grafana/tempo/tree/1900ed7bb5cad1a3edc285783d7d4ac4278337dc) | `v3.0.3` | `1900ed7bb5cad1a3edc285783d7d4ac4278337dc` | `.goreleaser.yml`, `docs/sources/tempo/release-notes/v3-0.md` |
| [Tempo native candidate](https://github.com/grafana/tempo/tree/b33945abd3e99ddeb05e5d8e71155df7800a615a) | `v2.7.2` | `b33945abd3e99ddeb05e5d8e71155df7800a615a` | `.goreleaser.yml`, `docs/sources/tempo/release-notes/v2-7.md`, `docs/sources/tempo/setup/upgrade.md` |
| [Loki](https://github.com/grafana/loki/tree/09e6ce2ff1bdc19763a10265b870c86f51c98655) | `v3.7.8` | `09e6ce2ff1bdc19763a10265b870c86f51c98655` | `CHANGELOG.md`, `docs/sources/setup/install/local.md`, `docs/sources/release-notes/v3-7.md`, `docs/sources/operations/upgrade.md` |
| [Mimir](https://github.com/grafana/mimir/tree/e49585d43c6e852225e114bd1ddd98da58a4c060) | `mimir-3.2.1` | `e49585d43c6e852225e114bd1ddd98da58a4c060` | `CHANGELOG.md`, `docs/sources/mimir/release-notes/v3.2.md`, `docs/configurations/single-process-config-blocks.yaml` |
| [mise](https://github.com/jdx/mise/tree/71212d424cd07189b22027f496c01ccad76e8b6d) | `v2026.8.6` | `71212d424cd07189b22027f496c01ccad76e8b6d` | `docs/dev-tools/backends/github.md`, `docs/dev-tools/backends/http.md`, `docs/dev-tools/backends/aqua.md`, `docs/directories.md`, `src/backend/github.rs`, `src/backend/http.rs` |

The source clones use `git clone --depth 1 --filter=blob:none --sparse --branch <tag>`. The table records the peeled commit, rather than an annotated tag object's SHA. The release pages and download assets were queried on 2026-09-26. Their `latest` labels can change after this snapshot.
