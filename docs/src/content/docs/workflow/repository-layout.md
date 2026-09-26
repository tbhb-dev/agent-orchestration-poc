---
title: Repository layout
description: The repository tree after the phase 1 skeleton and documentation moves.
---

This is the tree after the phase 1 skeleton and documentation moves. `apps/` and `packages/` contain placeholders, and the Go binaries currently print a version.

```text
.
├── AGENTS.md, CLAUDE.md       # cross-harness instructions and Claude import
├── README.md                 # project entry point
├── PLAN.md, HANDOFF.md       # pointers to site pages
├── FABLE_HANDOFF.md          # original operator handoff
├── mise.toml, prek.toml      # pinned tools, tasks, and hooks
├── go.mod                   # one root Go module
├── cmd/{agentd,agentctl}/    # version-printing commands
├── internal/                # Go packages
│   ├── api/, bus/, registry/, term/
│   ├── backend/{tmux,container}/
│   └── version/             # version value and tests
├── src/agent_orchestration_poc/ # shared Python helper package
├── tests/                   # pytest tests and marker setup
├── pyproject.toml, uv.lock   # Python project and locked dependencies
├── apps/, packages/         # future frontend workspace placeholders
├── package.json             # pnpm package-manager pin
├── pnpm-workspace.yaml      # currently includes docs only
├── pnpm-lock.yaml           # docs dependency lockfile
├── schema/                  # protocol format deferred to experiments
├── images/agent/            # future agent image
├── experiments/
│   └── 00-system-assessment/ # phase 0 evidence and versions
├── research/
│   ├── gates/{go,python,docs-stack}/ # raw conventions research
│   └── imported/            # immutable research and MANIFEST.md
├── docs/
│   ├── astro.config.mjs     # sidebar, Mermaid, and blog plugins
│   └── src/
│       ├── content.config.ts # docs and devlog schema
│       └── content/docs/    # project, workflow, research, experiments,
│                            # design, decisions, guides, retros, devlog
├── design-sketch/           # starting design until phase 4
├── reports/inputs/          # retained raw coordinator inputs
├── scripts/                 # repository guard scripts
│   └── mermaid-check/       # pinned Mermaid parser
├── .claude/
│   ├── agents/              # implementation, research, and review roles
│   └── rules/               # Go and Python path-scoped rules
├── .github/workflows/       # check, docs, pr-body, imported-research
└── .worktrees/              # ignored worker checkouts
```

Linter configuration is listed in [tooling](/workflow/tooling/). Generated `bin/`, `docs/dist/`, `docs/.astro/`, virtual environments, dependencies, and worktrees are ignored.

## Layout decisions

The Go module is at the root so commands use conventional `cmd/` and `internal/` paths. Python experiments share the `src/` helper package. The root pnpm workspace currently lists only `docs`, and future web and desktop packages will be added when their research gates are complete. Rust crates await their research gate.

The [plan](/project/plan/#repository-layout) records the intended later structure. The [handoff](/project/handoff/), [checkpoint](/project/phase-0-checkpoint/), [retro](/retros/2026-09-26-phase-0/), and [devlog](/devlog/2026-09-26-phase-0-done-phase-1-started/) now live in the site. Root plan and handoff pointers preserve session-start references.
