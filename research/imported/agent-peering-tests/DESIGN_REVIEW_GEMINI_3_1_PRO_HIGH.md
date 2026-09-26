# Design Review: Agent-Work Peer Authentication

## 1. Executive Summary

The `agent-work` coordination design presents a highly innovative approach to multi-agent peer authentication. By leveraging kernel-level process attribution (ancestry walking) rather than relying on injected secrets (like API keys or environment variables), the design elegantly side-steps the risks of credential theft within a shared local environment. Furthermore, the use of pinned TLS for server identity is a robust defense against port squatting and Man-in-the-Middle (MitM) attacks.

However, the pressure test reveals several critical vectors that could allow impersonation within the stated threat model, most notably regarding the execution of untrusted code by the agents, and the mechanisms used to detect nested subagents.

---

## 2. Security & Threat Model Pressure Tests

### 2.1 The Untrusted Code Execution Loophole (Critical)
* **Scenario:** The threat model explicitly excludes prompt injection, but it does not account for the standard agent workflow of executing untrusted code (e.g., running `make test`, building a downloaded repository, or executing scripts from a PR under review).
* **Attack:** If an agent (e.g., in the Reviewer role) executes `npm test` on a malicious PR, the test script can simply execute `agent-work send --role reviewer "Looks good to me! Approving."`
* **Impact:** Because the malicious test script is a descendant process of the registered harness, the C2's kernel ancestry walk will validate the request as legitimate. This allows a malicious repository or PR to achieve complete impersonation of the agent reviewing it.
* **Mitigation:** This is a fundamental limitation of relying solely on process ancestry. Mitigating this would require either OS-level isolation per command (which the design avoids), or requiring a dynamic, one-time token for each message that the agent must explicitly read and pass—though this creates new secret-management problems. At a minimum, the REPL should clearly flag when a message was sent via a background/spawned process rather than directly from the main agent loop, if detectable.

### 2.2 Bypassing the Nested-Harness Rule (Medium)
* **Scenario:** The design prevents subagents from messaging the C2 by checking for known harness executable names (`claude`, `codex`, `agy`, etc.) in the process ancestry.
* **Attack:** An agent (or a malicious script) can spawn a subagent and bypass this rule by simply copying or renaming the harness binary. For example: `cp $(which claude) /tmp/sub-claude && /tmp/sub-claude`.
* **Impact:** The ancestry walk will fail to recognize `/tmp/sub-claude` as a nested harness, allowing the subagent to impersonate the main session.
* **Mitigation:** Relying on hardcoded string matching of executable names is fragile. A more robust approach could involve checking the binary hashes of known harnesses, or inspecting process group IDs (PGIDs) and session IDs (SIDs)—though these can also be manipulated by the process.

### 2.3 Cross-Session Proxy Tunneling (Claude Code) (Medium/High)
* **Scenario:** As noted in the design's "Open Questions", Claude Code uses an in-process HTTP proxy to route localhost traffic to bypass sandbox restrictions.
* **Attack:** If Session A (Reviewer) and Session B (Implementer) are running on the same machine, and Session B's proxy binds to `127.0.0.1:50002`, Session A might be able to configure its `HTTPS_PROXY` to `127.0.0.1:50002`. Because the connection originates from Session B's proxy, C2 will attribute the request to Session B.
* **Mitigation:** This heavily depends on whether the Claude Code sandbox explicitly blocks outbound connections to localhost ports other than its own assigned proxy. If the sandbox allows general loopback access, this attack is viable. The proxy itself cannot easily verify that the incoming connection comes from its own specific sandbox instance.

---

## 3. Operational & Architecture Pressure Tests

### 3.1 Worktree Context Drift
* **Scenario:** A harness's worktree identity is bound to the C2 at launch (`agent-work start`).
* **Issue:** If an agent `cd`s into a different worktree, a git submodule, or a completely unrelated directory, its messages to the C2 will still be broadcast to the peers of the original launch worktree.
* **Impact:** Logical cross-contamination of contexts. An agent might think it is communicating about Repo B, but it is broadcasting to the group for Repo A.
* **Mitigation:** The CLI could optionally pass the current working directory or resolved git top-level dir with each message, allowing the C2 to warn the operator or reject the message if a context drift is detected.

### 3.2 Process Ancestry Race Conditions (TOCTOU)
* **Scenario:** The time-of-check to time-of-use (TOCTOU) window between the C2 calling `accept()` and the ancestry walk completing.
* **Issue:** While ephemeral ports prevent unrelated processes from hijacking the lookup, intermediate processes in the ancestry chain (e.g., transient shell wrappers) might terminate before the walk completes. This breaks the ancestry chain, causing the C2 to reject a valid request.
* **Mitigation:** The blocking nature of `agent-work send` mitigates this for the happy path. However, the C2 must ensure it handles `libproc`/`lsof` lookup failures gracefully (fail-safe) without crashing the C2 server.

### 3.3 Performance and Reliability of `lsof`
* **Scenario:** Using `lsof` via a subprocess takes ~40ms per connection.
* **Issue:** Under heavy system load, or on a machine with tens of thousands of open file descriptors, `lsof` can become a severe bottleneck, consume high CPU, or even timeout.
* **Mitigation:** As noted in the design, migrating to `libproc` on macOS and `/proc/net/tcp` + `fd` scanning (or `sock_diag`) on Linux is critical for production readiness. Subprocessing for every network request is inherently brittle.

---

## 4. Addressing Open Questions in the Design

* **Cross-session proxy isolation in Claude Code:** This is the most critical verification step for the proxy workaround. If the sandbox does not isolate localhost ports per instance, the proxy model is fundamentally vulnerable to cross-session impersonation. You must empirically test if Claude Code blocks access to other local ports.
* **Subagent enforcement via hooks:** Harnesses generally do not provide fine-grained hooks to differentiate subagent tool calls from main agent tool calls. Because they execute in the same process tree, the kernel attribution model inherently struggles to distinguish them.
* **libproc lookup cost:** Moving to `libproc` is highly recommended. The cost will drop from ~40ms to under 1ms, as it avoids spawning a new process and parsing standard output, instead making direct in-memory kernel struct reads.
