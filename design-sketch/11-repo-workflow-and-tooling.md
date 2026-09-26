# Repository, workflow, and tooling

## Monorepo

Everything lives in `tbhb/agent-orchestration-poc`. The coordinator should settle the monorepo structure early, before parallel work starts, since changing it later disrupts every open worktree. A candidate to react to, not a decision:

```text
.
├── mise.toml                 # tools and tasks for the whole repo
├── cmd/                      # Go binaries: provisioner, agentctl, broker (and agentd if Go)
├── internal/                 # Go packages
├── crates/                   # Rust crates, only if the daemon ends up in Rust
├── schema/                   # language-neutral protocol definitions
├── apps/
│   ├── web/                  # React app (Vite)
│   └── desktop/              # Tauri shell
├── packages/
│   ├── protocol/             # generated TypeScript types
│   ├── client/               # WebSocket client
│   └── ui/                   # Radix-based components
├── images/agent/             # agent image definition and hooks
├── experiments/              # one directory per experiment, with a results write-up
├── research/imported/        # verbatim copies of the earlier research folders, with the import manifest
├── docs/                     # Astro Starlight site
└── design-sketch/            # this sketch, until retired
```

The `uv init` scaffold also left a Python package at `src/agent_orchestration_poc/`. Decide early whether Python lives there, under `experiments/`, or in per-tool directories, since probe scripts and experiment harnesses are mostly Python.

## mise

All project tooling and task automation goes through mise so it's isolated to the project:

- Tool versions pinned in `mise.toml`: Go, Rust if used, Node, Python 3.14, uv, and CLIs the build needs. The operator has already pinned go, node LTS, rust, uv, vale, prek, rumdl, tombi, and ryl, and initialized `pyproject.toml` with uv.
- Every repeatable action is a mise task: build, test, lint, format, generate (protocol types), docs dev and build, image build, e2e, experiments.
- Workers run tasks through mise, never global installs. CI runs the same tasks.

## Linting, formatting, and hooks

The operator has chosen the toolchain:

| Scope | Tool |
| --- | --- |
| Python | uv (through mise) with Python 3.14; ruff for linting and formatting; pytest for tests |
| Documentation | vale-ai-tells (Vale styles, source at `~/Code/github.com/tbhb/vale-ai-tells`) and rumdl |
| YAML | ryl |
| TOML | tombi |
| JavaScript, TypeScript, CSS, JSON, HTML | Biome |
| Pre-commit hooks | prek |

Each tool gets a mise task, one task runs them all, prek runs them on commit, and CI runs the same task.

The broader tbhb workspace uses Justfiles and `repotools` primitives. This repository uses mise tasks instead, per the operator. Markdown in this repository follows the workspace rule of one line per paragraph with no hard wrapping.

## Dependency clones

Whenever the design depends on a third-party project, clone its latest source into `~/Code/github.com/<owner>/<repo>` (or pull if it's already there) and read the source and docs from there rather than relying on memory or web summaries. Likely candidates: `nats-io/nats-server`, `nats-io/nats.go`, `nats-io/nats-architecture-and-design` (the ADRs behind JetStream behavior), `apple/container`, `apple/containerization`, `shell-pool/shpool`, `tailscale/tailscale`, `tauri-apps/tauri`, `xtermjs/xterm.js`, `withastro/starlight`, `openai/codex`, `radix-ui/primitives`, `remix-run/react-router`, and whatever else the design leans on. Record the commit read in experiment write-ups.

## GitHub workflow

The coordinator designs the workflow early and has Codex write it down in the docs site (and in `AGENTS.md` and `CLAUDE.md` for workers). Things it should cover:

- **Project.** `https://github.com/users/tbhb/projects/9` holds every work item. Fields, views, and statuses are the coordinator's call.
- **Issues.** One issue per work item, with acceptance criteria and links to the relevant docs. Labels for area (bus, daemon, containers, terminal, ui, desktop, remote, docs, tooling, experiment) and type.
- **Branches and worktrees.** Every worker works in its own local git worktree on its own branch, so workers never share a checkout. Decide where worktrees live (outside the repository, or in a gitignored directory inside it) and how they're named.
- **Commits and PRs.** Commit message convention, PR template, one PR per issue, and small PRs. Reviews by a worker from a different harness than the author, where practical.
- **Merging.** Who merges (the coordinator after review, with the operator for anything risky), and the merge style.
- **CI.** GitHub Actions running the mise tasks, on macOS runners where anything depends on macOS.
- **Push discipline.** Everything committed and pushed; nothing lives only on a worker's disk.

## Documentation site

- Astro Starlight in `docs/`. All project documentation lives there: architecture, design decisions (a decision record format is worth adopting), research and experiment results, how-to guides for running the PoC, and the workflow.
- Only Codex agents write documentation and reports. Other agents supply evidence, notes, and answers; Codex writes the prose.
- Diagrams are Mermaid or hand-drawn SVG only. Mermaid needs a Starlight integration or a remark plugin; pick one that renders at build time if possible.
- When the site is established and has absorbed this sketch, delete `design-sketch/` in one commit (see its README).
