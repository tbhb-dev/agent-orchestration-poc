# Host harness lifecycle cells

## Prelaunch boundary

**Untested.** These commands are a review artifact for the later Claude executor. This Codex run did not launch a harness. Use only the four approved `/private/tmp/bv01-228-*` homes, the dedicated `/private/tmp/bv01-228-probe.tmux` socket, and the already reviewed [stage-two setup](../02-host-socket-attribution/stage-two-runbook.md). The operator runs the separate `opensnoop` command. Stop a cell if its effective settings, API request, or process tree differ from the reviewed values.

**Help-text.** Codex CLI 0.157.1 advertises `codex resume SESSION_ID` and `codex exec resume SESSION_ID`. Claude Code 2.1.284 advertises `--resume SESSION_ID`, `--print`, and `--output-format json`. Pin the versions again at execution. Claude 2.1.284 differs from the 2.1.283 stage-two pin, so the first harness cell needs an operator review of that version drift.

## Files and response bytes

Copy the exact committed [launcher](fixture/launch.py), [pure launch values](fixture/launch_core.py), [record writer](fixture/record.py), [observer](fixture/observe.py), and [pure decisions](fixture/lifecycle_core.py) into each home as the `fixture/` package. The launcher uses the literal profile, phase, and A/B slot arguments. It writes `root.pid` or `root-B.pid` and waits for `go` or `go-B` before replacing its process with the harness. A's state is `codex/` or `claude/` below its home. B's state is `B/codex/` or `B/claude/` in the same home. `workspace/` is shared by both slots. The initial and B invocations use the existing responder at `../02-host-socket-attribution/model_responder.py`. A resume uses [the adapter](fixture/resume_responder.py), which loads that same responder with the committed [resume frame set](fixture/resume_frames/).

```sh
for profile in codex-interactive codex-headless claude-interactive claude-headless; do
    home="/private/tmp/bv01-228-$profile"
    test -d "$home/workspace" && test -d "$home/tmp" && test -d "$home/xdg" || exit 1
    cp -R experiments/06-host-runtime-lifecycle/fixture "$home/fixture"
    mkdir -m 700 "$home/B" "$home/B/tmp" "$home/B/xdg"
    case "$profile" in
        codex-*) mkdir -m 700 "$home/B/codex"; cp "$home/codex/config.toml" "$home/B/codex/config.toml"; printf 'B-state-marker\n' > "$home/B/codex/private-marker" ;;
        claude-*) mkdir -m 700 "$home/B/claude"; printf 'B-state-marker\n' > "$home/B/claude/private-marker" ;;
    esac
done
```

**Protocol bytes.** The responder accepts only `POST /v1/responses` for Codex or `POST /v1/messages` for Claude, `Host: 127.0.0.1:<recorded-port>`, decimal `Content-Length` at most 2000000, and no transfer encoding. It sends exact committed `*-tool.sse` and `*-final.sse` byte streams with `Content-Type: text/event-stream`, then rejects a third request with HTTP 409. Initial and B invocations read [the merged response frames](../02-host-socket-attribution/fixtures/responder/). A resume reads [the resume frames](fixture/resume_frames/), which direct the tool to test B's harmless private marker for readability. Record `sha256sum` and `od -An -tx1` for both frame pairs before launch so review covers the exact bytes. Classify a third model request as unsupported and stop the cell before contacting any provider.

```sh
for profile in codex-interactive codex-headless claude-interactive claude-headless; do
    for source in experiments/02-host-socket-attribution/fixtures/responder experiments/06-host-runtime-lifecycle/fixture/resume_frames; do
        sha256sum "$source/$profile-tool.sse" "$source/$profile-final.sse"
        od -An -tx1 "$source/$profile-tool.sse" "$source/$profile-final.sse" > "/private/tmp/bv01-228-$profile/$(basename "$source")-bytes.hex"
    done
done
```

## Per-cell command sequence

Run one profile at a time in this order: `codex-headless`, `claude-headless`, `codex-interactive`, `claude-interactive`. For each profile, use the exact `profile` assignment below, then run the commands for A initial, B initial, and A resume. Record every command's exit status. Stop if a command fails. The stage-two runbook supplies the already reviewed base configuration and one-request Unix listener behavior. Start a fresh responder for each invocation with its own log. Stop and wait for the prior responder and listener before starting the next invocation.

```sh
profile=codex-headless
profile=claude-headless
profile=codex-interactive
profile=claude-interactive
```

Run each assignment above separately in the stated order. Before each A initial, B initial, and A resume launch, set `cell` to the corresponding literal `A-initial`, `B-initial`, or `A-resume` and run the block below. Its Codex TOML is the exact local provider file for that invocation. Its second copy gives B the same fake responder route with a separate state directory. Claude's two `settings.json` files keep the exact contents from the stage-two runbook. The headless `--ephemeral` and `--no-session-persistence` flags from stage two are absent because native resume requires retained state.

```sh
home="/private/tmp/bv01-228-$profile"
: "${cell:?set the literal cell label before starting the responder}"
case "$cell" in
    A-resume) responder=experiments/06-host-runtime-lifecycle/fixture/resume_responder.py ;;
    A-initial|B-initial) responder=experiments/02-host-socket-attribution/model_responder.py ;;
    *) exit 1 ;;
esac
PYTHONSAFEPATH=1 mise exec -- uv run python "$responder" --host 127.0.0.1 --port 0 --profile "$profile" --log "$home/$cell-model.jsonl" > "$home/$cell-model-start.json" 2> "$home/$cell-model.err" &
model_supervisor_pid=$!
while test ! -s "$home/$cell-model-start.json"; do sleep 0.05; done
model_pid=$(mise exec -- python -c 'import json,sys; print(json.load(open(sys.argv[1]))["pid"])' "$home/$cell-model-start.json")
port=$(mise exec -- python -c 'import json,sys; print(json.load(open(sys.argv[1]))["port"])' "$home/$cell-model-start.json")
printf '%s\n' "$port" > "$home/model-port"
if test "${profile#codex-}" != "$profile"; then
    cat > "$home/codex/config.toml" <<EOF
model_provider = "bv01"
default_permissions = "bv01"
[model_providers.bv01]
base_url = "http://127.0.0.1:$port/v1"
wire_api = "responses"
env_key = "BV01_FAKE_OPENAI_KEY"
[permissions.bv01.network]
enabled = true
[permissions.bv01.network.unix_sockets]
"$home/gateway.sock" = "allow"
EOF
    cp "$home/codex/config.toml" "$home/B/codex/config.toml"
fi
lsof -nP -a -p "$model_pid" -iTCP
```

Set `cell` separately in each invocation block below, then run the responder block above. The generated TOML contains the recorded loopback port and socket path, and no provider URL outside loopback. The profile's `settings.json` remains byte-identical to the stage-two file. Record the hash and sanitized contents of the effective file before releasing `go` or `go-B`.

```sh
home="/private/tmp/bv01-228-$profile"
cell=A-initial
rm -f -- "$home/go" "$home/root.pid"
case "$profile" in
    *-headless) PYTHONPATH="$home" PYTHONSAFEPATH=1 mise exec -- uv run python -m fixture.launch "$profile" initial A > "$home/A-initial.out" 2> "$home/A-initial.err" & launch_job_pid=$! ;;
    *-interactive) tmux -S /private/tmp/bv01-228-probe.tmux new-window -t bv01 -n "lifecycle-$profile" "cd $home && python3 -m fixture.launch $profile initial A" ;;
esac
while test ! -s "$home/root.pid"; do sleep 0.05; done
root_pid=$(cat "$home/root.pid")
PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/probe.py server "$home/gateway.sock" "$root_pid" 1 > "$home/A-listener.jsonl" 2> "$home/A-listener.err" &
listener_pid=$!
while test ! -S "$home/gateway.sock"; do sleep 0.05; done
PYTHONPATH="$home" PYTHONSAFEPATH=1 mise exec -- uv run python -m fixture.record "$profile" A A-1 pending
PYTHONPATH="$home" PYTHONSAFEPATH=1 mise exec -- uv run python -m fixture.observe "$home" > "$home/A-before.json"
: > "$home/go"
```

For A initial headless cells, collect the launched job's status in the same shell before reading its conversation ID:

```sh
if test "${profile#*-headless}" = ""; then
    if wait "$launch_job_pid"; then launch_status=0; else launch_status=$?; fi
    printf 'A initial exit: %s\n' "$launch_status"
fi
```

For interactive profiles, attach only through `tmux -S /private/tmp/bv01-228-probe.tmux attach-session -t bv01:lifecycle-$profile`, enter the literal socket-client prompt in the committed tool frame, and detach with `Ctrl-b d`. Confirm `tmux -S /private/tmp/bv01-228-probe.tmux has-session -t bv01:lifecycle-$profile` exits 0. Attach a second time with the same command. Exit the TUI through its own exit command, then check the recorded root process. A tmux reconnect only tests the live terminal, not native conversation resume or controller recovery.

For headless profiles, use `if wait "$launch_job_pid"; then launch_status=0; else launch_status=$?; fi` in the same initiating shell after releasing `go`, and record `launch_status` before inspecting the sanitized JSON output. `launch_job_pid` is the shell's child job (`mise exec -- uv run`). `root_pid` is the Python launcher PID later replaced by the harness and is the process identity for the listener and observer. Waiting on `root_pid` from the initiating shell cannot collect its exit status. Codex JSONL should contain a `thread.started` ID. Claude JSON output should contain a `session_id`. For interactive profiles, transcribe the native ID shown by the harness session status or its private session record. Verify that the ID belongs to this home and invocation. The ID is a runtime value and cannot be hardcoded in the reviewed command. Enter only that value at the prompt below. A missing ID classifies native resume as unsupported for that cell.

```sh
printf 'Native conversation ID for %s: ' "$profile"
IFS= read -r conversation_id
test -n "$conversation_id" || exit 1
printf '%s\n' "$conversation_id" > "$home/conversation-id"
PYTHONPATH="$home" PYTHONSAFEPATH=1 mise exec -- uv run python -m fixture.record "$profile" A A-1 "$conversation_id" --update-conversation
PYTHONPATH="$home" PYTHONSAFEPATH=1 mise exec -- uv run python -m fixture.observe "$home" --baseline "$home/A-before.json" > "$home/A-after.json"
```

Start a fresh controller observer by launching `fixture.observe` as a new Python process after the initiating shell or tmux client has exited. Compare `pid`, `process`, `conversation_id`, `incarnation`, and `private_state` in `A-before.json` and `A-after.json`. The observer reads `ps` start time to reject PID reuse. If `ps` is denied, record the denial and leave process reconciliation inconclusive. Do not infer authority from liveness. The observer's state fingerprints are evidence, while private file contents remain in the home.

For B initial, restart the responder and listener using the stage-two commands, with `root-B.pid` as listener root. `B/codex/config.toml` is the copied local provider config. Claude B uses the same explicit `settings.json` but a distinct `CLAUDE_CONFIG_DIR`. The B invocation is:

```sh
cell=B-initial
rm -f -- "$home/go-B" "$home/root-B.pid"
case "$profile" in
    *-headless) PYTHONPATH="$home" PYTHONSAFEPATH=1 mise exec -- uv run python -m fixture.launch "$profile" initial B > "$home/B-initial.out" 2> "$home/B-initial.err" & launch_job_pid=$! ;;
    *-interactive) tmux -S /private/tmp/bv01-228-probe.tmux new-window -t bv01 -n "lifecycle-B-$profile" "cd $home && python3 -m fixture.launch $profile initial B" ;;
esac
while test ! -s "$home/root-B.pid"; do sleep 0.05; done
root_pid=$(cat "$home/root-B.pid")
PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/probe.py server "$home/gateway.sock" "$root_pid" 1 > "$home/B-listener.jsonl" 2> "$home/B-listener.err" &
listener_pid=$!
while test ! -S "$home/gateway.sock"; do sleep 0.05; done
: > "$home/go-B"
if test "${profile#*-headless}" = ""; then
    if wait "$launch_job_pid"; then launch_status=0; else launch_status=$?; fi
    printf 'B launch exit: %s\n' "$launch_status"
fi
```

After B exits, record file count and SHA-256 fingerprints for B's harness state with `PYTHONSAFEPATH=1 mise exec -- uv run python -c 'import hashlib,pathlib,sys; root=pathlib.Path(sys.argv[1]); files=[p for p in root.rglob("*") if p.is_file() and not p.is_symlink()]; print(len(files)); print(hashlib.sha256(b"".join(sorted(hashlib.sha256(p.read_bytes()).digest() for p in files))).hexdigest())' "$home/B/codex"` for Codex or replace the final path with `"$home/B/claude"` for Claude. Run the A-environment shell check below and record its exit code as a host same-UID access result.

The A-environment shell result is preliminary. The A-resume tool frame below makes the live harness attempt the same B marker check, and its tool result qualifies or rejects that profile's harness-mediated access case.

Use a harmless shared file to compare the two disposable slots without treating `workspace/` as a private-state boundary. Run this block after A initial and before B initial, then read the same file after B initial and after A resume. This is a host filesystem check until a live harness tool writes the file.

```sh
printf 'A-shared-fixture\n' > "$home/workspace/lifecycle-shared.txt"
sha256sum "$home/workspace/lifecycle-shared.txt"
test "$(cat "$home/workspace/lifecycle-shared.txt")" = A-shared-fixture
```

```sh
case "$profile" in
    codex-*) marker="$home/B/codex/private-marker" ;;
    claude-*) marker="$home/B/claude/private-marker" ;;
esac
env -i HOME="$home" PATH=/usr/bin:/bin /bin/sh -c 'test -r "$1"' _ "$marker"
```

For A native resume, stop the initial A process, archive its output and state snapshot, restart the responder with the resume frames, then launch with `resume A` and a new incarnation record. The resume command reads the explicit `conversation-id` from A's home. It does not attach to tmux or use an exec operation as a substitute for native resume. The resume tool frame checks B's harmless private marker. Its tool result records harness-mediated A-to-B access or denial.

```sh
cell=A-resume
rm -f -- "$home/go" "$home/root.pid"
case "$profile" in
    *-headless) PYTHONPATH="$home" PYTHONSAFEPATH=1 mise exec -- uv run python -m fixture.launch "$profile" resume A > "$home/A-resume.out" 2> "$home/A-resume.err" & launch_job_pid=$! ;;
    *-interactive) tmux -S /private/tmp/bv01-228-probe.tmux new-window -t bv01 -n "resume-$profile" "cd $home && python3 -m fixture.launch $profile resume A" ;;
esac
while test ! -s "$home/root.pid"; do sleep 0.05; done
root_pid=$(cat "$home/root.pid")
PYTHONPATH="$home" PYTHONSAFEPATH=1 mise exec -- uv run python -m fixture.record "$profile" A A-2 "$conversation_id"
: > "$home/go"
PYTHONPATH="$home" PYTHONSAFEPATH=1 mise exec -- uv run python -m fixture.observe "$home" --baseline "$home/A-after.json" > "$home/A-resume-observer.json"
if test "${profile#*-headless}" = ""; then
    if wait "$launch_job_pid"; then launch_status=0; else launch_status=$?; fi
    printf 'A resume exit: %s\n' "$launch_status"
fi
```

Compare the A-1 and A-2 records. Require a new `pid` or process start time and the same native conversation ID, while allowing a new tmux window. A native CLI that rejects the fake responder or state is an unsupported or inconclusive cell with its exact error recorded. Do not fall back to a live provider.

## Command ledger and undo

| State-changing command | Owned state and undo |
| --- | --- |
| The `cp`, `mkdir`, and `printf` setup block | Writes below the four approved `/private/tmp/bv01-228-*` homes. Inspect copied files and fingerprints, then remove these paths with guarded home cleanup. |
| Per-cell responder startup from stage two | One `127.0.0.1` listener per invocation. `model_pid` from startup JSON owns the socket. `model_supervisor_pid=$!` is the child job to wait on. Signal the responder, wait for the supervisor, and check socket closure before reuse. Keep only redacted request counts. |
| Per-cell Unix listener startup from stage two | One `gateway.sock` per home. `listener_pid=$!` is the child job to wait on. Check socket closure after its responder exits. |
| `python -m fixture.launch` and dedicated-socket `tmux new-window` | `root_pid` identifies the Python launcher and later harness. For headless cells, `launch_job_pid=$!` is the child job that supplies exit status through `wait`. Interactive cells use the dedicated tmux window and its exit observation. Cancel only the recorded root/window and stop the dedicated tmux server after all cells. |
| `record.py`, `printf > conversation-id`, `: > go`, and redirected observer/output commands | Mapping, barrier, state fingerprints, and raw output stay below `/private/tmp/bv01-228-$profile`. Redact before copying evidence, then guarded home cleanup removes the originals. |
| `printf > "$home/workspace/lifecycle-shared.txt"` | Writes a harmless shared fixture file in that profile's workspace. Keep it through B and resume checks, then guarded home cleanup removes it. |
| `rm -f -- "$home/go" "$home/root.pid"` or the B equivalent | Removes only the prior barrier and root PID record in that same home. The next launch writes a new record, and final home teardown removes it. |
| Repeated cancellation, collision, and interrupted create from the existing deterministic [probe](probe.py) | `probe.py` creates and removes its unique `/private/tmp/bv08-243-*` directory. The live harness sequence must record unsupported behavior if the wrapper lacks that operation. |

**Cleanup.** Confirm every recorded root, listener, and responder PID has exited and wait on each child supervisor or launch job from its initiating shell. Inspect `lsof -nP -U`, each dedicated tmux window, and the four homes. Stop only the dedicated tmux server. Apply the exact guarded teardown in the stage-two runbook after the operator has stopped the root audit and reviewed its raw trace. Shared workspace sentinels remain until that final home teardown. No command deletes unrelated workspace data.
