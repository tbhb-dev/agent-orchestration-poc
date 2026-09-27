# Versions and sources

The first disposable probe began at 2026-09-27T18:12:18Z. All commands ran in the `exp/214-detect-idle-turns` worktree at `cfb74707dd57c70288b250c739c480bad4258770` on macOS unless a row says otherwise. Captures and command outcomes are in [README.md](README.md) and [evidence](evidence/).

| Command | Observed result |
| --- | --- |
| `mise exec -- codex --version` | `codex-cli 0.157.1`, exit 0 |
| `mise exec -- claude --version` | `2.1.283 (Claude Code)`, exit 0 |
| `mise exec -- agy --version` | `1.2.11`, exit 0 |
| `mise exec -- tmux -V` | `tmux 3.7b`, exit 0 |
| `mise exec -- python --version` | `Python 3.14.6`, exit 0 |
| `mise --version` | `2026.8.6 macos-arm64`, exit 0 |
| `mise exec -- gitleaks version` | `8.30.1`, exit 0 |

The Codex source checkout was `/Users/tony/Code/github.com/openai/codex`. I read the installed version's `rust-v0.157.1` commit `36650394c5b38c2990ccf2a3457165ca3e9d9726` with `git show`, specifically `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`, `turn.rs`, `codex-rs/app-server/src/thread_status.rs`, `request_processors/thread_enrichment.rs`, and `codex-rs/app-server/README.md`. The checkout itself was at `a6bd19261c30ce0a0225fe90e646822d29916f11` and was read without modification. The tagged schema defines `idle`, `active`, `notLoaded`, `systemError`, and the approval and user-input active flags. The tagged status function derives those values from loaded state, pending requests, runtime activity, and system error.

Claude Code and agy are distributed here as installed CLIs without readable source checkouts for these internals. I read their installed `--help` output and the imported versioned research at `research/imported/agent-session-tests/CLAUDE_CODE_SESSION_MANAGEMENT.md`, `ANTIGRAVITY_SESSION_MANAGEMENT.md`, `research/imported/agent-peering-tests/CLAUDE_CODE_PEERING.md`, and `agy-peering-results.md`. Those imported observations predate this run and do not establish behavior at the installed versions. The current runtime captures below take precedence.

I also read issue #214 with its review comments, the linked #176 and #153 bodies and comments, PR #192, #196, #211, #213, and #216 bodies and available review history through REST, the local direction proposal, the local remote-trust note, and the project plan before writing the recommendation. The trust note cites the same Codex tagged source. PR #216 remained open when this experiment began and its trust-writing launcher path was not used.
