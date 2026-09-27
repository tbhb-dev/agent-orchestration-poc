# Native observability provider research

## Scope and decision gate

This pass tests installation and version execution only. It does not establish a running stack, portable configuration, bounded retention, loopback bindings, or a resource profile. Issue #107 has not activated the required notebook tasks at this snapshot, and issue #110 reserves profiling until that gate is runnable.

The initial 780-unit estimate appears low after the provider pass. A working five-process lifecycle and configuration, core and shell tests, walker probes, retention and network probes, notebook, independent review, and site docs are estimated at about 1,050 #84 units. Issue #110 requires the coordinator to split work above 800 before stack code. The smallest independent piece is the version and provider record in this PR. The proposed dependent pieces are native lifecycle and ingestion, followed by verified profiling after #107.

## Provider findings

**Observed:** `mise registry grafana`, `alloy`, `tempo`, `loki`, and `mimir` each exited 1 with `tool not found in registry` on mise 2026.8.6. An explicit backend is therefore necessary. The [mise backend guide at the tested commit](https://github.com/jdx/mise/blob/71212d424cd07189b22027f496c01ccad76e8b6d/docs/dev-tools/backends/github.md) describes GitHub asset matching, while its [HTTP guide](https://github.com/jdx/mise/blob/71212d424cd07189b22027f496c01ccad76e8b6d/docs/dev-tools/backends/http.md) covers a publisher archive URL and checksum.

**Observed:** `mise ls-remote aqua:grafana/alloy` listed 1.20.0. The corresponding Aqua probes for Grafana, Tempo, Loki, and Mimir reported `no aqua-registry found`. `mise ls-remote` returned exit 0 even on those warnings, so the warnings are the result. Explicit GitHub assets worked for Alloy, Loki, and Mimir. [Alloy's standalone binary guide](https://github.com/grafana/alloy/blob/352ab819cf06611640a7e82048aa0671d24bbfb3/docs/sources/set-up/install/binary.md) and [Loki's local guide](https://github.com/grafana/loki/blob/09e6ce2ff1bdc19763a10265b870c86f51c98655/docs/sources/setup/install/local.md) document the release-asset route.

**Observed:** `mise install github:grafana/grafana@13.2.2` exited 1 with `No matching asset found for platform macos-arm64`. The GitHub release lists Linux packages, while Grafana's [versioned macOS source guide](https://github.com/grafana/grafana/blob/3db12332b66497c31f8ad2a5fb0eb0fe0ca05a7e/docs/sources/setup-grafana/installation/mac/index.md) points to its standalone download page. The [13.2.2 OSS download page](https://grafana.com/grafana/download?edition=oss&platform=mac) publishes the arm64 archive and SHA-256 `9ea91bf7cc92aa34dd59321c44e7a15a22ee6f3dbb491849a6357451d35d5932`. The `http:grafana` backend downloaded and executed this archive in the local probe. A future portable pin needs a tested Linux URL and checksum alongside the macOS mapping.

**Observed:** `mise install github:grafana/tempo[matching_regex=^tempo_]@3.0.3` exited 1 with `No matching asset found for platform macos-arm64`. The v3.0.3 [.goreleaser.yml](https://github.com/grafana/tempo/blob/1900ed7bb5cad1a3edc285783d7d4ac4278337dc/.goreleaser.yml) comments out `darwin` and points at a Go linker issue. This shows why that release has no macOS asset, but it does not prove a local source build would fail. Tempo v2.7.2 [.goreleaser.yml](https://github.com/grafana/tempo/blob/b33945abd3e99ddeb05e5d8e71155df7800a615a/.goreleaser.yml) includes Darwin, and the release archive installed and executed. Its [upgrade guide](https://github.com/grafana/tempo/blob/b33945abd3e99ddeb05e5d8e71155df7800a615a/docs/sources/tempo/setup/upgrade.md) records a receiver default binding change in 2.7. The provisional choice is 2.7.2 for the five-native-process requirement. It needs approval before configuration because it is an older major version.

**Documented:** Grafana 13.2.2, Alloy 1.20.0, Loki 3.7.8, and Mimir 3.2.1 release changes were read at the commits in `versions.md`. Tempo 3.0 changes its ingest architecture and offers a monolithic mode without Kafka, per its [v3.0 source release notes](https://github.com/grafana/tempo/blob/1900ed7bb5cad1a3edc285783d7d4ac4278337dc/docs/sources/tempo/release-notes/v3-0.md). That larger version difference needs an explicit pin choice before configuration is written.

## Clone-local probe

**Observed:** All five successful provider probes set `MISE_DATA_DIR`, `MISE_CACHE_DIR`, `MISE_STATE_DIR`, and `MISE_CONFIG_DIR` beneath this checkout's ignored `.observability/mise/`. `mise where <provider>@<version>` resolved beneath `.observability/mise/data/installs/`. The [mise directory guide at the tested commit](https://github.com/jdx/mise/blob/71212d424cd07189b22027f496c01ccad76e8b6d/docs/directories.md) documents these overrides. The local trust state required trusting this worktree and its parent configuration again after changing `MISE_STATE_DIR`.

The probe used these exact environment overrides and provider arguments from the worktree root. Each `mise install`, `mise where`, and `mise exec` command for the five successful rows exited 0. The two failed GitHub provider probes exited 1. `mise where` placed each binary under `.observability/mise/data/installs/`.

```sh
export MISE_DATA_DIR="$PWD/.observability/mise/data"
export MISE_CACHE_DIR="$PWD/.observability/mise/cache"
export MISE_STATE_DIR="$PWD/.observability/mise/state"
export MISE_CONFIG_DIR="$PWD/.observability/mise/config"
mise trust
mise trust /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/mise.toml
mise install 'http:grafana[url=https://dl.grafana.com/grafana/release/13.2.2/grafana_13.2.2_34846740809_darwin_arm64.tar.gz,checksum=sha256:9ea91bf7cc92aa34dd59321c44e7a15a22ee6f3dbb491849a6357451d35d5932]@13.2.2'
mise install 'github:grafana/alloy[matching_regex=^alloy-]@1.20.0'
mise install 'github:grafana/tempo[matching_regex=^tempo_]@2.7.2'
mise install 'github:grafana/loki[matching_regex=^loki-(darwin|linux|windows)]@3.7.8'
mise install 'github:grafana/mimir[matching_regex=^mimir-(darwin|linux|freebsd)]@mimir-3.2.1'
mise where 'http:grafana@13.2.2'
mise where 'github:grafana/alloy@1.20.0'
mise where 'github:grafana/tempo@2.7.2'
mise where 'github:grafana/loki@3.7.8'
mise where 'github:grafana/mimir@mimir-3.2.1'
mise exec 'http:grafana@13.2.2' -- grafana --version
mise exec 'github:grafana/alloy[matching_regex=^alloy-]@1.20.0' -- alloy --version
mise exec 'github:grafana/tempo[matching_regex=^tempo_]@2.7.2' -- tempo --version
mise exec 'github:grafana/loki[matching_regex=^loki-(darwin|linux|windows)]@3.7.8' -- loki --version
mise exec 'github:grafana/mimir[matching_regex=^mimir-(darwin|linux|freebsd)]@mimir-3.2.1' -- mimir -version
mise install 'github:grafana/grafana@13.2.2'
mise install 'github:grafana/tempo[matching_regex=^tempo_]@3.0.3'
```

The successful selections were `alloy-darwin-arm64.zip`, `loki-darwin-arm64.zip`, `mimir-darwin-arm64`, and `tempo_2.7.2_darwin_arm64.tar.gz`. Grafana used the download page's archive and published checksum. The observed version strings were `13.2.2`, `v1.20.0`, `2.7.2`, `3.7.8`, and `3.2.1` in table order. No Linux installation or service start has been run.

## Remaining work

The lifecycle slice needs approved pins, per-platform mise mappings, configuration and pure decisions with tests, checker exclusions and sentinels, loopback and retention probes, and clean-start and restart captures. The profile slice needs #107's executable Quarto tasks, load and resource samples, claims and notebook verification, an independent different-model review, and the design and runbook pages. Neither slice should be reported as verified from these installation probes.
