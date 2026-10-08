# Go formatter file selection for issue 302

## Source and reproduction

The repository pins gofumpt 0.12.0 in `mise.toml`. `mise exec -- gofumpt -version` printed `v0.12.0 (go1.27.1)`. The [v0.12.0 README](https://github.com/mvdan/gofumpt/blob/v0.12.0/README.md) at commit `3e07e7e70ac93761d8e79ca0083a19e3d59f753d` documents directory input and explicit file input. This check used the pinned executable, not an installed global formatter.

Observed locally on 2026-10-08: with an invalid `bad.go` under an ignored `node_modules` directory, `/usr/bin/time -p mise exec -- gofumpt -l .` exited 2 after 1.74 seconds with `expected ')', found 'EOF'` from that file. The same fixture remained in place for `/usr/bin/time -p mise exec -- scripts/check-gofumpt.sh`, which exited 0 after 0.90 seconds, and `/usr/bin/time -p mise run fmt:go`, which exited 0 after 0.80 seconds. The fixture was removed after these commands. These times are single local runs and do not measure a live pnpm install.

The regression script `scripts/test-go-format.sh` checks that an untracked, nonignored Go file is detected and formatted while an ignored `node_modules` Go file stays untouched. `mise run check:go` passed on the changed worktree.

## Check timings

| Environment | Before | After |
| --- | --- | --- |
| Local formatter probe | Old directory walk 1.74 seconds, exit 2 | New check 0.90 seconds and format 0.80 seconds, both exit 0 |
| CI `check` job | [Main run 37730050520](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37730050520) on `e34c9ea` ran from 04:58:30 to 05:01:10 UTC, 160 seconds, success | Recorded in the pull request after its first CI run |
| Local `mise run check` | Not measured on a fixed prechange tree | 495.28 seconds, exit 0, on the changed worktree |

The CI baseline is a whole job, while the local probe measures only formatting. Differences between those timings do not isolate formatter overhead.
