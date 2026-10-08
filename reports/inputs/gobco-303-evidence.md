# Go branch coverage stall evidence

## Source and reproduction

Documented: Gobco 1.3.4 is pinned in `mise.toml`. The versioned source is `github.com/rillig/gobco` commit `4c9ea04be46fdf4ee7d40f7bba782f83d0397731`, recorded in `research/gates/testing/coverage-branches-87.md`. Its `main.go` calls `copyDir` on the module root for every package, and its `util.go` walks and copies every regular file without an ignore filter. It then runs `go test` in that copy. The source was read from `/Users/tony/go/pkg/mod/github.com/rillig/gobco@v1.3.4` in this run.

Observed: `ls /Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.worktrees | wc -l` reported 282 entries on 2026-10-08. The repository's prior worker reports in `reports/inputs/process-incident-evidence.md` and `reports/inputs/workflow-forms-evidence.md` record local gobco runs that remained silent for several minutes, including one interrupted after more than ten minutes. The source behavior and checkout layout explain how a module-root copy can spend time on worktrees and generated dependencies, though no process trace from the original #298 run was available.

Verified reproduction: A disposable module under `/private/tmp` contained a Go core file and an ignored `.worktrees/worker/sentinel.txt`. Running pinned `gobco -branch -keep` on its core package exited 0 in 1.41 seconds. Inspection of gobco's retained module copy found the sentinel, confirming that gobco copies unrelated ignored worktree content before testing. The fixture was removed by Python's `TemporaryDirectory` cleanup.

## Local timings

Observed before: `/usr/bin/time -p mise exec -- gobco -branch internal/core/relay` in this worktree exited 0 with `34/38` branches and `real 11.45` seconds. This worktree had not yet created its Python virtual environment, so it does not reproduce the large checkout layout from earlier reports.

Verified after: a timed `mise exec -- uv run python -c` call staged `go.mod`, `go.sum`, and `internal/core`, then called `run_gobco` for `internal/core/relay`. It exited 0 with `34/38` branches and `real 6.25` seconds. The measurement includes the temporary staging step and the Python launcher.

Verified after: `/usr/bin/time -p mise run check:coverage` exited 0 in `real 412.85` seconds. It ran 995 Python integration tests in 330.64 seconds, then the Go statement tests and all six staged gobco packages. Go branch coverage was 94.74 percent. The new shell runner had full line and branch coverage in that test run. The synthetic stalled-child test exited through the `0.1s` deadline, and the success and nonzero-exit tests passed.

Verified after: `/usr/bin/time -p mise run -j 1 check` exited 0 in `real 526.12` seconds. Its regular Python suite had 870 passes and 125 expected integration skips, its integration coverage suite had 995 passes, and its Go branch gate again reported 94.74 percent. The serial invocation avoids concurrent repository writes from independent check tasks.

## CI timings

Observed before: [main push run 37730050520](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37730050520) started its successful `check` job at 2026-10-08 04:58:30 UTC and completed at 05:01:10 UTC, or 160 seconds. [Pull request run 37731242535](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37731242535) completed its successful `check` job in 175 seconds, from 05:12:52 to 05:15:47 UTC. These whole-job times are reference points, not gobco-only measurements.

CI after: pending the issue #303 pull request run.
