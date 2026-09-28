# Fixed cohort query transcript

Observed at 2026-09-27T17:45:59Z with `gh` 2.100.0 and repository checkout `cfb74707dd57c70288b250c739c480bad4258770`.

The issue specified `repos/tbhb/agent-orchestration-poc`. The repository now answers at `repos/tbhb-dev/agent-orchestration-poc`. Only the REST owner path changed. The cohort bounds remained `merged_at > 2026-09-26T22:22:57Z` and `merged_at <= 2026-09-27T04:30:06Z`.

```text
gh api 'repos/tbhb-dev/agent-orchestration-poc/pulls?state=closed&per_page=100&page=1' > pulls-page-1.json
exit 0, 49 closed PR rows
gh api 'repos/tbhb-dev/agent-orchestration-poc/pulls?state=closed&per_page=100&page=2' > pulls-page-2.json
exit 0, 0 rows
```

Observed: two requests completed the listing. The empty second page establishes completion for this query at the source time. The 49 page-one rows were projected to number, URL, title, state, creation time, and merge time before commit because the full API response exceeded the repository's file-size hook limit. The row count and filter fields remain intact. The fixed-bound filter selected the 17 PR URLs in `pr-metrics.csv`. Later merges do not change that selection.

Observed: each selected PR has a retained `pr-<number>.json`, `pr-<number>-files.json`, `pr-<number>-reviews.json`, `pr-<number>-commits.json`, and `pr-<number>-check-runs.json` from `GET repos/tbhb-dev/agent-orchestration-poc/pulls/<number>`, its `/files`, `/reviews`, and `/commits` collections, and `GET repos/tbhb-dev/agent-orchestration-poc/commits/<head.sha>/check-runs`. Each request exited 0. Each files response has the `changed_files` number reported by its PR detail. The files and commits captures were projected to the fields used here after the secret scan flagged token-like hashes and patch text. Full file patches and full commit hashes were kept out of Git. The check rows refer to the captured head SHA, which is not proof of check state at every earlier push.

Observed: `gh api --paginate 'users/tbhb/projectsV2/9/items?per_page=100&fields=417475452,417475453'` supplied the Size and Worker fields retained in `project-size-worker.tsv`. The field IDs came from `GET users/tbhb/projectsV2/9/fields?per_page=100`. Project values were read after merge and can differ from values at dispatch. An initial `fields=Size` request returned HTTP 400 because this endpoint requires the numeric field ID. Explicit `page=<n>` on this Projects endpoint repeated its first page, so the successful read used its `after` cursor through `gh api --paginate`.

Observed: `mise run scc:version` reported scc 4.1.0. The #84 research note at `reports/inputs/pr-size-research.md` describes fragment classification as a candidate and leaves the exact counter to #142. Therefore `measured_84_size` and full `excluded_raw_lines` are `unknown` in `pr-metrics.csv`. `excluded_raw_lines_explicit` sums GitHub file additions and deletions only for the reference's explicit excluded paths. `pr-files.csv` retains each path, raw line count, and explicit exclusion reason. It does not claim detection of generated, minified, or other vendored files.

Observed: `changes_requested_rounds` counts review rows whose state is `CHANGES_REQUESTED`. `open_to_merge_seconds` subtracts PR `created_at` from `merged_at` in UTC. `updates_from_main` is a lower bound from PR commit rows with more than one parent and a subject containing both `merge` and `main`. `unknown` means no such commit proved a zero count. Harness, model, and effort come from the PR body, supplemented by the recorded Project Worker field where named. Unknown or broad `GPT-6` variants remain unknown. Old and new reviewer account names are kept as returned by the review rows.

The row transformations used Python 3.14.6 from `mise exec -- python` over the retained JSON. The complete conversion command ran with exit 0 and produced `pr-metrics.csv`, `pr-files.csv`, `pr-review-rows.csv`, and `pr-ci-rows.csv`. The conversion checked that every selected merge timestamp lay inside both bounds and that each files array length equaled `changed_files`. This is raw evidence preparation, not #107 notebook verification or an independent recomputation.
