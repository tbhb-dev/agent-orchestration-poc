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
- Six interactive workers are proposed, including a permanent Codex docs writer. See `PLAN.md`, The build group and Concurrency. Subscription capacity at this load remains unknown.
- Unattended permission modes retain sandbox boundaries as the intended policy. See `PLAN.md`, Permission modes; flag evidence is in `experiments/00-system-assessment/permission-facts.md`. Runtime behavior is partly observed and partly untested, not a blanket guarantee.
- Experiments precede final container, shared-authentication, daemon-language, and remote-access decisions. See `PLAN.md`, Phases and the handoff.

## Open questions

- Approve the plan, concurrency table, and permission modes as recommended by the coordinator, including Codex's outbound-network widening for bootstrap and the two user-scope changes: Claude Code `allowLocalBinding` and Codex `network_access`.
- Choose the `agy` unattended mode: the coordinator recommends `--sandbox --dangerously-skip-permissions`, with `--sandbox --mode accept-edits` as the alternative. The phase 2 initial-prompt experiment records how each behaves.
- Confirm that pushing the scanned, redacted raw research evidence to the private repository is acceptable for the phase 1 import, as the coordinator recommends after scan, redaction or holdback, and manifest review.
- The coordinator recommends enabling branch protection on `main` itself in phase 1 after the first green CI run. Would the operator rather do it?

## Risks

- Subscription rate limits under six concurrent workers are unknown; the proposed limits are a starting assumption, renegotiated at phase 2.
- `agy` on Linux arm64 is unknown and gates the container design. Shared authentication also needs a tested answer per harness.
- Claude's `auto` classifier or Codex's `never` policy may block routine work and stall workers; the coordinator must escalate rather than approve terminal prompts.
- Mise shims are not on PATH in non-interactive shells. Every spawned process and CI step must go through mise.
- Codex's confirmed loopback setting opens outbound network. The narrower setting is untested; phase 2 verifies that `approval_policy = "never"` returns a deliberate sandbox denial as a failure without invoking the configured reviewer.
- The first draft could not be committed because the worktree's git metadata is under the main repository's `.git`, outside the workspace-write sandbox. Codex workers need that common git directory as an extra writable root to stage and commit; phase 2 checks the same requirement for Claude Code and `agy` before their first launch.

## What the coordinator proposes next

Once approved, start phase 1 with tooling and skeleton work in parallel, each in an isolated worktree. Follow with CI, the docs site, scanned research import and manifest, Codex-written worker instructions and pages, and Project configuration. Ask for approval before system changes or pushing raw imported evidence.
