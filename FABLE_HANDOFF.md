# Handoff: agent orchestration proof of concept

You're the coordinator for building an end-to-end proof of concept in this repository (`~/Code/github.com/tbhb/agent-orchestration-poc`, remote `tbhb/agent-orchestration-poc`). The operator is Tony. This document tells you what to build, how to work, and where to stop and check in.

Written 2026-09-26. Anything below described as "current" or "installed" was checked on that date; recheck before relying on it.

## Your role

You plan and coordinate. You never implement.

- You read, plan, decide what work exists, write issues and briefs, dispatch work to other agents, review their results, merge, and report to the operator.
- Other agents do all implementation, research, and experiments, including code, tests, and experiment scripts. Codex alone writes documentation and reports (see "Codex writes all documentation and reports" below).
- Before the bootstrap tooling exists (phase 2), your only workers are your own subagents and agent teams, plus non-interactive Codex runs from your shell for writing. As soon as the bootstrap provisioner works, move to provisioned interactive Claude Code, Codex, and `agy` sessions for nearly everything, including improvements to the provisioner itself.
- "Gemini" in any of the operator's notes means Antigravity's `agy` CLI. The standalone Gemini CLI is deprecated and not supported.

## Read first

Read all of these before planning anything. They're the research this project builds on.

- `design-sketch/` in this repository, starting with its README. A design sketch written from a conversation with the operator, meant only to start things off. See "The design sketch is a starting point" below.
- `~/Code/github.com/tbhb/agent-peering-tests/`: `DESIGN_V2.md`, `WORK_DESIGN.md`, `OPEN_ITEMS.md`, `SANDBOX_TESTS.md`, the per-harness peering and handoff documents, every design review, and the results files. This is the identity, transport, and sandbox research for coordinating harnesses on the host, plus the unwritten messaging and shared memory designs in `OPEN_ITEMS.md`.
- `~/Code/github.com/tbhb/agent-session-tests/`: the Claude Code, Codex, and Antigravity session management reports (the top-level Markdown files). This is how each harness identifies, persists, resumes, and exposes sessions, which the daemon's status, resume, and observability depend on.
- `~/Code/github.com/tbhb/CLAUDE.md` for the workspace's Markdown rule (one line per paragraph, no hard wrapping), which applies here too. The rest of that file (Justfiles, `apm`, `repotools`) doesn't apply to this repository, which uses mise instead. The worktree and stash rule in `~/Code/github.com/tbhb/.claude/rules/worktree-wip.md` does apply, since workers here share one stash stack across many worktrees; it belongs in this repository's `AGENTS.md` too.

Read the documents above yourself; together they're roughly 450 KB of Markdown. The probe scripts, harness and evidence files, logs, and transcripts underneath them are for subagents to digest and report on, not for you to read directly. Note that `agent-session-tests/codex/` contains a Python virtual environment (`.venv`) and `agent-session-tests/.obsidian/` holds editor state; neither is research.

Both research directories are plain folders, not git repositories, so nothing in them is backed up anywhere else. This project absorbs them: phase 1 imports them into this repository, phases 3 and 4 synthesize them into this project's own research and design docs, and phase 4 retires the original folders. Until they're retired, check them for anything newer each time you start a phase.

## State at handoff

Checked on 2026-09-26:

- The repository has no commits yet. The working tree holds this document, `design-sketch/`, and the scaffold the operator created: `mise.toml`, `prek.toml` (builtin hooks only), `pyproject.toml` with `uv.lock`, `.python-version` (3.14), an empty `README.md`, and `src/agent_orchestration_poc/__init__.py` with the `main` entry point that `pyproject.toml` declares. An untracked `.venv/` also sits at the root and must never be committed; a minimal `.gitignore` covering it was added with this handoff.
- The GitHub repository is private. The GitHub Project at `https://github.com/users/tbhb/projects/9` exists, titled `agent-orchestration-poc`, and the active `gh` account (`tbhb`) has the `project` scope.
- Installed: Claude Code 2.1.283, Codex CLI 0.157.1, `agy` 1.2.11, Apple's `container` CLI 1.4.1 (build 9a8917c), tmux, mise, Tailscale (the app), and `guard-markdown` on `PATH`. `codex exec` is the non-interactive Codex command.
- The `container` system service isn't running or registered with launchd (`container system status`). Starting it (`container system start`) is a system change, so ask the operator before the first container experiment.
- Not installed: shpool. It belongs in the agent image, and any host-side use is an experiment's call.
- This document and every page in `design-sketch/` pass `guard-markdown`.

## The design sketch is a starting point

You're free to change anything in `design-sketch/` that you judge should change: architecture, component boundaries, topology, protocols, subject layouts, persistence approach, repository layout, phase plans, experiment lists, naming, all of it. It captures one conversation's thinking before any research or experiments in this project, and it will be wrong in places. Edit it, restructure it, or discard parts of it as evidence comes in, and record why in the docs site when a change is significant. You don't need the operator's approval to depart from the sketch.

What isn't yours to change without asking are the operator's requirements, which this handoff states directly rather than leaving to the sketch: the features the operator must have, Apple Containers for groups, embedded NATS for messaging, Tailscale for remote access, dual Tauri and web frontends and their stack, Astro Starlight for docs, the required toolchain and mise, the diagram and Markdown rules, Codex as the only writer of documentation and reports, the GitHub Project and worktree-based workflow, and your role as a coordinator who doesn't implement. If evidence says one of those is a bad fit, bring it to the operator with the evidence and a proposed alternative.

## What to build

An end-to-end proof of concept of the system the sketch describes, shaped by whatever the research and experiments show:

- **Groups** of interactive agent sessions (Claude Code, Codex, `agy`), each group scoped to a git worktree and running in its own Apple Containers VM, with shpool (or whatever experiments show works better) keeping sessions alive.
- **A messaging and shared context system** that agents in a group use to coordinate. It uses an embedded NATS server (`nats-server` running in-process as a Go library, with JetStream for durable streams, consumers, and key-value buckets), not a filesystem-based message bus. The same system, with different deployment and credentials, is what you first build for yourself on the host (phase 2). Design it once for both.
- **A host daemon** that owns groups, sessions, terminal streams, the file API, bus observation, and remote access. Go or Rust; choose after experiments. Bootstrap tooling is Go.
- **Two frontends from one build:** a web UI served by the daemon and a Tauri desktop app. Stack: TypeScript, React, Radix UI, React Router, Vite, Vitest, Playwright. Terminals with xterm.js.
- **Remote access over Tailscale.** Choose the integration by experiment (`tsnet` embedded in the daemon, `tailscale serve`, or something else). Nothing is ever exposed publicly.

The operator must be able to:

1. Create, list, pause, resume, and tear down groups.
2. Spawn, attach to, interact with (through xterm.js), restart, resume, and remove agent sessions in a group.
3. Open bash, fish, or zsh shells into a group's VM.
4. Browse a group's files, with git status and diffs.
5. See all messaging between agents in a group, and send messages to the whole group or to individual agents.

The PoC also has to work out whether and how agent sessions can share authentication, so the operator doesn't log in to every session, group, or VM separately. The target is logging in once per harness (Claude Code, Codex, `agy`) on this machine and having every session of that harness, in any group, use it. Treat this as a research question with a required answer: find out what each harness supports, pick an approach per harness based on evidence, and build it. If a harness can't share auth safely, document why (Codex writes that up) and bring the operator the closest workable alternative. The starting options and the risks to test are in `design-sketch/06-containers.md` under "Credentials."

## Standing rules

- **mise for everything.** All project tooling and task automation goes through mise so it's isolated to the project: pinned tool versions and a task for every repeatable action. Workers run mise tasks, never global installs. CI runs the same tasks.
- **Required toolchain.** The operator has chosen these; configure them, don't substitute:
  - Python 3.14, with uv (run through mise) for everything Python: environments, dependencies, and running scripts. `pyproject.toml` is already initialized.
  - prek for pre-commit hooks.
  - vale-ai-tells (Vale styles) and rumdl to lint all documentation. The vale-ai-tells source is at `~/Code/github.com/tbhb/vale-ai-tells`; read its README for how consumers install and configure it.
  - ryl for YAML, tombi for TOML, ruff for Python linting, pytest for Python tests.
  - Biome for JavaScript, TypeScript, CSS, JSON, and HTML.
- **Latest source for dependencies.** Whenever the work depends on a third-party project, have an agent clone its latest source into `~/Code/github.com/<owner>/<repo>`, or pull if it's already there, and work from that source and its docs rather than memory. Record the commit read.
- **Evidence over assumption.** Anything the design depends on gets verified on this machine, with versions recorded. Use evidence labels like the research repositories do. Web research and model knowledge are leads to test, not facts.
- **Codex writes all documentation and reports.** Only Codex agents write or edit documentation and reports. That covers every page in the docs site, research synthesis, experiment write-ups, decision records, the design sketch while it exists, `README` files, `AGENTS.md` and `CLAUDE.md`, the phase 0 plan, checkpoint reports, and any other report to the operator. Claude Code and `agy` workers hand Codex their raw material instead: results, evidence files, notes, and answers to its questions, delivered over the bus or as files in their worktree. You don't write these either; you decide what a document or report needs to say, give Codex the inputs, review the result, and send it back for changes. Before provisioned workers exist, run Codex non-interactively from your shell (`codex exec` or its current equivalent; check the installed version's help) for any writing in phases 0 and 1. Code comments and docstrings stay with whoever writes the code.
- **Diagrams** are Mermaid or hand-drawn SVG only.
- **Markdown** uses one line per paragraph and sentence case headings.
- **Everything is committed and pushed.** Nothing that matters lives only on an agent's disk.
- **Parallel work uses local git worktrees.** Every worker gets its own worktree and branch. Workers never share a checkout.
- **Sandbox escapes go to the operator.** Never approve a worker's request to run outside its harness sandbox, and never type approvals into a worker's terminal on its behalf. Escalate blocked workers to the operator.
- **System changes go to the operator.** Anything installed or changed outside this repository (system packages, Apple Containers, Tailscale configuration, harness user settings, launch agents) needs the operator's approval first, with the exact change described.

## Phases

Each phase ends with a checkpoint where you report to the operator and wait for a go-ahead before starting the next one.

### Phase 0: orientation and assessment

1. Read everything in "Read first."
2. Have a subagent assess the local system and report what's installed, with versions, and what's missing. At least: macOS version, Apple silicon model and memory, Xcode command line tools, Apple's `container` (and whether its system service runs), git, `gh` (confirm the `project` scope), tmux, mise and every tool `mise.toml` pins (confirm `mise install` succeeds), Go, Rust, Node, Python 3.14 through uv, the three harnesses (versions, confirmation that each is authenticated, and where each keeps its user-scope settings and hooks), Tailscale (installed, logged in, tailnet name), and anything else the sketch assumes.
3. Have agents clone or update the dependency repositories you already know you'll need (see `design-sketch/11-repo-workflow-and-tooling.md` for a starting list).
4. Have Codex write a plan from your decisions and bring it to the operator. It should cover:
   - the monorepo structure,
   - the GitHub workflow (Project fields and views, issue conventions, branch and worktree naming, commit and PR conventions, review and merge policy, CI),
   - how you'll set up the build group of workers,
   - the phases below, refined,
   - the concurrency you want per harness,
   - the permission modes you want workers to run in.

The operator has said concurrency is negotiable once they see how you intend to set up the group.

**Checkpoint:** the operator approves the plan, the concurrency limits, and the worker permission modes.

### Phase 1: repository foundation

Using subagents only (no provisioned workers exist yet):

- Extend the minimal `.gitignore` (`.venv/`, `__pycache__/`, `.DS_Store` today) with `node_modules/`, build output, and whatever the worktree location needs.
- `mise.toml` with pinned tools and the initial tasks. The operator already created `mise.toml` (with go, node LTS, rust, uv, vale, prek, rumdl, tombi, and ryl) and ran `uv init` to create `pyproject.toml`; extend them rather than replacing them. Things still to do there include pinning Python 3.14 in `mise.toml` (only `.python-version` and `requires-python` say so now), adding Biome and pytest through whichever route fits (mise, uv dev dependencies, or the frontend package manager; ruff is already a uv dev dependency), and deciding what to do with the `uv init` scaffold (the placeholder `src/agent_orchestration_poc/` package and its script entry point, and the empty `README.md`).
- Configuration for every linter and formatter in the required toolchain, a mise task for each and one that runs them all, and prek hooks that run them on commit (extend the existing `prek.toml`). Documentation linting covers `docs/`, `design-sketch/`, and every other Markdown file in the repository, except the imported research, which stays as it was.
- The monorepo skeleton, including the Go module for the bootstrap tooling.
- `AGENTS.md` and `CLAUDE.md` for workers in this repository, written by Codex: the workflow, mise usage, worktree rules, Markdown rules, the rule that only Codex writes documentation and reports, and how to use the bus once it exists.
- An Astro Starlight site in `docs/` with an initial structure, Mermaid rendering, and a mise task to run and build it. Any agent can build the site's tooling; its pages are written by Codex.
- The GitHub Project (`https://github.com/users/tbhb/projects/9`) configured per the approved workflow, with issues for phases 2 and 3.
- CI running the mise tasks.
- An import of `~/Code/github.com/tbhb/agent-peering-tests` and `~/Code/github.com/tbhb/agent-session-tests` into this repository, in a location that fits the monorepo structure (for example `research/imported/<folder>/`):
  - Copy everything verbatim, including documents, scripts, probes, evidence, schemas, and results, so the originals can be deleted later without losing anything. Leave out only generated or vendored material: `__pycache__`, `.DS_Store`, Obsidian workspace state, and the Python virtual environment at `agent-session-tests/codex/.venv/` (record its dependency list instead). `agent-session-tests/CLAUDE_CODE_SESSION_MANAGEMENT.html` and its `_files` directory look like a saved rendering of the Markdown report next to them; confirm that before excluding them. List everything left out.
  - Before committing, scan every file for secrets, credentials, tokens, and personal data (harness local settings, raw terminal captures, logs, and session evidence are the likely places). Redact or hold back anything sensitive and list it for the operator. Confirm the repository's visibility with the operator before pushing raw evidence.
  - Commit a manifest of every source file with its checksum and its destination (or the reason it was excluded), so the import can be checked against the originals.
  - Don't edit imported files. Synthesis happens in new documents.

**Checkpoint:** the foundation is merged, the import and its manifest are merged, and the Project reflects the plan.

### Phase 2: bootstrap orchestration

Build the host-side provisioner and the messaging and shared context system on an embedded NATS server (see `design-sketch/10-bootstrap-orchestration.md` and `design-sketch/04-messaging-and-shared-context.md`). Build it with your subagents first, then switch to it as soon as it can:

- start an interactive Claude Code, Codex, or `agy` session in tmux, in its own worktree, with a brief,
- let workers and you exchange messages with background-call wakeups,
- give the group shared context (memory tiers, decisions, claims),
- report worker status through hooks.

Design the subject layout, streams, consumers, message format, key-value buckets, CLI, and shared context layout so they carry over unchanged into group VMs. Only the server topology, the network path to it, and how agents get their credentials should differ.

**Checkpoint:** show the operator one worker of each harness receiving a brief, exchanging messages with you and each other, and reporting status. Agree on concurrency again now that it's real.

### Phase 3: research and experiments

Have Codex workers synthesize the imported research into this project's own research section of the docs site: what was established (with its evidence labels and the versions it was tested against), what was superseded by the move to containers, what's still open, and which findings the PoC depends on. Findings tied to versions that have since changed get re-verified or marked stale. The synthesis should read as this project's research, with the imported material cited as its source, not as a summary of someone else's folders.

Run the experiments in `design-sketch/12-experiments-and-open-questions.md` in parallel with provisioned workers, critical path first. The first finding to get is whether all three harnesses run and authenticate inside a Linux arm64 Apple Containers VM, because the rest of the container design depends on it. Shared authentication across sessions follows right after, since it decides how every group VM gets credentials. Each experiment gets a directory under `experiments/` with its scripts and raw evidence, produced by whichever worker ran it, and a write-up in the docs site written by Codex from that evidence. Settle the open design questions with the evidence, including the daemon language and the Tailscale integration.

**Checkpoint:** results and proposed decisions go to the operator.

### Phase 4: design in the docs site

Have Codex workers turn the surviving parts of the sketch and the experiment results into the design section of the docs site, with decision records for the major choices. Once the docs cover everything the sketch did, retire the sketch by deleting `design-sketch/` in one commit that points to the replacement pages (see `design-sketch/README.md`). Move this handoff document into the docs site as project history, or delete it, in the same change.

Then retire the original research folders:

1. Have an agent check the import against the originals using the manifest: every file present with a matching checksum, or excluded for a recorded reason. Also check that neither folder gained files after the import. Anything new gets imported first.
2. Update every reference to the old folder paths (in the docs site, `AGENTS.md`, `CLAUDE.md`, the sketch if it still exists, and code comments) to point to the imported copies or the synthesized docs.
3. Bring the verification result to the operator and get explicit approval to delete. Deleting them is a change outside this repository and can't be undone.
4. After approval, delete `~/Code/github.com/tbhb/agent-peering-tests` and `~/Code/github.com/tbhb/agent-session-tests`, and record the retirement (date, manifest, and the docs pages that replaced them) in the docs site.

**Checkpoint:** the operator reviews the design docs and the research synthesis, and approves the folder retirement.

### Phase 5: build the proof of concept

Plan the build as vertical slices, each demonstrable on its own. For example:

1. The daemon with the registry and a local backend, plus a terminal session in xterm.js through the web UI.
2. The Apple Containers backend: group VMs, shpool sessions, operator shells, and shared authentication so new sessions start already logged in.
3. The bus inside groups, and the message timeline and composer in the UI.
4. The file browser.
5. The Tauri app.
6. Remote access over Tailscale.
7. Egress control and the rest of the security policy.

Keep the Project and the docs current as slices land. Have the bootstrap build group show up in the PoC UI as a group once the daemon can host the host-tmux backend.

### Phase 6: end-to-end verification

- Playwright tests for the main operator flows, against a fake backend for most of them and against Apple Containers for the full demo.
- A demo script in the docs site, written by Codex, that the operator can follow: create a group from a branch, run agents from all three harnesses in it without logging any of them in, watch them coordinate, send messages as the operator, browse files, open a shell, reach the UI from another device over Tailscale, tear the group down.
- Known gaps and follow-ups, written up in the docs by Codex and filed as issues.

**Checkpoint:** the operator runs the demo.

## Reporting

- At every checkpoint, have Codex write a short report from your inputs, review it, and give it to the operator: what's done (with links to PRs, docs pages, and experiment write-ups), decisions made and their evidence, open questions, risks, and what you propose next.
- Between checkpoints, bring the operator anything that blocks progress, anything that needs a system change, and any finding that contradicts the design sketch in a way that changes scope.
- Don't pad reports. State what's known, what isn't, and what you're assuming.
