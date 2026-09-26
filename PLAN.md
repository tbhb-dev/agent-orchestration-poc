# Project plan

## Status

Written 2026-09-26 for the phase 0 checkpoint, this plan records the coordinator's decisions, subject to the requirements in `FABLE_HANDOFF.md`. It awaits the operator's approval of the plan, concurrency limits, and worker permission modes. It moves into the docs site in phase 1.

## What is being built

The PoC runs groups of interactive Claude Code, Codex, and Antigravity `agy` sessions in git worktrees inside Apple Containers VMs, with a host daemon, embedded NATS messaging and shared context, and a shared web and Tauri UI for terminals, operator shells, files, git changes, and remote access over Tailscale. Shared authentication, targeting one login per harness across all groups, is a required research answer and implementation outcome; the starting scope is in `design-sketch/README.md`, `design-sketch/01-overview.md`, `design-sketch/06-containers.md`, `design-sketch/07-ui.md`, and `design-sketch/08-remote-access.md`.

## Names

The sketch's placeholders become the real names for the PoC, so nothing has to be renamed later:

- `agentd`: the host daemon. In phase 2 it is only the bootstrap provisioner plus the embedded NATS broker plus a SQLite registry with the host-tmux backend. It grows into the full daemon in phase 5. There is no separate throwaway `provision` tool; the sketch's `provision spawn|list|capture|nudge|stop` commands are `agentd`'s first API, exposed through `agentctl`.
- `agentctl`: one CLI for agents and the operator (join, send, receive, ack, status, roster, memory, claim; and in operator mode: group and session management).
- `agentd-guest`: the optional in-VM supervisor, only if experiments show shpool alone is not enough.
- The build group (the coordinator's own workers on the host) is a group named `build`.

## Repository layout

This refines `design-sketch/11-repo-workflow-and-tooling.md`.

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

## GitHub workflow

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

| View | Layout and selection |
| --- | --- |
| Default | Board by Status |
| Phase | Table grouped by Phase |
| Ready to dispatch | Table, Status = Ready, sorted by Priority |
| Blocked | Table, Status = Blocked |
| Experiments | Table, Area = experiment |

### Issues

One issue per work item. Every issue carries: goal (one paragraph), context and links (docs pages, sketch pages, research), acceptance criteria (checkboxes), evidence required (what raw material the worker must produce), docs impact (what Codex has to write or update when this lands), and out of scope. Labels: `area/<area>`, `type/<feature|experiment|research|docs|tooling|bug|decision>`, `phase/<n>`, `harness/<claude|codex|agy|any>`, `blocked`, `needs-operator`. A `decision` issue records a design decision and is closed by the decision record in the docs site.

### Branches and worktrees

Branch names are `<type>/<issue>-<slug>`, where type is one of `feat`, `fix`, `docs`, `exp`, `chore`, `research`, for example `feat/12-bus-consumer`. Every worker gets its own branch and its own worktree at `.worktrees/<type>-<issue>-<slug>/`. Workers never share a checkout and never work on `main`.

### Commits

Conventional Commits: `type(scope): imperative subject`, a body that explains why, and trailers `Refs: #<issue>` and `Assisted-by: <harness> <version>` (kernel-style attribution, which is what the vale-ai-tells commit rules ask for instead of marketing trailers). Commit messages are linted with the `ai-tells-commits` Vale style through a prek `commit-msg` hook. `--no-verify` is forbidden except for the throwaway work-in-progress commit described in the worktree rules (see Standing rules for workers).

Example commit message (illustrative, not a completed work item):

```text
feat(bus): add a durable consumer

Keep messages available until the worker acknowledges them.

Refs: #12
Assisted-by: Codex CLI 0.157.1
```

### Pull requests

One PR per issue, small. Title is the conventional subject. Body: what, why, evidence (links to `experiments/` output or test runs), docs (what Codex wrote or what still needs writing), and a checklist (CI green, docs updated or issue filed, no secrets, evidence committed). Squash merge with a linear history. Review policy: the coordinator reviews every PR; where practical a worker from a different harness than the author reviews first (a Claude worker reviews Codex PRs and the reverse), and the coordinator merges after review and green CI. The operator merges anything that changes security policy, credentials handling, egress rules, or anything installed outside the repository. Branch protection on `main` once CI exists in phase 1: PR required, CI required, no force pushes.

### CI

GitHub Actions running the same mise tasks workers run locally: `mise run check` (every linter and formatter check plus tests) on pull requests and on pushes to `main`, and `mise run docs:build` for the docs site. Jobs run on `ubuntu-latest` except where something needs macOS (Go code that links against Apple frameworks, the Tauri build, anything touching Apple Containers), which runs on `macos-latest`. mise itself is installed through the official action and cached.

### Push discipline

Workers push their branch whenever they report status on the bus and always before saying anything is done. Nothing that matters lives only on a worker's disk. The coordinator's `capture` of a pane is for diagnosis, never a substitute for a pushed branch.

## The build group

This refines `design-sketch/10-bootstrap-orchestration.md`. Fable coordinates, dispatches, reviews, and merges; workers implement.

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
| `build/agy-research` | `agy` | Research and experiments; implementation only if it proves capable |

Workers hand Codex their raw material (evidence files, notes, answers) over the bus or as files in their worktree, and `codex-docs` writes the prose. The coordinator's own subagents remain available for short, self-contained tasks (a search, a review pass) and for improving `agentd` while a provisioned worker is blocked on it.

## Concurrency

| Harness | Interactive workers | Notes |
| --- | --- | --- |
| Claude Code | 3 | Plus the coordinator's session and its subagents (at most 4 subagents at once) |
| Codex | 2 | One is always the docs writer |
| `agy` | 1 | Raised only if it proves useful for implementation |

Six interactive workers in total. The limits are a starting point set with the subscriptions' rate limits in mind (Claude Max, Codex Pro, Google AI Ultra; none of the three publishes concurrent-session limits that were checked for this plan) and are renegotiated at the phase 2 checkpoint once the group is real.

## Permission modes

Workers must run unattended. The coordinator never types approvals into worker terminals; failures or blocked workers go to the operator. These are proposed launch modes, not proof that every harness refuses every out-of-sandbox action. Exact CLI and configuration facts below come from `experiments/00-system-assessment/permission-facts.md`; observed behavior and launch proposals come from the coordinator's decisions and `experiments/00-system-assessment/evidence.md`. The commands show harness arguments; the provisioner launches processes through `mise exec` or `mise run`.

### Claude Code

```text
claude --permission-mode auto --settings <per-worker settings file>
```

The proposed settings are `sandbox.enabled: true`, `sandbox.autoAllowBashIfSandboxed: true`, and `sandbox.network.allowLocalBinding: true`. Evidence label: observed in the imported research. The settings file `agent-peering-tests/.claude/settings.local.json` places `enabled`, `autoAllowBashIfSandboxed`, `excludedCommands`, and `network.allowedDomains` under a top-level `sandbox` key; the research design documents cite `sandbox.network.allowLocalBinding` as the sibling of `allowedDomains`. Only `allowLocalBinding` needs user scope because Claude Code accepts it only there, and that change needs operator approval. The permission facts verify `--settings <file-or-json>` and `--setting-sources user,project,local`. Allowed proxy domains are the model APIs, GitHub, and package registries required by mise; the exact domain list is decided in phase 2 when the first worker is launched.

`auto` is a verified permission-mode value in the recorded release. The coordinator reports that its classifier auto-approves safe actions and observed it refuse an unsandboxed `codex queue` call in the research. This is observed behavior, not a guarantee that routine work will always pass. Proposed fallback: `--permission-mode acceptEdits` with an operator-controlled per-worker allowlist for `mise run *`, `git *`, `gh *`, and `agentctl *`. That fallback is not established as prompt-free. Claude subagents in phases 0 and 1 use the same proposed settings.

The provisioner writes each worker's settings file outside the worktree and passes it with `--settings`, including status and inbox hooks. This is operator-controlled configuration, not project-scope configuration. The research rule disallows project-scope configuration in a shared worktree because other agents can edit it; it does not conflict with this per-worker injection.

### Codex

```text
codex -s workspace-write -a never
```

```toml
[sandbox_workspace_write]
network_access = true
```

`-a` is `--ask-for-approval`; the verified interactive CLI values are `on-request` and `never`. With `never`, sandbox-permitted work proceeds without approval prompts and execution failures return to the model. Commands needing greater access fail and are reported over the bus. The proposed network setting is the research-confirmed loopback route, but opens all outbound network for tool calls, a known widening the coordinator proposes for bootstrap on the operator's machine.

The narrower candidate is `[network] allow_local_binding = true`, verified in source but untested here. It permits local servers and direct host-loopback connections, skips additional proxy private-network checks, and retains proxy domain rules. Phase 2 tests it as a replacement. It is not a valid `[sandbox_workspace_write]` key; that table accepts only `writable_roots`, `network_access`, `exclude_tmpdir_env_var`, and `exclude_slash_tmp`.

Do not use `--approve-for-me` (alias `--not-so-yolo`): it expands to `approvals_reviewer="auto_review"`, `approval_policy="on-request"`, and `sandbox_mode="workspace-write"`. The operator's `~/.codex/config.toml` already sets `approvals_reviewer = "auto_review"`, and the permission facts say core code can force that reviewer for some models. With `approval_policy = "never"` (`-a never` interactively or `-c 'approval_policy="never"'` for `codex exec`), Codex raises no approval requests, so the configured reviewer never runs; sandbox denials return to the model as failures. Phase 2 verifies this behavior with a deliberate sandbox denial before the first Codex worker is trusted unattended.

For phases 0 and 1, the coordinator's specified invocation is:

```text
codex exec -s workspace-write -c 'approval_policy="never"' -C <worktree> --add-dir <repo>/.git -o <last-message-file>
```

The brief is supplied on stdin. Recorded `exec` help has no `-a` approval-policy flag, so the invocation sets the policy through `-c`; blocked operations fail and appear in output for escalation.

The first draft could not be committed because the worktree's git metadata lives in the main repository's `.git` directory, outside the workspace-write sandbox. A Codex worker in `.worktrees/<name>/` needs the repository's common git directory as an extra writable root (`--add-dir <repo>/.git`, or `writable_roots` in `[sandbox_workspace_write]`), or it cannot stage or commit. Phase 2 checks the writable roots needed to stage and commit for Claude Code and `agy` workers as well, before the first launch.

The environment-policy caveat applies to both launch forms. The operator sets `shell_environment_policy.inherit = "core"`; injected group, worker, NATS URL, and credentials-path variables will not reach tool shells without `-c shell_environment_policy.inherit=all` or explicit `shell_environment_policy.set` entries. Default exclusions still remove names matching `*KEY*`, `*SECRET*`, and `*TOKEN*`. Pass credentials as a file path, for example `AGENTCTL_CREDS_FILE`, rather than secret contents in the environment or argv. Three existing `CLAUDE_*` variables in the `set` table also reach Codex shells and must not be interpreted as proof of a Claude session. Persistent changes to `~/.codex/config.toml` and user-scope hooks need operator approval; per-launch overrides do not themselves edit that file.

The permission-facts search marked the cloned `docs/config.md`, `docs/sandbox.md`, and `docs/example-config.md` contents NOT FOUND beyond documentation-site stubs. They supply no additional verified flags.

### Antigravity (`agy`)

```text
agy --sandbox --dangerously-skip-permissions --prompt-interactive "<pointer to brief>"
```

Verified help says `--dangerously-skip-permissions` auto-approves all tool permission requests and `--sandbox` enables terminal restrictions, with no sub-options. The coordinator's proposal relies on those sandbox restrictions as the boundary; exact refused operations are unverified. The conservative alternative is `--sandbox --mode accept-edits`, which the decisions say still prompts for commands. `--mode` accepts only `accept-edits` or `plan`, with no verified `auto` or bypass mode value. `--prompt-interactive` is verified in the assessment help output. Phase 2 tests initial prompts, unattended operation, and loopback reachability; the operator picks the mode and concurrency stays at one.

`agy help sandbox` and `agy help mode` were NOT FOUND as subcommands. Additional sandbox or mode flags are unverified. The user file `~/.gemini/antigravity-cli/settings.json` has keys `allowNonWorkspaceAccess`, `enableTerminalSandbox`, `model`, `permissions`, `toolPermission`, and `trustedWorkspaces`, but their values were not read. No values are prescribed here. Any changes to that file or user-scope status and inbox hooks need operator approval with exact content.

## What the system assessment established

The recorded facts below are from `experiments/00-system-assessment/evidence.md` and `experiments/00-system-assessment/versions.md`, assessed on 2026-09-26. They are a snapshot, not new runtime tests performed for this plan.

- The Apple M5 MacBook Air has 32 GB RAM and 466 GB free. Memory determines group-VM capacity; phase 3 measures it.
- Apple Containers is installed and its API server is already running under launchd, with zero containers and images. The handoff expected the service to be stopped, but no system change is needed to start it. The operator is still told before the first container experiment because creating VMs and images is the operator's call.
- Claude Code is authenticated through claude.ai with Max, and Codex through ChatGPT. The decisions call all three authenticated, but `agy` has only token-file-existence evidence and no auth-status command; working authentication is inferred. `gh` is logged in as `tbhb` over HTTPS with `project` scope.
- All tools pinned by `mise.toml` are installed; `mise ls --missing` was empty. `mise install` was not run. Non-interactive shells lack mise shims: `uv`, `prek`, `rumdl`, `vale`, `tombi`, `python3`, and `rustc` resolve to Homebrew, and `ryl` is missing on PATH. Every provisioned process and CI step must run through mise.
- Missing tools include `nats-server`, `nats`, shpool, ruff (provided through uv), fish, websocat, podman, colima, lima, qemu, and direnv. Docker CLI is present; daemon status was not checked.
- Tailscale runs on `tbhb.github`, with MagicDNS suffix `ibex-paradise.ts.net` and no serve or funnel configuration. Scripts must use `/Applications/Tailscale.app/Contents/MacOS/Tailscale`; `tailscale` is a zsh alias.
- The application firewall is off, SIP is on, and Rosetta is installed.
- At assessment time, Project 9 had only default fields, zero items, and one board view. The evidence includes Codex `exec` and `agy` help.

| Component | Recorded version |
| --- | --- |
| macOS | 26.5.1 |
| Apple container | 1.4.1 |
| Claude Code | 2.1.283 |
| Codex CLI | 0.157.1 |
| agy | 1.2.11 |
| tmux | 3.7b |
| mise | 2026.8.6 |
| Go | 1.27.1 |
| Node | 24.21.0 |
| Python | 3.14.6 |
| uv | 0.12.10 |
| Rust through rustup | 1.98.1 |
| Tailscale | 1.102.4 |
| gh | 2.100.0 |

## Dependency sources

Every third-party project the design leans on is cloned under `~/Code/github.com/<owner>/<repo>`, with commits recorded in `experiments/00-system-assessment/dependency-clones.md`; new dependencies must follow the same rule. The manifest records 23 clones or updates, with nothing built, installed, or run. The next two phases read the following sources most. Nearest tags identify source history, not installed runtime versions.

| Source | HEAD SHA | Nearest tag |
| --- | --- | --- |
| `nats-io/nats-server` | `3e8ddaa7fcdf2c6a0688f8872ca465eab08f1221` | `v2.15.0` |
| `nats-io/nats.go` | `5adc9d5d34ce8e3b7b8b002c5bd502a8b7a323d3` | `v1.54.0` |
| `apple/container` | `4a7d8615241b8ddecfd3bf225cd7c44f4b2ccf7c` | `1.4.1` |
| `apple/containerization` | `bc994b88df46207fad7775b0eabc51947e315881` | `0.47.0` |
| `shell-pool/shpool` | `3c41df9a610428b6c1766d78d36d3fefd5685c3b` | `v0.11.5` |
| `withastro/starlight` | `3ec633b8c50d3e1a6d67cae7dc4c50f80101ea41` | `@astrojs/starlight@0.42.4` |
| `openai/codex` | `a6bd19261c30ce0a0225fe90e646822d29916f11` | `voice-cygwin-108b38cf67cbb731` |
| `anthropics/sandbox-runtime` | `ddbeb74711c4097014ef3056791efa83f553116c` | `v0.0.77` |
| `anthropics/claude-code` | `7779afb12e3635f46f56ec823979d68350ae000b` | `v2.1.283` |

## Phases

These refine `design-sketch/10-bootstrap-orchestration.md`, `design-sketch/11-repo-workflow-and-tooling.md`, and `design-sketch/12-experiments-and-open-questions.md`. Each phase ends with an operator checkpoint and waits for a go-ahead. Check the original research folders for newer material at each phase until retirement.

### Phase 0: orientation and assessment

Done when the operator approves this plan, the concurrency, and the permission modes. Outputs: `experiments/00-system-assessment/` (raw evidence from the assessment subagent), the dependency clones under `~/Code/github.com/`, `PLAN.md`, and `reports/phase-0-checkpoint.md`. The scaffold landed directly on `main` because there was nothing to review against. Everything after it, including the assessment evidence and these two documents, goes through a pull request from `docs/phase-0-plan` that the coordinator reviews and merges after the operator's review. There is no CI yet, so the phase 0 merge gate is coordinator review only. Checkpoint: the operator approves the plan, concurrency limits, and permission modes.

### Phase 1: repository foundation

Work items, in dispatch order, each a subagent in its own worktree:

1. **Tooling** (`chore`): extend `.gitignore`; extend `mise.toml` (pin Python 3.14, pnpm, Biome, keep the operator's pins); configuration for ruff, pytest, Biome, Vale with vale-ai-tells (installed by release URL per its README, with `ai-tells` and `ai-tells-commits`), rumdl, ryl, tombi; a mise task per tool, `check` and `fmt` aggregate tasks; prek hooks (extend `prek.toml`, add the commit-msg lint); documentation linting covers every Markdown file except `research/imported/`. The assessment established that every pin is installed without running `mise install`; this item runs `mise install` after changing the pins and records the result, satisfying the handoff.
2. **Skeleton** (`chore`): `go.mod`, `cmd/agentd` and `cmd/agentctl` that build and print a version, `internal/` layout, `pnpm-workspace.yaml` with empty `apps/` and `packages/` placeholders, `schema/`, `experiments/`, `images/agent/` with a README placeholder (content by Codex), `tests/` with one passing test, `.worktrees/` ignored.
3. **CI** (`chore`): the workflows in GitHub workflow, running against the tooling from item 1. Branch protection after the first green run.
4. **Docs site** (`chore`): Astro Starlight in `docs/` with Mermaid rendering at build time (an integration or remark plugin the worker evaluates from the cloned starlight source and records), the sidebar structure (Project, Workflow, Research, Experiments, Design, Decisions, Guides), `mise run docs:dev` and `docs:build`. Pages are placeholders until Codex writes them.
5. **Research import** (`research`): copy `~/Code/github.com/tbhb/agent-peering-tests` and `~/Code/github.com/tbhb/agent-session-tests` verbatim into `research/imported/<folder>/`, excluding `__pycache__`, `.DS_Store`, `.obsidian/`, `codex/.venv/` (recording its `requirements.txt` and the installed package list), and `CLAUDE_CODE_SESSION_MANAGEMENT.html` plus its `_files/` directory (a Quarto rendering of the Markdown report beside it; the importer confirms this by comparing headings). Scan every file for secrets, tokens, credentials, and personal data (the `.claude/settings.local.json` and `.codex/config.toml` in the peering folder, raw terminal captures, logs, `results.jsonl`, and the Codex evidence directory are the likely places), redact or hold back anything sensitive, and list it. Commit `research/imported/MANIFEST.md` with every source file's SHA-256, size, and destination or exclusion reason. Confirm the repository's visibility with the operator before pushing raw evidence.
6. **Worker instructions and docs pages** (`docs`, Codex): `AGENTS.md` and `CLAUDE.md` (workflow, mise, worktree and stash rules, Markdown rules, Codex-writes-docs rule, bus usage once it exists); docs pages for the workflow, the tooling, the repository layout, and the project history; move `PLAN.md` and the phase 0 report into the docs site.
7. **Project and issues** (`workflow`): configure the Project fields and views from GitHub workflow, create labels, file the phase 2 and phase 3 issues from this plan, and put them in the Project.

Checkpoint: the foundation is merged, the import and its manifest are merged, the Project reflects the plan.

### Phase 2: bootstrap orchestration

Build `agentd` v0 and `agentctl` with subagents, then switch to provisioned workers as soon as one of each harness can be spawned and reached over the bus. Work items:

1. Embedded NATS server in `agentd` with JetStream, one account per group, per-agent credentials (nkeys or user JWTs) with publish permissions limited to subjects ending in the agent's own name, the subject and stream layout from `design-sketch/04-messaging-and-shared-context.md`, and a `build` group.
2. `agentctl join|send|receive|ack|status|roster` against it, with compact machine-readable output.
3. The registry (SQLite) and the host-tmux backend: `spawn`, `list`, `capture`, `nudge`, `stop`, and group start, stop, and status, creating the worktree and branch, minting credentials, and starting the harness in a tmux window with a brief file. The launch recipe per harness includes the writable roots its worktree needs to stage and commit.
4. Shared context: key-value buckets for status, roster, claims (create-if-absent plus compare-and-set), decisions, and brief; the memory tiers as files (`.agents/memory/` checked in, `.agents/local/` ignored).
5. Hooks per harness for status and inbox checks: Claude Code uses the operator-controlled per-worker settings file outside the worktree, passed with `--settings`; user-scope hooks for other harnesses need operator approval.
6. Experiments that gate the design: host loopback settings for each harness (which Codex setting, whether `agy` reaches loopback), initial-prompt behavior for each harness, and waiter semantics across compaction and restart.
7. How the coordinator itself uses the bus: `agentctl` from the coordinator's shell, with a background `receive` as its wake mechanism.

Checkpoint: one worker of each harness receives a brief, exchanges messages with the coordinator and each other, and reports status. Concurrency renegotiated.

### Phase 3: research and experiments

Codex workers synthesize the imported research into the docs site's Research section. Provisioned workers run the experiments from `design-sketch/12-experiments-and-open-questions.md`, critical path first: harnesses in a Linux arm64 Apple Containers VM, shared authentication per harness, `container exec -it` fidelity, shpool in the guest, worktree mounts, embedded NATS behavior, NATS topology and reachability from a VM, NATS credentials and identity, waiter semantics, wake mechanisms. Then the rest. The handoff expected the Apple Containers service to be stopped, but the assessment found it running. No system change is needed to start it. The operator is still told before the first container experiment because creating VMs and images is the operator's call, and any system change requires approval. The daemon language, protocol schema format, and Tailscale integration are decided here with evidence. Shared authentication must receive a supported approach per harness or a documented limitation and the closest workable alternative for the operator. Re-verify version-sensitive imported findings or mark them stale.

Checkpoint: results and proposed decisions go to the operator.

### Phase 4: design in the docs site

Codex turns the surviving sketch plus results into the Design section with decision records. Retire `design-sketch/` in one commit that points to replacement pages, and move `FABLE_HANDOFF.md` into the docs site as history or delete it in that change, as required by the handoff. Check for newly added research before verifying the manifest; import new material first. Verify the import against the originals with the manifest, update every reference, get explicit approval, delete the original folders, record the retirement.

Checkpoint: operator reviews the design docs and research synthesis, approves the retirement.

### Phase 5: build the PoC

Vertical slices, each demonstrable: daemon plus registry plus local backend plus one xterm.js terminal in the web UI; the Apple Containers backend with shpool, operator shells, and shared auth; the bus inside groups plus the message timeline and composer; the file browser; the Tauri app; Tailscale; egress control and the rest of the security policy. The build group appears in the PoC UI once the daemon hosts the host-tmux backend.

Each vertical slice is demonstrated to the operator as it lands. Checkpoint: all seven slices are demonstrable together on this machine, the Project shows no open phase 5 items, and the docs describe what was built.

### Phase 6: end-to-end verification

Playwright tests (fake backend for most flows, Apple Containers for the full demo), the demo script written by Codex, known gaps written up and filed.

Checkpoint: the operator runs the demo.

## Departures from the design sketch

- The provisioner is `agentd` from day one rather than a separate tool; the sketch already wanted the provisioner's operations to become daemon API calls.
- Worktrees live in `.worktrees/` inside the repository rather than outside it, as settled from the open location question in `design-sketch/11-repo-workflow-and-tooling.md`.
- Experiment directories are numbered.
- The `uv init` package is kept as a shared helper library rather than deleted.
- The handoff refers to a `WORK_DESIGN.md` in the peering research; no such file exists. The messaging and shared-memory designs exist only as the bullet lists in `OPEN_ITEMS.md`, which `design-sketch/04-messaging-and-shared-context.md` already absorbed. Nothing is missing from the import as a result, but the phase 3 synthesis should say so.

## Standing rules for workers

These come from the handoff and the tbhb workspace and go into `AGENTS.md` and `CLAUDE.md` in phase 1:

- mise for everything; no global installs; run tasks, never tools directly.
- Latest source for dependencies: clone or pull into `~/Code/github.com/<owner>/<repo>` and record the commit read.
- Evidence over assumption, with evidence labels: verified, observed, help-text, schema, documented, inference, untested.
- Only Codex writes documentation and reports. Code comments and docstrings stay with whoever writes the code.
- Diagrams: Mermaid or hand-drawn SVG.
- Markdown: one line per paragraph, sentence case headings; `guard-markdown` enforces the first.
- Everything committed and pushed. Parallel work in worktrees, one per worker.
- Shared stash stack: never a bare `git stash pop`; prefer `git rebase --autostash` or a throwaway `wip` commit (the only sanctioned `--no-verify`), unwound with `git reset --soft HEAD~1`.
- Sandbox escapes and system changes go to the operator.

## Open questions for the operator

- Approve the plan, concurrency table, and permission modes as recommended by the coordinator, including Codex's outbound-network widening for bootstrap and the two user-scope changes: Claude Code `allowLocalBinding` and Codex `network_access`.
- Choose the `agy` unattended mode: the coordinator recommends `--sandbox --dangerously-skip-permissions`, with `--sandbox --mode accept-edits` as the alternative. The phase 2 initial-prompt experiment records how each behaves.
- Confirm that pushing the scanned, redacted raw research evidence to the private repository is acceptable for the phase 1 import, as the coordinator recommends after scan, redaction or holdback, and manifest review.
- The coordinator recommends enabling branch protection on `main` itself in phase 1 after the first green CI run. Would the operator rather do it?
