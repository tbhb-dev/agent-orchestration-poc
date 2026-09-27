---
title: Build group workflow
description: How the coordinator starts, observes, and stops host workers.
---

## Start and dispatch

Start `agentd serve` with an absolute state directory and the chosen loopback port, then run `agentd group start`. Prepare a brief file for one issue and call `agentd spawn` with the worker name, harness, model, effort, issue, type, slug, and brief path. The model and effort must be explicit. The [provisioner design](/design/provisioner/) lists the full commands and launch flags.

Workers keep separate branches and worktrees. The coordinator sends task material over the bus and uses `agentd capture` only for diagnosis. `agentd nudge` sends the fixed prompt to check pending messages. It does not put the message body into a terminal pane.

## Review and shutdown

The worker commits, pushes, and opens its PR. The coordinator reviews and merges after CI. `agentd stop` ends the worker window and retains its worktree. `agentd group stop` treats a window that already exited as stopped. Interrupted shutdowns can be retried, and a completed shutdown ends the private tmux session. A record from an earlier tmux server cannot target a replacement window with the same numeric ID. Worktree removal after merge remains a separate deliberate step.

**Untested:** issue #28 does not run real Claude Code, Codex, or `agy` spawns inside the worker sandbox. The operator and coordinator run the [recorded acceptance procedure](https://github.com/tbhb/agent-orchestration-poc/blob/feat/28-registry-tmux/reports/inputs/registry-tmux-28-evidence-2026-09-26.md) with their subscriptions. Operator commands in `agentctl` are connected after issue #27 merges.
