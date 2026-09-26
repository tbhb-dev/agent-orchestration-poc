# Design Review: Agent-Work Peer Authentication v2

## 1. Executive Summary

The V2 revision of the `agent-work` coordination design is a massive leap forward in maturity and security. By incorporating a token-based, confinement-checked registration flow and shifting away from Claude Code's proxy in favor of direct loopback, the design successfully closes the most critical impersonation vectors identified in V1.

Crucially, V2 adopts a highly realistic threat model by explicitly acknowledging that the authenticated principal is the *entire process tree*, including any untrusted code executed by the agent. This shift from "we can secure the tool call" to "the session is the identity" is the correct, secure-by-default stance for agentic frameworks.

---

## 2. Security Improvements & Threat Model Validation (The Good)

* **Registration via Token + Confinement Check:** This is the strongest addition to the design. By requiring the wrapper redeeming the token to be strictly unconfined (`sandbox_check` / namespace inspection), the design eliminates the risk of sandboxed subagents or malicious scripts hijacking the registration phase via reparenting or ancestry spoofing.
* **Binding Generations & Boot IDs:** Tying waiters and messages to specific binding generations elegantly solves the TOCTOU race conditions around session compaction, crashes, and resumes. A stale process can no longer steal messages meant for its successor.
* **Direct TCP for Claude Code:** Bypassing the proxy (via `allowLocalBinding`) restores fine-grained, per-command attribution and eliminates the complex cross-session proxy tunneling risks that plagued V1.
* **Worktree-Scoped TLS:** Generating a unique C2 identity per worktree prevents a scenario where a wrapper is tricked into enrolling in the wrong peer group by a rogue C2 squatting the port.

---

## 3. Pressure Testing & Remaining Risks

While the design is solid, pressure testing reveals a few edge cases, implementation hurdles, and fundamental limitations of multi-agent shared state.

### 3.1 The "Chain-Shape" Policy Illusion
* **Scenario:** The design offers an optional chain-shape policy (`Harness -> Shell -> agent-work`) to mitigate drive-by untrusted code execution.
* **Pressure Test:** While this prevents deep nesting (e.g., `Harness -> Shell -> npm -> bash -> agent-work`), it is trivially bypassed by shallow untrusted scripts. If an agent directly executes a malicious script in the repository (e.g., `./setup.sh`), the resulting process tree (`Harness -> bash -> agent-work`) perfectly mimics the allowed shape.
* **Takeaway:** The document correctly notes this is a "policy hint" rather than a security boundary, but operators must be acutely aware that the chain-shape policy provides almost zero protection against malicious repository scripts. 

### 3.2 Cross-Agent Identity Hijacking via the Shared Worktree
* **Scenario:** The threat model states: "A peer can't send as another peer."
* **Pressure Test:** While the C2 strictly isolates network identities, the shared git worktree acts as a massive, untrusted shared memory space. Peer A (Malicious/Compromised) can modify a script (e.g., `build.sh`) in the worktree. When Peer B (e.g., the Reviewer) is instructed to run `build.sh`, Peer A's payload executes under Peer B's process tree and, consequently, Peer B's C2 identity. 
* **Takeaway:** This is essentially "social engineering" between agents. Because the worktree is untrusted shared state, Peer A can effectively send messages as Peer B by tricking Peer B into executing the payload. The C2 cannot defend against this.

### 3.3 The "Single Snapshot" Implementation Reality
* **Scenario:** The lookup contract mandates taking a "single snapshot of the process table" to walk the ancestry.
* **Pressure Test:** Neither macOS (`libproc`) nor Linux (`/proc`) provides a true, atomic snapshot of the entire process tree without falling back to kernel-level tracing (eBPF/DTrace). The process table will be read sequentially.
* **Takeaway:** The implementation will inevitably be subject to "torn reads" (a process dying and being recycled while the walk is occurring). The requirement to strictly verify `(pid, start_time)` tuples at each hop mitigates the security risk of a torn read (preventing ancestry splicing). However, the C2 must be highly resilient to `ENOENT` or mismatched start times during the walk, gracefully failing closed without crashing.

---

## 4. Feedback on the Appendix (Proxy Fallback)

The `PID-and-nonce` binding mechanism using `KERN_PROCARGS2` is an exceptionally clever cryptographic workaround for regaining per-command attribution over a shared, unauthenticated proxy. 

* **Caveat:** Be aware that on macOS, processes can overwrite their own `KERN_PROCARGS2` memory space (often done via `setproctitle` or by modifying `argv`). While a sandboxed malicious process cannot read the legitimate CLI's nonce (due to Seatbelt `process-info*` rules), a robust implementation must ensure it parses the initial arguments reliably and doesn't get confused if a process maliciously formats its overwritten argv to spoof a nonce.

---

## 5. Suggested Additions to "Tests before relying on this design"

I recommend adding the following to the testing checklist:

1. **The Shared Worktree Injection Test:** Have Peer A write a shell script to the worktree that calls `agent-work send`. Have Peer B execute that script. Verify that the C2 authenticates the message as Peer B, and document this behavior so operators understand the limits of peer isolation.
2. **Torn Read Simulation:** During the C2's ancestry walk (in a test harness), intentionally `kill -9` an intermediate shell process before the walk reaches the harness. Verify that the C2 fails closed cleanly and handles the missing process table entry without a panic/exception.
3. **Tmux Socket Access Test:** Verify if the standard sandboxes (particularly Codex and Antigravity) allow reading/writing to `/tmp/tmux-*`. If they do, a compromised agent could use `tmux capture-pane` to steal the `/add-peer` join token from the operator's scrollback before it is redeemed.
