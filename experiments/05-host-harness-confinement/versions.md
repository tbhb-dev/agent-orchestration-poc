# Versions and source reads

| Item | Version or revision | Source or command read |
| --- | --- | --- |
| Host | macOS 26.5.1 build 25F80, arm64 | `sw_vers`, `uname -m` on 2026-09-28 |
| Worktree base | `0169c84473855a92a40401c78fafb497022a7a0b` | `git rev-parse HEAD` before this change |
| Python | 3.14.6 | `mise exec -- python --version` |
| Codex | CLI 0.157.1, source `openai/codex@a6bd19261c30ce0a0225fe90e646822d29916f11` | `mise exec -- codex --version`, `codex-rs/core/config.schema.json` `NetworkToml` and `NetworkProxyConfigToml`, [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) |
| Claude Code | 2.1.283, source `anthropics/claude-code@7779afb12e3635f46f56ec823979d68350ae000b` | `mise exec -- claude --version`, `CHANGELOG.md` entries for `allowUnsandboxedCommands`, `failIfUnavailable`, and `excludedCommands`, [official sandbox documentation](https://code.claude.com/docs/en/sandboxing) |
| macOS peer identity | XNU source `apple-oss-distributions/xnu@f6217f891ac0bb64f3d375211650a4c1ff8ca1ea` | [BV-01 source and runtime report](../02-host-socket-attribution/versions.md) documents `LOCAL_PEERTOKEN`, `audit_token_to_pid`, and `audit_token_to_pidversion`. This fixture did not query peer identity |
| Imported design | `8384ca71d1ecc8ff590878fc4351954dbadd06d4` | `backend-validation-spikes.md`, `spiffe-mtls-authentication.md`, `supervisor-protection.md` in `research/imported/design-wiki-8384ca7/` |
| tmux | 3.7b | `mise exec -- tmux -V`. No tmux server was started |
| sbx | Not used | Outside host scope |
| M-001 queue protocol | Codex 0.157.1 source `a6bd19261c30ce0a0225fe90e646822d29916f11` | `app-server-protocol/src/protocol/v2/thread.rs`, `app-server/tests/suite/v2/thread_queue.rs`, and imported `agent-peering-tests/CODEX_PEERING.md` |
| M-001 Claude peer protocol | Claude Code 2.1.283 source `7779afb12e3635f46f56ec823979d68350ae000b` | Imported `agent-peering-tests/CLAUDE_CODE_PEERING.md` records the versioned NDJSON behavior. The dummy target does not enforce the real peer token or session rules |
| M-001 WebSocket and MCP | RFC 6455 and MCP 2025-11-25 | [WebSocket RFC](https://www.rfc-editor.org/rfc/rfc6455), [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#stdio) |

The Codex schema read comes from a source checkout. Runtime behavior of the selected profile remains unknown. The XNU revision is a source read and does not identify this Mac's booted kernel revision. The baseline did not load Claude settings, a Codex Unix-socket permission profile, or an operator control fixture. The effective settings of the current Codex worker session are unknown. This partial run used existing source checkouts. It didn't need a clone under `$TMPDIR`.
