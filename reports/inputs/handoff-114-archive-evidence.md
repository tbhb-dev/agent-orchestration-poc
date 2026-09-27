# Phase 2 handoff archive evidence

The coordinator note on PR #119 identifies the local prompt and generated state used to start incoming session `26834c4f-a585-4314-bb86-c1f6141aa9ee`. This report records the archive check for issue #114.

| Source in the main checkout's `.holding/handoff/` | Bytes | SHA-256 | Published page |
| --- | ---: | --- | --- |
| `2026-09-26-a8fde4b6.md` | 25,906 | `a7888b10db23243b1c52014fe1b8b5b52d28c620e7d5423893514f7b3c8ebfec` | `docs/src/content/docs/project/handoff-2026-09-26-prompt.md` |
| `2026-09-26-a8fde4b6-state.md` | 7,138 | `b7ff0e65996d8428cb277068cf4e1fd5de7dcc9412063d880f0dae89a7f5b965` | `docs/src/content/docs/project/handoff-2026-09-26-state.md` |

Verified: `mise exec -- gitleaks dir --redact --no-banner <source>` exited 0 for each source and reported no leaks. Manual inspection found locations and field names but no credential values. Redactions: none.

Verified: a byte comparison showed that each published page ends with the exact source bytes. The only prefix is site frontmatter and one provenance sentence. `mise run fmt` left both source suffixes unchanged.

Reproduced: `git show 7786728:docs/src/content/docs/project/handoff.md` has the 14-minute heartbeat instruction and an assignment row limited to coding, research, and first review. Commit `1c89c98` addressed both review findings; `b660b03` refreshed the roster. The archived prompt preserves the operator's later Monitor, merge-train, hourly fallback, and coordinator-only instructions as they were used at takeover.

Verified locally: `mise run check` completed all tasks, including coverage, and `mise run check:mutation` classified 89 Go mutants with none living and scored Python at 97.22%. `mise run build` and `mise run docs:build` passed. The site built both archive pages. `mise run docs:check-links` failed because sandboxed Chromium could not render existing Mermaid pages, causing five links in unchanged pages to be reported invalid. No reported invalid link targets either archive page.
