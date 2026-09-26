# Phase 0 checkpoint report

Written 2026-09-26. Phase 0 awaits operator approval; no phase 1 work is authorized by this report.

## What's done

- The initial scaffold commit is on `main`: `FABLE_HANDOFF.md`, `design-sketch/`, `mise.toml`, `prek.toml`, and the Python scaffold. The assessment and plan are on branch `docs/phase-0-plan`, to be merged by pull request after the operator's review.
- System assessment: `experiments/00-system-assessment/evidence.md` and `experiments/00-system-assessment/versions.md` record hardware, tools, authentication evidence, permission help, and environment constraints.
- Dependency sources: `experiments/00-system-assessment/dependency-clones.md` records 23 clones or updates under `~/Code/github.com/`, their commits and nearest tags. Nothing was built or installed by that assessment.
- Plan: `PLAN.md` records the coordinator's decisions, checked against the handoff and `experiments/00-system-assessment/permission-facts.md`.

## Decisions made and their evidence

- `agentd` starts as the Go bootstrap provisioner with embedded NATS, SQLite, and host tmux, then grows into the daemon. See `PLAN.md`, Names and Repository layout; this refines `design-sketch/10-bootstrap-orchestration.md`.
- One root Go module, a shared Python helper package, pnpm workspaces, numbered experiments, and isolated worktrees. See `PLAN.md`, Repository layout.
- Project fields, issue conventions, conventional commits, reviewed squash merges, and mise-based CI are specified. See `PLAN.md`, GitHub workflow.
- Nine interactive workers were set by the operator on 2026-09-26, three per harness, including a permanent Codex docs writer. See `PLAN.md`, The build group and Concurrency. Subscription capacity at this load remains unknown.
- The operator approved unattended permission modes on 2026-09-26; they retain sandbox boundaries as the intended policy. See `PLAN.md`, Permission modes; flag evidence is in `experiments/00-system-assessment/permission-facts.md`. Runtime behavior is partly observed and partly untested, not a blanket guarantee.
- Experiments precede final container, shared-authentication, daemon-language, and remote-access decisions. See `PLAN.md`, Phases and the handoff.
- Models and effort levels are explicit for all workers, coordinator tasks, and document runs. `INPUTS/phase-0-decisions.md`, section 9, supplies assignments; `experiments/00-system-assessment/model-inventory.md` verifies every assigned model by call and distinguishes help-text effort lists from tested overrides; `experiments/00-system-assessment/model-research.md` records vendor guidance. No assigned model is unverified, but not every effort pairing was tested.
- Retrospectives run at every phase checkpoint and after every ten merged PRs, proposing a mechanical check or explaining why none applies. Codex writes the retro and daily/checkpoint devlog; decisions sections 8 and 12 define cadence, evidence inputs, the first tooling checks, and later candidates. See `PLAN.md`, Retrospectives, devlog, and mechanical checks.
- Coordinator rollovers preserve durable decisions, memory, and a Codex-regenerated `HANDOFF.md`; decisions section 10 defines compaction and handoff triggers, the six-step procedure, verification by the new session, and resume as fallback. Every checkpoint regenerates the handoff.
- Commit attribution moves to the Project's Worker field and the PR body's evidence section, with no attribution or co-author trailers. Decisions section 13 retains the conventional subject, explanatory body, `Refs:` trailer, and commit lint; section 3 makes the PR title and body the squash commit.

## Open questions

- Approve the revised plan as a whole and the model and effort assignments. Concurrency and permission modes were approved on 2026-09-26; all assigned models were verified by call.
- Confirm whether the `tbhb` account is on GitHub Pro. Rulesets and classic branch protection on this private personal repository require Pro, and the API cannot expose the account plan; without it, coordinator review and CI remain the unenforced merge gate.

## Risks

- Subscription rate limits under nine concurrent workers are unknown; the operator-set limits are a starting assumption, renegotiated at phase 2.
- The harness research identifies a first-party `agy` Linux arm64 build; its runtime behavior in the target VM is untested and gates the container design. Shared authentication also needs a tested answer per harness.
- Claude's `auto` classifier or Codex's `never` policy may block routine work and stall workers; the coordinator must escalate rather than approve terminal prompts.
- Mise shims are not on PATH in non-interactive shells. Every spawned process and CI step must go through mise.
- Codex's confirmed loopback setting opens outbound network. The narrower setting is untested; phase 2 verifies that `approval_policy = "never"` returns a deliberate sandbox denial as a failure without invoking the configured reviewer.
- The first draft could not be committed because the worktree's git metadata is under the main repository's `.git`, outside the workspace-write sandbox. Codex workers need that common git directory as an extra writable root to stage and commit; phase 2 checks the same requirement for Claude Code and `agy` before their first launch.

## What the coordinator proposes next

Once approved, start phase 1 with tooling and the Go and Python research gates in parallel, each in an isolated worktree; skeleton code follows the gates. The tooling item includes the first batch of mechanical checks: secret scanning, `guard-markdown`, commit-message lint, experiment-directory completeness, imported-research immutability, PR evidence links, and Mermaid validation, plus scheduled silent-worker check-ins. Follow with CI, the docs site, scanned research import and manifest, Codex-written worker instructions and pages, and Project configuration. Ask for approval before system changes. Research evidence may be committed, with commit as the default after scanning and redaction or holdback.
