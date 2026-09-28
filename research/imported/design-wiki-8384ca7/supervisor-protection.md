---
title: Protecting the local supervisor
summary: "Mitigation options and a validation plan for protecting agentd from Claude Code, Codex, and Antigravity sessions on hosts and in containers."
type: research
status: active
tags:
  - area/security
  - area/orchestration
  - scope/destination
updated: 2026-09-27
---

Claim status: **decided** protection scope below, with **documented** mechanisms and **proposed** deployment choices, researched on 2026-09-27. No adversarial harness tests were run for this page, and no machine settings were changed. The options below are an investigation inventory, not a verified secure configuration or an exhaustive enumeration of every OS control.

**Current scope, 2026-09-27:** [Host mode and sbx](spiffe-mtls-authentication.md#initial-backend-scope) are the initial targets. Apply this research through [BV-02](backend-validation-spikes.md#bv-02-managed-harness-confinement-and-credential-custody), not as a requirement to investigate every mitigation below. Host mode trusts the OS user; arbitrary same-UID tampering is outside scope, while managed harness attempts to cross configured boundaries remain in scope. An outer macOS sandbox and a mandatory shared app server are not initial requirements.

## The requirement

The [current authentication design](spiffe-mtls-authentication.md) relies on a trusted wrapper holding workload credentials and agentd authorizing enrollment and workload operations. The operator requested investigation of how far supported harnesses can be prevented from interfering with that authority, particularly on a bare host, with explicit caveats where protection is incomplete.

Protecting the daemon means more than keeping its PID alive. It includes its code, launch configuration, registry, private keys, management channels, and dependencies. It also includes terminal and harness control services that could cause a different session to act. The threat includes agent tools and repository code executed by them. A malicious host administrator or compromised kernel is outside the proposed host protection claim; peer-accessible privilege elevation is not.

Separate integrity and identity from availability. A peer must not be able to rewrite bindings, steal signing authority, or replace the server. Resource exhaustion or termination may still be residual availability risks in an initial host deployment; record those independently rather than describing all protection as absent or complete.

## Accepted configuration caveat

**Decided, operator direction on 2026-09-27:** Protection depends on the harness sandbox being enabled and configured to deny access to the supervisor and its protected resources. If the operator disables the sandbox, permits unsandboxed execution with that access, or configures access to those resources, the supervisor-protection and peer-authentication guarantees no longer apply. The product need not preserve those guarantees against an explicitly permissive configuration.

The investigation should establish a supported configuration for each harness and OS, verify its effective protections, and document remaining gaps. Separate service identities and additional platform controls remain optional research rather than initial requirements. An outer macOS sandbox is excluded from the initial profile; protection after an operator disables the supported harness sandbox is not promised.

This caveat does not turn a bypass of the supported configuration into an accepted configuration change. If an agent can alter the protected settings or reach supervisor resources through an overlooked tool path while that configuration is in effect, record it as a gap to mitigate or an explicit residual limitation. Configuration detection and how the product presents degraded protection remain open UX work.

## Host operation has more than one possible protection level

**Inference:** Bare-host operation does not require agents and supervisor to share an unrestricted OS identity. It can use native users, permissions, sandboxing, and service management without a container product.

| Candidate deployment | What it can aim to protect | Principal limitation to investigate |
| --- | --- | --- |
| Same OS user, harness controls | Deny tool access to supervisor files, keys, and control sockets; constrain shell execution | Every agent-accessible tool and unsandboxed path matters; ordinary owner-only file permissions do not separate processes of the same user |
| Deferred research on compatible platforms: outer process sandbox | Cover the entire harness/runtime and its descendants, with explicit service access | Excluded from the initial macOS profile; other platforms require separate compatibility evidence |
| Separate supervisor and agent OS identities | Use OS ownership and access checks even if a harness tool is unsandboxed | Provisioning, cross-user launching, process inspection, worktree sharing, and credential access become integration work |
| Historical topology: container/VM plus in-guest separation | Constrain the guest's host access and separately protect guest `agentd` | The outer boundary alone does not isolate guest sessions from a supervisor sharing their privileges |

A separate supervisor identity protects the daemon but does not automatically protect peers from one another. If a backend uses a shared Codex app server, it must distinguish workload authority; assigning a UID to that server does not distinguish the threads it hosts.

## Mitigation inventory

These are **proposed** controls to evaluate in combination. Apply restrictions to the agent execution environment where the purpose is to constrain agents; restricting `agentd`'s own filesystem view alone does not stop another process from editing its files.

| Surface | Candidate mitigations | Residual risk or required check |
| --- | --- | --- |
| Supervisor binary and startup | Trusted absolute paths; protected executable and parent directories; validate symlink targets; sanitize loader, interpreter, and shell startup inputs | An immutable binary can still load writable configuration, libraries, plugins, or replacement helpers |
| Registry and policy | Service-owned directory outside worktrees; deny agent read/write as appropriate; keep all SQLite database, WAL, and sidecar files within it | Read-only main database with writable directory/sidecars is not the desired boundary; test native editors as well as shell writes |
| Private keys and credentials | Keep outside agent mounts and environments; separate owner or broker; test key-use authorization as well as export | A keychain location or mode 0600 alone is not evidence of isolation from the same user |
| Signals, debugging, process memory | Different OS credentials; OS process-access restrictions; sandbox process-control restrictions; platform hardening | Signal denial, debugger denial, and process-info denial are separate claims; preserve the supervisor's own required inspection access |
| Management API | Authenticate clients and authorize each operation; prevent agents from reading operator credentials; bound delegated launch permissions | Loopback address, executable name, and same UID do not establish operator authority |
| Peer API | Binding-derived identity; bounded requests and concurrency; reject ambiguous origin and unsupported proxy routes | File access to a socket and application authorization solve different problems |
| Terminal and harness control | Protect shpool/tmux sockets and the Codex management connection; mediate session-scoped attachment | Terminal input or unrestricted shared-server access can impersonate peers without modifying agentd |
| Configuration and extensions | Validate initial configuration; protect all loaded scopes; restrict untrusted hooks, MCP servers, plugins, and command exclusions | A shell sandbox may not contain in-process tools or helper services; loaded project settings can affect future executions |
| External process creation | Restrict access to service managers, automation APIs, remote shells, container sockets, and privileged brokers | A process spawned through another service may not inherit the caller's sandbox or ancestry |
| Availability and recovery | Process/memory/FD limits; bounded queues and disk usage; service restart; durable generations; authenticated recovery | Restart is recovery, not prevention; a replacement listener must not inherit trust merely by taking the old port |

## Harness controls and gaps

### Claude Code

**Documented:** The sandbox covers Bash, PowerShell, and Monitor commands and their descendants; tool permissions cover other tools separately. Managed `enabled`, `failIfUnavailable`, and `allowUnsandboxedCommands: false` can require sandbox startup and block the model's unsandboxed retry. However, `excludedCommands` merges across loaded scopes and has no managed-only lockdown. Managed read-path/domain restrictions do not close that separate escape route. The docs also warn that enabling Apple Events weakens code-execution isolation. [Claude sandbox documentation](https://code.claude.com/docs/en/sandboxing), accessed 2026-09-27.

**Proposed:** Protect and validate loaded settings, keep exclusions out of the protected deployment, deny supervisor paths through both filesystem sandbox and native tool permissions, and test service-launch/automation paths. Do not equate auto approval or a command deny rule with OS confinement. Validate missing-dependency behavior on Linux and project configuration already present before launch. Installed-version behavior still needs testing.

### Codex

**Documented:** Current sandbox documentation describes Seatbelt on macOS and bubblewrap prerequisites on Linux. This establishes candidate platform mechanisms, not all-process protection for a shared app server. [Codex sandbox documentation](https://learn.chatgpt.com/docs/sandboxing), accessed 2026-09-27.

**Documented:** Managed configuration supports requirements that restrict permission profiles, sandbox choices, and approval behavior, with system requirements on macOS/Linux and an MDM path on macOS. Current docs recommend permission profiles for recent versions; actual keys must match the deployed version. [Managed configuration](https://learn.chatgpt.com/docs/enterprise/managed-configuration), accessed 2026-09-27.

**Proposed:** Pin the allowed protection profile in trusted configuration; exclude full-access execution from the protected deployment; test escalation and auto-review separately from normal sandboxed tools. Evaluate shell commands, native edits, hooks, MCP/plugin execution, and the shared app-server endpoint independently. Keep the app-server management connection inaccessible to ordinary tool processes. One app server per boundary is no longer a chosen topology. Qualify the actual adapter topology; shared-service attribution is required only if that adapter uses shared execution.

### Antigravity / agy

**Documented:** Antigravity's CLI documentation exposes `enableTerminalSandbox` and `toolPermission`, and describes OS-backed shell confinement and unsandboxed-command paths. The documentation includes both IDE and CLI sections; do not apply an IDE preset as though it proved CLI behavior. [Terminal sandbox](https://antigravity.google/docs/sandbox?tab=cli), accessed 2026-09-27.

**Proposed:** Confirm the installed CLI's effective settings, project override behavior, native file-tool access, and all unsandboxed execution paths. The imported research raises questions about Mach-service and process-information access in an older embedded macOS profile. Treat those as test leads, not proof of current exposure. Do not declare this harness protected until the same supervisor-access tests pass as for Claude and Codex.

## macOS host candidates

The initial profile uses harness confinement. Separate service identities and packaging hardening below are optional follow-on research, not additional BV-02 prerequisites.

**Documented baseline:** Apple's archived `kill(2)` reference describes credential-based signal permissions. Its age means it supplies a model to test, not a complete statement about current sandbox and process protections. [Apple kill reference](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/kill.2.html).

**Proposed:** Compare same-user Seatbelt restrictions with placing `agentd` under a dedicated service identity. Consider a signed, Hardened Runtime build to reduce injection/debugging exposure; Apple's [Hardened Runtime documentation](https://developer.apple.com/documentation/security/hardened-runtime) describes process-integrity protections, not a universal defense against same-user signals, writable files, or authorized API calls. Packaging and entitlements require verification; a development build is not equivalent evidence.

Test launchd control, Mach services, LaunchServices, Apple Events, keychain operations, and terminal sockets using disposable targets. A service manager restarting a daemon does not prevent an agent from stopping it repeatedly. TCC consent and keychain prompts should be recorded as prompts, not as proof of permanent denial. An outer whole-harness Seatbelt wrapper is excluded from the initial host design because of the operator-reported nested-sandbox constraint; this inventory does not make it a fallback requirement.

Separate users may also restrict the very process/FD inspection required for authentication. The imported [v2 review](../agent-orchestration-poc/research/imported/agent-peering-tests/DESIGN_REVIEW_ASTRA_V2.md) flags this feasibility issue. Determine the narrow observation/launch privileges needed before deciding on any privileged helper; do not make the whole orchestration service root as an unexplored default.

## Linux host candidates

This is follow-on platform research. It does not broaden the initial macOS qualification matrix.

**Documented:** Ordinary signal permission depends on process credentials or capability. [Linux kill reference](https://man7.org/linux/man-pages/man2/kill.2.html). Yama can restrict ptrace relationships; daemon non-dumpability is another process-inspection control discussed in its documentation. Neither is a general substitute for signal or filesystem protection. [Kernel Yama documentation](https://docs.kernel.org/admin-guide/LSM/Yama.html).

**Documented candidates:** systemd exposes filesystem restrictions, privilege restrictions, and process visibility controls. Their applicability depends on service type, kernel, and permissions. `ProtectProc` is not a blanket same-UID isolation promise. Evaluate `User`, `NoNewPrivileges`, capability bounds, `ProtectSystem`, path restrictions, and `ProtectProc` together. [systemd execution reference](https://github.com/systemd/systemd/blob/main/man/systemd.exec.xml), accessed 2026-09-27.

**Proposed:** Place agents in constrained services or an outer sandbox with a filesystem view excluding supervisor state and management sockets. Evaluate namespaces, seccomp, AppArmor/SELinux policy where available, and cgroup resource limits; none is assumed installed or configured. Keep policy enforcement outside peer-writable storage. Seccomp syscall filters need a carefully chosen contract; a generic filter should not be credited with identifying the intended target of every operation.

**Documented:** Landlock supports unprivileged restrictions, with features dependent on kernel ABI; its signal scope can restrict signaling outside a sandbox domain. [Kernel Landlock documentation](https://docs.kernel.org/userspace-api/landlock.html). **Proposed:** Evaluate it for an outer restriction layer, while testing inherited/open descriptors and mandatory feature availability. Do not claim a filesystem-only Landlock policy also blocks signals.

Namespaces and `/proc` restrictions can hide processes or translate PIDs used by peer attribution. Validate these controls together with the identity mechanism. Protection that breaks observation must produce rejection or a supported alternative, not silently weaken attribution.

## What a container adds

**Historical alternative, not the sbx topology:** A controlled guest image makes it easier to fix users, ownership, mounts, capabilities, configuration, and exposed sockets at startup. Keep host control-plane credentials and container-management sockets out of the guest; give sessions no ability to administer the boundary. Protect guest `agentd` through the same local user/sandbox controls investigated above. Guest root or equivalent privileges cannot be treated as an untrusted peer while trusting a guest daemon it can control.

A VM limits effects on the host, but does not solve peer impersonation or daemon tampering inside that VM. Kernel or local-supervisor compromise invalidates per-session claims from that boundary. The external control plane should still cap the aggregate authority delegated to it.

## Validation plan and caveat format

Extend the imported [sandbox test matrix](../agent-orchestration-poc/research/imported/agent-peering-tests/SANDBOX_TESTS.md) and [open items](../agent-orchestration-poc/research/imported/agent-peering-tests/OPEN_ITEMS.md). Their result tables are not completed evidence. The old private-API confinement probe requires calibration; a single “confined” result cannot prove which operations are denied.

For initial qualification, run the Claude and Codex macOS profiles selected in BV-01/BV-02 against disposable fixtures, never real agentd state or credentials. Linux and agy remain optional follow-on matrix entries. Record OS/kernel, harness version, effective policy, user identities, launch topology, and tool path for every result. Use fake keys and dedicated terminal/service endpoints; do not probe the operator's live clipboard, keychain items, sessions, or service jobs.

| Probe family | Required evidence |
| --- | --- |
| Process interference | Separate harmless liveness checks from actual signal tests against a disposable target; test stop/termination, debugger attachment, and memory/process-info access |
| Files and key use | Attempt reads and changes through shell and native tools; include replacement via writable parent, symlinks, sidecars, and use of a dummy signing key |
| Control channels | Test peer versus management authorization and terminal input; test cross-thread control only if the chosen adapter uses a shared Codex server |
| Configuration | Test initial malicious fixture settings, runtime edits, each loaded scope, helper/plugin paths, and sandbox initialization failure |
| Escape/delegation | Test isolated service-manager and automation fixtures, nested helpers, approved versus unapproved escalation, and orphaned descendants |
| Recovery and pressure | Bounded resource-pressure tests, daemon restart, PID reuse, listener replacement, and stale-binding rejection |
| Compatibility | Confirm legitimate launches, interactive attachment, peer messages, and permitted coordinator launches still work |

Report each cell as blocked, allowed, prompted, unsupported, or inconclusive, with evidence and a resulting claim. A prompt is not an OS denial; a denied inspection is not proof the target is absent. Do not elevate or switch transports to get around a denial during the same test. Changes to test policy are separate, explicitly recorded configurations.

For each residual caveat, state the actor and required access, affected property (availability, integrity, secrecy, or attribution), affected harness/OS/profile, and mitigation or accepted limitation. For example: “Under the same-user profile, an unconfined command can terminate the disposable supervisor; binding integrity was tested separately; service restart only reduces downtime.” Leave untested cells unknown.

## Related architecture research

The [destination model](mental-model.md#lessons-from-ax-and-agent-substrate) records an initial reading of AX and Agent Substrate. Substrate's pinned threat model supplies additional test leads for local service access, management API self-modification, stale policy during execution reuse, and delegated child creation. Those are design inputs, not verified mitigations. Extend the harness matrix to distinguish interactive Sessions from headless Tasks, since their effective permissions may differ.

## Next bounded investigation

Use [BV-01 and BV-02](backend-validation-spikes.md) for the bounded initial macOS host qualification. Record unsupported profiles and gaps rather than expanding into an outer sandbox, separate service identities, or mandatory shared-server research. The broader Linux and mitigation inventory above remains optional research, not the initial spike backlog.
