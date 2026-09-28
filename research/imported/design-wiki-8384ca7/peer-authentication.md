---
title: Peer authentication design supersession
summary: "Why the former PID and native-session authority model is obsolete, and where the current authentication contract lives."
type: design
status: superseded
tags:
  - area/identity
  - area/security
  - scope/destination
updated: 2026-09-27
---

The original PID-ancestry-only authentication architecture is obsolete. Use [SPIFFE workload authentication](spiffe-mtls-authentication.md) for the current design and [initial backend validation spikes](backend-validation-spikes.md) for PoC planning. The [historical design and evidence](peer-authentication-historical.md) remain available for provenance, not as implementation requirements.

## What was replaced

- Agentd identifying each workload request through local TCP socket ownership and process ancestry.
- A local agentd inside every execution boundary attesting PID/native-session bindings to another control plane.
- The `(pid, native session ID, role)` tuple as the durable authority model and automatic native-conversation rebinding as its integration path.
- One shared Codex app server per boundary as a mandatory topology requiring trusted per-thread process mapping.

Agentd now authenticates workload requests with X.509-SVID mTLS or a runtime-injected JWT-SVID over TLS, then applies shared workload/incarnation, Group, role, and operation checks. Native conversation IDs support history and resume; they do not confer authority. Host mode and Docker Sandboxes are the initial backend targets; the bespoke microVM/sidecar topology is deferred.

## What remains relevant

Kernel peer identity and process-membership checks remain proposed for the local agentw-to-wrapper hop in host mode. They authorize use of that workload's credential-holding gateway; they are not an alternative to SPIFFE authentication at agentd. Their exact algorithm and harness compatibility remain BV-01/BV-02 validation questions.

Cross-workload impersonation prevention, protected management authority, stale-incarnation fencing, and the distinction between identity and intent remain requirements. The historical machinery used to pursue them does not. Retaining the archive does not revive its backlog.
