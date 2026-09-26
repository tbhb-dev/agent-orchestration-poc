# Phase 0 retrospective findings

Gathered 2026-09-26 by a coordinator research subagent (`claude-sonnet-5`, medium, via `.claude/agents/research.md`) for issue #13. This file is the raw input; Codex writes the retro and the devlog entry from it. Every item carries one of two labels: **observed** (from a command, a file, or the GitHub API) or **coordinator observation** (from the notes the coordinator handed the subagent, not independently verified).

Times below are local (UTC-4) unless marked otherwise; the GitHub API reports UTC and the git log was run with `--date=iso`.

## Sources read

- `PLAN.md`, section Retrospectives, devlog, and mechanical checks (inputs, output shape, the mechanical-checks rule, standing candidates, the silent-worker timer, and the Devlog subsection).
- `HANDOFF.md` (the checkpoint handoff, especially Gotchas discovered and Next three actions).
- `reports/phase-0-checkpoint.md`.
- `reports/inputs/phase-0-decisions.md` (sections 3, 8, 9, 10, 12, 13).
- `experiments/00-system-assessment/evidence.md` (headline findings, headings, and the items-not-checked list), plus the first lines of the other eight files in that directory.
- The coordinator's memory notes, read-only: `~/.claude/projects/-Users-tony-Code-github-com-tbhb-agent-orchestration-poc/memory/MEMORY.md` and the ten linked files.
- Issues #3 and #13 (`gh issue view`), the full issue list, PRs #1 and #2 (`gh pr view --json`), the repository settings and branch list (`gh query`).
- Commands run in the worktree: `git log --format='%h %ad %s' --date=iso main`, `git show --stat 7a57116`, `git show -s --format=%B` on the two squash commits, `git branch -a`, `git worktree list`, `git fetch --prune --dry-run`, `wc -l`, `git ls-files`, and `cat "$(git rev-parse --git-common-dir)/info/exclude"`.

Inputs the plan lists that do not exist yet, so the retro has nothing from them: there is no bus log (no bus until phase 2), no CI (no `.github/workflows/` directory; issue #7 adds it), no worker roster (phase 0 used one-shot coordinator subagents; `HANDOFF.md`, Worker roster), no hook denials or sandbox failures reported by workers, and no Project items that moved to Blocked (the Project had zero items during phase 0). Observed.

## Timeline

All observed from `git log` on `main` and the GitHub API.

| Time (local) | Event | Source |
| --- | --- | --- |
| 13:38:38 | `7a57116` scaffold commit lands directly on `main` (22 files, 1213 insertions: `FABLE_HANDOFF.md`, `design-sketch/`, mise, prek, uv scaffold). Carries an `Assisted-by: Claude Code` trailer. | `git log`, `git show --stat` |
| 13:46:05 | `e7b818a` on `docs/phase-0-plan`: assessment evidence and dependency clones. Carries `Assisted-by: Claude Code`. | PR #1 commits |
| 13:56:34 | `c695502`: first plan and checkpoint report, written by Codex. Carries `Assisted-by: Codex CLI 0.157.1`. | PR #1 commits |
| 13:57:40 | PR #1 opened. | `gh pr view 1` |
| 16:48:16 | `b1af95e`: models, retros, devlog, and rollover added to the plan (the revision round). No trailer. | PR #1 commits |
| 16:49:13 | `c948dc4`: decisions brief committed under `reports/inputs/`. No trailer. | PR #1 commits |
| 16:52:01 | `6c17e13`: `HANDOFF.md` added. No trailer. | PR #1 commits |
| 16:53:17 | PR #1 squash-merged as `7cac91a`. Zero reviews, zero comments on the PR. | `gh pr view 1`, `git log` |
| 16:55:30 | `2f69690` on `docs/handoff-after-approval`: handoff marked approved. | PR #2 commits |
| 16:55:33 | PR #2 opened. | `gh pr view 2` |
| 16:55:44 | PR #2 squash-merged as `1089627`, eleven seconds after opening. Zero reviews, zero comments. | `gh pr view 2`, `git log` |
| 17:07 | `.claude/agents/*.md` written uncommitted in the main checkout by the new coordinator session. | `ls -la .claude/agents` |
| 17:08:45 to 17:08:59 | Issues #3 through #14 filed by the phase 1 session (phase 1 has started; outside phase 0). | `gh issue list` |

Phase 0 wall clock from the scaffold commit to the PR #2 merge: about 3 hours 17 minutes. Observed. The stretch from PR #1 opening (13:57) to its revision commit (16:48) is 2 hours 51 minutes and contains the operator's plan review, the model, harness, GitHub Projects, and NATS research fan-out, the revision round, and the subagent stall described under What cost time.

PR data, observed:

| PR | Commits | Files | Additions | Deletions | Open to merge | Reviews | Comments |
| --- | --- | --- | --- | --- | --- | --- | --- |
| #1 | 5 | 14 | 3440 | 0 | 2 h 56 min | 0 | 0 |
| #2 | 1 | 1 | 6 | 6 | 11 s | 0 | 0 |

What phase 0 produced, in lines (`wc -l`), observed:

| File | Lines |
| --- | --- |
| `PLAN.md` | 522 |
| `reports/phase-0-checkpoint.md` | 41 |
| `reports/inputs/phase-0-decisions.md` | 357 |
| `experiments/00-system-assessment/evidence.md` | 786 |
| `experiments/00-system-assessment/harness-research.md` | 781 |
| `experiments/00-system-assessment/model-research.md` | 253 |
| `experiments/00-system-assessment/github-projects-research.md` | 234 |
| `experiments/00-system-assessment/nats-research.md` | 201 |
| `experiments/00-system-assessment/model-inventory.md` | 134 |
| `experiments/00-system-assessment/dependency-clones.md` | 33 |
| `experiments/00-system-assessment/permission-facts.md` | 33 |
| `experiments/00-system-assessment/versions.md` | 25 |
| Total | 3400 |

Plus `HANDOFF.md` (40 lines) and the 22-file scaffold. `git ls-files` on `main` lists 36 tracked files. Observed.

## What went well

- Observed: the whole phase, from empty repository to approved plan with evidence, finished in one afternoon (about 3 h 17 min of wall clock).
- Observed: every decision in the plan points at an evidence file. `experiments/00-system-assessment/` holds nine files, each opening with its date, method, and an evidence-label scheme (VERIFIED, NOT CHECKED, [help-text], [schema], [vendor-docs], [observed]). The checkpoint report's Decisions section cites a file or plan section per decision.
- Observed: the assessment cost nothing on the machine. `evidence.md` states all commands were read-only, nothing was installed or started, and `dependency-clones.md` records 23 clones with SHAs and nearest tags without building anything. The model inventory verified every assigned model by a real call.
- Coordinator observation: the operator answered every checkpoint question on the same day and approved the plan the same evening ("I approve the plan"), so no work waited overnight. Observed corroboration: PR #2 (the approval record) merged 2 minutes 27 seconds after PR #1.
- Observed: the squash-only setting worked as intended. Repository settings show `allow_squash_merge: true`, merge commits and rebase merges disabled, `squash_merge_commit_title: PR_TITLE`, `squash_merge_commit_message: PR_BODY`, and `delete_branch_on_merge: true`. Both squash commit bodies on `main` are the PR bodies verbatim, and the GitHub branch list holds only `main`.
- Coordinator observation: phase 0 left no stray worktrees or branches behind. Observed corroboration: `git worktree list` at the start of phase 1 showed only the main checkout before the phase 1 dispatches, and origin has only `main`. See What broke for the stale local remote-tracking refs.
- Observed: the decisions brief was committed under `reports/inputs/` (commit `c948dc4`) so the plan's provenance survives the coordinator session, as the rollover procedure in `PLAN.md`, Coordinator session rollover, requires.
- Coordinator observation: the plan revision needed one round, for judgment rather than facts. Observed corroboration: PR #1 has exactly two waves of commits (13:46 to 13:56, then 16:48 to 16:52), and `PLAN.md`, Models and effort levels, records the phase 0 plan as "written at Astra's default and needed one revision for judgment, not facts".

## What cost time

- Coordinator observation: a research subagent lead finished its sub-reports and then stalled for nearly two hours without assembling them. The coordinator waited for a completion notification that never came. This is why every dispatch over fifteen minutes now gets a scheduled check-in (`PLAN.md`, Retrospectives, devlog, and mechanical checks, "Promoted to phase 1 by a phase 0 failure"). Observed corroboration: `harness-research.md` opens by saying it was "researched by three coordinator subagents, one per harness" and that the sections are "the subagents' reports, assembled unchanged", which is consistent with the assembly being done after the lead stalled. The 2 h 51 min gap inside PR #1 is the only place in the timeline the stall can sit.
- Coordinator observation: the first `codex exec` document run inside a worktree could not commit until `--add-dir <repo>/.git` was added, because a linked worktree's index and refs live under the main repository's `.git`, outside the `workspace-write` sandbox. The memory note `codex-exec-worktree-add-dir.md` records that `git rev-parse --git-common-dir` returns the relative `.git` from the main checkout, which bit once more before an absolute path was used. Observed corroboration: `reports/phase-0-checkpoint.md`, Risks, records "The first draft could not be committed because the worktree's git metadata is under the main repository's `.git`".
- Coordinator observation: `codex exec` 0.157.1 has no `-a` approval flag, so the approval policy is set with `-c 'approval_policy="never"'`. Observed corroboration: `PLAN.md`, Permission modes, Codex, and the decisions brief section 4 both say the installed `exec` "has no approval flag at all".
- Coordinator observation: the harness attribution rule changed mid-phase and the commit convention was revised to drop trailers. Observed corroboration: the three commits before 16:00 carry `Assisted-by:` trailers and the three after do not; both squash commits are clean; `reports/inputs/phase-0-decisions.md`, section 13, records the decision.
- Coordinator observation: the plan needed one revision round (see What went well). The cost was a second `codex exec` run and a re-read of the whole plan.
- Coordinator observation: the Agent tool has no per-launch effort control, so the new session had to add `.claude/agents/*.md` definitions carrying `model` and `effort` before it could dispatch anything under the plan's rule that every launch names both. Observed: five definitions (`impl`, `research`, `mechanical`, `review`, `utility`) exist untracked in the main checkout, dated 17:07, and issue #3 has an acceptance criterion to commit them.
- Observed: the assessment could not run `mise install` by instruction and recorded `mise ls --missing` as empty instead (`evidence.md`, Items not checked). It found that mise shims are absent from non-interactive shells, so `uv`, `prek`, `rumdl`, `vale`, `tombi`, `python3`, and `rustc` resolve to Homebrew and `ryl` is missing from PATH. This shapes every provisioned process and CI step (`PLAN.md`, What the system assessment established) and is a standing cost until the tooling item lands.

## What broke

- Coordinator observation: git's `info/exclude` on this case-insensitive filesystem hid `reports/inputs/` behind a `/INPUTS/` entry, so the decisions brief was invisible to `git status` until the cause was found. Observed: the common `.git/info/exclude` still contains the line `/INPUTS/` today, so the trap remains armed for any future path that differs only by case.
- Coordinator observation: `HANDOFF.md` described its own PR as open ("The only open PR carries this update on `docs/handoff-after-approval`; the coordinator merges it itself") although PR #2 was merged before the next session started. Observed: that sentence is in `HANDOFF.md` on `main` now, and PR #2 merged at 16:55:44, before the phase 1 session filed issues at 17:08. The handoff is stale by construction because it is committed inside the PR it describes.
- Coordinator observation: `.obsidian/` sat untracked in the tree because `.gitignore` never listed it. Observed: `.gitignore` on `main` has four lines (`.venv/`, `__pycache__/`, `.DS_Store`, `.worktrees/`), and `git status` on the main checkout shows `?? .obsidian/` and `?? .claude/`. Issue #3 adds `.obsidian/`; nothing yet decides what in `.claude/` is tracked beyond `agents/`, and `.claude/scheduled_tasks.lock` sits beside it (covered by the global exclude, not the repository's `.gitignore`).
- Coordinator observation: two PRs merged with coordinator review as the only gate because CI did not exist. Observed: both PRs have zero reviews and zero comments in the API, there is no `.github/workflows/` directory, `gh query repos/tbhb/agent-orchestration-poc/rulesets` returns an empty list, and PR #2 merged eleven seconds after it opened. The coordinator's review left no trace on GitHub.
- Observed: the local clone still carries the remote-tracking refs `origin/docs/phase-0-plan` and `origin/docs/handoff-after-approval` even though origin deleted both on merge. `git fetch --prune --dry-run` lists both as deletable. Cosmetic, but a future `git branch -a` misreads it as branches left behind.
- Observed: the scaffold commit `7a57116` and the first two PR #1 commits carry `Assisted-by:` trailers that the current convention forbids. They are in history and stay there; the squash commits on `main` are clean, so only `git log --all` or the PR page shows them.
- Observed: no CI and no commit-message lint ran on any phase 0 commit. The `prek.toml` scaffold exists but nothing verifies it ran, since mise shims are absent from non-interactive shells and no hook output is recorded anywhere.

## Decisions made in the period

All observed from `PLAN.md`, `reports/phase-0-checkpoint.md`, and `reports/inputs/phase-0-decisions.md`, with the plan section that records each.

- `agentd` is the provisioner from day one, growing into the daemon; `agentctl` is the one CLI. `PLAN.md`, Names; decisions section 1.
- One root Go module, the `uv init` package kept as a shared helper library, pnpm workspaces, numbered experiments, worktrees under `.worktrees/`. `PLAN.md`, Repository layout; decisions section 2.
- Project fields and views, issue shape, branch naming `<type>/<issue>-<slug>`, Conventional Commits with a `Refs:` trailer, squash merges only with the PR body as the commit body, coordinator-managed branch protection once CI exists, mise-based CI. `PLAN.md`, GitHub workflow; decisions section 3.
- Nine interactive workers, three per harness, set by the operator; `agy` gets only bounded work; coordinator-side agent teams and workflows are allowed for non-implementation work. `PLAN.md`, The build group and Concurrency; decisions section 4.
- Permission modes per harness: Claude `--permission-mode auto` with sandbox and per-worker `--settings`, Codex `-s workspace-write` with `approval_policy = "never"`, `agy --sandbox --dangerously-skip-permissions`; `codex exec` runs need `--add-dir <repo>/.git` in a worktree. `PLAN.md`, Permission modes; decisions section 4.
- Retrospectives at every checkpoint and every ten merged PRs; every retro proposes a mechanical check; the silent-worker timer is promoted to phase 1. `PLAN.md`, Retrospectives, devlog, and mechanical checks; decisions section 8.
- Explicit model and effort per worker and task, starting from each vendor's published starting point. `PLAN.md`, Models and effort levels; decisions section 9.
- Coordinator session rollover: durable state first, `HANDOFF.md` regenerated by Codex at every rollover and checkpoint, compaction and handoff triggers, resume as fallback. `PLAN.md`, Coordinator session rollover; decisions section 10.
- An assumptions register that retros retire as evidence lands. `PLAN.md`, Assumptions register; decisions section 11.
- A Codex-written devlog on the docs site through `starlight-blog`, entries under `reports/devlog/` until then. `PLAN.md`, Retrospectives, devlog, and mechanical checks, Devlog; decisions section 12.
- No attribution trailers in commits or PR bodies; harness and model go in the Project's Worker field and the PR body. `PLAN.md`, GitHub workflow, Commits; decisions section 13.
- Research gates before the first code in every language and stack, frontend first. `PLAN.md`, Research gates for languages and stacks; decisions sections 14 and 15.
- Operator answers recorded on 2026-09-26: plan and model assignments approved, GitHub Pro confirmed, research evidence may be committed ("when in doubt, commit"), the coordinator manages branch protection and may add in-repo hooks and checks without asking. `HANDOFF.md`, Current phase and operator decisions; memory notes `when-in-doubt-commit.md` and `repo-scope-authority.md`.

## Mechanical-check candidates

Each entry names the failure it catches, the check, where it would run, and whether the phase 1 tooling item (issue #3) already covers it. Issue #3's acceptance criteria cover: `.gitignore` with `.obsidian/`, secret scanning in prek, `guard-markdown` as a mise task, the `ai-tells-commits` lint on `commit-msg`, the experiment-directory completeness script, a fenced Mermaid check, and committing `.claude/agents/`. Observed from `gh issue view 3`.

1. **Silent-worker timer.** Failure: a subagent finishes its parts and never assembles or reports, and the coordinator waits (nearly two hours in phase 0; coordinator observation). Check: on every dispatch expected to run longer than fifteen minutes, schedule a check-in with the harness's monitor or wakeup facility that inspects the worktree branch and the agent's last message. Where: coordinator timer now; from phase 2 a last-seen timestamp per worker in the bus status bucket with `agentd` flagging silence past a threshold. Covered by #3: no. Already a plan rule (`PLAN.md`, Retrospectives, devlog, and mechanical checks), but nothing mechanical enforces that the coordinator sets it; the phase 2 bus item is the mechanical form.
2. **Case-insensitive ignore collision.** Failure: an exclude or ignore entry differing only by case from a real path hides files on this filesystem (`/INPUTS/` hid `reports/inputs/`; the entry is still present). Check: a script that runs `git check-ignore -v --no-index` over every tracked and untracked path and fails if any tracked path or any path a brief names is ignored, and separately warns when an ignore entry matches a tracked path case-insensitively. Where: prek hook and mise task; a one-off cleanup deletes the `/INPUTS/` line from `.git/info/exclude`. Covered by #3: no.
3. **Attribution-trailer and `Refs:` rejection.** Failure: a commit carries `Assisted-by:`, `Co-Authored-By:`, or similar, or lacks a `Refs: #<n>` trailer (three phase 0 commits carry the forbidden trailer; none carries `Refs:`). Check: a `commit-msg` hook that rejects those trailer names and requires `Refs:` except on `wip` commits, plus the same test over the PR body in CI since the body becomes the squash commit. Where: prek `commit-msg` and a CI job on the PR body. Covered by #3: partly. #3 adds the `ai-tells-commits` lint, which is a prose-tells style, not a trailer check; the `Refs:` hook is a "later candidate" in the plan.
4. **Stale `HANDOFF.md` on merge.** Failure: the handoff describes its own PR as open after merge (observed on `main` now). Check: a CI job or a `gh` post-merge script that fails when `HANDOFF.md` names a PR number whose state is merged or closed, or a rule that the handoff refers to PRs only by branch and lets the reader run `gh pr list`. Where: CI on pushes to `main`; a retro script until then. Covered by #3: no.
5. **Review evidence on every merged PR.** Failure: PRs merge with zero reviews and zero comments, so the coordinator's review leaves no trace and cannot be audited (both phase 0 PRs). Check: a ruleset on `main` requiring one approving review, or, while the coordinator is the only reviewer and cannot approve its own PR as the same GitHub user, a required PR comment prefixed with a fixed marker recording what was reviewed and by which worker. Where: a `main` ruleset plus a CI job reading PR comments. Covered by #3: no; #7 (CI) and the ruleset in `HANDOFF.md`, Next three actions, cover the CI half.
6. **Ignored-file audit.** Failure: editor and harness state (`.obsidian/`, `.claude/scheduled_tasks.lock`) sits untracked and either gets committed by accident or hides real untracked work in `git status`. Check: a script that fails if `git status --porcelain` shows untracked paths outside an allowlist, run before every commit. Where: prek hook. Covered by #3: partly. #3 adds `.obsidian/` to `.gitignore`; the audit that catches the next such directory is not there.
7. **Stale remote-tracking refs.** Failure: `git branch -a` shows deleted origin branches and a reader concludes branches were left behind. Check: `git fetch --prune` in the worktree-creation script and a mise task that reports refs `--prune --dry-run` would delete. Where: mise task and the provisioner's worktree step. Covered by #3: no. Low value on its own; worth folding into the worktree tooling.
8. **Subagent definitions named per launch.** Failure: a dispatch runs on a harness default model or effort, which the plan forbids. Check: a script that lists `.claude/agents/*.md` and fails if any lacks `model` or (except Haiku) `effort` in frontmatter, and a coordinator rule that `subagent_type` is always one of them. Where: prek hook over `.claude/agents/`. Covered by #3: partly. #3 commits the definitions; nothing checks their frontmatter.
9. **`guard-markdown` in CI and over `reports/` and `experiments/`.** Failure: hard-wrapped prose in files the hook never saw (documents written by Codex or by `codex exec`, which does not run the Claude Code hook). Check: `guard-markdown` over every Markdown file except `research/imported/`. Where: mise task (#3) and CI (#7). Covered by #3 and #7: yes.
10. **Devlog presence after merges.** Failure: a day with merged PRs has no `reports/devlog/YYYY-MM-DD.md` (2026-09-26 had two merges and no entry until #13). Check: a script that compares merged PR dates from `gh pr list --state merged` against devlog filenames and warns on gaps. Where: retro script now, CI job later. Covered by #3: no; listed in the plan as a later candidate.

Standing candidates from the plan that phase 0 gave no new evidence for, listed so the retro author does not lose them: research-import immutability (`research/imported/` unchanged after the import lands; a CI job, not in #3), the PR-body evidence-link check for `feat` and `exp` changes (a CI job, not in #3), the dependency-clone staleness report (a mise task, later), and the bus-side schema check (phase 2).

## Open questions for the retro author

- Was the subagent stall a harness behavior (the lead finished but sent no completion) or a prompt defect (the lead was never told to assemble and notify)? The coordinator's notes say only that it stalled; the harness research reports that the reports were "assembled unchanged", which suggests the coordinator assembled them by hand. The answer decides whether the fix is the timer alone or also a brief template change.
- Should the `/INPUTS/` line be deleted from `.git/info/exclude` now, and who owns that file? It is outside the repository's tracked content, so the tooling item cannot fix it in a PR; it needs a coordinator action and a note in the handoff.
- Does the coordinator want its PR reviews to leave a GitHub trace (a comment or a review from a second account or a worker), or is the retro record enough? Candidate 5 depends on that.
- The plan says retros alternate between a Claude Code reviewer and the Codex docs writer for the findings step. This one used a Claude research subagent; should the phase 1 checkpoint retro's findings be gathered by Codex?
- `HANDOFF.md`'s "open PR" sentence is wrong on `main`. Does the retro action item regenerate the handoff now (a Codex run on this branch) or leave it until the phase 1 checkpoint regenerates it anyway?
- Three history commits carry `Assisted-by:` trailers. Rewriting `main` is not on the table; the retro should say whether the convention applies from the squash commits onward and stop there.
- Which of the ten candidates become issues now versus folding into #3 or #7 before those PRs open? Issue #3's worker is already running on `chore/3-tooling`, so anything added to its scope has to reach it before the PR opens.
