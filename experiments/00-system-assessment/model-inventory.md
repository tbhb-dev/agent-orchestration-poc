# Model inventory per coding harness

Inventory taken 2026-09-26 on this machine with read-only inspection followed by one tiny verification prompt per candidate model. Every finding is labeled VERIFIED (observed in this session) or NOT FOUND. No settings or config files were changed and no credential files were read.

## Claude Code 2.1.283 (`claude`)

Login reported by `claude auth status`: `authMethod: claude.ai`, `apiProvider: firstParty`, `subscriptionType: max`, org name `<redacted>`. VERIFIED.

### Models

| Model argument | Resolved model id (from `modelUsage`) | Display name | Default | Effort levels | VERIFIED by call |
| --- | --- | --- | --- | --- | --- |
| `fable` | `claude-fable-5-1` | Fable | Yes (`~/.claude/settings.json` sets `model: "fable"`) | low, medium, high, xhigh, max (`--effort`) | Yes |
| `claude-fable-5-1` | `claude-fable-5-1` | Fable | see above | same | Yes |
| `claude-fable-5-1[1m]` | `claude-fable-5-1` | Fable (1M context option from `additionalModelOptionsCache`) | No | same | Yes |
| `opus` | `claude-opus-5-5` | NOT FOUND (no display name in caches) | No | same | Yes |
| `claude-opus-5-5` | `claude-opus-5-5` | NOT FOUND | No | same | Yes |
| `sonnet` | `claude-sonnet-5` | NOT FOUND | No | same | Yes |
| `claude-sonnet-5` | `claude-sonnet-5` | NOT FOUND | No | same | Yes |
| `haiku` | `claude-haiku-4-5-20251001` | NOT FOUND | No | same | Yes |
| `claude-haiku-4-5-20251001` | `claude-haiku-4-5-20251001` | NOT FOUND | No | same | Yes |

All nine calls returned `is_error: False` and `result: 'ok'`. The `--effort` flag itself was not exercised by a call; its accepted values come from the help text and the settings file. The per-model effort levels are the harness-wide list, since the help text does not scope them per model.

### Raw evidence

`claude --help`, `--model` text (VERIFIED): `--model <model>  Model for the current session. Provide an alias for the latest model (e.g. 'fable', 'opus', or 'sonnet') or a model's full name (e.g. 'claude-fable-5').`

`claude --help`, `--effort` text (VERIFIED): `--effort <level>  Effort level for the current session (low, medium, high, xhigh, max)`

`claude --help` also lists `--fallback-model <model>  Enable automatic fallback to specified model(s) when the default model is ...` (VERIFIED, text truncated by the grep).

`~/.claude.json` cache values (VERIFIED): `modelAccessCache` is `[]`. `orgModelDefaultCache` is `null`. `additionalModelCostsCache` is `{}`. `additionalModelOptionsCache` is a one-item list: `{"value": "claude-fable-5-1[1m]", "label": "Fable", "description": "Fable 5.1 · Most capable for your hardest and longest-running tasks"}`.

`~/.claude/settings.json` (VERIFIED): `model: "fable"`, `effortLevel: "high"`, `modelSettings: {"claude-fable-5-1": {"effortLevel": "high"}}`.

Verification command per candidate: `claude -p --model <candidate> --no-session-persistence --max-turns 1 --output-format json 'Reply with exactly the word ok.'` with `CLAUDECODE` unset so the nested run was allowed. Observed `modelUsage` keys: `fable`, `claude-fable-5-1`, `claude-fable-5-1[1m]` all produced `['claude-fable-5-1']`; `opus`, `claude-opus-5-5` produced `['claude-opus-5-5']`; `sonnet`, `claude-sonnet-5` produced `['claude-sonnet-5']`; `haiku`, `claude-haiku-4-5-20251001` produced `['claude-haiku-4-5-20251001']`. Full log: `verify_claude.log` in this scratchpad directory.

## Codex CLI 0.157.1 (`codex`)

Login reported by `codex login status`: `Logged in using ChatGPT`. VERIFIED. The plan tier is not exposed by that command and was not read from credential files, so the ChatGPT plan is NOT FOUND.

### Models

Source of truth: the running app-server's `model/list` response (VERIFIED), cross-checked against `~/.codex/models_cache.json` (fetched `2026-09-26T18:05:21Z`, `client_version 0.157.1`).

| Model id | Display name | Default | Default effort | Supported reasoning efforts | Hidden | VERIFIED by call |
| --- | --- | --- | --- | --- | --- | --- |
| `gpt-6-astra` | GPT-6-Astra | Yes (`isDefault: true`) | medium | low, medium, high, xhigh, max, ultra | No | Yes |
| `gpt-6-sol` | GPT-6-Sol | No | medium | low, medium, high, xhigh, max, ultra | No | Yes |
| `gpt-6-luna` | GPT-6-Luna | No | medium | low, medium, high, xhigh, max | No | Yes |
| `gpt-5.6-sol` | GPT-5.6-Sol | No | low | low, medium, high, xhigh, max, ultra | No | Yes |
| `gpt-5.6-terra` | GPT-5.6-Terra | No | medium | low, medium, high, xhigh, max, ultra | No | Yes |
| `gpt-5.6-luna` | GPT-5.6-Luna | No | medium | low, medium, high, xhigh, max | No | Yes |
| `gpt-5.5` | GPT-5.5 (`upgrade: gpt-5.6-sol`) | No | medium | low, medium, high, xhigh | No | Yes |
| `gpt-reserve` | GPT-Reserve | No | medium | low, medium, high, xhigh, max | Yes (`visibility: hide`, cache only; absent from `model/list`) | Yes |
| `codex-auto-review` | Codex Auto Review | No | medium | low, medium, high, xhigh, max | Yes (`visibility: hide`, cache only; absent from `model/list`) | Yes |

Descriptions from `model/list`: GPT-6-Astra "Frontier intelligence for the most demanding work."; GPT-6-Sol "Workhorse model for coding and everyday work."; GPT-6-Luna "Fast and affordable model for easier tasks."; GPT-5.6-Sol "Older coding model for complex work."; GPT-5.6-Terra "Older balanced model for straightforward work."; GPT-5.6-Luna "Older fast and efficient model."; GPT-5.5 "Legacy coding model."

Effort descriptions (same across models): low "Fast responses with lighter reasoning"; medium "Balances speed and reasoning depth for everyday tasks"; high "Greater reasoning depth for complex problems"; xhigh "Extra high reasoning depth for complex problems"; max "Maximum reasoning depth for the hardest problems"; ultra "Maximum reasoning with automatic task delegation".

The `ultra` level is listed for `gpt-6-astra`, `gpt-6-sol`, `gpt-5.6-sol`, and `gpt-5.6-terra` only. The wire enum in the client also knows `none`, `minimal`, and `persistent`, but no model advertises them.

### Raw evidence

`codex --help` and `codex exec --help` (VERIFIED): `-m, --model <MODEL>  Model the agent should use`. Neither help text has a dedicated reasoning-effort flag. The generic override example reads: `Examples: - `-c model="o3"` - `-c 'sandbox_permissions=["disk-full-read-access"]'``. There is no `model_reasoning_effort` mention in either help text; it is reached through `-c`.

`ReasoningEffort` enum (VERIFIED): it is not in `codex-rs/protocol/src/config_types.rs` (that file only imports it at line 23 and uses it at lines 723 to 768). It lives in `~/Code/github.com/openai/codex/codex-rs/protocol/src/openai_models.rs` lines 59 to 72: `None, Minimal, Low, #[default] Medium, High, XHigh, Max, Ultra, Persistent, Custom(String)`. Serialization goes through `as_str()` at lines 76 to 89 with wire values `"none"`, `"minimal"`, `"low"`, `"medium"`, `"high"`, `"xhigh"`, `"max"`, `"ultra"`, `"persistent"`, and the custom string as is. `openai_models/reasoning_effort.rs` line 37 maps `Persistent` to the wire value `"disabled"` for the Responses API.

App-server query (VERIFIED): connected to `~/.codex/app-server-control/app-server-control.sock` via `websockets.sync.client.unix_connect` using the venv at `~/Code/github.com/tbhb/agent-session-tests/codex/.venv`. Sent `initialize` (id 1), `initialized`, and `model/list` with `{}` (id 2). `initialize` returned `userAgent: codex-tui/0.157.1 (Mac OS 26.5.1; arm64) Ghostty (model_inventory; 0.1)`, `codexHome: /Users/tony/.codex`. `model/list` with `{}` succeeded on the first try, so the `limit` fallback was not needed. Result keys were `data` and `nextCursor`; seven models were returned, all with `hidden: false`. Script: `model_list.py` in this scratchpad directory. No thread was started, resumed, or modified.

Models cache (VERIFIED): `~/.codex/models_cache.json` has keys `fetched_at`, `etag`, `client_version`, `identity`, `models`. Its nine entries match the table above; the two extra entries versus `model/list` are `gpt-reserve` and `codex-auto-review`, both `visibility: hide`.

Verification command per model: `codex exec --ephemeral -s read-only -m <id> -C <scratchpad> --skip-git-repo-check -o /dev/stdout 'Reply with exactly the word ok.'`. All nine exited 0 and the transcript on stderr showed `codex` replying `ok`. Stdout showed `okok` because `-o /dev/stdout` writes the final message a second time next to the normal final-message print. Run header for the plain run: `model: gpt-6-astra`, `provider: openai`, `approval: on-request`, `sandbox: read-only`, `reasoning effort: none`, `reasoning summaries: none`.

Effort override (VERIFIED): `codex exec ... -m gpt-6-astra -c 'model_reasoning_effort="high"' ...` exited 0, replied `ok`, and its header read `reasoning effort: high`. Without the override the header read `reasoning effort: none`, so the local config has no effort set and the server default applies. Full log: `verify_codex.log`.

## Antigravity agy 1.2.11 (`agy`)

Login: NOT FOUND. `agy` has no auth or status subcommand in its help, `agy models` prints no account line, and credential files were not read.

### Models

| Model id | Display name | Default | Effort levels | VERIFIED by call |
| --- | --- | --- | --- | --- |
| `gemini-3.8-flash-high` | Gemini 3.8 Flash (High) | NOT FOUND (list marks no default) | `--effort` low, medium, high, max; the id also carries its own high/medium/low tier | Yes |
| `gemini-3.8-flash-medium` | Gemini 3.8 Flash (Medium) | NOT FOUND | same | Yes |
| `gemini-3.8-flash-low` | Gemini 3.8 Flash (Low) | NOT FOUND | same | Yes |
| `gemini-3.7-flash-high` | Gemini 3.7 Flash (High) | NOT FOUND | same | Yes |
| `gemini-3.7-flash-medium` | Gemini 3.7 Flash (Medium) | NOT FOUND | same | Yes |
| `gemini-3.7-flash-low` | Gemini 3.7 Flash (Low) | NOT FOUND | same | Yes |
| `gemini-3.6-flash-high` | Gemini 3.6 Flash (High) | NOT FOUND | same | Yes |
| `gemini-3.6-flash-medium` | Gemini 3.6 Flash (Medium) | NOT FOUND | same | Yes |
| `gemini-3.6-flash-low` | Gemini 3.6 Flash (Low) | NOT FOUND | same | Yes |
| `gemini-3.1-pro-high` | Gemini 3.1 Pro (High) | NOT FOUND | same | Yes (also with `--effort high`) |
| `gemini-3.1-pro-low` | Gemini 3.1 Pro (Low) | NOT FOUND | same | Yes |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 (Thinking) | NOT FOUND | same | Yes |
| `claude-opus-4-6-thinking` | Claude Opus 4.6 (Thinking) | NOT FOUND | same | Yes |
| `gpt-oss-120b-medium` | GPT-OSS 120B (Medium) | NOT FOUND | same | Yes |

Antigravity encodes a reasoning tier inside most model ids (the `-high`, `-medium`, `-low` suffix) and separately exposes a session-wide `--effort` flag. How the two interact is NOT FOUND; only acceptance of `--effort high` was verified.

### Raw evidence

`agy --help` (VERIFIED): `--effort  Reasoning effort for the current CLI session (low|medium|high|max)` and `--model  Model for the current CLI session`. The subcommand list includes `models  List available models`.

`agy models` output in full (VERIFIED):

```
Fetching available models...
gemini-3.8-flash-high	Gemini 3.8 Flash (High)
gemini-3.8-flash-medium	Gemini 3.8 Flash (Medium)
gemini-3.8-flash-low	Gemini 3.8 Flash (Low)
gemini-3.7-flash-high	Gemini 3.7 Flash (High)
gemini-3.7-flash-medium	Gemini 3.7 Flash (Medium)
gemini-3.7-flash-low	Gemini 3.7 Flash (Low)
gemini-3.6-flash-high	Gemini 3.6 Flash (High)
gemini-3.6-flash-medium	Gemini 3.6 Flash (Medium)
gemini-3.6-flash-low	Gemini 3.6 Flash (Low)
gemini-3.1-pro-high	Gemini 3.1 Pro (High)
gemini-3.1-pro-low	Gemini 3.1 Pro (Low)
claude-sonnet-4-6	Claude Sonnet 4.6 (Thinking)
claude-opus-4-6-thinking	Claude Opus 4.6 (Thinking)
gpt-oss-120b-medium	GPT-OSS 120B (Medium)
```

Command syntax note (VERIFIED): the form `agy --print --model <id> ... 'prompt'` fails with `Error: --print took "--model" as its prompt, so the intended prompt was left as an argument and ignored. Attach the prompt to the flag (--print='your prompt') and move --model elsewhere on the command line.` The `--print` flag takes the prompt as its value.

Verification command per model: `agy --model <id> --new-project --print-timeout 90s --print='Reply with exactly the word ok.'` from the scratchpad directory. All fourteen exited 0 and printed `ok` on stdout (`gemini-3.1-pro-low` printed `ok.`) with empty stderr. The output does not echo a model name, so the model actually used is inferred from the accepted `--model` argument only. The extra run `agy --model gemini-3.1-pro-high --effort high --new-project --print-timeout 90s --print='...'` exited 0 and printed `ok`, so `--effort high` is accepted. Full log: `verify_agy.log`.

## Scratchpad files

All under `/private/tmp/claude-501/-Users-tony-Code-github-com-tbhb-agent-orchestration-poc/0b1b7917-950a-4135-8c89-7951a84c8690/scratchpad/`: `model_list.py` (app-server query), `verify_claude.sh` and `verify_claude.log`, `verify_codex.sh` and `verify_codex.log` plus per-model `codex_<id>.out` and `.err`, `verify_agy.sh` and `verify_agy.log` plus per-model `agy_<id>.out` and `.err`.
