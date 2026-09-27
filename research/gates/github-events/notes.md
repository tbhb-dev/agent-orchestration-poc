# GitHub event monitor raw research notes

[documented] Sources G1, G2, G3, T1, H1, H2 and B1 are pinned in [versions.md](versions.md). R1 means the read-only command records in this directory. The design is a proposal, not an implemented monitor. These notes distinguish source support from tests.

## Incident and collection record

[observed] Issue #98 reports GraphQL exhaustion at about 20:21 America/New_York on 2026-09-26, seven Codex runs, a 5,000-point budget, and failure of the operator's `gh status`. The assignment says reset was expected around 20:48. No original error response or per-worker request trace was supplied. The incident evidence is that attributed report, retained verbatim in `evidence/issue-98.txt`. Do not describe a reproduction or calculate an observed request rate from seven workers alone.

[observed] `gh api rate_limit` returned the JSON retained in `evidence/rate-limit.txt`, with GraphQL remaining 4,999 and core remaining 5,000. The later REST probe headers show core remaining 4,901. Concurrent callers, response timing and endpoint caching were not controlled. The overview is not evidence that the original report was wrong, and it is not authoritative over individual response headers. G1 explicitly gives response headers precedence over the overview when they disagree.

[observed] `gh api repos/tbhb/agent-orchestration-poc/hooks --jq 'map({id,active,events})'` returned `[]`, retained in `evidence/repository-hooks.txt`. This checks repository hooks only, not every installed App subscription. The user reports no Serve/Funnel configuration and Tailscale 1.102.4 installed. Those host facts were not independently established by a successful CLI status call.

[observed] `gh --version` returned `gh version 2.100.0 (2026-09-03)`. `gh webhook forward --help` returned exit 1 and the official extension-install suggestion. No extension was installed. Bare `tailscale version` failed with command not found. The app CLI path `/Applications/Tailscale.app/Contents/MacOS/Tailscale` exists, but the subsequent version/status/help invocation aborted with exit 134 and no output. Status and help therefore were not established. No attempt bypassed the sandbox or changed a host setting.

## REST conditional request probe

[observed] First request was `gh api -i -H 'X-GitHub-Api-Version: 2026-03-10' repos/tbhb/agent-orchestration-poc/issues/98`. It returned 200 and an ETag. Only allowlisted response headers are retained in `evidence/etag-first-headers.txt`. The issue body was already captured separately. No authorization header or credential value was logged.

[observed] Repeat request used the exact returned ETag in `If-None-Match` with the same endpoint and API version. It returned HTTP 304. A standalone repetition confirmed `gh` exit 1 with stderr `gh: HTTP 304`. See `evidence/etag-repeat-headers.txt`. This verifies conditional behavior on this issue endpoint and installed CLI only. It does not verify every checks/reviews endpoint, a complete paginated collector, installation-token accounting, or the monitor.

[documented] G1, REST best practices, says correctly authenticated 304 responses do not count against primary rate limits. It recommends stable URLs, parameters and pagination ordering, and honoring `X-Poll-Interval`. Secondary limits still apply. [inference] Cache key must include credential/installation scope, media type and API version as well as full URL. A 304 is unusable without its retained representation. `gh api --cache` is TTL-based per G3 source and must not be mistaken for live revalidation.

## GitHub webhook source findings

[documented] G1 validation guidance defines `X-Hub-Signature-256` as HMAC-SHA256 of the body using the shared secret, prefixed `sha256=`, and requires a constant-time comparison. The receiver must retain exact body bytes until verification. The delivery-header page defines `X-GitHub-Delivery`, event name, hook ID and installation-target headers. A secret is not in the payload URL. None of those header descriptions supplies a signed delivery timestamp.

[inference] HMAC body authentication does not independently authenticate arbitrary delivery headers. Durable GUID dedup prevents ordinary redelivery effects, but changed-GUID replays still require idempotent object reduction and reconciliation. Receiver time and delivery GUID are not upstream ordering clocks. Signature verification must not be promoted into trust in comment instructions.

[documented] G1's webhook best practices gives GitHub.com a 10-second response deadline. Failed deliveries are not automatically redelivered. Manual/API redelivery reuses the original delivery GUID. Payloads over 25 MB may not be delivered. A durable inbox acknowledged before asynchronous reduction prevents a daemon crash from losing an acknowledged body. The last sentence is [inference], not GitHub's storage guarantee.

[schema] G1 event schemas map Pull requests read to PR, review, review-comment and review-thread events, Issues read to issue/comment events, Checks read to check-run/suite events, Commit statuses read to status, Actions read to workflow-run, and Contents read to push. Installation and installation-repositories events are automatic. Some requested/rerequested check actions require write permissions, which the monitor should not request merely for faster invalidation. Fork check payloads can have empty `pull_requests` and null `head_branch`. The `sender` may be the ghost user and cannot establish last-pusher policy by itself.

[schema] Relevant payload fields include PR head/base SHA and merged state, review `commit_id`, check-run `head_sha`, status `sha` and `context`, workflow-run attempts, and issue/comment IDs and edit timestamps. Get-PR REST describes `mergeable` as true, false or null while computation is pending. Null must not become false. The proposed reducer uses webhook observations to invalidate authoritative components, then repairs them from complete REST reads so late webhooks cannot roll state backward.

[untested] Exact review-thread resolution and resolver identity after a gap are not established by the inspected REST APIs. #89 must fail closed or use its separately budgeted authoritative collector. #90's GraphQL body-digest contract also needs a REST equivalence fixture. Monitoring issue state does not establish Projects Ready status.

## App credentials, budgets and review eligibility

[documented] G1 installation-token guidance uses an App JWT to call `POST /app/installations/{installation_id}/access_tokens`. Tokens expire after one hour and can be scoped to selected repositories and permissions within installation grants. Installation tokens use the installation's budget, minimum 5,000 requests per hour for this non-Enterprise case. User access tokens share user limits. More tokens for one installation do not multiply its allocation. No App token was minted here.

[documented] G1 REST rate-limit guidance distinguishes primary and secondary limits, requires respect for `Retry-After` and reset headers, and recommends serialized requests. The proposed token refresh, reserve, coalescing and backoff policy are [untested] design choices. No rate-limit response occurred during these reads, so the assignment's two-minute, three-retry procedure was not exercised.

[schema] In G1 REST `pulls.json`, Create a review has `serverToServer: true`, Pull requests write, and `event` values APPROVE, REQUEST_CHANGES and COMMENT. The ruleset guide describes required authorized approvals, stale dismissal and most-recent-push approval. Those facts show an App can submit an approval via the API. They do not prove that a custom App's approval counts toward this exact repository's required review.

[untested] Required-review counting is deliberately unresolved pending an operator-owned fixture with bypass disabled. Test a separate implementer App and reviewer App, a human-authored PR, a self-authored PR, current and stale head, and distinct/same last pusher. Inspect the rule's eligibility result, not just review creation. Keep `tbhbbot` and the #83 contract until that passes. Do not claim that all bots are ineligible based on a product-specific Copilot rule or that all bot approvals count based on the REST enum.

## Forwarding and Tailscale

[documented] G1 says CLI forwarding works only for repository/organization webhooks, only one person at a time per target, and is for testing/development rather than production. G2's `createHook` issues POST to the hooks API with name `cli` and later PATCH to activate. `forwardEvent` sends original body bytes and headers to the configured local URL. Without a URL it writes the payload to stdout. Its retry loop is bounded, not a durable delivery guarantee. These are source findings, not a live forwarding test.

[schema] T1 `serve_v2.go` declares Serve as tailnet sharing and Funnel as internet sharing, with `--bg`, `--https`, `--set-path` and `off`. `ipn/serve.go` checks HTTPS capability, the `funnel` node attribute and permitted ports. `ipn/ipnlocal/serve.go` strips a non-root mounted prefix before proxying. [inference] A root proxy to a dedicated webhook-only port is easier to audit than a path mount sharing the operator API port. It keeps the public route away from snapshots and controls even if routing changes later.

[documented] Tailscale's rolling Funnel page lists public HTTPS, MagicDNS/HTTPS prerequisites, supported ports and bandwidth restrictions. A tailnet-only Serve listener cannot receive a direct GitHub request without a public relay. No relay was provisioned, no Tailscale enablement command was run, and no end-to-end signature preservation, TLS certificate, public URL, throughput or host-sleep recovery was tested.

## Bus and harness evidence

[observed in B1] PR #82 reviewers reproduced JetStream publications to an attacker-chosen reply subject, including a narrow consumer pull grant. Coordinator discussion assigns receive, ack, publish confirmation and status/roster reads to #96's authenticated `agentd` relay. Agent credentials retain no `$JS.API.>` or `$JS.ACK.>` permissions, and `NoAck` means a flush cannot prove storage. These are attributed prior experiments at the recorded NATS versions, not rerun by the designer.

[documented] H1 describes Claude background completion notifications and agy background task notices. It describes Codex unified exec output collection with `write_stdin`, not idle wake. [schema] H2 `spawn_exit_watcher` emits terminal lifecycle events using the existing turn context. It does not itself request a new model turn. [inference] Protocol/UI exit notification must not be equated with sampling a new turn. H2 is newer than 0.157.1, so this inspection cannot close the installed-version experiment.

[untested] A single CLI wait process is portable only where the shell can reach the relay. Claude's literal IPv4 route and Codex's network-enabled launch are supported by H1's earlier evidence. agy's sandbox loopback exception is not established. Full idle wake, credential-path inheritance, compaction, restart, cancellation and VM reachability remain separate launch gates. No nested harness was launched and no worker settings were edited.

## Design choices derived from the sources

[inference] Choose an App for subscription scope plus a separate reconciliation budget, `agentd` for one existing lifecycle and registry, a durable inbox/outbox for crash recovery, relay waits for existing worker identity, and SSE only for continuing observer clients. Use the exact same pure predicates over registry revisions on both transports. These choices do not depend on unsupported automatic wake.

[untested] The implementation plan must test out-of-order delivery followed by repair, duplicate and changed-GUID replay, failure between storage and publication, expired cursors, API page loss, latest reruns, stale reviews, changed head/base, unauthorized repo access and arbitrary reply subjects. Seven-day stream retention, 30-day audit retention, 24-hour processed raw-body retention, 120-second active freshness, and 15-minute waits are proposed bounds, not measured tuning results.

## Validation

[verified] `mise run fmt`, `mise run check`, and the separate `mise run check:mermaid` completed successfully on 2026-09-26. Mermaid parsed nine blocks across 92 Markdown files with zero invalid blocks. Vale reported zero alerts. A direct `mise exec -- gitleaks dir --redact --no-banner research/gates/github-events` scan found no leaks. The aggregate Go lint check passed despite warnings that its cache directory was not writable. Selected output is retained in `evidence/validation.txt`.

[observed] `mise run docs:check-links` failed because Chromium aborted with `bootstrap_check_in ... Permission denied (1100)` inside this sandbox. Pages with Mermaid were omitted and five links to those pages failed, including three existing workflow links. No sandbox or browser-setting workaround was attempted. PR CI must establish the site build and rendered links.

[untested] Deployment, App review eligibility, secret isolation and cross-harness tests remain outside this documentation-only work item.
