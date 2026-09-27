# GitHub event monitor research versions

[observed] Research date 2026-09-26 America/New_York, with REST probe response time 2026-09-27T00:34:43Z. Worktree base `ee61cb093bcb229bfdab498183ae5f22e595fc14`. Designer assignment is Codex CLI 0.157.1, `gpt-6-astra`, medium. Source inspections below are schema or documented evidence, not runtime verification.

## Source checkouts

[observed] New checkouts live under `/var/folders/ns/cc4x7s5j5271ltrw1t08w7p40000gn/T/github-events-98/`, the session's `$TMPDIR`. The allowed writable roots exclude `~/Code/github.com` outside this worktree. An attempted read of a missing tagged object in the existing partial Tailscale clone triggered a promisor fetch that failed with `Operation not permitted`, so the tagged source was cloned into the allowed temporary directory. No installation or host setting was changed.

| ID | Repository and version | Commit read | Commit date | Checkout |
| --- | --- | --- | --- | --- |
| G1 | `github/docs`, GitHub.com documentation, REST `2026-03-10` | `18945a31a4f2d97beb6c5c1a7479102e23c25727` | 2026-09-25T16:28:57-07:00 | `$TMPDIR/github-events-98/github-docs` |
| G2 | `cli/gh-webhook`, default branch snapshot | `115d4d6768b55c74ee7d7c61d4775d83fdc323d2` | 2025-10-21T10:21:17-06:00 | `$TMPDIR/github-events-98/gh-webhook` |
| G3 | `cli/cli`, v2.100.0 | `45437bc7eeeb3359bbfddd1742f79de7652fd3e2` | 2026-09-03T17:24:19+02:00 | `$TMPDIR/github-events-98/cli` |
| T1 | `tailscale/tailscale`, v1.102.4 | `bbcd7d1fc2054b9189ebc1531acf74bd880ca0c8` | 2026-09-10T10:45:34-07:00 | `$TMPDIR/github-events-98/tailscale` |
| H2 | `openai/codex`, existing source HEAD, newer than installed release | `a6bd19261c30ce0a0225fe90e646822d29916f11` | 2026-09-26T17:31:48Z | `/Users/tony/Code/github.com/openai/codex` |

[documented] H1 is `experiments/00-system-assessment/harness-research.md` and `permission-facts.md`, read with the project plan. It records Claude Code 2.1.283, Codex CLI 0.157.1, and agy 1.2.11. H1 distinguishes Codex release commit `36650394c5b3` from the newer source HEAD. The new H2 inspection therefore does not establish installed-release behavior.

[documented] B1 is the REST capture of PR #82 metadata, discussion, inline comments and reviews, plus issue #96. Those reviews record nats-server v2.15.0 and nats.go v1.54.0. The earlier `nats-research.md` inspected server `3e8ddaa7` and client `5adc9d5d`, which are later development snapshots. Its API findings are background evidence, while the relay decision comes from B1's versioned probes.

## Documents and source files read

[documented] G1 paths below are relative to its checkout and pinned by the commit above. GitHub.com documentation has no product release tag, so the commit is the document version. Pages were read on 2026-09-26. The REST schemas selected are `fpt-2026-03-10`, not Enterprise Server variants.

- `content/webhooks/webhook-events-and-payloads.md` and `data/reusables/webhooks/payload_cap.md`.
- `content/webhooks/using-webhooks/validating-webhook-deliveries.md`, `best-practices-for-using-webhooks.md`, and `handling-failed-webhook-deliveries.md`.
- `content/webhooks/testing-and-troubleshooting-webhooks/using-the-github-cli-to-forward-webhooks-for-testing.md`.
- `content/apps/creating-github-apps/registering-a-github-app/using-webhooks-with-github-apps.md` and `choosing-permissions-for-a-github-app.md`.
- `content/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app.md` and `data/reusables/apps/generate-installation-access-token.md`.
- `content/rest/using-the-rest-api/rate-limits-for-the-rest-api.md` and `best-practices-for-using-the-rest-api.md`.
- `data/reusables/rest-api/primary-rate-limit-github-app-installations.md` and `secondary-rate-limit-rest-graphql.md`.
- `content/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets.md`, required-review sections, and the approval guide under `content/pull-requests/how-tos/review-pull-requests/`.
- `src/webhooks/data/fpt/{pull_request,pull_request_review,pull_request_review_comment,pull_request_review_thread,issues,issue_comment,check_run,check_suite,status,workflow_run,push,installation,installation_repositories}.json`, event descriptions and parameter schemas.
- `src/rest/data/fpt-2026-03-10/pulls.json`, get-PR and create-review entries. Endpoint support, body parameters and token permissions were inspected.

[schema] G2 source inspected is `README.md`, `webhook/create_webhook.go` and `webhook/forward.go`. G3 source inspected is `pkg/cmd/api/api.go` for `--cache`, TTL and header options. The installed `gh --version` reported `2.100.0 (2026-09-03)`.

[schema] T1 source inspected is `cmd/tailscale/cli/serve_v2.go` for Serve/Funnel modes, `--bg`, `--https`, `--set-path`, `off`, and status syntax, `ipn/serve.go` for Funnel capability checks, and `ipn/ipnlocal/serve.go` for proxy path handling. The annotated tag resolves to commit `bbcd7d1fc2054b9189ebc1531acf74bd880ca0c8` in the fresh checkout.

[documented] Live first-party pages read on 2026-09-26 are [Funnel](https://tailscale.com/docs/features/tailscale-funnel), [Funnel CLI](https://tailscale.com/docs/reference/tailscale-cli/funnel), and [Codex App Server](https://learn.chatgpt.com/docs/app-server). No publication date was established for those rolling pages. Version-sensitive Tailscale command syntax is grounded in T1. The Codex page distinguishes protocol process-exit notifications from starting a model turn.

[schema] H2 source inspected is `codex-rs/core/src/unified_exec/async_watcher.rs`, `spawn_exit_watcher` and `emit_exec_end_for_unified_exec`, and output collection in `process_manager.rs`. H1 supplies the installed-version caveat and shell tool names. No new harness, service, or nested agent was launched.

## Repository inputs

[documented] Read `AGENTS.md`, the project plan's Names, Build group, Permission modes, Phase 2 and Departures sections, both requested messaging/bootstrap sketch pages, all current design pages, docs-stack conventions, and the three requested system-assessment reports. At this worktree base the design section contained only `index.md`. PR #82's bus page was described by its PR and reviews but had not landed in this checkout.

[observed] REST captures in `evidence/` contain full issue bodies and all available comment pages for #98, #72, #89, #90, #96, #28, #33, #49, #54 and #83. PR #82 includes metadata, reviews, inline review comments and issue-style discussion. Commands used `gh api repos/tbhb/agent-orchestration-poc/issues/<n>` and `gh api --paginate .../comments`, and the equivalent `pulls/82` paths. Files have `.txt` suffixes to retain raw JSON responses without JSON reformatting, with a terminal newline added by the repository hook. No GraphQL issue read or check watch was used.
