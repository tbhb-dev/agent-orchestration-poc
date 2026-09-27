---
paths: ["scripts/*.sh", "scripts/**/*.sh", "images/agent/**", ".claude/hooks/**", ".codex/hooks/**", "**/*.bash", "**/*.zsh", "**/*.fish"]
---

Read [Shell conventions](../../docs/src/content/docs/guides/shell-conventions.md) before editing a shell script or hook command.

## Interpreter

- Keep `#!/usr/bin/env sh` scripts POSIX compatible. Choose an explicit Bash shebang for Bash features and state whether the script must run on macOS Bash 3.2 or only Bash 5 in the agent image.
- Put hook logic in a script with a shebang. At the assessed versions, Claude Code command hooks select Bash or PowerShell, Codex command hooks use `$SHELL -lc`, and agy command hooks use `sh -c`. Verify a changed harness before relying on that behavior.
- Do not use fish syntax in a `sh -c`, Bash, or zsh command. Fish is not installed on the assessed host.

## Portability and errors

- In host-compatible scripts, avoid associative arrays, `mapfile`, `${var,,}`, `wait -n`, `coproc`, `local -n`, `printf '%(...)T'`, `globstar`, and `lastpipe`. Guard empty indexed-array expansion under `set -u` on Bash 3.2.
- Keep process substitution out of `sh` scripts. Redirect a loop's input when it must update the caller's variables. Do not expect pipeline assignments to persist.
- Use explicit `if` checks for expected failures. `set -e` has conditional-context exceptions. Use `pipefail` only when the selected interpreter supports it.
- Quote data expansions and test globs before use. zsh defaults to no scalar word splitting, failing unmatched globs, and one-based arrays. Do not depend on `setopt` changes in a hook's calling shell.
- Write scripts for both GNU and BSD userland when they run on Mac and Linux. Avoid GNU-only `date -d`, `stat -c`, `head -n -1`, `find -printf`, and unqualified `sed -i` in those scripts.
- Use shell for process and file I/O, and put substantial decisions and transformations in a pure Go or Python function.

## Tooling

- Run `mise run check:shell` for ShellCheck 0.11.0 and shfmt 3.14.0. Use `mise run fmt:shell` to format current repository scripts, then inspect the diff.
- Add new hook or agent-image shell paths to `check:shell` and prek when the files arrive. Give each ShellCheck suppression a specific rule code and an adjacent reason. Do not suppress the whole file.
