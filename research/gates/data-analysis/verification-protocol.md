# Analysis verification protocol

## Claim ledger

Every analysis commits its notebook or query script, sanitized source table, `claims.csv`, and a review artifact. Give every numerical statement in prose, table, or chart a stable claim ID. A `claims.csv` row records `claim_id`, `kind`, `statement`, `value`, `unit`, `population`, `denominator`, `source_ids`, `query_path`, `result_table`, `result_row_id`, `input_version`, `verification`, and `limitations`. Use `kind=headline` for numbers that drive a conclusion and `kind=supporting` for other numbers. The query or script must be committed, its named result row must reproduce the displayed value, and rounding rules must be explicit. A number with unavailable source fields is marked `unavailable`, not estimated without a stated method.

Qualitative claims receive a stable claim ID too. A `kind=documented` row names a versioned source URL and the exact claim it supports. A `kind=inference` row names its premises, reasoning, and uncertainty. Observed behavior uses the `observed` label with the run conditions. Reserve `verified` for a targeted check at recorded versions. These labels follow `AGENTS.md` and do not turn documentation or a proposed mechanism into a measurement.

Keep population boundaries, time zone, excluded rows, duplicate policy, missing fields, and input hashes or source versions with the analysis. For private input, commit only opaque IDs and sanitized aggregate tables. Keep the mapping from opaque IDs to raw records outside git. No query, notebook output, cache, chart metadata, or review artifact may reveal a raw record, prompt, credential, token, key, or private path.

## Independent recomputation

The analysis author runs a second method over the same defined source population, independently of the primary engine and its intermediate tables. It must parse or load the source separately and implement the counting or arithmetic separately. Reusing the primary result table, transformation function, or copied query is not independent. Recompute every headline number and its denominator, then recompute a deterministic sample of at least ten distinct supporting result rows, or every supporting row when fewer than ten exist. Include all chart source rows in the chart comparison even when they are outside the sample.

Choose the supporting sample by sorting unique result-row IDs by the lowercase hexadecimal SHA-256 digest of `"issue-id|" + row_id`, with the ID as a tie breaker. Take the first `min(10, row_count)` IDs. Record the issue ID, complete sorted ID list or a committed hash of it, selected IDs, and input version so a reviewer can regenerate the same sample. Do not sample from raw private IDs whose mapping would be exposed. Compare exact integer counts and Decimal or explicitly rounded values. Record every difference, including zero differences, and resolve mismatches before publication.

## Review and chart checks

A reviewer using a different model reruns the committed query and the independent method in the pinned environment with access to the authorized source inputs. The review artifact records reviewer harness and model, source commit and input version, exact commands with exit codes, every headline value and denominator from both methods, sampled row IDs and results, differences and resolutions, chart file names, and the chart source table rows checked. The reviewer inspects chart marks, labels, units, ordering, and light and dark variants against the committed source table. A visual match alone does not verify the query. A query match alone does not verify the visual encoding.

For each chart, commit the source table, chart-producing source, and reviewed static SVG variants. The chart must read only the committed aggregate table during site builds. The reviewer compares the table's row IDs and plotted values to the rendered marks and reports any omitted, extra, or mislabelled row. The docs site build validates that images and links render. It does not prove the plotted values agree with the table, which is a separate review step.

## Worked paper example

The following four JSON lines are illustrative public data, not the runnable example owned by #107:

```json
{"id":"E01","group":"A","duration":2}
{"id":"E02","group":"A","duration":5}
{"id":"E03","group":"B","duration":3}
{"id":"E04","group":"B","duration":4}
```

The primary committed notebook would execute this query against those four rows:

```sql
WITH events AS (
    SELECT * FROM read_ndjson('example.jsonl', columns = {id: 'VARCHAR', "group": 'VARCHAR', duration: 'INTEGER'})
), grouped AS (
    SELECT "group", SUM(duration) AS duration_total FROM events GROUP BY "group"
)
SELECT 'G-' || "group" AS row_id, "group", duration_total FROM grouped
UNION ALL
SELECT 'G-ALL' AS row_id, 'all' AS "group", SUM(duration_total) FROM grouped
ORDER BY row_id;
```

| Result row ID | Group | `duration_total` |
| --- | --- | ---: |
| G-A | A | 7 |
| G-B | B | 7 |
| G-ALL | all | 14 |

| Claim ID | Kind and statement | Result row or source | Independent check |
| --- | --- | --- | --- |
| N-01 | Headline, total duration is 14 units | `G-ALL`, four events | Python total is 14 |
| N-02 | Supporting, each group totals 7 units | `G-A` and `G-B` | Python group totals are 7 and 7 |
| Q-01 | Documented, Arrow reads only line-delimited JSON | Arrow 25.0.1 Python JSON guide | Reviewer opens the tagged source |

Claim `N-01` is “Total duration is 14 units.” Its claims row points to the committed query and `G-ALL`, and states the four-event population. Claim `N-02` is “Both groups total 7 units.” Its claims row points to `G-A` and `G-B`. The independent method uses Python's `json.loads` on the four original lines and sums `duration` by `group` without reading the SQL result. It obtains A = 2 + 5 = 7, B = 3 + 4 = 7, and 14 overall. All four raw event IDs and both supporting result rows are checked because each set has fewer than ten rows. In a real analysis the reviewer records the deterministic supporting sample rule above, not a hand-picked example.

Claim `Q-01` is “The Arrow JSON reader only accepts line-delimited JSON.” It is `documented`, not `verified`, and cites the [Arrow 25.0.1 source guide](https://github.com/apache/arrow/blob/beccec0d0c451b7aa3e4530416ac431b3c035c69/docs/source/python/json.rst). The example bar chart has exactly two bars, A = 7 and B = 7, in the order of the committed table. Its axis label says “Duration, units,” its text alternative states both values, and the review record checks both SVG variants against `G-A` and `G-B`. The paper example makes no runtime claim.

## Activation boundary

Issue #107 implements `mise run notebooks:lint`, `mise run notebooks:render -- <path>`, and `mise run notebooks:verify -- <path>` and retains the synthetic run and different-model review artifact. Until those gates pass, this protocol is an accepted research rule with an `untested` execution path. Issues #100 and #103 wait for #107 before their measured notebooks run.
