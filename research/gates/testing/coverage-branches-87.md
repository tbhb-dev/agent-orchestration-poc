# Go branch coverage research for issue 87

Recorded 2026-09-26 with Go 1.27.1 on darwin/arm64. Source clones live under `/tmp` because the sandbox does not permit writing to `~/Code/github.com`. The versions below are the commits read, and the trial used the pinned v1.3.4 source rather than the repository HEAD.

## Sources and versions

| Source | Path and commit read | Evidence |
| --- | --- | --- |
| `rillig/gobco` v1.3.4 | `/tmp/coverage-87-gobco` at `4c9ea04be46fdf4ee7d40f7bba782f83d0397731` | [README](https://github.com/rillig/gobco/blob/4c9ea04be46fdf4ee7d40f7bba782f83d0397731/README.md), [instrumenter](https://github.com/rillig/gobco/blob/4c9ea04be46fdf4ee7d40f7bba782f83d0397731/instrumenter.go), [v1.3.4 release commit](https://github.com/rillig/gobco/commit/4c9ea04be46fdf4ee7d40f7bba782f83d0397731) |
| `rillig/gobco` HEAD, comparison | same clone, initially `7a099954a61f3955163d5cef03e884c2e72622dd` | [source](https://github.com/rillig/gobco/tree/7a099954a61f3955163d5cef03e884c2e72622dd) |
| `junhwi/gobco` | `/tmp/coverage-87-gobco-legacy` at `c015e3f3de351ad5e6b91893ec1f2bbef5102668` | [README](https://github.com/junhwi/gobco/blob/c015e3f3de351ad5e6b91893ec1f2bbef5102668/README.md) |
| Go cover | `~/Code/github.com/golang/go` at `862c888e612ac346c7c4d99c9392bdfd265f33b0` from the existing Go research gate | [coverage integration guide](https://go.dev/doc/build-cover), `research/gates/go/versions.md` |
| `srvgit/gocove` | clone attempted at `/tmp/coverage-87-gocove`, no commit available | `git clone https://github.com/srvgit/gocove.git` returned `Repository not found` |

## Comparison and decision

Documented: Go's `go test -coverprofile` records statement blocks and integrates with package tests, but it does not report source branch outcomes (`go help testflag`, `go tool cover`, [Go coverage guide](https://go.dev/doc/build-cover)). It remains the statement gate and records zero-hit blocks in packages with no test files.

Verified: `rillig/gobco` v1.3.4 instruments boolean branch expressions, supports `-branch`, and reports `Branch coverage: covered/total` (`main.go`, `instrumenter.go`). Its v1.3.4 release commit follows a fix for instrumentation of types derived from `bool`. The project has version tags but no separate release-note file. Its README says it misses `select` branches and unused functions without conditions. It accepts one package at a time, so the gate runs each core package and adds the counts in a pure function.

Observed: Building v1.3.4 with Go 1.27.1 and running `gobco -branch` on `internal/core/subject` completed with `Branch coverage: 6/6`. The same command after skipping the new `internal/core/command` tests reported an aggregate 75%, so a 90% gate detects an untested decision path. The observed trial does not establish compatibility with future Go syntax or all core packages.

Verified: `junhwi/gobco` requires every target package to add a `TestMain`, calls `go test` with `-toolexec`, and last committed its v0.1 README in 2020. This would add test harness code to each core package and has no observed Go 1.27.1 result. The `gocove` package listing advertises branch reports, but the source clone returned 404, so its source and release history could not be checked here.

Decision: Pin `rillig/gobco` v1.3.4 through mise and gate aggregate Go core branches at 90%. Keep the 95% Go core statement floor because gobco does not measure uncalled functions without a condition. Neither gate proves every `select` branch or every possible control-flow path is tested.

## Python report format

Documented: [Coverage.py 7.16.1 branch measurement](https://coverage.readthedocs.io/en/7.16.1/branch.html) says branch mode adds destinations to the overall percentage and that JSON contains separate statement and branch percentages. Its [JSON command](https://coverage.readthedocs.io/en/7.16.1/commands/cmd_json.html) has one `--fail-under` threshold for the total. The JSON observed from the pinned 7.16.1 package includes `meta.branch_coverage` and per-file `covered_lines`, `num_statements`, `covered_branches`, and `num_branches` counts.

Verified: The pytest-cov 7.0.0 source clone at `/tmp/coverage-87-pytest-cov`, commit `224d8964caad90074a8cf6dc8720b8f70f31629b`, documents `--cov-branch` and one `--cov-fail-under=MIN` for total coverage in `docs/config.rst` lines 64 to 82. Its `src/pytest_cov/plugin.py` declares the same options. The separate 95% line and 90% branch floors therefore use a small pure checker over the JSON, with `branch = true` in `[tool.coverage.run]`.

Documented: pytest-cov 7.0.0 removed its own subprocess support and directs projects to `[tool.coverage.run] patch = ["subprocess"]` (`/tmp/coverage-87-pytest-cov/docs/subprocess-support.rst` at the recorded commit). [Coverage.py 7.16.1 process guidance](https://coverage.readthedocs.io/en/7.16.1/subprocess.html) says the patch starts coverage in spawned Python processes and uses parallel data files. Observed: the existing coordinator preflight process test covered 49 of 108 shell statements after the patch, up from zero without it. New process tests raised shell line coverage to 82 of 108 statements.
