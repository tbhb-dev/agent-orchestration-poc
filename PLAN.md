# Project plan

## Status

Written 2026-09-26 for the phase 0 checkpoint, this plan records the coordinator's decisions, subject to the requirements in `FABLE_HANDOFF.md`. It awaits the operator's approval of the revised plan and model and effort assignments. It moves into the docs site in phase 1.

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
├── HANDOFF.md                 # living coordinator handoff, regenerated at every rollover and checkpoint
└── reports/                   # checkpoint reports, until the docs site absorbs them in phase 1
    └── devlog/                # dated devlog entries until the docs site exists
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

What the phase 1 worker can script, per `experiments/00-system-assessment/github-projects-research.md`: custom fields (single-select options included), replacing the built-in Status options, creating views with a layout, a filter, and visible fields, adding items and setting their fields, labels, and issue forms that auto-add to the project. What stays in the UI: the board column field, grouping, sorting, and the auto-add and auto-archive workflows; the worker leaves the operator a short list of those clicks. Issue types are organization-only, so the `type/*` labels carry that meaning here; sub-issues work and are used for splitting large items.

### Issues

One issue per work item. Every issue carries: goal (one paragraph), context and links (docs pages, sketch pages, research), acceptance criteria (checkboxes), evidence required (what raw material the worker must produce), docs impact (what Codex has to write or update when this lands), and out of scope. Labels: `area/<area>`, `type/<feature|experiment|research|docs|tooling|process|bug|decision>`, `phase/<n>`, `harness/<claude|codex|agy|any>`, `blocked`, `needs-operator`. A `decision` issue records a design decision and is closed by the decision record in the docs site.

### Branches and worktrees

Branch names are `<type>/<issue>-<slug>`, where type is one of `feat`, `fix`, `docs`, `exp`, `chore`, `research`, for example `feat/12-bus-consumer`. Every worker gets its own branch and its own worktree at `.worktrees/<type>-<issue>-<slug>/`. Workers never share a checkout and never work on `main`.

### Commits

Conventional Commits: `type(scope): imperative subject`, a body that explains why, and a `Refs: #<issue>` trailer. No attribution or co-author trailers in commits or PR descriptions: the Project's Worker field and the PR body's evidence section record which harness and model did the work. Commit messages are linted with the `ai-tells-commits` Vale style through a prek `commit-msg` hook. `--no-verify` is forbidden except for the throwaway work-in-progress commit described in the worktree rules (see Standing rules for workers).

Example commit message (illustrative, not a completed work item):

```text
feat(bus): add a durable consumer

Keep messages available until the worker acknowledges them.

Refs: #12
```

### Pull requests

One PR per issue, small. Title is the conventional subject. Body: what, why, evidence (links to `experiments/` output or test runs), docs (what Codex wrote or what still needs writing), and a checklist (CI green, docs updated or issue filed, no secrets, evidence committed). Squash merge only: the repository settings allow squash merges and disable merge commits and rebase merges (set by the coordinator on 2026-09-26 at the operator's direction), the squash commit takes the PR title as its subject and the PR body as its body, so the PR body is written to the commit convention, and head branches are deleted on merge (the provisioner removes the matching worktree). Review policy: the coordinator reviews every PR; where practical a worker from a different harness than the author reviews first (a Claude worker reviews Codex PRs and the reverse), and the coordinator merges after review and green CI. The operator merges anything that changes security policy, credentials handling, egress rules, or anything installed outside the repository. Branch protection on `main` once CI exists in phase 1, as a repository ruleset (require a pull request, require the CI job by name, block force pushes and deletion), enabled by the coordinator. Rulesets and classic branch protection on a private personal repository both need GitHub Pro, and the API does not expose the account plan, so the operator confirms the plan first; without Pro the merge gate stays coordinator review plus CI status, unenforced by GitHub.

### CI

GitHub Actions running the same mise tasks workers run locally: `mise run check` (every linter and formatter check plus tests) on pull requests and on pushes to `main`, and `mise run docs:build` for the docs site. Jobs run on `ubuntu-latest` except where something needs macOS (Go code that links against Apple frameworks, the Tauri build, anything touching Apple Containers), which runs on `macos-latest`. mise itself is installed through the official action and cached.

### Push discipline

Workers push their branch whenever they report status on the bus and always before saying anything is done. Nothing that matters lives only on a worker's disk. The coordinator's `capture` of a pane is for diagnosis, never a substitute for a pushed branch. The operator permits committing research evidence; when in doubt, commit it after the required secret scan and redaction or holdback.

## Retrospectives, devlog, and mechanical checks

- **Cadence.** A retrospective at every phase checkpoint, and a lightweight one after every ten merged pull requests during a phase. The coordinator dispatches it; it never skips one because the phase went well.
- **Who runs it.** A worker agent (a Claude Code reviewer or the Codex docs writer, alternating so both harnesses' views appear) reads the inputs and produces the raw findings; Codex writes the retro document.
- **Inputs.** The bus log for the period (message volume, unanswered questions, time-to-first-response), merged and closed PRs with review turnaround, CI failures and their causes, hook denials and sandbox failures reported by workers, worker restarts and blocked states, Project items that moved to Blocked, and the coordinator's own notes on where it had to intervene.
- **Output.** A retro page in the docs site under a Retros section (`docs/src/content/docs/retros/YYYY-MM-DD-<phase-or-count>.md`) with: what went well, what cost time, what broke, decisions, and action items. Every action item becomes an issue labeled `type/tooling` or `type/process` and goes into the Project. Until the docs site exists, retros live in `reports/`.
- **The mechanical-checks rule.** Every retro proposes at least one new mechanical check (a lint rule, a prek hook, a CI job, a guard script, a test, or a bus-side validation) or states why none applies this time. A check is preferred over an instruction in `AGENTS.md` whenever the failure it catches is detectable by a program.
- **Standing candidates for phase 1 tooling** (the first batch, added to the phase 1 tooling item): secret scanning in prek (gitleaks or an equivalent) so the research import and every later commit are scanned automatically; `guard-markdown` as a mise task and a CI job; the `ai-tells-commits` commit-message lint through prek; a script that checks every `experiments/<NN-slug>/` has a `README.md`, an `evidence/` directory, and a `versions.md`; a CI job that fails if anything under `research/imported/` changes after the import lands; a check that PR bodies contain an evidence link for `feat` and `exp` changes (a GitHub Actions job reading the PR body); a Mermaid CLI check over every fenced `mermaid` block.
- **Standing candidates for later** (tracked as issues, not built yet): a bus-side schema check on message bodies; a hook that rejects worker commits without `Refs:`; a mise task that reports dependency-clone staleness against the recorded SHAs; Playwright smoke tests on every PR once the UI exists; a CI job or retro script warning when merged PRs have no devlog entry in the following day.
- **Promoted to phase 1 by a phase 0 failure:** a silent-worker timer. On 2026-09-26 a research subagent finished its sub-reports and then never assembled them; the coordinator waited nearly two hours for a notification that never came. Until the bus exists, the coordinator uses a scheduled check-in (the harness's wakeup or monitor facility) on every dispatch longer than fifteen minutes; from phase 2 the bus status bucket carries a last-seen timestamp per worker and `agentd` flags anything silent past a threshold.

### Devlog

- **Who and when.** `build/codex-docs` writes it once provisioned; until then the coordinator runs `codex exec` for it. At least one entry per working day that had merged pull requests, experiment results, or a decision, and one entry at every checkpoint. The coordinator hands Codex the inputs at the end of each such day: merged PRs, bus highlights, experiment findings, decisions, blockers, and what is next.
- **Where.** In the docs site through the `starlight-blog` plugin (`HiDeoo/starlight-blog`), which the phase 1 docs-site worker evaluates from a clone under `~/Code/github.com/HiDeoo/starlight-blog` at a recorded commit and wires up with a `Devlog` entry in the sidebar; if the plugin does not fit the pinned Starlight version, dated pages under a `devlog/` section are the fallback. Until the site exists, entries accumulate under `reports/devlog/YYYY-MM-DD.md` and move into the site in phase 1 item 6.
- **What an entry contains.** Date and phase in frontmatter, tags by area; then: what landed (PR links), decisions and their evidence, experiments run and what they showed, problems and how they were resolved, what is next. Written for the operator and for future readers of the project, not for workers; no padding, no restated plans.
- **The first entry** covers phase 0 retroactively and is written when the phase 1 docs site item lands.
- **Mechanical check, later candidate:** a CI job or retro script that warns when merged PRs exist with no devlog entry in the following day, included in the standing candidates above.

## Coordinator session rollover

- **Durable state before anything else.** The coordinator keeps nothing that matters only in its context window. Decisions go to the repository (the plan, issues, decision records, and from phase 2 the group's decisions bucket on the bus); working facts and operator preferences go to the coordinator's memory directory (`~/.claude/projects/<repo-slug>/memory/`, which every Claude Code session in this repository loads); in-flight state goes to a living handoff document. Workers are independent processes, so a coordinator rollover never stops them.
- **`HANDOFF.md`** at the repository root (moved into the docs site in phase 1 as the project's current-state page) is regenerated by Codex from the coordinator's inputs at every rollover and at every checkpoint. It holds: current phase and what is awaiting the operator, open PRs and their state, the worker roster with each worker's task and last known status, decisions made since the last checkpoint, gotchas discovered (the kind of thing in the coordinator's memory directory), the next three actions, the previous coordinator session id, and the date. `FABLE_HANDOFF.md` stays as the original operator handoff and is retired in phase 4 as planned.
- **Compaction triggers.** Compact at boundaries: after a checkpoint is approved, after a batch of dispatches is out and acknowledged, after a large reading phase. Never in the middle of reviewing a document or a PR. Before a deliberate compaction the coordinator writes any new durable facts to memory and, if more than a handful of things changed, has Codex refresh `HANDOFF.md`. Automatic compaction needs no ceremony once those habits hold, because nothing is lost that was not already written down.
- **Handoff triggers.** Start a fresh Fable session at every phase checkpoint once the operator approves it (the clean cut, and the moment `HANDOFF.md` is freshest), on the second compaction within one phase, when the coordinator shows degraded recall (asking about settled decisions, re-deriving established facts, contradicting the plan), or when the operator wants one. The operator can also ask for a rollover at any time.

Handoff procedure:

1. Finish or park in-flight reviews; dispatched workers keep running.
2. Write new facts to memory.
3. Have Codex regenerate `HANDOFF.md` from the coordinator's inputs, review it, commit and push it (on `main` for a checkpoint handoff, on the current branch otherwise).
4. Record the session id in `HANDOFF.md`.
5. The operator starts a new session in the repository with `@HANDOFF.md`.
6. The new coordinator verifies before acting: `git status` and open PRs, the Project board, the bus roster and status bucket once they exist, and the memory index; it reports any discrepancy with `HANDOFF.md` to the operator instead of trusting the document.

- **Resume as the fallback.** `claude --resume <session id>` brings back the previous transcript when a new session finds `HANDOFF.md` insufficient, which is why the id is recorded. A resumed session is a stopgap for recovering context, not the normal path.
- **The coordinator owns the timing.** The operator monitors only this one interactive session and asked (2026-09-26) that the coordinator be proactive about compaction and handoff. So the coordinator, not the operator, watches context: every checkpoint message and every message that closes a heavy stretch of reading or dispatching ends with a one-line context recommendation (continue, compact after a named step, or hand off now), and the coordinator never recommends compacting while its judgment is still needed on in-flight results. The operator can still compact or roll over whenever they like. The phase retros review whether rollovers lost anything and add checks or handoff fields accordingly.
- **The coordinator's brief files survive rollover.** The scratchpad directory is per session and disappears with it, so anything a future coordinator needs from it (the decisions brief, research outputs) is committed to the repository before a handoff: research outputs under `experiments/`, the coordinator's decision briefs under `reports/inputs/`.

## The build group

This refines `design-sketch/10-bootstrap-orchestration.md`. Fable coordinates, dispatches, reviews, and merges; workers implement.

### Before the provisioner exists (phases 0 and 1)

Workers are the coordinator's own Claude subagents, each in its own worktree (the Agent tool's worktree isolation), running three to four at a time. Codex runs non-interactively from the coordinator's shell (`codex exec`) inside a worktree for every document; Codex commits its own work on its branch. The coordinator reviews and merges. The operator is asked before anything is installed or changed outside the repository.

### Once `agentd` can spawn workers (phase 2 onward)

One tmux session named `build`, one window per worker, each worker in its own worktree with a brief file. Standing roster:

| Worker | Harness | Role | Model | Effort |
| --- | --- | --- | --- | --- |
| `build/codex-docs` | Codex | Writes every document and report. Always present. | `gpt-6-sol` | medium |
| `build/codex-impl` | Codex | Implementer | `gpt-6-sol` | medium |
| `build/claude-impl-1` | Claude Code | Implementer | `claude-opus-5-5` | medium |
| `build/claude-impl-2` | Claude Code | Implementer or experimenter | `claude-opus-5-5` | medium |
| `build/claude-review` | Claude Code | Reviews Codex PRs; runs experiments when idle | `claude-opus-5-5` | high; medium for idle experiments |
| `build/codex-review` | Codex | Reviews Claude Code PRs and runs `codex exec review`; experiments when idle | `gpt-6-astra` | low |
| `build/agy-research` | `agy` | Bounded research: doc reading, inventories, lookups with a defined output shape | `gemini-3.1-pro-high` | high (variant) |
| `build/agy-probe` | `agy` | Runs probe scripts that another worker wrote and collects the evidence; does not design experiments | `gemini-3.8-flash-high` | high (variant) |
| `build/agy-impl` | `agy` | Probationary implementer for small, fully specified items; keeps the seat only if its PRs pass review at a rate comparable to the others | `gemini-3.1-pro-high` | high (variant) |

Workers hand Codex their raw material (evidence files, notes, answers) over the bus or as files in their worktree, and `codex-docs` writes the prose. The coordinator's own subagents remain available for short, self-contained tasks (a search, a review pass) and for improving `agentd` while a provisioned worker is blocked on it.

**What `agy` is not given.** The operator's direction (2026-09-26): `agy` does not get anything that requires a lot of thought. Experiment design, the critical-path experiments (harnesses in the VM, shared authentication, bus semantics, NATS topology), security-relevant code, and design documents go to Claude Code and Codex workers. `agy` runs what others specified and reports evidence.

**Coordinator-side agent teams and workflows.** For non-implementation work the coordinator may run Claude Code agent teams or dynamic multi-agent workflows inside its own session instead of dispatching worktree workers: research fan-out across many sources, cross-checking a document against evidence, review passes over a PR set, retro data gathering, and inventories. The operator allowed this on 2026-09-26. Teammates run on `claude-sonnet-5` at medium (Anthropic's guidance for teammates) or `claude-opus-5-5` at high for review passes; they never edit the repository, so the worktree rule is not affected. Implementation always goes to worktree workers.

## Concurrency

| Harness | Interactive workers | Notes |
| --- | --- | --- |
| Claude Code | 3 | Plus the coordinator's session and its subagents (at most 4 subagents at once) |
| Codex | 3 | One is always the docs writer; one reviews |
| `agy` | 3 | Research, experiments, and a probationary implementer |

Nine interactive workers in total. The operator set Codex and `agy` at three each on 2026-09-26 after the first proposal of two and one. The limits are renegotiated at the phase 2 checkpoint with observed rate-limit data (the vendors publish only multipliers and five-hour windows; see the model research).

## Permission modes

The operator approved these permission modes on 2026-09-26, including Codex's outbound-network widening for bootstrap and the user-scope settings described below.

Workers must run unattended. The coordinator never types approvals into worker terminals; failures or blocked workers go to the operator. These are approved launch modes, not proof that every harness refuses every out-of-sandbox action. Exact CLI and configuration facts below come from `experiments/00-system-assessment/permission-facts.md`; observed behavior and launch proposals come from the coordinator's decisions and `experiments/00-system-assessment/evidence.md`. The commands show harness arguments; the provisioner launches processes through `mise exec` or `mise run`.

### Claude Code

```text
claude --permission-mode auto --settings <per-worker settings file>
```

The approved settings are `sandbox.enabled: true`, `sandbox.autoAllowBashIfSandboxed: true`, and `sandbox.network.allowLocalBinding: true`. Evidence label: observed in the imported research. The settings file `agent-peering-tests/.claude/settings.local.json` places `enabled`, `autoAllowBashIfSandboxed`, `excludedCommands`, and `network.allowedDomains` under a top-level `sandbox` key; the research design documents cite `sandbox.network.allowLocalBinding` as the sibling of `allowedDomains`. Only `allowLocalBinding` needs user scope because Claude Code accepts it only there, and the operator approved that change on 2026-09-26. The permission facts verify `--settings <file-or-json>` and `--setting-sources user,project,local`. Allowed proxy domains are the model APIs, GitHub, and package registries required by mise; the exact domain list is decided in phase 2 when the first worker is launched.

`auto` is a verified permission-mode value in the recorded release. The coordinator reports that its classifier auto-approves safe actions and observed it refuse an unsandboxed `codex queue` call in the research. This is observed behavior, not a guarantee that routine work will always pass. Proposed fallback: `--permission-mode acceptEdits` with an operator-controlled per-worker allowlist for `mise run *`, `git *`, `gh *`, and `agentctl *`. That fallback is not established as prompt-free. Claude subagents in phases 0 and 1 use the same approved settings.

The provisioner writes each worker's settings file outside the worktree and passes it with `--settings`, including status and inbox hooks. This is operator-controlled configuration, not project-scope configuration. The research rule disallows project-scope configuration in a shared worktree because other agents can edit it; it does not conflict with this per-worker injection.

### Codex

```text
codex -s workspace-write -a never
```

```toml
[sandbox_workspace_write]
network_access = true
```

`-a` is `--ask-for-approval`; the verified interactive CLI values are `on-request` and `never`. With `never`, sandbox-permitted work proceeds without approval prompts and execution failures return to the model. Commands needing greater access fail and are reported over the bus. The approved network setting is the research-confirmed loopback route, but opens all outbound network for tool calls, a known widening the operator approved for bootstrap on the operator's machine.

The narrower candidate from `experiments/00-system-assessment/harness-research.md` is `allow_local_binding = true` in a per-profile `[permissions.<name>.network]` table, verified in source but untested here. There is no top-level `[network]` table; general network policy lives under `[features.network_proxy]`. It permits local servers and direct host-loopback connections, skips additional proxy private-network checks, and retains proxy domain rules. Phase 2 tests it as a replacement. It is not a valid `[sandbox_workspace_write]` key; that table accepts only `writable_roots`, `network_access`, `exclude_tmpdir_env_var`, and `exclude_slash_tmp`.

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

The installed 1.2.11 has `--sandbox` (run in a sandbox with terminal restrictions), `--mode accept-edits|plan`, and `--dangerously-skip-permissions` (auto-approve all tool permission requests) [assessment]. The approved policy relies on the sandbox as the boundary while skipping permission prompts that would block unattended work; phase 2 verifies the boundary at runtime. The operator approved unattended `agy` on 2026-09-26. The harness research (`experiments/00-system-assessment/harness-research.md`, Antigravity section) describes a variant: `--sandbox` with `toolPermission: proceed-in-sandbox` in the worker's settings auto-runs sandboxed commands and prompts only for sandbox bypasses, the same shape as Claude Code's `autoAllowBashIfSandboxed`. Phase 2 tests that variant first and falls back to `--dangerously-skip-permissions` inside the sandbox if it still prompts for routine work; both are within what the operator approved. The Antigravity sandbox blocks network by default, so the loopback path to the bus is part of the same experiment. On Linux the `agy` sandbox uses kernel namespaces rather than Seatbelt, and headless Linux hosts without a D-Bus session bus bypass the keyring, which matters for the container experiments.

Any persistent changes to user settings or user-scope status and inbox hooks need operator approval with exact content.

## Models and effort levels

Every launch names a model and an effort level explicitly, including coordinator subagents and `codex exec` document runs; nothing runs on a harness default. The coordinator may raise the model or effort for a specific work item and records that choice in the issue. Haiku is the explicit exception in decision 9: its assignment records no effort control, not an effort value to pass to the harness.

The tables below reproduce model ids, display names, and accepted effort values only from `experiments/00-system-assessment/model-inventory.md`, recorded on 2026-09-26 on the operator's logins. Every listed model was verified by call; none is merely listed but not called. Reachability does not verify every model-effort pairing. Claude effort values are harness-wide help-text evidence, not per-model tests; the inventory does not establish the decisions' Haiku no-effort exception. Codex verified an explicit high override on `gpt-6-astra`; the remaining levels come from the model list or cache, including the hidden cache-only `gpt-reserve` and `codex-auto-review`. For `agy`, only the high flag override was called, the flag's interaction with the model-id variant is unverified, and the actual model is inferred from the accepted argument because output does not echo it. Phase 2 checks the assigned effort behavior before relying on it.

### Claude Code 2.1.283 (`claude`)

| Model id or argument | Display name | Effort or reasoning levels accepted by the harness | Evidence |
| --- | --- | --- | --- |
| `fable` | Fable | low, medium, high, xhigh, max (harness-wide help; not tested per model) | Verified by call |
| `claude-fable-5-1` | Fable | low, medium, high, xhigh, max (harness-wide help; not tested per model) | Verified by call |
| `claude-fable-5-1[1m]` | Fable (1M context option from `additionalModelOptionsCache`) | low, medium, high, xhigh, max (harness-wide help; not tested per model) | Verified by call |
| `opus` | NOT FOUND (no display name in caches) | low, medium, high, xhigh, max (harness-wide help; not tested per model) | Verified by call |
| `claude-opus-5-5` | NOT FOUND | low, medium, high, xhigh, max (harness-wide help; not tested per model) | Verified by call |
| `sonnet` | NOT FOUND | low, medium, high, xhigh, max (harness-wide help; not tested per model) | Verified by call |
| `claude-sonnet-5` | NOT FOUND | low, medium, high, xhigh, max (harness-wide help; not tested per model) | Verified by call |
| `haiku` | NOT FOUND | low, medium, high, xhigh, max (harness-wide help; not tested per model) | Verified by call |
| `claude-haiku-4-5-20251001` | NOT FOUND | low, medium, high, xhigh, max (harness-wide help; not tested per model) | Verified by call |

### Codex CLI 0.157.1 (`codex`)

| Model id or argument | Display name | Effort or reasoning levels accepted by the harness | Evidence |
| --- | --- | --- | --- |
| `gpt-6-astra` | GPT-6-Astra | low, medium, high, xhigh, max, ultra | Verified by call |
| `gpt-6-sol` | GPT-6-Sol | low, medium, high, xhigh, max, ultra | Verified by call |
| `gpt-6-luna` | GPT-6-Luna | low, medium, high, xhigh, max | Verified by call |
| `gpt-5.6-sol` | GPT-5.6-Sol | low, medium, high, xhigh, max, ultra | Verified by call |
| `gpt-5.6-terra` | GPT-5.6-Terra | low, medium, high, xhigh, max, ultra | Verified by call |
| `gpt-5.6-luna` | GPT-5.6-Luna | low, medium, high, xhigh, max | Verified by call |
| `gpt-5.5` | GPT-5.5 (`upgrade: gpt-5.6-sol`) | low, medium, high, xhigh | Verified by call |
| `gpt-reserve` | GPT-Reserve | low, medium, high, xhigh, max | Verified by call |
| `codex-auto-review` | Codex Auto Review | low, medium, high, xhigh, max | Verified by call |

### Antigravity agy 1.2.11 (`agy`)

| Model id or argument | Display name | Effort or reasoning levels accepted by the harness | Evidence |
| --- | --- | --- | --- |
| `gemini-3.8-flash-high` | Gemini 3.8 Flash (High) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gemini-3.8-flash-medium` | Gemini 3.8 Flash (Medium) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gemini-3.8-flash-low` | Gemini 3.8 Flash (Low) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gemini-3.7-flash-high` | Gemini 3.7 Flash (High) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gemini-3.7-flash-medium` | Gemini 3.7 Flash (Medium) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gemini-3.7-flash-low` | Gemini 3.7 Flash (Low) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gemini-3.6-flash-high` | Gemini 3.6 Flash (High) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gemini-3.6-flash-medium` | Gemini 3.6 Flash (Medium) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gemini-3.6-flash-low` | Gemini 3.6 Flash (Low) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gemini-3.1-pro-high` | Gemini 3.1 Pro (High) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gemini-3.1-pro-low` | Gemini 3.1 Pro (Low) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 (Thinking) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `claude-opus-4-6-thinking` | Claude Opus 4.6 (Thinking) | low, medium, high, max (help); tier in model id where present | Verified by call |
| `gpt-oss-120b-medium` | GPT-OSS 120B (Medium) | low, medium, high, max (help); tier in model id where present | Verified by call |

### Assignments

Assignments and their rationale follow `reports/inputs/phase-0-decisions.md`, section 9, informed by the vendor documentation recorded in `experiments/00-system-assessment/model-research.md`.

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
| Utility tier: mechanical, fully specified tasks whose output a program verifies (checksum manifests, converting probe output to tables, running a fixed verification script, parsing logs and CI results for retros, PR template checks) | Claude Code | `claude-haiku-4-5-20251001` | Not applicable (no effort control per decision 9; not established by the inventory) | Anthropic's guidance for simple subagent tasks; the verification step, not the model, carries the correctness. |
| Utility tier on the Codex side (the same task kinds, when a Codex worker owns the item) | Codex | `gpt-6-luna` | medium | OpenAI's high-volume model; its Pro allowance is an order of magnitude larger than Sol's. |
| `agy` headless probes (`--print`) and quick tasks | `agy` | `gemini-3.8-flash-medium` | medium (the variant) | The current Flash model at Google's default level. |

Not used: `ultra` on Codex (it delegates tasks on its own, which conflicts with the coordinator owning dispatch); Claude Code's `ultracode` setting for the same reason and because it reaches subscription limits sooner; the Claude and GPT-OSS models inside `agy` (the point of the third harness is a third model family); the `gpt-5.x` line; `max` effort anywhere until a measured gain justifies it. The utility tier is never given a task that needs judgment about whether something is wrong; the retros track rework caused by utility-tier runs and move a task class up if it recurs.

### Escalation and cost

The coordinator steps a worker up when a work item is on the critical path, touches security or credentials, or has failed once at the default; the vendor guidance is the same in all three cases: raise effort before switching model, switch model when the model had the context and still got it wrong. It steps down when retros show a task class routinely finishing without revision. Which Codex Pro tier and which Max tier the operator holds is not recorded (the CLIs do not expose it), and it decides how many Astra and Fable turns the group can afford per five hours, so the phase 2 checkpoint collects observed limits per harness and adjusts the concurrency table and these assignments together.

## What the system assessment established

The recorded facts below are from `experiments/00-system-assessment/evidence.md` and `experiments/00-system-assessment/versions.md`, assessed on 2026-09-26. They are a snapshot, not new runtime tests performed for this plan.

- The Apple M5 MacBook Air has 32 GB RAM and 466 GB free. Memory determines group-VM capacity; phase 3 measures it.
- Apple Containers is installed and its API server is already running under launchd, with zero containers and images. The handoff expected the service to be stopped, but no system change is needed to start it. The operator is still told before the first container experiment because creating VMs and images is the operator's call.
- Claude Code is authenticated through claude.ai with Max, and Codex through ChatGPT. The later model inventory records successful calls for all three harnesses, including `agy`; `agy` still has no auth-status command. `gh` is logged in as `tbhb` over HTTPS with `project` scope.
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

Done when the operator approves the revised plan and the model and effort assignments; concurrency and permission modes were approved on 2026-09-26. Outputs: `experiments/00-system-assessment/` (raw evidence from the assessment subagent), the dependency clones under `~/Code/github.com/`, `PLAN.md`, and `reports/phase-0-checkpoint.md`. The scaffold landed directly on `main` because there was nothing to review against. Everything after it, including the assessment evidence and these two documents, goes through a pull request from `docs/phase-0-plan` that the coordinator reviews and merges after the operator's review. There is no CI yet, so the phase 0 merge gate is coordinator review only. Checkpoint: run the phase 0 retro and regenerate `HANDOFF.md`; the operator approves the revised plan and model and effort assignments.

### Phase 1: repository foundation

Work items, in dispatch order, each a subagent in its own worktree:

1. **Tooling** (`chore`): extend `.gitignore`; extend `mise.toml` (pin Python 3.14, pnpm, Biome, keep the operator's pins); configuration for ruff, pytest, Biome, Vale with vale-ai-tells (installed by release URL per its README, with `ai-tells` and `ai-tells-commits`), rumdl, ryl, tombi; a mise task per tool, `check` and `fmt` aggregate tasks; prek hooks (extend `prek.toml`, add the commit-msg lint); documentation linting covers every Markdown file except `research/imported/`. The assessment established that every pin is installed without running `mise install`; this item runs `mise install` after changing the pins and records the result, satisfying the handoff. The first batch of mechanical checks includes secret scanning in prek, `guard-markdown` as a mise task and CI job, the `ai-tells-commits` lint, experiment-directory completeness, imported-research immutability, PR evidence links for `feat` and `exp`, and Mermaid CLI validation of fenced diagrams; phase 1 also establishes the silent-worker scheduled check-in for dispatches longer than fifteen minutes.

1a. **Go research gate** (`research`): read the pinned Go 1.27 docs and release notes for modules, the `go.mod` toolchain directive, testing, `go vet`, formatting, and the linter choice (`staticcheck` or `golangci-lint` through mise, recorded as a decision issue); Codex writes the conventions page and worker rules before item 2 or other Go code.

1b. **Python research gate** (`research`): read Python 3.14, uv, ruff, and pytest docs for the `src/` layout, ruff rules, pytest configuration, free-threading, and other relevant 3.14 changes; Codex writes the conventions page and worker rules before item 2 or helper-library work. Both gates run alongside item 1.

2. **Skeleton** (`chore`): `go.mod`, `cmd/agentd` and `cmd/agentctl` that build and print a version, `internal/` layout, `pnpm-workspace.yaml` with empty `apps/` and `packages/` placeholders, `schema/`, `experiments/`, `images/agent/` with a README placeholder (content by Codex), `tests/` with one passing test, `.worktrees/` ignored.
3. **CI** (`chore`): the workflows in GitHub workflow, running against the tooling from item 1. Branch protection after the first green run.
4. **Docs site** (`chore`): first complete the Astro, Starlight 0.42, and `starlight-blog` research gate, with Codex-written conventions and rules before configuration or code; record the pinned versions, cloned commits, and docs read in the PR. Evaluate `HiDeoo/starlight-blog` for the Devlog sidebar entry, falling back to dated pages if incompatible. Then build Astro Starlight in `docs/` with Mermaid rendering at build time (an integration or remark plugin the worker evaluates from the cloned starlight source and records), the sidebar structure (Project, Workflow, Research, Experiments, Design, Decisions, Guides), `mise run docs:dev` and `docs:build`. Pages are placeholders until Codex writes them.
5. **Research import** (`research`): copy `~/Code/github.com/tbhb/agent-peering-tests` and `~/Code/github.com/tbhb/agent-session-tests` verbatim into `research/imported/<folder>/`, excluding `__pycache__`, `.DS_Store`, `.obsidian/`, `codex/.venv/` (recording its `requirements.txt` and the installed package list), and `CLAUDE_CODE_SESSION_MANAGEMENT.html` plus its `_files/` directory (a Quarto rendering of the Markdown report beside it; the importer confirms this by comparing headings). Scan every file for secrets, tokens, credentials, and personal data (the `.claude/settings.local.json` and `.codex/config.toml` in the peering folder, raw terminal captures, logs, `results.jsonl`, and the Codex evidence directory are the likely places), redact or hold back anything sensitive, and list it. Commit `research/imported/MANIFEST.md` with every source file's SHA-256, size, and destination or exclusion reason. The operator permits committing research evidence; default to committing after scanning and redaction or holdback.
6. **Worker instructions and docs pages** (`docs`, Codex): `AGENTS.md` and `CLAUDE.md` (workflow, mise, worktree and stash rules, Markdown rules, Codex-writes-docs rule, bus usage once it exists); docs pages for the workflow, the tooling, the repository layout, and the project history; move `PLAN.md`, the phase 0 report, and `HANDOFF.md` into the docs site; write the first devlog entry covering phase 0 when the docs site lands, and migrate any entries from `reports/devlog/`.
7. **Project and issues** (`workflow`): configure the Project fields and views from GitHub workflow, create labels, file the phase 2 and phase 3 issues from this plan, and put them in the Project.

Checkpoint: the foundation is merged, the import and its manifest are merged, the Project reflects the plan; regenerate `HANDOFF.md`, then run the phase 1 retro as the last checkpoint step before writing the report.

### Phase 2: bootstrap orchestration

Build `agentd` v0 and `agentctl` with subagents, then switch to provisioned workers as soon as one of each harness can be spawned and reached over the bus. Work items:

1. Embedded NATS server in `agentd` with JetStream, one account per group, per-agent credentials (nkeys or user JWTs) with publish permissions limited to subjects ending in the agent's own name, the subject and stream layout from `design-sketch/04-messaging-and-shared-context.md`, and a `build` group.
2. `agentctl join|send|receive|ack|status|roster` against it, with compact machine-readable output.
3. The registry (SQLite) and the host-tmux backend: `spawn`, `list`, `capture`, `nudge`, `stop`, and group start, stop, and status, creating the worktree and branch, minting credentials, and starting the harness in a tmux window with a brief file. The launch recipe per harness includes the writable roots its worktree needs to stage and commit.
4. Shared context: key-value buckets for status, roster, claims (create-if-absent plus compare-and-set), decisions, and brief; the memory tiers as files (`.agents/memory/` checked in, `.agents/local/` ignored).

4a. Shell-scripting research gate: write the conventions page and worker rules for hooks and agent-image scripts, covering bash 3.2 on macOS versus bash 5 in the image and fish and zsh differences, before item 5.

5. Hooks per harness for status and inbox checks: Claude Code uses the operator-controlled per-worker settings file outside the worktree, passed with `--settings`; user-scope hooks for other harnesses need operator approval.
6. Experiments that gate the design: host loopback settings for each harness (which Codex setting, whether `agy` reaches loopback), initial-prompt behavior for each harness, and waiter semantics across compaction and restart.
7. How the coordinator itself uses the bus: `agentctl` from the coordinator's shell, with a background `receive` as its wake mechanism.

Checkpoint: one worker of each harness receives a brief, exchanges messages with the coordinator and each other, and reports status. Revisit concurrency and every model and effort assignment with observed rate-limit and quality data. Regenerate `HANDOFF.md`. The phase retro runs before the checkpoint report is written.

### Phase 3: research and experiments

Codex workers synthesize the imported research into the docs site's Research section. Provisioned workers run the experiments from `design-sketch/12-experiments-and-open-questions.md`, critical path first: harnesses in a Linux arm64 Apple Containers VM, shared authentication per harness, `container exec -it` fidelity, shpool in the guest, worktree mounts, embedded NATS behavior, NATS topology and reachability from a VM, NATS credentials and identity, waiter semantics, wake mechanisms. Then the rest. The handoff expected the Apple Containers service to be stopped, but the assessment found it running. No system change is needed to start it. The operator is still told before the first container experiment because creating VMs and images is the operator's call, and any system change requires approval. The daemon language, protocol schema format, and Tailscale integration are decided here with evidence. Shared authentication must receive a supported approach per harness or a documented limitation and the closest workable alternative for the operator. Re-verify version-sensitive imported findings or mark them stale.

Checkpoint: results and proposed decisions go to the operator. Regenerate `HANDOFF.md`. The phase retro runs before the checkpoint report is written.

### Phase 4: design in the docs site

Codex turns the surviving sketch plus results into the Design section with decision records. Retire `design-sketch/` in one commit that points to replacement pages, and move `FABLE_HANDOFF.md` into the docs site as history or delete it in that change, as required by the handoff. Check for newly added research before verifying the manifest; import new material first. Verify the import against the originals with the manifest, update every reference, get explicit approval, delete the original folders, record the retirement.

Checkpoint: operator reviews the design docs and research synthesis, approves the retirement. Regenerate `HANDOFF.md`. The phase retro runs before the checkpoint report is written.

### Phase 5: build the PoC

Work items:

1. Frontend conventions page for the React, Vite, Radix, React Router, xterm.js, and Tauri stack, before the first UI slice. Cover the full stack and enforcement in Research gates for languages and stacks, including the Rust gate before any crate.
2. Vertical slices, each demonstrable: daemon plus registry plus local backend plus one xterm.js terminal in the web UI; the Apple Containers backend with shpool, operator shells, and shared auth; the bus inside groups plus the message timeline and composer; the file browser; the Tauri app; Tailscale; egress control and the rest of the security policy. The build group appears in the PoC UI once the daemon hosts the host-tmux backend.

Each vertical slice is demonstrated to the operator as it lands. Checkpoint: all seven slices are demonstrable together on this machine, the Project shows no open phase 5 items, and the docs describe what was built. Regenerate `HANDOFF.md`. The phase retro runs before the checkpoint report is written.

### Phase 6: end-to-end verification

Playwright tests (fake backend for most flows, Apple Containers for the full demo), the demo script written by Codex, known gaps written up and filed.

Checkpoint: the operator runs the demo. Regenerate `HANDOFF.md`. The phase retro runs before the checkpoint report is written.

## Departures from the design sketch

- The provisioner is `agentd` from day one rather than a separate tool; the sketch already wanted the provisioner's operations to become daemon API calls.
- Worktrees live in `.worktrees/` inside the repository rather than outside it, as settled from the open location question in `design-sketch/11-repo-workflow-and-tooling.md`.
- Experiment directories are numbered.
- The `uv init` package is kept as a shared helper library rather than deleted.
- The handoff refers to a `WORK_DESIGN.md` in the peering research; no such file exists. The messaging and shared-memory designs exist only as the bullet lists in `OPEN_ITEMS.md`, which `design-sketch/04-messaging-and-shared-context.md` already absorbed. Nothing is missing from the import as a result, but the phase 3 synthesis should say so.

## Assumptions register

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
| Current React, React Router 8, Vite, Vitest, Playwright, Radix, xterm.js 6, Tauri 2 APIs and best practices | Phase 5 item 1 and UI slices; phase 1 docs site | The frontend conventions page, phase 5 item 1, and the phase 1 docs-site conventions page for Astro and Starlight |

## Research gates for languages and stacks

- **The gate.** Before the first work item that writes real code in a language or stack, a research item runs: a worker reads the pinned toolchain's release notes and docs at the recorded versions and the key libraries' docs and migration guides, and produces raw notes; Codex writes a conventions page in the docs site (Guides section) and encodes the operative rules into the instruction files. The gate is a Project item with the language in its title, sized S or M, and it blocks the first coding item for that language.
- **What gets encoded where.** The conventions page holds the full account with citations and versions. The instruction files hold only the rules a worker must apply while coding: `AGENTS.md` (read natively by Codex and by the other harnesses through `CLAUDE.md`, which imports it) for cross-harness rules, and path-scoped rules for Claude Code under `.claude/rules/<language>.md` so a worker editing Go sees the Go rules. The phase 1 harness research reports how Codex and `agy` load per-path rules; if either has an equivalent, the same rules are mirrored there by the tooling item. Rules name the versions they were written for, and the PR that moves a pin updates them.
- **Phase 1 items added.** Go 1.27 (modules, `go.mod` toolchain directive, testing, `go vet`, formatting, and which linter to adopt since the operator's required toolchain names none for Go; the coordinator proposes `staticcheck` or `golangci-lint` through mise and records the choice as a decision issue), and Python 3.14 with uv, ruff, and pytest (project layout under `src/`, ruff rule set, pytest configuration, free-threading and other 3.14 changes that matter). Both run before phase 1 items 2 and the helper-library work, alongside item 1. The Astro and Starlight page from the Frontend subsection runs before item 4.
- **Later phases.** Rust gets its gate before any crate is created: in phase 3 if the daemon is Rust, and in any case before the Tauri slice in phase 5, because the Tauri shell is Rust whatever the daemon language. Tauri 2.12 gets its own conventions coverage before that slice (the capabilities and permissions model, IPC commands and events, plugins, the CLI and bundling, and WKWebView specifics), alongside the React stack page that is phase 5 item 1 (see Frontend). Shell scripting in the agent image and the hooks gets a short page too (bash 3.2 on macOS versus bash 5 in the image, and fish and zsh differences), before phase 2 item 5.
- **Mechanical enforcement.** Each language's linter and formatter configuration is derived from the conventions page and checked in CI; a retro check confirms every language present in the tree (by file extension) has a conventions page and a rules file.

### Frontend

- **A research gate before frontend code.** No work item that writes TypeScript, React, Astro, or Tauri code starts until a research pass on the exact pinned versions has produced a conventions page in the docs site, written by Codex from the raw material a research worker gathers. The stack: TypeScript, React, React Router (the clone sits at the 8.x line), Vite, Vitest, Playwright, Radix UI, xterm.js 6, Tauri 2.12, Biome 2.5, and for phase 1 Astro and Starlight 0.42 with the `starlight-blog` plugin.
- **What the research reads.** The cloned sources' own docs and changelogs at the recorded commits (`experiments/00-system-assessment/dependency-clones.md`), the vendors' current docs sites, and each project's migration or upgrade guides for the last two major versions, since those name the deprecated patterns models still produce.
- **What the conventions page contains.** Per package: the pinned version and the commit read, the current APIs to use, the deprecated or removed APIs and patterns to avoid (with the version that removed them), project structure and data-flow conventions, testing patterns for Vitest and Playwright, and the Biome rules that enforce any of it. It is refreshed whenever a pin moves, as part of the PR that moves it.
- **Per PR.** Every frontend PR cites the conventions page sections it followed and any vendor doc it consulted beyond them; reviewers check code against the page, not against their own memory. A PR that introduces an API the page lists as deprecated fails review.
- **Mechanical enforcement.** Biome rules for what can be expressed as lint; a CI check that `package.json` pins match the versions the conventions page records; `pnpm outdated` reported in the retro so pins move deliberately.
- **Phase 1 already applies it** to the docs site: the docs-site worker reads Starlight 0.42 and Astro docs from the clones before writing configuration, records what it read in the PR, and Codex writes the first conventions page for the docs stack. The full React stack page is a phase 5 prerequisite and is listed as its own work item ahead of the first UI slice.

## Standing rules for workers

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

## Open questions for the operator

- Approve the revised plan as a whole and the model and effort assignments. Concurrency and permission modes were approved on 2026-09-26; all assigned models were verified by call.
- Confirm whether the `tbhb` account is on GitHub Pro. Rulesets and classic branch protection on this private personal repository require Pro, and the API cannot expose the account plan; without it, coordinator review and CI remain the unenforced merge gate.
