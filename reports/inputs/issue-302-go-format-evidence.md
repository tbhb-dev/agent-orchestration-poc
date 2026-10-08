# Go formatter file selection for issue 302

## Source and reproduction

The repository pins gofumpt 0.12.0 in `mise.toml`. `mise exec -- gofumpt -version` printed `v0.12.0 (go1.27.1)`. The [v0.12.0 README](https://github.com/mvdan/gofumpt/blob/v0.12.0/README.md) at commit `3e07e7e70ac93761d8e79ca0083a19e3d59f753d` documents directory input and explicit file input. This check used the pinned executable, not an installed global formatter.

Observed locally on 2026-10-08: with an invalid `bad.go` under an ignored `node_modules` directory, `/usr/bin/time -p mise exec -- gofumpt -l .` exited 2 after 1.74 seconds with `expected ')', found 'EOF'` from that file. The same fixture remained in place for `/usr/bin/time -p mise exec -- scripts/check-gofumpt.sh`, which exited 0 after 0.90 seconds, and `/usr/bin/time -p mise run fmt:go`, which exited 0 after 0.80 seconds. The fixture was removed after these commands. These times are single local runs and do not measure a live pnpm install.

The regression script `scripts/test-go-format.sh` checks that an untracked, nonignored Go file is detected and formatted while an ignored `node_modules` Go file stays untouched. `mise run check:go` passed on the changed worktree.

Observed during PR #305 review follow-up on 2026-10-08: a disposable Git repository with a staged Go file removed from the working tree caused the original `scripts/go-source-files.sh` to emit that missing path. The new regression failed with `deleted tracked Go file remained in the source inventory`. After filtering for existing files, `mise exec -- scripts/test-go-format.sh` passed; it now runs both the check and formatter against the unstaged deletion. This fixture covers a removed tracked file, not a concurrent deletion during formatting.

Verified after merging `origin/main`: `mise run check` passed in 203.60 seconds, `mise run check:shell` passed, and `mise run build` passed. A concurrent `mise run check:mutation` attempt stopped with a Gremlins panic; its isolated rerun completed Go mutation scoring with 97.32% efficacy while Python mutation scoring continued.

## Check timings

| Environment | Before | After |
| --- | --- | --- |
| Local formatter probe | Old directory walk 1.74 seconds, exit 2 | New check 0.90 seconds and format 0.80 seconds, both exit 0 |
| CI `check` job | [Main run 37730050520](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37730050520) on `e34c9ea` ran from 04:58:30 to 05:01:10 UTC, 160 seconds, success | [PR run 37733747527](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37733747527) ran from 05:43:56 to 05:47:10 UTC, 194 seconds, success. A later PR body edit triggered another successful `check` from 05:48:30 to 05:50:48 UTC, 138 seconds |
| Local `mise run check` | 516.32 seconds, exit 0, in a disposable detached worktree at `e34c9ea549a7f3a652cebb6eef5df95bc02023d2` | 495.28 seconds, exit 0, on the changed worktree at `f394732ac34fc2a3e5be610ec987a405f84b0de4` |

The CI and local full-check timings include more than formatting. They are single runs with different cache states and do not isolate formatter overhead. The local formatter probe measures only file selection and formatting.
