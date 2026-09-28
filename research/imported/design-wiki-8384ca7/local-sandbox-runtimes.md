---
title: Local agent sandbox runtimes
summary: "A comparison of Docker Sandboxes alternatives for workload launch, external credential custody, and agentd integration."
type: research
status: active
tags:
  - area/containers
  - area/identity
  - area/orchestration
  - scope/destination
updated: 2026-09-27
---

This survey informs [execution isolation](execution-isolation.md) and [workload placement](mental-model.md#workload-placement-extensibility). The target is a locally managed, potentially long-lived harness workload that can call agentd without receiving its real authentication credential. Supporting arbitrary command execution alone is insufficient.

## Evidence and recommendation

**Documented, accessed 2026-09-27:** Capabilities below come from first-party documentation and repository pages. These are mutable documentation snapshots, not a release-pinned compatibility matrix. No runtime was installed, executed, benchmarked, or security-tested. Attempts to resolve repository HEADs through the GitHub API failed because the shell could not connect; version-specific qualification remains required. The subsequent operator decision selects host mode and Docker Sandboxes as the [initial backend targets](spiffe-mtls-authentication.md#initial-backend-scope); the alternatives below remain research.

**Earlier proposal, deferred by the initial backend decision:** Probe Matchlock first for a direct runtime integration, then Gondolin for programmable mediation. Evaluate microsandbox alongside them if persistent VM state and branching become priorities. Study OpenShell as an architectural comparison and potential integrated backend; evaluate agentcage for reuse of its Apple Container integration. This order reflects fit to our contracts, not an established security or maturity ranking.

## Closest alternatives

| Candidate | Documented execution surface | Credential mediation | Integration assessment |
| --- | --- | --- | --- |
| Matchlock | Linux KVM and Apple Silicon macOS microVMs; OCI images; CLI and Go/Python/TypeScript SDKs | Host proxy replaces destination-scoped placeholders | Direct backend candidate; explicitly experimental |
| Gondolin | macOS/Linux microVMs; QEMU default, optional krun; TypeScript SDK and CLI | Host HTTP hooks substitute scoped placeholders | Flexible mediation; separate Node runtime to integrate |
| microsandbox | Local microVMs on Apple Silicon macOS, Linux KVM, and Windows WHP; CLI and SDKs | Host TLS proxy substitutes destination-bound placeholders | Persistent and branchable workloads; explicitly beta |
| NVIDIA OpenShell | Gateway-managed Docker, Podman, Kubernetes, and MicroVM drivers | Provider profiles bind credentials to endpoints | Closest broader architecture; control-plane ownership to reconcile |
| agentcage | Rootless Podman, Apple Container, and Lima backends | Inspecting proxy and configurable secret substitution | Existing Apple Container integration; inspect backend-specific trust boundaries |

Sources and qualifications for each row follow.

### Matchlock

**Documented:** Supports detached long-lived VMs, interactive exec, output streaming, and SDK-driven lifecycle. Its architecture uses Firecracker on Linux and Virtualization.framework on macOS. Secret configuration triggers network interception; macOS's default NAT path is a different mode. The README labels the project experimental. [Project and examples](https://github.com/jingkaihe/matchlock).

**Inference:** An agentd token appears to fit its general secret-binding interface. **Unknown:** Injection to a host-local endpoint on our chosen port, credential rotation, live terminal reconnection, and cross-VM binding isolation. Network hooks expose request mutation, useful if fixed header insertion is preferable to placeholder substitution. [Network interception](https://github.com/jingkaihe/matchlock/blob/main/docs/network-interception.md).

### Gondolin

**Documented:** Host-side JavaScript controls networking and virtual filesystem behavior. The project describes itself as early. [Overview](https://earendil-works.github.io/gondolin/).

Secret scopes and global network allowlists are separate. Default substitution covers HTTP headers, including bearer credentials; query substitution is optional, while bodies are not substituted. Host hooks may observe real credentials after substitution. [Secrets handling](https://earendil-works.github.io/gondolin/secrets/).

The CLI has interactive and noninteractive execution, running-session discovery, and snapshots. Crucially, `attach` starts a new interactive command in the existing VM; it does not establish reconnection to the previous harness PTY. [CLI](https://earendil-works.github.io/gondolin/cli/). HTTP/2 and HTTP/3 are unsupported in its documented mediation path, which matters if agentw uses gRPC rather than HTTP/1-compatible requests. [Limitations](https://earendil-works.github.io/gondolin/limitations/).

**Inference:** A per-VM host hook could implement the application gateway directly. **Unknown:** Host service routing, terminal continuity, and recovery after the controlling process exits.

### microsandbox

**Documented:** Offers OCI images, named and detached sandboxes, create/exec/start/stop, snapshots, branching, and embeddable SDKs. Its README labels it beta. [Project](https://github.com/superradcompany/microsandbox).

Its credential boundary explicitly trusts host memory. SDK-supplied secret values can also persist in host configuration; environment references avoid storing the value there. TLS interception checks destination identity before substitution. An allowed endpoint can still return the real credential to the guest. [Secret handling](https://docs.microsandbox.dev/security/secrets).

Default networking blocks private, host-local, and metadata destinations, making access to local agentd a specific integration question. The documented CLI secret example is tied to version 0.7.3; it does not establish an installed version here. [Credential walkthrough](https://microsandbox.dev/blog/sandboxes-that-lie-about-their-secrets).

**Unknown:** The narrowest local host-access exception, persistent PTY behavior, and whether restoring or branching a VM duplicates authority. A restored workload must receive an authorized incarnation rather than automatically reusing saved identity.

### NVIDIA OpenShell

**Documented:** Includes a gateway control plane, provider management, CLI, and multiple SDKs. Its support matrix lists Docker, Podman, Kubernetes, and libkrun-based MicroVM drivers, with platform-specific prerequisites. [Project](https://github.com/NVIDIA/OpenShell), [support matrix](https://docs.nvidia.com/openshell/latest/about/support-matrix).

Custom provider profiles can bind credentials to host, port, and path; network permission and credential permission are separate checks. Header substitution supports bearer authentication, so our endpoint is not inherently limited to a built-in model-provider integration. [Providers](https://docs.nvidia.com/openshell/latest/how-it-works/providers/overview).

**Documentation discrepancy:** The overview retrieved during this survey says the supervisor runs inside each sandbox workload, while the repository architecture describes a separate supervisor outside the workload and an in-workload sandbox component. Treat that as a version/alignment question. The latter design also describes protected channels, workload generations, and reconnection fencing. [Overview](https://docs.nvidia.com/openshell/latest/about/how-it-works), [repository architecture](https://github.com/NVIDIA/OpenShell/blob/main/architecture/sandbox.md).

**Inference:** Potentially reusable as a complete backend, but adopting it creates an explicit boundary between agentd's workload/Group authority and OpenShell's runtime/policy authority. **Unknown:** Release-specific topology, local endpoint policy, and attachment behavior.

### agentcage

**Documented:** Supports service, interactive, and ephemeral lifecycles, domain policies, and custom environment-to-destination secret bindings. Backend differences include filesystem and mount behavior; the Apple Container backend targets macOS 26+ on Apple Silicon. [Project and backend matrix](https://github.com/agentcage/agentcage).

**Inference:** Useful as a future backend candidate and prior art for the deferred Apple Container profile. **Unknown:** Where the proxy and credentials reside in the selected backend, whether guest privilege can reach them, and how to permit exactly agentd without opening broader host access. Do not infer a separate credential microVM from the term proxy.

## Adjacent tools

Anthropic's [sandbox-runtime](https://github.com/anthropics/sandbox-runtime) is an OS process-confinement building block rather than the VM runtime sought here. A macOS outer Seatbelt layer is excluded from this exploration because the operator requires preserving the harness's own sandbox and reports that nested sandbox-exec is unavailable; this survey did not independently test nesting.

[cco](https://github.com/nikvdp/cco) is relevant launcher prior art, but its documented Docker credential-file mount gives the workload credential access. Keeping a secret out of an image is different from keeping it unreadable to the running workload. [Security model](https://github.com/nikvdp/cco/security).

## Contract implications

**Proposed:** Separate preparation of execution, storage, and the authenticated request path from the Launcher that presents an interactive terminal or starts a headless command. A backend can supply credential injection itself; a separately packaged agentgw is not inherently necessary for that function. Preserve a common application authorization contract regardless of whether agentd receives a mediated bearer token or workload mTLS.

An exec API, a new interactive shell, reconnection to a living harness PTY, and native conversation resume are four different capabilities. Require each backend to declare them separately. Tmux can own the local attachment process without owning the actual guest harness lifetime.

**Decided host-mode boundary, operator discussion on 2026-09-27:** Host mode trusts the OS user. Arbitrary same-UID processes tampering with the wrapper, gateway, or binding are outside its threat model. Credential custody and kernel-derived process attribution remain useful within that assumption; they do not establish hostile same-user isolation. Host mode and sbx are now the initial backend targets; their integration remains unverified and the bespoke microVM topology is deferred.

## Bounded qualification experiment

For the accepted initial targets, use the issue-ready [backend validation spikes](backend-validation-spikes.md). The experiment below remains a compact source of runtime test cases.

For a runtime-mediated credential backend, use two workloads, an agentd-like local HTTPS service, and disposable credentials. The placeholder cases below do not apply to credential-free host peer connections. No model-provider account is needed for the initial credential-path check.

1. Prepare and launch both workloads headlessly, then invoke agentw-equivalent requests from shell descendants. Confirm distinct authenticated identities while guest environment and files contain only placeholders.
2. Copy A's placeholder into B; try A's endpoint and supplied identity headers. Confirm B cannot acquire A's identity, regardless of placeholder secrecy.
3. Confirm injection reaches exactly the intended local service and cannot be redirected to another host, port, or reflective endpoint. Include direct connections and relevant proxy bypass paths.
4. Revoke A at the service, rotate its credential, and recreate its sandbox name. Confirm obsolete incarnations cannot recover authority through cached credentials, snapshots, or name reuse.
5. Launch a long-lived terminal process, disconnect the viewer, reconnect, resize, and restart the controller. Record separately which failures end the attachment, harness, VM, or authority.
6. Check shared workspace writes and private harness-state persistence. Capture versions and backend configuration before labeling any result verified.
