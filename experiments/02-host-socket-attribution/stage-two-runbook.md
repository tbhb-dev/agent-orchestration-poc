# Stage-two harness runbook

## Boundary and preflight

**Untested:** none of these harness commands ran in stage one. The operator must review [the responder source](model_responder.py) and all eight exact [response fixtures](fixtures/responder/). Review [the listener](probe.py) and [the file-open audit](file-open-audit.md) before a cell starts. The responder returns one fixed native shell tool call and one final frame, then rejects another request. A startup request outside the fixed Responses or Messages endpoint is rejected. Stop that cell and report `unsupported with fake key` if it cannot reach the one connector command. The model HTTP port is separate from the Unix workload connector. No SVID is issued or bound, and there is no operator control socket.

Run from `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/exp-228-host-harness-connectors` in a fresh operator-approved shell. Use the pinned `codex-cli 0.157.1`, Claude Code `2.1.283`, and the source commits in [versions.md](versions.md). Record output and exit codes for each preflight command without inspecting an operator profile.

```sh
date '+%Y-%m-%d %H:%M:%S %Z'
sw_vers
uname -m
codex --version
claude --version
git status --short
for name in codex-interactive codex-headless claude-interactive claude-headless; do test ! -e "/private/tmp/bv01-228-$name" || exit 1; done
```

## Disposable homes and trace

Use exactly the four approved homes. Set `umask 077`. A system-wide open trace requires the operator's privileged terminal and the separate audit review. A directory snapshot by itself says nothing about reads.

```sh
umask 077
for name in codex-interactive codex-headless claude-interactive claude-headless; do mkdir -m 700 "/private/tmp/bv01-228-$name"; mkdir -m 700 "/private/tmp/bv01-228-$name/tmp" "/private/tmp/bv01-228-$name/xdg" "/private/tmp/bv01-228-$name/workspace"; done
for name in codex-interactive codex-headless; do mkdir -m 700 "/private/tmp/bv01-228-$name/codex"; done
for name in claude-interactive claude-headless; do mkdir -m 700 "/private/tmp/bv01-228-$name/claude"; done
for name in codex-interactive codex-headless claude-interactive claude-headless; do stat -c '%a %n' "/private/tmp/bv01-228-$name"; done
for name in codex-interactive codex-headless claude-interactive claude-headless; do mkdir -p "/private/tmp/bv01-228-$name/workspace/experiments/02-host-socket-attribution" "/private/tmp/bv01-228-$name/workspace/agent_orchestration_poc/core"; cp experiments/02-host-socket-attribution/probe.py "/private/tmp/bv01-228-$name/workspace/experiments/02-host-socket-attribution/probe.py"; cp src/agent_orchestration_poc/__init__.py "/private/tmp/bv01-228-$name/workspace/agent_orchestration_poc/__init__.py"; cp src/agent_orchestration_poc/core/__init__.py src/agent_orchestration_poc/core/host_socket_attribution.py "/private/tmp/bv01-228-$name/workspace/agent_orchestration_poc/core/"; done
for name in codex-interactive codex-headless claude-interactive claude-headless; do sha256sum "/private/tmp/bv01-228-$name/workspace/experiments/02-host-socket-attribution/probe.py" "/private/tmp/bv01-228-$name/workspace/agent_orchestration_poc/core/host_socket_attribution.py"; done
```

Use this fixed executable path, recorded from stage one on this host. Check that Codex, Claude, and Python still resolve to the pinned versions before launching. The responder runs once per cell so its two-frame sequence and log remain isolated.

```sh
probe=experiments/02-host-socket-attribution/probe.py
responder=experiments/02-host-socket-attribution/model_responder.py
```

## Per-cell setup

For each cell, set `profile` to one of the four literal names below and start exactly one responder. Its startup JSON supplies `port` and `pid`. Read that line only from the disposable log. Confirm `lsof` shows a `127.0.0.1` listener for that PID. The command is a loopback bind even if `--host` is omitted in code, and `--host` accepts only `127.0.0.1`.

```sh
profile=codex-headless
home="/private/tmp/bv01-228-$profile"
PYTHONSAFEPATH=1 mise exec -- uv run python "$responder" --host 127.0.0.1 --port 0 --profile "$profile" --log "$home/model.jsonl" > "$home/model-start.json" 2> "$home/model.err" &
model_pid=$!
while test ! -s "$home/model-start.json"; do sleep 0.05; done
port=$(mise exec -- python -c 'import json,sys; print(json.load(open(sys.argv[1]))["port"])' "$home/model-start.json")
printf '%s\n' "$port" > "$home/model-port"
lsof -nP -a -p "$model_pid" -iTCP
```

Run the same block in sequence with `profile=codex-interactive`, `profile=claude-headless`, and `profile=claude-interactive`, always using a fresh responder process and that cell's own home. Do not run two responder instances against the same profile log. Record the responder PID, port, request count, and exit status. A path or host mismatch in `model.jsonl` stops that cell.

Write the Codex file inside that profile's `codex` directory. Substitute the recorded loopback port and the literal mode in the socket path. The following example lists the intended Codex settings.

```sh
cat > /private/tmp/bv01-228-codex-headless/codex/config.toml <<EOF
model_provider = "bv01"
default_permissions = "bv01"
[model_providers.bv01]
name = "bv01"
base_url = "http://127.0.0.1:$port/v1"
wire_api = "responses"
env_key = "BV01_FAKE_OPENAI_KEY"
[permissions.bv01.network]
enabled = true
[permissions.bv01.network.unix_sockets]
"/private/tmp/bv01-228-codex-headless/gateway.sock" = "allow"
EOF
```

For Codex interactive, use the port from that profile's fresh responder. Do not use `-s` to replace the selected permissions profile.

```sh
cat > /private/tmp/bv01-228-codex-interactive/codex/config.toml <<EOF
model_provider = "bv01"
default_permissions = "bv01"
[model_providers.bv01]
name = "bv01"
base_url = "http://127.0.0.1:$port/v1"
wire_api = "responses"
env_key = "BV01_FAKE_OPENAI_KEY"
[permissions.bv01.network]
enabled = true
[permissions.bv01.network.unix_sockets]
"/private/tmp/bv01-228-codex-interactive/gateway.sock" = "allow"
EOF
```

Write the Claude file inside each Claude home. Use the mode's literal socket path. Each command writes settings for its own profile.

```sh
cat > /private/tmp/bv01-228-claude-headless/settings.json <<'EOF'
{"sandbox":{"enabled":true,"network":{"allowUnixSockets":["/private/tmp/bv01-228-claude-headless/gateway.sock"],"allowAllUnixSockets":false,"allowLocalBinding":false},"allowUnsandboxedCommands":false}}
EOF
cat > /private/tmp/bv01-228-claude-interactive/settings.json <<'EOF'
{"sandbox":{"enabled":true,"network":{"allowUnixSockets":["/private/tmp/bv01-228-claude-interactive/gateway.sock"],"allowAllUnixSockets":false,"allowLocalBinding":false},"allowUnsandboxedCommands":false}}
EOF
```

Inspect each effective file for unexpected socket paths, provider URLs, and settings. The fake literal `not-a-real-key` is the only provider credential supplied. Do not answer a login, trust, or real-key prompt.

## Launch barrier and listener

The listener needs the launch-root PID before it binds. Start a wrapper shell that writes its own PID to `root.pid`, waits for `go`, and then replaces itself with `env -i` and the harness. Run the wrapper from that profile's `workspace`. For an interactive cell, enter its wrapper command in a dedicated tmux server made with `tmux -S /private/tmp/bv01-228-probe.tmux -f /dev/null`, without addressing the default server or session `0`. The wrapper command for Codex headless is shown exactly. For another cell, use its literal home and the corresponding harness command below.

```sh
sh -c 'printf "%s\n" "$$" > /private/tmp/bv01-228-codex-headless/root.pid; while test ! -e /private/tmp/bv01-228-codex-headless/go; do sleep 0.05; done; cd /private/tmp/bv01-228-codex-headless/workspace || exit 1; exec env -i HOME=/private/tmp/bv01-228-codex-headless CODEX_HOME=/private/tmp/bv01-228-codex-headless/codex TMPDIR=/private/tmp/bv01-228-codex-headless/tmp XDG_CONFIG_HOME=/private/tmp/bv01-228-codex-headless/xdg PYTHONPATH=/private/tmp/bv01-228-codex-headless/workspace BV01_FAKE_OPENAI_KEY=not-a-real-key PATH=/Users/tony/.local/bin:/Users/tony/.local/share/mise/installs/python/3.14.6/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm-256color LANG=C.UTF-8 codex exec --ephemeral --skip-git-repo-check -C /private/tmp/bv01-228-codex-headless/workspace -c approval_policy=never "Run python3 experiments/02-host-socket-attribution/probe.py client /private/tmp/bv01-228-codex-headless/gateway.sock codex-headless and then stop."' &
```

From the supervisor shell, wait for `root.pid` and start a one-request listener. Then release the wrapper. Repeat with a fresh listener for each cell. Capture listener stdout under that cell's home and keep its `gateway.sock` path there. The listener records the root's PID and start time through `proc_pidinfo`.

```sh
while test ! -s "$home/root.pid"; do sleep 0.05; done
root_pid=$(cat "$home/root.pid")
PYTHONSAFEPATH=1 mise exec -- uv run python "$probe" server "$home/gateway.sock" "$root_pid" 1 > "$home/listener.jsonl" 2> "$home/listener.err" &
listener_pid=$!
while test ! -S "$home/gateway.sock"; do sleep 0.05; done
: > "$home/go"
```

The wrapper runs each harness from that cell's `workspace` and sets `PYTHONPATH` to that workspace so the copied package resolves when Python executes the nested probe script. The setup copied it entirely inside the disposable home. The fresh workspaces contain no Git repository. The Codex headless command uses `--skip-git-repo-check` for that precondition. Do not point a harness at the operator's repository checkout.

Create the remaining launch commands inside their approved homes. Each script writes its own process ID before replacing the shell with the harness. The port for Claude comes from that profile's `model-port` file. These scripts are stage-two commands and were not written during stage one.

```sh
cat > /private/tmp/bv01-228-codex-interactive/launch.sh <<'EOF'
#!/bin/sh
printf '%s\n' "$$" > /private/tmp/bv01-228-codex-interactive/root.pid
while test ! -e /private/tmp/bv01-228-codex-interactive/go; do sleep 0.05; done
cd /private/tmp/bv01-228-codex-interactive/workspace || exit 1
exec env -i HOME=/private/tmp/bv01-228-codex-interactive CODEX_HOME=/private/tmp/bv01-228-codex-interactive/codex TMPDIR=/private/tmp/bv01-228-codex-interactive/tmp XDG_CONFIG_HOME=/private/tmp/bv01-228-codex-interactive/xdg PYTHONPATH=/private/tmp/bv01-228-codex-interactive/workspace BV01_FAKE_OPENAI_KEY=not-a-real-key PATH=/Users/tony/.local/bin:/Users/tony/.local/share/mise/installs/python/3.14.6/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm-256color LANG=C.UTF-8 codex -C /private/tmp/bv01-228-codex-interactive/workspace -c approval_policy=never
EOF
cat > /private/tmp/bv01-228-claude-interactive/launch.sh <<'EOF'
#!/bin/sh
printf '%s\n' "$$" > /private/tmp/bv01-228-claude-interactive/root.pid
while test ! -e /private/tmp/bv01-228-claude-interactive/go; do sleep 0.05; done
cd /private/tmp/bv01-228-claude-interactive/workspace || exit 1
port=$(cat /private/tmp/bv01-228-claude-interactive/model-port)
exec env -i HOME=/private/tmp/bv01-228-claude-interactive CLAUDE_CONFIG_DIR=/private/tmp/bv01-228-claude-interactive/claude TMPDIR=/private/tmp/bv01-228-claude-interactive/tmp XDG_CONFIG_HOME=/private/tmp/bv01-228-claude-interactive/xdg PYTHONPATH=/private/tmp/bv01-228-claude-interactive/workspace ANTHROPIC_API_KEY=not-a-real-key ANTHROPIC_BASE_URL="http://127.0.0.1:$port" PATH=/Users/tony/.local/bin:/Users/tony/.local/share/mise/installs/python/3.14.6/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm-256color LANG=C.UTF-8 claude --bare --strict-mcp-config --setting-sources '' --settings /private/tmp/bv01-228-claude-interactive/settings.json
EOF
cat > /private/tmp/bv01-228-claude-headless/launch.sh <<'EOF'
#!/bin/sh
printf '%s\n' "$$" > /private/tmp/bv01-228-claude-headless/root.pid
while test ! -e /private/tmp/bv01-228-claude-headless/go; do sleep 0.05; done
cd /private/tmp/bv01-228-claude-headless/workspace || exit 1
port=$(cat /private/tmp/bv01-228-claude-headless/model-port)
exec env -i HOME=/private/tmp/bv01-228-claude-headless CLAUDE_CONFIG_DIR=/private/tmp/bv01-228-claude-headless/claude TMPDIR=/private/tmp/bv01-228-claude-headless/tmp XDG_CONFIG_HOME=/private/tmp/bv01-228-claude-headless/xdg PYTHONPATH=/private/tmp/bv01-228-claude-headless/workspace ANTHROPIC_API_KEY=not-a-real-key ANTHROPIC_BASE_URL="http://127.0.0.1:$port" PATH=/Users/tony/.local/bin:/Users/tony/.local/share/mise/installs/python/3.14.6/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm-256color LANG=C.UTF-8 claude --bare --strict-mcp-config --setting-sources '' --settings /private/tmp/bv01-228-claude-headless/settings.json --print --no-session-persistence --permission-prompts none 'Run python3 experiments/02-host-socket-attribution/probe.py client /private/tmp/bv01-228-claude-headless/gateway.sock claude-headless and then stop.'
EOF
tmux -S /private/tmp/bv01-228-probe.tmux -f /dev/null new-session -d -s bv01 -n anchor 'sleep 7200'
tmux -S /private/tmp/bv01-228-probe.tmux new-window -t bv01 -n codex-interactive 'sh /private/tmp/bv01-228-codex-interactive/launch.sh'
tmux -S /private/tmp/bv01-228-probe.tmux new-window -t bv01 -n claude-interactive 'sh /private/tmp/bv01-228-claude-interactive/launch.sh'
sh /private/tmp/bv01-228-claude-headless/launch.sh > /private/tmp/bv01-228-claude-headless/harness.out 2> /private/tmp/bv01-228-claude-headless/harness.err &
```

For interactive cells, enter only the corresponding literal socket-client prompt from its committed response fixture. Record argv, exit code, sanitized stdout and stderr, effective settings, process tree, token and ancestry trace, connection ID, case tag, and responder request count. If a helper or relay opens the socket, identify that process as the kernel peer. Do not infer the original caller from the relay PID. Repeat the required lifecycle and two-workload cases only under the operator-approved stage-two procedure. Keep each profile's separate socket and launch record.

## Teardown

Send `SIGTERM` only to recorded probe PIDs and wait for exit. Inspect `lsof -nP -U` and `lsof -nP -a -p <recorded-pid>` for remaining probe sockets and processes. Stop the dedicated tmux server. Scan all raw evidence for usable values before moving redacted output into this experiment directory. Remove only the approved paths after guarded equality checks.

```sh
tmux -S /private/tmp/bv01-228-probe.tmux kill-server
for name in codex-interactive codex-headless claude-interactive claude-headless; do test -d "/private/tmp/bv01-228-$name" || exit 1; done
for name in codex-interactive codex-headless claude-interactive claude-headless; do rm -r -- "/private/tmp/bv01-228-$name"; done
if test -e /private/tmp/bv01-228-probe.tmux; then rm -- /private/tmp/bv01-228-probe.tmux; fi
test -z "$(find /private/tmp -maxdepth 1 -name 'bv01-228-*' -print)"
```

Report `configuration and keychain reads unverified` unless the reviewed file-open audit establishes better evidence. Stage one cannot qualify a harness profile. In all cases, the inherited-descriptor attribution gap from the fixture remains a security limit until a new binding mechanism is tested.
