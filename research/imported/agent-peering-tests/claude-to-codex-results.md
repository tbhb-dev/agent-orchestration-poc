# Claude-to-Codex results

Run on 2026-09-26 from Claude Code session `agent-peering-tests-3d` (sessionId `8d3b00a9-d61c-4105-864a-477611e2da4c`, Claude Code 2.1.281, auto mode, macOS Seatbelt Bash sandbox), following [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md). Sender CLI `codex-cli 0.157.1`. Target thread `01a0de04-2459-7913-97cf-bd483040cd02` (`Acknowledge queue probe`, `cli_version` 0.157.1, `history_mode` paginated), confirmed by a read-only query of `~/.codex/state_5.sqlite`. Correlation marker `CLAUDE-CODEX-20260926-01`. Outbound log: `claude-to-codex-outbound.jsonl`.

## Summary

No message reached the Codex recipient. `codex queue` cannot run inside Claude Code's Bash sandbox, and Claude Code's auto-mode classifier denied running it outside the sandbox. Per the handoff, the tests that need a delivery stopped there, with no workaround attempted. Only T8's empty-argument case, which fails in argument parsing before any state or socket access, ran.

Recipient rollout size was 197941 bytes before the first attempt and 197941 bytes after the last, and contains no `CLAUDE-CODEX` marker. That confirms nothing was queued or delivered.

## T1: introduction and attribution

**Blocked.** Two attempts:

1. Inside the sandbox, at 14:40:22.80 UTC: exit 1 after 0.013 s, empty stdout, stderr:

   ```text
   WARNING: proceeding, even though we could not create PATH aliases: Operation not permitted (os error 1)
   Error: failed to initialize state database: failed to initialize sqlite local db at /Users/tony/.codex/state_5.sqlite: failed to initialize state runtime at /Users/tony/.codex: failed to open state DB at /Users/tony/.codex/state_5.sqlite: error returned from database: (code: 8) attempt to write a readonly database: error returned from database: (code: 8) attempt to write a readonly database: (code: 8) attempt to write a readonly database
   ```

   This matches the sender-sandbox failure recorded in `CODEX_PEERING.md`: the CLI opens its state database read-write before it contacts the daemon.

2. The same command with the sandbox disabled, submitted through Claude Code's permission gate: **denied** by the auto-mode classifier (`Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Safety Bypass Flag]`). The command never ran, so it has no log entry.

**Third attempt, after the user added `Bash(codex queue:*)` to `permissions.allow`:** the same command ran outside the sandbox and exited 0: `Queued message 01a0de39-470f-7c61-bf48-0476c6654c47 for thread 01a0de04-2459-7913-97cf-bd483040cd02.` A read-only query of `~/.codex/queue_1.sqlite` shows the entry **still pending** (order 0, `created_at_ms` 1790434690831, 14:58:10 UTC), and the recipient's rollout is unchanged since 14:08:32 UTC. The message was accepted but has not started a turn, which matches the "stored but not loaded" behavior in `CODEX_PEERING.md`. Runtime status was not queried. Per the handoff, the next step is for the user to confirm the recipient is loaded on this daemon, not for the sender to resume it.

## T2 to T7

**Skipped.** Each needs a successful `codex queue` send or an app-server socket connection, both blocked by the same denial. T4's negative addressing probes also need the state database, so running them inside the sandbox would fail at the same step without saying anything about name resolution.

## T8: negative text

**Empty argument, ran inside the sandbox, at 14:40:52.21 UTC:** `--message ''` exited 2 in 0.007 s. The stderr was `error: a value is required for '--message <TEXT>' but none was supplied`, printed after the PATH-alias warning. This matches `CODEX_PEERING.md`. The CLI rejects the message during argument parsing, before any state database or socket access, so the sandbox did not affect it.

**Whitespace-only message: skipped,** because it needs a real send.

## What would unblock the rest

The Claude session needs permission to run `codex queue` outside its Bash sandbox, because the CLI writes `~/.codex/state_5.sqlite` and connects to the daemon socket under `/private/tmp/codex-daemon-501/`. The user can grant that with a Bash permission rule, or adjust sandbox write access with `/sandbox`. Alternatively the user can run the commands in the handoff from an ordinary terminal and relay the results. The observation side (read-only rollout inspection through the state database) already works inside the sandbox.

## Difference from the opposite direction

Codex sending into Claude needed its own sandbox relaxed before it could bind its reply socket, and it then succeeded. Claude sending into Codex hits the same class of barrier, but in auto mode the classifier refused the relaxation outright rather than asking.
