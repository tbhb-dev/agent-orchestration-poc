---
title: Tooling
description: Pinned tools, configuration, mise tasks, hooks, and prose exemptions.
---

Run project tooling through mise so local checks and CI select the same versions. Use tasks for repeatable work and `mise exec -- <tool>` for an ad hoc command. Do not install global substitutes.

## Setup

Run `mise install` for the repository pins and `mise run vale:sync` once in a fresh worktree. Install hooks with `mise exec -- prek install`, which installs pre-commit and commit-msg hooks. `mise run check` runs the repository checks, `mise run fmt` applies formatters, and `mise run build` produces the two Go binaries. Inspect formatter diffs before committing.

Use `mise run docs:dev` for local reading. `mise run docs:build` writes `docs/dist/`, and `mise run docs:check-links` validates internal links and hashes. Site tasks install dependencies from the committed lockfile. Mermaid rendering needs Chromium, installed through `mise run docs:browsers`. Ask the operator before a setup step requires system changes.

## Pinned tools

These are the exact pins in `mise.toml`. Rust uses the default profile. CI separately pins mise itself to 2026.8.6.

| Tool | Version |
| --- | --- |
| `go` | 1.27.1 |
| `gofumpt` | 0.12.0 |
| `golangci-lint` | 2.14.0 |
| `node` | 24.21.0 |
| `pnpm` | 12.7.0 |
| `python` | 3.14.6 |
| `rust` | 1.98.1 |
| `uv` | 0.12.10 |
| `gitleaks` | 8.30.1 |
| `prek` | 0.5.1 |
| `rumdl` | 0.2.48 |
| `tombi` | 1.5.0 |
| `vale` | 3.22.0 |
| `actionlint` | 1.7.12 |
| `shellcheck` | 0.11.0 |
| `shfmt` | 3.14.0 |
| `npm:@biomejs/biome` | 2.5.14 |
| `pipx:ryl` | 0.22.0 |
| `pipx:jscpd` | 5.3.2 |
| `go:golang.org/x/tools/cmd/deadcode` | 0.50.0 |
| `go:github.com/tbhb/repotools/cmd/guard-markdown` | 0.9.0 |
| `go:github.com/go-gremlins/gremlins/cmd/gremlins` | 0.6.0 |
| `go:github.com/rillig/gobco` | 1.3.4 |

Python development dependencies are locked in `uv.lock` and declared in `pyproject.toml`, including Ruff 0.16.9, pytest 9.1.1, pyrefly 1.3.1, import-linter 2.15, vulture 2.16, Hypothesis 6.168.1, mutmut 3.8.0, and pytest-cov 7.0.0. Go properties use rapid 1.3.0 from `go.mod`. Site package versions are in `docs/package.json` and `pnpm-lock.yaml`, with their rationale in [docs stack conventions](/guides/docs-stack-conventions/). Vale downloads `ai-tells` and `ai-tells-commits` v1.37.0 through the release URLs in `.vale.ini`.

## Configuration

| Tool or check | Configuration |
| --- | --- |
| Go and gofumpt | `go.mod`, `mise.toml`, `scripts/check-gofumpt.sh` |
| ShellCheck and shfmt | `mise.toml`, `scripts/*.sh` shebangs |
| golangci-lint | `.golangci.yml` |
| Go core imports and complexity | `.golangci.yml` depguard, gocognit, gocyclo, funlen, and nestif settings |
| Duplicate code | `.jscpd.json`, with 50 tokens and 5 lines |
| Go dead code | `scripts/check-deadcode.sh` fails on deadcode output |
| Ruff and pytest | `pyproject.toml`, with test markers in `tests/conftest.py` |
| pyrefly | `[tool.pyrefly]` in `pyproject.toml`, strict for source, tests, and experiments |
| Gremlins | `.gremlins.yaml`, floors of 90 percent for the share of covered mutants killed and for mutant coverage |
| mutmut | `[tool.mutmut]` in `pyproject.toml`, `scripts/check-mutation-score.py`, 90 percent score |
| Coverage.py and pytest-cov | `[tool.coverage.run]` in `pyproject.toml` enables branch and subprocess measurement, `scripts/check-coverage.py` enforces separate Python line and branch floors |
| Go coverage and gobco | `go test -coverprofile`, gobco 1.3.4, `scripts/check-coverage.py`, separate statement and branch floors |
| Python imports | `[tool.importlinter]` in `pyproject.toml` and the core's nested `ruff.toml` |
| Python dead code | `[tool.vulture]` in `pyproject.toml` at confidence 60 |
| Biome | `biome.json` |
| Vale | `.vale.ini`, generated styles under `.vale/styles/` |
| rumdl | `.rumdl.toml` |
| ryl | `.ryl.toml` |
| tombi | `tombi.toml` |
| actionlint | `.github/workflows/*.yml`, default actionlint rules |
| gitleaks | Default rules, with redacted output in mise and prek commands |
| guard-markdown | Markdown file list from `scripts/markdown-files.sh` |
| Mermaid | `scripts/mermaid-check/package.json` and its lockfile |
| Hooks | `prek.toml` |

`GOTOOLCHAIN=local` prevents an implicit Go download. `UV_PYTHON_PREFERENCE=only-system` selects mise's Python. Go checks include module tidiness and verification, then lint, build, and race-enabled shuffled tests. `check:pyrefly` runs in the `check` aggregate and CI.

Property tests run in `check` with ordinary Go and Python tests. Required CI fixes the rapid seed at 20260926 and uses Hypothesis's built-in `ci` profile. Nightly tasks use random seeds and file an issue with their output on failure. Mutation tests run separately through `check:mutation`, and its CI job succeeds without running the tools when no core code or test changed.

`check:coverage` runs in `check` on every pull request. It requires 95 percent Go core statements, 90 percent Go core branches, and 70 percent Go shell statements. Python requires 95 percent core lines, 90 percent core branches, and 70 percent shell lines when shell code exists. The coverage pytest run includes integration tests. Coverage.py 7.16.1 JSON supplies separate line and branch counts because pytest-cov 7.0.0 `--cov-fail-under` checks a combined total. The pure decisions and failure probes are in `scripts/check-coverage.py`, `agent_orchestration_poc.core.coverage_floors`, and `reports/inputs/coverage-floors-87-evidence-2026-09-26.md`.

The `check` aggregate also runs `check:imports`, `check:dupl`, and `check:deadcode`. Go and Python complexity checks run in their existing linter tasks. Biome checks the TypeScript complexity rules at error level. Recalibrate thresholds at the first retro with phase 2 code.

## Mise tasks

| Task | Purpose |
| --- | --- |
| `check` | Run every check and the tests |
| `fmt` | Apply every formatter |
| `check-timings:record` | Record one command: `mise run check-timings:record -- <command>` |
| `check:timing-inventory` | Fail when a configured task or hook lacks a wrapper or local record |
| `check:go` | Format check, vet, module checks, lint, build, and test the Go module |
| `check:shell` | Lint and check formatting of repository shell scripts |
| `fmt:shell` | Format repository shell scripts |
| `fmt:go` | Format Go with gofumpt |
| `build` | Build bin/agentd and bin/agentctl, stamping VERSION (default dev) into the binaries |
| `check:ruff` | Lint and check formatting of Python with ruff |
| `check:imports` | Check Python core and shell import contracts |
| `check:dupl` | Fail on exact duplicate blocks in Go, Python, and TypeScript |
| `check:deadcode` | Fail on unreachable Go functions and unused Python names |
| `fmt:ruff` | Fix and format Python with ruff |
| `check:pytest` | Run the Python tests |
| `check:coverage` | Gate Go core and shell statements, Go core branches, and Python core and shell lines and core branches |
| `check:pyrefly` | Type check Python with pyrefly in strict mode |
| `check:mutation` | Enforce both core mutation gates outside `check` |
| `check:mutation:go` | Score the share of covered Go mutants killed and mutant coverage |
| `check:mutation:python` | Enforce Python core mutation score |
| `check:property:nightly:go` | Run Go core properties with a random seed from CI |
| `check:property:nightly:python` | Run Python tests with the default Hypothesis profile and a random seed |
| `check:biome` | Lint and check formatting with Biome |
| `fmt:biome` | Fix and format with Biome |
| `vale:sync` | Download the pinned Vale styles into .vale/styles |
| `check:vale` | Lint prose with Vale (ai-tells) |
| `check:rumdl` | Lint Markdown with rumdl |
| `fmt:rumdl` | Fix Markdown with rumdl |
| `check:guard-markdown` | Check that no Markdown paragraph is hard-wrapped |
| `check:mermaid` | Parse every fenced mermaid block |
| `check:ryl` | Lint YAML with ryl |
| `check:tombi` | Lint and check formatting of TOML with tombi |
| `fmt:tombi` | Format TOML with tombi |
| `check:experiments` | Check that every experiment directory has README.md, evidence/, and versions.md |
| `check:ignore-collisions` | Fail when Git ignores a tracked path and warn on case-insensitive directory matches |
| `check:handoff` | Verify that PRs described as open in the handoff are open on GitHub |
| `check:handoff-classifier` | Test open PR classification with line fixtures |
| `check:secrets` | Scan the git history for secrets with gitleaks |
| `check:actions` | Lint the GitHub Actions workflows with actionlint |
| `review:preflight` | Check a PR's workflows against revisions added to `origin/main` since its merge base |
| `pr:wait-check` | Wait for one named check to succeed on the PR head recorded at start |
| `checkpoint:closure-audit` | Report closed work-item issues lacking a linked merged PR or a recorded non-code reason |
| `check:pr-body` | Check a PR body on stdin against the commit convention: `mise run check:pr-body -- '<title>' < body.md` |
| `check:imported-research` | Check that research/imported/ is unchanged against a base ref: `mise run check:imported-research -- <base> '<title>'` |
| `docs:install` | Install the docs site dependencies from the committed lockfile |
| `docs:browsers` | Install the Playwright Chromium that rehype-mermaid renders diagrams with |
| `docs:dev` | Serve the docs site with live reload |
| `docs:build` | Build the docs site into docs/dist |
| `docs:check-links` | Build the docs site with starlight-links-validator enabled |

The PR-body and imported-research tasks need arguments from a PR or base ref and run separately from `check`. Docs builds also run separately. The CI job table is on [workflow](/workflow/#ci-jobs).

## Local check timings

Mechanical mise tasks and prek hooks append timing records to `.local-cache/check-timings/timings.sqlite3` in the main clone, including checks invoked from worktrees. The path is gitignored and is resolved from Git's common directory. The `check` aggregate is a dependency runner, so its child tasks are recorded individually. Each invocation writes one `local_checks` row after its command exits. A failed append does not change the command's stdout, stderr, or exit status.

The SQLite table has an integer `id` primary key, `name`, UTC ISO 8601 `started_at`, monotonic `duration_ns`, integer `exit_status`, nullable `commit_sha`, nullable `branch`, `origin` (`local` or `ci`), nullable `actor`, and `host`. It contains no command, arguments, output, environment, credentials, prompts, transcripts, or comment bodies. The actor comes only from `CHECK_TIMING_ACTOR` or `GITHUB_ACTOR`. An unknown actor or detached branch is stored as null.

Run `mise run check-timings:record -- <command>` for an ad hoc command. Run `mise run check:timing-inventory` after each configured task and hook has executed to verify both wrapper configuration and stored coverage. The inventory is separate from the `check` aggregate because a fresh clone has no prior records. To inspect the local table, use a SQLite reader against the main clone's store. If a check ran while the store was unavailable, rerun it to create a record. A later collector will import GitHub Actions timings without requiring a CI runner to write to this local path.

Run `mise run review:preflight -- <pr>` before review, `mise run pr:wait-check -- <pr> <name> <timeout-seconds>` before merge or completion reports, and `mise run checkpoint:closure-audit` at each checkpoint. The closure audit also runs weekly in read-only GitHub Actions. The [phase 1 retrospective](/retros/2026-09-26-phase-1/) records the failures behind these checks.

The [documentation brief template](https://github.com/tbhb/agent-orchestration-poc/blob/main/docs/briefs/documentation-brief-template.md) is for coordinator dispatches. Codex runs `mise run check:vale -- <changed-markdown-paths>` locally with pinned Vale 3.22.0 before returning pages. The [sample brief](https://github.com/tbhb/agent-orchestration-poc/blob/main/docs/briefs/documentation-brief-sample.md) and [sample page](/workflow/documentation-brief-sample/) show the required prose and command.

## Prek hooks

The built-in hooks remove trailing whitespace, fix the final newline, and reject added large files. Local pre-commit hooks check staged secrets with gitleaks, Go formatting and golangci-lint, ShellCheck and shfmt on `scripts/*.sh`, Ruff lint and formatting, import-linter, strict pyrefly, Biome, tombi lint and formatting, ryl, rumdl, paragraph wrapping, Vale prose, Mermaid fences, and experiment layout. Tool hooks run through mise, with the shell-only experiment check invoked directly. The import-linter and pyrefly hooks pass no file names so whole-project configuration applies.

The commit-msg hook runs Vale with `ai-tells` and `ai-tells-commits`. Real commits cannot bypass hooks. The exception is an incomplete throwaway work-in-progress commit that is removed before shared history, as described in `AGENTS.md`.

The `commit-trailers` hook rejects attribution and missing `Refs:` trailers except for subject `wip`, and `ignore-collisions` checks tracked paths and directory case matches before commits.

## Repository scripts

| Script | Purpose |
| --- | --- |
| `scripts/markdown-files.sh` | Enumerates tracked and unignored Markdown, excluding imported research |
| `scripts/check-vale.sh` | Synchronizes missing styles and checks supplied files or the Markdown inventory |
| `scripts/check-gofumpt.sh` | Fails on Go files needing formatting |
| `scripts/check-deadcode.sh` | Fails when deadcode prints an unreachable function |
| `scripts/check-mermaid.sh` | Installs the locked parser package and checks supplied files or the inventory |
| `scripts/mermaid-check/check.mjs` | Extracts fenced Mermaid and parses it with Mermaid |
| `scripts/check-experiments.sh` | Requires `NN-slug`, README, evidence directory, and versions, except the phase 0 assessment |
| `scripts/check-pr-body.sh` | Rejects attribution, missing `Refs:`, and missing evidence links for feature or experiment PRs |
| `scripts/check-ignore-collisions.sh` | Checks tracked paths with Git and warns on case-insensitive ignore directory matches |
| `scripts/check-handoff-prs.sh` | Classifies open PR claims and checks their GitHub state |
| `scripts/check-imported-research.sh` | Compares imports against a base ref and permits additions only for import PRs |
| `scripts/check-mutation-score.py` | Runs mutmut from a fresh cache and enforces the exported score |
| `scripts/check-gremlins-output.py` | Rejects timed-out Go mutants that gremlins excludes from its score |
| `agent_orchestration_poc.shell.coordinator_preflight` | Reads git and GitHub state for the three coordinator tasks |
| `agent_orchestration_poc.core.coordinator_preflight` | Decides workflow drift, check outcome, and closure review from values |
| `scripts/check-coverage.py` | Checks Go and Python coverage reports against separate floors, including gobco branches |

## Vale exemptions

New prose is linted with `ai-tells`. The baseline [alert inventory](https://github.com/tbhb/agent-orchestration-poc/blob/main/reports/inputs/vale-alerts-2026-09-26.txt) recorded 1,113 alerts in 30 older files and 344 in eight later files. These counts describe the tooling rollout, not a current full-tree scan.

`.vale.ini` exempts verbatim `research/imported/**` and raw `research/gates/**` notes. Older prose remains exempt at these paths until Codex cleans it:

- Root `PLAN.md` and `HANDOFF.md` pointers, plus the original `FABLE_HANDOFF.md`.
- `.claude/agents/*.md` and `.claude/rules/go.md`.
- `design-sketch/*.md` and `experiments/00-system-assessment/*.md`.
- Raw `reports/inputs/**`, with `research/gates/go/*.md` also listed in the legacy glob.
- `docs/src/content/docs/guides/go-conventions.md` and `docs/src/content/docs/decisions/0001-go-linter.md`.

When moving or rewriting exempt prose, resolve its alerts and remove its exemption. The moved handoff, checkpoint, retro, and devlog are linted at their site paths. The moved `docs/src/content/docs/project/plan.md` retains a specific exemption after one punctuation pass reduced its alerts from 168 to 105. Further cleanup is deferred to preserve its detailed decisions and citations during this move. Preserve facts, versions, decisions, and citations when fixing prose.
