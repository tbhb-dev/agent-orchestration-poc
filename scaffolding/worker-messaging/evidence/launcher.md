# Interactive worker launcher evidence

## Sources and versions

- [documented] Codex source checkout `openai/codex@a6bd19261c30ce0a0225fe90e646822d29916f11`, installed CLI 0.157.1 help, and the imported [Codex lifecycle report](../../../research/imported/agent-session-tests/CODEX_SESSION_MANAGEMENT.md) distinguish a persisted thread from a loaded runtime thread. The checkout commit is a source snapshot, not proof that the installed binary was built from it.
- [documented] Claude Code source checkout `anthropics/claude-code@7779afb12e3635f46f56ec823979d68350ae000b`, its 2.1.283 `CHANGELOG.md`, installed CLI help, and the imported [Claude lifecycle report](../../../research/imported/agent-session-tests/CLAUDE_CODE_SESSION_MANAGEMENT.md) describe the live registry and peer socket.
- [help-text] Installed `agy --version` returned 1.2.11. `agy --help` advertises `--prompt-interactive` and `--remote-control` but no external send command.
- [observed] The imported [agy peering probe](../../../research/imported/agent-peering-tests/agy-peering-results.md) delivered `send_message` at a later turn and ignored an unsigned inbox file. An external coordinator sender and active-turn steering remain untested.

## Operator trial provenance

Sanitized coordinator notes in this directory record interactive Codex queue trials. The first confirmed idle delivery and a clean pause, but its proposed busy case remained idle. The second confirmed acceptance while busy and a separate turn after completion, without a numeric queue exit code. App-server steering and delivery to an unloaded thread remain untested by these trials. Both notes were scanned with `mise exec -- gitleaks dir --no-banner --redact=100` before inclusion.

## Current worker probes

- [verified] `mise exec -- codex --version` returned `codex-cli 0.157.1` with exit 0.
- [verified] `mise exec -- claude --version` returned `2.1.283 (Claude Code)` with exit 0.
- [verified] `mise exec -- agy --version` returned `1.2.11` with exit 0.
- [verified] `mise exec -- tmux -V` returned `tmux 3.7b` with exit 0.
- [observed] `mise exec -- codex app-server daemon version` failed because the sandbox denied connection to `~/.codex/app-server-control/app-server-control.sock` with `Operation not permitted`. A direct Python Unix-socket connect had the same `PermissionError`. The worker did not bypass the denial.
- [observed] The first disposable Codex launch started a tmux pane and Git worktree but `ps -o lstart=` returned `Operation not permitted` before a registry row was written. The worker killed its probe window and removed the clean worktree and branch. The launcher now persists a starting row before observing the pane.
- [observed] `mise run worker:launch -- --name launchprobe176 --issue 176 --harness codex --model gpt-6-sol --effort high --branch tooling/176-launch-probe --worktree /private/tmp/worker176-probe --brief-file /private/tmp/worker176-brief.md` returned run `01a0e15b-2bc2-72a8-92ad-b419f66819b2`, `unknown`, and exit 3. [The Codex pane capture](codex-launch-capture.txt) shows the interactive startup brief and exact `LAUNCHER-176-READY` reply. `tmux list-windows` recorded window `@25`, pane `%60`, and PID `36111`. `git worktree list --porcelain` recorded the requested branch and worktree. Both status and readiness returned `unknown` with exit 3 because the sandbox denied process start observation.
- [observed] `mise run worker:launch -- --name claudeprobe176 --issue 176 --harness claude --model haiku --effort low --branch tooling/176-claude-probe --worktree /private/tmp/worker176-claude-probe --brief-file /private/tmp/worker176-claude-brief.md` returned run `01a0e15c-16a6-7211-8891-f21cb5c38dae`, `unknown`, and exit 3. [The Claude pane capture](claude-launch-capture.txt) shows the interactive startup brief and exact `CLAUDE-176-READY` reply. `tmux list-windows` recorded window `@26`, pane `%61`, and PID `48678`. A live registry row for that PID reported `sessionId`, matching tmux target and cwd, but `ps` could not independently confirm process start. `claude agents --json` returned an empty array during the live probe, so this run did not confirm `ListAgents` membership.
- [observed] Killing each disposable pane made `worker:status` return `unknown` with exit 3. Both probe worktrees were clean and removed with their branches. The worker killed only its own `worker-messaging` tmux session and never touched session 0.
- [untested] Codex native thread discovery and `thread/read` confirmation remain unavailable under the sandbox's `ps` and Unix-socket denials. Claude `ListAgents` confirmation remains unavailable from the external coordinator CLI. Neither run is eligible for follow-up sends.

## Agy capability table

| Capability | Label | Limit |
| --- | --- | --- |
| Interactive startup prompt | help-text | `agy --prompt-interactive` advertises it, with no launch result from this worker yet |
| Model-side `send_message` | observed | Imported probe at 1.2.11 delivered at a later turn |
| Active-turn steering | untested | Imported probe saw later-turn delivery only |
| External coordinator sender | untested | No installed CLI command or bounded live proof |
| `--remote-control` send path | help-text | Flag presence is not delivery proof |
| Unsigned inbox injection | observed | Imported probe's foreign file was ignored |

## Checks

- [verified] `mise run worker:test-launcher` exited 0 with 24 tests passed. Plain value tables and properties cover ownership, native candidates, trust, first brief, stale process and tmux generations, unloaded recipients, and restart.
- [verified] `mise run fmt` exited 0 and changed only scaffold files.
- [verified] `mise run check` exited 0 after the prose fixes. Its coverage floors passed with Python core lines 100%, Python core branches 94%, Python shell lines 77.54%, Go core statements 96.43%, Go shell statements 74.58%, and Go core branches 94.74%.
- [verified] `mise run check:mutation` exited 0 with 145 of 149 Go mutants killed, 97.32%, and 454 of 467 Python mutants killed, 97.22%. The mutation task scores the product's core modules and does not score this temporary scaffold.
- [verified] `mise run build` exited 0. `mise exec -- gitleaks dir --no-banner --redact=100 --log-level error scaffolding/worker-messaging` exited 0.
- [verified] `mise run docs:build` exited 0 and built 54 pages. Chromium emitted a sandbox permission error during content sync, so that log is not evidence that browser rendering ran successfully.

## Review correction

- [schema] The pinned Codex source snapshot defines `thread/loaded/list` `data` as string thread IDs with `nextCursor` pagination, and thread status as an object tagged by `type`. The revised adapter reads every page; pure identity functions classify active, idle, and not-loaded statuses.
- [verified] `mise run worker:test-launcher` passed 37 tests after review corrections. New tests first failed on the old loaded-list decoder, absent tagged-status handling, fixed-depth repository paths, unowned checkout adoption, and first tmux startup. The corrected tests cover paged string IDs, active/idle/not-loaded statuses, a main checkout and linked checkout, lost registry and main rejection, and absent versus failed tmux observation.
- [verified] `git rev-parse --path-format=absolute --git-common-dir` returned the main checkout's `.git` path from this linked worktree. The command builder now receives that path, shim path, and captured `PATH` as values.
- [inference] Native readiness still requires an operator-authorized coordinator trial with process and Unix socket access because the unit tests cannot establish live Codex `thread/read`, Claude `ListAgents`, or agy external sends under this worker's sandbox denials.
- [verified] `mise run check:mutation` exited 0 after the review corrections. Go core killed 145 of 149 mutants (97.32%), and Python core killed 994 of 1068 mutants (93.07%). The temporary launcher scaffold is outside those mutation targets.
- [observed] Two `mise run check` attempts failed in the newly merged workflow-forms property test because a Hypothesis example exceeded its 200 ms deadline (265.36 ms and 333.05 ms). `mise run check:workflow-forms` passed alone with 41 tests. A third aggregate run passed prose and Python coverage checks but remained in Go branch coverage for more than five minutes and was interrupted. None of those failing or slow paths was changed in this PR.

## Scope and mapping

The file registry is distinct from [#153's run record](https://github.com/tbhb/agent-orchestration-poc/issues/153). The mappings and recovery steps are in [the start guide](../docs/start.md). The launcher exports the stage one author and committer environment from the operator's main-checkout launch wrapper. It does not change trust, sandbox, credentials, grants, or host settings.
