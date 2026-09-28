# Host runtime lifecycle versions

| Component | Version or revision | Evidence |
| --- | --- | --- |
| Host | macOS 26.5.1, Darwin arm64 | `sw_vers -productVersion`, `uname -sm` on 2026-09-28 |
| Python | 3.14.6 | `mise exec -- python3 --version` |
| tmux | 3.7b | `mise exec -- tmux -V`, installed `man tmux` sections for `-S`, `new-session`, `attach-session`, `capture-pane`, and `kill-server` |
| Codex CLI | 0.157.1 | `mise exec -- codex --version`, source checkout `openai/codex@a6bd19261c30ce0a0225fe90e646822d29916f11` |
| Claude Code | 2.1.283 during the stand-in report, 2.1.284 at fixture drafting | `mise exec -- claude --version` on 2026-09-28, source checkout `anthropics/claude-code@7779afb12e3635f46f56ec823979d68350ae000b` |
| Imported design wiki | `8384ca71d1ecc8ff590878fc4351954dbadd06d4` | Frozen source in `research/imported/design-wiki-8384ca7/`, merged through PR #232 |
| PoC checkout | `cb7fdd7811f09a8ae5864ff40b9bb01ba34889d9` before this fixture delivery | `git rev-parse HEAD` on branch `exp/243-harness-fixtures` |

The tmux source checkout was unavailable under the writable roots. The installed tmux 3.7b manual supplied the versioned command reference. The Codex and Claude source checkouts were read only. No harness process ran in this probe.

**Help-text.** `mise exec -- codex resume --help`, `mise exec -- codex exec resume --help`, and `mise exec -- claude --help` supplied the native resume argv in the runbook. **Documented.** The pinned Codex checkout's `codex-rs/exec/src/cli.rs` and `codex-rs/cli/src/main.rs` define explicit session-ID resume arguments. The pinned Claude checkout's `CHANGELOG.md` documents headless `-p --resume` behavior. The local Claude executable changed one patch release since the stage-two pin. No runtime compatibility is asserted for the new version.
