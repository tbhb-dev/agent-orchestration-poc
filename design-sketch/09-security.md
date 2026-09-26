# Security

This adapts the threat model in `agent-peering-tests/DESIGN_V2.md` to the container era. Read that document first; much of its reasoning carries over.

## Principals

- **The operator.** Trusted. Acts through the Tauri app, the local or tailnet web UI, `agentctl` in operator mode, and operator shells.
- **An agent.** The harness process tree inside its session, including its tool calls, subagents, and any code it runs (test suites, build scripts, code from a branch under review). A message authenticated as an agent came from somewhere inside that tree; attribution can't tell which instruction caused it.
- **The daemon.** Trusted. Runs as the operator on the host.

## Boundaries

| Boundary | Enforced by | Notes |
| --- | --- | --- |
| Agent to host | The VM (hypervisor) | Weakened by anything mounted; mount only the worktree and the repository's `.git` if needed |
| Group to group | Separate VMs | The main reason for one VM per group |
| Agent to agent in a group | Linux users plus per-agent NATS credentials readable only by their owner (proposed) | NATS subject permissions enforce who may publish as whom; not confidentiality, since members share a worktree |
| Agent to the internet | Internal network plus host egress proxy | Allowlist per group; depends on tools honoring proxy variables |
| Remote client to daemon | Tailscale plus identity allowlist | Remote shells gated separately |

## In scope

- A bus message attributed to an agent came from that agent's session. An agent can't send as another agent, alter or remove another agent's messages, or take over another agent's identity.
- An agent can't reach another group's files, bus, or credentials.
- An agent can't reach the host filesystem beyond its mounts, or the network beyond its allowlist.
- A remote attacker without tailnet access can't reach the daemon.

## Out of scope

- Confidentiality between agents in a group.
- Prompt injection through messages, shared memory, files, or anything else an agent reads. Authenticated content is still untrusted input.
- A malicious process running unconfined as the operator on the host.
- Hypervisor escapes.
- Denial of service as a security goal, though the daemon and broker apply limits so a misbehaving agent can't make the system unusable by accident.

## Specific risks to handle

- **The daemon's control plane.** Whatever can call the daemon can create groups with mounts. Mount paths come only from the operator's settings, never from a request; remote clients get a narrower API.
- **Credentials in VMs.** Agents can read their own harness credentials. If one login is shared across every session of a harness, a single compromised agent exposes that login for all of them. Egress control limits where credentials can be sent; short-lived tokens from a host broker, where a harness allows it, limit how long a stolen one is useful.
- **Shared `.git` mounts.** If the main repository's `.git` is mounted, an agent can rewrite any branch's refs and objects. Consider clones for groups working on anything sensitive, and push protection on the remote.
- **Project configuration in the worktree.** The research found that project-scope harness configuration (for example `.claude/settings.json`, `.mcp.json`) can add hooks and commands that run outside a harness's sandbox, and that one harness can edit another's project config. Inside a VM this matters less for the host, but it still lets one agent change what another agent's harness runs. Decide whether harness configuration comes from the image and per-agent volumes only.
- **The operator's views.** Terminal output is rendered by xterm.js, which interprets escape sequences by design. Message timelines, file names, memory entries, and session names are rendered as text and must be sanitized. Consider what a hostile OSC sequence in a terminal could do in xterm.js with the clipboard and link addons enabled.
- **Remote shells.** Off by default, with step-up confirmation when enabled.
- **The egress proxy.** It's a policy enforcement point and a parser of untrusted traffic; keep it simple and well-tested.
- **The NATS listener.** It's the one host service group VMs can reach. Bind it only where VMs need it, require credentials on every connection, give each group its own account so groups can't see each other's subjects, restrict each agent's publish and subscribe permissions, and set connection, payload, and storage limits. Losing an agent's credentials file means someone can act as that agent within its group, which is the same principal boundary the research already accepted.
