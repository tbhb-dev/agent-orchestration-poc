# Formatter scratch isolation for issue 313

## CI failure and cause

Observed on 2026-10-08 in [check run 37755429457](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37755429457), head `a3848759062d1c5acd70627a34f6afbf5bf81f91`: [job 113238668318](https://github.com/tbhb-dev/agent-orchestration-poc/actions/runs/37755429457/job/113238668318) failed during `scripts/check-deadcode.sh` with these lines at 09:17:04 UTC:

```text
[check:deadcode] -: pattern ./...: stat /home/runner/work/agent-orchestration-poc/agent-orchestration-poc/node_modules/issue-302.u99Yjn: directory not found
[check:deadcode] deadcode: packages contain errors
```

The run metadata came from `gh query repos/tbhb-dev/agent-orchestration-poc/actions/workflows/check.yml/runs --jq '.workflow_runs[] | {head_sha, conclusion, html_url}'`, using the assigned `gh-as-agent api` REST wrapper with `per_page=100`. The job log came from `gh-as-agent api repos/tbhb-dev/agent-orchestration-poc/actions/jobs/113238668318/logs --allow-escape-sequences` redirected to a temporary file. Only the diagnostic excerpt is retained here.

Inference from the log and repository source at `0e579b756195fefd1ff6bd24af477463ed001db3`: the concurrent `check:go` task ran `scripts/test-go-format.sh`, whose exit trap removed its `node_modules/issue-302.*` directory while `deadcode -test ./...` discovered packages. The Python vulture command follows that shell script and was not the failing scanner. Vulture already restricts its paths to `src`, `tests`, `experiments`, and `scripts`.

## Versioned sources

Documented in `golang/tools` v0.50.0, commit `265dd1a6ecf0ee85548c7a8d1787d25fc5675e06`: `cmd/deadcode/doc.go` defines package arguments using `go list` notation. `cmd/deadcode/deadcode.go` passes the arguments to `packages.Load` and fails when loaded packages contain errors. These files explain why a disappearing directory can fail discovery before dead-code analysis.

The existing dependency clone at `/Users/tony/Code/github.com/golang/tools` required a lazy object fetch for the pinned source file. The sandbox denied its write to `.git/objects/pack`. The brief's authorized alternative was used: a shallow v0.50.0 clone at `/var/folders/ns/cc4x7s5j5271ltrw1t08w7p40000gn/T/issue-313-golang-tools`. No host installation or sandbox escape was used.

Observed local versions: `mise exec -- go version` reported Go 1.27.1 on darwin/arm64, and `mise exec -- gofumpt -version` reported v0.12.0 built with Go 1.27.1. The task pins deadcode 0.50.0 and vulture 2.16.

## Change and regression

The formatter regression script copies the three formatter scripts and repository ignore rules into a temporary Git repository outside the checkout. Source, ignored dependency, and deleted tracked-file fixtures all live there, with one cleanup trap. The dead-code scan retains its existing package arguments and confidence settings.

Verified locally: `mise exec -- scripts/test-go-format.sh` passed. It retains the assertions for detecting and formatting an untracked source file, leaving an ignored dependency file untouched, and excluding a deleted tracked file. Its new physical-path assertion rejects fixtures inside the checkout before creating Go files. The negative probe `mise exec -- env TMPDIR="$PWD" scripts/test-go-format.sh` exited 1 with `formatter fixtures must be outside the checkout scanned by deadcode` and cleaned up its temporary directory.

Verified locally: `mise run check:shell`, `mise run check:deadcode`, and `mise run fmt` exited 0. The formatter diff contained only the intended script and tooling-page changes.

Verified locally: `/usr/bin/time -p mise run check` exited 0 in 294.43 seconds. The Python coverage run passed all 1,204 tests, and Go core branch coverage was 94.74 percent against the 90 percent floor. This is one full aggregate run with the formatter regression and dead-code scan scheduled concurrently. It confirms the changed path under these conditions, not a general guarantee against unrelated filesystem races.

Verified at implementation commit `87bb05d`: `mise run pr:size -- origin/main` reported 34 counted units, comprising 33 script units and one prose unit. `mise run check:gate-changes -- --base 0e579b756195fefd1ff6bd24af477463ed001db3 --head HEAD --body-file /tmp/issue-313-pr-body.md` reported no registered gate findings. The normal commit hooks passed, including the staged secret scan.

Verified locally: `/usr/bin/time -p mise run check:mutation` exited 0 in 844.32 seconds. Go killed 145 of 149 mutants, with 97.32 percent efficacy, 100 percent mutant coverage, and no timeouts. Python killed 11,854 of 13,155 mutants, scoring 90.11 percent against the 90 percent floor. Python reported 1,299 surviving mutants and two timeouts. No mutation settings or core code changed for #313.

## Validation limits for issue 313

Verified locally: `mise run build` passed. The docs link check for #313 could not finish in the worker sandbox: `mise run docs:check-links` failed when Chromium attempted `bootstrap_check_in` for its Mach-port rendezvous server, returning `Permission denied (1100)`. The coordinator was given the exact command to run outside the worker sandbox. No browser setting or check was changed.

The brief requires a `phase/` PR label, but issue #313 has none, `config/workflow-reference.toml` defines none, and the repository labels API returned no `phase/` names. Clarification was requested before PR creation for #313.

The passing CI run after the change remains pending for #313 because PR creation awaits that clarification. The local full check and mutation results above do not replace the required CI evidence.

A diagnostic `ps` process listing was also denied by the sandbox during #313 validation. No alternate process-inspection route was attempted.
