# Design sketch

This directory is a starting sketch for the agent orchestration proof of concept. It was written from a design conversation before any research, experiments, or code in this repository existed. Treat it as a set of informed proposals and open questions, not decisions. Anything here can be overturned by evidence.

## Status and retirement

This sketch is temporary. Once the Astro Starlight documentation site in `docs/` is established and has absorbed whatever survives from these pages (as design docs, decision records, or research notes), delete this entire directory in a single commit whose message says the sketch has been retired and points to the docs pages that replaced it. Nothing should link to `design-sketch/` after that commit. Until then, when a docs page supersedes a sketch page, add a line at the top of the sketch page pointing to its replacement.

## Pages

| Page | Covers |
| --- | --- |
| [01-overview.md](01-overview.md) | What the PoC is, goals and non-goals, principles, vocabulary, how it relates to the earlier agent-work research |
| [02-architecture.md](02-architecture.md) | Components, process topology, where each piece runs |
| [03-groups-and-sessions.md](03-groups-and-sessions.md) | The group model, session kinds, lifecycles, registry sketch |
| [04-messaging-and-shared-context.md](04-messaging-and-shared-context.md) | The bus, delivery semantics, identity, wake mechanisms, shared memory tiers |
| [05-terminal-data-path.md](05-terminal-data-path.md) | From a harness in a VM to xterm.js: PTYs, shpool, framing, resize, reattach |
| [06-containers.md](06-containers.md) | Apple Containers backend, images, mounts, users, credentials, egress, other backends |
| [07-ui.md](07-ui.md) | Operator UI features, shared web and Tauri frontends, stack |
| [08-remote-access.md](08-remote-access.md) | Tailscale options and remote policy |
| [09-security.md](09-security.md) | Threat model for the container era |
| [10-bootstrap-orchestration.md](10-bootstrap-orchestration.md) | The host-side tmux provisioner and bus that the coordinating agent uses to build everything else |
| [11-repo-workflow-and-tooling.md](11-repo-workflow-and-tooling.md) | Monorepo, mise, GitHub Project workflow, worktrees, docs site, dependency clones |
| [12-experiments-and-open-questions.md](12-experiments-and-open-questions.md) | What has to be tested before the design firms up |

## Conventions used in these pages

- Diagrams are Mermaid. Project documentation should use Mermaid or hand-drawn SVG only.
- Claims about third-party tools that came from web research or memory, not from a test on the operator's machine, are marked as unverified. The research repos use evidence labels (verified, observed, help-text, schema, documented, inference, untested); the docs site should adopt the same discipline.
- Release dates and version numbers quoted from web research (Apple Containers, Docker, the SharedRoot exploit) were not cross-checked and some are inconsistent with each other. Treat them as leads for the experiments, not as a version history.
- Names like `agentd` (host daemon), `agentctl` (agent and operator CLI), and `agentd-guest` (in-VM supervisor) are placeholders.
