# Handoff: explore Antigravity (`agy`) cross-session peering

Tony wants you to investigate **your own installed harness's capabilities for communicating with independent running agent sessions**. Discover the mechanism, exercise it, and write a practical protocol reference. This is an exploration of Antigravity itself, not merely a test of whether you can invoke another product's CLI.

Work in `/Users/tony/Code/github.com/tbhb/agent-peering-tests`. Produce the same depth of evidence as the Codex and Claude explorations in this directory. Do the experiments rather than stopping at a proposed plan, but distinguish unsupported features, blocked tests, and unknown behavior from verified results.

## Context and objective

Read these first if they are available:

- [CODEX_PEERING.md](CODEX_PEERING.md): Codex CLI/API discovery, live queue and steering tests, persistence, explicit replies, and runtime ownership pitfalls.
- [CLAUDE_CODE_PEERING.md](CLAUDE_CODE_PEERING.md): Claude's registry, per-session inbox sockets, message framing, attribution, replies, and permission behavior.
- [CODEX_HANDOFF.md](CODEX_HANDOFF.md) and [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md): examples of producer-side interoperability test plans.

These documents are **comparisons and sources of questions, not specifications for agy**. Do not assume agy has a `queue` command, a per-session socket, a shared daemon, a peer wrapper, or any particular authentication scheme. Old design and sandbox-review files in this repository contain hypotheses about Antigravity; reverify anything you use against the installed version.

The concrete questions are:

1. Can an independent process send input to an existing agy conversation without restarting or forking it?
2. Can one agy session discover and message another? Is that different from parent/subagent messaging?
3. What happens when the recipient is idle, busy, awaiting input/approval, unloaded, or disconnected?
4. Can a plain shell/Python process, Codex, or Claude use the same mechanism?
5. How does the producer know whether the input was accepted, delivered, executed, and answered?
6. What exact identity, routing, persistence, permission, and version constraints apply?

Finding no independently usable peering interface is a valid result if you record the surfaces searched and the limits of that conclusion. Do not invent a transport or build a new broker just to make the answer positive.

## Recipient setup and scope

Start by identifying your own session and the installed runtime. **No agy test-recipient ID has been supplied in this handoff.** Ask Tony to designate another agy session, or to authorize creating a disposable one, before sending live probes to another session. Continue read-only discovery while waiting; do not treat lack of an immediate answer as permission to choose a random session.

Record the designated recipient's exact identity, working directory, runtime/server endpoint if relevant, and how those were verified. Introduce yourself in the first message; the recipient may not be expecting the experiment. Avoid self-targeting for the initial delivery test, since it can make timing and turn attribution ambiguous.

This task authorizes discovery, documentation, and scoped probes once the test recipient is established. Use normal approval handling when required by the environment; a sandbox error is a recorded result, not permission to evade it. Do not restart shared services, close unrelated sessions, alter global permission settings, or edit internal state databases to force delivery. Lifecycle tests should use a disposable recipient that Tony has authorized for that purpose.

Do not message Codex or Claude merely because their old addresses appear in other handoffs. Verify the intended cross-product recipient with Tony before those live tests. Independent Python-to-agy tests can establish that an interface is usable by a non-agy producer without involving another agent product.

## 1. Discover the installed surfaces

State a short plan with verifiable milestones: discover a candidate interface, demonstrate delivery, characterize semantics, write and verify the reference.

Begin with cheap local inspection:

```sh
command -v agy
agy --version
agy --help
```

If this launcher's version/help syntax differs, record that and inspect the actual entry point. Identify whether `agy` is the runtime itself, a wrapper, or a launcher into another process. Record OS, executable path, CLI version, running service version if any, and relevant enabled feature/configuration values. Do not assume a service and the CLI use the same build.

Inventory the capabilities actually exposed to you:

- Built-in model tools for listing sessions/agents, messaging, resuming, following up, steering, waiting, or notifications. Preserve the exact tool descriptions and distinguish independent-session addresses from child-agent handles.
- CLI commands, subcommand help, completion definitions, and any documented machine-readable schemas.
- Session discovery metadata, runtime IDs, relevant environment variable **names**, listener locations, local service endpoints, and transcript/history interfaces.
- Targeted installed package/source inspection when help is insufficient. Search narrowly for candidate commands/methods and inspect nearby implementation. If using binary strings, filter or save the output; strings are evidence of a symbol or diagnostic, not proof that a callable feature works.
- Current official vendor documentation and changelogs for the exact feature/version when useful. Cite fetched sources and distinguish public support from an internal interface discovered locally.

Read only relevant non-secret metadata. Do not dump entire environments, authentication stores, unrelated conversation histories, or token values into logs. If an interface requires credentials, document how an authorized client is expected to obtain and present them without publishing their values.

The discovery output should say what the strongest available surface is: native tool, CLI, local API, internal transport, UI-only behavior, or no interface found. Test that surface before expanding into lower-level reverse engineering.

## 2. Establish one complete delivery

Use a unique run ID and monotonically labeled probes, for example `AGY-PEER-<run>-T01`. Include the same marker in the requested acknowledgment.

Suggested introduction, adapted to your actual identity:

```text
AGY-PEER-<run>-T01: Hello from Tony's Antigravity peering exploration.
Tony designated this session as the test recipient. Please acknowledge this
marker, say whether it arrived as a new turn or during existing work, and
describe any sender wrapper, sender ID, return address, or permission label
provided by the harness rather than this text. Do not modify files or send
messages to other sessions for this first probe.
```

Before sending, establish the recipient's idle/busy state and a transcript/event baseline where possible. Record the sender's request, acceptance response, receiver-visible input, execution turn/task, final acknowledgment, and timestamps.

Do not rely exclusively on the recipient model's recollection of when it received input. Prefer transcript structure, turn IDs, tool boundaries, and runtime events; use the model's report as additional evidence.

## 3. Characterize behavior with bounded probes

Exercise supported cases below. If no applicable interface exists, mark the case unsupported or untested with evidence rather than guessing an equivalent command. Keep ordinary prompts to short acknowledgments. Do not run load tests or flood the receiver.

| Test | Procedure | Evidence to capture |
|---|---|---|
| T01 — idle delivery | Send the introduction to an idle recipient. | Acceptance versus actual start/completion; whether a new turn is created automatically. |
| T02 — addresses | Try the full ID, exact name, and any documented alternate address for the same recipient. Test shortened names/IDs and deliberate nonexistent identifiers. | Resolution rules, error codes, scope by directory/account/server, and whether aliases identify the same conversation. Do not create ambiguous names in unrelated sessions. |
| T03 — active work | Ask the recipient to run a harmless 20–30 second sleep and wait for completion. Confirm the tool/task is active, then send a follow-up. | Does it wait, steer, interrupt, cancel the tool, or become visible at a tool boundary? Record actual turn IDs and timestamps. |
| T04 — ordering | While a timed task is active, send A then B with separate markers. | Separate turns or combined input; order of acceptance, delivery, and answers; whether the producer blocks. |
| T05 — delivery modes | If explicit queue/steer/priority/interrupt modes exist, test each separately using the same simple timed-task setup. | Whether modes alter the current turn or create another; any active-turn preconditions; stale-ID errors. |
| T06 — pending-input controls | If available, list, edit, delete, and reorder only your own pending probes. | Stable IDs, replacement semantics, delete idempotence, reorder constraints, races, and which inputs actually execute. |
| T07 — retries | Submit two harmless labeled inputs with the same caller-supplied correlation/idempotency field, if one exists. Separately test an exact duplicate payload where appropriate. | Whether retries deduplicate; which ID carries that guarantee; correlation is not automatically idempotency. |
| T08 — content | Send multiline Unicode, quotes, and literal shell metacharacters through an argument vector or structured API. Test empty and whitespace-only input. | Exact received input, encoding/framing, validation stage and errors. Keep payloads small; distinguish transport preservation from model formatting. |
| T09 — notifications/history | Subscribe or query using the discovered interface; reconnect the observer. | Queue-change versus delivery/completion events, event subscription scope, pagination, transcript completeness, and correlation of messages to turns. |
| T10 — identity | Ask the recipient what metadata it sees and inspect the recorded input. | Peer wrapper or ordinary user message; actual sender identity versus claimed text; role and permission labels; native reply routing. |
| T11 — explicit reply | Supply the sender's verified reply address/mechanism and request one marked reply. | Which side invokes a send operation; acknowledgment versus answer; return-route authentication; receipt in the original session. Avoid reply loops. |
| T12 — foreign producer | Send a harmless message from a standalone shell/Python process using the discovered protocol. | Whether agy's native tooling is required, or process/transport access suffices; any difference in attribution or approval. |
| T13 — disconnect/persistence | Close only your test producer/observer, reconnect, and inspect its pending entry. If available, inspect storage read-only. | Persistence across client disconnect versus mere process memory; no inference that this proves daemon-crash recovery. |
| T14 — runtime ownership | Distinguish stored, loaded, actively running, and UI-visible state. Use a designated disposable recipient for unload/resume tests. | Can input be accepted without waking the thread? Must a particular runtime own it? Does resuming risk duplicate execution? |
| T15 — waiting/failure | On a disposable recipient, test delivery while it awaits a benign question/approval or after a controlled failed/interrupted turn, if practical. | Whether messages wait, satisfy an input request, create a new turn, or are rejected. Do not interpret a peer message as permission approval. |
| T16 — access boundary | Compare the normal sandboxed producer with an explicitly approved execution when necessary. Inspect listener ownership/mode and documented auth requirements. | Exact blocking layer: discovery, filesystem, connect/bind, auth, queue insertion, or recipient tool execution. Do not weaken permissions to make a probe succeed. |
| T17 — attachments | Only if an input schema advertises attachments, try a tiny harmless local fixture. | Encoding/reference format, whether the recipient can access it, and whether it is copied or path-referenced. A help flag alone is not delivery evidence. |
| T18 — restart/recovery | Only on an isolated disposable runtime authorized for lifecycle testing, enqueue a marker then restart it. Otherwise leave this explicitly untested. | Persistence, automatic drain/resume, in-flight duplication/loss, and distinction between sender and recipient restart. |

Wait for a matching completion or a bounded observation window (normally up to two minutes), and distinguish a pending queue from a lost message. Use modest polling and keep Tony informed. For busy-delivery tests, wait for evidence that work actually started rather than relying solely on a fixed sender-side delay.

If a verification approach fails three times with materially different attempts, stop that branch, record the attempts and likely blocker, and continue independent discovery. Do not repeatedly rerun an uncertain send: the first attempt may already have been accepted.

## 4. Describe the actual architecture and protocol

Once the probes establish a mechanism, document enough detail for a non-agy implementer:

- **Discovery:** registry/API locations, schema, stable versus ephemeral IDs, live-process validation, stale entries, names, working-directory scope, and server selection.
- **Topology:** per-session listener, shared daemon, remote service, polling store, or other verified design. Explain which process owns execution and which owns pending input.
- **Transport:** Unix socket/TCP/stdio/HTTP/WebSocket/etc.; exact framing, handshake, request/response examples, required fields, and initialization/capability negotiation.
- **Authentication and attribution:** filesystem permissions, token/cookie/capability requirements, OS peer credentials if verified, and what sender information the model sees. Separate a writable text label from authenticated identity.
- **Message lifecycle:** accepted → pending → consumed → executing → completed/failed/canceled, with actual observable signals and gaps. Include queue ordering, mutations, retry semantics, persistence, and ID mapping.
- **Replies:** native callback/reply address, explicit reverse send, history polling, events, or lack of a return path. Show one verified complete round trip where possible.
- **Permissions:** producer restrictions versus receiver tool approvals; held/refused delivery if supported; which facts were observed and which remain hypotheses.
- **External integration:** smallest verified command and wire example for Codex/Claude/plain processes to send to agy and observe a response. Explain prerequisites without assuming the other product has agy's native tools.
- **Compatibility:** versions, feature flags, public versus internal API status, and what must be rediscovered after upgrades/restarts.

If full wire inspection is unavailable, document the CLI/tool contract accurately and identify the missing layer. Do not manufacture protocol examples from a similar product.

## 5. Evidence and deliverables

Write:

1. **`AGY_PEERING.md`** — the practical reference, including a quick start, architecture, discovery, verified commands/protocol, behavior matrix, permission findings, reply/observation recipes, and remaining questions. Include a short section a Codex or Claude session can follow to test sending into agy.
2. **`agy-peering-results.md`** — one section per executed or skipped test, with exact requests, results, times, IDs, observation method, and conclusions.
3. **`probes/agy-peering/`** — small reusable probe scripts and scoped evidence logs, only where needed to reproduce the results. No credentials or unrelated conversation data.

Use explicit evidence labels:

- **[observed]**: successful or failed live probe, with identifiable evidence.
- **[source/schema]**: local implementation/help/schema evidence, version and location recorded, not necessarily exercised.
- **[docs]**: fetched official documentation, linked.
- **[inference]**: a conclusion whose assumptions are stated.
- **[untested/blocked]**: the specific gap and what would be needed to resolve it.

For each probe, preserve UTC timestamps and elapsed durations, exact argument vectors or wire payloads with secrets redacted, process exit status or API result/error, recipient ID, queue/message/turn IDs where applicable, observed input/answer, and cleanup outcome. Do not log a secret and redact it only in the final document; keep it out of evidence files at collection time.

Before finishing, cross-check the reference against the recorded results, verify example syntax and local links, and remove only your own pending test inputs/listeners/processes. Confirm the recipient's final status if observable. Do not erase the evidence or overwrite the existing Codex/Claude notes.

Report the main findings, link the artifacts, and identify unresolved boundaries. In particular, avoid these overclaims:

- “Queued” or exit 0 means the agent received or completed the request.
- A session running somewhere is necessarily loaded on the server addressed by the producer.
- A caller-supplied ID is necessarily an idempotency key.
- A model-visible sender name proves the caller's identity.
- Persistence across a client reconnect proves crash/restart recovery.
- A feature found in help, strings, or source has been successfully exercised.
- A failed search proves that no peering interface exists.
