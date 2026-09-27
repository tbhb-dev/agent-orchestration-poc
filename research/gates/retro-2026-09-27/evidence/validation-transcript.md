# Evidence validation transcript

The source checkout was `cfb74707dd57c70288b250c739c480bad4258770` before these evidence files were committed. The tools were `gh` 2.100.0, `scc` 4.1.0, and mise-pinned Python 3.14.6.

```text
mise exec -- jq -r 'length' pulls-page-1.json pulls-page-2.json
49
0
exit 0

bounded jq filter over pulls-page-1.json > cohort-rows.tsv
17 rows
exit 0

mise exec -- python - [compare cohort IDs, file row counts, and CHANGES_REQUESTED review row counts with pr-metrics.csv]
17 cohort IDs, file counts, and changes-requested rounds match retained rows
exit 0

mise tasks ls | rg 'notebooks:(lint|render|verify)'
no matching tasks
exit 1

mise run fmt
exit 0, no tracked changes outside this issue

mise run check
exit 0, including Vale with zero alerts

mise run check:mutation
exit 0, Go 145 of 149 killed and Python 1418 of 1557 killed

mise run docs:build
exit 0, Chromium failed to launch inside the sandbox while the site build completed

mise run docs:check-links
exit 1, Chromium Mach bootstrap permission denied and seven links reported in unchanged site pages

mise exec -- gitleaks dir --redact --no-banner research/gates/retro-2026-09-27 reports/inputs/retro-2026-09-27-claims.md
no leaks found
exit 0
```

The `docs:check-links` result is a sandbox-limited local check. This change adds no site page or site link. Hosted CI remains the site link validation for the PR. The initial secret scan found token-like commit hashes and patch text in raw API captures. Commit rows were reduced to short IDs, parent counts, and subjects, while file rows kept paths and counts without patches. A repeat scan then passed. No full patch or full commit hash capture is committed from those endpoints.
