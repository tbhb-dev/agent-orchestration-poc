---
title: "0001: Go linter is golangci-lint"
description: Why golangci-lint through mise, not standalone staticcheck.
---

## Status

Accepted 2026-09-26 for issue #14 (research/gates/go/notes.md §5).

## Context

The required Go 1.27.1 toolchain names no third-party linter. The candidates were standalone staticcheck 2026.2.1 and golangci-lint 2.14.0, both installable through mise's aqua backend and both supporting Go 1.27 (research/gates/go/versions.md; research/gates/go/notes.md §5).

## Decision

Use golangci-lint 2.14.0 through mise with a v2 config and `linters.default: standard`; use gofumpt 0.12.0 as the formatter and do not install standalone staticcheck (golangci-lint/pkg/lint/lintersdb/builder_linter.go; research/gates/go/notes.md §§4–5).

## Consequences

The `check` task needs one third-party lint command alongside formatting, vetting, module checks, build, and tests; golangci-lint's standard group provides `errcheck`, `govet`, `ineffassign`, `staticcheck`, and `unused`, and v2.14.0 bundles gofumpt 0.12.0 as a configurable formatter (golangci-lint/pkg/lint/lintersdb/builder_linter.go; golangci-lint/CHANGELOG.md; golangci-lint/.golangci.reference.yml; research/gates/go/notes.md §§4–5).

Pin golangci-lint 2.14.0 and gofumpt 0.12.0 in `mise.toml`, configure `linters.default: standard`, and require `//nolint:name // reason` for an inline suppression; these pins and configuration belong to the later tooling implementation (golangci-lint/docs/content/docs/configuration/file.md; research/gates/go/notes.md §5).

Reopen this decision if a pinned golangci-lint release drops timely Go support, changes standard-group coverage materially, or produces a sustained false-positive or runtime burden in this repository; the two-package trial alone cannot establish that burden (research/gates/go/notes.md §5).

## Evidence

The trial module had seven seeded issues. Go 1.27.1 `go vet ./...` reported one `hostport` finding; staticcheck 2026.2.1 reported three by default and four with `-checks all`, but neither run caught unchecked `f.Close()`; golangci-lint 2.14.0 reported eight, including `errcheck` on `Close`, `govet` findings, staticcheck findings, and `unused` (research/gates/go/notes.md §5).

golangci-lint 2.14.0 uses `honnef.co/go/tools` v0.8.1, the same analyzer source as staticcheck 2026.2.1; its standard group adds `errcheck`, `ineffassign`, `unused`, and a go vet superset, and golangci-lint has supported Go 1.27 since v2.13.0 (golangci-lint/go.mod; golangci-lint/pkg/golinters/staticcheck/staticcheck.go; golangci-lint/CHANGELOG.md; research/gates/go/notes.md §5).

On the two-package macOS arm64 trial, warm runs took 0.13 seconds for staticcheck and 0.29 seconds for golangci-lint; no false positives appeared among golangci-lint's eight findings (research/gates/go/notes.md §5).
