# Codex interactive-stream probes

Results: [../codex.md](../codex.md). These are bounded experiment scripts, not a production session manager.

## Setup

From the repository root:

```sh
python3 -m venv codex/.venv
codex/.venv/bin/pip install -r codex/requirements.txt
```

The scripts target the installed Codex 0.157.1 daemon and default control socket. They require host permission to access that socket/tmux. They do not start a daemon or submit an agent turn.

## Observe a normal interactive TUI

Start plain `codex` in a terminal/tmux pane. Finish trust/login setup and submit a harmless first prompt through that TUI. Then discover loaded threads matching its working directory:

```sh
codex/.venv/bin/python codex/observe.py \
  --cwd /absolute/path/to/workspace --output /tmp/codex-discovery.jsonl
```

Select its exact thread ID from the `candidate` record, then:

```sh
codex/.venv/bin/python codex/observe.py \
  --thread THREAD_ID --mode resume --exclude-turns \
  --seconds 60 --output /tmp/codex-live.jsonl
```

Wait for `READY`, then submit a second prompt through the original TUI. `--mode read --exclude-turns` is the metadata-only comparison. Omit `--exclude-turns` to request history too. `--via-proxy` uses a WebSocket handshake through `codex app-server proxy` instead of connecting directly to its Unix socket.

The observer checks that the thread is already loaded, sends no turn/input/configuration overrides, and closes its own connection when the timer expires. It is not a server-enforced read-only client. It does not answer approval requests, implement reconnect/replay, or provide a safe remote-viewer API. Use controlled sessions for testing. Captures contain the selected thread's content.

## Terminal and rollout timing

```sh
python3 codex/capture_control.py --session YOUR_TEST_TMUX_SESSION \
  --seconds 60 --output /tmp/codex-terminal.jsonl
python3 codex/watch_rollout.py /absolute/path/to/rollout.jsonl \
  --seconds 60 --output /tmp/codex-rollout-timing.jsonl
```

The first creates a read-only, size-ignored tmux control client and detaches it on timeout. Its output is tmux control framing, not decoded screen text. The second starts at EOF and records new completed JSONL records' types, sizes, timestamps and test markers; it does not copy arbitrary transcript content or handle file rotation.

The retained prompts are `evidence/prompt-{alpha,beta,gamma,standalone}.json`. Alpha/beta print stdout immediately; gamma delays its first line. Timed commands execute only harmless printing and sleeps. The installed model remained GPT-6-Astra.

## Check retained evidence

```sh
python3 codex/analyze.py
python3 -m py_compile codex/observe.py codex/watch_rollout.py \
  codex/capture_control.py codex/analyze.py
```

`analyze.py` rebuilds `evidence/analysis.json` from the recorded experiment. Some observers deliberately covered only part of the multi-turn run, so their counts need not match.

The initial failed attachment captures are `resume-live.jsonl` and `read-live.jsonl`. `resume-attached.jsonl` is the successful run; the initial probe's unchecked readiness bug was fixed. Schemas were generated with `codex app-server generate-json-schema --out codex/schema`; only the three relevant top-level protocol schema files were retained.

The experiment's tmux session has been removed. Codex's normal history records remain under its user data directory. An isolated dependency virtualenv remains under `codex/.venv/` and is ignored by the local `.gitignore`.
