# Claude Code Session Management, Behavior, and Persistence

This report covers how Claude Code identifies, tracks, persists, resumes, forks, and cleans up sessions, written to inform a cross-harness session manager for observability and control. It was produced by a Claude Code session inspecting its own state and running controlled experiments against the CLI on 2026-09-26.

Environment: Claude Code `2.1.283`, macOS (darwin), `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, `cleanupPeriodDays: 7`. Seven other interactive sessions were live during the investigation, which gave real multi-session data to observe.

Claims are tagged by how they were established:

- **[verified]**: observed on disk or reproduced by experiment in this session.
- **[observed]**: seen in existing data from other sessions, but not reproduced deliberately.
- **[help-text]**: taken from `claude --help`, not exercised.

Everything here is an internal, undocumented on-disk format unless stated otherwise. Field names changed across the 2.1.27x to 2.1.283 versions seen in these files, so any tool built on it should parse leniently.

## 1. Summary for a session manager

The short version, if you only read one section:

| Question | Best source | Notes |
| --- | --- | --- |
| Which sessions are running right now? | `claude agents --json` (supported CLI) or `~/.claude/sessions/<pid>.json` | Registry entries include status (`busy` / `idle` / `waiting`), cwd, name, tmux pane, and messaging socket |
| Is a registry entry still alive? | `kill -0 pid` plus compare `procStart` against the process start time | `procStart` is recorded in UTC and guards against PID reuse |
| What happened in a session? | `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl` | Append-only JSONL tree of messages plus metadata records |
| Session title / name | `ai-title`, `custom-title`, `agent-name` records in the transcript; `name` in the registry | Last one wins; records repeat many times |
| Cost and token usage | `cost-state` record in the transcript; `result` message in `-p --output-format json` | `cost-state` is a cumulative snapshot with per-model breakdown |
| Background-job progress | `~/.claude/jobs/<short-id>/state.json` and `timeline.jsonl` | Has a model-authored `state` / `detail` narrative separate from process status |
| Push-based events | Hooks (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `SessionEnd`, and more) | Every payload carries `session_id`, `transcript_path`, `cwd` |
| Subagents | `<session-id>/subagents/agent-<id>.jsonl` plus `.meta.json` | Sidechain transcripts nested under the parent session |
| Control | `claude --resume`, `--continue`, `--fork-session`, `--session-id`, `--bg`, `attach`, `logs`, `stop`, `rm`, `respawn` | The background-session commands only address daemon-managed sessions |

The most important structural facts:

1. **Session identity is a UUID** that you can choose up front (`--session-id`), and it is stable across resume. Fork mints a new UUID.
2. **The transcript file is keyed by the directory the session was *started* in**, not the directory it is in now. Resuming from elsewhere, or moving into a worktree, appends to the original file while the per-record `cwd` changes.
3. **Liveness and history are separate stores.** `sessions/<pid>.json` is the live registry and disappears when the process exits cleanly. `projects/**.jsonl` is the durable history.
4. **Retention is time-based.** `cleanupPeriodDays` (7 here) prunes old transcripts. A manager that wants long history must copy transcripts out on its own schedule.

## 2. Directory map

Everything lives under `~/.claude/` (override with `CLAUDE_CONFIG_DIR`, not tested). Per-session state is spread across several siblings rather than in one per-session directory.

```text
~/.claude/
├── sessions/                     # LIVE registry, one file per running process
│   ├── <pid>.json                #   status, sessionId, cwd, name, tmux, socket …
│   └── <pid>.<hash>.key          #   per-process secret (messaging auth; not read)
├── projects/                     # DURABLE transcripts, grouped by start directory
│   └── <encoded-cwd>/
│       ├── <session-id>.jsonl    #   main transcript
│       ├── <session-id>/
│       │   ├── subagents/agent-<agentId>.jsonl       # sidechain transcripts
│       │   ├── subagents/agent-<agentId>.meta.json   # agentType, description, spawn info
│       │   └── tool-results/<id>.txt                 # oversized tool outputs spilled to disk
│       └── memory/               #   auto-memory (per project, not per session)
├── history.jsonl                 # prompt history across all projects (interactive only)
├── file-history/<session-id>/    # pre-edit file backups for /rewind (content-hash@vN)
├── session-env/<session-id>/     # per-session env scratch (empty in every sample)
├── shell-snapshots/              # shell env snapshots used to seed Bash tool
├── tasks/session-<id8>/          # per-session task list (Task tools)
├── teams/session-<id8>/          # agent-teams config + per-member inboxes
│   ├── config.json
│   └── inboxes/<member>.json
├── jobs/                         # BACKGROUND sessions (daemon-managed)
│   ├── <short-id>/state.json
│   ├── <short-id>/timeline.jsonl
│   └── pins.json
├── daemon/                       # background supervisor state
│   ├── roster.json               #   supervisor pid + worker table
│   ├── control.key, auth/, dispatch/
└── .last-cleanup                 # ISO timestamp of the last retention sweep
```

Sockets live outside `~/.claude`: `/tmp/cc-socks/<pid>.sock` for per-session peer messaging, and `/tmp/cc-daemon-<uid>/<hash>/…` for the background daemon's rendezvous and PTY sockets. [verified]

### Project directory encoding

`<encoded-cwd>` is the absolute start directory with `/` and `.` both replaced by `-` [verified]. Examples:

- `/Users/tony/Code/github.com/tbhb/agent-session-tests` becomes `-Users-tony-Code-github-com-tbhb-agent-session-tests`.
- `/Users/tony/.claude` becomes `-Users-tony--claude`.
- `…/vale-ai-tells/.claude/worktrees/strained` becomes `…-vale-ai-tells--claude-worktrees-strained`.

The encoding is lossy: `github.com` and `github/com` would collide, and it cannot be reversed. **Never decode the directory name; read `cwd` from the records inside.** Directory names start with `-`, so shell tools need `./` or `--` in front of them (`ls -…` fails).

## 3. Live registry: `~/.claude/sessions/<pid>.json`

Each running Claude Code process writes one JSON file, named by PID, and keeps it updated as its status changes [verified]. A real entry (this session):

```json
{
  "pid": 12852,
  "sessionId": "de7c9c89-4c37-4dcb-9fea-494e30f3d23c",
  "cwd": "/Users/tony/Code/github.com/tbhb/agent-session-tests",
  "startedAt": 1790433922166,
  "procStart": "Sat Sep 26 14:45:21 2026",
  "version": "2.1.283",
  "peerProtocol": 1,
  "peerFeatures": ["notify_idle", "reply_across_default_dirs", "artifact_yield"],
  "kind": "interactive",
  "entrypoint": "cli",
  "pidDomain": "darwin",
  "tmux": "0:@6.%22",
  "messagingSocketPath": "/tmp/cc-socks/12852.sock",
  "name": "agent-session-tests-ba",
  "nameSource": "derived",
  "nameSince": 1790433922166,
  "status": "busy",
  "updatedAt": 1790433923672,
  "statusUpdatedAt": 1790433923672
}
```

Field notes:

- **`status`** takes the values `busy`, `idle`, and `waiting`. When `waiting`, a `waitingFor` string explains why; the values seen were `"input needed"` and `"dialog open"` (a permission prompt). [observed] This is the cheapest "needs attention" signal available.
- **`kind`** is `interactive` for TUI sessions and `bg` for daemon-managed background sessions [verified]. `claude agents --json` normalizes `bg` to `"background"`. Headless `claude -p` runs **also register while running, as `kind: "interactive"` with `entrypoint: "sdk-cli"`** [verified], so use `entrypoint` to tell them apart.
- **`procStart`** is the process start time in UTC (compare `ps -o lstart=`, which is local time). Use it with the PID to reject a recycled PID.
- **`tmux`** is `session:@window.%pane` when running inside tmux, which lets a manager jump to or capture the pane directly.
- **`name` / `nameSource`**: `derived` names are `<dirname>-<2 hex>`; `user` means set by `-n/--name` or `/rename`; `peer` was seen on a background session named at dispatch.
- Background entries also carry `jobId` (the short ID).

Lifecycle: the file appears at startup and is removed on clean exit (`claude stop` removed it within 3 seconds) [verified]. A `kill -9` leaves a stale file showing `busy` that is swept later by something not yet identified, and leaves the socket permanently (see 4.5) [verified], so always check liveness. All eight entries present during this investigation were live, including one 11 days old.

`claude agents --json` is the supported view of the same data (a trimmed subset: `pid`, `id`, `cwd`, `kind`, `startedAt`, `sessionId`, `name`, `status`, plus `state` for background jobs). `--all` adds completed background sessions; `--cwd <path>` filters. It needs no TTY. [verified]

## 4. Durable transcript: `projects/<encoded-cwd>/<session-id>.jsonl`

Append-only JSONL, written incrementally during the session at turn, response, and tool-completion boundaries rather than while streaming (see 4.5). Files are mode `0600`. [verified]

### 4.1 Conversation records

`user`, `assistant`, `system`, and `attachment` records form a **tree** through `uuid` / `parentUuid`. Common fields: `sessionId`, `timestamp` (ISO), `cwd`, `gitBranch`, `version`, `entrypoint` (`cli` or `sdk-cli`), `isSidechain`, `userType`. [verified]

- **`assistant`** records carry `message` (Anthropic API message with `usage`), `requestId`, `effort`, and the model. Streaming produces multiple assistant records per API response (`apiBlockIndex`).
- **`user`** records are human prompts *and* tool results (`toolUseResult`, `sourceToolAssistantUUID`). Provenance fields are useful for observability: `origin.kind` (`human`, or `peer` with `from` / `senderTaskId` for subagent hand-backs and peer messages), `promptSource` (`typed`), and `turnOrigin` (`human`, `sdk`). [verified / observed]
- **`attachment`** records hold context injected into the turn: `environment`, `instructions` (CLAUDE.md), `skill_listing`, `deferred_tools_delta`, `mcp_instructions_delta`, `date`, `model`, `session_context`, `total_tokens_reminder`, and others. [verified]
- **`system`** subtypes seen: `turn_duration` (with `durationMs`, one per turn and ideal for latency metrics), `away_summary`, `local_command` (slash commands), `informational`, `model_refusal_fallback`, `compact_boundary`. [observed]

### 4.2 Metadata records (no `uuid`, keyed by `sessionId`)

These are rewritten repeatedly (for example, 38 `ai-title` records in one session). Read the **last** occurrence of each. [verified / observed]

| `type` | Payload | Use |
| --- | --- | --- |
| `ai-title` | `aiTitle` | Auto-generated title (what `/resume` shows) |
| `custom-title` | `customTitle` | User-set title (`/rename`, `-n`); prefer over `ai-title` |
| `agent-name` | `agentName` | Name used for peer messaging |
| `last-prompt` | `lastPrompt` (truncated), `leafUuid` | Current leaf of the conversation tree and a preview |
| `mode` / `permission-mode` | `mode`, `permissionMode` | Mode changes (for example `auto`, `default`) |
| `cost-state` | `totalCostUSD`, `totalAPIDuration`, `totalToolDuration`, `totalLinesAdded` / `Removed`, `totalDuration`, `startTime`, `modelUsage{model: tokens, costUSD}` | Cumulative cost snapshot |
| `queue-operation` | `operation` (`enqueue` / `remove`), `content`, `reason` (for example `absorbed_mid_turn`) | Prompts typed while the agent was busy |
| `file-history-snapshot` / `file-history-delta` | tracked file backups per message | Backs `/rewind`; content in `file-history/<session-id>/` |
| `worktree-state` | `worktreePath`, `worktreeBranch`, `originalCwd`, `originalBranch`, `originalHeadCommit`, `sessionId` | Session is operating inside a git worktree |
| `relocated` | `relocatedCwd` | Session's working directory moved |
| `atis-latch` | `atis` | Internal; ignore |

### 4.3 Compaction

A `/compact` (or auto-compact) writes a `system` / `compact_boundary` record with `parentUuid: null`, a `logicalParentUuid` back into the old tree, and `compactMetadata` (`trigger: manual|auto`, `preTokens`, `postTokens`, `durationMs`, preserved message UUIDs). The next record is a `user` message with `isCompactSummary: true` holding the summary. The pre-compaction history **stays in the same file**. The file is the full history, and the model's context is only the part after the last boundary. [observed]

### 4.4 Oversized tool output

Tool results too large for context are written to `projects/<encoded-cwd>/<session-id>/tool-results/<id>.txt`, and the transcript and model see a pointer plus a preview. This happened live to one of my own commands during the investigation. [verified]

### 4.5 Write timing and crash durability (interactive)

The transcript is written at **completion boundaries**: when a prompt is submitted, when a model response finishes, and when a tool call finishes. It is not a live stream. Everything below is [verified] with a fresh interactive session (`claude --session-id <uuid> --model haiku --name flush-lab`) driven through a detached tmux session. A watcher polled the transcript size every 1 ms, recording which records each growth event added, and also tracked the registry file and the tmux pane. The run produced 21 write events.

**No file handle is held.** `lsof` on a live session shows no open `.jsonl`. Every growth event contained whole records: across 21 events there were zero partial lines and zero unparseable lines, including a single 187 KB event. That is consistent with open, append, and close per batch. The exact syscall pattern was not traced, because `fs_usage` needs root.

**The file is created lazily.** A newly started session has a registry entry immediately, but **no transcript file exists until the first prompt is submitted**. A manager that sees a registry entry must not assume `transcript_path` exists yet.

When records land, with timings relative to pressing Enter:

| Moment | What is written | Observed timing |
| --- | --- | --- |
| Prompt submitted | First turn only: the metadata block (`custom-title`, `agent-name`, `mode`, `permission-mode`, `atis-latch`). Every turn: `file-history-snapshot`, the `user` record, and the context `attachment`s. Written **before** the API call | +40 ms to +150 ms |
| Response streaming | **Nothing.** In one run the text was on screen from +1.6 s and fully rendered by +10.8 s, with no assistant bytes on disk in between | — |
| Response complete | Every content block of that API response in one batch (`thinking`, `text`, `tool_use`) | About 50 ms after the stream ends |
| Tool awaiting permission | The `tool_use` is already on disk, and nothing more is written while the prompt is open (33 s in one run). Registry shows `waiting` | — |
| Tool running | **Nothing.** A 6-second loop printing a line per second wrote nothing until it exited | — |
| Tool complete | One `user` record with the `tool_result`, then a `total_tokens_reminder` attachment | On exit of the tool |
| Turn complete | Final response batch plus `system/turn_duration`; `last-prompt` after the first turn only | About 50 to 100 ms **after** the registry flips to `idle` |
| Idle | **Nothing.** Zero writes in 60 s idle | — |
| `/exit` | `file-history-snapshot`, `last-prompt`, `cost-state`, then the three `user` records of the `/exit` command | Within 0.5 s |

Two consequences stand out. First, a streaming response or a long tool call is invisible on disk until it finishes, so transcript tailing lags the screen by up to a full response or tool duration. Second, **`cost-state` was written only at `/exit`**, not after any turn, in the interactive session. `-p` runs do write it after each turn. No `ai-title` was written during this short session either.

**The registry leads the transcript.** Status went `busy` 40 to 60 ms after Enter, and the transcript's first write came right after. At the end of a turn the registry flipped to `idle` before the final assistant batch hit disk. A manager that reacts to `idle` by reading the transcript should allow about 100 ms, or re-read on the next file change.

#### Crash (`kill -9`) behavior

| Killed during | On disk afterwards | Lost |
| --- | --- | --- |
| Response streaming, about 2 s into visible output | The `user` prompt and its attachments | **All streamed text**, even what was already on screen |
| Tool execution (`sleep 20`, killed 4 s in) | The assistant's `tool_use` record, with no `tool_result` | The tool outcome. **The tool's subprocess was orphaned and kept running** after its session died |

Side effects of a hard kill:

- **`sessions/<pid>.json` is left behind with `status: "busy"`.** Stale files were later removed by something: one was gone within seconds, after a `claude agents --json` call, and the other was still present when the session was resumed about 25 s later, then gone shortly after. Which process sweeps them was not isolated. During the overlap, a watcher that matches registry files by `sessionId` saw **two entries for one session**: the dead PID's `busy` file and the new PID's file.
- **`/tmp/cc-socks/<pid>.sock` is not removed.** Sockets for both killed PIDs were still present at the end of the experiment.
- There is no `cost-state` for the killed run, since it is only written on exit.

**Resume repairs the transcript, but lazily.** On `--resume`, Claude Code closes the broken turn with synthetic records:

- For a prompt with no response: an `assistant` record with `model: "<synthetic>"` and the text `"No response requested."`.
- For a `tool_use` with no result: a `user` `tool_result` with `is_error: true` and the content `"[Tool call interrupted: the session ended before this call's result was recorded, so its outcome is …"`.

Both are **held in memory and only written together with the next prompt**, carrying a timestamp from the resume time. Resuming wrote nothing at launch in one case, and only the metadata block in the other. So a transcript can end in a dangling state even while a resumed session is live and idle on it.

Implications for a manager:

- **Live progress** comes from the registry (status changes are sub-second), from hooks (`PreToolUse` and `PostToolUse` bracket tool execution), or from `tmux capture-pane`. It does not come from the transcript.
- **Crash detection:** the last conversation record is a `user` prompt, or a `tool_use` without a matching `tool_result`, *and* no live process holds the session. Check the PID with `procStart`, not just the presence of a registry file.
- **Cost for crashed interactive runs has to be summed** from `assistant.message.usage` (grouped by `requestId`), since `cost-state` never lands.
- **Sweep stale sockets and registry files** when validating liveness, and dedupe registry entries by `sessionId`, preferring the live PID.

## 5. Lifecycle operations (tested)

All experiments used `claude -p --model haiku` in a scratch directory unless noted. [verified]

| Operation | Command | Result |
| --- | --- | --- |
| New session with chosen ID | `claude -p --session-id <uuid> …` | Transcript created at `<uuid>.jsonl`; `session_id` echoed in JSON output |
| Reuse an ID that exists | `claude -p --session-id <existing> …` | Refused: `Error: Session ID … is already in use.` |
| Resume by ID | `claude -p --resume <uuid> …` | Same `session_id`; prior context present (it recalled its earlier answer); records **appended to the same file** |
| Resume from a different directory | `cd other && claude -p --resume <uuid> …` | Works. Appends to the **original** project dir's file; new records carry `cwd: …/other`; an empty project dir for `other` is created |
| Continue most recent | `claude -p -c …` | Picks the most recent session **in the current directory**, including forks |
| Fork | `claude -p --resume <uuid> --fork-session …` | New UUID and new file. The parent's records are copied with `sessionId` rewritten, and **message `uuid`s are preserved** (21 of 21 shared). No field names the parent session ID |
| No persistence | `claude -p --no-session-persistence …` | Gets a session ID, writes no transcript (only valid with `-p`) |
| Background launch | `claude --bg -n <name> "<prompt>"` | Prints short ID (first 8 hex of the session UUID); refuses untrusted workspaces (`-p` does not check trust) |
| Background logs | `claude logs <short>` | Raw PTY byte stream (ANSI escapes and redraws); not structured |
| Background stop | `claude stop <short>` | Registry entry removed; job state becomes `stopped`; transcript kept |
| Background remove | `claude rm <short>` | Deletes `jobs/<short>/` only. **Transcript, `tasks/`, `teams/`, `session-env/` all remain** |

Not exercised: interactive `/resume` picker, `--from-pr`, `--teleport`, `--cloud`, `--remote-control`, `claude attach`, `claude respawn`, `claude project purge` (help text says it deletes transcripts, tasks, file history, and the config entry for a project path) [help-text].

### Fork lineage

Because a fork never records its parent ID, a manager has to infer lineage. The reliable method is **shared message `uuid`s**: the fork's first N records have the same `uuid`s as the parent's. Build an index of `uuid → first sessionId seen (by earliest timestamp)` and any session whose early UUIDs belong to another session is a fork of it.

### Resume and working-directory drift

A single session can span several directories and CLI versions. One 8-day-old session in the data started in `vale-ai-tells`, moved into `vale-ai-tells/.claude/worktrees/strained` (with `worktree-state` and `relocated` records), was resumed under a newer CLI (records from 2.1.273 and 2.1.277 in one file), and had its `tool-results/` written under the worktree's project dir while the transcript stayed under the original. So:

- The transcript path is found by session ID, not by current cwd. Glob `projects/*/<session-id>.jsonl`.
- Auxiliary per-session directories can live under a **different** project dir from the transcript. Glob `projects/*/<session-id>/` too.
- The registry's `cwd` is the current directory; the transcript's first record's `cwd` is the origin.

## 6. Background sessions and the daemon

`claude --bg` starts a supervisor on demand [verified]:

```text
claude daemon run --origin transient --spawned-by {"label":"claude --bg",...}   (ppid 1)
 └─ claude bg-pty-host --bg-pty-host /tmp/cc-daemon-501/<hash>/spare/<id>.pty.sock 200 50 -- <claude binary> --bg-spare …
     └─ claude bg-spare --bg-spare …claim.sock        ← the session process (pre-warmed spare, then claimed)
```

The daemon keeps a pre-warmed spare worker ready, gives each session a PTY host (which is why `logs` is raw terminal output and why `attach` can reconnect a terminal), and **exits once it has no workers** (`--origin transient`).

`~/.claude/daemon/roster.json` lists `supervisorPid` and a `workers` map keyed by short ID with `pid`, `procStart`, `sessionId`, socket paths, `cliVersion`, `attempt`, `cwd`, and the full `dispatch` record (launch args, env, `isolation`, `respawnFlags`, and the `seed` intent and name). It also contains auth tokens, so treat it as secret.

`~/.claude/jobs/<short>/state.json` is the richest per-job status [verified]:

```json
{
  "state": "done",
  "detail": "sleep 25 completed; replied DONE",
  "tempo": "idle",
  "inFlight": { "tasks": 1, "queued": 0, "kinds": ["local_bash"] },
  "fan": [{ "id": "bfa39o9kk", "kind": "shell", "label": "sleep 25", "startedAt": 1790434098328 }],
  "tokens": 345,
  "output": { "result": "sleep 25 completed as requested" },
  "template": "bg",
  "intent": "Run the bash command 'sleep 25' …",
  "name": "bg-probe",
  "sessionId": "e64ffdc8-…",
  "resumeSessionId": "e64ffdc8-…",
  "backend": "daemon",
  "createdAt": "…", "updatedAt": "…", "firstTerminalAt": "…", "lastTerminalAt": "…"
}
```

`timeline.jsonl` records each state transition as `{at, state, detail, text}`. States seen: `working`, `done`, `blocked`, `stopped`.

**Caveat, observed live:** `state` is a model-authored self-report and can disagree with process reality. The job reported `done` while a backgrounded `sleep` was still running (registry `status: busy`, `inFlight.tasks: 1`). Thirty seconds later it flipped to `blocked` ("awaiting DONE reply") while the registry said `idle`. Treat `status` (process activity) and `state` / `detail` (declared progress) as two separate signals and show both.

## 7. Hooks: the push channel

Hooks are the only supported way to get events pushed rather than polled. They can be injected per invocation with `--settings '<json>'`, so a manager can instrument sessions it launches without touching the user's settings. A logging hook on every event produced these payloads [verified]:

| Event | Extra fields beyond `session_id`, `transcript_path`, `cwd`, `hook_event_name` |
| --- | --- |
| `SessionStart` | `source`: `startup` or `resume` (docs also list `clear`, `compact`). On resume: `seconds_since_last_response`, `context_tokens`, `prompt_cache_likely_expired`, `estimated_cache_write_usd` |
| `UserPromptSubmit` | `prompt`, `prompt_id`, `permission_mode` |
| `PreToolUse` | `tool_name`, `tool_input`, `tool_use_id`, `prompt_id`, `permission_mode` |
| `PostToolUse` | same plus `tool_response`, `duration_ms` |
| `Stop` | `last_assistant_message`, `stop_hook_active`, `background_tasks[]`, `session_crons[]` |
| `SessionEnd` | `reason` (`other` for a `-p` run that finished) |

`PreCompact`, `Notification`, and `SubagentStop` were registered but did not fire in these short runs. `Notification` should be the hook for "waiting on the user" (the registry's `waiting` status covers the same state by polling).

`transcript_path` in the payload is authoritative. It is the fastest way to map an event to its file without computing the encoded directory. `prompt_id` groups all events in one turn.

### 7.1 Injecting prompts into a running interactive session

The goal was a reliable way to push a prompt into a live interactive session other than typing into its terminal (`tmux send-keys`) and other than the peer-messaging socket (covered in `../agent-peering-tests/CLAUDE_CODE_PEERING.md`). Each candidate was tested against throwaway interactive sessions in a detached tmux session, or read from the 2.1.283 binary.

| Route | Result | Tag |
| --- | --- | --- |
| **`asyncRewake` hook inbox** | **Works** idle and busy, survives crashes, needs only `--settings` or user settings | [verified] |
| **MCP channels** (`notifications/claude/channel`) | **Works**, and is two-way (reply tool, permission relay). Needs an opt-in launch flag. See 7.2 | [verified] |
| Agent-teams lead mailbox (`teams/<team>/inboxes/team-lead.json`) | A poller exists ("Session idle, delivering pending message(s)"), but a fresh session never got team context (tried Haiku, the default model, a prompt, and a subagent spawn), and a hand-written inbox was ignored | [code], not reproduced |
| `TIOCSTI` into the pane's tty | `EACCES`: macOS only allows it on the caller's own controlling terminal | [verified] |
| Deep link `claude-cli://` | Launches a **new** session with `prefill`, `deepLinkRepo`, and `deepLinkCwdB64`. It cannot target a running session, and it prefills without submitting | [code] |
| IDE bridge (`at_mentioned`) | Inserts an @-mention into the input box; no submit path found | [code] |
| Remote Control (`--remote-control`) | Official way to drive a local session from claude.ai or mobile, but it goes through Anthropic's backend with no local API | [help-text] |
| `--input-format stream-json` | The clean programmatic input channel, but `-p` only, so not an interactive TUI | [help-text] |

#### The `asyncRewake` inbox

The hook schema documents `asyncRewake: true` as "runs in background and wakes the model on exit code 2 (blocking error). Implies async", along with two `@internal` fields: `rewakeMessage` (the prefix of the system reminder the model sees) and `rewakeSummary` (the one-line label shown in the terminal, defaulting to "Stop hook feedback"). Registering a blocking waiter on both `SessionStart` and `Stop` turns this into a durable, file-based inbox. `SessionStart` arms it for a fresh or resumed session before any prompt; `Stop` re-arms it after each turn. The waiter watches a directory, and when a file lands it claims the file atomically, prints it to stderr, and exits 2.

The version tested (`session_inbox.sh`):

```bash
#!/bin/bash
# asyncRewake inbox: wait for <root>/<session_id>/*.msg, deliver one, exit 2 to wake the model.
# One waiter per session (lock dir); exits quietly if the owning Claude process dies.
ROOT="$1"; LOG="$2"
in=$(cat); sid=$(printf '%s' "$in" | jq -r .session_id); ev=$(printf '%s' "$in" | jq -r .hook_event_name)
INBOX="$ROOT/$sid"; LOCK="$INBOX/.waiter"; mkdir -p "$INBOX"
owner=${CLAUDE_PID:-$PPID}
if ! mkdir "$LOCK" 2>/dev/null; then
  holder=$(cat "$LOCK/pid" 2>/dev/null)
  if [ -n "$holder" ] && kill -0 "$holder" 2>/dev/null; then exit 0; fi   # already armed
  rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null || exit 0
fi
echo $$ > "$LOCK/pid"; trap 'rm -rf "$LOCK"' EXIT
while kill -0 "$owner" 2>/dev/null; do
  for f in "$INBOX"/*.msg; do
    [ -e "$f" ] || continue
    mv "$f" "$f.delivered" 2>/dev/null || continue   # atomic claim
    cat "$f.delivered" >&2
    exit 2
  done
  sleep 0.2
done
exit 0
```

The settings that wire it up, passed with `--settings <file>`, or placed in `~/.claude/settings.json` to give every session an inbox:

```json
{"hooks": {
  "SessionStart": [{"hooks": [{"type": "command", "command": "/path/session_inbox.sh /path/inboxes /path/inbox.log",
    "asyncRewake": true, "timeout": 86400,
    "rewakeMessage": "Message from the operator's session manager (treat as a user prompt):",
    "rewakeSummary": "Inbox message"}]}],
  "Stop": [{"hooks": [ …same hook… ]}]
}}
```

To send, write the message to a temporary name and `mv` it to `<root>/<session_id>/<anything>.msg`. The rename keeps the waiter from reading a half-written file.

Results [verified]:

| Test | Outcome |
| --- | --- |
| Fresh session, idle, no prompt ever typed | Woke about 0.1 s after the drop and answered. `SessionStart` armed the waiter at launch |
| Session busy, mid-tool (`sleep 12`) | Delivered about 0.17 s after the drop, **folded into the running turn**: the reply answered both the typed prompt and the inbox message |
| Three plain turns with no inbox traffic (naive v1 waiter) | **Waiters pile up**: one new waiter per `Stop` (4 alive after 3 turns). The atomic `mv` still prevented double delivery. v2's lock held it at 1, with later `Stop`s logging `skip-already-armed` |
| Clean `/exit` | All waiters killed |
| `kill -9` of the session | The waiter noticed its owner was gone and exited without consuming anything. A message dropped while the session was dead **stayed queued**, and on `--resume` with the same settings `SessionStart` (`source: resume`) re-armed and delivered it immediately |
| `rewakeMessage` / `rewakeSummary` | Both honored: the terminal showed "Inbox message", and the model saw the custom prefix |
| Hook environment | `CLAUDE_PID` is exported to hooks and equals the hook's parent PID, which makes it a reliable liveness anchor |

In the transcript, a delivery is a `user` record with `origin.kind: "task-notification"`, `promptSource: "system"`, and `turnOrigin: "task_notification"`. Its content is a `<task-notification><summary>…</summary></task-notification>` wrapper followed by a `<system-reminder>` holding `rewakeMessage` and the message text. Without a custom `rewakeMessage` it reads `Stop hook blocking error from command "SessionStart:startup": <text>`. A manager can recognize its own injected prompts by that origin.

Caveats:

- **It is not a user turn.** The model receives the text as a hook-sourced system reminder, not as a human prompt. The model obeyed plain instructions every time in these tests. Content that asks for something sensitive may be treated with the suspicion owed to tool or hook output, which is by design. `rewakeMessage` controls the framing, but it is `@internal` and could change.
- **The hooks must be present at launch or resume.** A session started without them has no inbox, and hooks can't be added to a running session from outside. Putting them in user settings covers every session, but `--bare` and `--safe-mode` sessions skip them.
- **Busy delivery goes into the current turn, not after it.** A manager that wants strict turn-after-turn delivery should drop messages only when the registry says `idle`.
- **Without the lock and liveness check**, waiters accumulate per turn and, after a crash, an orphaned waiter could consume a message on behalf of a dead session.
- One waiter delivers one message and then exits, and the next `Stop` re-arms it. Several files queued at once are delivered one per turn, in glob order.

### 7.2 MCP channels

Channels are Claude Code's built-in, purpose-made route for pushing external events into a running interactive session. They are also the only route found that is **two-way**: a channel can receive the model's replies, and it can answer permission prompts. Everything below is [verified] against 2.1.283 in throwaway interactive sessions driven through tmux. Two servers were used. The first was `labchan.py`, a dependency-free Python stdio MCP server whose control plane is a spool directory, so pushes, raw frames, and permission answers can all be scripted from a shell. The second was the official `fakechat` plugin. Code-derived details are tagged [code].

#### Protocol

A channel is an ordinary MCP server, usually stdio and spawned by the session, that declares an experimental capability in its `initialize` result:

```json
{"capabilities": {"tools": {}, "experimental": {"claude/channel": {}, "claude/channel/permission": {}}}}
```

| Direction | Message | Params |
| --- | --- | --- |
| Server → Claude Code | `notifications/claude/channel` | `content` (string), `meta` (object of **string** values) |
| Claude Code → server | `notifications/claude/channel/permission_request` | `request_id` (5 lowercase letters, for example `tfemj`), `tool_name`, `description`, `input_preview` (JSON text of the tool input) |
| Server → Claude Code | `notifications/claude/channel/permission` | `request_id`, `behavior`: `allow` or `deny` |
| Claude Code → server | `tools/call` on the server's own tools (by convention `reply`) | Whatever the tool defines. This is how the model talks back |

The `claude/channel/permission` capability is optional. The official plugins' source comments say to declare it only if the server authenticates whoever sends the permission answer. `fakechat` doesn't declare it. The server's `instructions` string is where it tells the model how to use the channel (for example "reply with the reply tool").

#### Enabling it

A session only accepts channel pushes when it is **launched** with an opt-in flag naming the server. Both flags are hidden from `--help`.

| Launch | Result |
| --- | --- |
| No flag (server in `--mcp-config` only) | Server connects and pushes, and every push is **silently dropped** |
| `--channels server:<name>` | Refused: "server: entries need --dangerously-load-development-channels" / "not on the approved channels allowlist". Pushes dropped |
| `--channels plugin:<name>@<marketplace>` | Works for an **installed** plugin on the allowlist. The official `fakechat@claude-plugins-official` worked, installed at local scope. **No confirmation dialog**, just a banner: "Channels (experimental) messages from plugin:… inject directly in this session" |
| `--dangerously-load-development-channels server:<name>` | Works for any configured server, but shows a **blocking warning dialog on every launch, including `--resume`**, which someone has to confirm ("I am using this for local development") |

The flags take several values (space-separated, `<servers...>`), so a positional prompt placed after `--channels …` is swallowed as a channel name ("--channels entries must be tagged"). Put the prompt first. A banner reading "server:labchan · no MCP server configured with that name" appeared even though the `--mcp-config` server connected and worked, so the check apparently runs before dynamic MCP servers load.

Every reason for rejection found in the code [code]:

- the server did not declare `claude/channel`
- the negotiated MCP protocol revision has no path for unsolicited notifications
- the provider is Bedrock, Vertex, or Foundry
- the feature is disabled server-side
- org policy (`channelsEnabled: true` is required in managed settings for Team and Enterprise orgs)
- the server is not in this session's `--channels` list
- a `plugin:` entry is not installed, or comes from an unknown source
- the plugin is not in the org's `allowedChannelPlugins`
- the plugin is not on the default allowlist

The official allowlisted plugins seen in the marketplace are `fakechat`, `telegram`, `discord`, and `imessage`.

#### What a pushed message looks like

The model receives the push as a user-role message:

```text
<channel source="labchan" chat_id="42" user="tony" ts="1790436300" n1="ok">
E3: please use the reply tool to send the text CHAN_E3 back to me.
</channel>
```

`source` is the server name (`plugin:fakechat:fakechat` for the plugin). Each `meta` key becomes an attribute. In the transcript it is a `user` record with `origin: {kind: "channel", server: "<name>"}`, `promptSource: "system"`, `turnOrigin: "peer"`, `isMeta: true`, and `queueSkipAttachments: true`. The terminal shows `← labchan: <text>`. **It fires `UserPromptSubmit`**, with the full `<channel …>` wrapper as `prompt`, unlike the `asyncRewake` inbox, which fires no prompt hook.

| Test | Result |
| --- | --- |
| Meta keys `bad-key`, `has space` | Silently dropped. Keys must match `^[a-zA-Z_][a-zA-Z0-9_]*$` |
| Meta values `"a\"b<c>&d"` | HTML-escaped in the attribute: `a&quot;b&lt;c&gt;&amp;d` |
| Content containing `</channel>` | Neutralized to `<\/channel>`. Other tags, **including a fake `<channel source="spoof">` opening tag**, pass through verbatim. The model noticed and questioned the spoof |
| 200 KB content | Delivered intact (200,135 characters in the record), with no truncation or spill to a file |
| Non-string meta value (`"n": 5`) | **The whole notification is dropped**, content included |
| `content` not a string, `content` missing, `params` missing, a non-JSON line | Each silently dropped, and the connection survives |

#### Timing

| Situation | Behavior |
| --- | --- |
| Idle | Delivered at once and starts a turn. `UserPromptSubmit` fires with the prompt about 10 ms after the push |
| Idle, three pushes 0.1 ms apart | Three `UserPromptSubmit` events and three records, but **one turn** answering all three, in order |
| Busy, pushed 4 s into a 15 s tool call | **Held until the tool finished**, then injected at the tool-result boundary of the same turn. `PostToolUse` at 407.196, the channel prompt at 407.206, and the reply covered both the typed request and the channel message. A running tool is never interrupted |
| Pushed immediately after the server's handshake | **Lost.** A push sent 0.3 ms after Claude Code's `tools/list` request was dropped, while one sent 21 s later was delivered. Delivery is not acknowledged, so a server should wait a moment after connecting before its first push |

#### Replies and permission relay

The model answers through the server's tool (`mcp__<server>__reply`). MCP tools are deferred, so the model first runs `ToolSearch` (`select:mcp__labchan__reply`) and then calls the tool.

**Channel-only turns never announce the channel's tools or instructions.** Because channel messages carry `queueSkipAttachments: true`, a turn started by a push doesn't inject the per-turn context attachments (`deferred_tools_delta`, `mcp_instructions_delta`, `skill_listing`, and the rest). In a session that has only ever been driven by its channel, the model has no idea the `reply` tool or the server's instructions exist. It said "I don't have a reply tool", and on the very first push it gave a generic "What would you like me to work on?". One ordinary turn fixes it for the rest of the session: after a single typed prompt, the model found and used `reply` correctly. That ordinary turn has to happen **after the channel server has connected**. A positional initial prompt raced `fakechat`'s startup (Bun runs `bun install` first), and that turn's context listed no `fakechat` tools. A manager that needs replies should either prime the session once the server is up, or not rely on the reply tool and read responses from the transcript or the `Stop` hook's `last_assistant_message` instead.

**Permission relay works both ways.** When the model called `reply`, which needs approval by default, the terminal showed the usual dialog. At the same moment the channel received a `permission_request` with `request_id: "tfemj"`, `tool_name: "mcp__labchan__reply"`, the description, and `input_preview: "{ \"text\": \"CHAN_E4\" }"`. `PreToolUse`, `PermissionRequest`, and `Notification` hooks also fired.

- Answering `{request_id: "tfemj", behavior: "allow"}` over the channel **closed the terminal dialog and ran the tool**. The server received `CHAN_E4`.
- `behavior: "deny"` closed it with a rejected tool result ("The user doesn't want to proceed… the user said: Denie…"), and the model reported the denial.
- An unknown `request_id` (`zzzzz`) and a stale one (an already answered `tfemj`) were silently ignored, and the dialog stayed open.
- The terminal and the channel race: whichever answers first wins.

This makes a channel a remote approval surface as well as an input path, so the server must authenticate whoever is on the other end.

#### Lifecycle and failure modes

| Event | Behavior |
| --- | --- |
| Channel server killed (`kill -9`) | Shown as `✘ failed` in `/mcp`. **No automatic restart** within 48 s. Pushes while it's down go nowhere, and only a queue the server keeps itself survives |
| `/mcp` → labchan → Reconnect | Spawns a fresh server process. Channel delivery resumes (after the handshake race above) |
| Claude Code killed (`kill -9`) | The stdio server gets EOF on stdin and, if written to exit on EOF as `labchan` is, exits |
| `--resume` **without** the channel flag | The server reconnects as a plain MCP server, and pushes are silently dropped |
| `--resume` with the dev flag | Works, but the warning dialog appears again |
| `/clear` | The session keeps the same server process, and delivery continues into the new conversation. The server's `CLAUDE_CODE_SESSION_ID` env var is **stale** (still the pre-clear ID), while the registry's `sessionId` updated in place |
| `/exit` with `fakechat` | **Orphaned the plugin's server**: Claude Code ended the `bun run` wrapper, but the `bun server.ts` child (reparented to PID 1) kept port 8787 for more than 3.5 minutes until I killed it |
| Two sessions with `fakechat` | The second session's server died silently (fixed port 8787 already in use), with no error in the UI. The first session owned the port |

The MCP server process receives `CLAUDE_CODE_SESSION_ID`, `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA` (plugins), `CLAUDECODE`, `AI_AGENT`, and also `CLAUDE_CODE_MESSAGING_SOCKET` and `CLAUDE_CODE_MESSAGING_TOKEN`: the session's peer-messaging credentials are visible to every MCP server it spawns. `CLAUDE_PID` is not set, but the server's parent PID is the Claude process when it is spawned directly.

#### Channels compared with the `asyncRewake` inbox (7.1)

| | MCP channel | `asyncRewake` inbox |
| --- | --- | --- |
| How the model sees it | `<channel source=…>` user-role message, `origin.kind: "channel"` | Hook "blocking error" system reminder, `origin.kind: "task-notification"` |
| `UserPromptSubmit` hook | Fires | Does not fire |
| Busy delivery | At the next tool-result boundary, in the same turn | At the next boundary, in the same turn |
| Burst | Batched into one turn | One message per wake |
| Durability | None built in; the server must queue. Early pushes after connect can be lost | Files wait on disk across crashes and resumes |
| Two-way | Yes: `reply` tool and permission relay | No (read the transcript or the `Stop` hook) |
| Launch requirement | `--channels plugin:…` (installed, allowlisted) or the dev flag (dialog on every launch) | Hooks in `--settings` or user settings |
| Org gating | `channelsEnabled` / `allowedChannelPlugins` for Team and Enterprise; unavailable on third-party providers | None |
| Stability | Experimental, but a designed, documented-in-code feature | Relies on `@internal` hook fields |

For a manager-owned channel, the design these results point to is:

- A small stdio server keyed by its parent Claude PID, not by `CLAUDE_CODE_SESSION_ID`, which goes stale on `/clear`.
- A per-session endpoint (a socket or spool directory under the manager's own directory, never a fixed TCP port).
- A persistent queue, a short delay after the handshake before the first push, and exit on stdin EOF.
- Optionally, the permission capability, which gives remote approvals.
- Packaged as a plugin, so `--channels plugin:…` avoids the dev dialog. For personal Max and Pro accounts that still requires the plugin to be on Anthropic's default allowlist; an org can extend it with `allowedChannelPlugins`. Otherwise the dev flag and its dialog remain, and the dialog is easy to confirm through tmux.

## 8. Headless and SDK output

`claude -p --output-format json` returns one `result` object with `session_id`, `total_cost_usd`, `usage` (including cache-creation TTL breakdown), `modelUsage` per model, `num_turns`, `duration_ms`, `duration_api_ms`, `ttft_ms`, `permission_denials`, `terminal_reason`, `subagent_stats` (spawned, completed, failed, killed, refused by reason), and `is_error` / `subtype`. [verified]

`--output-format stream-json --verbose` emits `system/init` first (with `session_id`, `cwd`, `model`, `tools`, `mcp_servers`, `agents`, `skills`, `plugins`, `permissionMode`, `claude_code_version`, `memory_paths`, `messaging_socket_path`), then `assistant` / `user` messages, `rate_limit_event`, and the final `result`. [verified] For sessions a manager launches itself, this is the cleanest way to get structured events without reading the transcript.

## 9. Subagents, teams, and peers

**Subagents** (the Agent tool) get their own sidechain transcripts at `projects/<dir>/<parent-session-id>/subagents/agent-<agentId>.jsonl`. Records have `isSidechain: true`, `agentId`, and the **parent's** `sessionId`. The sibling `.meta.json` holds `agentType`, `description`, `toolUseId` (the parent's Agent tool call), `spawnDepth`, `requestShape` (`background` / foreground), and `requestNonInteractive`. [observed] The subagent's final report returns to the parent as a `user` record with `origin.kind: "peer"` and `origin.from: <agentId>`. So parent-to-child linking works both ways: `toolUseId` in the meta, and `origin.from` in the parent.

**Agent teams** (experimental, enabled here) write `teams/session-<id8>/config.json` (`leadSessionId`, `members[]` with `agentId`, `agentType`, `backendType: in-process`, `tmuxPaneId`, `cwd`) and `inboxes/<member>.json` message queues. [verified]

**Peer messaging**: every live session exposes a Unix socket (`messagingSocketPath`) authenticated with the `<pid>.<hash>.key` file, advertises `peerProtocol: 1` and `peerFeatures`, and can be listed and messaged from any other session via the `ListAgents` / `SendMessage` tools. `ListAgents` shows name, a 6-hex peer handle (not the session-ID prefix), kind, status, tmux pane, and age. [verified] A manager could in principle join this mesh, but the protocol is undocumented; the registry file gives the same inventory without speaking it.

## 10. Other persistent state

- **`history.jsonl`**: one line per **interactive** prompt (`display`, `pastedContents`, `timestamp`, `project`, `sessionId`); 4,690 lines here. `-p` prompts are not recorded [verified]. Useful for a global "recent prompts" search without opening transcripts.
- **`file-history/<session-id>/`**: pre-edit snapshots named `<content-hash>@v<n>`, referenced by `file-history-*` transcript records; powers `/rewind` checkpoints.
- **`shell-snapshots/`**: zsh environment captures (`snapshot-zsh-<epoch-ms>-<rand>.sh`) used to start Bash tool shells; not session-keyed by name.
- **Environment inside a session**: `CLAUDECODE=1`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_PID`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_MESSAGING_SOCKET`, `CLAUDE_EFFORT`, `AI_AGENT=claude-code_<ver>_agent` [verified]. Any process started from a session (hooks, scripts, a `ccstatusline`-style status line) can identify its session this way.

## 11. Retention and deletion

- `cleanupPeriodDays` in `settings.json` (7 here) controls pruning; `.last-cleanup` records the last sweep (it ran at startup of a session that day). Only about 15 main transcripts survived across 30 project dirs, which fits a 7-day window keyed on file modification time, since a session started 8 days ago but still active survived. Exact criteria not verified.
- `claude rm` removes background job records only. `claude project purge [path]` is the bulk deletion path per project [help-text].
- Orphans accumulate: `tasks/`, `teams/`, `session-env/` directories remained after `rm`, and empty project dirs are created by cross-directory resumes.

## 12. Recommendations for the cross-harness manager

1. **Inventory**: poll `claude agents --json` (supported and cheap), or read `~/.claude/sessions/*.json` directly for the richer fields (`waitingFor`, `tmux`, `entrypoint`, `version`). Validate each with `kill -0` plus `procStart`.
2. **History index**: walk `~/.claude/projects/*/*.jsonl`; key by the filename UUID; take `cwd` from the first record, title from the last `custom-title` or else the last `ai-title`, cost from the last `cost-state` (interactive sessions only write it on exit, so for live or crashed sessions sum `usage` by `requestId` instead), and timestamps from first and last `timestamp`. Tail files incrementally (they are append-only) instead of re-reading.
3. **Archive before retention deletes**: copy transcripts out, or raise `cleanupPeriodDays`, if long-term observability matters.
4. **Events**: for sessions the manager launches, pass `--settings` with hooks that forward JSON to the manager, or use `-p --output-format stream-json`. For sessions it didn't launch, a user-level hook in `~/.claude/settings.json` is the only push option; otherwise use filesystem watch on `sessions/` and `projects/`.
5. **"Needs attention"**: registry `status == "waiting"` plus `waitingFor`, or the `Notification` hook.
6. **Control surface**: resume with `claude --resume <id>` (works from any directory), fork with `--fork-session`, pre-assign IDs with `--session-id` so the manager knows the ID before the process starts, and use `--bg` / `attach` / `stop` / `rm` / `respawn` for detached runs. For interactive sessions in tmux, the registry's `tmux` pane ID is the handle for focus and capture.
7. **Normalize**: the common model across harnesses is roughly {id, parent id (fork or subagent), origin cwd, current cwd, title, status, started / updated, cost, transcript path}. Claude Code fills all of these, but parent-of-fork has to be inferred from shared UUIDs, and status comes only from the live registry.

## 13. Gaps and open questions

- Which process sweeps stale `sessions/*.json` after a crash, and on what trigger. They do get removed (4.5), but the sweeper was not isolated. Stale sockets were never removed.
- Flush timing for subagent transcripts, compaction, and `/clear` was not measured. 4.5 covers the main transcript only.
- What makes a session get agent-team context, which would let its lead mailbox poller deliver file-written messages.
- Channels (7.2): not measured whether a server pushing while the session awaits a *permission* prompt is held or delivered, how channels behave in `-p --input-format stream-json` sessions, or whether the post-connect race has a fixed window. Org-policy gates (`channelsEnabled`, `allowedChannelPlugins`) were read from code only.
- `claude attach`, `respawn`, cloud, teleport, and remote-control sessions were not exercised; cloud sessions presumably have no local transcript until teleported.
- `PreCompact`, `Notification`, `SubagentStop`, `SubagentStart`, and `SessionStart` with `source: compact|clear` payloads were not captured.
- The retention algorithm (mtime compared with creation time, and whether subagent files are pruned with the parent) is inferred, not confirmed.
- Every format here is internal and has shifted between minor versions (for example, some records carry both `sessionId` and `session_id`). Pin parsers to tolerant field access and log unknown `type`s rather than failing.

## Appendix: artifacts created by this investigation

- Scratch sessions under `~/.claude/projects/-private-tmp-claude-501-…-scratchpad-exp/` (IDs `11111111-2222-4333-8444-555555555555`, `72740f30-…` (fork), `0bce92ce-…`, `753e3e76-…`, `0737d9fb-…`, `8dcd80be-…`) and an empty `…-scratchpad-other/` dir.
- Background probe session `e64ffdc8-6bfc-499f-83e5-dd5f7f213cb7` ("bg-probe"): its job record was removed with `claude rm`, but its transcript remains in this project's directory along with `tasks/session-e64ffdc8`, `teams/session-e64ffdc8`, and `session-env/e64ffdc8-…`.
- Flush-timing session `55c3c5b6-4910-40b5-b039-e04f14bfc937` ("flush-lab") under `~/.claude/projects/-private-tmp-claude-501-…-scratchpad-flush/`. Its tmux session `cc-flush-lab` was closed. Stale sockets `/tmp/cc-socks/13740.sock` and `/tmp/cc-socks/67872.sock` from its two `kill -9` runs were left in place as evidence.
- Injection-test sessions `inject-lab`, `inject-lab-2` (`586b6bdf-…`), and `team-lab` (`4097da8f-…`), all in the same `…-scratchpad-flush/` project dir. Their tmux session `cc-inject-lab` was closed and no inbox waiters remain. The hand-made `teams/session-586b6bdf/` directory was removed.
- Channel-test sessions `chan-e0`, `chan-lab` (`e0bdc8b2-…`), `chan-e12`, `chan-fakechat` (`503dd907-…`), `chan-fakechat-2` (`250082d7-…`, then `88e973c7-…` after `/clear`), and `chan-fakechat-3`, all in the same `…-scratchpad-flush/` project dir. Their tmux session `cc-chan-lab` was closed. `fakechat` was installed at **local scope** in the scratch directory and uninstalled afterwards, leaving `enabledPlugins: {}` in that directory's `.claude/settings.local.json`. One orphaned `fakechat` server was killed by hand.
