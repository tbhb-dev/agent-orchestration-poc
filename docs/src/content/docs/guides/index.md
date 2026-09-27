---
title: Guides
description: Versioned conventions and the research gate before coding.
---

Read the conventions for the language or stack before editing it:

- [Go conventions](/guides/go-conventions/) cover the module, standard library, tests, and linter choice.
- [Python conventions](/guides/python-conventions/) cover the helper package, uv, Ruff, pytest, and typing.
- [Shell conventions](/guides/shell-conventions/) cover portable scripts, harness hooks, and shell tooling.
- [Docs stack conventions](/guides/docs-stack-conventions/) cover Astro, Starlight, Mermaid, the devlog, and builds.

A research gate precedes first code in each new language or stack. A worker reads the pinned release notes, source documentation, and migration guides and records raw notes under `research/gates/`. Codex writes the conventions and worker rules before coding starts. A PR that changes a pin updates the affected guidance. See the [research gate policy](/project/plan/#research-gates-for-languages-and-stacks).
