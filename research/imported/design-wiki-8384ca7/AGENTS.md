# Agent orientation

## Purpose

This project is the design wiki for the destination state of the agent orchestration product.

It sits beside `~/Code/github.com/tbhb/agent-orchestration-poc`, which builds and tests the foundational orchestration proof of concept.

The wiki may inspect the PoC, record what it teaches us, and develop inputs for it, but its scope is broader: the complete domain architecture, operator and agent experience, product capabilities, long-term system boundaries, and unresolved design questions.

Claude, Codex, and Gemini collaborate on this project. Gemini is invoked as `agy` in CLI workflows. Write shared instructions and wiki content so that none of the three depends on private context from another harness.

## Knowledge hierarchy

The wiki is the durable knowledge base and source of shared project context.

Keep this file and any harness-specific project memory sparse. Their purpose is to orient a new session toward the wiki, not to reproduce the wiki inside model-specific context.

- Put durable facts, synthesis, decisions, alternatives, and open questions in wiki pages.
- Put only essential startup instructions and pointers in project memory.
- Do not rely on chat history or harness-specific memory for knowledge another collaborator needs.
- When a session produces a durable conclusion, integrate it into the wiki rather than preserving it only in memory.
- Recheck live state at its source instead of storing frequently changing status in project memory.

Begin with `README.md`, then read the wiki pages relevant to the request. As navigation conventions emerge, follow the wiki index rather than expanding this file.

## Relationship to the PoC

- Treat the PoC repository as the source of truth for what the PoC currently plans, implements, and verifies.
- Treat this wiki as the source of truth for destination-state synthesis and decisions made here.
- Keep current implementation, PoC proposals, destination proposals, and accepted destination decisions visibly distinct.
- Do not edit the sibling PoC unless the user explicitly asks. An idea developed here remains a design input until it is deliberately transferred.
- Do not duplicate the PoC's issue tracker or changing implementation detail. Link to it and date any status snapshot.

## Evidence discipline

Use the PoC's claim vocabulary when it helps readers distinguish evidence from intent:

- `verified`: a targeted check confirmed the claim at recorded versions.
- `observed`: a run exhibited the behavior under recorded conditions.
- `documented`: versioned documentation states the behavior.
- `inference`: cited evidence supports the conclusion, but no direct test confirms it.
- `proposed`: this wiki is exploring the idea.
- `decided`: the user has accepted the destination-state choice.
- `unknown`: evidence or a decision is still needed.

Do not turn a proposal into a fact through repetition. Record contradictions, superseded claims, and uncertainty where readers encounter them.

## Frontmatter and tags

Every wiki content page uses YAML frontmatter. `README.md` and agent instruction files are exempt.

Use this minimal shape:

```yaml
---
title: Group lifecycle
summary: "The destination lifecycle for creating, operating, pausing, and retiring a group."
type: design
status: active
tags:
  - area/groups
  - scope/destination
updated: 2026-09-26
---
```

The fields mean:

- `title`: the human-readable page title. Do not repeat it as a body H1.
- `summary`: one sentence stating what the page lets a reader learn.
- `type`: one of `topic`, `design`, `decision`, `research`, `input`, or `index`.
- `status`: one of `draft`, `active`, `settled`, or `superseded`.
- `tags`: a short list of namespaced discovery labels.
- `updated`: the date of the last material content change in `YYYY-MM-DD` form.

Status describes the page lifecycle, not the strength of every claim on the page:

- `draft`: incomplete or not yet coherent enough to rely on.
- `active`: usable working knowledge that may continue to change.
- `settled`: an accepted destination conclusion or decision. Use this only after the user accepts it.
- `superseded`: retained for history but replaced. Link the replacement near the start of the body.

Tags are for discovery, not for encoding every property of a page. Use lowercase kebab-case, reuse existing tags, and normally keep a page between two and four tags.

- Include exactly one scope tag: `scope/poc`, `scope/destination`, or `scope/bridge`. A bridge page connects current PoC evidence to destination design or defines a possible PoC input.
- Include at least one area tag, such as `area/groups`, `area/sessions`, `area/orchestration`, `area/messaging`, `area/context`, `area/terminals`, `area/containers`, `area/identity`, `area/security`, `area/ux`, `area/remote-access`, or `area/workflow`.
- Add an actor tag only when a particular actor is central to the page, such as `actor/operator`, `actor/coordinator`, or `actor/worker`.
- Do not duplicate `type` or `status` as tags, and do not add unnamespaced tags.

Prefer an existing broad area over inventing a near-synonym. Add a new area or actor tag only when the existing vocabulary would make retrieval misleading.

## Initial wiki practice

The user curates sources, questions, and priorities. The agent writes and maintains the wiki.

Before changing the wiki:

1. Read the relevant wiki pages.
2. Inspect the sibling PoC when the request depends on its current state.
3. Identify whether the work concerns present evidence, a PoC input, or destination design.

When changing the wiki:

- Integrate new knowledge into existing pages instead of accumulating disconnected summaries.
- Add links where they help a reader traverse a real relationship.
- Preserve provenance close to material claims.
- Prefer a small coherent page over a speculative taxonomy.
- Use one line per paragraph and sentence case headings.

The fuller ingestion, indexing, logging, linting, and review workflow is intentionally not fixed yet. Evolve this file with the user as that workflow is designed.
