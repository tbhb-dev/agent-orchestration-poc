---
title: Shell conventions
description: Interpreter, portability, hook, userland, and tooling rules for repository shell scripts.
---

## Versions and scope

The [shell research gate](https://github.com/tbhb/agent-orchestration-poc/tree/main/research/gates/shell) was run on 2026-09-26 for issue #30. The host has Apple Bash 3.2.57 and zsh 5.9. Bash 5.3.0 was built from its release source in a temporary directory for comparison. Fish 4.0.8 was read from source but was not installed or run. `research/gates/shell/versions.md` records executable versions, source commits, and clone paths, while `research/gates/shell/notes.md` records probes and evidence labels.

Current repository scripts under `scripts/` use `#!/usr/bin/env sh`. Keep that shebang for scripts that need to run on both the host and the Linux agent image. Choose Bash explicitly for a script that needs Bash features and test it under both `/bin/bash` 3.2 and the image's pinned Bash before calling it host compatible. A script intended only for the image may require Bash 5, with that scope stated next to its entrypoint.

Use shell scripts to start processes and access files. Put decisions and substantial transformations in a pure function in Go or Python. Pass data between commands with explicit arguments or a defined input format, and split a script when its interpreter or failure path becomes hard to follow.

## Bash compatibility

Do not use associative arrays, `mapfile`, `${var,,}`, `wait -n`, `coproc`, `local -n`, `printf '%(...)T'`, `globstar`, or `lastpipe` in host-compatible scripts. The Bash 3.2 probes rejected each of them, while the source-built Bash 5.3 accepted them (research/gates/shell/notes.md, Bash section). An indexed array is available in Bash 3.2, but an empty `"${array[@]}"` expansion under `set -u` fails there and succeeds on Bash 5.3. Check an array's state before expansion or use positional parameters for a small argument list.

Process substitution works in both tested Bash versions, but is not POSIX `sh` syntax. Use a redirection or a temporary file in a `sh` script. Bash 5 `lastpipe` can make a final pipeline stage run in the current shell when job control is off, while Bash 3.2 does not offer the option. Redirect input into a loop if it must update a variable in the caller.

Use `set -eu` in a POSIX script where its failure behavior has been checked, and use `set -o pipefail` only under an explicit Bash or zsh interpreter. `set -e` does not exit for a failed command inside a function called as an `if` condition. A pipeline reports only its last command's status without `pipefail`. Handle an expected failure with an explicit `if` and test the command status at the point it matters. These behaviors were verified on both tested Bash versions (research/gates/shell/notes.md, Bash section).

## Hook command interpreters

The harness assessment records three different command paths at its pinned versions. Claude Code command hooks expose a `bash` or `powershell` shell choice and support an `args` form without a shell. Codex CLI 0.157.1 runs command hooks through `$SHELL -lc`, which is `/bin/zsh -lc` on the assessed host. agy 1.2.10 uses `sh -c` on Unix (`experiments/00-system-assessment/harness-research.md`, hook sections). These are versioned findings, so check the active harness before changing hook configuration.

Put nontrivial hook logic in an executable file with an explicit shebang, and have the hook command invoke that file by path. Keep any inline command valid for the harness's actual command interpreter. Give arguments as separate values when the harness supports an exec form. Do not depend on the operator's interactive shell startup files or aliases in a hook.

With `zsh -lc`, an unquoted scalar such as `$x` stays one argument by default, an unmatched glob fails before the command runs, and arrays start at index one. `setopt SH_WORD_SPLIT`, `NONOMATCH`, or `KSH_ARRAYS` can change those behaviors, but a hook should select its interpreter rather than modify the caller's options. The zsh 5.9 probes and versioned `options.yo` source are in the gate notes.

Fish uses its own syntax, with `set` for variables, `$argv` for arguments, `$status` for the last command's status, and failing unmatched globs. Fish was read from its 4.0.8 documentation only because it is missing on the host. A fish user can invoke an executable hook script, but fish syntax must not be embedded in a `sh -c`, Bash, or zsh hook command.

## Userland and quoting

This Mac places GNU `sed`, coreutils, findutils, and awk first on PATH. A stock Mac or a harness with a different PATH can select BSD commands. The local probes showed that GNU `date -d`, `stat -c`, `head -n -1`, and `find -printf` are rejected by the Apple commands. Apple `sed -i` requires an extension argument. Use shared flags in scripts that run on macOS and Linux, or detect the selected tool and test both branches. The developer's GNU-first host convention applies to ad hoc commands here, while repository scripts must work in their stated targets.

Quote path and user-data expansions. Use `printf '%s\n'` instead of `echo` for data, `IFS= read -r` for line input, and `--` where the called program supports it. Do not parse `ls` output. Treat newline-delimited `xargs` input as a format with a known filename limit. The existing `xargs -r` calls were observed to work with the tested Apple and GNU tools, but they are not a general POSIX guarantee.

## Checks and exemptions

ShellCheck 0.11.0 checks the current `scripts/*.sh` files at `--severity=style`. shfmt 3.14.0 checks them with `-d -i 4 -ci`. Both versions are pinned in `mise.toml`, run in `mise run check:shell`, and are part of `mise run check` and the prek hooks. `mise run fmt:shell` applies the formatter. The [tooling decision](/decisions/0005-shell-tooling/) records the choice. Add new hook and image script paths to the gate and prek matcher when they are introduced.

ShellCheck follows the declared shell dialect for portability findings, but it does not analyze zsh or fish semantics. shfmt can format zsh but does not check behavior. Test interpreter selection, external commands, GNU and BSD flags, process failures, and hook JSON on the target host and image when writing hooks.
