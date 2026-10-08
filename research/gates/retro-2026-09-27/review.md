# Independent review of the fixed PR cohort

Reviewer: Codex collaboration subagent, gpt-6-astra, medium effort. The runtime did not expose an exact CLI version for this reviewer. Author: Codex CLI 0.157.1, gpt-6-sol, medium effort. Source snapshot: 2026-09-27T17:45:59Z at `cfb74707dd57c70288b250c739c480bad4258770`. Review checkout: `d32e4f4052323d10d25a354a5e0e9a13fc4c4d44`. Python: 3.14.6. DuckDB: 1.5.5. Quarto: 1.10.18.

## Inputs and commands

The [independent script](evidence/independent-review.txt) reads the two retained listing pages and each selected PR's projected detail, file, and review JSON. Its `.txt` extension keeps this single-use review command outside the reusable Python module checks. The reviewer ran the same script bytes from `/private/tmp/retro-independent-review.py` with exit 0, and the author reran the retained copy with exit 0. It does not read the notebook result table or reuse its transformation. Its input manifest hashes 53 sorted source files by SHA-256, one `<file hash>  <relative path>` line per file, then hashes the concatenation. The resulting manifest digest is `349044c045b33c186df764b451dfddd8affb59fb9f776ac07fb03c1a09091cbb`.

```text
mise exec -- python research/gates/retro-2026-09-27/evidence/independent-review.txt
exit 0
mise run notebooks:lint
exit 0
mise run notebooks:render -- research/gates/retro-2026-09-27/cohort.qmd
exit 1, sandbox denied Quarto's log write before kernel execution
mise run notebooks:verify -- research/gates/retro-2026-09-27/cohort.qmd
exit 1, same sandbox denial after lint passed
```

The different-model reviewer also reran both fenced notebook cells from `research/gates/retro-2026-09-27` with the following command and exit 0. The first cell printed `(17, 12, 51635, 3203.0, 279, 2196, 10)`. The second printed the ten sampled IDs below and `17 12 51635 279 2196`. This direct execution does not substitute for a Quarto render. The hosted analysis check must execute Quarto in its clean environment.

```sh
mise exec -- uv run --group analysis python - <<'PY'
from pathlib import Path
import re
source = Path('cohort.qmd').read_text()
cells = re.findall(r'^```\{python\}\n(.*?)^```\s*$', source, flags=re.MULTILINE | re.DOTALL)
assert len(cells) == 2, len(cells)
namespace = {'__name__': '__main__'}
for index, cell in enumerate(cells, 1):
    exec(compile(cell, f'cohort.qmd:python-cell-{index}', 'exec'), namespace)
assert namespace['totals'] == (17, 12, 51635, 3203.0, 279, 2196, 10)
assert namespace['sample'] == ['PR-82', 'PR-75', 'PR-76', 'PR-112', 'PR-122', 'PR-119', 'PR-79', 'PR-99', 'PR-95', 'PR-85']
print('Both notebook cells match independent reconstruction headlines and sample order.')
PY
```

## Headline comparison

The 49-row page followed by an empty page establishes completion of the retained request. Exactly 17 PRs satisfy the fixed bounds. All seven headline values and the denominator independently match the notebook and [claim table](claims.csv).

| Claim | DuckDB value | Independent value | Difference |
| --- | ---: | ---: | ---: |
| N01 merged PRs | 17 | 17 | 0 |
| N02 changes-requested verdicts | 12 | 12 | 0 |
| N03 PRs with changes requested | 10 | 10 | 0 |
| N04 elapsed seconds, sum | 51,635 | 51,635 | 0 |
| N05 elapsed seconds, median | 3,203 | 3,203 | 0 |
| N06 changed files | 279 | 279 | 0 |
| N07 explicitly excluded raw lines | 2,196 | 2,196 | 0 |

N01 selects 17 merged PRs from 49 closed rows. The denominator for N02 through N07 is those 17 merged PRs. The exclusion value covers only reference-listed paths, so the full excluded count remains `unknown`. Five later captured declared Size fields are known. Full #84 measured sizes and dispatch-time Size values are unavailable.

## Supporting-row comparison

The reviewer sorted unique `PR-<number>` IDs by lowercase SHA-256 of `165|<row ID>` with row ID as tie breaker, then selected the first ten. Each tuple is changes-requested rounds, elapsed seconds, files changed, and explicitly excluded raw lines. Every tuple matched with difference `(0, 0, 0, 0)`.

| Row ID | Independent and query tuple | Difference |
| --- | --- | --- |
| PR-82 | (2, 4999, 11, 149) | (0, 0, 0, 0) |
| PR-75 | (0, 300, 29, 234) | (0, 0, 0, 0) |
| PR-76 | (0, 1192, 24, 333) | (0, 0, 0, 0) |
| PR-112 | (0, 956, 5, 107) | (0, 0, 0, 0) |
| PR-122 | (0, 890, 8, 0) | (0, 0, 0, 0) |
| PR-119 | (1, 4168, 7, 16) | (0, 0, 0, 0) |
| PR-79 | (0, 407, 2, 0) | (0, 0, 0, 0) |
| PR-99 | (1, 5747, 37, 0) | (0, 0, 0, 0) |
| PR-95 | (1, 4890, 17, 0) | (0, 0, 0, 0) |
| PR-85 | (1, 3203, 15, 234) | (0, 0, 0, 0) |

All 279 projected file rows match the raw path and addition/deletion fields. All 67 projected review rows match PR number, review ID, state, and submission time. Every PR file-list length matches its detail's `changed_files`. No chart is produced for this retro, so there are no chart rows or light/dark visual marks to compare.

## Findings and limits

The reviewer found stale C02 and C14 wording, an overstatement that 14 PR bodies identify exact CLI/model details, and a mismatched C13 label. The author revised the claim table and report. PR #80's exact identity comes from a later Project field, while 13 PR bodies carry their own exact identity. The notebook's explicit exclusion matcher was expanded to all relevant patterns in the workflow reference. The reviewer independently applied the full pattern set and obtained the same 2,196-line lower bound. There are no unresolved numeric differences.

PR #121 has three retained changes-requested verdicts outside the cohort. The reported #164 response headers and private stopped-run logs were not independently obtained. The review does not promote testimony about those records, full #84 classifications, or dispatch-time fields into verified measurements.
