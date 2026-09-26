---
title: Project
description: Interactive agent groups in Apple Containers with a shared operator interface.
---

The agent orchestration proof of concept will run groups of interactive Claude Code, Codex, and Antigravity `agy` sessions in git worktrees inside Apple Containers VMs. A host daemon will manage the groups with embedded NATS messaging and shared context. Web and Tauri interfaces will provide terminals, operator shells, files, git changes, and remote access over Tailscale.

## Required outcomes

The operator must be able to manage groups and sessions, open bash, fish, or zsh shells, inspect files and diffs, and see or send group messages. Shared authentication targets one login per harness across all groups. Experiments must establish a supported approach per harness or document a limitation and the closest workable alternative.

## Components and current state

`agentd` is the host daemon. Phase 2 starts it as a bootstrap provisioner with embedded NATS, a SQLite registry, and a host-tmux backend. `agentctl` is the CLI for workers and the operator. An optional `agentd-guest` supervisor depends on whether experiments show shpool is sufficient in a VM. The coordinator's host workers form the `build` group.

Phase 0 is approved and phase 1 is in progress. The binaries currently print a version. Messaging, group management, and the product UI are planned work.

Read the [plan](/project/plan/), [history](/project/history/), and dated [coordinator handoff](/project/handoff/). The [phase 0 checkpoint report](/project/phase-0-checkpoint/) preserves the assessment submitted for approval.
