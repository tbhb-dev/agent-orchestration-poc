---
title: Structured requests
summary: "Proposed request claims and outcomes, with Codex review of candidate eligibility, state races, visibility, and evidence."
type: design
status: draft
tags:
  - area/messaging
  - area/orchestration
  - scope/destination
updated: 2026-09-27
---

**Claim status:** Everything on this page is **proposed**. Claude drafted it at the operator's request on 2026-09-27, before a multi-model review of the wiki. Whether structured requests belong in the first experiment at all is itself an open question, discussed below. It builds on the [schema](messaging-schema.md), [API](messaging-api.md), [commands](messaging-commands.md), and [experiment](messaging-experiments.md) pages.

**Review navigation:** Claude's original proposal is retained below. The labeled [Codex review](#codex-review) records integration recommendations and qualifications; where they differ, both remain proposals for operator review.

## The problem with free-text requests

Today a request is a message with `expects_reply` set. "Please merge my branch," "can you review this diff," and "what's the status of the migration" all look the same to agentd. Whether a request was taken on, is being worked, or was finished lives entirely in model judgment and free text. That has three costs:

- **Senders can't tell where their request stands.** The operator's PoCs showed senders getting anxious when replies didn't come. Presence and receipts help with "has it arrived" and "is the recipient busy," but not with "did they take this on."
- **Multi-recipient requests invite duplicate work.** A request to a role or a channel reaches several workloads, and nothing stops two of them from doing the same job.
- **Requests can't link to the work they cause.** A merge request that results in a Task has no recorded connection to that Task, so neither the sender nor the operator can follow the request through to its outcome.

## Requests versus API operations

Before adding a request kind, it's worth drawing the line it shouldn't cross. Some things an agent might "ask for" are really operations agentd can perform directly under policy: launching a child workload, suspending a Task, adding a member to a channel. Those should stay authorized API calls. Routing them through messages would turn messaging into a remote procedure call layer with worse authorization and no clear failure semantics.

Proposed rule: **if fulfilling it needs another agent's judgment, it's a request. If agentd can just do it under policy, it's an API operation.** "Merge my branch after checking it against main" needs the merge group's judgment, so it's a request. "Create a Task in my own group" doesn't, so it's an API call the requester makes itself if its permissions allow.

A request never grants authority. Accepting a request is the recipient's decision under its own group's policy, which preserves the invariant in [group peering](group-peering.md) that a remote requester keeps its original scope.

## The request kind

Proposed: a request is a message with `kind: request` plus a request record. The message carries the content as usual, and the record carries status.

| Field | Meaning |
| --- | --- |
| `assignment` | `any` (one recipient should take it) or `each` (every recipient should respond individually) |
| `status` | For `any`: the request's overall status. For `each`: tracked per recipient. |
| `assignee` | For `any`: the participant that claimed it, if any. |
| `deadline` | Optional. Displayed and used for overdue status, but not a timer that wakes or escalates anything by itself. |
| `outcome_message_id` | The reply that resolved the request, when resolved by reply. |
| `fulfilled_by` | Optional references to Tasks or workloads created to fulfill it. |

**Status values:** `open`, `claimed`, `completed`, `declined`, `failed`, `cancelled`. `Overdue` is a display state derived from the deadline, not a stored status. `Delivered` and `seen` stay on delivery receipts where they already live, not duplicated here.

## Status rides on replies

A request lifecycle that depends on agents running separate status commands repeats the explicit-ack problem: agents forget bookkeeping, and the sender is left with stale status. The design should get status from actions agents take anyway.

- **Claiming.** For `any` requests, the first recipient to reply with an outcome or an explicit claim becomes the assignee. A reply that says "I'll take this" can carry a claim flag in the same send. Agentd rejects a second claim with `request_already_claimed`, and the rejected workload learns someone else has it before duplicating work.
- **Resolving.** A reply can carry an outcome (`completed`, `declined`, `failed`) in the same send: `agentw request reply REQUEST_ID --outcome completed --body '...'`. The reply is both the answer and the status change, so there's no separate step to forget.
- **Plain replies.** A reply to a request without an outcome keeps the request open. Clarifying questions and progress notes don't close anything by accident.
- **Cancelling.** Only the sender can cancel, through a cancel action that notifies the assignee if there is one.
- **Working.** "The assignee is working on it" isn't stored. It's shown from presence evidence when an injecting adapter knows the assignee's current turn was triggered by the request, as the presence design already allows. Where that evidence isn't available, the status shows `claimed` and nothing more.

Agents will still sometimes finish work without replying with an outcome. The sender view should show claimed requests with no outcome as candidates for a follow-up question, and the soft backpressure in the [loop and budget controls](messaging-loops-and-budgets.md) should steer senders toward `message wait` instead of repeated pings.

## Assignment and the three conversation constructs

- **DM with one other participant.** `assignment` is effectively `any` with one candidate.
- **Multi-participant DM.** Either mode makes sense. `any` suits "someone please review this." `each` suits "everyone confirm you've rebased."
- **Channel.** Requests in a channel should usually be `any` and address a role, for example a merge request in a `merges` channel mentioning the `merger` role. The claim makes it visible to every member that the request is taken, even members who only read ambiently.
- **Threads.** A request can open a thread, and discussion about it happens there. Status stays on the request record, not the thread.

## Links to Tasks and outcomes

When fulfilling a request launches a Task, the Task creation call can reference the request, and agentd records it in `fulfilled_by`. That gives the sender and operator a path from request to execution.

Proposed: don't mark a request completed automatically when a linked Task ends. The [destination mental model](mental-model.md) already notes that Task completion needs an explicit result contract and that a finished execution doesn't prove the requested work succeeded. The assignee still resolves the request with an outcome reply, which can cite the Task's result. Automatic completion could come later if the Task result contract makes it trustworthy.

## Loops and requests

Request links make one class of loop detectable. If A's request to B leads B to send a request to A, and A's reply to that leads to another request to B, the request graph contains a cycle that plain messages wouldn't reveal. The [loop and budget controls](messaging-loops-and-budgets.md) can use request cycles as a breaker signal. Requests created during a turn triggered by another request also carry causal depth, which bounds delegation chains.

## Should requests be in the first experiment?

The first experiment compares DM-style and channel-style coordination. Adding structured requests at the same time would mix two variables. Two options:

- **Defer.** Run the conversation comparison with free-text `expects_reply` first, then run a second comparison of free-text versus structured requests with the conversation model held fixed. This isolates each effect but delays learning about requests.
- **Include from the start.** Structured requests may reduce anxious re-pings and duplicate work enough to change the outcome of the conversation comparison, and it may be better to learn that early.

Claude leans toward deferring, since the experiment page already warns against mixing effects. The metrics that would show whether requests help are already on the experiment page: re-sends and pings before a reply, duplicate actions, and send-to-reply latency. A request comparison would add claim conflicts and unresolved-claim counts.

## Schema and interface implications

Candidate additions for the other pages:

- **Message kind** field on `messages`, with `message`, `request`, and the agentd `notice` kind from the [envelope design](messaging-envelope.md).
- **Request table** keyed by message ID, holding assignment, status, assignee, deadline, outcome reference, and fulfillment links. For `each` requests, a per-recipient status table keyed by message and participant.
- **Reply fields** for `claim` and `outcome`, validated against the request's state in the reply's acceptance transaction, so a reply and its status change commit together.
- **Error codes** `request_already_claimed`, `request_closed`, and `not_request_recipient`.
- **Commands** such as `agentw request send`, `agentw request reply --outcome`, `agentw request claim`, `agentw request cancel`, and `agentw request list --mine|--assigned`.
- **Event log kinds** for claim, resolution, cancellation, and fulfillment links.
- **Envelope rendering** that shows request status, assignment, and the exact reply command, so the recipient knows it's a request and how to resolve it.

## Open questions

- Whether requests enter the first experiment or a later one.
- Whether a claim can be released or reassigned, and by whom.
- Whether `each` requests need per-recipient deadlines.
- Whether operator messages can create requests that carry operator authority, which depends on the unresolved question in [operator oversight](operator-oversight.md#operator-messages-and-authority).
- Whether bots can create or claim requests, for example a CI bot filing a "fix this failing test" request.
- The [central retention decision](messaging-schema.md#retention-and-redaction-open-decision), including closed requests and their links.

## Codex review

**Peer review and counterproposals, 2026-09-27; all proposed:** A structured request is useful coordination state, but it cannot guarantee that a claimant actually does the work, or prevent duplicate external side effects if someone acts before claiming. Recommend testing requests as a second comparison, preserving the first-experiment decision as open. The proposed capability-versus-permission distinction still applies: neither a request, claim, Task link, nor outcome grants authority.

The original first-outcome-wins rule needs a decline exception. Recommend that an unclaimed `any` candidate's `declined` outcome update only that candidate; others can still claim. If all candidates decline, mark the request declined. Once claimed, only that assignee can report its outcome, while the sender may cancel. For `each`, each eligible participant changes only its own state; aggregate display must show partial/mixed outcomes rather than invent an overall completed result. A plain reply preserves `claimed` as well as `open`; it never reopens terminal state. Reassignment, abandoned-claim expiry, and automatic retries remain undesigned, not implicit.

Fix candidates at original acceptance from the declared recipient snapshot, activating them only on publication after hold revalidation. Ambient channel readership and later role membership do not add claim eligibility. Reject zero-candidate requests for the initial proposal; a public volunteer/open-call mechanism would need separate semantics. Claim competition, reply insertion, outcome, and cancellation serialize atomically with stable retry keys; lost responses return the committed result even if state has since changed. Cancellation is a coordination status and notification, not termination of a Task or rollback of an external operation. Define cancellation notification recipients explicitly and subject them to ordinary budgets; no inferred lifecycle command.

The original “working on it” suggestion overstates turn-trigger evidence. Prefer “claimed; current turn began with this request” only where qualified evidence supports that statement, as [presence](messaging-schema.md#presence-observations) already distinguishes triggering input from ongoing work. Otherwise report claimed plus independently sampled presence. Request deadlines should normalize to `reply_by`, not introduce competing clocks. Task references and outcome-message links need their own visibility checks; an ambient request view cannot reveal a private DM outcome body. Held request replies change state only on release after revalidation.

Proposed tests include simultaneous claims, one candidate declining before another claims, partial `each` outcomes, cancel-versus-complete, lost claim/outcome responses, sender/recipient revocation, held transitions, private outcome visibility, stale claimant recovery, and misleading Task-completion assertions. Explicit request links can suggest repeated participant dependencies, but chronological message links alone do not prove a deadlocked workflow cycle. No tests or new research probes were run. Persistence/routes/commands are linked from [schema](messaging-schema.md#requests-controls-and-publication), [API](messaging-api.md#requests-backpressure-and-management-separation), and [commands](messaging-commands.md#request-commands-and-envelope-output); retention is one [central open item](messaging-schema.md#retention-and-redaction-open-decision).

## Provenance

The operator asked on 2026-09-27 for design of structured requests before a multi-model review of the wiki. The received, working, and replied lifecycle idea and the request-to-Task linkage question came from the earlier messaging discussion the same day. Claude wrote the request kind, reply-carried status, claim semantics, and the request-versus-operation rule on this page as proposals. Nothing here was implemented or tested.

Codex reviewed this page on 2026-09-27 against the pinned imports and the integrated participant/conversation model. The labeled review adds counterproposals, evidence limits, failure cases, and links to schema/interface owners; it preserves Claude's original proposals for multi-model review. No new operator decision, implementation, or experiment is claimed.
