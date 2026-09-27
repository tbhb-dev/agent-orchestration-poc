# Local reference migration report

Observed: `git for-each-ref --format='%(refname:short)' refs/heads` compared with `git show-ref --verify --quiet refs/remotes/origin/<branch>` on 2026-09-26 found these local-only refs:

- `issue30-rebased-backup`
- `research/100-document-size-limits`
- `research/104-data-analysis-stack`
- `tooling/84-conventions-reference`

The report is separate from remote PR validation. CI neither reads nor blocks these refs. This is a snapshot, not a branch-age determination, and no branch was renamed or deleted.
