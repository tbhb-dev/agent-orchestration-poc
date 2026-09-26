# Coordinator decisions for the phase 0 plan

Written 2026-09-26 by the coordinator (Fable) after reading the design sketch, the agent-peering-tests research, and the agent-session-tests research. These are the inputs Codex turns into `PLAN.md`. Where a decision departs from `design-sketch/`, the reason is given. Facts marked [assessment] come from the system assessment in `experiments/00-system-assessment/`; facts marked [research] come from the imported research; everything else is a coordinator decision.

## 1. Names

The sketch's placeholders become the real names for the PoC, so nothing has to be renamed later:

- `agentd`: the host daemon. In phase 2 it is only the bootstrap provisioner plus the embedded NATS broker plus a SQLite registry with the host-tmux backend. It grows into the full daemon in phase 5. There is no separate throwaway `provision` tool; the sketch's `provision spawn|list|capture|nudge|stop` commands are `agentd`'s first API, exposed through `agentctl`.
- `agentctl`: one CLI for agents and the operator (join, send, receive, ack, status, roster, memory, claim; and in operator mode: group and session management).
- `agentd-guest`: the optional in-VM supervisor, only if experiments show shpool alone is not enough.
- The build group (the coordinator's own workers on the host) is a group named `build`.

## 2. Monorepo structure

```text
.
├── mise.toml                  # tools and tasks for the whole repo
├── go.mod                     # one Go module at the root: github.com/tbhb/agent-orchestration-poc
├── cmd/                       # Go binaries: agentd, agentctl (agentd-guest later)
├── internal/                  # Go packages (bus, registry, backend/tmux, backend/container, term, api)
├── crates/                    # Rust crates, only if experiments choose Rust for the daemon
├── schema/                    # language-neutral protocol definitions (format decided by experiment in phase 3)
├── apps/
│   ├── web/                   # React + Vite app
│   └── desktop/               # Tauri shell
├── packages/
│   ├── protocol/              # generated TypeScript types
│   ├── client/                # WebSocket client
│   └── ui/                    # Radix-based components
├── images/agent/              # agent image definition and in-image hook configs
├── experiments/               # NN-slug/ directories: README, scripts, evidence/, versions
├── research/imported/         # verbatim copies of the two research folders plus MANIFEST
├── src/agent_orchestration_poc/  # the shared Python helper package for experiment scripts
├── tests/                     # pytest tests for the Python package
├── docs/                      # Astro Starlight site
├── design-sketch/             # the sketch, until retired in phase 4
├── .github/workflows/         # CI
├── .worktrees/                # gitignored; every worker's worktree lives here
├── AGENTS.md, CLAUDE.md       # worker instructions (Codex writes them in phase 1)
├── PLAN.md                    # this plan, until the docs site absorbs it in phase 1
└── reports/                   # checkpoint reports, until the docs site absorbs them in phase 1
```

Decisions behind it:

- One Go module at the repository root, not under a `go/` directory. `go install ./cmd/...` and `go test ./...` stay conventional, and the bootstrap tooling is Go regardless of the daemon language.
- The `uv init` scaffold stays as the single Python project. The placeholder `src/agent_orchestration_poc/` package becomes the shared helper library for experiment scripts (evidence recording, harness discovery, the WebSocket-over-Unix client the Codex research already wrote twice). Its `main` entry point and the `[project.scripts]` entry go away. Experiment scripts live under `experiments/<NN-slug>/` and import the package. `README.md` gets real content from Codex.
- Frontend packages use pnpm workspaces (`pnpm-workspace.yaml` at the root), with pnpm pinned in `mise.toml`. Biome is the one JavaScript, TypeScript, CSS, JSON, and HTML tool, pinned through mise's `npm:` backend so it exists before any frontend package does.
- `experiments/` directories are numbered in dispatch order (`00-system-assessment`, `01-harnesses-in-container`, ...). Each has a `README.md` (written by Codex from the worker's evidence), the scripts, and an `evidence/` directory with raw output and a `versions.md` listing every version involved.
- Worktrees live in `.worktrees/<branch-slug>/` inside the repository, gitignored. The tbhb workspace's other repos use `.claude/worktrees/`, but that name is Claude-specific and this repository provisions worktrees for three harnesses, so one harness-neutral location is better. Linters and formatters exclude `.worktrees/`.

## 3. GitHub workflow

### Project

`https://github.com/users/tbhb/projects/9` holds every work item. Fields:

| Field | Type | Values |
| --- | --- | --- |
| Status | single select | Backlog, Ready, In progress, In review, Blocked, Done |
| Phase | single select | 0, 1, 2, 3, 4, 5, 6 |
| Area | single select | bus, daemon, containers, terminal, ui, desktop, remote, docs, tooling, experiment, research, workflow, security |
| Harness | single select | claude, codex, agy, any (the harness the coordinator intends to dispatch to) |
| Worker | text | the worker name once dispatched (for example `build/codex-docs`) |
| Priority | single select | P0 (critical path), P1, P2 |
| Size | single select | S, M, L |

Views: a board by Status (default), a table grouped by Phase, a filtered table "Ready to dispatch" (Status = Ready, sorted by Priority), a filtered table "Blocked" (Status = Blocked), and a table "Experiments" (Area = experiment). What the phase 1 worker can script, per `experiments/00-system-assessment/github-projects-research.md`: custom fields (single-select options included), replacing the built-in Status options, creating views with a layout, a filter, and visible fields, adding items and setting their fields, labels, and issue forms that auto-add to the project. What stays in the UI: the board column field, grouping, sorting, and the auto-add and auto-archive workflows; the worker leaves the operator a short list of those clicks. Issue types are organization-only, so the `type/*` labels carry that meaning here; sub-issues work and are used for splitting large items.

### Issues

One issue per work item. Every issue carries: goal (one paragraph), context and links (docs pages, sketch pages, research), acceptance criteria (checkboxes), evidence required (what raw material the worker must produce), docs impact (what Codex has to write or update when this lands), and out of scope. Labels: `area/<area>`, `type/<feature|experiment|research|docs|tooling|bug|decision>`, `phase/<n>`, `harness/<claude|codex|agy|any>`, `blocked`, `needs-operator`. A `decision` issue records a design decision and is closed by the decision record in the docs site.

### Branches and worktrees

Branch names are `<type>/<issue>-<slug>`, where type is one of `feat`, `fix`, `docs`, `exp`, `chore`, `research`, for example `feat/12-bus-consumer`. Every worker gets its own branch and its own worktree at `.worktrees/<type>-<issue>-<slug>/`. Workers never share a checkout and never work on `main`.

### Commits

Conventional Commits: `type(scope): imperative subject`, a body that explains why, and a `Refs: #<issue>` trailer. No attribution trailers (see section 13). Commit messages are linted with the `ai-tells-commits` Vale style through a prek `commit-msg` hook. `--no-verify` is forbidden except for the throwaway work-in-progress commit described in the worktree rules (see section 7).

### Pull requests

One PR per issue, small. Title is the conventional subject. Body: what, why, evidence (links to `experiments/` output or test runs), docs (what Codex wrote or what still needs writing), and a checklist (CI green, docs updated or issue filed, no secrets, evidence committed). Squash merge only: the repository settings allow squash merges and disable merge commits and rebase merges (set by the coordinator on 2026-09-26 at the operator's direction), the squash commit takes the PR title as its subject and the PR body as its body, so the PR body is written to the commit convention, and head branches are deleted on merge (the provisioner removes the matching worktree). Review policy: the coordinator reviews every PR; where practical a worker from a different harness than the author reviews first (a Claude worker reviews Codex PRs and the reverse), and the coordinator merges after review and green CI. The operator merges anything that changes security policy, credentials handling, egress rules, or anything installed outside the repository. Branch protection on `main` once CI exists in phase 1, as a repository ruleset (require a pull request, require the CI job by name, block force pushes and deletion), enabled by the coordinator. Rulesets and classic branch protection on a private personal repository both need GitHub Pro, and the API does not expose the account plan, so the operator confirms the plan first; without Pro the merge gate stays coordinator review plus CI status, unenforced by GitHub.

### CI

GitHub Actions running the same mise tasks workers run locally: `mise run check` (every linter and formatter check plus tests) on pull requests and on pushes to `main`, and `mise run docs:build` for the docs site. Jobs run on `ubuntu-latest` except where something needs macOS (Go code that links against Apple frameworks, the Tauri build, anything touching Apple Containers), which runs on `macos-latest`. mise itself is installed through the official action and cached.

### Push discipline

Workers push their branch whenever they report status on the bus and always before saying anything is done. Nothing that matters lives only on a worker's disk. The coordinator's `capture` of a pane is for diagnosis, never a substitute for a pushed branch.

## 4. The build group

### Before the provisioner exists (phases 0 and 1)

Workers are the coordinator's own Claude subagents, each in its own worktree (the Agent tool's worktree isolation), running three to four at a time. Codex runs non-interactively from the coordinator's shell (`codex exec`) inside a worktree for every document; Codex commits its own work on its branch. The coordinator reviews and merges. The operator is asked before anything is installed or changed outside the repository.

### Once `agentd` can spawn workers (phase 2 onward)

One tmux session named `build`, one window per worker, each worker in its own worktree with a brief file. Standing roster:

| Worker | Harness | Role |
| --- | --- | --- |
| `build/codex-docs` | Codex | Writes every document and report. Always present. |
| `build/codex-impl` | Codex | Implementer |
| `build/claude-impl-1` | Claude Code | Implementer |
| `build/claude-impl-2` | Claude Code | Implementer or experimenter |
| `build/claude-review` | Claude Code | Reviews Codex PRs; runs experiments when idle |
| `build/codex-review` | Codex | Reviews Claude Code PRs and runs `codex exec review`; experiments when idle |
| `build/agy-research` | `agy` | Bounded research: doc reading, inventories, lookups with a defined output shape |
| `build/agy-probe` | `agy` | Runs probe scripts that another worker wrote and collects the evidence; does not design experiments |
| `build/agy-impl` | `agy` | Probationary implementer for small, fully specified items; keeps the seat only if its PRs pass review at a rate comparable to the others |

Workers hand Codex their raw material (evidence files, notes, answers) over the bus or as files in their worktree, and `codex-docs` writes the prose. The coordinator's own subagents remain available for short, self-contained tasks (a search, a review pass) and for improving `agentd` while a provisioned worker is blocked on it.

**What `agy` is not given.** The operator's direction (2026-09-26): `agy` does not get anything that requires a lot of thought. Experiment design, the critical-path experiments (harnesses in the VM, shared authentication, bus semantics, NATS topology), security-relevant code, and design documents go to Claude Code and Codex workers. `agy` runs what others specified and reports evidence.

**Coordinator-side agent teams and workflows.** For non-implementation work the coordinator may run Claude Code agent teams or dynamic multi-agent workflows inside its own session instead of dispatching worktree workers: research fan-out across many sources, cross-checking a document against evidence, review passes over a PR set, retro data gathering, and inventories. The operator allowed this on 2026-09-26. Teammates run on `claude-sonnet-5` at medium (Anthropic's guidance for teammates) or `claude-opus-5-5` at high for review passes; they never edit the repository, so the worktree rule is not affected. Implementation always goes to worktree workers.

### Proposed concurrency

| Harness | Interactive workers | Notes |
| --- | --- | --- |
| Claude Code | 3 | Plus the coordinator's session and its subagents (at most 4 subagents at once) |
| Codex | 3 | One is always the docs writer; one reviews |
| `agy` | 3 | Research, experiments, and a probationary implementer |

Nine interactive workers in total. The operator set Codex and `agy` at three each on 2026-09-26 after the first proposal of two and one. The limits are renegotiated at the phase 2 checkpoint with observed rate-limit data (the vendors publish only multipliers and five-hour windows; see the model research).

### Proposed permission modes

The rule that drives all of this: workers must run unattended for long stretches, the coordinator never types approvals into a worker's terminal, and a blocked worker is escalated to the operator. So each harness runs in the mode that auto-approves routine, sandboxed work and denies or fails anything outside the sandbox rather than prompting.

- **Claude Code workers:** `claude --permission-mode auto --settings <per-worker settings file>` with sandbox on (`sandbox.enabled: true`), `autoAllowBashIfSandboxed: true`, and `sandbox.network.allowLocalBinding: true` (needed for direct loopback to the embedded NATS server [research]; user scope only, so it is a user-settings change the operator approves). `auto` is a documented `--permission-mode` choice in 2.1.283 [assessment]; its classifier auto-approves safe actions and denies sandbox bypasses (observed in the research when it refused to run `codex queue` unsandboxed). `--settings` lets the provisioner inject per-worker hooks without touching the operator's files. Fallback if `auto` stalls routine work: `acceptEdits` with a project-scope allowlist for `mise run *`, `git *`, `gh *`, and `agentctl *`. The allowed domains for the sandbox proxy are the model APIs, GitHub, and the package registries mise needs.
- **Codex workers:** `codex -s workspace-write -a never` (both flags verified in 0.157.1 [assessment]), with `[sandbox_workspace_write] network_access = true` (the only confirmed way Codex tool calls reach loopback [research]; it also opens all outbound network for those tool calls, which is acceptable on the operator's own machine for the bootstrap and is written down as a known widening). A narrower candidate exists in the source: `allow_local_binding = true` in a per-profile `[permissions.<name>.network]` table (there is no top-level `[network]` table; general network policy lives under `[features.network_proxy]`), and phase 2 tests it as a replacement. Two more Codex facts from the harness research shape phase 2: Codex hooks run unsandboxed and load from project `.codex/hooks.json` as well as user and inline config, so the shared-worktree caveat applies to Codex as it does to Claude Code and worker hooks are injected per launch rather than from the worktree; and hooks need a persisted trust hash, which `codex exec` never prompts for, so a provisioned Codex worker's hooks are trusted ahead of launch or the launch passes `--dangerously-bypass-hook-trust` for hooks the provisioner itself wrote. With `never`, a command that needs more than the sandbox allows fails and the worker reports it over the bus instead of prompting. Not `--approve-for-me`: the operator's user config already sets `approvals_reviewer = "auto_review"`, which lets Codex approve its own escalations, and the research flagged that mode as defeating the sandbox boundary. Two more Codex facts from the assessment shape phase 2: the operator's `~/.codex/config.toml` sets `shell_environment_policy.inherit = "core"`, so environment variables the provisioner injects (group, worker name, NATS URL, credentials path) do not reach Codex tool shells unless the launch adds `-c shell_environment_policy.inherit=all` or lists them under `shell_environment_policy.set`; that Codex strips any variable whose name contains `KEY`, `SECRET`, or `TOKEN` from tool shells by default, so per-worker bus credentials are handed over as a file path in a variable named without those words (for example `AGENTCTL_CREDS_FILE`), which also keeps the secret out of the environment; and that same config already sets three `CLAUDE_*` variables into Codex shells, which the phase 2 hook design must not mistake for a Claude Code session.
- **`agy` workers:** `agy --sandbox --dangerously-skip-permissions --prompt-interactive "<pointer to brief>"`. The installed 1.2.11 has `--sandbox` (run in a sandbox with terminal restrictions), `--mode accept-edits|plan`, and `--dangerously-skip-permissions` (auto-approve all tool permission requests) [assessment]. Inside the sandbox, skipping permission prompts is the same shape as Claude Code's `autoAllowBashIfSandboxed`: the sandbox is the boundary and prompts are what would otherwise block an unattended worker. The operator approved unattended `agy` on 2026-09-26. The harness research (`experiments/00-system-assessment/harness-research.md`, Antigravity section) then surfaced a better-shaped variant: `--sandbox` with `toolPermission: proceed-in-sandbox` in the worker's settings auto-runs sandboxed commands and prompts only for sandbox bypasses, the same shape as Claude Code's `autoAllowBashIfSandboxed`. Phase 2 tests that variant first and falls back to `--dangerously-skip-permissions` inside the sandbox if it still prompts for routine work; both are within what the operator approved. The Antigravity sandbox blocks network by default, so the loopback path to the bus is part of the same experiment. On Linux the `agy` sandbox uses kernel namespaces rather than Seatbelt, and headless Linux hosts without a D-Bus session bus bypass the keyring, which matters for the container experiments.
- **The coordinator's Claude subagents (phases 0 and 1):** the same settings as Claude Code workers.
- **`codex exec` runs (phases 0 and 1):** `codex exec -s workspace-write -C <worktree> -o <last-message-file>` with the brief on stdin. The installed 0.157.1 `exec` has no approval flag at all (it never prompts); `--approve-for-me` exists to route escalations through Codex's automatic review and is not used, so anything the sandbox blocks fails and shows up in the output for the coordinator to escalate [assessment].

Hooks for status reporting and inbox checks are installed in user scope for each harness in phase 2 (the research established that project-scope hooks in a shared worktree are a cross-harness escape). Each is a system change and goes to the operator with the exact file and content.

### Facts from the system assessment that shape the plan

From `experiments/00-system-assessment/evidence.md` [assessment]:

- Apple M5 MacBook Air, 32 GB, 466 GB free, macOS 26.5.1. Memory is the budget that decides how many group VMs run at once; the phase 3 memory experiment measures it.
- Apple `container` 1.4.1 is installed and its API server is already running under launchd with zero containers and images. The handoff expected it to be stopped; no system change is needed to start it, though the operator is still told before the first container experiment.
- All three harnesses are authenticated: Claude Code 2.1.283 (claude.ai login, Max), Codex CLI 0.157.1 (ChatGPT login), `agy` 1.2.11 (an OAuth token file exists; no status command). `gh` 2.100.0 is logged in as `tbhb` with the `project` scope over HTTPS.
- Every tool pinned in `mise.toml` is installed (`mise ls --missing` is empty), but mise shims are not on PATH in non-interactive shells: `uv`, `prek`, `rumdl`, `vale`, `tombi`, `python3`, and `rustc` resolve to Homebrew there and `ryl` is missing entirely. Every process the provisioner starts, and every CI step, runs through `mise exec` or `mise run`, never bare tool names.
- Not installed: `nats-server`, `nats`, shpool, ruff (it comes from uv), fish, websocat, podman, colima, lima, qemu, direnv. The Docker CLI is present; whether a daemon runs was not checked.
- Tailscale 1.102.4 is running on tailnet `tbhb.github` with MagicDNS suffix `ibex-paradise.ts.net`, no serve or funnel configuration. The `tailscale` command is a zsh alias to the app bundle binary, so scripts call the full path.
- The application firewall is off and SIP is on. Rosetta is installed.
- Project 9 has only GitHub's default fields, zero items, and one board view.
- The Codex `exec` help and the `agy` help are reproduced in the evidence file.

## 5. Phases, refined

### Phase 0 (this phase)

Done when the operator approves this plan, the concurrency, and the permission modes. Outputs: `experiments/00-system-assessment/` (raw evidence from the assessment subagent), the dependency clones under `~/Code/github.com/`, `PLAN.md`, and `reports/phase-0-checkpoint.md`. The initial commit of the scaffold plus these files lands directly on `main` (there is no CI or branch protection yet); after that everything goes through PRs.

### Phase 1: repository foundation

Work items, in dispatch order, each a subagent in its own worktree:

1. **Tooling** (`chore`): extend `.gitignore`; extend `mise.toml` (pin Python 3.14, pnpm, Biome, keep the operator's pins); configuration for ruff, pytest, Biome, Vale with vale-ai-tells (installed by release URL per its README, with `ai-tells` and `ai-tells-commits`), rumdl, ryl, tombi; a mise task per tool, `check` and `fmt` aggregate tasks; prek hooks (extend `prek.toml`, add the commit-msg lint); documentation linting covers every Markdown file except `research/imported/`.
2. **Skeleton** (`chore`): `go.mod`, `cmd/agentd` and `cmd/agentctl` that build and print a version, `internal/` layout, `pnpm-workspace.yaml` with empty `apps/` and `packages/` placeholders, `schema/`, `experiments/`, `images/agent/` with a README placeholder (content by Codex), `tests/` with one passing test, `.worktrees/` ignored.
3. **CI** (`chore`): the workflows in section 3, running against the tooling from item 1. Branch protection after the first green run.
4. **Docs site** (`chore`): Astro Starlight in `docs/` with Mermaid rendering at build time (an integration or remark plugin the worker evaluates from the cloned starlight source and records), the sidebar structure (Project, Workflow, Research, Experiments, Design, Decisions, Guides), `mise run docs:dev` and `docs:build`. Pages are placeholders until Codex writes them.
5. **Research import** (`research`): copy `~/Code/github.com/tbhb/agent-peering-tests` and `~/Code/github.com/tbhb/agent-session-tests` verbatim into `research/imported/<folder>/`, excluding `__pycache__`, `.DS_Store`, `.obsidian/`, `codex/.venv/` (recording its `requirements.txt` and the installed package list), and `CLAUDE_CODE_SESSION_MANAGEMENT.html` plus its `_files/` directory (a Quarto rendering of the Markdown report beside it; the importer confirms this by comparing headings). Scan every file for secrets, tokens, credentials, and personal data (the `.claude/settings.local.json` and `.codex/config.toml` in the peering folder, raw terminal captures, logs, `results.jsonl`, and the Codex evidence directory are the likely places), redact or hold back anything sensitive, and list it. Commit `research/imported/MANIFEST.md` with every source file's SHA-256, size, and destination or exclusion reason. Confirm the repository's visibility with the operator before pushing raw evidence.
6. **Worker instructions and docs pages** (`docs`, Codex): `AGENTS.md` and `CLAUDE.md` (workflow, mise, worktree and stash rules, Markdown rules, Codex-writes-docs rule, bus usage once it exists); docs pages for the workflow, the tooling, the repository layout, and the project history; move `PLAN.md` and the phase 0 report into the docs site.
7. **Project and issues** (`workflow`): configure the Project fields and views from section 3, create labels, file the phase 2 and phase 3 issues from this plan, and put them in the Project.

Checkpoint: the foundation is merged, the import and its manifest are merged, the Project reflects the plan.

### Phase 2: bootstrap orchestration

Build `agentd` v0 and `agentctl` with subagents, then switch to provisioned workers as soon as one of each harness can be spawned and reached over the bus. Work items:

1. Embedded NATS server in `agentd` with JetStream, one account per group, per-agent credentials with publish permissions limited to subjects ending in the agent's own name, the subject and stream layout from `design-sketch/04`, and a `build` group. Constraints verified against the cloned server (`experiments/00-system-assessment/nats-research.md`): the embedded server and in-process connections exist since 2.9; multi-filter consumers since 2.10; subject templates such as `{{name()}}` apply only to JWT scoped signing keys and auth callout, so either credentials are decentralized JWTs (operator, account, user) with a scoped signing key per group, or `agentd` generates an explicit per-user allow list in static config for each worker; per-key KV TTLs need the bucket created with limit markers and apply only on create (2.11+); connection limits are per account or per server, not per user; auth callout sees only connection metadata, credentials, and TLS state, so no kernel attribution is possible through it, and the research's socket-owner design stays retired. Current stable is v2.15.0 (2026-09-17); the Go module pins that tag.
2. `agentctl join|send|receive|ack|status|roster` against it, with compact machine-readable output.
3. The registry (SQLite) and the host-tmux backend: `spawn`, `list`, `capture`, `nudge`, `stop`, and group start, stop, and status, creating the worktree and branch, minting credentials, and starting the harness in a tmux window with a brief file.
4. Shared context: key-value buckets for status, roster, claims (create-if-absent plus compare-and-set), decisions, and brief; the memory tiers as files (`.agents/memory/` checked in, `.agents/local/` ignored).
5. Hooks per harness for status and inbox checks, in user scope, approved by the operator.
6. Experiments that gate the design: host loopback settings for each harness (which Codex setting, whether `agy` reaches loopback), initial-prompt behavior for each harness, and waiter semantics across compaction and restart.
7. How the coordinator itself uses the bus: `agentctl` from the coordinator's shell, with a background `receive` as its wake mechanism.

Checkpoint: one worker of each harness receives a brief, exchanges messages with the coordinator and each other, and reports status. Concurrency renegotiated.

### Phase 3: research and experiments

Codex workers synthesize the imported research into the docs site's Research section. Provisioned workers run the experiments from `design-sketch/12`, critical path first: harnesses in a Linux arm64 Apple Containers VM, shared authentication per harness, `container exec -it` fidelity, shpool in the guest, worktree mounts, embedded NATS behavior, NATS topology and reachability from a VM, NATS credentials and identity, waiter semantics, wake mechanisms. Then the rest. Starting the `container` system service is the first system change of this phase and goes to the operator before the first container experiment. The daemon language and the Tailscale integration are decided here with evidence.

Checkpoint: results and proposed decisions go to the operator.

### Phase 4: design in the docs site

Codex turns the surviving sketch plus results into the Design section with decision records. Retire `design-sketch/` in one commit. Verify the import against the originals with the manifest, update every reference, get explicit approval, delete the original folders, record the retirement.

Checkpoint: operator reviews the design docs and research synthesis, approves the retirement.

### Phase 5: build the PoC

Vertical slices, each demonstrable: daemon plus registry plus local backend plus one xterm.js terminal in the web UI; the Apple Containers backend with shpool, operator shells, and shared auth; the bus inside groups plus the message timeline and composer; the file browser; the Tauri app; Tailscale; egress control and the rest of the security policy. The build group appears in the PoC UI once the daemon hosts the host-tmux backend.

### Phase 6: end-to-end verification

Playwright tests (fake backend for most flows, Apple Containers for the full demo), the demo script written by Codex, known gaps written up and filed.

Checkpoint: the operator runs the demo.

## 6. Departures from the sketch, so far

- The provisioner is `agentd` from day one rather than a separate tool; the sketch already wanted the provisioner's operations to become daemon API calls.
- Worktrees live in `.worktrees/` inside the repository rather than outside it.
- Experiment directories are numbered.
- The `uv init` package is kept as a shared helper library rather than deleted.
- The handoff refers to a `WORK_DESIGN.md` in the peering research; no such file exists. The messaging and shared-memory designs exist only as the bullet lists in `OPEN_ITEMS.md`, which the sketch's page 04 already absorbed. Nothing is missing from the import as a result, but the phase 3 synthesis should say so.

## 7. Rules restated for workers

These come from the handoff and the tbhb workspace and go into `AGENTS.md` and `CLAUDE.md` in phase 1:

- mise for everything; no global installs; run tasks, never tools directly.
- Latest source for dependencies: clone or pull into `~/Code/github.com/<owner>/<repo>` and record the commit read.
- Evidence over assumption, with evidence labels: verified, observed, help-text, schema, documented, inference, untested.
- Only Codex writes documentation and reports. Code comments and docstrings stay with whoever writes the code.
- Diagrams: Mermaid or hand-drawn SVG. Mermaid sources are validated before they land: the coordinator's session has the Mermaid Chart MCP for interactive validation and rendering, and a Mermaid CLI check over every fenced `mermaid` block joins the CI checks (a phase 1 tooling candidate). Hand-drawn diagrams are made in Excalidraw (the coordinator's session has the Excalidraw MCP), exported to SVG for the docs site, and committed together with their `.excalidraw` source so they stay editable. Codex writes the Mermaid source as part of a page; drawings are produced on the coordinator's side from the page's content and handed to Codex to place.
- Markdown: one line per paragraph, sentence case headings; `guard-markdown` enforces the first.
- Everything committed and pushed. Parallel work in worktrees, one per worker.
- Shared stash stack: never a bare `git stash pop`; prefer `git rebase --autostash` or a throwaway `wip` commit (the only sanctioned `--no-verify`), unwound with `git reset --soft HEAD~1`.
- Sandbox escapes and system changes go to the operator.

## 8. Retrospectives and mechanical checks

The operator asked (2026-09-26) for regular agent-based retrospectives and for a standing watch for mechanical tooling, verification, and checks that raise quality or efficiency. Decisions:

- **Cadence.** A retrospective at every phase checkpoint, and a lightweight one after every ten merged pull requests during a phase. The coordinator dispatches it; it never skips one because the phase went well.
- **Who runs it.** A worker agent (a Claude Code reviewer or the Codex docs writer, alternating so both harnesses' views appear) reads the inputs and produces the raw findings; Codex writes the retro document.
- **Inputs.** The bus log for the period (message volume, unanswered questions, time-to-first-response), merged and closed PRs with review turnaround, CI failures and their causes, hook denials and sandbox failures reported by workers, worker restarts and blocked states, Project items that moved to Blocked, and the coordinator's own notes on where it had to intervene.
- **Output.** A retro page in the docs site under a Retros section (`docs/src/content/docs/retros/YYYY-MM-DD-<phase-or-count>.md`) with: what went well, what cost time, what broke, decisions, and action items. Every action item becomes an issue labeled `type/tooling` or `type/process` and goes into the Project. Until the docs site exists, retros live in `reports/`.
- **The mechanical-checks rule.** Every retro proposes at least one new mechanical check (a lint rule, a prek hook, a CI job, a guard script, a test, or a bus-side validation) or states why none applies this time. A check is preferred over an instruction in `AGENTS.md` whenever the failure it catches is detectable by a program.
- **Standing candidates for phase 1 tooling** (the first batch, added to the phase 1 tooling item): secret scanning in prek (gitleaks or an equivalent) so the research import and every later commit are scanned automatically; `guard-markdown` as a mise task and a CI job; the `ai-tells-commits` commit-message lint through prek; a script that checks every `experiments/<NN-slug>/` has a `README.md`, an `evidence/` directory, and a `versions.md`; a CI job that fails if anything under `research/imported/` changes after the import lands; a check that PR bodies contain an evidence link for `feat` and `exp` changes (a GitHub Actions job reading the PR body).
- **Standing candidates for later** (tracked as issues, not built yet): a bus-side schema check on message bodies; a hook that rejects worker commits without `Refs:`; a mise task that reports dependency-clone staleness against the recorded SHAs; Playwright smoke tests on every PR once the UI exists.
- **Promoted to phase 1 by a phase 0 failure:** a silent-worker timer. On 2026-09-26 a research subagent finished its sub-reports and then never assembled them; the coordinator waited nearly two hours for a notification that never came. Until the bus exists, the coordinator uses a scheduled check-in (the harness's wakeup or monitor facility) on every dispatch longer than fifteen minutes; from phase 2 the bus status bucket carries a last-seen timestamp per worker and `agentd` flags anything silent past a threshold.

## 10. Coordinator session rollover

The operator asked (2026-09-26) for a plan for rolling over coordination sessions: when to compact, when to hand off to a new Fable session, and how. Decisions:

- **Durable state before anything else.** The coordinator keeps nothing that matters only in its context window. Decisions go to the repository (the plan, issues, decision records, and from phase 2 the group's decisions bucket on the bus); working facts and operator preferences go to the coordinator's memory directory (`~/.claude/projects/<repo-slug>/memory/`, which every Claude Code session in this repository loads); in-flight state goes to a living handoff document. Workers are independent processes, so a coordinator rollover never stops them.
- **`HANDOFF.md`** at the repository root (moved into the docs site in phase 1 as the project's current-state page) is regenerated by Codex from the coordinator's inputs at every rollover and at every checkpoint. It holds: current phase and what is awaiting the operator, open PRs and their state, the worker roster with each worker's task and last known status, decisions made since the last checkpoint, gotchas discovered (the kind of thing in the coordinator's memory directory), the next three actions, the previous coordinator session id, and the date. `FABLE_HANDOFF.md` stays as the original operator handoff and is retired in phase 4 as planned.
- **Compaction triggers.** Compact at boundaries: after a checkpoint is approved, after a batch of dispatches is out and acknowledged, after a large reading phase. Never in the middle of reviewing a document or a PR. Before a deliberate compaction the coordinator writes any new durable facts to memory and, if more than a handful of things changed, has Codex refresh `HANDOFF.md`. Automatic compaction needs no ceremony once those habits hold, because nothing is lost that was not already written down.
- **Handoff triggers.** Start a fresh Fable session at every phase checkpoint once the operator approves it (the clean cut, and the moment `HANDOFF.md` is freshest), on the second compaction within one phase, when the coordinator shows degraded recall (asking about settled decisions, re-deriving established facts, contradicting the plan), or when the operator wants one. The operator can also ask for a rollover at any time.
- **Handoff procedure.** (1) Finish or park in-flight reviews; dispatched workers keep running. (2) Write new facts to memory. (3) Have Codex regenerate `HANDOFF.md` from the coordinator's inputs, review it, commit and push it (on `main` for a checkpoint handoff, on the current branch otherwise). (4) Record the session id in `HANDOFF.md`. (5) The operator starts a new session in the repository with `@HANDOFF.md`. (6) The new coordinator verifies before acting: `git status` and open PRs, the Project board, the bus roster and status bucket once they exist, and the memory index; it reports any discrepancy with `HANDOFF.md` to the operator instead of trusting the document.
- **Resume as the fallback.** `claude --resume <session id>` brings back the previous transcript when a new session finds `HANDOFF.md` insufficient, which is why the id is recorded. A resumed session is a stopgap for recovering context, not the normal path.
- **The coordinator owns the timing.** The operator monitors only this one interactive session and asked (2026-09-26) that the coordinator be proactive about compaction and handoff. So the coordinator, not the operator, watches context: every checkpoint message and every message that closes a heavy stretch of reading or dispatching ends with a one-line context recommendation (continue, compact after a named step, or hand off now), and the coordinator never recommends compacting while its judgment is still needed on in-flight results. The operator can still compact or roll over whenever they like. The phase retros review whether rollovers lost anything and add checks or handoff fields accordingly.
- **The coordinator's brief files survive rollover.** The scratchpad directory is per session and disappears with it, so anything a future coordinator needs from it (the decisions brief, research outputs) is committed to the repository before a handoff: research outputs under `experiments/`, the coordinator's decision briefs under `reports/inputs/`.

## 11. Assumptions register

The operator asked (2026-09-26) what the plan still takes from the coordinator's training data. This register lists those assumptions with the item that verifies each. The plan carries the register so a reader can tell a decision from a hypothesis, and the retros retire rows as evidence lands. A worker brief for any item below names the cloned source and docs to read first, at the commit recorded in `experiments/00-system-assessment/dependency-clones.md`.

| Assumption | Where it is used | Verified by |
| --- | --- | --- |
| Custom Project fields can be scripted with `gh`; whether views can be created through the API is doubtful | Phase 1 item 7 | Phase 0 research: `experiments/00-system-assessment/github-projects-research.md` |
| JetStream supports multi-filter pull consumers, `Nats-Msg-Id` dedup, KV compare-and-set and per-key TTLs, one account per group, per-user subject permissions, auth callout, leaf nodes, and an embedded Go server | Phase 2 items 1, 2, 4; sketch page 04 | Phase 0 research: `experiments/00-system-assessment/nats-research.md`, then the phase 2 bus experiments |
| Model capabilities and usage limits per subscription | Models section | Phase 0 research: `model-research.md` and `model-inventory.md` in the same directory; phase 2 checkpoint data |
| Harness hooks, tools, permission settings, and Linux support as of the installed versions | Permission modes, phase 2 items 3 and 5, phase 3 experiment 1 | Phase 0 research: `experiments/00-system-assessment/harness-research.md` (all three harnesses publish first-party Linux arm64 builds, glibc and musl for Claude Code and Codex), then the phase 2 and 3 experiments |
| mise `npm:` and `pipx:` backends, tasks, and `mise exec` in CI; prek `commit-msg` stage; Biome 2.5 config; Starlight 0.42 Mermaid options; Vale package install; pnpm workspaces | Phase 1 items 1 to 4 | The phase 1 workers read the cloned sources and docs before configuring; the item is not done until the versions and docs read are recorded in the PR |
| Apple `container` 1.4.1: internal networks, builder egress, exec resize forwarding, exec over vsock, memory return to the host | Sketch pages 05 and 06; phase 3 experiments 1, 3, 5, 12, 13 | Phase 3 experiments |
| shpool 0.11.5: `attach -c`, force attach, one client per session, restore modes | Sketch page 05; phase 3 experiment 4 | Phase 3 experiment 4 |
| Tailscale `tsnet` embedding and `tailscale serve` identity headers | Sketch page 08; phase 3 experiment 15 | Phase 3 experiment 15 |
| xterm.js 6 addon set and WebGL context limits in WKWebView; Tauri 2.12 shell behavior | Sketch pages 05 and 07; phase 3 experiments 14 and 16 | Phase 3 experiments 14 and 16, and the phase 5 UI slice |
| Kept on judgment, not research: Conventional Commits, squash merges, the branch naming scheme, the Project field set | GitHub workflow | Retros revise them if they cost time |

## 9. Models and effort levels

The operator asked (2026-09-26) for explicit models and effort levels for every worker and task. Evidence: `experiments/00-system-assessment/model-inventory.md` (which models each harness accepts on the operator's logins, each verified by a call, with the effort values each harness takes) and `experiments/00-system-assessment/model-research.md` (the vendors' model cards, docs, and release notes as fetched on 2026-09-26). Rules:

- Every launch names a model and an effort level explicitly. Nothing runs on a harness default, including `codex exec` document runs and the coordinator's own subagents.
- Starting assignments follow each vendor's published starting point for the model, not the coordinator's instinct: Anthropic says to start with Opus 5.5 at its default effort and step up only when evals or observed failures call for it; OpenAI says to start Sol at medium and Astra at low; Google exposes effort as a variant of the model id.
- The coordinator may raise the model or effort for one work item and records the choice in the issue. Stepping down happens only when retros show a task class routinely finishing without revision.
- The phase 2 checkpoint revisits every assignment with observed rate-limit and quality data, and rechecks the lineup: Anthropic has announced Sonnet 5.5 and Haiku 5.5 for the coming weeks, and Codex retires GPT-5.5 on 2026-10-14.

### What each harness offers

- **Claude Code 2.1.283:** `claude-fable-5-1` (alias `fable`; the `claude-fable-5-1[1m]` picker option selects the 1M-token context), `claude-opus-5-5` (`opus`, released 2026-09-22, the Max plan's default in Claude Code), `claude-sonnet-5` (`sonnet`), `claude-haiku-4-5-20251001` (`haiku`). Effort (`--effort`, `effortLevel`, `modelSettings`): low, medium, high, xhigh, max on Fable 5.1, Opus 5.5, and Sonnet 5; Haiku 4.5 has no effort control. Default effort is medium on Opus 5.5 and high on the others. Fable models draw weekly Max usage faster than other models and are capped at half of it; usage limits are otherwise shared across all models in five-hour and weekly windows.
- **Codex CLI 0.157.1:** `gpt-6-astra` (default locally; "most capable, built for the hardest end-to-end work"), `gpt-6-sol` ("built for complex coding and agentic workflows"), `gpt-6-luna` ("most efficient model for focused, high-volume tasks"), plus the older `gpt-5.6-*` line and `gpt-5.5` (retiring 2026-10-14). Reasoning effort (`-c model_reasoning_effort="<value>"`): low, medium, high, xhigh, max on all three; `ultra` on Astra and Sol delegates to subagents. Pro-plan allowance per five hours is published as message ranges: Astra 5 to 45 (Pro $100) or 100 to 900 (Pro $200); Sol 15 to 150 or 300 to 3,000; Luna 350 to 3,000 or 7,000 to 56,000. Astra consumes the allowance fastest.
- **Antigravity `agy` 1.2.11:** effort is a variant of the model id. Gemini 3.8, 3.7, and 3.6 Flash in high, medium, and low; `gemini-3.1-pro-high` and `gemini-3.1-pro-low` (Gemini 3.1 Pro is still a Preview model in the API); `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium`. The `--effort low|medium|high|max` flag selects the variant; `max` is accepted syntax that no Gemini model supports. Ultra-plan quota is 5x or 20x the Pro plan, refreshed every five hours, shared across Gemini models and drawn down by API pricing.

### Assignments

| Worker or task | Harness | Model | Effort | Why |
| --- | --- | --- | --- | --- |
| Coordinator (this session and its successors) | Claude Code | `claude-fable-5-1[1m]` | high | Anthropic's model for long-horizon agentic work at its default effort, with the 1M context because coordination reads everything. Fable's half-of-weekly cap is a reason the coordinator delegates reading to subagents on other models. |
| Coordinator subagents: implementation (phase 1 items) | Claude Code | `claude-opus-5-5` | medium | The vendor's recommended starting point: Opus 5.5 at its default effort matched Opus 5 at high on repository tasks. |
| Coordinator subagents: search, inventory, verification | Claude Code | `claude-sonnet-5` | medium | Fan-out work; medium on Sonnet 5 is documented as comparable to Sonnet 4.6 at high. |
| Coordinator subagents: mechanical git and file operations | Claude Code | `claude-sonnet-5` | low | Scripted steps; low is documented as suited to subagents. |
| Coordinator subagents: design-critical review | Claude Code | `claude-fable-5-1` | high | Where a missed defect is expensive (bus semantics, credentials, security policy). |
| `build/claude-impl-1`, `build/claude-impl-2` | Claude Code | `claude-opus-5-5` | medium | Implementer default per the vendor; high when an item fails once at medium, `claude-fable-5-1` at high for design-heavy items at the coordinator's call. |
| `build/claude-review` | Claude Code | `claude-opus-5-5` | high | Review is where "skipped a file, didn't run the tests" failures cost most, which is the vendor's trigger for stepping effort up. Experiments when idle at medium. |
| `build/codex-docs` and routine `codex exec` document runs (pages, retros, reports) | Codex | `gpt-6-sol` | medium | OpenAI's starting point for Sol, and the docs writer is always on; Astra's Pro allowance is too small for an always-on role. |
| Plans, design pages, and decision records (`codex exec` or `build/codex-docs` on request) | Codex | `gpt-6-astra` | medium | Judgment-heavy documents; the phase 0 plan was written at Astra's default and needed one revision for judgment, not facts. |
| `build/codex-impl` | Codex | `gpt-6-sol` | medium | The vendor's coding model at its starting effort; high for debugging and multi-file changes, `gpt-6-astra` at high for hard items at the coordinator's call. |
| `build/codex-review` and `codex exec review` runs | Codex | `gpt-6-astra` | low | Cross-harness review of Claude PRs; OpenAI's starting point for Astra is low, stepping up when a review misses something a retro catches. |
| `build/agy-research` | `agy` | `gemini-3.1-pro-high` | high (the variant) | Bounded research with a defined output shape. |
| `build/agy-probe` | `agy` | `gemini-3.8-flash-high` | high (the variant) | Runs specified probe scripts and reports; speed matters more than depth. |
| `build/agy-impl` | `agy` | `gemini-3.1-pro-high` | high (the variant) | The strongest Gemini coding option on the list; small, fully specified items only; the seat is probationary. |
| Coordinator agent teams and workflows (non-implementation) | Claude Code | `claude-sonnet-5`, or `claude-opus-5-5` for review passes | medium, or high for review | Anthropic's guidance for teammates; fan-out work stays cheap. |
| Utility tier: mechanical, fully specified tasks whose output a program verifies (checksum manifests, converting probe output to tables, running a fixed verification script, parsing logs and CI results for retros, PR template checks) | Claude Code | `claude-haiku-4-5-20251001` | none (no effort control) | Anthropic's guidance for simple subagent tasks; the verification step, not the model, carries the correctness. |
| Utility tier on the Codex side (the same task kinds, when a Codex worker owns the item) | Codex | `gpt-6-luna` | medium | OpenAI's high-volume model; its Pro allowance is an order of magnitude larger than Sol's. |
| `agy` headless probes (`--print`) and quick tasks | `agy` | `gemini-3.8-flash-medium` | medium (the variant) | The current Flash model at Google's default level. |

Not used: `ultra` on Codex (it delegates tasks on its own, which conflicts with the coordinator owning dispatch); Claude Code's `ultracode` setting for the same reason and because it reaches subscription limits sooner; the Claude and GPT-OSS models inside `agy` (the point of the third harness is a third model family); the `gpt-5.x` line; `max` effort anywhere until a measured gain justifies it. The utility tier is never given a task that needs judgment about whether something is wrong; the retros track rework caused by utility-tier runs and move a task class up if it recurs.

### Escalation and cost

The coordinator steps a worker up when a work item is on the critical path, touches security or credentials, or has failed once at the default; the vendor guidance is the same in all three cases: raise effort before switching model, switch model when the model had the context and still got it wrong. It steps down when retros show a task class routinely finishing without revision. Which Codex Pro tier and which Max tier the operator holds is not recorded (the CLIs do not expose it), and it decides how many Astra and Fable turns the group can afford per five hours, so the phase 2 checkpoint collects observed limits per harness and adjusts the concurrency table and these assignments together.

## 12. Devlog

The operator asked (2026-09-26) for a Codex agent to keep a regularly updated devlog for the project on the Starlight site. Decisions:

- **Who and when.** `build/codex-docs` writes it once provisioned; until then the coordinator runs `codex exec` for it. At least one entry per working day that had merged pull requests, experiment results, or a decision, and one entry at every checkpoint. The coordinator hands Codex the inputs at the end of each such day: merged PRs, bus highlights, experiment findings, decisions, blockers, and what is next.
- **Where.** In the docs site through the `starlight-blog` plugin (`HiDeoo/starlight-blog`), which the phase 1 docs-site worker evaluates from a clone under `~/Code/github.com/HiDeoo/starlight-blog` at a recorded commit and wires up with a `Devlog` entry in the sidebar; if the plugin does not fit the pinned Starlight version, dated pages under a `devlog/` section are the fallback. Until the site exists, entries accumulate under `reports/devlog/YYYY-MM-DD.md` and move into the site in phase 1 item 6.
- **What an entry contains.** Date and phase in frontmatter, tags by area; then: what landed (PR links), decisions and their evidence, experiments run and what they showed, problems and how they were resolved, what is next. Written for the operator and for future readers of the project, not for workers; no padding, no restated plans.
- **The first entry** covers phase 0 retroactively and is written when the phase 1 docs site item lands.
- **Mechanical check, later candidate:** a CI job or retro script that warns when merged PRs exist with no devlog entry in the following day, added to the standing candidates in section 8.

## 13. Commit attribution

Attribution trailers in commit messages and pull request descriptions are dropped (decided 2026-09-26). Commits carry the conventional subject, the body, and `Refs: #<issue>`; which harness and model did the work is recorded in the Project's Worker field and the PR body's evidence section. The commit-message lint stays.

## 14. Frontend research discipline

The operator warned (2026-09-26) that every model's training data is stale or wrong about current React development and asked for meticulous research of the latest APIs and best practices within the chosen stack before any frontend work. Decisions:

- **A research gate before frontend code.** No work item that writes TypeScript, React, Astro, or Tauri code starts until a research pass on the exact pinned versions has produced a conventions page in the docs site, written by Codex from the raw material a research worker gathers. The stack: TypeScript, React, React Router (the clone sits at the 8.x line), Vite, Vitest, Playwright, Radix UI, xterm.js 6, Tauri 2.12, Biome 2.5, and for phase 1 Astro and Starlight 0.42 with the `starlight-blog` plugin.
- **What the research reads.** The cloned sources' own docs and changelogs at the recorded commits (`experiments/00-system-assessment/dependency-clones.md`), the vendors' current docs sites, and each project's migration or upgrade guides for the last two major versions, since those name the deprecated patterns models still produce.
- **What the conventions page contains.** Per package: the pinned version and the commit read, the current APIs to use, the deprecated or removed APIs and patterns to avoid (with the version that removed them), project structure and data-flow conventions, testing patterns for Vitest and Playwright, and the Biome rules that enforce any of it. It is refreshed whenever a pin moves, as part of the PR that moves it.
- **Per PR.** Every frontend PR cites the conventions page sections it followed and any vendor doc it consulted beyond them; reviewers check code against the page, not against their own memory. A PR that introduces an API the page lists as deprecated fails review.
- **Mechanical enforcement.** Biome rules for what can be expressed as lint; a CI check that `package.json` pins match the versions the conventions page records; `pnpm outdated` reported in the retro so pins move deliberately.
- **Phase 1 already applies it** to the docs site: the docs-site worker reads Starlight 0.42 and Astro docs from the clones before writing configuration, records what it read in the PR, and Codex writes the first conventions page for the docs stack. The full React stack page is a phase 5 prerequisite and is listed as its own work item ahead of the first UI slice.

## 15. Research gates for every language and stack

The operator extended the frontend rule (2026-09-26): every phase that starts using a new language (Python, Rust, Go, and the rest) does the same research pass first and encodes the learnings into `AGENTS.md`, `CLAUDE.md`, and rules files. Section 14 becomes the frontend instance of this general rule. Decisions:

- **The gate.** Before the first work item that writes real code in a language or stack, a research item runs: a worker reads the pinned toolchain's release notes and docs at the recorded versions and the key libraries' docs and migration guides, and produces raw notes; Codex writes a conventions page in the docs site (Guides section) and encodes the operative rules into the instruction files. The gate is a Project item with the language in its title, sized S or M, and it blocks the first coding item for that language.
- **What gets encoded where.** The conventions page holds the full account with citations and versions. The instruction files hold only the rules a worker must apply while coding: `AGENTS.md` (read natively by Codex and by the other harnesses through `CLAUDE.md`, which imports it) for cross-harness rules, and path-scoped rules for Claude Code under `.claude/rules/<language>.md` so a worker editing Go sees the Go rules. The phase 1 harness research reports how Codex and `agy` load per-path rules; if either has an equivalent, the same rules are mirrored there by the tooling item. Rules name the versions they were written for, and the PR that moves a pin updates them.
- **Phase 1 items added.** Go 1.27 (modules, `go.mod` toolchain directive, testing, `go vet`, formatting, and which linter to adopt since the operator's required toolchain names none for Go; the coordinator proposes `staticcheck` or `golangci-lint` through mise and records the choice as a decision issue), and Python 3.14 with uv, ruff, and pytest (project layout under `src/`, ruff rule set, pytest configuration, free-threading and other 3.14 changes that matter). Both run before phase 1 items 2 and the helper-library work, alongside item 1. The Astro and Starlight page from section 14 runs before item 4.
- **Later phases.** Rust gets its gate before any crate is created: in phase 3 if the daemon is Rust, and in any case before the Tauri slice in phase 5, because the Tauri shell is Rust whatever the daemon language. Tauri 2.12 gets its own conventions coverage before that slice (the capabilities and permissions model, IPC commands and events, plugins, the CLI and bundling, and WKWebView specifics), alongside the React stack page that is phase 5 item 1 (section 14). Shell scripting in the agent image and the hooks gets a short page too (bash 3.2 on macOS versus bash 5 in the image, and fish and zsh differences), before phase 2 item 5.
- **Mechanical enforcement.** Each language's linter and formatter configuration is derived from the conventions page and checked in CI; a retro check confirms every language present in the tree (by file extension) has a conventions page and a rules file.
