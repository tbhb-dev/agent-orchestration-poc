---
title: Temporary GitHub monitor startup
description: Coordinator startup, local state contract, and recovery handoff for issue 167.
---

## Scope

This temporary scaffold receives signed GitHub App webhooks for repository `1389534135` (`tbhb/agent-orchestration-poc`) and records local invalidations. It does not establish current GitHub state. The real monitor's proposed active-wait freshness lifetime is 120 seconds. This scaffold uses its own five-minute expiry for a complete REST observation after #179 adds repair.

## Coordinator start and stop

The coordinator controls the existing Funnel mapping and listener cutover. After checking that port 8787 is free, start the receiver in the foreground with the existing 1Password item reference:

```sh
GITHUB_INSTALLATION_ID=<verified-numeric-id> GITHUB_WEBHOOK_SECRET='op://tbhb.dev/github-app-tbhb-monitor/webhook_secret' op run -- mise run monitor:start
```

The command refuses an absent or empty `GITHUB_WEBHOOK_SECRET` and requires the coordinator's verified numeric `GITHUB_INSTALLATION_ID`. It binds only `127.0.0.1:8787` and accepts `POST /hooks/github`. Stop it with Ctrl-C or SIGTERM. Do not expose the local store or status command through Funnel.

## Local commands

Run `mise run monitor:status` to identify this listener or report another process on the port, then read store instance, schema version, revision, tracked count, receipt count, and signature failure counters. Run `mise run monitor:track -- pr 167` or `mise run monitor:track -- issue 167` to name an object explicitly. Tracking does not fetch GitHub data. The SQLite file is `.local-cache/github-monitor/state.sqlite3`, under the repository's existing ignored `.local-cache/` entry.

The programmatic `Store.register_watch()` returns a token and projection snapshot from one SQLite transaction. Ordinary snapshots also read one committed revision. A token includes store-instance UUID and revision. `Store.watch_state(token)` returns `waiting`, `changed`, or `unavailable`. Replacing the database changes its UUID, and restarting the receiver advances the revision and each component generation, fencing repairs captured before restart.

The projection reports `schema_version=1`, `store_instance`, monotonic `revision`, and per-object components. Each component reports generation, completeness, source IDs, head SHA where known, observation and expiry UTC times, and a stale reason. Missing fields are unknown. Signed webhooks set dirty and cannot clear it. A future complete REST repair must capture the component generation before collection and clear dirty only if it still matches at commit.

## Recovery and limits

Issue [#179](https://github.com/tbhb/agent-orchestration-poc/issues/179) owns `monitor:repair -- --tracked` and authoritative current-state collection. That command is unavailable in this PR. Before #179 is merged, tracked objects remain dirty, unknown, or restart-stale. Restart the receiver after a crash, inspect `monitor:status`, and hand the tracked set and generation contract to #179. GitHub may not redeliver failed events automatically, and REST repair cannot recreate every intermediate event.

The receipt table stores GUID and body digest without payload bytes. The receiver bounds each body at 25 MiB, parsed header fields at 16 KiB, and socket inactivity at five seconds starting before request parsing. Only verified deliveries for the allowlisted repository and configured installation ID can name tracked objects. Events with no PR number, including a status payload without a PR association, record a receipt without discovering objects. Unsupported events or actions record an inert receipt. No webhook supplies REST authority or merge permission.

The real design's [state and conditions](https://github.com/tbhb/agent-orchestration-poc/blob/main/docs/src/content/docs/design/github-event-monitor.md#state-and-conditions) and [loss and repair](https://github.com/tbhb/agent-orchestration-poc/blob/main/docs/src/content/docs/design/github-event-monitor.md#loss-ordering-and-repair) sections map this scaffold to permanent inbox and projection [item C](https://github.com/tbhb/agent-orchestration-poc/issues/189) and verified ingress [item E](https://github.com/tbhb/agent-orchestration-poc/issues/190).
