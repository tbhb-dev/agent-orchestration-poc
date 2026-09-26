# Agent orchestration PoC

This project is building groups of interactive Claude Code, Codex, and Antigravity sessions in Apple Containers, with embedded NATS messaging and a shared web and Tauri interface. Phase 1 provides the repository foundation. The current Go binaries print their version.

## Documentation

Run `mise run docs:dev` to read the docs locally. Start with the [project overview](docs/src/content/docs/project/index.md), [plan](docs/src/content/docs/project/plan.md), and [workflow](docs/src/content/docs/workflow/index.md).

## Checks

Use `mise install` for pinned tools and `mise run vale:sync` in a fresh worktree. Run `mise run check` for lint, formatting checks, and tests. `mise run fmt` applies formatters, and `mise run build` produces `bin/agentd` and `bin/agentctl`.

Run `mise run docs:build` and `mise run docs:check-links` for site changes. Builds require Chromium for Mermaid rendering. See [tooling](docs/src/content/docs/workflow/tooling.md) for setup and tasks.

## Workers

Read [AGENTS.md](AGENTS.md) before working. It defines issues, branches, worktrees, commits, review, evidence, and language-rule loading.
