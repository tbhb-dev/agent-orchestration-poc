# Host runtime lifecycle versions

| Component | Version or revision | Evidence |
| --- | --- | --- |
| Host | macOS 26.5.1, Darwin arm64 | `sw_vers -productVersion`, `uname -sm` on 2026-09-28 |
| Python | 3.14.6 | `mise exec -- python3 --version` |
| tmux | 3.7b | `mise exec -- tmux -V`, installed `man tmux` sections for `-S`, `new-session`, `attach-session`, `capture-pane`, and `kill-server` |
| Codex CLI | 0.157.1 | `mise exec -- codex --version`, source checkout `openai/codex@a6bd19261c30ce0a0225fe90e646822d29916f11` |
| Claude Code | 2.1.283 | `mise exec -- claude --version`, source checkout `anthropics/claude-code@7779afb12e3635f46f56ec823979d68350ae000b` |
| Imported design wiki | `8384ca71d1ecc8ff590878fc4351954dbadd06d4` | Frozen source in `research/imported/design-wiki-8384ca7/`, merged through PR #232 |
| PoC checkout | `0169c84473855a92a40401c78fafb497022a7a0b` before changes | `git rev-parse HEAD` |

The tmux source checkout was unavailable under the writable roots. The installed tmux 3.7b manual supplied the versioned command reference. The Codex and Claude source checkouts were read only. No harness process ran in this probe.
