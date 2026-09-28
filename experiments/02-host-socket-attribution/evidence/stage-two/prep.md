# BV-01 stage two preparation record

Raw executor notes for #228 stage two, preparation step only, under operator decision BV-20 (approved 2026-09-28 15:30). The executor was a Claude Code 2.1.284 subagent on model `claude-opus-5-5`, launched by the coordinator. Scope was the runbook's "Boundary and preflight" and "Disposable homes and trace" sections plus the per-cell harness files that don't depend on a responder port. No responder, listener, harness, tmux server, background process, or `sudo` command was started.

## Context

- Worktree: `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/exp-228-harness-stage-two`, branch `exp/228-harness-stage-two`, HEAD `cb7fdd7811f09a8ae5864ff40b9bb01ba34889d9` (main with the merged stage-one work).
- Difference from the runbook: the runbook says to run from `.worktrees/exp-228-host-harness-connectors`. The coordinator assigned this worktree instead. Both check out the same merged `probe.py` and package sources. The copied file hashes are recorded below.
- Difference from the pins: the runbook and `versions.md` pin Claude Code `2.1.283`. The installed Claude Code is `2.1.284`. The coordinator instructed the executor to record the difference and continue. Codex matches its pin at `codex-cli 0.157.1`.
- Excluded paths: `/private/tmp/bv01-228-pr-body.md` and `/private/tmp/bv01-228-review-*` are stage-one files, not homes. They match the `bv01-228-*` glob and were listed but not touched. The runbook's final teardown check `test -z "$(find /private/tmp -maxdepth 1 -name 'bv01-228-*' -print)"` will fail while they exist.
- Recording method: a helper printed each command as `$ <command>`, then its combined output and `[exit <status>]`.

## Boundary and preflight

Started 2026-09-28 15:32:29 EDT.

```text
$ pwd
/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees/exp-228-harness-stage-two
[exit 0]

$ date '+%Y-%m-%d %H:%M:%S %Z'
2026-09-28 15:32:29 EDT
[exit 0]

$ sw_vers
ProductName:		macOS
ProductVersion:		26.5.1
BuildVersion:		25F80
[exit 0]

$ uname -m
arm64
[exit 0]

$ codex --version
codex-cli 0.157.1
[exit 0]

$ claude --version
2.1.284 (Claude Code)
[exit 0]

$ git status --short
[exit 0]

$ for name in codex-interactive codex-headless claude-interactive claude-headless; do test ! -e "/private/tmp/bv01-228-$name" || { echo "exists: /private/tmp/bv01-228-$name"; exit 1; }; done; echo "all four homes absent"
all four homes absent
[exit 0]

$ find /private/tmp -maxdepth 1 -name 'bv01-228-*' -print | sort
/private/tmp/bv01-228-pr-body.md
/private/tmp/bv01-228-review-check.raw
/private/tmp/bv01-228-review-focused.raw
/private/tmp/bv01-228-review-mutation.raw
/private/tmp/bv01-228-review-scan
[exit 0]

$ command -v codex claude python3 uv mise
/Users/tony/.local/bin/codex
/Users/tony/.local/bin/claude
/Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3
/Users/tony/.local/share/mise/installs/uv/0.12.10/uv-aarch64-apple-darwin/uv
mise
[exit 0]

$ mise exec -- python --version
Python 3.14.6
[exit 0]

$ mise exec -- uv --version
uv 0.12.10 (3c979abda 2026-09-04 aarch64-apple-darwin)
[exit 0]

$ env -i PATH=/Users/tony/.local/bin:/Users/tony/.local/share/mise/installs/python/3.14.6/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin sh -c 'command -v codex claude python3'
/Users/tony/.local/bin/codex
/Users/tony/.local/bin/claude
/Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3
[exit 0]

$ /Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3 --version
Python 3.14.6
[exit 0]

$ ls -l /Users/tony/.local/bin/claude /Users/tony/.local/bin/codex 2>&1; ls -l $(command -v codex) $(command -v claude)
lrwxr-xr-x 1 tony staff 48 Sep 28 14:19 /Users/tony/.local/bin/claude -> /Users/tony/.local/share/claude/versions/2.1.284
lrwxr-xr-x 1 tony staff 56 Sep 26 09:59 /Users/tony/.local/bin/codex -> /Users/tony/.codex/packages/standalone/current/bin/codex
lrwxr-xr-x 1 tony staff 48 Sep 28 14:19 /Users/tony/.local/bin/claude -> /Users/tony/.local/share/claude/versions/2.1.284
lrwxr-xr-x 1 tony staff 56 Sep 26 09:59 /Users/tony/.local/bin/codex -> /Users/tony/.codex/packages/standalone/current/bin/codex
[exit 0]

$ git rev-parse HEAD
cb7fdd7811f09a8ae5864ff40b9bb01ba34889d9
[exit 0]
```

**Observed:** the fixed launch `PATH` resolves `codex`, `claude`, and `python3` to the same paths as the executor shell. **Observed:** the `claude` link was updated at 14:19 today to `versions/2.1.284`. **Observed:** the `codex` link target lies under the operator's `~/.codex/packages/standalone/current/bin/`. Only the link in `~/.local/bin` was listed. Nothing under `~/.codex` was read. **Inference:** every Codex launch executes a binary stored under `~/.codex`, so the file-open audit will likely show loader or package opens under that directory. Those opens are not configuration reads by themselves and need separate classification during trace review.

## Disposable homes and trace

Started 2026-09-28 15:32:44 EDT. All commands ran in one shell after `umask 077`.

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'
2026-09-28 15:32:44 EDT
[exit 0]

$ umask 077
[exit 0]

$ umask
077
[exit 0]

$ for name in codex-interactive codex-headless claude-interactive claude-headless; do mkdir -m 700 "/private/tmp/bv01-228-$name"; mkdir -m 700 "/private/tmp/bv01-228-$name/tmp" "/private/tmp/bv01-228-$name/xdg" "/private/tmp/bv01-228-$name/workspace"; done
[exit 0]

$ for name in codex-interactive codex-headless; do mkdir -m 700 "/private/tmp/bv01-228-$name/codex"; done
[exit 0]

$ for name in claude-interactive claude-headless; do mkdir -m 700 "/private/tmp/bv01-228-$name/claude"; done
[exit 0]

$ for name in codex-interactive codex-headless claude-interactive claude-headless; do stat -c '%a %n' "/private/tmp/bv01-228-$name"; done
700 /private/tmp/bv01-228-codex-interactive
700 /private/tmp/bv01-228-codex-headless
700 /private/tmp/bv01-228-claude-interactive
700 /private/tmp/bv01-228-claude-headless
[exit 0]

$ for name in codex-interactive codex-headless claude-interactive claude-headless; do mkdir -p "/private/tmp/bv01-228-$name/workspace/experiments/02-host-socket-attribution" "/private/tmp/bv01-228-$name/workspace/agent_orchestration_poc/core"; cp experiments/02-host-socket-attribution/probe.py "/private/tmp/bv01-228-$name/workspace/experiments/02-host-socket-attribution/probe.py"; cp src/agent_orchestration_poc/__init__.py "/private/tmp/bv01-228-$name/workspace/agent_orchestration_poc/__init__.py"; cp src/agent_orchestration_poc/core/__init__.py src/agent_orchestration_poc/core/host_socket_attribution.py "/private/tmp/bv01-228-$name/workspace/agent_orchestration_poc/core/"; done
[exit 0]

$ for name in codex-interactive codex-headless claude-interactive claude-headless; do sha256sum "/private/tmp/bv01-228-$name/workspace/experiments/02-host-socket-attribution/probe.py" "/private/tmp/bv01-228-$name/workspace/agent_orchestration_poc/core/host_socket_attribution.py"; done
783c711f9bc2806b943cee6170d7fce2be2e37e4d95571bdbf2218490a2820e0  /private/tmp/bv01-228-codex-interactive/workspace/experiments/02-host-socket-attribution/probe.py
ad8de2891c07921d177d3d6643477e3388ab1274aee54d803e3081b202cee1ab  /private/tmp/bv01-228-codex-interactive/workspace/agent_orchestration_poc/core/host_socket_attribution.py
783c711f9bc2806b943cee6170d7fce2be2e37e4d95571bdbf2218490a2820e0  /private/tmp/bv01-228-codex-headless/workspace/experiments/02-host-socket-attribution/probe.py
ad8de2891c07921d177d3d6643477e3388ab1274aee54d803e3081b202cee1ab  /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/core/host_socket_attribution.py
783c711f9bc2806b943cee6170d7fce2be2e37e4d95571bdbf2218490a2820e0  /private/tmp/bv01-228-claude-interactive/workspace/experiments/02-host-socket-attribution/probe.py
ad8de2891c07921d177d3d6643477e3388ab1274aee54d803e3081b202cee1ab  /private/tmp/bv01-228-claude-interactive/workspace/agent_orchestration_poc/core/host_socket_attribution.py
783c711f9bc2806b943cee6170d7fce2be2e37e4d95571bdbf2218490a2820e0  /private/tmp/bv01-228-claude-headless/workspace/experiments/02-host-socket-attribution/probe.py
ad8de2891c07921d177d3d6643477e3388ab1274aee54d803e3081b202cee1ab  /private/tmp/bv01-228-claude-headless/workspace/agent_orchestration_poc/core/host_socket_attribution.py
[exit 0]

$ sha256sum experiments/02-host-socket-attribution/probe.py src/agent_orchestration_poc/__init__.py src/agent_orchestration_poc/core/__init__.py src/agent_orchestration_poc/core/host_socket_attribution.py
783c711f9bc2806b943cee6170d7fce2be2e37e4d95571bdbf2218490a2820e0  experiments/02-host-socket-attribution/probe.py
958483316cd1a90c611970888bd20fc4a749877c05b28d619988a566ffd7567a  src/agent_orchestration_poc/__init__.py
af047bc1594c80fd0fd4e89683c847e601920626866f01a0e73b79990ccf21c9  src/agent_orchestration_poc/core/__init__.py
ad8de2891c07921d177d3d6643477e3388ab1274aee54d803e3081b202cee1ab  src/agent_orchestration_poc/core/host_socket_attribution.py
[exit 0]

$ for name in codex-interactive codex-headless claude-interactive claude-headless; do sha256sum "/private/tmp/bv01-228-$name/workspace/agent_orchestration_poc/__init__.py" "/private/tmp/bv01-228-$name/workspace/agent_orchestration_poc/core/__init__.py"; done
958483316cd1a90c611970888bd20fc4a749877c05b28d619988a566ffd7567a  /private/tmp/bv01-228-codex-interactive/workspace/agent_orchestration_poc/__init__.py
af047bc1594c80fd0fd4e89683c847e601920626866f01a0e73b79990ccf21c9  /private/tmp/bv01-228-codex-interactive/workspace/agent_orchestration_poc/core/__init__.py
958483316cd1a90c611970888bd20fc4a749877c05b28d619988a566ffd7567a  /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/__init__.py
af047bc1594c80fd0fd4e89683c847e601920626866f01a0e73b79990ccf21c9  /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/core/__init__.py
958483316cd1a90c611970888bd20fc4a749877c05b28d619988a566ffd7567a  /private/tmp/bv01-228-claude-interactive/workspace/agent_orchestration_poc/__init__.py
af047bc1594c80fd0fd4e89683c847e601920626866f01a0e73b79990ccf21c9  /private/tmp/bv01-228-claude-interactive/workspace/agent_orchestration_poc/core/__init__.py
958483316cd1a90c611970888bd20fc4a749877c05b28d619988a566ffd7567a  /private/tmp/bv01-228-claude-headless/workspace/agent_orchestration_poc/__init__.py
af047bc1594c80fd0fd4e89683c847e601920626866f01a0e73b79990ccf21c9  /private/tmp/bv01-228-claude-headless/workspace/agent_orchestration_poc/core/__init__.py
[exit 0]

$ for name in codex-interactive codex-headless claude-interactive claude-headless; do find "/private/tmp/bv01-228-$name" -exec stat -c '%a %U %F %n' {} + | sort -k4; done
700 tony directory /private/tmp/bv01-228-codex-interactive
700 tony directory /private/tmp/bv01-228-codex-interactive/codex
700 tony directory /private/tmp/bv01-228-codex-interactive/tmp
700 tony directory /private/tmp/bv01-228-codex-interactive/workspace
700 tony directory /private/tmp/bv01-228-codex-interactive/workspace/agent_orchestration_poc
700 tony directory /private/tmp/bv01-228-codex-interactive/workspace/agent_orchestration_poc/core
700 tony directory /private/tmp/bv01-228-codex-interactive/workspace/experiments
700 tony directory /private/tmp/bv01-228-codex-interactive/workspace/experiments/02-host-socket-attribution
700 tony directory /private/tmp/bv01-228-codex-interactive/xdg
600 tony regular file /private/tmp/bv01-228-codex-interactive/workspace/agent_orchestration_poc/__init__.py
600 tony regular file /private/tmp/bv01-228-codex-interactive/workspace/agent_orchestration_poc/core/__init__.py
600 tony regular file /private/tmp/bv01-228-codex-interactive/workspace/agent_orchestration_poc/core/host_socket_attribution.py
600 tony regular file /private/tmp/bv01-228-codex-interactive/workspace/experiments/02-host-socket-attribution/probe.py
700 tony directory /private/tmp/bv01-228-codex-headless
700 tony directory /private/tmp/bv01-228-codex-headless/codex
700 tony directory /private/tmp/bv01-228-codex-headless/tmp
700 tony directory /private/tmp/bv01-228-codex-headless/workspace
700 tony directory /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc
700 tony directory /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/core
700 tony directory /private/tmp/bv01-228-codex-headless/workspace/experiments
700 tony directory /private/tmp/bv01-228-codex-headless/workspace/experiments/02-host-socket-attribution
700 tony directory /private/tmp/bv01-228-codex-headless/xdg
600 tony regular file /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/__init__.py
600 tony regular file /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/core/__init__.py
600 tony regular file /private/tmp/bv01-228-codex-headless/workspace/agent_orchestration_poc/core/host_socket_attribution.py
600 tony regular file /private/tmp/bv01-228-codex-headless/workspace/experiments/02-host-socket-attribution/probe.py
700 tony directory /private/tmp/bv01-228-claude-interactive
700 tony directory /private/tmp/bv01-228-claude-interactive/claude
700 tony directory /private/tmp/bv01-228-claude-interactive/tmp
700 tony directory /private/tmp/bv01-228-claude-interactive/workspace
700 tony directory /private/tmp/bv01-228-claude-interactive/workspace/agent_orchestration_poc
700 tony directory /private/tmp/bv01-228-claude-interactive/workspace/agent_orchestration_poc/core
700 tony directory /private/tmp/bv01-228-claude-interactive/workspace/experiments
700 tony directory /private/tmp/bv01-228-claude-interactive/workspace/experiments/02-host-socket-attribution
700 tony directory /private/tmp/bv01-228-claude-interactive/xdg
600 tony regular file /private/tmp/bv01-228-claude-interactive/workspace/agent_orchestration_poc/__init__.py
600 tony regular file /private/tmp/bv01-228-claude-interactive/workspace/agent_orchestration_poc/core/__init__.py
600 tony regular file /private/tmp/bv01-228-claude-interactive/workspace/agent_orchestration_poc/core/host_socket_attribution.py
600 tony regular file /private/tmp/bv01-228-claude-interactive/workspace/experiments/02-host-socket-attribution/probe.py
700 tony directory /private/tmp/bv01-228-claude-headless
700 tony directory /private/tmp/bv01-228-claude-headless/claude
700 tony directory /private/tmp/bv01-228-claude-headless/tmp
700 tony directory /private/tmp/bv01-228-claude-headless/workspace
700 tony directory /private/tmp/bv01-228-claude-headless/workspace/agent_orchestration_poc
700 tony directory /private/tmp/bv01-228-claude-headless/workspace/agent_orchestration_poc/core
700 tony directory /private/tmp/bv01-228-claude-headless/workspace/experiments
700 tony directory /private/tmp/bv01-228-claude-headless/workspace/experiments/02-host-socket-attribution
700 tony directory /private/tmp/bv01-228-claude-headless/xdg
600 tony regular file /private/tmp/bv01-228-claude-headless/workspace/agent_orchestration_poc/__init__.py
600 tony regular file /private/tmp/bv01-228-claude-headless/workspace/agent_orchestration_poc/core/__init__.py
600 tony regular file /private/tmp/bv01-228-claude-headless/workspace/agent_orchestration_poc/core/host_socket_attribution.py
600 tony regular file /private/tmp/bv01-228-claude-headless/workspace/experiments/02-host-socket-attribution/probe.py
[exit 0]
```

**Verified:** each copied file's SHA-256 matches its source in this worktree at `cb7fdd7`. **Observed:** all directories are mode 700 and all copied files mode 600, owned by `tony`.

## Per-cell harness files

**Blocked by permissions:** the executor did not write the harness files that don't depend on a responder port. The first attempt, at about 15:34 EDT, was one shell that set `umask 077` and wrote five heredocs, each followed by `echo "[exit $?] <file>"`. A repository hook rejected it before execution because of the trailing exit-status echoes. The retry removed the echoes and added `set -e`. The Claude Code auto mode classifier then denied it before execution with this message:

```text
Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Create Unsafe Agents].
```

The denied command was exactly the runbook's heredoc text for these five files, prefixed by `set -e; umask 077; date '+%Y-%m-%d %H:%M:%S %Z'`:

- `/private/tmp/bv01-228-claude-headless/settings.json`, from the runbook's "Per-cell setup" Claude block.
- `/private/tmp/bv01-228-claude-interactive/settings.json`, from the same block.
- `/private/tmp/bv01-228-codex-interactive/launch.sh`, from "Launch barrier and listener".
- `/private/tmp/bv01-228-claude-interactive/launch.sh`, from the same section.
- `/private/tmp/bv01-228-claude-headless/launch.sh`, from the same section.

Per the dispatch rule, the executor stopped this step without trying another method. A check at 15:35:14 EDT confirmed that no file had been written. Each home contained only its `codex` or `claude`, `tmp`, `workspace`, and `xdg` directories:

```text
$ for name in codex-interactive codex-headless claude-interactive claude-headless; do find "/private/tmp/bv01-228-$name" -maxdepth 1 -exec stat -c '%a %F %n' {} + | sort -k3; done
700 directory /private/tmp/bv01-228-codex-interactive
700 directory /private/tmp/bv01-228-codex-interactive/codex
700 directory /private/tmp/bv01-228-codex-interactive/tmp
700 directory /private/tmp/bv01-228-codex-interactive/workspace
700 directory /private/tmp/bv01-228-codex-interactive/xdg
700 directory /private/tmp/bv01-228-codex-headless
700 directory /private/tmp/bv01-228-codex-headless/codex
700 directory /private/tmp/bv01-228-codex-headless/tmp
700 directory /private/tmp/bv01-228-codex-headless/workspace
700 directory /private/tmp/bv01-228-codex-headless/xdg
700 directory /private/tmp/bv01-228-claude-interactive
700 directory /private/tmp/bv01-228-claude-interactive/claude
700 directory /private/tmp/bv01-228-claude-interactive/tmp
700 directory /private/tmp/bv01-228-claude-interactive/workspace
700 directory /private/tmp/bv01-228-claude-interactive/xdg
700 directory /private/tmp/bv01-228-claude-headless
700 directory /private/tmp/bv01-228-claude-headless/claude
700 directory /private/tmp/bv01-228-claude-headless/tmp
700 directory /private/tmp/bv01-228-claude-headless/workspace
700 directory /private/tmp/bv01-228-claude-headless/xdg
[exit 0]
```

Files that wait for a responder port regardless of the denial:

- `/private/tmp/bv01-228-codex-headless/codex/config.toml` needs `$port` in `base_url`.
- `/private/tmp/bv01-228-codex-interactive/codex/config.toml` needs `$port` in `base_url`.
- Codex headless has no launch file. Its wrapper is the inline `sh -c` command in "Launch barrier and listener", run at launch time.
- Each Claude `launch.sh` reads the port from `model-port` at run time. Each `model-port` file comes from that cell's responder startup.

## Process state at stop

```text
$ date '+%Y-%m-%d %H:%M:%S %Z'; pgrep -fl 'bv01-228|model_responder|probe.py' ; echo "pgrep status $?"; test -e /private/tmp/bv01-228-probe.tmux && echo "tmux socket present" || echo "no dedicated tmux socket"
2026-09-28 15:35:59 EDT
pgrep status 1
no dedicated tmux socket
```

**Observed:** no responder, listener, probe, or harness process was running, and the dedicated tmux socket did not exist. The default tmux server and session `0` were never addressed.

## Audit command check

The root command in the approved ledger is `sudo /usr/bin/opensnoop -F -e -s > /private/tmp/bv01-228-codex-headless/file-opens.raw 2> /private/tmp/bv01-228-codex-headless/file-opens.err &`. It matches `file-open-audit.md` line 10 character for character. The runbook's "Disposable homes and trace" section refers to the audit without restating the command. Its target directory `/private/tmp/bv01-228-codex-headless` now exists with mode 700.

**Schema, from the installed `/usr/bin/opensnoop` script (ver 1.60, read with `grep` and `sed`):** `-F` prints the open flags, `-e` prints errno, and `-s` prints a microsecond timestamp. With these options each line contains `TIME UID PID COMM FD FLAGS ERR PATH`. It omits PPID and arguments. Descendant attribution depends on the separately recorded PIDs. The D program probes only `syscall::open`, `syscall::open_nocancel`, and `syscall::open_extended`. The script has no `openat` probe, and `grep -c openat /usr/bin/opensnoop` returned 0.

**Inference, untested:** an open made through `openat` or `openat_nocancel` doesn't produce a line. A clean trace says nothing about opens a harness or its runtime makes with those calls. The missing `openat` probe adds to the inherited-descriptor and memory-map limits in `file-open-audit.md`.

**Inference:** the operator's unprivileged shell performs the `>` and `2>` redirections, so `file-opens.raw` and `file-opens.err` will be owned by `tony`. Running `sudo` in the background cannot prompt for a password, so credentials should be cached with `sudo -v` first. `audit_pid=$!` records the `sudo` PID. **Documented in sudo(8) for Sudo 1.9.17p2, "Signal handling":** when the command runs as a child of `sudo`, `sudo` relays the signals it receives to that command. **Untested:** whether the ledger's unprivileged `kill -TERM "$audit_pid"` is permitted against the root `sudo` process, or whether the operator needs `sudo kill -TERM "$audit_pid"`.
