# Antigravity Agent Session Streaming Approaches

This document outlines methods for streaming live output of an Antigravity (Gemini) agent session to a web UI or TUI. Given that Antigravity isolates conversation state in a dedicated "brain" directory, there are robust mechanisms for capturing session lifecycles, both actively and passively.

## 1. Active UI Integration: NDJSON Streaming (`--output-format stream-json`)
The most effective way to build a web UI or TUI that directly drives an agent session is to invoke `agy` headlessly for each user turn using the `--continue` and `--print` flags, coupled with `--output-format stream-json`.

### How it Works
When the user submits a message in the UI, the backend spawns:
```bash
agy --continue --print "User's message here" \
    --output-format stream-json \
    --dangerously-skip-permissions
```
- **State Persistence**: Because Antigravity persists state to `~/.gemini/antigravity-cli/brain/`, the `--continue` flag perfectly resumes the context without needing to hold a long-running process open.
- **NDJSON Stream**: The command outputs a line-delimited JSON (NDJSON) stream to `stdout`, which your UI backend can easily parse and stream via Server-Sent Events (SSE) or WebSockets.

### Event Lifecycle
The NDJSON stream emits distinct lifecycle events:
1. `{"event": "init", "init": {...}}`: Provides conversation ID and available tools.
2. `{"event": "step_update", "step_update": {"state": "ACTIVE", "step_type": "tool", "tool_name": "...", "tool_info": {...}}}`: Emitted when the agent invokes a tool.
3. `{"event": "step_update", "step_update": {"state": "DONE", "step_type": "tool", "output": "..."}}`: Emitted when the tool finishes execution.
4. `{"event": "step_update", "step_update": {"state": "ACTIVE", "step_type": "agent_response", "text_delta": "..."}}`: Emitted token-by-token during the agent's textual response, ideal for live typing effects in the UI.
5. `{"event": "result", "result": {"status": "SUCCESS", "response": "..."}}`: Emitted at the end of the turn with token usage metrics.

## 2. Passive Observability: Tailing the Transcript
If the goal is to passively monitor an agent session that is running in another terminal (e.g., in a tmux pane or native CLI), you can tail the session's transcript.

### How it Works
Every conversation has a unique ID, and its state is written strictly to:
`~/.gemini/antigravity-cli/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`

A session manager tool can observe this directory and `tail -f` the active transcript:
- **Step-by-Step Logging**: The `transcript.jsonl` file logs every turn, internal model reasoning (`thinking`), tool calls, and execution results as complete JSON objects.
- **Limitation**: This method only updates when a step reaches the `DONE` state. It does not provide real-time token streaming (`text_delta`), making it better suited for an observability dashboard rather than an interactive chat UI.

## 3. Remote Control Daemon
Antigravity supports a built-in background daemon for remote connectivity:
```bash
agy remote-control start
```
While this enables external tools to attach to a session programmatically, the protocol relies on internal API endpoints. For most external UIs and TUIs, the `--output-format stream-json` method over standard `stdio` is far more accessible and robust.

---
**Summary for Implementers:**
- Use **Method 1** if your UI acts as the primary interface (User -> UI -> `agy`).
- Use **Method 2** if your UI is a read-only observability dashboard watching agents work elsewhere.
