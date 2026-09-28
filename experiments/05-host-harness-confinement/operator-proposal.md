# Operator proposal for the managed host run

## Gate and target

**Proposed, not run:** launch four isolated Codex and Claude profiles against disposable A/B wrappers under `/private/tmp/bv02-242-managed/`. This would change temporary harness settings and exercise managed code with a fake provider responder. Operator direction requires a fresh proposal and authorization before that state change. The #228 fake-credential plan is a pattern only and does not authorize this run.

The target state is four clean homes, four independent workspaces, fixed per-profile settings, an A/B socket fixture, and a loopback model responder restricted to a local address. No global harness setting, agentd, local kit, trust store, live `cc-socks`, or default tmux server may be touched. The fixture must capture effective settings and launched process identity. It must record tool path and transport peer, then verify cleanup. No real provider credential may enter the environment.

## Exact setup and undo commands

The following setup is submitted for review and has not been executed. It deliberately stops before a harness launch because a reviewed scripted model responder and protocol-correct dummy queue/`cc-socks` targets do not yet exist in this experiment. The launch command set must be submitted with those artifacts before execution.

```sh
umask 077
test ! -e /private/tmp/bv02-242-managed || exit 1
mkdir -m 700 /private/tmp/bv02-242-managed
for name in codex-interactive codex-headless claude-interactive claude-headless; do mkdir -m 700 "/private/tmp/bv02-242-managed/$name" "/private/tmp/bv02-242-managed/$name/workspace" "/private/tmp/bv02-242-managed/$name/tmp" "/private/tmp/bv02-242-managed/$name/xdg"; done
for name in codex-interactive codex-headless; do mkdir -m 700 "/private/tmp/bv02-242-managed/$name/codex"; done
for name in claude-interactive claude-headless; do mkdir -m 700 "/private/tmp/bv02-242-managed/$name/claude"; done
find /private/tmp/bv02-242-managed -maxdepth 2 -type d -print
```

The undo targets only the literal disposable directory and a dedicated tmux socket. A later reviewed launch plan must specify every child PID for `SIGTERM` and verify it has exited before this removal.

```sh
tmux -S /private/tmp/bv02-242-managed.tmux kill-server
test -d /private/tmp/bv02-242-managed || exit 1
rm -r -- /private/tmp/bv02-242-managed
if test -e /private/tmp/bv02-242-managed.tmux; then rm -- /private/tmp/bv02-242-managed.tmux; fi
test ! -e /private/tmp/bv02-242-managed
test ! -e /private/tmp/bv02-242-managed.tmux
```

The `tmux` cleanup command is only applicable if the later interactive launch starts that dedicated server. Its expected nonzero exit when no server exists is not an instruction to touch another server. The unresolved responder and protocol targets block the managed run before its first attempt. The authorized run still needs all four profile cells. Native file tools and process control need separate attempts. Malicious project settings, sandbox startup failure, and M-001 also remain.
