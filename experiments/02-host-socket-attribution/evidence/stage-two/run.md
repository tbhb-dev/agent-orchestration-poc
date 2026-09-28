# BV-01 stage two run record

Raw executor notes for the #228 stage-two run step, under operator decisions BV-19, BV-20, BV-22, OP-12, and OP-15 (2026-09-28). The executor was a Claude Code subagent on model `claude-opus-5-5`, launched by the coordinator. The run stopped at the audit positive control. No responder, listener, harness, tmux server, or other process was started.

## Audit capture as found

The operator started the capture at 16:02 EDT. The executor did not stop, signal, or edit it. A process listing at 16:04:42 EDT showed:

```text
$ ps -o pid,ppid,etime,command -p 12868,12870
  PID  PPID ELAPSED COMMAND
12868 95183   02:12 sudo eslogger open
12870 95183   02:12 grep --line-buffered -E /Users/tony/\.(codex|claude)|/Library/Keychains|1Password|/private/tmp/bv01-228-
```

The output file is `/private/tmp/bv01-228-codex-headless/file-opens.json`, owned by `tony`.

## Positive control

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; /bin/cat /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/__init__.py > /dev/null & echo "cat pid $!"; wait
2026-09-28 16:03:19 EDT
cat pid 23720
[exit 0]
```

A background loop then checked the file every 0.5 seconds for 30 seconds for the control path:

```text
$ f=/private/tmp/bv01-228-codex-headless/file-opens.json; for i in $(seq 1 60); do grep -q 'bv01-228-codex-headless/workspace/agent_orchestration_poc/__init__.py' "$f" && break; sleep 0.5; done; date '+%Y-%m-%d %H:%M:%S %Z'; grep -c 'bv01-228-codex-headless/workspace/agent_orchestration_poc/__init__.py' "$f"; wc -l < "$f"; ls -l "$f"
2026-09-28 16:04:13 EDT
0
29
-rw-r--r-- 1 tony wheel 58025 Sep 28 16:03 /private/tmp/bv01-228-codex-headless/file-opens.json
[exit 0]
```

**Observed: the positive control failed.** No line for the control path or for PID 23720 appeared within 30 seconds. The capture was live over the same window. Of its 29 lines, 28 were events timestamped after the control open, from 20:03:20Z to 20:03:28Z, all from 1Password or `PerfPowerServices` opening 1Password bundle paths.

```text
$ grep -c 'bv01-228' /private/tmp/bv01-228-codex-headless/file-opens.json
0
$ grep -c 'Keychains' /private/tmp/bv01-228-codex-headless/file-opens.json
0
```

## Cause

**Observed:** `eslogger` escapes every forward slash in its JSON output as `\/`. All 29 lines contain `\/`, and a matched path reads `"path":"\/Applications\/1Password.app\/Contents\/..."`. The filter's alternatives `/Users/tony/\.(codex|claude)`, `/Library/Keychains`, and `/private/tmp/bv01-228-` each contain a literal `/`, so no escaped path can match them. Only `1Password`, which has no slash, can match. **Inference:** the running capture can't record any open under `~/.codex`, `~/.claude`, `~/.claude.json`, `/Library/Keychains`, or the four homes, so it can't serve as the #228 audit.

**Observed, on sample strings only:** this pattern matches escaped paths for the control home, `~/.codex`, and `/Library/Keychains`. Run against the capture file, it matched all 29 existing 1Password lines.

```text
grep --line-buffered -E '\\/Users\\/tony\\/\.(codex|claude)|\\/Library\\/Keychains|1Password|\\/private\\/tmp\\/bv01-228-'
```

**Untested:** a restarted capture using that pattern with `eslogger`. Only the operator starts and stops the capture, so a restart is the operator's step. The positive control would then run again before any harness launch.

## Stop

Per the dispatch rule, the executor stopped without launching any harness. The homes `/private/tmp/bv01-228-{codex-interactive,codex-headless,claude-interactive,claude-headless}` and their prepared harness files remain as left by the preparation step.

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; pgrep -fl 'bv01-228|model_responder|probe.py'; test -e /private/tmp/bv01-228-probe.tmux && echo "tmux socket present" || echo "no dedicated tmux socket"
2026-09-28 16:04:58 EDT
12870 grep --line-buffered -E /Users/tony/\.(codex|claude)|/Library/Keychains|1Password|/private/tmp/bv01-228-
no dedicated tmux socket
```

**Observed:** the only matching process is the operator's capture filter. No responder, listener, probe, or harness process was running, and the dedicated tmux socket did not exist. The default tmux server and session `0` were never addressed.

The capture file was read only through `grep` and `jq` for times, PIDs, executable names, and paths. It isn't copied into this repository.

## Second attempt

The second run executor was a Claude Code subagent on model `claude-opus-5-5`, launched by the coordinator. The operator restarted the capture at 17:13 EDT with a filter that contains no slashes.

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; ps -o pid,ppid,etime,command -p 28387,28388; ls -l /private/tmp/bv01-228-codex-headless/file-opens.json
2026-09-28 17:14:50 EDT
  PID  PPID ELAPSED COMMAND
28387  4566   01:04 sudo eslogger open
28388  4566   01:04 grep --line-buffered -E \.codex|\.claude|Keychains|1Password|bv01-228-
-rw-r--r-- 1 tony wheel 13682458 Sep 28 17:14 /private/tmp/bv01-228-codex-headless/file-opens.json
```

**Observed:** the filter also matches other Codex and Claude sessions on this Mac. The file grows quickly. The executor reads it only through counts and filters on PID and `bv01-228` paths.

### Positive control, second attempt

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; /bin/cat /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/__init__.py > /dev/null & echo "cat pid $!"; wait
2026-09-28 17:14:57 EDT
cat pid 46032

$ date '+%Y-%m-%d %H:%M:%S %Z'; f=/private/tmp/bv01-228-codex-headless/file-opens.json; grep -F 'bv01-228-codex-headless' "$f" | grep -F 'agent_orchestration_poc' | grep -F '__init__.py' | grep -c '"pid":46032'; grep -F 'bv01-228-codex-headless' "$f" | grep -F '__init__.py' | grep '"pid":46032' | head -n 1 | jq -c '{time, pid: .process.audit_token.pid, exe: .process.executable.path, path: .event.open.file.path}'
2026-09-28 17:15:04 EDT
1
{"time":"2026-09-28T21:14:57.609456507Z","pid":46032,"exe":"/bin/cat","path":"/private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/__init__.py"}
```

**Observed: the positive control passed.** The capture recorded one open event for the control path from `/bin/cat` PID 46032, 7 seconds before the check. The harness cells proceed.

### Versions at launch

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; codex --version; claude --version; mise exec -- python --version; mise exec -- tmux -V; readlink /Users/tony/.local/bin/claude; git -C <worktree> rev-parse HEAD
2026-09-28 17:16:26 EDT
codex-cli 0.157.1
2.1.284 (Claude Code)
Python 3.14.6
tmux 3.7b
/Users/tony/.local/share/claude/versions/2.1.284
84bec13bd2ddaf0a4a3f7a43571b8d878984963d
```

Each long-running command (responder, wrapper, listener) ran as a Claude Code background Bash task instead of with a trailing `&`, with the same argv and redirections as the runbook. The runbook's `: > "$home/go"` was performed with the Claude Code Write tool writing an empty file. The runbook's `while test ! -s ...; do sleep 0.05; done` waits were replaced by a separate check call after the file appeared.

### Cell codex-headless, attempt 1

Responder, from the worktree root:

```text
$ date '+%Y-%m-%d %H:%M:%S %Z' && PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/model_responder.py --host 127.0.0.1 --port 0 --profile codex-headless --log /private/tmp/bv01-228-codex-headless/model.jsonl > /private/tmp/bv01-228-codex-headless/model-start.json 2> /private/tmp/bv01-228-codex-headless/model.err

$ date '+%Y-%m-%d %H:%M:%S %Z'; h=/private/tmp/bv01-228-codex-headless; cat "$h/model-start.json"; cat "$h/model.err"; pid=$(jq -r .pid "$h/model-start.json"); port=$(jq -r .port "$h/model-start.json"); printf '%s\n' "$port" > "$h/model-port"; cat "$h/model-port"; lsof -nP -a -p "$pid" -iTCP; ps -o pid,ppid,command -p "$pid"
2026-09-28 17:16:36 EDT
{"host": "127.0.0.1", "port": 54706, "pid": 69931}
Using CPython 3.14.6 interpreter at: /Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3.14
Creating virtual environment at: .venv
   Building agent-orchestration-poc @ file:///Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/exp-228-harness-stage-two
      Built agent-orchestration-poc @ file:///Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/exp-228-harness-stage-two
Installed 28 packages in 120ms
54706
COMMAND     PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python3.1 69931 tony    3u  IPv4 0x455a6916e12a676e      0t0  TCP 127.0.0.1:54706 (LISTEN)
  PID  PPID COMMAND
69931 69790 <worktree>/.venv/bin/python experiments/02-host-socket-attribution/model_responder.py --host 127.0.0.1 --port 0 --profile codex-headless --log /private/tmp/bv01-228-codex-headless/model.jsonl
```

**Observed:** responder PID 69931 listened only on `127.0.0.1:54706`.

The executor wrote `/private/tmp/bv01-228-codex-headless/codex/config.toml` with the Write tool, ran `chmod 600` on it, and compared it with the runbook heredoc after substituting the port:

```text
$ awk -v t="cat > $f <<EOF" '$0==t{on=1;next} on&&$0=="EOF"{exit} on' experiments/02-host-socket-attribution/stage-two-runbook.md | sed 's/\$port/54706/' > <scratch>/expected/codex-headless-config.toml && cmp <scratch>/expected/codex-headless-config.toml "$f" && echo 'identical to runbook heredoc with port 54706'; stat -c '%a %s %n' "$f"
identical to runbook heredoc with port 54706
600 315 /private/tmp/bv01-228-codex-headless/codex/config.toml
```

Wrapper, the runbook's exact `sh -c '...'` Codex headless command with `> /private/tmp/bv01-228-codex-headless/harness.out 2> /private/tmp/bv01-228-codex-headless/harness.err` in place of `&`:

```text
$ cat /private/tmp/bv01-228-codex-headless/root.pid; ps -o pid,ppid,lstart,command -p 75591
75591
  PID  PPID STARTED                      COMMAND
75591 75589 Mon Sep 28 17:16:56 2026     sh -c printf "%s\n" "$$" > /private/tmp/bv01-228-codex-headless/root.pid; while test ! -e ... codex exec --ephemeral --skip-git-repo-check -C /private/tmp/bv01-228-codex-headless/workspace -c approval_policy=never "Run python3 experiments/02-host-socket-attribution/probe.py client /private/tmp/bv01-228-codex-headless/gateway.sock codex-headless and then stop."
```

Listener, from the worktree root, started 17:17:0x EDT:

```text
$ PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/probe.py server /private/tmp/bv01-228-codex-headless/gateway.sock 75591 1 > /private/tmp/bv01-228-codex-headless/listener.jsonl 2> /private/tmp/bv01-228-codex-headless/listener.err
$ test -S "$h/gateway.sock" && echo "socket present"; stat -c '%a %F %n' "$h/gateway.sock"
socket present
755 socket /private/tmp/bv01-228-codex-headless/gateway.sock
```

**Observed:** listener PID 77357 (under `uv` PID 77334) bound the socket with mode 755, because the listener shell did not set `umask 077`. The home directory is mode 700.

The executor wrote the empty `go` file at about 17:17:10 EDT. The wrapper exited 1 immediately:

```text
$ cat /private/tmp/bv01-228-codex-headless/harness.out
$ cat /private/tmp/bv01-228-codex-headless/harness.err
Error loading config.toml: model_providers.bv01: provider name must not be empty
in `model_providers`
$ cat /private/tmp/bv01-228-codex-headless/model.jsonl
cat: /private/tmp/bv01-228-codex-headless/model.jsonl: No such file or directory
$ cat /private/tmp/bv01-228-codex-headless/listener.jsonl
```

**Observed:** the Codex CLI rejected the runbook's configuration before sending any model request or running any tool. The responder log was never created, and the listener log is empty. Codex created `codex/tmp/arg0/codex-arg0<random>/` with `.lock` and the `applypatch`, `apply_patch`, and `codex-execve-wrapper` links before exiting.

**Source-confirmed at `openai/codex@a6bd19261c30ce0a0225fe90e646822d29916f11`:** `codex-rs/config/src/config_toml.rs` lines 924 to 927, in `validate_model_providers`, return this error when a non-Bedrock provider's `name` is empty after trimming. The runbook's two Codex heredocs omit `name`. This runbook defect blocks both Codex cells. The fake key and the permission rules played no part.

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; ps -o pid,ppid,command -p 77357,69931; kill -TERM 77357 69931
2026-09-28 17:17:50 EDT
(both PIDs listed with the recorded responder and listener commands)
$ date '+%Y-%m-%d %H:%M:%S %Z'; pgrep -fl 'bv01-228-codex-headless|model_responder'; lsof -nP -iTCP:54706
2026-09-28 17:17:55 EDT
```

**Observed:** both background tasks ended with status 143, and nothing remained on port 54706. The stale `gateway.sock` remains, because the killed listener never reached its `unlink`. At 17:18 EDT the executor asked the coordinator whether to add `name = "bv01"` under `[model_providers.bv01]` in both Codex configs as a recorded deviation, and continued with the Claude cells.

### Cell claude-headless

```text
$ date '+%Y-%m-%d %H:%M:%S %Z' && PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/model_responder.py --host 127.0.0.1 --port 0 --profile claude-headless --log /private/tmp/bv01-228-claude-headless/model.jsonl > /private/tmp/bv01-228-claude-headless/model-start.json 2> /private/tmp/bv01-228-claude-headless/model.err
$ (startup check, same form as codex-headless)
2026-09-28 17:18:45 EDT
{"host": "127.0.0.1", "port": 55370, "pid": 98791}
55370
COMMAND     PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python3.1 98791 tony    3u  IPv4 0x154847fe22855678      0t0  TCP 127.0.0.1:55370 (LISTEN)
{"sandbox":{"enabled":true,"network":{"allowUnixSockets":["/private/tmp/bv01-228-claude-headless/gateway.sock"],"allowAllUnixSockets":false,"allowLocalBinding":false},"allowUnsandboxedCommands":false}}

$ sh /private/tmp/bv01-228-claude-headless/launch.sh > /private/tmp/bv01-228-claude-headless/harness.out 2> /private/tmp/bv01-228-claude-headless/harness.err
$ cat /private/tmp/bv01-228-claude-headless/root.pid; ps -o pid,ppid,lstart,command -p 767
767
  PID  PPID STARTED                      COMMAND
  767   763 Mon Sep 28 17:18:49 2026     sh /private/tmp/bv01-228-claude-headless/launch.sh

$ PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/probe.py server /private/tmp/bv01-228-claude-headless/gateway.sock 767 1 > /private/tmp/bv01-228-claude-headless/listener.jsonl 2> /private/tmp/bv01-228-claude-headless/listener.err
$ stat -c '%a %F %n' /private/tmp/bv01-228-claude-headless/gateway.sock
2026-09-28 17:19:06 EDT
755 socket /private/tmp/bv01-228-claude-headless/gateway.sock
(listener PID 3356 under uv PID 3349)
```

The executor wrote the empty `go` file at about 17:19:10 EDT. The launch task exited 1:

```text
$ date; cat harness.out; cat harness.err; cat model.jsonl; cat listener.jsonl   (in /private/tmp/bv01-228-claude-headless)
2026-09-28 17:19:16 EDT
--- harness.out
Failed to authenticate. API Error: 403 status code (no body)
--- harness.err
--- model.jsonl
{"path": "<unexpected-path>", "status": 501}
{"path": "<unexpected-path>", "status": 403}
--- listener.jsonl
```

**Observed:** the Claude Code 2.1.284 process sent two requests to the loopback responder, and neither was the exact `POST /v1/messages` the responder accepts. The first drew 501, which `BaseHTTPRequestHandler` returns for a method with no handler, since the responder defines only `do_POST` and `do_GET`. The second drew 403, which `responder_reply` returns for a wrong method, a path that differs from `/v1/messages`, or a wrong `Host`. By design the responder logs neither the path nor the method. Claude printed an authentication failure and exited 1 without running a tool. The listener log is empty.

**Observed:** the run created `claude/.claude.json` (mode 600), `claude/backups/`, `claude/sessions/`, `claude/seed-admin/`, `xdg/anthropic/`, and `tmp/node-compile-cache/`, all inside the disposable home.

**Inference, from strings in the installed binary, not from the request:**

```text
$ b=/Users/tony/.local/share/claude/versions/2.1.284; file "$b" | cut -c1-120; grep -a -o '/v1/messages?beta=true' "$b" | sort | uniq -c; grep -a -o '"/v1/messages"' "$b" | sort | uniq -c; grep -a -o 'method:"HEAD"' "$b" | sort | uniq -c
2026-09-28 17:19:43 EDT
/Users/tony/.local/share/claude/versions/2.1.284: Mach-O 64-bit executable arm64
      5 /v1/messages?beta=true
     13 "/v1/messages"
      1 method:"HEAD"
```

The binary contains `/v1/messages?beta=true` and one `HEAD` request literal. **Inference:** the 501 was a `HEAD` request and the 403 was a Messages request with the `?beta=true` query, which the exact path comparison in `responder_reply` rejects. A logged method and raw path would confirm it. Under the runbook rule ("a path or host mismatch in `model.jsonl` stops that cell"), the cell stopped. Following the dispatch rule, the result is recorded as **`unsupported with fake key`** for the committed responder. The fake key itself was never evaluated, since the responder does not check credentials. The runbook's `--permission-prompts none` flag was accepted, because the process got as far as sending model requests.

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; ps -o pid,ppid,command -p 3356,98791; kill -TERM 3356 98791
2026-09-28 17:19:36 EDT
(both PIDs listed with the recorded listener and responder commands; both background tasks ended with status 143)
```

### Cell claude-interactive

```text
$ PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/model_responder.py --host 127.0.0.1 --port 0 --profile claude-interactive --log /private/tmp/bv01-228-claude-interactive/model.jsonl > /private/tmp/bv01-228-claude-interactive/model-start.json 2> /private/tmp/bv01-228-claude-interactive/model.err
2026-09-28 17:19:54 EDT
{"host": "127.0.0.1", "port": 55497, "pid": 12732}
python3.1 12732 tony    3u  IPv4 0xb4a8057162d5b07b      0t0  TCP 127.0.0.1:55497 (LISTEN)

$ tmux -S /private/tmp/bv01-228-probe.tmux -f /dev/null new-session -d -s bv01 -n anchor 'sleep 7200'
$ tmux -S /private/tmp/bv01-228-probe.tmux new-window -t bv01 -n claude-interactive 'sh /private/tmp/bv01-228-claude-interactive/launch.sh'
$ date; cat root.pid; ps -o pid,ppid,lstart,command -p 14780; tmux -S /private/tmp/bv01-228-probe.tmux list-windows -t bv01 -F '#{window_index} #{window_name} #{pane_pid}'; tmux -S /private/tmp/bv01-228-probe.tmux display -p '#{pid}'
2026-09-28 17:20:05 EDT
14780
  PID  PPID STARTED                      COMMAND
14780 13952 Mon Sep 28 17:20:00 2026     sh /private/tmp/bv01-228-claude-interactive/launch.sh
0 anchor 13953
1 claude-interactive 14780
13952

$ PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/probe.py server /private/tmp/bv01-228-claude-interactive/gateway.sock 14780 1 > /private/tmp/bv01-228-claude-interactive/listener.jsonl 2> /private/tmp/bv01-228-claude-interactive/listener.err
2026-09-28 17:20:13 EDT
755 socket /private/tmp/bv01-228-claude-interactive/gateway.sock
(listener PID 16750 under uv PID 16739)
```

**Observed:** the dedicated tmux server is PID 13952. The launch root, PID 14780, is the pane process of window 1.

The executor wrote the empty `go` file at about 17:20:16 EDT, then captured the pane:

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; tmux -S /private/tmp/bv01-228-probe.tmux capture-pane -p -t bv01:claude-interactive | sed '/^$/d' | head -60; cat /private/tmp/bv01-228-claude-interactive/model.jsonl
2026-09-28 17:20:20 EDT
Welcome to Claude Code v2.1.284
 Let's get started.
 Choose the text style that looks best with your terminal
 To change this later, run /theme
   1. Auto (match terminal)
 ❯ 2. Dark mode ✔
   3. Light mode
   ... (theme preview omitted)
{"path": "<unexpected-path>", "status": 501}

$ ps -axo pid,ppid,lstart,command | awk 'NR==1 || $1==14780 || $2==14780'
2026-09-28 17:20:28 EDT
  PID  PPID STARTED                      COMMAND
14780 13952 Mon Sep 28 17:20:00 2026     claude --bare --strict-mcp-config --setting-sources  --settings /private/tmp/bv01-228-claude-interactive/settings.json
```

**Observed:** the first-run theme selection is shown, and the responder already logged a 501 for an unexpected path before any prompt was entered. The runbook permits entering only the literal socket-client prompt, and a path mismatch stops the cell. The executor did not answer the theme prompt and entered no prompt. **Classification: prompted (first-run theme onboarding). The responder path mismatch stopped the cell, and it is recorded as `unsupported with fake key`.**

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; ps -o pid,ppid,command -p 14780,16750,12732; kill -TERM 14780 16750 12732
2026-09-28 17:20:31 EDT
(all three listed with the recorded commands)
$ date; ps -o pid,command -p 14780,16750,12732; tmux ... list-windows -t bv01 -F '#{window_index} #{window_name} #{pane_pid} dead=#{pane_dead}'
2026-09-28 17:20:36 EDT
  PID COMMAND
0 anchor 13953 dead=0
```

**Observed:** all three processes exited, and the claude-interactive window closed. The anchor window stays for the Codex interactive cell.

### Audit trace for the Claude cells

The executor read the capture only through PID filters and `jq` summaries, replacing `/Users/tony` with `~` in its output. First, the processes whose parent was a launch root:

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; f=/private/tmp/bv01-228-codex-headless/file-opens.json; ls -l "$f"; grep -E '"ppid":(767|14780|75591)[,}]' "$f" | jq -r '[.process.audit_token.pid, .process.ppid, .process.executable.path] | @tsv' | sort | uniq -c
2026-09-28 17:21:16 EDT
-rw-r--r-- 1 tony wheel 108247870 Sep 28 17:21 /private/tmp/bv01-228-codex-headless/file-opens.json
      1 18036	14780	/opt/homebrew/Cellar/coreutils/9.11/bin/gcat
      1 18046	14780	/usr/bin/security
      1 4635	767	/opt/homebrew/Cellar/coreutils/9.11/bin/gcat
      1 4754	767	/usr/bin/security
      2 4762	767	/opt/homebrew/Cellar/git/2.55.0/bin/git
      2 4763	767	/opt/homebrew/Cellar/git/2.55.0/bin/git
     14 4769	767	/Users/tony/.local/share/claude/versions/2.1.284
      1 4770	767	/bin/bash
      1 4771	767	/bin/bash
      3 4771	767	/opt/homebrew/Cellar/node/26.5.1/bin/node
      2 4773	767	/opt/homebrew/Cellar/git/2.55.0/bin/git
      1 4887	767	/bin/bash
```

A second query over those PIDs' parents found no further generation:

```text
$ grep -E '"ppid":(18036|18046|4635|4754|4762|4763|4769|4770|4771|4773|4887)[,}]' "$f" | jq -r '[.process.audit_token.pid, .process.ppid, .process.executable.path] | @tsv' | sort | uniq -c
(no output)
```

`gcat` is the launch script's `cat model-port` (GNU coreutils comes first on this host's fixed `PATH`). The per-path summary for all these PIDs came from this command:

```text
$ grep -E '"pid":(767|14780|18036|18046|4635|4754|4762|4763|4769|4770|4771|4773|4887)[,}]' "$f" | jq -r 'select(.process.audit_token.pid as $p | [767,14780,...] | index($p)) | [.process.audit_token.pid, (.process.executable.path|split("/")|last), (.event.open.fflag|tostring), .event.open.file.path] | @tsv' | sed 's#/Users/tony#~#g' | sort | uniq -c
```

The capture filter matches any event line containing `bv01-228-`, so it also recorded opens of unrelated paths by processes whose event JSON carries a `bv01-228` string. Findings, all **observed** within the capture's conditions:

- Neither launch-root process nor any recorded descendant opened a path under `~/.claude`, `~/.codex`, `~/.claude.json`, `~/Library/Keychains`, or 1Password. Claude opened its configuration only as `/private/tmp/bv01-228-<profile>/claude/.claude.json`, `.../claude/sessions`, `.../claude/backups`, and `.../settings.json` inside the disposable homes.
- Both Claude processes (PIDs 767 and 14780) opened `/Library/Keychains/System.keychain` with flag 1 (read). Each also executed `/usr/bin/security` (PIDs 4754 and 18046), and each of those opened `/Library/Keychains/System.keychain` with flag 1. The `security` argv is not in this capture, which records only open events.
- Both Claude processes opened `~/.CFUserTextEncoding` in the real home, and `~/.local/share/claude/versions/2.1.284`, `~/.local/share/claude/versions`, and `~/.local/bin`. **Inference:** the first is CoreFoundation's per-user text encoding file, which CoreFoundation locates through the password database instead of `$HOME`. The other paths contain the installed binary. None of them is Claude configuration.
- Both Claude processes executed `/opt/homebrew/Cellar/node/26.5.1/bin/node` and `/opt/homebrew/lib/node_modules/npm/bin/npm-cli.js`. In claude-headless, `node` PID 4771 created `/private/tmp/bv01-228-claude-headless/.npm/_logs`, inside the home. claude-headless also ran `git` in its workspace (PIDs 4762, 4763, 4773) and `/bin/ps`.
- **Write outside the disposable home:** claude-headless PID 767 created `/private/tmp/claude-501/-private-tmp-bv01-228-claude-headless-workspace/6d30609d-ee41-4799-b5bd-48ec3015fe11/tasks`, and both Claude processes opened `/private/tmp/claude-501` and `/private/tmp/claude-501/bash-edit-diff`. `/private/tmp/claude-501` is the per-UID Claude Code temporary directory that the operator's own sessions also use. **Inference:** the Claude Code 2.1.284 binary derives this location from the UID and ignores the `TMPDIR` the wrapper set. `bash-edit-diff` predates the run (dated Sep 27 08:56). The new `-private-tmp-bv01-228-claude-headless-workspace` directory is residue outside the four approved homes.

```text
$ ls -la /private/tmp/claude-501 | grep -E 'bv01|bash-edit-diff'; find /private/tmp/claude-501/-private-tmp-bv01-228-* -maxdepth 3
drwx------    3 tony wheel    96 Sep 28 17:19 -private-tmp-bv01-228-claude-headless-workspace
drwx------    2 tony wheel    64 Sep 27 08:56 bash-edit-diff
/private/tmp/claude-501/-private-tmp-bv01-228-claude-headless-workspace
/private/tmp/claude-501/-private-tmp-bv01-228-claude-headless-workspace/6d30609d-ee41-4799-b5bd-48ec3015fe11
/private/tmp/claude-501/-private-tmp-bv01-228-claude-headless-workspace/6d30609d-ee41-4799-b5bd-48ec3015fe11/tasks
```

**Limit:** this is an open-event trace. Keychain access brokered by `securityd` or another daemon is attributed to that daemon, not to the harness PID. Reads through inherited descriptors or memory maps don't produce an open event. Configuration and keychain reads remain **unverified**.

### Codex configuration deviation

At 17:22 EDT the coordinator approved one recorded deviation. It adds `name = "bv01"` under `[model_providers.bv01]` in both Codex configurations and in the runbook's two heredocs. It also removes the stale socket. The other configuration lines are unchanged. The approval cites the error above and `openai/codex@a6bd192`, `codex-rs/config/src/config_toml.rs` lines 924 to 927. The runbook diff in this branch:

```diff
@@ -61,6 +61,7 @@ cat > /private/tmp/bv01-228-codex-headless/codex/config.toml <<EOF
 model_provider = "bv01"
 default_permissions = "bv01"
 [model_providers.bv01]
+name = "bv01"
 base_url = "http://127.0.0.1:$port/v1"
 wire_api = "responses"
 env_key = "BV01_FAKE_OPENAI_KEY"
@@ -78,6 +79,7 @@ cat > /private/tmp/bv01-228-codex-interactive/codex/config.toml <<EOF
 model_provider = "bv01"
 default_permissions = "bv01"
 [model_providers.bv01]
+name = "bv01"
 base_url = "http://127.0.0.1:$port/v1"
 wire_api = "responses"
 env_key = "BV01_FAKE_OPENAI_KEY"
```

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; test -S /private/tmp/bv01-228-codex-headless/gateway.sock && rm /private/tmp/bv01-228-codex-headless/gateway.sock; ls -l /private/tmp/bv01-228-codex-headless/gateway.sock
2026-09-28 17:22:39 EDT
ls: cannot access '/private/tmp/bv01-228-codex-headless/gateway.sock': No such file or directory
```

The executor copied the attempt-1 outputs to [codex-headless/attempt-1](codex-headless/attempt-1/) and removed the old `/private/tmp/bv01-228-codex-headless/go` with `rm`. Otherwise the new wrapper would have passed its barrier before the listener bound.

### Capture restart and third positive control

At 17:23:06 EDT a second capture pipeline was running, and `file-opens.json` had been recreated at 17:21:55 EDT:

```text
$ ls -l --time-style=full-iso /private/tmp/bv01-228-codex-headless/file-opens.*; pgrep -fl 'eslogger|grep --line-buffered'
-rw-r--r-- 1 tony wheel        0 2026-09-28 17:21:55.427425692 -0400 /private/tmp/bv01-228-codex-headless/file-opens.err
-rw-r--r-- 1 tony wheel 12192243 2026-09-28 17:23:06.376020966 -0400 /private/tmp/bv01-228-codex-headless/file-opens.json
28387 sudo eslogger open
28388 grep --line-buffered -E \.codex|\.claude|Keychains|1Password|bv01-228-
28391 sudo eslogger open
28392 eslogger open
36396 sudo eslogger open
36397 grep --line-buffered -E \.codex|\.claude|Keychains|1Password|bv01-228-
36400 sudo eslogger open
36401 eslogger open
$ grep -c '"pid":46032[,}]' "$f"; grep -c '"pid":767[,}]' "$f"
0
0
```

**Observed:** the recreated file lacks the second positive control (PID 46032) and every claude-headless event (PID 767). The first capture (sudo PID 28387, grep PID 28388) is still running and presumably writes to the unlinked original file. The Claude-cell trace summary above was read from the original file at 17:21:16 EDT, before it was replaced. That summary is the only retained record of those events in the executor's view. The operator's vault notes that a completed restart block was run again at 17:21 and deleted the live capture file.

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; /bin/cat /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/__init__.py > /dev/null & echo "cat pid $!"; wait
2026-09-28 17:23:16 EDT
cat pid 52319
$ f=...; for i in $(seq 1 25); do n=$(grep -F '__init__.py' "$f" | grep -c '"pid":52319[,}]'); test "$n" -gt 0 && break; sleep 1; done; date; echo "matches $n"
2026-09-28 17:23:42 EDT
matches 1
{"time":"2026-09-28T21:23:16.900610622Z","pid":52319,"exe":"/bin/cat","path":"/private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/__init__.py"}
```

**Observed: the third positive control passed**, against the restarted capture. The event appeared between 6 and 26 seconds after the open. Later checks showed the capture running up to about 80 seconds behind real time (at 17:27:15 EDT its newest event was 21:25:52Z), and it had caught up by 17:27:49 EDT.

### Cell codex-headless, attempt 2

```text
$ PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/model_responder.py --host 127.0.0.1 --port 0 --profile codex-headless --log /private/tmp/bv01-228-codex-headless/model.jsonl > .../model-start.json 2> .../model.err
2026-09-28 17:22:59 EDT
{"host": "127.0.0.1", "port": 56475, "pid": 47561}
python3.1 47561 tony    3u  IPv4 0x497dbcf3c92e234      0t0  TCP 127.0.0.1:56475 (LISTEN)
no model log yet
```

The executor wrote the corrected configuration with the Write tool (it remained mode 600) and verified it:

```text
$ awk ... stage-two-runbook.md | sed 's/\$port/56475/' > <scratch>/expected/codex-headless-config-2.toml && cmp <scratch>/expected/codex-headless-config-2.toml "$f" && echo 'identical to corrected runbook heredoc with port 56475'; diff evidence/stage-two/codex-headless/attempt-1/config.toml "$f"
identical to corrected runbook heredoc with port 56475
4c4,5
< base_url = "http://127.0.0.1:54706/v1"
---
> name = "bv01"
> base_url = "http://127.0.0.1:56475/v1"
```

The wrapper was the same runbook command as attempt 1. Root PID 62657 started at 17:24:03. Listener PID 64233 (under `uv` PID 64219) ran `probe.py server /private/tmp/bv01-228-codex-headless/gateway.sock 62657 1`, and its socket was present at 17:24:13 with mode 755. The executor wrote `go` at about 17:24:15 EDT, and the wrapper exited 1:

```text
$ date; cat harness.out; sed 's/not-a-real-key/<fake>/g' harness.err; cat model.jsonl; cat listener.jsonl
2026-09-28 17:24:21 EDT
--- harness.out
--- harness.err
Reading additional input from stdin...
2026-09-28T21:24:16.155500Z ERROR codex_core::session: Failed to create session: failed to load AGENTS.md instructions for environment `local`: fs sandbox helper failed with status exit status: 71: sandbox-exec: execvp() of '/Users/tony/.local/bin/codex' failed: Operation not permitted
Error: thread/start: thread/start failed: error creating thread: failed to load AGENTS.md instructions for environment `local`: fs sandbox helper failed with status exit status: 71: sandbox-exec: execvp() of '/Users/tony/.local/bin/codex' failed: Operation not permitted (code -32603)
--- model.jsonl
cat: /private/tmp/bv01-228-codex-headless/model.jsonl: No such file or directory
--- listener.jsonl
```

**Observed:** with the corrected configuration, Codex loaded its configuration and started its session setup. It then failed while loading `AGENTS.md` instructions, because its filesystem sandbox helper could not start: `sandbox-exec` returned exit 71 after `execvp` of `/Users/tony/.local/bin/codex` was denied. The responder log was never created, and the listener log is empty.

**Source-confirmed at `openai/codex@a6bd192`:** `codex-rs/exec-server/src/fs_sandbox.rs` line 152 uses `runtime_paths.codex_self_exe` as the helper launched under the sandbox. Lines 232 to 270 add a read grant for exactly that path, plus the `Minimal` special read set when the profile lacks full disk read. `codex-rs/arg0/src/lib.rs` line 426 sets `codex_self_exe` from `std::env::current_exe()`.

**Inference:** `/Users/tony/.local/bin/codex` is a symlink to `/Users/tony/.codex/packages/standalone/current/bin/codex`, which resolves under the operator's real `~/.codex` (see prep.md). The Seatbelt profile grants read on the link path but not on the resolved binary under `~/.codex`. The kernel then denies the exec. That makes this `bv01` profile, a standalone install under `~/.codex`, and a disposable `CODEX_HOME` incompatible as launched. An untested fix is to launch the resolved binary path, or to grant read on the package directory. Either would be a further deviation needing approval, and the executor did not try one. **Classification: blocked at harness startup, before any model request. The runbook's launch recipe is `unsupported` on this install.**

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; ps -o pid,ppid,command -p 64233,47561; kill -TERM 64233 47561
2026-09-28 17:24:59 EDT
(both listed with the recorded listener and responder commands; both tasks ended with status 143)
```

Before failing, Codex created in `codex/`: `logs_2.sqlite`, `state_5.sqlite`, `goals_1.sqlite`, `memories_1.sqlite`, `queue_1.sqlite` (each with WAL and SHM), `installation_id`, `.sandbox_migration`, `shell_snapshots/`, `skills/.system/` (six system skills), `tmp/arg0/`, and `.tmp/plugins-clone-MlTu6x` (a partial clone with no `.git`). The logs database held 0 rows when read with `sqlite3 -readonly`.

### Cell codex-interactive

```text
$ PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/model_responder.py --host 127.0.0.1 --port 0 --profile codex-interactive --log /private/tmp/bv01-228-codex-interactive/model.jsonl > .../model-start.json 2> .../model.err
$ date; h=...; test -s "$h/model-start.json" || exit 3; cat "$h/model-start.json"; ...; lsof -nP -a -p "$pid" -iTCP
2026-09-28 17:25:13 EDT
{"host": "127.0.0.1", "port": 57143, "pid": 76644}
57143
python3.1 76644 tony    3u  IPv4 0x518d9c5a55a767ac      0t0  TCP 127.0.0.1:57143 (LISTEN)
```

The executor's first startup check, at 17:25:07 EDT, ran before `model-start.json` was written. With an empty PID, `lsof -nP -a -p "" -iTCP` listed every TCP socket on the host. That output is not retained here. The guarded retry above is the record.

The executor wrote the corrected configuration with the Write tool, ran `chmod 600` on it, and verified it:

```text
$ awk ... | sed 's/\$port/57143/' > <scratch>/expected/codex-interactive-config.toml && cmp ... && echo 'identical to corrected runbook heredoc with port 57143'; stat -c '%a %s %n' "$f"; cmp <(awk ... launch.sh heredoc) /private/tmp/bv01-228-codex-interactive/launch.sh && echo 'launch.sh identical to runbook'
identical to corrected runbook heredoc with port 57143
600 332 /private/tmp/bv01-228-codex-interactive/codex/config.toml
launch.sh identical to runbook

$ tmux -S /private/tmp/bv01-228-probe.tmux new-window -t bv01 -n codex-interactive 'sh /private/tmp/bv01-228-codex-interactive/launch.sh'
$ date; cat root.pid; ps ...; tmux ... list-windows ...
2026-09-28 17:25:32 EDT
80701
  PID  PPID STARTED                      COMMAND
80701 13952 Mon Sep 28 17:25:29 2026     sh /private/tmp/bv01-228-codex-interactive/launch.sh
0 anchor 13953
1 codex-interactive 80701

$ PYTHONSAFEPATH=1 mise exec -- uv run python experiments/02-host-socket-attribution/probe.py server /private/tmp/bv01-228-codex-interactive/gateway.sock 80701 1 > .../listener.jsonl 2> .../listener.err
2026-09-28 17:25:44 EDT
755 socket /private/tmp/bv01-228-codex-interactive/gateway.sock
(listener PID 83193 under uv PID 83179)
```

The executor wrote `go` at about 17:25:47 EDT. Codex then appended `[tui]` and `screen_reader_detection_done = true` to its own `codex/config.toml` ([after-run copy](codex-interactive/config-after-run.toml.raw)). The pane showed:

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; tmux -S /private/tmp/bv01-228-probe.tmux capture-pane -p -t bv01:codex-interactive | sed '/^[[:space:]]*$/d' | head -50; cat /private/tmp/bv01-228-codex-interactive/model.jsonl
2026-09-28 17:25:55 EDT
  Folder access
  /private/tmp/bv01-228-codex-interactive/workspace
  Trust this folder? Codex can read, edit, and run files here, subject to your
  permission settings. Folder settings can run code automatically, even
  without a model request. Continue only if you trust these files. Your trust
  decision will be saved.
› 1. Trust and continue
  2. Quit
  enter continue · esc quit
cat: /private/tmp/bv01-228-codex-interactive/model.jsonl: No such file or directory
```

**Observed: a folder trust prompt.** Under the runbook rule against answering a trust prompt, the executor entered nothing. **Classification: prompted (folder trust) before any model request. The socket-client prompt was never entered.** Because this cell stopped before session creation, whether it would hit the same sandbox helper failure as headless is unknown.

```text
$ ps -axo pid,ppid,command | awk '$1==80701 || $2==80701'
2026-09-28 17:26:01 EDT
80701 13952 codex -C /private/tmp/bv01-228-codex-interactive/workspace -c approval_policy=never
$ date; ps -o pid,ppid,command -p 80701,83193,76644; kill -TERM 80701 83193 76644
2026-09-28 17:26:05 EDT
(all three listed with the recorded commands)
$ date; ps -o pid,command -p 80701,83193,76644; tmux ... list-windows ...
2026-09-28 17:26:11 EDT
  PID COMMAND
0 anchor 13953
```

**Observed: outbound network requests from the Codex cells.** Codex's own log database in the disposable home, read with `sqlite3 -readonly`, records these requests from codex-interactive before the trust prompt was answered, or any prompt entered:

```text
$ sqlite3 -readonly /private/tmp/bv01-228-codex-interactive/codex/logs_2.sqlite "select feedback_log_body from logs;" | grep -oE '(method=[A-Z]+ )?url=[^ ]+|https?://[^ "]+ failed with status [0-9]+' | sort | uniq -c
      1 https://chatgpt.com/backend-api/plugins/featured?platform=codex failed with status 401
      1 method=GET url=https://api.github.com/repos/openai/codex/releases/latest
      1 method=GET url=https://raw.githubusercontent.com/openai/codex/main/announcement_tip.toml
```

Both the GitHub requests returned `200 OK`. The ChatGPT plugins request returned `401 Unauthorized`. **Inference:** no credential was available in the disposable home to authenticate it, but the request headers are not logged. Both Codex cells also ran `git` subprocesses that cloned into `codex/.tmp/plugins-clone-*`. In the interactive cell the clone completed into `codex/.tmp/plugins` at commit `5fd93af4cd0c623e020d0cc7e9ce178b4ac1f70f`. **Source-confirmed at `openai/codex@a6bd192`:** `codex-rs/core-plugins/src/startup_sync.rs` line 30 sets `OPENAI_PLUGINS_GIT_URL` to `https://github.com/openai/plugins.git`, and lines 389 and 433 use the `plugins-clone-` prefix. The runbook's approval covered a loopback model route only. These startup requests went to the public internet with no provider credential. They are recorded here as observed egress outside the approved loopback-only design. Egress from the Claude cells was not measured.

### Audit trace for the Codex cells

The restarted capture covers codex-headless attempt 2 (root 62657) and codex-interactive (root 80701). Attempt 1 (root 75591) ran before the restart, so its events are only in the replaced file. Descendants found through `ppid`:

```text
$ grep -E '"ppid":(62657|80701)[,}]' "$f" | jq -r '[.process.audit_token.pid, .process.ppid, .process.executable.path] | @tsv' | sort | uniq -c   (at 17:27:49 after the capture caught up)
codex-headless 62657: git 65504 (child git 65505), zsh 65507 (child /usr/libexec/path_helper 65508), zsh 65536, git 65557
codex-interactive 80701: git 85326 (child git 85328), git 85452, git 85464 (children git 85465, 85491, 85749, 85783), git 85798, git 86355, git 86379
```

The per-path summaries used the same `jq` form as the Claude cells, collapsing paths below `plugins*`, `git-*`, and `skills/.system`. **Observed:**

- Neither Codex root nor any descendant opened `~/.codex/config.toml`, `~/.codex/auth.json`, any other path under `~/.codex` except the installed package, anything under `~/.claude`, `~/.claude.json`, a keychain path, or 1Password.
- Both Codex processes opened `~/.codex/packages/standalone/releases/0.157.1-aarch64-apple-darwin/bin/codex` (flag 1), its parent `bin` directory, and `.../codex-package.json`. These are the executable and package metadata under the operator's real `~/.codex`, as prep.md predicted. They are not configuration.
- Both opened `~/.CFUserTextEncoding`, `~/.local/bin`, `/Library/Preferences/com.apple.networkd.plist`, and `/Library/Preferences/com.apple.security.plist`. codex-headless also opened `Security.framework/.../mdsDirectory.db`.
- Codex configuration was read only from `/private/tmp/bv01-228-<profile>/codex/config.toml` (7 opens in codex-headless and 10 in codex-interactive). All state and plugin clone writes stayed in the disposable `codex/` directories. codex-headless's zsh 65536 wrote `codex/shell_snapshots/<id>.tmp-<n>`.
- No Codex open outside `/private/tmp/bv01-228-*` with write intent was found. Paths in the operator's home were opened only with flag 1 (read) or as directories.

Configuration and keychain reads remain **unverified**, for the same limits stated for the Claude cells.

## Teardown of run processes

```text
$ date; tmux -S /private/tmp/bv01-228-probe.tmux list-windows -a -F '#{session_name}:#{window_index} #{window_name} #{pane_pid} #{pane_current_command}'
2026-09-28 17:27:24 EDT
bv01:0 anchor 13953 gsleep
$ tmux -S /private/tmp/bv01-228-probe.tmux kill-server
$ date; ps -o pid,command -p 13952,13953; ls -l /private/tmp/bv01-228-probe.tmux; pgrep -fl 'bv01-228|model_responder|probe.py' | grep -v -E 'eslogger|grep --line-buffered|shell-snapshots'; lsof -nP -U | grep -c 'bv01-228'; for p in 75591 767 14780 62657 80701 69931 77357 98791 3356 12732 16750 47561 64233 76644 83193; do ps -p $p -o pid= ; done
2026-09-28 17:27:30 EDT
  PID COMMAND
srw------- 1 tony wheel 0 Sep 28 17:19 /private/tmp/bv01-228-probe.tmux
0
$ if test -S /private/tmp/bv01-228-probe.tmux; then rm -- /private/tmp/bv01-228-probe.tmux; fi; ls -l /private/tmp/bv01-228-probe.tmux; find /private/tmp -maxdepth 1 -name 'bv01-228-*' -print | sort
ls: cannot access '/private/tmp/bv01-228-probe.tmux': No such file or directory
/private/tmp/bv01-228-claude-headless
/private/tmp/bv01-228-claude-interactive
/private/tmp/bv01-228-codex-headless
/private/tmp/bv01-228-codex-interactive
/private/tmp/bv01-228-pr-body.md
/private/tmp/bv01-228-review-check.raw
/private/tmp/bv01-228-review-focused.raw
/private/tmp/bv01-228-review-mutation.raw
/private/tmp/bv01-228-review-scan
```

**Observed:** no launch root, harness, responder, listener, or tmux process from this run remains. No Unix socket under a `bv01-228` path is open. The dedicated tmux server is stopped and its socket file removed. The homes remain for #242 and #243 and for operator review of the trace. Both capture pipelines (sudo 28387 with grep 28388, and sudo 36396 with grep 36397) are the operator's and were not touched. `/private/tmp/claude-501/-private-tmp-bv01-228-claude-headless-workspace/` is residue outside the homes, left for the operator.

## Case results for the integrated cells

No harness reached its Unix socket, so no listener recorded a kernel peer, and no integrated two-workload trace exists. Each cell stopped before its native shell tool ran.

| Cell | Result | Stop point |
| --- | --- | --- |
| codex-headless | blocked, `unsupported` as launched | Attempt 1: configuration rejected (runbook defect, since fixed). Attempt 2: filesystem sandbox helper exec denied (`sandbox-exec` exit 71) during session creation |
| codex-interactive | prompted | Folder trust prompt, not answered |
| claude-headless | `unsupported with fake key` | Responder rejected the startup requests (501, then 403). Claude reported a 403 authentication failure |
| claude-interactive | prompted, then `unsupported with fake key` | First-run theme prompt, not answered. Responder had already rejected a startup request (501) |

| Required case | Integrated-cell answer | Evidence |
| --- | --- | --- |
| 1. A descendants allowed, B rejected, shared tmux | Not reached in any cell. The fixture-only result from stage one stands. | This record, `listener.jsonl` files (all empty) |
| 2. Connecting process and relay | No cell reached its socket, and the trace doesn't show a harness connector or relay process | Same |
| 3. Exec, nested and detached children, parent exit, helpers | Not reached through the socket. The trace shows each harness's startup helpers. Claude runs `security`, `git`, `bash`, `node`/`npm`, and `ps`, while Codex runs `git` and `zsh`, and its `sandbox-exec` helper failed. | Audit sections above |
| 4. Stale launch records and churn | Not reached in integrated cells | None |
| 5. Descriptors, replacement, lifetime | Not reached in integrated cells | None |

This run completes no required case for an integrated cell. The recorded blockers are the Claude startup request shape against the responder, the Codex sandbox helper exec, and the two first-run prompts.

## Evidence files

Raw per-cell outputs are copied under [claude-headless](claude-headless/), [claude-interactive](claude-interactive/), [codex-headless](codex-headless/), and [codex-interactive](codex-interactive/). Each JSON and TOML output file carries a `.raw` suffix, which keeps the repository formatter from rewriting the recorded bytes. The two `settings.json.raw` files match the files in the homes byte for byte. Empty `listener.jsonl` and `listener.err` files record that no listener received a connection or wrote an error. The capture file, Codex databases, Claude `.claude.json`, and plugin clones are not copied. A `gitleaks dir --redact` scan of this directory found nothing, and the fake key literal appears only inside the recorded `sed` command. The repository end-of-file hook removed one trailing blank line from `codex-headless/attempt-1/harness.err`.

## Audit loss from the capture replacement

The coordinator reported that at about 17:21 EDT the operator re-ran the capture restart block by mistake, because the ask still showed it. The block ran `rm -f file-opens.json` and started a second capture (sudo PID 36396, grep PID 36397) into a new `file-opens.json`, created at 17:21:55 EDT. The 17:13 capture (sudo PID 28387, grep PID 28388) keeps writing into the deleted file. The operator stops the orphaned capture. The executor signalled neither capture.

Events from 17:13 to 17:21:55 EDT are gone from disk. That window covers three items:

- The second positive control (PID 46032 at 17:14:57 EDT). Its one matching line is kept only as the `jq` excerpt quoted in "Positive control, second attempt".
- The claude-headless cell (root 767, 17:18:49 to about 17:19:16 EDT) and the claude-interactive cell (root 14780, 17:20:00 to 17:20:31 EDT). The executor had saved only the summaries in "Audit trace for the Claude cells", read at 17:21:16 and 17:21:43 EDT. They cover child processes and per-path open counts with the username replaced by `~`. A separate `claude-501` directory listing was also saved. The executor copied the summaries but never the raw event lines. **The raw audit for both Claude cells is lost**, and the summaries are the only retained record.
- codex-headless attempt 1 (root 75591, 17:16:56 to about 17:17:11 EDT). The executor never summarized it. **Its audit is lost.** That attempt exited at config load before any model request, and attempt 2 covers the same cell in the new file.

The executor did not re-run the Claude cells. A rerun would meet the same responder rejection and leave another `claude-501` residue directory. It wouldn't reach the socket, so the integrated-cell outcome would be unchanged. The loss is recorded instead, and the operator can ask for a rerun if raw Claude events are needed for the trace review. The third positive control passed against the new file at 17:23:16 EDT, before codex-headless attempt 2 and codex-interactive launched. Both Codex cells' events are in the new file.

`/private/tmp/claude-501/-private-tmp-bv01-228-claude-headless-workspace/` is a finding: a claude-headless write outside the four approved homes. It is left in place for the operator's review and belongs on the teardown list.
