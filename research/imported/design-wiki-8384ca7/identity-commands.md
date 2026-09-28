---
title: Identity commands
summary: "Proposed workload identity inspection, operator administration, and protected backend credential resolver commands."
type: design
status: draft
tags:
  - area/identity
  - area/ux
  - scope/destination
updated: 2026-09-28
---

**Proposed initial sketch, 2026-09-27:** These command names are illustrative, not installed or validated commands. They map to the [identity API](identity-api.md), [schema](identity-schema.md), and [data flow](identity-data-flow.md), under the [SPIFFE authentication contract](spiffe-mtls-authentication.md). The [threat model](identity-threat-model.md) governs credential handling. `identity-` prefixes this document family; executable namespaces remain `agentw` and `agentctl` as in the existing wiki.

## Workload surface

```sh
agentw identity show --format json
```

This calls `GET /v1/identity` through the configured wrapper or runtime proxy and shows the effective participant, authentication method, and current workload binding. It accepts no `--as`, sender, role, or incarnation override. Host agentw gets only its gateway endpoint; sbx agentw also receives the runtime's placeholder. Neither path exposes real credentials. Ordinary [messaging commands](messaging-commands.md) use this same authority automatically.

Identity inspection is not a local token decoder and does not certify the sandbox. If authentication fails, report the safe reason without printing an Authorization header or suggesting a credential-bearing direct connection. Agentw has no enrollment, credential-export, bot-registration, or policy-management commands.

## Operator surface

| Proposed command | API mapping and meaning |
| --- | --- |
| `agentctl identity show PARTICIPANT --format json` | Authorized identity inspection; show kind-specific binding, status, revisions, and visible grants. |
| `agentctl identity audit --participant PARTICIPANT --format json` | Paginated identity-event metadata under audit permission. |
| `agentctl identity bot register --name NAME --request-id ID` | Register a bot, initially without grants. Return stable participant ID and pending enrollment status. |
| `agentctl identity bot enroll BOT --method x509-svid --request-id ID` | Begin the selected protected enrollment flow; attestation and custody must be configured first. JWT is the other proposed method. |
| `agentctl identity bot cutoff BOT --expected-revision N --request-id ID` | Propose advancing generation and invalidating all old enrollments; require authorized re-attestation. Ordinary renewal preserves generation; registration revocation blocks the participant. |
| `agentctl identity bot revoke BOT --expected-revision N --request-id ID` | Revoke the bot across all installations while preserving historical identity. |
| `agentctl identity installation create --participant BOT --scope group:GROUP --grants-file PATH --request-id ID` | Create explicit bot grants under delegated authority. `--scope host` denotes this agentd's host scope; no remote host selector is implied. |
| `agentctl identity installation revoke INSTALLATION --expected-revision N --request-id ID` | Revoke this installation only; report that other grants may remain. |

Finite administrative commands emit one complete result, support explicit `--format json|text`, and send diagnostics to stderr. Text-versus-JSON default remains open. Mutations report affected stable IDs and resulting revisions; they do not print enrollment secrets, private keys, or tokens. Enrollment delivers credentials through the configured protected mechanism rather than this human-readable result. The selected issuer/bootstrap flow must make that mechanism concrete before the enroll command is runnable. A protected pairing channel or explicitly protected output file is a candidate for enrollment handoff, not yet a selected flag or secret-output behavior.

Grant files name exact permissions and scope, rather than converting a capability list into grants. Bridge inbound assertion and outbound relay permissions remain separate. Installation creation does not silently join every conversation. Cross-Group DM policy and ambient bot membership remain open in [Participants and permissions](participants-and-permissions.md).

## Lifecycle integration and protected resolver

Each mode selects exactly one principal class: operator administration, workload wrapper, or enrolled resolver. Wrapper/resolver modes never read operator credentials or fall back to them. Missing enrollment fails closed. Operators authorize enrollment rather than receiving issued workload credentials through the administrative mode. These are proposed least-privilege rules, not a same-UID isolation guarantee.

Normal workload launch/resume/suspend commands should orchestrate the reserve/enroll/activate/fence API sequence inside the existing workload-management surface; do not require users or agents to hand-assemble credentials. These command names remain outside this sketch. A displayed workload name, native conversation ID, or terminal reattachment is never an enrollment proof. On sbx resume, remove the old resolver binding and bind the new immutable incarnation before activation; never substitute a stable workload ID with a latest-incarnation lookup.

Retain the authentication page's proposed runtime resolver spelling:

```sh
agentctl worker-token WORKLOAD_INCARNATION_ID
```

This is a trusted backend helper, not an agentw operation or ordinary operator credential export. It authenticates through its narrowly authorized enrollment, verifies the immutable incarnation is active, and uses the credential-issuance route to obtain a JWT with agentd's configured audience and lifetime. The ID argument selects a target; the resolver's authenticated entitlement must match it. There are no caller-selected participant, audience, role, or lifetime overrides.

On success, stdout contains only the JWT captured privately by the runtime. On failure, return nonzero, empty stdout, and a sanitized stderr diagnostic. Never print progress or JSON to resolver stdout, echo a stale token, or persist token output in logs. Configure the runtime with a trusted absolute executable path and shell-safe immutable ID, sandbox-specific injection, and a fixed destination. The [sbx setup sketch](spiffe-mtls-authentication.md#runtime-mediated-jwt-authentication) remains untested; this page does not turn it into a working installation recipe.

Normal credential rotation stays automatic in the custody component. Do not add an agent-facing refresh command or repair an issuer outage by changing guest credentials. Optional MCP tools must preserve the same workload binding and API allowlist; a tool named “identity” cannot enroll an independent principal.

## Failure and review behavior

Propose exit `0` for a complete successful result, `2` for invalid syntax, and `1` for authentication, authorization, conflict, or service failure, with structured error codes in JSON mode. Final exit-code allocation is open. Do not silently retry a revision conflict against a different incarnation. Lost mutation responses reuse the original request ID after reconciliation; credential issuance follows its separate API retry contract.

Inspection and revocation output should distinguish credential expiry, fenced incarnation, revoked bot registration, and revoked installation. Those failures have different recovery actions. A command cannot override them by using a display name or by disabling TLS verification. Exact interactive confirmation conventions belong to the later CLI UX design; none of these examples authorizes changes to host trust stores.

## Deferred command additions

IR-16 proposes participant/enrollment/installation lists, public trust-state inspection, and a distinct transient-failure exit code. Keep these as follow-on interface design; add matching scoped API routes before exposing commands. Current structured error codes distinguish retryable service failures from denied authority.

## Provenance

The `agentw`/`agentctl` split follows the existing messaging and authentication pages; `worker-token` is an existing proposed resolver name. The identity command namespace, administration mappings, and output/exit behavior are new Codex proposals requested on 2026-09-27. No executable, enrollment, credential, or runtime configuration was created or tested.

**Review integration, 2026-09-28:** Revised against [Claude’s preliminary review and Codex disposition](identity-preliminary-review-claude.md#codex-reconciliation). Corrections and new recommendations remain proposed; no issuer, bootstrap, liveness policy, or operator installation model is selected.
