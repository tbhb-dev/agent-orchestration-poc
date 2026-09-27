---
title: "0005: pure Go SQLite driver for the host registry"
description: The driver choice and pinned versions for the agentd registry.
---

## Status

Proposed for issue #28 on 2026-09-26.

## Context

The host registry needs one file backed database that builds on the operator's macOS arm64 machine and the repository's Linux CI runner. The registry uses `database/sql` and stores small group and worker records.

## Decision

Pin `modernc.org/sqlite` v1.59.0 and its required `modernc.org/libc` v1.75.7. The [v1.59.0 source](https://gitlab.com/cznic/sqlite/-/tree/v1.59.0) describes a pure Go `database/sql` driver for macOS arm64 and Linux arm64. Its `go.mod` requires the matching `libc` pin. [mattn/go-sqlite3 v1.14.52](https://github.com/mattn/go-sqlite3/tree/v1.14.52) also uses `database/sql`, but its README requires cgo and a C compiler. Avoiding that build dependency is useful for the host and CI binaries.

The registry sets one open connection and enables foreign keys, as verified by file backed tests that also reopen the database. For this small roster, we accept the higher CPU time reported in the modernc release notes for three measured workloads against comparable C builds.

## Evidence

The [issue #28 evidence](https://github.com/tbhb/agent-orchestration-poc/blob/feat/28-registry-tmux/reports/inputs/registry-tmux-28-evidence-2026-09-26.md) records the source commits, release notes read, module pins, schema, and local checks. The clones are under `/private/tmp/agent28-modernc-sqlite` and `/private/tmp/agent28-mattn-sqlite3` because the sandbox cannot write to the standard dependency source location.
