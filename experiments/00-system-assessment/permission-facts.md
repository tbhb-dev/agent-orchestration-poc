# Harness permission-mode facts

Verified read-only on 2026-09-26 by a coordinator subagent. No settings were changed and no sessions were started. VERIFIED means observed in help text or in the cloned source; NOT FOUND means the check came up empty.

## Claude Code 2.1.283

VERIFIED: `claude --help` documents `--permission-mode <mode>` with choices `acceptEdits`, `auto`, `bypassPermissions`, `manual`, `dontAsk`, `plan`. `auto` is a valid choice. There is no `default` value in the list.

VERIFIED: `--dangerously-skip-permissions` ("Bypass all permission checks. Recommended only for sandboxes with no internet access") and `--allow-dangerously-skip-permissions` exist.

VERIFIED: `--settings <file-or-json>` loads additional settings, so a launcher can inject hooks and sandbox settings per session without touching the user's files. `--setting-sources user,project,local` selects which scopes load. `--restricted` removes command-running tools. An `auto-mode` subcommand inspects or resets the auto mode classifier configuration.

## Codex CLI 0.157.1 (source at ~/Code/github.com/openai/codex, HEAD a6bd19261c30ce0a0225fe90e646822d29916f11)

VERIFIED: the top-level interactive `codex` command accepts `-a, --ask-for-approval <APPROVAL_POLICY>` with CLI values `on-request` and `never` only (`codex-rs/tui/src/cli.rs:69-71`, `codex-rs/utils/cli/src/approval_mode_cli_arg.rs:7-16`). `never` means "Never ask for user approval. Execution failures are immediately returned to the model."

VERIFIED: the `approval_policy` config key (`codex-rs/protocol/src/protocol.rs:984-1009`) accepts `untrusted`, `on-request` (default; `on-failure` is a legacy alias), `granular` (a table with `sandbox_approval`, `rules`, `skill_approval`, `request_permissions`, `mcp_elicitations`), and `never`.

VERIFIED: `--approve-for-me` (alias `--not-so-yolo`) expands to `approvals_reviewer="auto_review"`, `approval_policy="on-request"`, `sandbox_mode="workspace-write"` (`codex-rs/utils/cli/src/shared_options.rs:43-93`). `approvals_reviewer` is `user` (default) or `auto_review`, where a subagent decides sandbox escapes, blocked network access, MCP approval prompts, and escalations (`codex-rs/protocol/src/config_types.rs:175-190`). The operator's user config currently sets `approvals_reviewer = "auto_review"`. The core can also force `auto_review` on for some models (`codex-rs/core/src/session/mod.rs:662-694`).

VERIFIED: `shell_environment_policy.inherit` is `core`, `all` (default), or `none` (`codex-rs/protocol/src/config_types.rs:205-218`). `core` keeps only `PATH, SHELL, TMPDIR, TEMP, TMP, HOME, LANG, LC_ALL, LC_CTYPE, LOGNAME, USER` (`codex-rs/protocol/src/shell_environment.rs:162-166`). After inheritance, default excludes drop any variable whose name matches `*KEY*`, `*SECRET*`, or `*TOKEN*` unless `ignore_default_excludes` is set (lines 123-125). The operator's user config sets `inherit = "core"` plus a `set` table. Keys available: `inherit`, `ignore_default_excludes`, `exclude`, `set`, `include_only`, `filters`, `experimental_use_profile` (`codex-rs/config/src/shell_environment_policy.rs:15-38`).

VERIFIED: `[sandbox_workspace_write]` has exactly four keys: `writable_roots`, `network_access`, `exclude_tmpdir_env_var`, `exclude_slash_tmp` (`codex-rs/config/src/types.rs:1134-1145`, unknown fields rejected). `allow_local_binding` is a `[network]` key instead: "Permits local servers and direct host-loopback connections and skips the proxy's additional private-network destination checks. Proxy domain rules still apply. Defaults to false" (`codex-rs/config/src/permissions_toml.rs:328-348`). So the two candidate ways for Codex tool calls to reach loopback are `[sandbox_workspace_write] network_access = true` (confirmed working in the research; opens all outbound network) and `[network] allow_local_binding = true` (narrower; untested here).

NOT FOUND: the cloned repo's `docs/config.md`, `docs/sandbox.md`, and `docs/example-config.md` are stubs pointing at developers.openai.com.

## Antigravity agy 1.2.11

VERIFIED: `agy help` documents `--dangerously-skip-permissions` ("Auto-approve all tool permission requests without prompting"), `--mode` ("Set the agent execution mode for this session (accept-edits, plan)"), and `--sandbox` ("Run in a sandbox with terminal restrictions enabled"). `--mode` has only those two values; there is no auto or bypass mode value. `--sandbox` takes no sub-options.

NOT FOUND: `agy help sandbox` and `agy help mode` report unknown subcommands; the help covers only the listed subcommands.

VERIFIED: `~/.gemini/antigravity-cli/settings.json` (mode 600) has top-level keys `allowNonWorkspaceAccess`, `enableTerminalSandbox`, `model`, `permissions`, `toolPermission`, `trustedWorkspaces`. Values were not read.
