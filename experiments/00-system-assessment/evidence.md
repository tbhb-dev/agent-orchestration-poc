# Local system assessment for the agent-orchestration PoC

Date: 2026-09-26. Host: Tony's MacBook Air. All commands were read-only. Nothing was installed, started, or configured. Each finding is labelled VERIFIED (observed) or NOT CHECKED (with the reason).

## Headline findings

- The machine is an Apple M5 MacBook Air with 32 GB RAM, 466 GB free, running macOS 26.5.1. VERIFIED.
- Apple `container` 1.4.1 is installed and its apiserver is already running under launchd, with zero containers and zero images. VERIFIED.
- All three harnesses are installed and authenticated: Claude Code 2.1.283 (claude.ai login, Max subscription), Codex CLI 0.157.1 (ChatGPT login), Antigravity `agy` 1.2.11 (OAuth token file present). VERIFIED for Claude and Codex via their status subcommands. Antigravity auth is inferred from a token file's existence only.
- `gh` is logged in as `tbhb` with the `project` scope. VERIFIED.
- Tailscale 1.102.4 is running on tailnet `tbhb.github`, MagicDNS suffix `ibex-paradise.ts.net`, no serve or funnel config, zero peers currently online. VERIFIED.
- Every tool pinned in the repo's `mise.toml` is installed; `mise ls --missing` printed nothing. VERIFIED.
- Non-interactive shells do not pick up the repo's mise tool versions. In this session's shell `uv`, `prek`, `rumdl`, `vale`, `tombi`, `python3`, and `rustc` resolve to Homebrew, not mise, and `ryl` is not on PATH at all. `mise doctor` reports `shims_on_path: no`. VERIFIED. This matters for any orchestrator that spawns harnesses from a non-login shell.
- Missing tools the design may assume: `nats-server`, `nats`, `podman`, `colima`, `lima`, `qemu-system-aarch64`, `ruff`, `direnv`, `fish`, `websocat`, `shpool`, and a standalone `gemini` CLI. VERIFIED.
- The application firewall is disabled and SIP is enabled. VERIFIED.
- The repo has no commits yet on `main`, the GitHub remote is private with an empty default branch, and project 9 exists with 13 default fields, zero items, and one board view. VERIFIED.

## 1. macOS, hardware, and disk

VERIFIED.

```text
$ sw_vers
ProductName:    macOS
ProductVersion: 26.5.1
BuildVersion:   25F80

$ sysctl -n machdep.cpu.brand_string
Apple M5

$ sysctl -n hw.memsize
34359738368

$ system_profiler SPHardwareDataType | grep -Ei 'model name|model identifier|chip|memory|cores'
Model Name: MacBook Air
Model Identifier: Mac17,3
Chip: Apple M5
Total Number of Cores: 10 (4 Super and 6 Efficiency)
Memory: 32 GB

$ df -h /
Filesystem      Size  Used Avail Use% Mounted on
/dev/disk3s1s1  927G  462G  466G  50% /
```

## 2. Xcode command line tools

VERIFIED.

```text
$ xcode-select -p
/Library/Developer/CommandLineTools

$ pkgutil --pkg-info=com.apple.pkg.CLTools_Executables
package-id: com.apple.pkg.CLTools_Executables
version: 26.6.0.0.1781586589
volume: /
location: /
install-time: 1785799289

$ clang --version
Apple clang version 21.0.0 (clang-2100.1.1.101)
Target: arm64-apple-darwin25.5.0
```

## 3. Apple container CLI

VERIFIED. The system was already running before this assessment; nothing was started. `container system status` is a read-only query.

```text
$ container --version
container CLI version 1.4.1 (build: release, commit: 9a8917c)

$ which container
/usr/local/bin/container

$ container system status
status              running
client.version      1.4.1
server.version      1.4.1
server.appName      container-apiserver
host.os             Version 26.5.1 (Build 25F80)
host.architecture   arm64
host.cpus           10
paths.appRoot       /Users/tony/Library/Application Support/com.apple.container/
paths.installRoot   /usr/local/
containers.total    0
containers.running  0
images.total        0

$ launchctl list | grep -i container
30065  0   com.apple.container.container-network-vmnet.default
30476  0   com.apple.container.container-core-images
29653  0   com.apple.container.apiserver
22301  -9  com.apple.containermanagerd
-      0   com.apple.ContainerMigrationService
30272  0   com.apple.container.machine-apiserver
```

Top-level subcommands from `container --help`: container commands `clean`, `copy`/`cp`, `create`, `delete`/`rm`, `exec`, `export`, `inspect`, `kill`, `list`/`ls`, `logs`, `run`, `start`, `stats`, `stop`, `prune`; image commands `build`, `image`/`i`, `registry`/`r`; machine command `machine`/`m`; volume command `volume`/`v`; other commands `builder`, `network`/`n`, `system`/`s`; plugin `k8s` (local Kubernetes cluster management). Global options `--debug`, `--version`, `--help`.

Note the `com.apple.containermanagerd` and `com.apple.ContainerMigrationService` entries are Apple system daemons unrelated to the `container` CLI. The CLI's own agents are the `com.apple.container.*` entries. The `containermanagerd` last exit status of -9 is a system daemon detail, not a CLI fault.

## 4. git and gh

VERIFIED.

```text
$ git --version
git version 2.55.0
global user.name set: yes
global user.email set: yes

$ gh --version
gh version 2.100.0 (2026-09-03)

$ gh auth status
github.com
  ✓ Logged in to github.com account tbhb (keyring)
  - Active account: true
  - Git operations protocol: https
  - Token: gho_****
  - Token scopes: 'gist', 'project', 'read:org', 'repo', 'workflow'

  ✓ Logged in to github.com account aitellsbot (keyring)
  - Active account: false
  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'
```

The active `tbhb` account has the `project` scope. The secondary `aitellsbot` account does not.

## 5. tmux and shpool

VERIFIED.

```text
$ tmux -V
tmux 3.7b

$ which shpool
shpool not found
```

## 6. mise

VERIFIED. `mise install` was not run.

```text
$ mise --version
2026.8.6 macos-arm64 (2026-08-14)
mise WARN  mise version 2026.9.14 available
mise WARN  self-update is disabled for this install, update mise the same way you installed it
```

Repo `mise.toml`:

```toml
[tools]
go = "1.27"
node = "lts"
"pipx:ryl" = "latest"
prek = "latest"
rumdl = "latest"
rust = "stable"
tombi = "latest"
uv = "latest"
vale = "latest"
```

Pinned tools as resolved by `mise ls` in the repo (rows that cite the repo `mise.toml` or `.python-version`):

| Tool | Pin | Installed version resolved for this repo | Status |
| --- | --- | --- | --- |
| go | 1.27 | 1.27.1 | installed |
| node | lts | 24.21.0 | installed |
| pipx:ryl | latest | 0.22.0 | installed |
| prek | latest | 0.5.1 | installed |
| rumdl | latest | 0.2.48 (v0.2.53 and v0.2.62 builds also present) | installed |
| rust | stable | stable (symlink to ~/.cargo/bin, rustc 1.98.1) | installed |
| tombi | latest | 1.5.0 | installed |
| uv | latest | 0.12.10 | installed |
| vale | latest | 3.22.0 | installed |
| python (from .python-version) | 3.14 | 3.14.6 | installed |

```text
$ mise ls --missing
(no output)
```

`mise doctor` summary: `activated: yes`, `shims_on_path: no`, shell `/bin/zsh 5.9`, config files `~/.config/mise/config.toml`, the repo's `.python-version`, and the repo's `mise.toml`. Settings: `experimental = true`, `idiomatic_version_file_enable_tools = ["node", "python"]`. Backends include aqua, cargo, core, go, npm, pipx, github, ubi. One plugin: `asdf-code-lever-asdf-rust`. Result: "1 warning found: new mise version 2026.9.14 available, currently on 2026.8.6. No problems found."

The `rumdl` resolution is odd: `mise ls` shows the repo's `latest` mapped to 0.2.48 while `v0.2.53` and `v0.2.62` are also installed. The aqua backend toolset entry is `aqua:rvben/rumdl@0.2.48`. This was not investigated further.

The mise rust "install" is a symlink: `~/.local/share/mise/installs/rust/stable -> /Users/tony/.cargo/bin`. That directory is managed by rustup (`/opt/homebrew/bin/rustup 1.29.0`), so rust comes from rustup, not from a mise-downloaded toolchain.

## 7. Language toolchains and PATH resolution

VERIFIED. Two views are shown because they differ: what this session's non-interactive shell resolves, and what `mise` resolves for the repo.

Resolution in this session's shell (`which`):

```text
go      -> /Users/tony/.local/share/mise/installs/go/1.27.1/bin/go   (mise)
rustc   -> /opt/homebrew/bin/rustc                                    (Homebrew)
cargo   -> /opt/homebrew/bin/cargo                                    (Homebrew)
node    -> /Users/tony/.local/share/mise/installs/node/24/bin/node    (mise)
npm     -> /Users/tony/.local/share/mise/installs/node/24/bin/npm     (mise)
pnpm    -> /Users/tony/Library/pnpm/pnpm                              (pnpm self-managed)
bun     -> /Users/tony/.local/share/mise/installs/bun/latest/bin/bun  (mise)
python3 -> /opt/homebrew/bin/python3                                  (Homebrew)
uv      -> /opt/homebrew/bin/uv                                       (Homebrew)
```

Versions in this session's shell:

```text
go version go1.27.1 darwin/arm64
rustc 1.97.1 (8bab26f4f 2026-07-14) (Homebrew)
cargo 1.97.1 (c980f4866 2026-06-30) (Homebrew)
node v24.21.0
npm 11.19.0
pnpm 10.32.1
bun 1.3.12
Python 3.14.6
uv 0.12.1 (Homebrew 2026-07-31 aarch64-apple-darwin)
```

Resolution via mise for the repo (`mise which` and `mise exec`):

```text
rustc   -> /Users/tony/.cargo/bin/rustc        rustc 1.98.1 (48a229cea 2026-09-01)
cargo   -> /Users/tony/.cargo/bin/cargo        cargo 1.98.1 (797e8a9bc 2026-08-05)
uv      -> ~/.local/share/mise/installs/uv/latest/uv-aarch64-apple-darwin/uv   uv 0.12.10 (3c979abda 2026-09-04)
python3 -> ~/.local/share/mise/installs/python/3.14/bin/python3               Python 3.14.6
node    -> ~/.local/share/mise/installs/node/lts/bin/node
```

The PATH in this session contains only the mise entries from the global config (bun, go, kubectl, node, ruby, starship), not the repo-level ones (uv, prek, rumdl, vale, tombi, python, pipx-ryl). That is why `uv`, `rustc`, and `python3` fall through to Homebrew. Anything the orchestrator launches from a non-login or non-activated shell should run through `mise exec` or `mise x`, or put `~/.local/share/mise/shims` on PATH.

```text
$ uv python list | grep 3.14
cpython-3.14.6-macos-aarch64-none                   /opt/homebrew/bin/python3.14 -> ../Cellar/python@3.14/3.14.6/bin/python3.14
cpython-3.14.6-macos-aarch64-none                   /opt/homebrew/bin/python3 -> ../Cellar/python@3.14/3.14.6/bin/python3
cpython-3.14.6-macos-aarch64-none                   <download available>
cpython-3.14.6+freethreaded-macos-aarch64-none      <download available>
cpython-3.14.3-macos-aarch64-none                   /Users/tony/.local/bin/python3.14 -> /Users/tony/.local/share/uv/python/cpython-3.14-macos-aarch64-none/bin/python3.14
cpython-3.14.3-macos-aarch64-none                   /Users/tony/.local/share/uv/python/cpython-3.14-macos-aarch64-none/bin/python3.14
cpython-3.14.3+freethreaded-macos-aarch64-none      /Users/tony/.local/bin/python3.14t -> ...
cpython-3.14.3+freethreaded-macos-aarch64-none      /Users/tony/.local/share/uv/python/cpython-3.14+freethreaded-macos-aarch64-none/bin/python3.14t
```

Three Python 3.14 sources exist: Homebrew 3.14.6, mise 3.14.6, and uv-managed 3.14.3 (plus a free-threaded 3.14.3). The mise-managed interpreter is not in `uv python list` output because it is not on this shell's PATH.

## 8. Harnesses

### Claude Code

VERIFIED unless noted.

```text
$ claude --version
2.1.283 (Claude Code)
$ which claude
/Users/tony/.local/bin/claude

$ claude --help | grep -iE 'auth|login|setup-token'
  auth                                  Manage authentication
  setup-token                           Set up a long-lived authentication token

$ claude auth status
{
  "loggedIn": true,
  "authMethod": "claude.ai",
  "apiProvider": "firstParty",
  "analyticsDisabled": false,
  "projectsDirectory": "/Users/tony/.claude/projects",
  "configDirectory": "/Users/tony/.claude",
  "email": "<redacted>",
  "orgId": "<redacted>",
  "orgName": "<redacted>",
  "subscriptionType": "max"
}
```

`~/.claude/.credentials.json` and the macOS keychain entry: NOT CHECKED. The auto-mode permission classifier denied the command that inspected them as credential exploration, and `claude auth status` already answers the auth question.

User-scope settings, `~/.claude/settings.json` top-level keys:

```text
$schema, agentPushNotifEnabled, attribution, autoMode, cleanupPeriodDays, effortLevel, enabledPlugins, env, feedbackSurveyState, hooks, includeCoAuthoredBy, model, modelSettings, permissions, promptSuggestionEnabled, skipDangerousModePermissionPrompt, skipWorkflowUsageWarning, spinnerVerbs, statusLine, switchModelsOnFlag, tui
```

Hook event names in `settings.json`: `PreToolUse` only.

```text
~/.claude/settings.local.json   exists (79 bytes), top-level key: permissions
~/.claude/hooks/                guard-exit-echo.pl  rewrite-bsd-sed-i.pl  rewrite-zsh-equals.pl
~/.claude/CLAUDE.md             exists (3745 bytes)
~/.claude/rules/                does not exist
~/.claude/skills/               find-skills, synced/<org-id_user-id>/
~/.claude/agents/               does not exist
~/.claude/plugins/              blocklist.json cache config.json data installed_plugins.json known_marketplaces.json marketplaces plugin-catalog-cache.json synced
~/.claude.json                  exists, mode 600, 239161 bytes
```

Installed plugins from `installed_plugins.json`: `48-flaws-of-power@social-skills`, `agent-sdk-dev@claude-plugins-official`, `aitells-dev@aitells-dev`, `astral@astral-sh`, `claude-code-setup@claude-plugins-official`, `claude-md-management@claude-plugins-official`, `feature-dev@claude-plugins-official`, `playground@claude-plugins-official`, `process-theater@social-skills`, `skill-creator@claude-plugins-official`, `soft-skills@social-skills`, `weaponized-empathy@social-skills`. Marketplaces present: `astral-sh`, `claude-plugins-official`. Org-synced plugins under `plugins/synced/`: cowork-plugin-management, customer-support, data, design, engineering, finance, legal, marketing, operations, product-management.

`~/.claude.json` top-level keys (first 60, values omitted): additionalModelCostsCache, additionalModelOptionsAnsweredAt, additionalModelOptionsCache, announcementImpressions, anonymousId, autoCompactWindowsCache, autoModeEnvSetup, autoPermissionsNotificationCount, autoUpdates, autoUpdatesProtectedForNative, btwUseCount, cachedArtifactRoster, cachedChromeExtensionInstalled, cachedExperimentData, cachedExperimentFeatures, cachedExtraUsageDisabledReason, cachedGrowthBookFeatures, cachedGrowthBookFeaturesAt, cachedUsageUtilization, changelogLastFetched, claudeAiMcpEverConnected, claudeCodeFirstTokenDate, claudeInChromeDefaultEnabled, clientDataCacheSlots, closedIssuesLastChecked, customApiKeyResponses, deepLinkTerminal, effortCalloutV2Dismissed, feedbackSurveyState, firstStartTime, githubRepoPaths, githubWebConnectionStatusCache, groveConfigCache, hasCompletedClaudeInChromeOnboarding, hasCompletedOnboarding, hasResetAutoModeOptInForDefaultOffer, hasSeenAutoDefaultNotice, hasSeenAutoModeEntryWarning, hasSeenAutoModeOutsideReadPrompt, hasSeenTasksHint, hasUsedBackgroundTask, hasUsedRemoteControl, hasVisitedPasses, ideHintShownCount, installMethod, lastOnboardingVersion, lastPlanModeUse, lastReleaseNotesSeen, lastShownEmergencyTip, lspRecommendationIgnoredCount, machineID, mcpNeedsAuthNoticed, migrationVersion, modelAccessCache, numStartups, oauthAccount, officialMarketplaceAutoInstallAttempted, officialMarketplaceAutoInstalled, opusProMigrationComplete, orgModelDefaultCache.

### Codex CLI

VERIFIED unless noted.

```text
$ codex --version
codex-cli 0.157.1
$ which codex
/Users/tony/.local/bin/codex

$ codex login status
Logged in using ChatGPT
```

`~/.codex/auth.json`: exists, mode 600, 4305 bytes. Its top-level keys were NOT CHECKED, since `codex login status` already confirms auth and the classifier denied credential-file inspection for Claude's equivalent.

`codex --help` top-level commands: `agents`, `exec` (alias `e`), `review`, `login`, `logout`, `mcp`, `plugin`, `app-server` (experimental), `remote-control` (experimental), `app`, `completion`, `update`, `doctor`, `sandbox`, `debug`, `apply` (alias `a`), `resume`, `queue`, `archive`, `delete`, `migrate-rollouts`, `unarchive`, `fork`, `cloud` (experimental), `exec-server` (experimental), `features`, `help`. Notable global options: `-c key=value`, `--enable/--disable <FEATURE>`, `--remote <ADDR>` (ws, wss, unix), `--remote-auth-token-env`, `-s/--sandbox {read-only,workspace-write,danger-full-access}`, `--approve-for-me`, `--dangerously-bypass-approvals-and-sandbox`, `--dangerously-bypass-hook-trust`, `-C/--cd`, `--worktree`, `--add-dir`.

Full `codex exec --help` (112 lines):

```text
Run Codex non-interactively

Usage: codex exec [OPTIONS] [PROMPT]
       codex exec [OPTIONS] <COMMAND> [ARGS]

Commands:
  resume  Resume a previous session by id or pick the most recent with --last
  fork    Fork a previous session by id into a new session
  review  Run a code review against the current repository
  help    Print this message or the help of the given subcommand(s)

Arguments:
  [PROMPT]
          Initial instructions for the agent. If not provided as an argument (or if `-` is used),
          instructions are read from stdin. If stdin is piped and a prompt is also provided, stdin
          is appended as a `<stdin>` block

Options:
  -c, --config <key=value>
          Override a configuration value that would otherwise be loaded from `~/.codex/config.toml`.
          Use a dotted path (`foo.bar.baz`) to override nested values. The `value` portion is parsed
          as TOML. If it fails to parse as TOML, the raw string is used as a literal.

          Examples: - `-c model="o3"` - `-c 'sandbox_permissions=["disk-full-read-access"]'` - `-c
          shell_environment_policy.inherit=all`

      --enable <FEATURE>
          Enable a feature (repeatable). Equivalent to `-c features.<name>=true`

      --disable <FEATURE>
          Disable a feature (repeatable). Equivalent to `-c features.<name>=false`

      --strict-config
          Error out when config.toml contains fields that are not recognized by this version of
          Codex

  -i, --image <FILE>...
          Optional image(s) to attach to the initial prompt

  -m, --model <MODEL>
          Model the agent should use

      --oss
          Use open-source provider

      --local-provider <OSS_PROVIDER>
          Specify which local provider to use (lmstudio or ollama). If not specified with --oss,
          will use config default or show selection

  -p, --profile <CONFIG_PROFILE_V2>
          Layer $CODEX_HOME/<name>.config.toml on top of the base user config

  -s, --sandbox <SANDBOX_MODE>
          Select the sandbox policy to use when executing model-generated shell commands

          [possible values: read-only, workspace-write, danger-full-access]

      --approve-for-me
          Route approval requests through automatic review using the workspace-write sandbox

      --dangerously-bypass-approvals-and-sandbox
          Skip all confirmation prompts and execute commands without sandboxing. EXTREMELY
          DANGEROUS. Intended solely for running in environments that are externally sandboxed

      --dangerously-bypass-hook-trust
          Run enabled hooks without requiring persisted hook trust for this invocation. DANGEROUS.
          Intended only for automation that already vets hook sources

  -C, --cd <DIR>
          Tell the agent to use the specified directory as its working root

      --worktree
          Run the session in a new managed Git worktree

      --add-dir <DIR>
          Additional directories that should be writable alongside the primary workspace

      --thread-source <SOURCE>
          Source classification for newly created or forked threads

      --skip-git-repo-check
          Allow running Codex outside a Git repository

      --ephemeral
          Run without persisting session files to disk

      --ignore-user-config
          Do not load `$CODEX_HOME/config.toml`; auth still uses `CODEX_HOME`

      --ignore-rules
          Do not load user or project execpolicy `.rules` files

      --output-schema <FILE>
          Path to a JSON Schema file describing the model's final response shape

      --color <COLOR>
          Specifies color settings for use in the output

          [default: auto]
          [possible values: always, never, auto]

      --json
          Print events to stdout as JSONL

  -o, --output-last-message <FILE>
          Specifies file where the last message from the agent should be written

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

`~/.codex/config.toml` (mode 600, 6485 bytes), reproduced with values that looked like secrets redacted; nothing in it matched a token or key pattern. Sections in order:

```toml
notify = ["/Users/tony/.codex/computer-use/Codex Computer Use.app/Contents/SharedSupport/SkyComputerUseClient.app/Contents/MacOS/SkyComputerUseClient", "turn-ended"]
approvals_reviewer = "auto_review"

[marketplaces.openai-bundled]            source_type = "local"  (bundled marketplace under ~/.codex/.tmp)
[marketplaces.openai-primary-runtime]    source_type = "local"  (~/.cache/codex-runtimes/...)
[marketplaces.claude-plugins-official]   source_type = "git"    source = "https://github.com/anthropics/claude-plugins-official.git"

# enabled plugins
browser@openai-bundled, visualize@openai-bundled, documents@openai-primary-runtime, pdf@openai-primary-runtime,
spreadsheets@openai-primary-runtime, presentations@openai-primary-runtime, template-creator@openai-primary-runtime,
google-calendar@openai-curated, slack@openai-curated, claude-code-setup@claude-plugins-official,
claude-md-management@claude-plugins-official, feature-dev@claude-plugins-official, playground@claude-plugins-official,
skill-creator@claude-plugins-official, chrome@openai-bundled, sites@openai-bundled   (all enabled = true)

[features]
js_repl = false
memories = true

[mcp_servers.node_repl]
command = "/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node_repl"
startup_timeout_sec = 120
[mcp_servers.node_repl.env]   # NODE_REPL_* and BROWSER_USE_* settings, CODEX_HOME, CODEX_CLI_PATH (ChatGPT.app bundled codex)

[mcp_servers.computer-use]
command = "./Codex Computer Use.app/Contents/SharedSupport/SkyComputerUseClient.app/Contents/MacOS/SkyComputerUseClient"
args = ["mcp"]
enabled = false

[shell_environment_policy]
inherit = "core"
[shell_environment_policy.set]
BROWSER_USE_AVAILABLE_BACKENDS = "chrome,iab"
NODE_REPL_TRUSTED_BROWSER_CLIENT_SHA256S = "<sha256>"
NODE_REPL_TRUSTED_CODE_PATHS = "/Users/tony/.codex:/Applications/ChatGPT.app/Contents/Resources/cua_node/lib/node_modules"
CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR = "1"
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"
CLAUDE_CODE_DISABLE_MOUSE = "1"

[desktop]
external-agent-import-sync-enabled = true
followUpQueueMode = "queue"

# trusted projects (trust_level = "trusted"):
/Users/tony/Code/github.com/tbhb/repotools
/Users/tony/Code/github.com/tbhb/dotfiles
/Users/tony/Code/github.com/tbhb
/Users/tony/Code/github.com/tbhb/agent-peering-tests
/Users/tony/Code/github.com/tbhb/agent-session-tests
/Users/tony/Code/github.com/tbhb/agent-session-tests/codex
/Users/tony/Code/github.com/tbhb/agent-session-tests/codex/standalone
plus five scratchpad fixture paths under /private/tmp/claude-501/... and one /var/folders/.../codex-steering-* path

[hooks.state]   # trusted_hash entries for:
~/.codex/hooks.json:pre_tool_use:0:0, :0:1, :0:2
~/Code/github.com/tbhb/repotools/.codex/hooks.json:pre_tool_use:0:0
~/Code/github.com/tbhb/.codex/hooks.json:pre_tool_use:0:0

[tui]
screen_reader_detection_done = true
[tui.model_availability_nux]
gpt-6-astra = 4
```

Note the `shell_environment_policy.inherit = "core"` setting: Codex child shells get only a core environment, plus the explicitly `set` variables. Any environment the orchestrator relies on inside Codex will need `-c shell_environment_policy.inherit=all` or explicit `set` entries. Note also that the `[shell_environment_policy.set]` block already sets three `CLAUDE_*` variables, which will leak into Codex-spawned shells.

Other `~/.codex` items:

```text
~/.codex/AGENTS.md        exists (3739 bytes)
~/.codex/hooks.json       exists; one event, PreToolUse, with 1 matcher group (3 trusted hook commands)
~/.codex/hooks/           guard-exit-echo.pl  rewrite-bsd-sed-i.pl  rewrite-zsh-equals.pl   (same three scripts as ~/.claude/hooks)
~/.codex/skills/          only .system/ (imagegen, openai-docs, plugin-creator, review-agent, skill-creator, skill-installer); no user skills
~/.codex/prompts/         does not exist
~/.codex/rules/           default.rules
~/.codex/plugins/         cache/
~/.codex/app-server-daemon/, app-server-control/, ipc/   present (app-server daemon state directories)
```

### Antigravity agy

VERIFIED unless noted.

```text
$ which agy
/Users/tony/.local/bin/agy
$ agy --version
1.2.11
```

`agy --help`:

```text
Usage of agy:
  --add-dir                       Add a directory to the workspace (repeatable) (default [])
  --agent                         Agent for the current CLI session
  -c                              Short alias for --continue
  --continue                      Continue the most recent conversation
  --conversation                  Resume a previous conversation by ID
  --dangerously-skip-permissions  Auto-approve all tool permission requests without prompting
  --disable-slash-commands        Disable slash command and skill expansion in print mode
  --effort                        Reasoning effort for the current CLI session (low|medium|high|max)
  -i                              Short alias for --prompt-interactive
  --input-format                  Input format for print mode (text, stream-json). stream-json reads one NDJSON message per line from stdin and runs a turn for each; it requires --output-format stream-json (default text)
  --json-schema                   Optional JSON schema string or path to a schema file to enforce structured output (for stream-json, only applicable to the final result)
  --log-file                      Override CLI log file path
  --mode                          Set the agent execution mode for this session (accept-edits, plan)
  --model                         Model for the current CLI session
  --new-project                   Create a new project for this session
  --output-format                 Output format for print mode (text, json, stream-json) (default text)
  -p                              Short alias for --print
  --print                         Run a single prompt non-interactively and print the response
  --print-timeout                 Optional time limit for print mode; 0 waits until the turn completes (default 0s)
  --project                       Project ID or project name for the current CLI session
  --prompt                        Alias for --print
  --prompt-interactive            Run an initial prompt interactively and continue the session
  --remote-control                Create a remote connection for the CLI session on start up
  --sandbox                       Run in a sandbox with terminal restrictions enabled

Available subcommands:
  agent           List available agents
  agents          List available agents
  changelog       Show changelog and release notes
  help            Show help for subcommands
  install         Configure environment paths and shell settings
  mcp             Manage MCP servers (add, remove, list, enable, disable)
  mic-serve       Serve this machine's microphone to a CLI on another host
  models          List available models
  plugin          Manage plugins (install, uninstall, list, enable, disable)
  plugins         Alias for plugin
  remote-control  Manage the remote-control background daemon (start, status, stop)
  update          Update CLI
```

There is no auth-status subcommand. Config lives in `~/.gemini/`. Top-level contents:

```text
~/.gemini/antigravity-cli/   annotations/ antigravity-oauth-token (mode 600, 503 bytes, dated Sep 8) bin/ brain/ builtin/ cache/ cli.log -> log/cli-20260926_110744.log conversation_summaries.db conversations/ crashes/ history.jsonl implicit/ installation_id jetbox_summaries_proto.pb jetski_state.pbtxt keybindings.json knowledge/ last_check.timestamp log/ presence/ scratch/ settings.json (mode 600, 637 bytes) updater/
~/.gemini/config/            .migrated  config.json (mode 600, 86 bytes)  mcp_config.json (empty)  projects/
```

Auth evidence is the existence of `antigravity-oauth-token` only. Its contents and the contents of `settings.json` and `config.json` were NOT CHECKED (they are mode 600 and may hold credentials). `~/.antigravity`, `~/Library/Application Support/Antigravity`, `~/.config/antigravity`, and `~/.agy` do not exist. The `agy models` and `agy agents` subcommands were not run because they may contact the service. No standalone `gemini` CLI is installed (`which gemini` reports not found).

## 9. Tailscale

VERIFIED. No login was performed. Note `tailscale` on this machine is a zsh alias in `~/.zshrc` line 52 pointing at the app bundle binary, so non-interactive shells must call the full path.

```text
$ ls -d /Applications/Tailscale.app
/Applications/Tailscale.app

$ which tailscale
tailscale: aliased to /Applications/Tailscale.app/Contents/MacOS/Tailscale

$ /Applications/Tailscale.app/Contents/MacOS/Tailscale --version
1.102.4
  tailscale commit: 3caf7d9e7dcaba589cfc58beda596929733e4fea
  long version: 1.102.4-t3caf7d9e7-g084ee3b64
  go version: go1.26.6 (tailscale/go 7275f792d4)

$ tailscale status --json | jq '{...}'
{
  "BackendState": "Running",
  "HostName": "Tony's MacBook Air",
  "DNSName": "usdholt05.ibex-paradise.ts.net.",
  "MagicDNSSuffix": "ibex-paradise.ts.net",
  "Tailnet": "tbhb.github",
  "PeerCount": 10,
  "OnlinePeers": 0
}

$ tailscale serve status
No serve config

$ tailscale funnel status
No serve config
```

## 10. Other tools the design assumes

VERIFIED. Versions are as resolved on this session's PATH.

| Tool | Result | Path |
| --- | --- | --- |
| nats-server | missing | |
| nats | missing | |
| docker | Docker version 29.2.1, build a5c7197 | /usr/local/bin/docker |
| podman | missing | |
| colima | missing | |
| lima / limactl | missing | |
| qemu-system-aarch64 | missing | |
| just | just 1.57.0 | /opt/homebrew/bin/just |
| vale | vale version 3.21.0 (mise repo pin resolves 3.22.0) | /opt/homebrew/bin/vale |
| rumdl | rumdl 0.2.48 | /opt/homebrew/bin/rumdl |
| prek | prek 0.4.11 (Homebrew 2026-07-24) (mise repo pin resolves 0.5.1) | /opt/homebrew/bin/prek |
| tombi | tombi 1.2.5 (mise repo pin resolves 1.5.0) | /opt/homebrew/bin/tombi |
| ryl | missing on PATH (installed via mise pipx as 0.22.0, not on this shell's PATH) | |
| ruff | missing | |
| biome | Version: 2.5.6 | /opt/homebrew/bin/biome |
| guard-markdown | present | /Users/tony/go/bin/guard-markdown |
| jq | jq-1.8.2 | /opt/homebrew/bin/jq |
| direnv | missing | |
| fish | missing | |
| zsh | zsh 5.9 (arm64-apple-darwin25.0) | /bin/zsh |
| bash | GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25) | /bin/bash |
| sqlite3 | 3.51.0 2025-06-12 | /usr/bin/sqlite3 |
| websocat | missing | |
| caddy | v2.11.4 | /opt/homebrew/bin/caddy |

The Docker CLI is present at `/usr/local/bin/docker` and `~/.docker/bin` is on PATH, but whether a Docker daemon or Docker Desktop is installed or running was NOT CHECKED (checking would require contacting the daemon socket). The system bash is Apple's 3.2.57; no Homebrew bash 5 is on PATH.

## 11. Homebrew and Rosetta

VERIFIED.

```text
$ brew --version
Homebrew 7.0.4
$ brew --prefix
/opt/homebrew
$ /usr/bin/pgrep -q oahd && echo yes || echo no
yes
```

Rosetta 2 is installed (the `oahd` daemon is running).

## 12. Firewall and SIP

VERIFIED.

```text
$ /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
Firewall is disabled. (State = 0)
$ csrutil status
System Integrity Protection status: enabled.
```

Local servers will not be blocked by the application firewall. SIP is on, so anything touching protected system paths or kernel extensions is off the table.

## 13. Repo state and GitHub project

VERIFIED.

```text
$ git -C /Users/tony/Code/github.com/tbhb/agent-orchestration-poc status --short --branch
## No commits yet on main
?? .gitignore
?? .python-version
?? FABLE_HANDOFF.md
?? README.md
?? design-sketch/
?? mise.toml
?? prek.toml
?? pyproject.toml
?? src/
?? uv.lock

$ git remote -v
origin  https://github.com/tbhb/agent-orchestration-poc.git (fetch)
origin  https://github.com/tbhb/agent-orchestration-poc.git (push)

$ gh repo view tbhb/agent-orchestration-poc --json visibility,isPrivate,defaultBranchRef
{"defaultBranchRef":{"name":""},"isPrivate":true,"visibility":"PRIVATE"}
```

The local branch has zero commits and every file is untracked. The remote repo exists, is private, and has no default branch yet (nothing has been pushed).

```text
$ gh project view 9 --owner tbhb --format json   (trimmed)
{
  "title": "agent-orchestration-poc",
  "id": "PVT_kwHOARFd7s4BkxtJ",
  "number": 9,
  "url": "https://github.com/users/tbhb/projects/9",
  "closed": false,
  "public": false,
  "fieldCount": 13,
  "itemCount": 0,
  "readme": "",
  "shortDescription": ""
}

$ gh project field-list 9 --owner tbhb --format json   (name + type)
Title                  ProjectV2Field
Assignees              ProjectV2Field
Status                 ProjectV2SingleSelectField
Labels                 ProjectV2Field
Linked pull requests   ProjectV2Field
Milestone              ProjectV2Field
Repository             ProjectV2Field
Reviewers              ProjectV2Field
Parent issue           ProjectV2Field
Sub-issues progress    ProjectV2Field
Created                ProjectV2Field
Updated                ProjectV2Field
Closed                 ProjectV2Field

$ gh query graphql ... projectV2(number:9) { views(first:20) { nodes { name layout number } } }
View 1   BOARD_LAYOUT   number 1
```

The project has only GitHub's default fields (no custom fields yet), zero items, and a single default board view. `gh project` has no view-list subcommand, so views were read with a read-only GraphQL query.

## 14. Sibling test directories

VERIFIED.

```text
$ git -C ~/Code/github.com/tbhb/agent-peering-tests rev-parse --is-inside-work-tree
fatal: not a git repository (or any of the parent directories): .git
du -sh: 436K
files: 31
top-level: .claude .codex AGY_HANDOFF.md AGY_PEERING.md agy-peering-results.md c2.py CLAUDE_CODE_PEERING.md CLAUDE_HANDOFF.md claude-to-codex-outbound.jsonl claude-to-codex-results.md CODEX_HANDOFF.md CODEX_PEERING.md codex-peering-harness.py codex-peering-inbound.log codex-peering-outbound.json codex-peering-results.md DESIGN_REVIEW_ASTRA_V2.md DESIGN_REVIEW_ASTRA.md DESIGN_REVIEW_FABLE_5_1.md DESIGN_REVIEW_GEMINI_3_1_PRO_HIGH.md DESIGN_V2_REVIEW_FABLE_5_1.md DESIGN_V2_REVIEW_GEMINI_3_1_PRO_HIGH.md DESIGN_V2.md DESIGN.md OPEN_ITEMS.md peer.py probes SANDBOX_TESTS.md

$ git -C ~/Code/github.com/tbhb/agent-session-tests rev-parse --is-inside-work-tree
fatal: not a git repository (or any of the parent directories): .git
du -sh: 18M
files: 1082 total, 94 excluding .venv, .git, node_modules
top-level: .obsidian antigravity ANTIGRAVITY_SESSION_MANAGEMENT.md CLAUDE_CODE_SESSION_MANAGEMENT_files CLAUDE_CODE_SESSION_MANAGEMENT.html CLAUDE_CODE_SESSION_MANAGEMENT.md codex CODEX_SESSION_MANAGEMENT.md codex.md session_experiments
```

Neither directory is a git repository. Both are also listed as trusted projects in the Codex config.

```text
~/Code/github.com/tbhb/agent-session-tests/codex/.venv   exists
lib/                                                     python3.14
site-packages top-level names:                           pip  websockets
dist-info:                                               pip-26.1.2  websockets-17.1
```

The venv holds only `websockets` 17.1 on Python 3.14.

## Items not checked

- `~/.claude/.credentials.json` mode and keys, and the `Claude Code-credentials` keychain item. The permission classifier denied the inspection as credential exploration. `claude auth status` covers the auth question.
- `~/.codex/auth.json` top-level keys, `~/.gemini/antigravity-cli/settings.json`, `~/.gemini/config/config.json`, and the `antigravity-oauth-token` file contents. Skipped for the same reason; existence and modes are reported above.
- Whether a Docker daemon is installed or running. The CLI is present; querying the daemon was skipped as it may spawn or wake Docker Desktop.
- `agy models` and `agy agents`. Skipped because they may contact the service.
- Codex `doctor`. Skipped because its help says it diagnoses auth and runtime health and may attempt network or daemon interactions.
- `mise install`. Not run by instruction. `mise ls --missing` was empty, so nothing is pending.
