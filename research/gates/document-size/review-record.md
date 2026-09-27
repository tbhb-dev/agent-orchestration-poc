# Document size verification record

## Author-side reproduction

**Observed:** At input commit `d2add70d5ce58d89c188b7944f561ab9b30477b9` on branch merge commit `2d7fc01`, `mise run notebooks:render -- research/gates/document-size/measure.qmd` and `mise run notebooks:verify -- research/gates/document-size/measure.qmd` each exited 1 with `no task ... found`. Issue #107 owns these tasks and remains a prerequisite. The direct `mise exec -- python -` execution of both fenced Python cells in `measure.qmd` exited 0; it is an author-side word-table check, not a notebook render or verification run.

~~~sh
mise exec -- python - <<'PY'
from pathlib import Path
source = Path('research/gates/document-size/measure.qmd').read_text()
namespace = {}
for block in source.split('```{python}\n')[1:]:
    code = block.split('\n```', 1)[0]
    exec(compile(code, 'research/gates/document-size/measure.qmd', 'exec'), namespace)
PY
~~~

**Verified by author-side direct execution:** The primary and independent methods each counted 128 of 128 eligible documents and 266,716 words. Each of the seven class totals and all 128 path rows matched exactly. Every difference was zero. `summary.csv` retains the primary headline and class result rows; `counts.csv` retains the supporting path rows. No charts were produced, so there are no chart marks or variants to inspect.

## Deterministic supporting sample

The issue ID is `100`, and the result-row ID is the path in `counts.csv`. Sort all 128 IDs by lowercase SHA-256 of UTF-8 `100|<row_id>`, breaking digest ties by ID, then take ten. SHA-256 of the complete sorted IDs joined by LF and terminated by LF is `6574a6de9f46a42d04114905828fe32f5504da6118b57e290c7d5a7b3eb94a38`. The input version is `d2add70d5ce58d89c188b7944f561ab9b30477b9`.

| Row ID | Primary words | Independent words | Difference |
| --- | ---: | ---: | ---: |
| `research/imported/agent-session-tests/codex.md` | 2,621 | 2,621 | 0 |
| `design-sketch/11-repo-workflow-and-tooling.md` | 750 | 750 | 0 |
| `research/gates/python/notes.md` | 8,661 | 8,661 | 0 |
| `research/imported/agent-session-tests/CLAUDE_CODE_SESSION_MANAGEMENT.md` | 7,419 | 7,419 | 0 |
| `docs/src/content/docs/workflow/repository-layout.md` | 360 | 360 | 0 |
| `design-sketch/01-overview.md` | 653 | 653 | 0 |
| `research/gates/python/versions.md` | 676 | 676 | 0 |
| `research/imported/agent-peering-tests/claude-to-codex-results.md` | 698 | 698 | 0 |
| `docs/src/content/docs/design/bus.md` | 756 | 756 | 0 |
| `research/imported/agent-peering-tests/DESIGN_REVIEW_ASTRA.md` | 3,146 | 3,146 | 0 |

## Pending independent review

**Untested:** A reviewer using a different model must record their harness and model, source commit, input version, exact commands and exit codes, headline values and denominators, sampled row comparisons, differences and resolutions after #107 provides the notebook tasks. The author-side checks above cannot stand in for that review. Vendor token counts remain unavailable because the operator has not supplied keys or the trusted collector.
