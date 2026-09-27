# Security cross-check and disposition

## Reviewer and method

Claude Code 2.1.283, `claude-sonnet-5`, medium, reviewed the supplied design, operator plan, account probe record, and signature source notes on 2026-09-27 UTC. The project plan assigns this harness/model to security cross-checks. Codex wrote this report from the reviewer's raw findings. The reviewer assessed documents. Runtime security testing and GitHub approval remain separate steps.

The command was `mise exec -- claude -p --model claude-sonnet-5 --effort medium --tools '' --strict-mcp-config --no-session-persistence --permission-prompts none`, with the four documents supplied on stdin from `$TMPDIR/issue-132-cross-check-input.txt` and raw output retained locally at `$TMPDIR/issue-132-cross-check-output.txt`. Exit 0. The launcher printed a pre-existing permission-rule syntax warning, which did not stop the review. The reviewer ran without tools and did not change accounts, keys, or the repository. The report preserves each finding's disposition below without committing the raw harness output.

## Findings

| ID and priority | Finding | Disposition |
| --- | --- | --- |
| H1, high | A forged post-cutover `tbhb` comment can appear authoritative while its token is reachable | Open accepted-policy risk. The operator explicitly retained the token and comment precedence. The design requires independent confirmation before consequential execution and mandatory reporting. Removing authorship authority would contradict the operator decision |
| H2, high | Independent authorization needed a concrete trust boundary and trustworthy approval display | Resolved in design. A separate service principal stores one-use records and renders exact payloads in the operator's separately authenticated control session. Host paths/modes are proposed in the report. Runtime isolation remains an activation blocker |
| H3, high | A worker can override Git config or alter a verifier in its own branch | Resolved in design. Required `pr-body` uses a trusted base/host verifier with isolated Git configuration and public policy. Enforcement changes require operator merge. Local signing settings alone are insufficient |
| H4, high | Reachable reviewer credentials can let an implementer impersonate a reviewer | Open process-control risk. Require reviewer-dispatch reconciliation and incidents for unmatched review actions. The project does not claim credential isolation between these accounts |
| H5, high | Polling and worker-written receipts miss transient writes and can be disabled | Resolved as a cutover blocker. Protected event/receipt storage, independent heartbeat, configuration snapshots, and demonstrated edit/deletion/Project coverage are required. Coverage is untested, and a five-minute poll alone cannot establish it |
| H6, high | Old sessions or scheduled automation can continue writing as `tbhb` | Resolved in the drain contract. Inventory coordinator, workers, jobs, automation, and helper users. Refresh environments and instructions before resumption. Explicitly catalog automated actors |
| M1, medium | GitHub cannot distinguish an operator sensitive merge from an agent merge when both use `tbhbagent` | Reject the suggested switch to `tbhb` merge transport because the operator permits `tbhbagent`. Require the independent `merge-sensitive` record and reconcile the actor/result against it |
| M2, medium | Project field writes could be mistaken for issue readiness or completion | Resolved by consuming #90 verdict freshness and operator approval where required. Require completion evidence for Done. Project values never create authority by themselves |
| M3, medium | A worktree wrapper is editable by the worker | Resolved in design through a pinned operator-owned installed wrapper. Retained token access still permits deliberate bypass, which remains H1/H4 risk |
| M4, medium | Key reuse, leftover copies, endpoint access, and digest-only approvals weaken signing | Resolved in design through a dedicated agent key/subkey, operator migration audit, Unix socket permissions and authenticated requests, trusted payload display, and feature-branch-only signing. These controls remain untested until deployment |
| M5, medium | New account scopes and access may be broader than needed | Open until login. The operator audits permissions and limits grants. Browser account selection, push identity, and Project access each need verification. This PR does not inspect tokens or invent actual scopes |
| M6, medium | Signature status, revocation freshness, and GitHub key rotation need explicit handling | Resolved in design. Require `G`, full signing/primary fingerprints and account binding, current revocation policy, and operator-approved web-flow key updates. Cryptographic execution is deferred |
| M7, medium | Signer failure can block rollback and the pause lacked an owner | Resolved in design. Operator owns suspension and rehearses a separately admitted recovery signer. A scoped ruleset change remains a separately authorized fallback, with normal PR review preserved |
| M8, medium | Delaying `required_signatures` leaves a potential enforcement gap | Resolved in design. The trusted verifier is mandatory within the existing required `pr-body` context at activation. Legacy exemptions must be explicit. Ruleset read-modify-write preserves and compares every existing field |

The reviewer suggested cryptographically signed authorization records. The selected initial boundary is a separately authenticated operator service with protected storage and atomic consumption. A same-user editable file is expressly insufficient. Cryptographic portability is deferred unless the service's trust boundary cannot be demonstrated. Codex chose this disposition. The reviewer did not rerun or approve the revised draft.

## Open verification gates

The login/default/helper probes, Project read/write access, key format and fingerprints, email/account binding, signing isolation, request replay and failure behavior, public-key revocation refresh, GitHub merge/ruleset behavior, remain untested, along with complete event coverage by the detector. Issue #134 must retain their exact commands, outcomes, and operator authorizations before activation. The H1/H4 risks remain visible even after a successful rehearsal because the operator chose reachable credentials.

The final design and operator plan record these requirements as future work. They do not establish a verified sandbox boundary.
