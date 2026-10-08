---
title: Process incident management
description: Declaration, response, manual tracking-write breaker, and review rules for process failures.
---

A process incident is a failure of the coordination process, even when a product defect also exists. Any worker may report a suspected incident to the coordinator with a bounded source that states the time and affected work. The coordinator declares it and assigns a lead. The coordinator opens one stable record URL and records later severity or status revisions with UTC time and reason. If the coordinator is unavailable, the reporter preserves evidence and alerts the operator for an apparent SEV1 or operator-boundary change.

## Severity and record contract

| Severity | Declaration test | Review due after recovery |
| --- | --- | --- |
| SEV1 | Immediate safety or credential exposure requiring operator control. | Within one day. |
| SEV2 | Work stopped across workers or material repeated cost. An open tracking-write breaker is at least SEV2. | Within three days. |
| SEV3 | Localized recoverable failure or near miss. | By the next retrospective. |

Notify the operator immediately for SEV1 and any proposed credential, host, or sandbox-policy change. For SEV2, notify within the coordinator's next heartbeat, and immediately if an operator boundary is involved. Report SEV3 at the next handoff. The coordinator records the notification time or `unknown` in Response. Severity may change when evidence changes. A revision retains the previous value, time, author, and reason in Response.

The incident URL is the committed page under `/workflow/incidents/<Incident-ID without INC- prefix in lowercase>/`, as shown by [INC-2026-09-27-001](/workflow/incidents/2026-09-27-001/). Revisions use the same URL. Use exactly these record field names: `Incident-ID`, `Started-UTC`, `Detected-UTC`, `Ended-UTC`, `Severity`, `Status`, `Reporter`, `Lead`, `Category`, `Impact`, `Evidence`, `Response`, `Cause`, `Actions`, and `Review-URL`. Timestamps are `YYYY-MM-DDTHH:MM:SSZ`, URLs are absolute `https://` URLs or site-root paths, and unavailable facts are `unknown`. Do not substitute an estimate for an unknown timestamp. `Incident-ID` is `INC-YYYY-MM-DD-NNN`, where the date is the declaration date in UTC. `Severity` is `SEV1`, `SEV2`, or `SEV3`. `Status` is `declared`, `containing`, `recovering`, `resolved`, or `reviewed`. `Category` is `tracking`, `worker-stop`, `review`, `duplicate`, `coordination`, `capacity`, `safety`, or `other`. Reporter and Lead are named people or worker IDs, or `unknown`. Impact, Evidence, Response, and Cause are bounded prose with source URLs and explicit evidence labels, or `unknown`.

`Actions` is a Markdown table with columns `Action-ID`, `Target-URL`, `Owner`, `Status`, and `Verification-URL`. IDs are `A-NNN` unique within the incident. A target is a stub or issue URL, or `unknown` while the intake request is pending. Status is exactly `proposed`, `accepted`, `in-progress`, `verified`, or `rejected`. Verification is an absolute `https://` URL or `unknown`. A verified action needs a verification URL. Each record has one Actions table, including an `unknown` row if no action is known. The [template](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/docs/briefs/process-incident-template.md) and [count fixture](https://github.com/tbhb-dev/agent-orchestration-poc/blob/main/reports/inputs/process-incident-evidence.md#action-state-count) show the table format.

## Response and recovery

1. The coordinator declares severity, lead, and the stable URL. The lead records `Started-UTC` and `Detected-UTC` separately, using `unknown` when necessary.
2. Contain ongoing cost or exposure. Pause affected dispatch or writes, protect credentials, and tell the operator about any operator-boundary remedy. Preserve bounded request identifiers, UTC times, response status and rate-limit headers. Redact credentials and private session material.
3. State the owner of each response step and the next UTC update time in Response. Running workers may finish and preserve results. Do not launch replacements while the applicable breaker is open.
4. Recover through the relevant procedure. For stopped runs, use [#153](https://github.com/tbhb-dev/agent-orchestration-poc/issues/153) and link its settled report when available. Use [#18](https://github.com/tbhb-dev/agent-orchestration-poc/issues/18) for silence detection rather than recreating its collector.
5. Record the completed recovery and independent read-back before setting `Ended-UTC` and `resolved`. Record each status change with UTC time and reason. Keep `unknown` where the proof is absent.
6. Complete a blameless review by the severity deadline. Set `Review-URL` and `reviewed` only after the review is linked.

## Manual tracking-write breaker

Tracking writes include Project field edits, issue and PR state changes, labels, and role comments. For each failed write, record UTC time, write kind, authenticated account, endpoint, request identifier or sanitized request, response status/body summary, and response headers including `x-ratelimit-limit`, `x-ratelimit-used`, `x-ratelimit-remaining`, and `x-ratelimit-reset`. An explicit rate-limit refusal counts as a failure. The summary rate-limit endpoint is diagnostic context only and cannot replace the failed response's headers.

Group failures by the exact `(write kind, account, endpoint)` tuple. When any group reaches three failed writes in any rolling ten-minute UTC window, the coordinator opens the breaker and declares at least SEV2. Record the three timestamps and source references, opening time, affected account, and scope in the incident. The threshold is inclusive at ten minutes. A success does not erase earlier failures in that window. A failure in a different tuple does not count toward it. If failures spread, the coordinator widens the recorded scope and records why.

While open, pause new worker launches, dispatches, issue or PR authoring, and routine tracking writes for the affected account. Permit read-only diagnosis, incident and repair records, missed-write reconciliation, and reviews through an unaffected reviewer account. Running workers finish and preserve results without replacement launches. Record any repair write as reconciliation, including its account and read-back. A reviewer account's successful call does not establish recovery for the affected account. The operator alone authorizes credential or host remedies.

Only the coordinator closes the breaker. First establish that the underlying failure is resolved on the affected account. List every missed write and either apply it with a successful read-back or mark it verified obsolete with the reason and read-back. Freshly read GitHub and Project state and compare it with completed work. Link the reconciliation evidence from the incident, then record breaker close time and the decision to resume. An available budget, HTTP success without read-back, or an unaffected account's success is insufficient. If any required state is `unknown`, keep the breaker open.

## Review and actions

The review separates trigger, contributing conditions, detection gap, impact, helpful response, disputed or unknown cause, and verified follow-ups. Worker or model blame is not a system cause. Record response time from `Detected-UTC` to containment only when both times are supported. At the next retrospective, report incident counts by severity and category, unresolved action states, recurring causes, and supported response times with unknown denominators shown.

An accepted action goes through the current approved issue path. When the work-model intake process is activated, send new work to its dedicated intake agent for duplicate review and a Project stub before issue refinement. [#161](https://github.com/tbhb-dev/agent-orchestration-poc/issues/161) was closed without a merged design, so its earlier proposal is not an active intake path. Do not bypass [#90](https://github.com/tbhb-dev/agent-orchestration-poc/issues/90) review. The proposed `tracking-write-breaker-automation` stub is for a durable wrapper that reads response headers and applies this policy. Existing [#170](https://github.com/tbhb-dev/agent-orchestration-poc/issues/170), [#171](https://github.com/tbhb-dev/agent-orchestration-poc/issues/171), and [#182](https://github.com/tbhb-dev/agent-orchestration-poc/issues/182) own temporary monitor admission, write helpers, and Project sync. Check those owners for duplication before intake, and retain manual breaker control under this page.
