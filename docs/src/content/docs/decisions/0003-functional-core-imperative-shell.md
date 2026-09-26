---
title: "0003: functional core and imperative shell"
description: Operator requirement and import boundaries for Go and Python code.
---

## Status

Accepted 2026-09-26 for issue #58 as an operator requirement.

## Context

The phase 2 packages will handle broker connections, SQLite, processes, and terminal capture. Decisions about roster transitions, messages, and provisioning can operate on values. The current Go packages describe shell jobs, while the Python helper package had no named core or shell (research/gates/boundaries/notes.md §1).

## Decision

Put Go core packages under `internal/core/<topic>` and Python core modules under `agent_orchestration_poc.core`. Keep `cmd/*`, `internal/bus`, `internal/registry`, `internal/backend/*`, `internal/term`, `internal/api`, `agent_orchestration_poc.shell`, and experiment scripts in the imperative shell. The shell obtains state and performs effects, then passes plain values into core functions. `internal/version` stays in place (research/gates/boundaries/notes.md §1).

Use depguard in golangci-lint 2.14.0 to deny `os`, `net`, `syscall`, NATS modules, and shell imports under the Go core tree. Allow `net/netip` and `net/url` as value packages. Use import-linter 2.15 with a layers contract and a forbidden external import contract for Python. Ruff 0.16.9 `TID251` adds a limited check for named I/O calls in the Python core (research/gates/boundaries/notes.md §§2, 3).

Go-arch-lint 1.19.0 does not inspect standard library imports, so it cannot express this boundary. Arch-go 2.1.2 adds a second tool and configuration without improving the required import check. A per-feature core layout would need package lists or wildcard contracts that are easier to leave incomplete (research/gates/boundaries/notes.md §§1, 3).

## Consequences

Core tests use values and no mocks. Shell tests cover real effects as integration tests. The import checkers inspect dependency paths, so a `pathlib` write or an I/O handle passed into the core remains a review violation. TypeScript needs its own boundary gate before the phase 5 UI slice (research/gates/boundaries/notes.md §§2, 4, 6).

Reopen this decision if a phase 2 package cannot fit the layout or a measured gap needs a different enforcement tool.

## Evidence

The research gate recorded failing and passing import probes on Go 1.27.1 and Python 3.14.6, with clone commits and tool versions in `research/gates/boundaries/versions.md`. This PR records local task failures in `reports/inputs/gates-failing-examples-2026-09-26.md`.
