---
title: Operator oversight and intervention
summary: "Proposed operator oversight and interventions, with Codex review of hold visibility, egress enforcement, and redaction limits."
type: design
status: draft
tags:
  - area/messaging
  - area/security
  - actor/operator
  - scope/destination
updated: 2026-09-28
---

**Claim status:** Everything on this page is **proposed**. Claude drafted it at the operator's request on 2026-09-27, before a multi-model review of the wiki. It builds on the [integrated participant proposal](participants-and-permissions.md), in which the operator is a participant kind alongside workloads and bots, and on the [loop and budget controls](messaging-loops-and-budgets.md), which depend on operator intervention.

**Review navigation:** Claude's original proposal is retained below. The labeled [Codex review](#codex-review) records integration recommendations and qualifications; where they differ, both remain proposals for operator review.

## Participation and oversight are different authorities

Treating the operator as a participant lets them hold DMs with workloads, post in channels, and be mentioned, all through the same model agents use. That covers talking. It doesn't cover watching or stepping in. Those are oversight, and they need their own authority for three reasons:

- **Oversight shouldn't require membership.** The operator must be able to read any conversation in their scope without joining it, since joining would change delivery sets, receipts, and what agents see.
- **Oversight acts on the system, not in a conversation.** Pausing wakes, muting a participant, or redacting a leaked secret changes how agentd behaves. None of those are messages.
- **Oversight must not leak to agents by accident.** An agent that can post in a channel must not gain the ability to pause it merely because the operator happens to share that channel.

Proposed: oversight is a set of permissions in the operator's installation, scoped like any other installation (host-wide for the local operator by default). Because oversight actions are permissions, they can be delegated in part, for example letting a coordinator workload pause a channel in its own group. Workloads and bots hold no oversight permissions by default.

**Open storage choice, Codex reconciliation of Claude IR-06, 2026-09-28:** The paragraph above proposes operator installations, whereas the initial identity sketches reserve installations for bots. The [identity schema](identity-schema.md#lifecycle-and-policy-records) now offers an interim scoped `operator_grants` record without choosing unification. Neither representation nor a host-wide default is decided; explicit operator grants are required whichever storage is selected.

## Oversight read

With oversight read, the operator can read every conversation, thread, and history range within their scope:

- Reading creates no delivery rows, receipts, or channel cursor movement, and it doesn't make the operator a member.
- Reading is recorded in the event log as an oversight access. On a single-operator laptop, the audit value is low, but it becomes important once more than one person operates a host, and the cost of recording it is small.
- Agents should know that the operator can read their conversations. This is a disclosure question, not a security control: agents shouldn't be led to believe any conversation is private from the operator. The bootstrap instructions or the [envelope design](messaging-envelope.md) can carry that fact.

## Graded interventions

Interventions should range from light to severe, so the operator doesn't need a kill switch to handle a noisy channel.

| Intervention | Scope | Effect on sends | Effect on wakes | Typical use |
| --- | --- | --- | --- | --- |
| Hold | Participant or conversation | Accepted, but held for operator review before any delivery rows are created | None until released | Checking a new bot, reviewing cross-group requests, approving outbound bridge relays |
| Quiet | Conversation, participant, or group | Accepted and delivered normally | Suppressed; deliveries stay pending and readable by pull | A tripped loop breaker, a noisy channel, a group over budget |
| Mute | Participant | Rejected with `participant_muted` | Not applicable | A misbehaving workload or bot |
| Pause | Conversation | Rejected with `conversation_paused` | Suppressed | Stopping a conversation while the operator investigates |
| Freeze | Group or host | Rejected for everyone except the operator | Suppressed | Emergency stop for messaging |

Rejections carry explicit error codes so the sender learns immediately and doesn't retry into the block. Held messages appear in an operator review queue, where the operator releases them (creating delivery rows at release time) or discards them. Discarding tells the sender through their status view that the message was not delivered by operator decision.

Messaging interventions are separate from lifecycle actions. Suspending or terminating a workload belongs to lifecycle management, and the two should stay distinct in the UI: quieting a workload's wakes leaves it running, while suspending it stops its execution.

**Holds as an approval gate.** Holds double as a general approval mechanism. Group policy could require operator approval for classes of sends, such as cross-group requests, channel-wide mentions, or outbound bridge relays. That last case matters because relaying out of the system is data egress. The approval queue is the same held-message queue, not a separate mechanism.

## Redaction

Agents will sometimes post secrets, credentials, or content that shouldn't persist. Redaction lets the operator remove a message body from storage and from every view:

- The message becomes a tombstone that keeps its ID, sender, conversation position, and redaction time, and records that the operator redacted it. Threads and reply references stay intact.
- The body is removed from SQLite and from any derived storage the design adds, such as search indexes or exports. SQLite free pages and WAL files can retain bytes after deletion, which the Codex research observed for its own databases ([R2](https://github.com/tbhb/agent-orchestration-poc/blob/0d04ae5facd63448e278a08be68ce54922e6c994/research/imported/agent-session-tests/CODEX_SESSION_MANAGEMENT.md), E11). Secure erasure therefore needs an explicit step, such as a vacuum, and the page shouldn't promise it without one.
- Redaction cannot retract text already delivered into model contexts or harness transcripts. The operator view should say so plainly, and it should list which recipients had delivery receipts before the redaction, so the operator knows where the content may still live.

## Operator attention

The operator needs one place where things that want their attention arrive, whatever the source:

- DMs and mentions addressed to the operator participant.
- Loop breaker trips and wake-budget exhaustion from the [loop and budget controls](messaging-loops-and-budgets.md).
- Held messages awaiting review.
- Workloads waiting on permission or user input. The Claude registry's `waiting` status and the Codex waiting states are the evidence sources the delivery research identified.
- Stalled deliveries and unknown wake outcomes from the delivery design.

Proposed routing: everything lands in an attention view in the shared Tauri and browser frontend described in the [destination mental model](mental-model.md#terminal-attachment-and-ui-streaming). Items the operator marks urgent, or that policy classifies as urgent, also raise an OS notification through the desktop app. A bridge bot could forward attention items to the operator elsewhere, for example as a Slack DM. That's an ordinary outbound bridge, subject to the same egress permission and hold rules as any other.

## Operator authentication

The operator doesn't authenticate through the workload paths. Proposed approach:

- **Local operator surfaces.** Agentctl and the desktop app's backend run as trusted host processes under the operator's OS user, which the host-mode threat model already trusts. They can hold an operator SPIFFE identity under a distinct path in the trust domain, so agentd derives the operator participant kind from the authenticated ID, the same way it does for workloads and bots.
- **Browser access, locally or remotely.** The browser never holds an SVID. The mental model already states that forwarding the web endpoint through Tailscale or Cloudflare doesn't replace application authentication. The UI backend authenticates the human, with passkeys as a reasonable default and OIDC as an option, and then acts as the operator participant on their behalf. The backend is the SPIFFE-authenticated component, and the human session maps to it.
- **More than one operator.** A future with several humans operating one host needs distinct operator participants, per-operator installations, and oversight permissions scoped per operator. The model above allows that, but nothing more is designed here.

## Operator messages and authority

When the operator sends a message through the messaging system, what authority does it carry for the agent that receives it? This question is **unresolved** and deserves an operator decision.

The case for treating authenticated operator messages as user instructions: the operator is the person the agent works for, and forcing them to switch to the terminal to give real instructions defeats the purpose of messaging.

The case against: messaging content passes through bridges, bots, and channels, and a design where one kind of message can carry user authority creates an incentive to forge that kind. The envelope design makes forgery much harder, but the agent is still a model reading text.

A middle position is that operator messages are labeled as authenticated operator messages in the envelope, carry the operator's authority for coordination and direction, and still cannot approve permission prompts. Approval would stay with the harness's own approval surface. This keeps messaging from becoming a remote approval channel, which the delivery design already refuses for Claude MCP channel permission relay.

## Open questions

- The authority of operator messages, described above.
- Whether oversight reads should be visible to agents in real time or only disclosed as a standing fact.
- Which interventions a coordinator workload may be delegated by default, if any.
- The [central retention decision](messaging-schema.md#retention-and-redaction-open-decision), including held/discarded bodies and audit copies.
- How holds interact with the loop breaker, for example whether a tripped breaker should hold or merely quiet.
- Multi-operator roles and how operator installations are scoped.

## Codex review

**Peer review and counterproposals, 2026-09-27; all proposed:** The participant handoff has been integrated in [Participants and permissions](participants-and-permissions.md). Operator kind is proposed; unifying operator/workload installations with bot installations remains open. Oversight requires explicit permissions, not merely a capable client, kind label, or conversation membership. Browser sessions must map each human to an operator identity/grant boundary rather than collapse all humans into a powerful backend identity.

Recommend **quiet as the breaker default**, following the [combined wake policy](messaging-loops-and-budgets.md#codex-review-and-combined-wake-policy); hold remains a deliberate escalation. The table's “delivered normally” for quiet should mean accepted/published with normal delivery obligations, not preemptively marked delivered: rows remain pending until qualified push or pull evidence. Budget deferral and indefinite operator quiet are distinct causes even if both suppress wakes. Mute stops future admissions; it does not retract accepted messages. Pause/freeze suppress future dispatch, but already queued native input may execute. The proposed operator exemption from freeze must still require authenticated, scoped authority; scope composition for ownerless multi-Group DMs remains open.

**Hold visibility and release:** Hiding only delivery rows would leak a held body through ambient history, summaries, SSE, or a bridge. Recommend private held acceptance followed by atomic publication at release with fresh sequence and revalidated frozen recipient snapshot, as integrated in [schema](messaging-schema.md#requests-controls-and-publication). Held request outcomes do not reserve claims. Inbound message hold and outbound relay approval share review UI but are different obligations: holding a bot's inbound send cannot prevent that bot from exporting already-read data. Egress approval needs a mediated outbound operation and explicit enforcement boundary; credentials/network access outside agentd cannot be controlled by an inbox hold alone.

**Evidence qualification:** R2 E11 at the pinned revision observed residual deleted identifiers in SQLite/WAL/log files after logical rows and rollout files were removed. It supports the warning against equating API deletion with erasure; it did not test sanitizing agentd stores or show that a vacuum guarantees erasure across logs, backups, filesystems, and native transcripts. Retain “logical redaction” as the proposed promise pending a separately validated erasure procedure. Remove body-bearing canonical retry copies and controllable queued envelopes too. Receipts identify known deliveries, not all exposure: ambiguous pushes, history readers, bots, and exports may have obtained content without such receipts. See the single [retention decision](messaging-schema.md#retention-and-redaction-open-decision).

Proposed checks: unauthorized oversight read/intervention; read without membership or receipt/cursor mutation; cross-operator session confusion; hold/release/discard races and lost responses; release after membership/revocation; redaction versus retry/replay/dispatch; durable controls after restart; and attention floods while a breaker is active. Coalesce operator alerts and audit metadata without copying bodies. No check has been run. Operator-sent message authority, delegation defaults, multi-operator grants, and all earlier choices remain open.

## Provenance

The operator asked on 2026-09-27 for design of operator oversight and intervention before a multi-model review of the wiki. The operator-as-participant idea comes from the original PoC design notes and the participant model handed to Codex the same day. Claude wrote the oversight authority split, intervention grades, redaction, attention routing, and authentication approach on this page as proposals. The residual-bytes caution cites the Codex session-management research at the pinned PoC revision. Nothing here was implemented or tested.

Codex reviewed this page on 2026-09-27 against the pinned imports and the integrated participant/conversation model. The labeled review adds counterproposals, evidence limits, failure cases, and links to schema/interface owners; it preserves Claude's original proposals for multi-model review. No new operator decision, implementation, or experiment is claimed.
