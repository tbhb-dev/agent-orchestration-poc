# Current models behind three coding harnesses

Researched 2026-09-26 from vendor pages fetched live. Every fact carries a source label: [vendor-docs] for reference documentation and model cards, [vendor-announcement] for vendor blog or launch posts, [third-party] for press or community reporting. Where a page could not be fetched or was ambiguous, the "what could not be found" list at the end of each section says so.

## 1. Claude Code (Anthropic), Claude Max plan

### Summary table

| Model | Model id | Released | Purpose (vendor wording) | Context / max output | Effort levels (Claude Code) | Source |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Fable 5.1 | `claude-fable-5-1` | 2026-09-01 | "For demanding reasoning and long-horizon agentic work" | 1M / 128K | `low`, `medium`, `high` (default), `xhigh`, `max`; adaptive thinking always on | [vendor-docs] <https://platform.claude.com/docs/en/models/fable-5-1/overview> |
| Claude Opus 5.5 | `claude-opus-5-5` | 2026-09-22 | "For long-running agentic coding and knowledge work" | 1M / 128K | `low`, `medium` (default), `high`, `xhigh`, `max`; adaptive thinking always on | [vendor-docs] <https://platform.claude.com/docs/en/models/opus-5-5/overview> |
| Claude Sonnet 5 | `claude-sonnet-5` | 2026-06-30 | "The best combination of speed and intelligence" | 1M / 128K | `low`, `medium`, `high` (default), `xhigh`, `max`; adaptive thinking on by default | [vendor-docs] <https://platform.claude.com/docs/en/models/sonnet-5/overview> |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` (alias `claude-haiku-4-5`) | 2025-10-15 | "The fastest model with near-frontier intelligence" | 200K / 64K | Effort not supported; manual extended thinking with `budget_tokens` | [vendor-docs] <https://platform.claude.com/docs/en/models/haiku-4-5/overview> |

### Lineup and specifications

The models overview page (fetched 2026-09-26, no last-updated date shown) lists exactly these four as the current lineup, with Claude Fable 5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Opus 4.5, Sonnet 4.6, and Sonnet 4.5 as legacy models still available. [vendor-docs] <https://platform.claude.com/docs/en/models/overview>

Pricing per million tokens from the same page: Fable 5.1 $10 in / $50 out; Opus 5.5 $4 / $20; Sonnet 5 $2 / $10; Haiku 4.5 $1 / $5. Cache reads are 10% of input price except 2.5% on Fable 5.1 and Mythos 5.1 ($0.25) and 5% on Opus 5.5 ($0.20). [vendor-docs] <https://platform.claude.com/docs/en/models/overview>

Knowledge cutoffs: Fable 5.1 and Opus 5.5 reliable through June 2026; Sonnet 5 January 2026; Haiku 4.5 February 2025 (training data July 2025). Retirement not sooner than 2027-09-01 (Fable 5.1), 2027-09-22 (Opus 5.5), 2027-06-30 (Sonnet 5), 2026-10-15 (Haiku 4.5). [vendor-docs] <https://platform.claude.com/docs/en/models/overview>

Every current model id is a pinned snapshot; the dateless ids from the 4.6 generation on have no separate dated form. [vendor-docs] <https://platform.claude.com/docs/en/models/overview>

The overview's opening recommendation: "start with Claude Opus 5.5 for most workloads. Use Claude Fable 5.1 for demanding reasoning and long-horizon agentic work, or when your evals on Claude Opus 5.5 at higher effort still fall short." [vendor-docs] <https://platform.claude.com/docs/en/models/overview>

Opus 5.5 announcement (2026-09-22): 40% lower cost than Opus 5 on typical workloads, more than 30% faster output, "Five-hour usage limits increased on Pro, Max, Team, and seat-based Enterprise plans," subscription users receive a saveable rate-limit reset, and "Claude Sonnet 5.5 and Claude Haiku 5.5 will follow in the coming weeks." Fast mode pricing is $8 / $40. [vendor-announcement] <https://www.anthropic.com/claude-opus-5-5>

Opus 5.5 breaking changes relevant to harnesses: thinking cannot be disabled (a request with `thinking: {"type": "disabled"}` returns 400), forced tool use returns an error, thinking blocks are bound to the model and conversation, and text between tool calls now arrives in `thinking` blocks that are empty at the default `display` setting. The first three also apply to Fable 5.1. [vendor-docs] <https://platform.claude.com/docs/en/models/opus-5-5/overview>

Sonnet 5 announcement (2026-06-30): "built to be the most agentic Sonnet model yet," permanent pricing $2 / $10 as of 2026-08-10, default model on Free and Pro, available on Max. [vendor-announcement] <https://www.anthropic.com/news/claude-sonnet-5>

Haiku 4.5 announcement (2025-10-15) describes it for "real-time, low-latency" uses including pair programming and agentic coding, and gives the pattern where a larger model can "orchestrate a team of multiple Haiku 4.5s to complete subtasks in parallel." [vendor-announcement] <https://www.anthropic.com/news/claude-haiku-4-5>

### Fable 5.1 versus Mythos 5.1

The Fable product page states that Fable 5.1 was announced 2026-09-01 as "Our most capable model for coding and knowledge work," that it is "a Mythos-level model," and that because of advanced cyber and biology capability "many queries in these domains are automatically routed to less capable models if flagged by these safeguards." Flagged cybersecurity queries route to Opus 4.8 and flagged biology queries route to Opus 5, and rerouted requests are not charged at Fable pricing. [vendor-announcement] <https://www.anthropic.com/claude/fable>

The launch post says the two releases "are configurations of the same underlying model with different levels of safeguards," Fable 5.1 is generally available while Mythos 5.1 is restricted to trusted access programs for cybersecurity and life sciences work, and Fable 5.1 has "improved safeguards to reduce false positives." Cache reads dropped 75% to $0.25. [vendor-announcement] <https://www.anthropic.com/claude-fable-and-mythos-5-1>

The Mythos 5.1 model page confirms model id `claude-mythos-5-1`, released 2026-09-01, "Invite only," "the same model as Claude Fable 5.1, offered by invitation only through Project Glasswing," sharing Fable 5.1's specifications and pricing (1M context, 128K output, $10 / $50, default effort `high`). Note that Mythos 5.1 is not listed on the Claude Platform on AWS. [vendor-docs] <https://platform.claude.com/docs/en/models/mythos-5-1/overview>

The choosing-a-model page repeats: Fable 5.1 "is Anthropic's most capable model open to all customers" and Mythos 5.1 "offers the same capabilities to Project Glasswing participants only." [vendor-docs] <https://platform.claude.com/docs/en/about-claude/models/choosing-a-model>

The Opus 5.5 prompting guide notes that Opus 5.5's biology safeguards "are the same as Claude Fable 5.1's" and that in cybersecurity "Finding vulnerabilities in source code is allowed. High-risk dual-use cybersecurity activities are not." [vendor-docs] <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5>

### Effort and thinking in Claude Code

The Claude Code `--effort` flag accepts `low`, `medium`, `high`, `xhigh`, `max`, or `ultracode`; available levels depend on the model; `ultracode` "requests `xhigh` effort with ultracode turned on, and requires Claude Code v2.1.203 or later"; the flag overrides the `modelSettings` and `effortLevel` settings for the session and does not persist. [vendor-docs] <https://code.claude.com/docs/en/cli-reference>

Per the model configuration page, Fable 5.1, Fable 5, Opus 5.5, Opus 5, Sonnet 5, Opus 4.8, and Opus 4.7 support `low`, `medium`, `high`, `xhigh`, `max`; Opus 4.6 and Sonnet 4.6 support `low`, `medium`, `high`, `max`; other models do not support effort. Default effort is `medium` on Opus 5.5, `xhigh` on Opus 4.7, and `high` on every other model that supports effort. [vendor-docs] <https://code.claude.com/docs/en/model-config>

The same page's effort table, quoted: `low` "Reserve for short, scoped, latency-sensitive tasks that are not intelligence-sensitive"; `medium` "Reduces token usage for cost-sensitive work that can trade off some intelligence. The default on Opus 5.5"; `high` "Balances token usage and intelligence. The default on every model except Opus 5.5 and Opus 4.7"; `xhigh` "Deeper reasoning at higher token spend. The default on Opus 4.7"; `max` "Can improve performance on demanding tasks but may show diminishing returns and is prone to overthinking. Test before adopting broadly"; `ultracode` "A Claude Code setting that plans a dynamic workflow for each substantive task with `xhigh` per-message reasoning." [vendor-docs] <https://code.claude.com/docs/en/model-config>

Settings: `effortLevel` sets "a default effort level for models without a saved level of their own"; `modelSettings` keeps "a saved effort level per model, or cap one model's effort" (shape `{"modelSettings": {"claude-opus-5-5": {"effort": "medium"}}}`); `CLAUDE_CODE_EFFORT_LEVEL` is the environment form; `/effort` and the `/model` picker slider set it interactively; skill and subagent frontmatter accept `effort:`. [vendor-docs] <https://code.claude.com/docs/en/settings-reference> and <https://code.claude.com/docs/en/model-config>

Thinking cannot be turned off on Opus 5.5, Fable 5.1, or Fable 5; on those models effort is the primary control. `MAX_THINKING_TOKENS=0` disables thinking on other Anthropic API models. [vendor-docs] <https://code.claude.com/docs/en/model-config> and <https://code.claude.com/docs/en/costs>

Fable 5.1, Fable 5, Sonnet 5, and Opus 4.7 and later have a native 1M window in Claude Code on the Anthropic API with auto-compaction at about 967K by default; `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` reverts to 200K. [vendor-docs] <https://code.claude.com/docs/en/model-config>

Ultracode: "Ultracode is a Claude Code setting rather than a model effort level: it sends `xhigh` to the model and additionally has Claude orchestrate dynamic workflows for substantive tasks." On a subscription "a session with ultracode on reaches a session or weekly limit sooner than the same work at `high`." [vendor-docs] <https://code.claude.com/docs/en/model-config> and <https://code.claude.com/docs/en/workflows>

Version requirements in Claude Code: Opus 5.5 needs v2.1.280 or later, Sonnet 5 v2.1.197 or later, Fable 5.1 v2.1.257 or later per the model config page; the Fable support article says Fable 5.1 needs v2.1.255 or later. [vendor-docs] <https://code.claude.com/docs/en/model-config> and <https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan>

### Max plan defaults and usage notes

Default model on the Max plan in Claude Code is Opus 5.5. The `opus` alias resolves to Opus 5.5 and `sonnet` to Sonnet 5 on the Anthropic API. Fable models "require explicit selection; never account default." The `best` alias picks Fable when available, else Opus. [vendor-docs] <https://code.claude.com/docs/en/model-config>

Fable on Max: "Fable 5 and Fable 5.1 are included as a standard part of your plan," "You can use up to 50% of your weekly usage limits on Fable models at no extra cost," they "draw from your plan's regular weekly usage limits and use them faster than other Claude models," and past the Fable limit you can continue with usage credits or switch models. Article shows "Updated over 3 weeks ago" as of 2026-09-26. [vendor-docs] <https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan>

Max tiers: Max 5x is $100 per month with "five times the Pro plan's per-session usage allowance," Max 20x is $200 per month with 20 times; "Your session-based usage limit will reset every five hours"; weekly limits apply across all models and reset at a fixed weekly time per account. Article shows "Updated this week." [vendor-docs] <https://support.claude.com/en/articles/11049741-what-is-the-max-plan>

Claude Code usage on Pro and Max "counts toward the same usage limits shared across Claude and Claude Code" (article dated 2026-08-19). No numeric message or token caps are published. [vendor-docs] <https://support.claude.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan>

On usage-limit messages: session and weekly limits are "shared across all models, so the developer can't restore access by switching models," whereas after a model-specific message such as "You've hit your Opus limit," switching family does keep working. [vendor-docs] <https://code.claude.com/docs/en/costs>

### Guidance on lead versus subagent models

Subagent `model` frontmatter accepts `sonnet`, `opus`, `haiku`, `fable`, a full id, or `inherit`. Resolution order: per-invocation parameter, frontmatter, `CLAUDE_CODE_SUBAGENT_MODEL`, then the main conversation's model. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` (v2.1.257+) applies one model to every subagent, teammate, and workflow agent. Setting only the default variable "doesn't change the model the built-in Explore and Plan subagents run on." Explore inherits the main model capped at Opus; Plan inherits; general-purpose uses `CLAUDE_CODE_SUBAGENT_MODEL` if set. Subagents inherit the main conversation's thinking configuration (v2.1.198+). [vendor-docs] <https://code.claude.com/docs/en/sub-agents>

The costs page: "Sonnet handles most coding tasks well and costs less than Opus. Reserve Opus for complex architectural decisions or multi-step reasoning." "For simple subagent tasks, specify `model: haiku` in your subagent configuration." "The subagent's own requests still draw on your usage. To spend less on them, choose a smaller model for a subagent or run every subagent on one model." For agent teams: "Use Sonnet for teammates. It balances capability and cost for coordination tasks." [vendor-docs] <https://code.claude.com/docs/en/costs>

Agent teams: teammates inherit the lead's effort level; a teammate's model is fixed at spawn; model chosen from the spawn prompt, then the subagent definition, then `CLAUDE_CODE_SUBAGENT_MODEL`, then the lead's model. Agent teams remain experimental behind `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. [vendor-docs] <https://code.claude.com/docs/en/agent-teams>

The API effort page marks `low` as suited to "Simpler tasks that need the best speed and lowest costs, such as subagents" and `xhigh` to "Long-running agentic and coding tasks (over 30 minutes) with token budgets in the millions." [vendor-docs] <https://platform.claude.com/docs/en/build-with-claude/effort>

The cost and intelligence page documents two multi-model patterns with measurements: an orchestrator ("a Claude Fable 5.1 lead over 25 Claude Sonnet 5 workers" cost 47% to 55% less than the frontier model alone on a 21.6M-token corpus benchmark while scoring 10 to 12 points lower) and an advisor (a Claude Opus 5.5 executor at `high` with a Fable 5.1 advisor scored 90.1% at $2.92 per attempt, 1.7 points over Opus 5.5 alone for about 2.1 times the cost). It warns: "If the work is one chain, fits in one context without a long cost tail, or a single model at lower effort already meets your bar, don't build an orchestrator," and that an executor at low effort "can stop detecting that it is stuck." [vendor-docs] <https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence>

The Fable 5.1 prompting guide adds harness advice for leads: "If your coding agent lets Claude Fable 5.1 delegate work to subagents, don't force the lead agent to stop and wait for each one," because letting the lead continue "lowers average time to completion at similar quality, token usage, and cost." [vendor-docs] <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1>

The Opus 5.5 prompting guide describes "Time signals for multiagent harnesses": appending elapsed time against a budget (for example `elapsed 340s / 1200s`) made small agent teams finish sooner at comparable quality. [vendor-docs] <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5>

Anthropic's blog post "Choosing a Claude model and effort level in Claude Code" (2026-07-07) says "for most tasks you should use the model's default effort level," to "Pick a higher effort level if Claude got it wrong by skipping a file, not running the tests, or not double-checking its work," to pick a larger model when "Claude has all the pertinent context and clearly tried and still got it wrong," and that "dropping to the smaller model for routine stretches saves real money at no quality cost." It predates Opus 5.5 and Fable 5.1. [vendor-announcement] <https://claude.com/blog/claude-model-and-effort-level-in-claude-code>

### Guidance on effort level for coding agents

Per model, from the effort page: Fable 5.1 "Start with `high`, the default. Step up to `xhigh` or `max` for the most capability-sensitive agentic and coding work, and step down to `medium` or `low` for routine or latency-sensitive work once your evals show quality holds." Opus 5.5: `medium` is the default, "effort is the primary control for how much the model reasons and what a request costs. Run an effort sweep on your own evals rather than carrying settings over from an earlier model." Sonnet 5: `high` default "for complex reasoning, coding, and agentic tasks," `xhigh` "For the hardest coding and agentic tasks," `medium` "Comparable to Claude Sonnet 4.6 at high effort." [vendor-docs] <https://platform.claude.com/docs/en/build-with-claude/effort>

Fable 5.1 prompting: "At `medium`, results roughly match Claude Fable 5 at lower cost," and "At `low`, Claude Fable 5.1 is often competitive with Claude Opus and Claude Sonnet models on cost per task while scoring higher, so include it in the comparison wherever you'd otherwise run a smaller model at a higher effort level." At `low` it "is less likely than Claude Fable 5 to call a search or retrieval tool." [vendor-docs] <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1>

Opus 5.5 prompting: "at its default `medium` effort the model matched or beat Claude Opus 5 at `high` effort" on repository tasks, "on several coding evaluations `low` comes close to it at much lower cost," "Reserve `xhigh` and `max` for work where you've measured a quality gain," and a `max_tokens` of 128,000 "has worked well" for long agentic coding turns. [vendor-docs] <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5>

Choosing-a-model page: "Tuning effort is often a better lever than switching models." On Opus 4.8 and 4.7 (legacy), `xhigh` "is the best setting for most coding and agentic use cases." [vendor-docs] <https://platform.claude.com/docs/en/about-claude/models/choosing-a-model>

Claude Code costs page: "For simpler tasks where deep reasoning isn't needed, you can reduce costs by lowering the effort level with `/effort` or in `/model`." Plan mode is recommended "for complex tasks" before implementation. [vendor-docs] <https://code.claude.com/docs/en/costs>

No Anthropic page found says literally "use high for planning and medium for routine edits." The closest published guidance is the per-model default plus sweep advice above and the `low` for subagents note.

### What could not be found (Anthropic)

- The Fable 5.1 and Mythos 5.1 system card PDF exceeded the fetch size limit, so the exact system-card wording on shared weights was not read directly. The relationship is taken from the launch post, the Fable product page, and the Mythos 5.1 model page instead.
- No published numeric Max-plan token or message limits for Opus 5.5 or Sonnet 5 in Claude Code; Anthropic publishes only multipliers (5x, 20x), the five-hour and weekly windows, and the 50% Fable weekly cap.
- The Claude Code settings reference fetch returned only setting descriptions, not the enumerated `effortLevel` values; the values come from the CLI reference and model config pages.
- No vendor page states which effort level is used by default for subagents beyond "subagents inherit the main conversation's thinking configuration" and per-definition `effort:` frontmatter.

## 2. Codex CLI (OpenAI), ChatGPT Pro plan

### Summary table

| Model | Model id | Released | Purpose (vendor wording) | Context / max output (API) | Reasoning effort | Source |
| --- | --- | --- | --- | --- | --- | --- |
| GPT-6 Astra | `gpt-6-astra` | 2026-09-03 (system card date; staged rollout) | "Our most capable model, built for the hardest end-to-end work" | 1,050,000 / 128,000 | API: `low`, `medium` (default), `high`, `xhigh`, `max`; `none` rejected. Codex: Light, Medium, High, Extra High, Max, Ultra | [vendor-docs] <https://developers.openai.com/api/docs/models/gpt-6-astra> and <https://learn.chatgpt.com/docs/models> |
| GPT-6 Sol | `gpt-6-sol` | 2026-09-22 | "Built for complex coding and agentic workflows" | 1,050,000 / 128,000 | API: `none`, `low`, `medium` (default), `high`, `xhigh`, `max`. Codex: Light, Medium, High, Extra High, Max, Ultra | [vendor-docs] <https://developers.openai.com/api/docs/models/gpt-6-sol> and <https://learn.chatgpt.com/docs/models> |
| GPT-6 Luna | `gpt-6-luna` | 2026-09-22 | "Our most efficient model for focused, high-volume tasks" | 1,050,000 / 128,000 | API: `none`, `low`, `medium` (default), `high`, `xhigh`, `max`. Codex: Light, Medium, High, Extra High, Max | [vendor-docs] <https://developers.openai.com/api/docs/models/gpt-6-luna> and <https://learn.chatgpt.com/docs/models> |

### Models and specifications

API model page for `gpt-6-astra`: context window 1,050,000 tokens, max input 922,000, max output 128,000, knowledge cutoff 2026-04-30, reasoning effort `low`, `medium`, `high`, `xhigh`, `max`, pricing $10 in / $50 out with $1 cached input, and prompts over 272K input tokens billed at 2x input and 1.5x output. [vendor-docs] <https://developers.openai.com/api/docs/models/gpt-6-astra>

API model page for `gpt-6-sol`: same 1,050,000 / 128,000 limits, knowledge cutoff 2026-04-20, effort `none`, `low`, `medium` (default), `high`, `xhigh`, `max`, pricing $2 / $10, fast mode doubles applicable rates. [vendor-docs] <https://developers.openai.com/api/docs/models/gpt-6-sol>

API model page for `gpt-6-luna`: 1,050,000 context, 922,000 max input, 128,000 output, knowledge cutoff 2026-05-18, effort `none`, `low`, `medium` (default), `high`, `xhigh`, `max`, pricing $0.10 / $0.50. [vendor-docs] <https://developers.openai.com/api/docs/models/gpt-6-luna>

The API reasoning guide lists the full effort enumeration as `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, warns "Some models support only a subset of these values," and states "GPT-6 Astra does not support `none` reasoning effort. Setting `reasoning.effort` (Responses) or `reasoning_effort` (Chat Completions) to `none` returns HTTP 400." GPT-5.6 and GPT-6 default to `medium`. [vendor-docs] <https://developers.openai.com/api/docs/guides/reasoning>

The model guidance page: Astra is "our most intelligent model yet, with state-of-the-art performance in computer use, browsing, software engineering, science, and professional work"; Sol for "strong reasoning on demanding tasks"; Luna for "efficient, repeatable work at scale"; when migrating "If your existing request uses `minimal`, start with `low` and compare results." [vendor-docs] <https://developers.openai.com/api/docs/guides/latest-model>

GPT-6 Astra system card is dated 2026-09-03 and classifies cybersecurity at the Critical threshold; it discusses a deployment simulation across "54,218 internal Codex tasks." An appendix covering GPT-6 Sol and GPT-6 Luna was added 2026-09-22. [vendor-docs] <https://deploymentsafety.openai.com/gpt-6-astra> and <https://deploymentsafety.openai.com/gpt-6-astra/sec:appendix-sol-luna>

Astra release timing from press: released to approved users on 2026-09-03 with broader availability the following day, and rolled out to "ChatGPT Plus, Pro, Business, and Enterprise 'over the coming days'." [third-party] <https://www.cnbc.com/2026/09/03/open-ai-astra-gpt-6-cyber.html> and <https://9to5mac.com/2026/09/04/openai-releasing-major-upgrade-to-chatgpt-and-codex-with-gpt-6-astra-details-here/>

Sol and Luna availability from press (2026-09-22): "Both models are available in ChatGPT Work and Codex for Plus, Pro, Business, Enterprise, and Edu users," both "cost 50% less" than their GPT-5.6 predecessors, and the primary source is <https://openai.com/index/introducing-gpt-6-sol-and-luna/> (which returned HTTP 403 to this fetch). [third-party] <https://9to5mac.com/2026/09/22/openai-upgrading-chatgpt-and-codex-with-two-more-gpt-6-models/>

### Codex model catalog and effort names

The Codex models page names the effort levels Light, Medium, High, Extra High, Max, and Ultra; Luna is listed without Ultra. It says "Light in the ChatGPT desktop app, ChatGPT Work on the web, and IDE extension, or Low in the CLI, suits quick, well-scoped tasks." "Ultra uses subagents to handle separate parts of a complex task in parallel." Recommendation: "Start with Medium for Sol, High for Luna, or Light for Astra. Increase the effort for tasks that need more planning, analysis, or checking." Model choice: "Choose Astra when a task needs the strongest capability across multiple steps and tools. Sol suits everyday work and complex coding, and Luna suits clear, repeatable tasks." Astra and Luna are listed for desktop, web, CLI, IDE, and API but not Codex cloud. GPT-5.5 retires 2026-10-14; GPT-5.4 and GPT-5.4 Mini retired 2026-08-31 (replaced by Sol and Luna). [vendor-docs] <https://learn.chatgpt.com/docs/models>

Codex config reference: `model` "Model to use (e.g., `gpt-6-sol`)"; `model_reasoning_effort` "Reasoning effort advertised by the selected model, such as `low`, `medium`, `high`, `xhigh`, `max`, or `ultra`"; `model_reasoning_summary` is `auto | concise | detailed | none`; `service_tier` "Preferred service tier for new turns. Use `fast` or another tier advertised by the active model"; `features.fast_mode` enables Fast-tier commands in the TUI and is "stable; on by default"; `model_context_window` is "Context window tokens available to the active model." [vendor-docs] <https://learn.chatgpt.com/docs/config-file/config-reference>

Fast mode: "Codex offers the ability to increase the speed of the model for increased credit consumption." Supported on GPT-6 Astra, Sol, and Luna plus GPT-5.6, 5.5, and 5.4; GPT-6 models bill at 2.5x the Standard credit rate; enable with `/fast on` or `service_tier = "fast"` in `config.toml`. [vendor-docs] <https://learn.chatgpt.com/docs/agent-configuration/speed>

No "mini" variant exists in the GPT-6 series; Luna is the small model and GPT-5.4 Mini "Replaced by Luna." [vendor-docs] <https://learn.chatgpt.com/docs/models>

### Codex CLI 0.157

Codex CLI 0.157.0 released 2026-09-25 and 0.157.1 on 2026-09-26 per the vendor changelog; the changelog attributes the GPT-6 Sol and Luna catalog additions to 0.156.0 and 0.156.1 (2026-09-22 and 2026-09-23), while the GitHub release notes for 0.157.0 also list "Added GPT-6 Sol and Luna, including Amazon Bedrock support and migration prompts for older models." [vendor-docs] <https://learn.chatgpt.com/docs/changelog> and <https://github.com/openai/codex/releases/tag/rust-v0.157.0>

The GitHub 0.157.0 notes also say GPT-5.6-Sol "received priority updates and the ultrafast service tier was removed for this model." [vendor-docs] <https://github.com/openai/codex/releases/tag/rust-v0.157.0>

### Pro plan usage

Codex pricing page: Pro "offers 5x or 20x higher rate limits than Plus" (Pro $100 and Pro $200), with estimated local messages per five-hour period of "5-45" to "100-900" for GPT-6 Astra, "15-150" to "300-3,000" for GPT-6 Sol, and "350-3,000" to "7,000-56,000" for GPT-6 Luna, and "Weekly limits may also apply." Credits: Luna 2.5 credits and Astra 250 credits per million input tokens at standard speed; "Fast mode uses 2.5x the Standard credit rate." [vendor-docs] <https://learn.chatgpt.com/docs/pricing>

Help center (search snippets only; the pages returned HTTP 403): "Pro $100 and Pro $200 plans and Business Premium seats can use their full existing allowance for Astra," "Astra can use your allowance faster than GPT-5.6 Sol," limits "may apply over a five-hour window and a weekly window," and "GPT-6 Pro in Chat is powered by Astra, but Chat has its own model availability and message limits. Work and Codex share a separate usage allowance." [vendor-docs] <https://help.openai.com/en/articles/20001516-managing-usage-with-gt-6-astra-in-work-and-codex> and <https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan>

Plus and Pro users can buy an instant weekly reset or credits. [vendor-docs] <https://help.openai.com/en/articles/20001507-paid-weekly-work-and-codex-rate-limit-resets>

### Guidance on effort level for coding agents

Codex best practices: "Light for GPT-6 Astra (`low` in configuration)" for routine edits; "Medium for GPT-6 Sol, High for GPT-6 Luna" as starting points; "Extra High for long, agentic, reasoning-heavy tasks"; "Low for faster, well-scoped tasks"; "Medium or High for more complex changes or debugging"; and use Plan mode (`/plan`) so Codex can "gather context, ask clarifying questions, and build a stronger plan before implementation." [vendor-docs] <https://learn.chatgpt.com/guides/best-practices>

API reasoning guide: `low` "ideal for use cases requiring tool-use, planning, search, or multi-step decision making, while optimizing for speed and cost"; `high` for "complex workflows and agentic tasks" where "quality and intelligence matters more than latency"; `xhigh` for "asynchronous workflows and agentic tasks that require long runs." [vendor-docs] <https://developers.openai.com/api/docs/guides/reasoning>

The models page's "Start with the default effort and increase it when the task needs deeper planning or analysis" is the closest OpenAI statement to a planning-versus-edits rule. [vendor-docs] <https://learn.chatgpt.com/docs/models>

### What could not be found (OpenAI)

- Which model Codex CLI 0.157 selects by default on a Pro account. The models page does not state a default and says "Availability depends on the rollout, your sign-in method, and your client." The operator's local report of `gpt-6-astra` as default is not contradicted by any vendor page, but is not confirmed by one either.
- The context window Codex CLI uses in ChatGPT-signed-in mode; only the API page's 1,050,000 figure is published, and Codex exposes `model_context_window` as a per-model advertised value.
- The exact Codex catalog mapping of Ultra to an API value; the config reference lists `ultra` as an accepted `model_reasoning_effort` value but the API reasoning guide does not list it.
- The `openai.com/index` launch posts for Astra and for Sol and Luna returned HTTP 403, as did every help.openai.com article; those facts rest on system-card dates, learn.chatgpt.com pages, and search snippets.
- Whether the GPT-6 Sol and Luna release notes belong to 0.156.0 or 0.157.0; the two vendor sources disagree as noted above.
- The GitHub release page fetch rendered the release year ambiguously; the date 2026-09-25 is taken from the vendor changelog.

## 3. Antigravity `agy` (Google), Google AI Ultra plan

### Summary table

| Model | Model id (API) | `agy models` ids | Released | Purpose (vendor wording) | Context / max output | Effort (thinking level) | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` (still Preview) | `gemini-3.1-pro-high`, `gemini-3.1-pro-low` | 2026-02-19 | "Advanced intelligence, complex problem-solving skills, and powerful agentic and vibe coding capabilities" | 1,048,576 / 65,536 | Antigravity: Low, High. API: `low`, `medium`, `high` (default `high`) | [vendor-docs] <https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview> and <https://antigravity.google/docs/models/> |
| Gemini 3.8 Flash | `gemini-3.8-flash` (Stable) | `gemini-3.8-flash-high`, `-medium`, `-low` | 2026-09-02 | "Our most intelligent Flash model, engineered for long-horizon software engineering, autonomous agents, and complex enterprise workflows" | 1,048,576 / 65,536 | Low, Medium, High (API default `medium`; `minimal` rejected) | [vendor-docs] <https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash> and <https://deepmind.google/models/model-cards/gemini-3-8-flash/> |
| Gemini 3.7 Flash, 3.6 Flash | `gemini-3.7-flash`, `gemini-3.6-flash` | `gemini-3.7-flash-*`, `gemini-3.6-flash-*` | not researched | Previous Flash generations still offered in Antigravity | not researched | Low, Medium, High | [vendor-docs] <https://antigravity.google/docs/models/> |

### Models and specifications

The Antigravity models page lists the reasoning models as Gemini 3.8 Flash, Gemini 3.7 Flash, Gemini 3.6 Flash, and Gemini 3.1 Pro, plus third-party Claude Sonnet 4.6 (thinking), Claude Opus 4.6 (thinking), and GPT-OSS-120b. Thinking levels shown are "Low, Medium, High" for the Flash models and "Low, High" for Gemini 3.1 Pro. "Users can select which reasoning model they want to use within the model selector drop-down under the conversation prompt box." [vendor-docs] <https://antigravity.google/docs/models/>

Gemini 3.1 Pro API page: model id `gemini-3.1-pro-preview` (plus `gemini-3.1-pro-preview-customtools`), latest update February 2026, input limit 1,048,576 tokens, output limit 65,536 tokens, thinking supported, "built to refine the performance and reliability of the Gemini 3 Pro series." [vendor-docs] <https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview>

Gemini 3.1 Pro model card (published 2026-02-19): "the next iteration in the Gemini 3 series," intended for "Agentic performance, advanced coding, long-context understanding," context "up to 1M" input and "64K token" output, listed as available in Google Antigravity, and 80.6% on SWE-Bench Verified. [vendor-docs] <https://deepmind.google/models/model-cards/gemini-3-1-pro/>

Gemini 3.1 Pro launch post (2026-02-19): "designed for tasks where a simple answer isn't enough," 77.1% on ARC-AGI-2, available "in preview" in the Gemini API, Google AI Studio, Gemini CLI, Google Antigravity, and Android Studio. [vendor-announcement] <https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-pro/>

Antigravity's own post on 3.1 Pro (2026-02-19) describes it enabling "robust planning" and navigating "extensive codebases," with no effort or limit detail. [vendor-announcement] <https://antigravity.google/blog/gemini-3-1-pro-in-google-antigravity>

Gemini 3.8 Flash API page: model id `gemini-3.8-flash`, "New Stable," latest update September 2026, 1,048,576 input and 65,536 output tokens, thinking at low, medium, and high with "minimal is not supported and returns an error." [vendor-docs] <https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash>

Gemini 3.8 Flash model card (2026-09-02): "performance advancements across software engineering and agentic knowledge workflows," 1M input and 64K output, knowledge cutoff March 2026 for most domains, and it "builds directly on Gemini 3.7 Flash" without "meaningful new capabilities" for frontier safety purposes. [vendor-docs] <https://deepmind.google/models/model-cards/gemini-3-8-flash/>

The Gemini API models index (last updated 2026-09-24) confirms `gemini-3.1-pro-preview` remains Preview and `gemini-3.8-flash` is Stable, alongside `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, and `gemini-3.5-flash-lite`. [vendor-docs] <https://ai.google.dev/gemini-api/docs/models>

### Effort values and what they map to

The Gemini API thinking page (last updated 2026-09-25) defines `thinking_level` values `low`, `medium`, `high` for all thinking models plus `minimal` on select models; defaults are `high` for `gemini-3.1-pro-preview` and `medium` for `gemini-3.8-flash`, `gemini-3.7-flash`, and `gemini-3.5-flash`. No `max` level exists in the API. [vendor-docs] <https://ai.google.dev/gemini-api/docs/thinking>

In the Antigravity CLI the effort is baked into the catalog id: the Google codelab shows `agy models` returning `gemini-3.8-flash-high|medium|low`, `gemini-3.7-flash-high|medium|low`, `gemini-3.6-flash-high|medium|low`, `gemini-3.1-pro-high`, and `gemini-3.1-pro-low`, with the default at the codelab's last update being "Gemini 3.8 Flash (Medium)" and version 1.1.27 current. So `--effort` selects a thinking-level variant of the base model rather than a token budget. [vendor-docs] <https://codelabs.developers.google.com/antigravity-cli-hands-on>

CLI changelog entries: 1.1.5 "Added an `--effort` flag to select a model's reasoning-effort variant when launching the CLI" and "Added a `/effort` command to view and change the current model's reasoning effort"; 1.1.22 "Fixed selectable reasoning effort for Gemini 3.1 Pro and Gemini 3.5 Flash when you authenticate with a Gemini API key"; 1.1.25 "Added Gemini 3.8 Flash to the model catalog when connecting with a `GEMINI_API_KEY`"; 1.2.0 "Changed unselected model families in interactive `/model` picker to default to medium reasoning effort instead of low"; 1.2.11 "Improved reasoning effort level for models with different support, selectable with `--effort` or from the effort gauge in `/effort` and `/model`." [vendor-docs] <https://github.com/google-antigravity/antigravity-cli/blob/main/CHANGELOG.md>

Antigravity product changelog: 2026-07-31 (v2.5.0) "Added per-model reasoning effort levels (Low, Medium, High)"; 2026-09-02 (v2.12.2) Gemini 3.8 Flash for enterprise via ADC; CLI v1.2.0 on 2026-09-10 and v1.2.9 on 2026-09-23. [vendor-docs] <https://antigravity.google/changelog/>

The `max` value in the CLI help: a third-party integration's notes say "agy 1.2.11 accepts max as flag syntax, but no model on this account supports it" and "Gemini 3.1 Pro only publishes low/high effort levels." No Google page documents `max` for any Gemini model. [third-party] <https://github.com/hathbanger/orc/pull/111>

### Ultra plan limits

Antigravity plans page: Free has "Meaningful weekly quota with weekly refresh"; Google AI Pro has "High, generous quota, refreshed every five hours until weekly limit reached"; Google AI Ultra has "The highest, most generous quota, refreshed every five hours" and the highest weekly limits; Pro and Ultra can buy AI credits for overage; all tiers list Gemini 3.1 Pro and 3.8 Flash; "Rate limits correlate with agent workload rather than prompt count alone." [vendor-docs] <https://antigravity.google/docs/plans>

Plan change post (2026-05-19): $100 per month Google AI Ultra has "a rate limit of 5X worth of tokens compared to the $20/mo Pro plan" and $200 per month Ultra "20X worth of tokens"; quota is shared across Gemini Flash and Pro models and "drawn down according to API pricing"; non-Gemini models have separate fixed limits. [vendor-announcement] <https://antigravity.google/blog/changes-to-antigravity-plans>

Gemini subscriptions page: Ultra 5x at $99.99 per month gives "Higher rate limits to agent model in Google Antigravity"; Ultra 20x at $199.99 per month gives "Highest rate limits to agent model in Google Antigravity." [vendor-docs] <https://gemini.google/subscriptions/>

Gemini Apps help: Ultra limits are "5x or 20x higher than AI Pro limits depending on your subscription" with compute-based usage that refreshes every five hours, a 1M context window, and access to Flash-Lite, Flash, and Pro. [vendor-docs] <https://support.google.com/gemini/answer/16275805>

Press: Google raised Antigravity Gemini limits 3x twice in the week of 2026-05-21 after users hit weekly limits within a few sessions. [third-party] <https://9to5google.com/2026/05/21/google-has-tripled-gemini-usage-limits-for-antigravity-twice/>

### Guidance on effort level for coding agents

The Gemini thinking page: "Use minimal or low thinking for fact retrieval or classification," default thinking for moderate tasks, and "Use maximum thinking for advanced coding, math, or multi-step planning," with agentic work matched to complexity (lower for simple automations, higher for multi-step orchestration). [vendor-docs] <https://ai.google.dev/gemini-api/docs/thinking>

The Antigravity CLI best-practices page offers no model or effort recommendation per task type; its only delegation note is "For large-scale sweeps or multi-file refactoring, direct the primary agent to spawn concurrent background subagents." [vendor-docs] <https://antigravity.google/docs/cli/best-practices/>

A community guide asserts that low effort is "dramatically faster" for mechanical edits and high effort is "a different tool" for hard bugs, but that is not Google guidance. [third-party] <https://continuumcode.ai/guides/antigravity-cli/>

### What could not be found (Google)

- No Google page documents `--effort max` or maps it to a Gemini thinking level; the API has no `max` level, the Antigravity models page shows only Low and High for 3.1 Pro, and the only statement that `max` is accepted syntax without a supporting model is third-party.
- No Google page defines effort as a thinking token budget for Antigravity; the evidence (catalog ids like `gemini-3.1-pro-high`) shows effort selects a `thinking_level` variant.
- The Antigravity CLI docs pages "Using AGY CLI," "Overview," "Reference," and "Best Practices" contain no `--effort` or model list; the CLI documentation of those flags lives in the GitHub changelog and the Google codelab. The URLs `/docs/cli/configuration/` and `/releases/tag/v1.2.11` returned 404.
- Numeric Ultra quotas for Antigravity (tokens, requests, or prompts per five hours) are not published; only the 5X and 20X multipliers and the five-hour refresh.
- Gemini 3.1 Pro's general-availability date; as of 2026-09-24 the API still marks it Preview.
- The GitHub releases page fetch rendered years ambiguously for 1.2.9 through 1.2.11; the vendor changelog dates v1.2.9 as 2026-09-23.
