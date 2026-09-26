# Retro checks #15, #16, and #17 evidence

Observed on 2026-09-26 in `tooling/15-16-17-retro-checks`. The fixture repository was created under the system temporary directory. Its exclude file was separate from the real repository's common `.git/info/exclude`.

## Commit and PR body trailers

The `commit-trailers` prek hook was invoked with `--stage commit-msg --commit-msg-filename` against temporary message files.

Failing commit message, exit 1:

```text
tooling(workflow): test

Co-Authored-By: Example Bot

commit attribution and Refs trailers.....................................Failed
- hook id: commit-trailers
- exit code: 1

  attribution trailer found; the plan forbids them in commits and PR bodies:
    3:Co-Authored-By: Example Bot
  missing 'Refs: #<issue>' trailer
```

Passing commit message with `Refs: #15`, exit 0:

```text
commit attribution and Refs trailers.....................................Passed
```

A message with subject exactly `wip` also passed, as the documented temporary commit exception.

The PR body examples ran through `mise run check:pr-body -- 'tooling(workflow): test'`, the same script used by the `pr-body` CI job.

Failing PR body with `Generated with Example Bot` and no `Refs:`, exit 1:

```text
[check:pr-body] $ scripts/check-pr-body.sh 'tooling(workflow): test'
attribution trailer found; the plan forbids them in commits and PR bodies:
  4:Generated with Example Bot
missing 'Refs: #<issue>' trailer
[check:pr-body] ERROR task failed
```

Passing PR body with `Refs: #15`, exit 0:

```text
[check:pr-body] $ scripts/check-pr-body.sh 'tooling(workflow): test'
PR body ok
```

## Ignore collisions

A temporary repository tracked `reports/inputs/item` and had `/INPUTS/` in its own `.git/info/exclude`. `scripts/check-ignore-collisions.sh <fixture>` warned and exited 0:

```text
case-insensitive directory match: .git/info/exclude:1:/INPUTS/ -> reports/inputs
```

With `reports/inputs/` in the fixture `.gitignore`, the same check failed with exit 1:

```text
ignored tracked path: .gitignore:1:reports/inputs/	reports/inputs/item
case-insensitive directory match: .gitignore:1:reports/inputs/ -> reports/inputs
```

The clean worktree ran `mise run check:ignore-collisions` with exit 0 and no collision output:

```text
[check:ignore-collisions] $ scripts/check-ignore-collisions.sh
```

The check excludes personal global ignore files so local user settings do not make the repository gate vary by machine. It reads repository `.gitignore` files and the common Git directory's `info/exclude`.

## Handoff PR state

The line fixture covered `Open PR #2`, `PR #3 remains open`, a linked `pull/4`, closed PR #5, and a sentence where an open-list query precedes merged PRs #75 and #76. `mise run check:handoff-classifier` passed:

```text
[check:handoff-classifier] $ scripts/test-handoff-pr-classifier.sh
handoff classifier fixtures ok
```

A temporary handoff claiming `Open PR #2` produced exit 1 after the script queried GitHub:

```text
handoff calls PR #2 open, but GitHub reports MERGED
```

The current root pointer and docs handoff produced exit 0:

```text
[check:handoff] $ scripts/check-handoff-prs.sh
handoff has no PR references described as open
```
