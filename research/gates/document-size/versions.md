# Document size research versions

Read on 2026-09-26 America/New_York. The repository input is `d2add70d5ce58d89c188b7944f561ab9b30477b9`. The installed Codex CLI reports `0.157.1` through `mise exec -- codex --version`. The project plan records Claude Code `2.1.283`, Antigravity `agy` `1.2.11`, and the model inventory at this snapshot. These CLI versions and models were not re-probed through vendor token APIs.

| Source | Version or commit | Material read |
| --- | --- | --- |
| `openai/codex` local clone at `/Users/tony/Code/github.com/openai/codex` | `a6bd19261c30ce0a0225fe90e646822d29916f11` | `codex-rs/core/src/agents_md.rs:45-105`, `codex-rs/core/src/config/mod.rs:252`, `codex-rs/core/src/agents_md_tests.rs:666-740` |
| [Codex AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md) and [model guidance](https://developers.openai.com/api/docs/guides/latest-model) | Live documentation read 2026-09-26 | Hierarchical instructions and context guidance |
| [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol), [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra), [OpenAI token counting](https://developers.openai.com/api/docs/guides/token-counting) | Live documentation read 2026-09-26 | Model windows and `responses/input_tokens` method |
| [Claude Code memory](https://code.claude.com/docs/en/memory), [extension guidance](https://code.claude.com/docs/en/features-overview), [Claude models](https://platform.claude.com/docs/en/models/overview), [token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting) | Live documentation read 2026-09-26 | Loading, instruction length, Fable 5.1 and Sonnet 5 windows, count method |
| [Google Antigravity rules codelab](https://codelabs.developers.google.com/getting-started-agy-ide), [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash/), [token guide](https://ai.google.dev/gemini-api/docs/tokens) | Live documentation read 2026-09-26 | Rule locations, model input limit and token method |
| [Liu et al. 2024](https://aclanthology.org/2024.tacl-1.9/) | Published 2024 | Multi-document QA and key-value retrieval position experiments |
| [Nielsen 1997](https://www.nngroup.com/articles/how-users-read-on-the-web/) and [Morkes and Nielsen 1998](https://www.nngroup.com/articles/applying-writing-guidelines-web-pages/) | Published 1997 and 1998 | Web reading and concise, scannable writing studies |

Live vendor pages are not immutable snapshots. Recheck them when a model, harness, or endpoint changes. The Codex source commit is a pinned checkout, while the Claude Code and Antigravity loading claims rely on the cited live documentation and the repository's installed-version inventory.
