# Agent orchestration design

This is the design wiki for the destination state of an agent orchestration product.

The neighboring [`agent-orchestration-poc`](https://github.com/tbhb/agent-orchestration-poc) project builds and tests foundational orchestration. Its current implementation and backlog are authoritative in that repository; historical PoC technology choices are not destination requirements.

This wiki looks past the proof of concept. It is where we will develop the full domain architecture and user experience, explore capabilities beyond the foundational build, preserve decisions and open questions, and turn useful conclusions into inputs for the PoC when appropriate.

## Start here

[Glossary](glossary.md) is the shared domain vocabulary reference, with source links, scope and claim-status distinctions, unresolved terminology questions, and a complete wiki crawl register. The owning pages in the authority map below remain authoritative.

[Participants and permissions](participants-and-permissions.md) defines the decided bot and capability/permission direction and the proposed workload/bot/operator abstraction, installations, membership, and containment. It separates authenticated bridge identity from asserted external authors and inbound relay from outbound egress. Issuer, enrollment, initial bot delivery, and scope composition remain open.

The initial backend targets are **host mode and Docker Sandboxes (`sbx`)**, reusing existing sandboxing rather than building a custom sandbox. Read the [SPIFFE participant authentication design](spiffe-mtls-authentication.md#initial-backend-scope) for the accepted scope, wrapper mTLS and runtime-mediated JWT paths, and remaining integration checks.

Initial identity sketches develop the [schema](identity-schema.md), [data flow](identity-data-flow.md), [API](identity-api.md), [commands](identity-commands.md), and [threat model](identity-threat-model.md). They keep workload incarnations, bot credential generations, and operator sessions distinct; issuer/bootstrap selection and authenticated generation binding remain open. These are destination proposals, not implemented interfaces or qualified security guarantees. [Claude’s preliminary review and Codex reconciliation](identity-preliminary-review-claude.md#codex-reconciliation) track integrated corrections, alternatives, and remaining operator choices.

For PoC validation planning, use [Initial backend validation spikes](backend-validation-spikes.md): ten bounded spike specifications, dependencies, fixtures, negative tests, evidence requirements, and completion criteria for the coordinator to reconcile with existing issues.

The [workload and agentd architecture](workload-architecture.md) and [execution-isolation page](execution-isolation.md) retain the earlier microVM/sidecar profile as a deferred design. Their custom runtime topology is not a prerequisite for the initial backends.

The [local sandbox runtime survey](local-sandbox-runtimes.md) preserves research into other runtime options and launcher integration for later consideration.

Read the [destination mental model](mental-model.md) for the laptop-focused product direction: interactive Sessions, headless Tasks, Workspaces, and the open relationships between execution, coordination, and isolation. It records accepted definitions separately from proposed architecture.

The [group peering design](group-peering.md) defines logical Groups managed by agentd and explores federated versus control-plane identity for collaboration across worktrees.

The [messaging schema](messaging-schema.md) and [messaging data flow](messaging-data-flow.md) develop the decided DM, ambient-channel, and nested-thread experiment under one agentd per host. Groups remain policy scopes; proposed SQLite mechanics distinguish inbox deliveries from channel history and read cursors. The initial [messaging API](messaging-api.md) and [agentw commands](messaging-commands.md) sketch the application interfaces. Detailed mechanics, interfaces, and the provisional channel name remain proposed. [Messaging experiments](messaging-experiments.md) separates measurable wake/reply signals from operator judgments about missed information and duplicate actions.

The [harness delivery proposal](messaging-delivery.md) traces the original Codex and Claude experiments and proposes native wakeups with authenticated inbox consumption, recovery from uncertain push outcomes, and hook/pull fallbacks.

Four draft proposals prepare messaging for multi-model review: [Loops and wake budgets](messaging-loops-and-budgets.md) owns the combined wake-policy recommendation; [Operator oversight](operator-oversight.md) separates participation from scoped reads and interventions; [Structured requests](messaging-requests.md) explores claims and outcomes; and [Model-facing envelopes](messaging-envelope.md) compares framed text with JSON. Each preserves Claude's proposal alongside labeled Codex review. No thresholds, request rollout, operator message authority, or rendering default is decided. Their schema and interface implications are integrated in the owning pages; [retention](messaging-schema.md#retention-and-redaction-open-decision) is one shared open decision.

The [PoC-derived mental model](mental-model-poc.md) preserves the earlier group-centered synthesis, four architectural planes, lifecycle and state ownership, and its source evidence. It is a bridge from the PoC, not a set of destination decisions.

The [PID-only authentication design is obsolete](peer-authentication.md); its archive is for provenance, not spike planning. The [supervisor protection investigation](supervisor-protection.md) remains useful as an adversarial test inventory, filtered through the current backend scope.

## Current authority and historical material

| Question | Canonical page | Interpretation |
| --- | --- | --- |
| Product primitives, UI goals, backend contracts | [Destination mental model](mental-model.md) | Accepted direction and explicitly labeled proposals |
| Participants, bots, bridges, capabilities, and grants | [Participants and permissions](participants-and-permissions.md) | Decided distinctions; proposed kinds, installations, containment, and bot mechanics |
| Initial backends, credentials, host threat model | [SPIFFE authentication](spiffe-mtls-authentication.md) | Protected workload mTLS/mediated JWT; bots support both mechanisms with proposed separate custody and enrollment |
| Identity records, lifecycle flows, interfaces, and abuse cases | [Schema](identity-schema.md), [data flow](identity-data-flow.md), [API](identity-api.md), [commands](identity-commands.md), [threat model](identity-threat-model.md) | Initial proposed mechanics; authenticated generation binding and enrollment remain qualification gates |
| Validation work to seed in the PoC | [Backend validation spikes](backend-validation-spikes.md) | Proposed experiments, not verified capabilities |
| Cross-Group and cross-daemon authority | [Group peering](group-peering.md) | Group scope is decided; cross-daemon mechanics remain open |
| Message persistence, delivery, and receipts | [Schema](messaging-schema.md), [data flow](messaging-data-flow.md) | Decided conversation experiment; proposed SQLite receipts, snapshots, channel cursors, and recovery |
| Messaging application interfaces | [API](messaging-api.md), [commands](messaging-commands.md) | Proposed DM/channel/rooted-reply interfaces; receive and presence decisions remain open |
| Comparing inbox and ambient coordination | [Messaging experiments](messaging-experiments.md) | Decided experiment direction; proposed protocol and metrics, no PoC scope transfer |
| Codex and Claude delivery mechanisms | [Harness delivery](messaging-delivery.md) | Versioned research, proposed wake adapters, and push fallbacks |
| Wake policy, budgets, and loop controls | [Loops and budgets](messaging-loops-and-budgets.md) | Proposed combined policy; thresholds and urgent allowances open |
| Operator oversight and message authority | [Operator oversight](operator-oversight.md) | Proposed scoped management; operator-sent message authority unresolved |
| Request coordination state | [Structured requests](messaging-requests.md) | Proposed claims/outcomes; first-experiment inclusion open |
| Model-facing rendering and trust framing | [Envelope](messaging-envelope.md) | Text recommendation and JSON alternative; neither selected or security-qualified |
| Harness mitigations and other runtimes | [Supervisor research](supervisor-protection.md), [runtime survey](local-sandbox-runtimes.md) | Research inputs filtered through initial-backend scope |
| PID-only architecture | [Supersession notice](peer-authentication.md) | Obsolete; archive is provenance only |
| Bespoke microVM/sidecar architecture | [Architecture](workload-architecture.md), [isolation](execution-isolation.md) | Superseded baseline, retained as a deferred alternative |
| Older PoC model | [Pinned snapshot](mental-model-poc.md) | Historical evidence, not current destination guidance |

Historical decisions retain their original context; they do not create competing current requirements. Unresolved choices remain marked as proposals or unknowns until decided and validated. Initial backend support is an accepted target, not an implementation or security guarantee.

## How the two projects relate

The PoC answers, "What can we make work, and what does the evidence say?"

This wiki asks, "Given what we are learning, what should the complete product become?"

The relationship runs both ways:

- PoC research, experiments, implementation, and retrospectives provide evidence for this wiki.
- Destination-state work here can expose missing experiments, sharpen requirements, or produce bounded design inputs for the PoC.
- A design in this wiki is not PoC scope until it is deliberately transferred there.
- A PoC implementation choice is not automatically a destination-state decision.

## PoC evidence boundary

The [PoC-derived model](mental-model-poc.md) records a pinned 2026-09-26 snapshot. It does not report current implementation or issue status. For current PoC state, consult that repository's plan, checkpoint, and coordinator handoff directly. This wiki does not maintain a duplicate live backlog.

## What belongs here

- The destination domain model and its vocabulary.
- System architecture, trust boundaries, protocols, lifecycle, and data ownership.
- Operator, coordinator, and worker-agent journeys.
- Interaction design for desktop, web, terminal, messaging, files, and oversight.
- Capability ideas that exceed the foundational PoC.
- Decisions, alternatives, contradictions, open questions, and research needs.
- Dated syntheses of PoC findings that materially change the destination design.
- Clearly bounded inputs that may later be handed to the PoC.

Live issue tracking, implementation instructions, raw experiment evidence, and detailed PoC status belong in the PoC rather than being copied here.

## How this wiki will work

The starting model comes from Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): the wiki is a persistent, compounding artifact maintained by an agent, not a pile of documents rediscovered from scratch for every question.

The intended division of labor is simple. The user curates sources, directs exploration, and makes consequential choices. Claude, Codex, and Gemini, including `agy` in CLI workflows, share responsibility for synthesis, cross-linking, consistency, provenance, and routine maintenance. Useful answers should be filed back into the wiki when they add durable knowledge.

The wiki, rather than any harness's project memory or chat history, is the shared knowledge base. Project memories should remain small orientation layers that point new sessions into the relevant wiki pages. This keeps knowledge available and consistent across all three collaborators.

We will design the concrete workflow together. Likely concerns include source ingestion, an index, a chronological change log, page templates, evidence and decision states, contradiction checks, stale-page detection, and review gates. None of those conventions is fixed merely by appearing on this list.

The initial maintainer context lives in [`AGENTS.md`](AGENTS.md). It records the project boundary, a dated PoC snapshot, evidence vocabulary, and the few practices needed before the fuller curation workflow exists.

## Status

The wiki contains a destination model in progress, the earlier PoC synthesis, and linked identity and supervisor-protection investigations. Continue developing the primitive relationships and validating execution and trust assumptions while keeping accepted direction distinct from proposed mechanisms.

The conversation index reflects the operator's 2026-09-27 discussion, recorded in Claude's handoff: one agentd per host, Group policy separate from conversation space, and an experimental DM/channel/thread starting set. Linked mechanics are Claude proposals with labeled Codex synthesis; unresolved earlier reviews remain open.

The operator's 2026-09-27 participant/authority discussion, handed off by Claude, decided bots as distinct messaging participants, both SPIFFE authentication mechanisms, Group/host installation scopes with future scopes possible, bridges as bot installations with bridging permissions, and capabilities distinct from permissions. The participant/installation mechanics are Claude proposals; Codex's kind-specific lifecycle, containment, and evidence qualifications are linked from [Participants and permissions](participants-and-permissions.md). Issuer/enrollment, first bot delivery paths, ambient membership, workload installation unification, and host-wide federation meaning remain open.
