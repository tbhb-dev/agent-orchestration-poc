# Versions and source reads

Stage-one continuation on 2026-09-28 used macOS 26.5.1 build 25F80 on arm64, Python 3.14.6, Codex CLI 0.157.1, Claude Code 2.1.283, and tmux 3.7b. The source checkouts remained `openai/codex@a6bd19261c30ce0a0225fe90e646822d29916f11` and `anthropics/claude-code@7779afb12e3635f46f56ec823979d68350ae000b`. The Codex response fixtures follow `codex-rs/core/tests/common/responses.rs` at that commit, including `ev_function_call`, `ev_completed`, and `sse`. The Claude frames follow the [documented Messages stream event sequence](https://platform.claude.com/docs/en/build-with-claude/streaming), with `tool_use` and `input_json_delta`. The Claude web page is current documentation and is not frozen to CLI 2.1.283. Harness acceptance of these frames remains untested. The installed `/usr/bin/opensnoop` script and the `opensnoop(1m)` and `fs_usage(1)` manuals were read on build 25F80 for [the audit method](file-open-audit.md). This continuation used the existing dependency clones.

| Item | Version or revision | Evidence read |
| --- | --- | --- |
| Host | macOS 26.5.1 build 25F80, Darwin 25.5.0, arm64 | `sw_vers`, `uname -m`, `uname -r` |
| Apple SDK | macOS SDK 26.5 | `xcrun --show-sdk-version`, `sys/un.h`, `sys/proc_info.h`, `mach/message.h`, `bsm/libbsm.h`, `libproc.h` under `/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/` |
| XNU source | `apple-oss-distributions/xnu@f6217f891ac0bb64f3d375211650a4c1ff8ca1ea` | `bsd/kern/uipc_usrreq.c` lines 900-935 and `bsd/kern/uipc_socket.c` lines 400-421, sparse clone at `/private/tmp/bv01-xnu-228` |
| Python | 3.14.6 | `mise exec -- python --version` |
| uv | 0.12.10 | `mise exec -- uv --version` |
| Codex | CLI 0.157.1 | `mise exec -- codex --version` and `codex exec --help`, local source `openai/codex@a6bd19261c30ce0a0225fe90e646822d29916f11`, `codex-rs/config/src/permissions_toml.rs` |
| Claude Code | 2.1.283 | `mise exec -- claude --version` and `claude --help`, local source `anthropics/claude-code@7779afb12e3635f46f56ec823979d68350ae000b`, `examples/settings/settings-bash-sandbox.json` |
| tmux | 3.7b | `mise exec -- tmux -V`, disposable server trace in `evidence/tmux.jsonl` |
| sbx | Not used | Outside this host fixture |
| Imported design | `8384ca71d1ecc8ff590878fc4351954dbadd06d4` | `research/imported/design-wiki-8384ca7/backend-validation-spikes.md` and `spiffe-mtls-authentication.md` |

The XNU checkout is a source revision read for the mechanism, not proof that this Mac booted that exact commit. The targeted runtime trace is tied to build 25F80.

The Python process fixture did not load a Codex or Claude Code sandbox configuration. Neither `permissions.<name>.network.unix_sockets` nor `features.network_proxy.unix_sockets` was set for it. The Codex source defines the former profile field, while the existing assessment records the latter feature field. Claude's example settings define `sandbox.network.allowUnixSockets`, but no Claude settings were changed or measured here. No harness cell is qualified by these settings examples.
