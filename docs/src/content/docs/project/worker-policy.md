---
title: Worker policy
description: Durable operator boundaries and quality rules for project workers.
---

Workers follow [AGENTS.md](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/AGENTS.md) for operative instructions. This page gives the durable policy and its decision trail. The [2026-09-26 plan](/project/plan/) is the source for the original requirements, and the [phase 1 coordinator inputs](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/reports/inputs/phase-1-coordinator-notes.md) record their additions.

## Operator and credential boundaries

After current approval and green CI, the coordinator may merge ordinary reviewed product code, including code that handles credentials. The operator controls changes to project credential issuance, storage, grants, repository secrets, security policy, egress rules, and host setup or installations. Reviewer identity records the review process and does not protect credentials from workers on the same machine. Workers report sandbox denials and proposed system changes to the operator. They do not approve another worker's escape or type an approval into its terminal. See [AGENTS.md, Operator boundaries](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/AGENTS.md#operator-boundaries), [plan, Operator requirements](/project/plan/#operator-requirements-added-in-phase-1), and [plan, Permission modes](/project/plan/#permission-modes).

## Code and quality boundaries

Functional core, imperative shell is binding for every language. Pure core functions decide and transform data. A thin shell performs I/O. Go core is under `internal/core/` and Python core under `agent_orchestration_poc.core`. Boundary tools, property tests, mutation tests, duplication, dead-code, complexity, and coverage gates precede core code. Run the applicable mise checks. The operative rules are in [AGENTS.md, Functional core, imperative shell](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/AGENTS.md#functional-core-imperative-shell), [decision 0003](/decisions/0003-functional-core-imperative-shell/), [decision 0004](/decisions/0004-quality-gates/), [decision 0005](/decisions/0005-property-and-mutation-testing/), and [tooling](/workflow/tooling/).

Strict pyrefly is the Python type checker. [Decision 0002](/decisions/0002-python-type-checker/) records the two annotation relaxations for tests and experiments. The phase 1 checkpoint's question about overturning them is historical, not a pending worker choice.

## Research before coding

Before first code in a language or stack, read the pinned release notes, versioned documentation, source, and migration guides. Record the source commits and evidence, then have Codex write conventions and operative worker rules. A pin change updates those rules in the same PR. [AGENTS.md, Documentation and language rules](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/AGENTS.md#documentation-and-language-rules) is operative, with [Go](/guides/go-conventions/), [Python](/guides/python-conventions/), [shell](/guides/shell-conventions/), and [docs stack](/guides/docs-stack-conventions/) conventions. Frontend and Rust gates remain prerequisites for their first code, as recorded in [plan, Research gates](/project/plan/#research-gates-for-languages-and-stacks).

## Evidence and publication

Read dependency source at a recorded commit before relying on it. Use the evidence labels in [AGENTS.md, Evidence and dependencies](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/AGENTS.md#evidence-and-dependencies). Preserve imported research verbatim, write synthesis separately, and scan evidence for secrets before committing. Codex writes documentation and reports. Use one line per Markdown paragraph, sentence case headings, and Mermaid or editable Excalidraw drawings. The operative workflow and checks are in [AGENTS.md](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/AGENTS.md) and [tooling](/workflow/tooling/).
