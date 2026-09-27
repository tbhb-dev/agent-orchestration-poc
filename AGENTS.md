# Worker instructions

Read the assigned issue and [project plan](docs/src/content/docs/project/plan.md) before working. The coordinator assigns the harness, model, and effort explicitly. Keep the issue's acceptance criteria and scope in view.

## Workflow

- Use one issue per work item in [Project 9](https://github.com/users/tbhb/projects/9). Issues need a goal, context and links, acceptance criteria, evidence required, docs impact, and out of scope.
- Work on `<type>/<issue>-<slug>` in your own `.worktrees/<type>-<issue>-<slug>/` checkout. Use the coordinator's assigned branch. Never work on `main` or share a checkout with another worker.
- Commit with `type(scope): imperative subject`, an explanatory body, and a `Refs: #<n>` trailer. Use Conventional Commits. Do not add attribution or co-author trailers to commits or PR bodies.
- The commit-msg hook rejects attribution and missing `Refs:` trailers except for subject `wip`, the ignore check guards tracked paths, and the handoff check verifies open PR claims.
- Keep work committed. Push before reporting completion and, once the bus exists, whenever reporting status there. Scan evidence for secrets and redact or hold back sensitive material before committing it.
- Open one small PR per issue with `gh pr create`. Use the conventional subject as its title. Include what, why, evidence, docs, and checklist sections, ending with `Refs: #<n>`. Include evidence links for `feat` and `exp` changes.
- The checklist covers green CI, docs updated or an issue filed, no secrets, and evidence committed. The Project Worker field and PR evidence section record the harness and model.
- Reviewers use `scripts/reviewer-gh.sh` for each reviewing command. It resolves the `tbhbbot` token and checks the effective account before running `gh`. The default implementer account stays `tbhb`, and workers never switch accounts. Never print, log, or write a token.
- `tbhbbot` posts request-changes and approval verdicts as PR reviews with inline threads. State the harness, model, and effort on the first line. Implementers reply in threads and push fixes without force pushing, then the reviewer re-reviews. One round is one verdict by `tbhbbot`. After three changes-requested verdicts, stop until a newer coordinator `tbhb` comment has the exact body `Arbitration: authorize another round`. The coordinator never approves through `tbhbbot`.
- The coordinator reviews every PR. A different harness reviews first where practical. Workers do not merge. The coordinator squash-merges after a current approval and green CI. The PR title and body become the squash commit.
- Reviewer identity records the project review process. It does not protect credentials from workers on the same machine. The coordinator may merge product code that handles credentials after ordinary review. The operator merges changes to project credential issuance, storage, grants, or repository secrets, security policy, egress rules, and host setup or installations. Escalate those changes to the operator.
- The `main` ruleset requires a PR, one approval of the latest push by someone other than its pusher, resolved threads, an up-to-date branch, and successful `check`, `docs`, `pr-body`, `imported-research`, and `mutation` checks. It dismisses stale approvals on push and permits only squash merges. Its bypass list is empty. Ruleset `all-branches` blocks force pushes on every branch.
- CI jobs are `check` (linters, formatting, tests, and repository guards), `docs` (site build and internal links), `pr-body` (trailers and evidence links), and `imported-research` (import immutability). See [workflow](docs/src/content/docs/workflow/index.md).
- Use `gh query` for read-only GitHub API calls. Reserve `gh api` for mutations.

## Functional core, imperative shell

- Functional core, imperative shell is a binding operator requirement from 2026-09-26. Put decisions and data transformations in pure functions. Keep side effects in a thin shell at the edges. A PR that puts I/O in the core or decisions in the shell cannot merge.
- Go core packages live under `internal/core/`. `cmd/`, `internal/bus`, `internal/registry`, `internal/backend/`, `internal/term`, and `internal/api` are shell packages. golangci-lint 2.14.0 `depguard` checks core imports.
- Python core modules live under `agent_orchestration_poc.core`. I/O lives under `agent_orchestration_poc.shell` and in experiment scripts. import-linter 2.15 checks the layers and forbidden I/O imports, with ruff 0.16.9 `TID251` as a partial call check.
- Test the core with plain values and no mocks. Property tests run in `check`, and `check:mutation` enforces scores for the core. Put process and socket tests in the shell's integration suite.
- Review rejects calls that import checkers cannot see, including `pathlib` writes and I/O through writer, connection, or process parameters. Run `check:go`, `check:imports`, and `check:ruff` for the boundary.

## Mise and checks

Run project tools through mise tasks, never as bare tools or global installs. For an ad hoc invocation without a task, use `mise exec -- <tool>` and add a task when the action becomes repeatable. Non-interactive shells may lack mise shims.

- Run `mise run vale:sync` once in each fresh worktree for the pinned prose styles.
- Run `mise run check` before completion. Run `mise run fmt` to apply formatters, then inspect the diff.
- `check:imports`, `check:dupl`, and `check:deadcode` also run in the `check` aggregate.
- Run `mise run build` for `bin/agentd` and `bin/agentctl`.
- Use `mise run docs:dev` for local docs, `mise run docs:build` for the output, and `mise run docs:check-links` to validate internal links. These tasks install locked site dependencies through `docs:install`.
- `mise run docs:browsers` installs Chromium for Mermaid rendering when needed. Any required system change goes to the operator first.
- Keep pins and their conventions in agreement. See [tooling](docs/src/content/docs/workflow/tooling.md) for individual checks and hooks.

## Worktrees, stashes, and work in progress

Every worktree shares one global `git stash` stack. An unqualified restore can take another worker's entry.

- Merge `main` into a pushed branch to update it. A clean update retains approval, while a hand-resolved merge dismisses it and needs a new review. Rebase only unpublished history. Never force push a pushed branch.
- Prefer `git rebase --autostash` when rebasing dirty unpublished history. It scopes the save to the rebase without using the shared stack.
- Never run bare `git stash pop` or `git stash apply`. Stack indices change whenever any worktree pushes an entry.
- If a manual stash is unavoidable, name it with `git stash push -m`. Run `git stash list` immediately before restoring, match your own message, and pop the explicit `stash@{n}`.

Prefer a throwaway work-in-progress commit to preserve state across a rebase or branch switch. It stays on your branch.

```sh
git commit -am wip --no-verify
# Rebase unpublished history, switch, or perform the required operation.
git reset --soft HEAD~1
```

This incomplete snapshot is the only permitted `--no-verify` use. Remove it with the soft reset before it reaches shared history. Run the full hook suite on real commits. Stage new files first if the snapshot must include them.

## Documentation and language rules

Only Codex writes or edits documentation and reports, including README files, site pages, worker instructions, research synthesis, experiment write-ups, decisions, and checkpoint reports. Other workers give Codex raw notes and evidence. Code comments and docstrings stay with the coder.

Write Markdown with one line per paragraph and sentence case headings. `guard-markdown` checks paragraph wrapping. All new Markdown uses the `ai-tells` Vale style and rumdl. Existing exemptions are listed in `.vale.ini` and [tooling](docs/src/content/docs/workflow/tooling.md). Clear alerts and remove exemptions when rewriting or moving those files.

Site pages need `title` and `description` frontmatter and no body H1. Use Mermaid or Excalidraw SVG diagrams only. Validate Mermaid with `mise run check:mermaid` and the site build. Commit the editable `.excalidraw` source with exported SVG. Codex writes Mermaid, and the coordinator supplies Excalidraw drawings for Codex to place.

Before editing a language or stack, read its rules and conventions:

| Work | Rules and conventions |
| --- | --- |
| Go | [.claude/rules/go.md](.claude/rules/go.md), [Go conventions](docs/src/content/docs/guides/go-conventions.md) |
| Python | [.claude/rules/python.md](.claude/rules/python.md), [Python conventions](docs/src/content/docs/guides/python-conventions.md) |
| Shell | [.claude/rules/shell.md](.claude/rules/shell.md), [Shell conventions](docs/src/content/docs/guides/shell-conventions.md) |
| Docs stack | [Docs stack conventions, including Rules for workers](docs/src/content/docs/guides/docs-stack-conventions.md#rules-for-workers) |

Codex reads this file natively but does not apply Claude's path-scoped rule globs. A Codex worker must read the corresponding file explicitly. Claude imports this file through `CLAUDE.md` and loads language rules from `.claude/rules/`. The docs stack rules currently live in the conventions page. Verify `agy` rule loading before relying on it.

A research gate precedes first code in each new language or stack. Read pinned release notes and migration guides, give Codex the evidence, and wait for conventions and worker rules before coding. Update the rules in the PR that moves a pin.

## Evidence and dependencies

Clone or update dependency sources under `~/Code/github.com/<owner>/<repo>` and record the commit read with the evidence. Read source and versioned documentation before relying on model knowledge. Preserve imported research verbatim under `research/imported/`, with synthesis in new documents.

Label claims precisely and cite the command, file, or source:

| Label | Meaning |
| --- | --- |
| verified | A targeted check confirmed the stated claim at recorded versions. |
| observed | A run exhibited the behavior, within the recorded conditions. |
| help-text | CLI help advertises the option or behavior. |
| schema | A source or configuration schema defines it. |
| documented | Versioned documentation describes it. |
| inference | The conclusion follows from cited evidence but lacks a direct test. |
| untested | The proposed behavior still needs a test. |

Do not treat help text or schema support as proof of runtime behavior. Record versions and limits of a test. Experiment directories use `NN-slug/` with a Codex-written `README.md`, raw `evidence/`, and `versions.md`.

## Operator boundaries

Sandbox escapes and system changes go to the operator with the exact proposed change. Never approve another worker's sandbox escape or type an approval into its terminal. Report blocked operations instead of bypassing the sandbox. Changes to host packages, Apple Containers, Tailscale, harness user settings, or launch agents require operator approval.

## Bus

The messaging bus does not exist yet. Phase 2 adds `agentctl` usage here after the bootstrap bus is verified. Until then, use the coordinator's dispatch and reporting channel and commit the evidence files it needs.
