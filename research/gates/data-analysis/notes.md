# Data analysis stack research

## Scope and decision

Issue #104 covers JSON lines transcripts, logs, and GitHub payloads in the low hundreds of megabytes. The first analysis needs auditable grouping, filtering, and joins over normalized events. Choose DuckDB 1.5.5 as the only data engine for the first runnable gate in #107. Use Python's standard library to normalize irregular records before SQL where needed. Do not add Polars or pyarrow to the first dependency group. This is a minimum-tool decision, not a measured speed ranking. The [source inventory](versions.md) records release tags and commits.

Transcript and log records can vary by event type, while GitHub webhook and REST payloads have nested objects and arrays. Normalize each source to rows with opaque IDs and declared claim fields before aggregation, and retain counts of malformed or excluded rows. A JSON lines reader alone does not define event identity, deduplication, or a safe privacy boundary. #108 owns transcript inventory and deduplication, while each analysis records its own population and exclusions.

| Candidate | JSON lines and nested data | Reproducible analysis fit | First gate |
| --- | --- | --- | --- |
| DuckDB 1.5.5 | `read_ndjson` reads JSON lines, `read_json` accepts explicit columns and nested `LIST` or `STRUCT` values | SQL queries can be committed beside claims tables, and one engine covers filters, joins, and aggregates | Select |
| Polars 1.44.2 | `scan_ndjson` returns a lazy frame and accepts a schema | Lazy expressions and streaming are useful if later workloads need them, but add a second transformation API to the first gate | Exclude for now |
| pyarrow 25.0.1 | `pyarrow.json.read_json` reads JSON lines and `open_json` streams batches, while inferred types freeze after the first block | Strong interchange and columnar I/O, but the first reports do not require a separate Arrow table layer | Exclude for now |

**Documented:** DuckDB's [JSON loading reference](https://duckdb.org/docs/stable/data/json/loading_json) and [tagged table function](https://github.com/duckdb/duckdb/blob/d8cdaa33fda8df955cc76ef58a280f68f4cd43fa/extension/json/json_functions/read_json.cpp) define `read_ndjson`, explicit `columns`, and `ignore_errors`. Keep `ignore_errors` false for claim-producing inputs so malformed rows fail rather than silently changing denominators. Explicitly type fields used in a headline claim and record the raw row count before filtering. Schema inference on heterogeneous payloads remains a risk to check with fixtures in #107.

**Documented:** Polars' [tagged `scan_ndjson` API](https://github.com/pola-rs/polars/blob/1bd8ec12f42d40fcec62badf32ef2177d2377d8d/py-polars/src/polars/io/ndjson.py) supports lazy scans, schema control, and an inference length. Its [version 1 migration guide](https://github.com/pola-rs/polars/blob/1bd8ec12f42d40fcec62badf32ef2177d2377d8d/docs/source/releases/upgrade/1.md) was checked before selecting a future-compatible version. Polars is a credible replacement if a measured DuckDB workload needs lazy frame transformations or streaming. No benchmark was run for this issue.

**Documented:** Arrow's [tagged JSON guide](https://github.com/apache/arrow/blob/beccec0d0c451b7aa3e4530416ac431b3c035c69/docs/source/python/json.rst) limits its JSON reader to line-delimited records. `open_json` can read batches, but inferred types freeze after the first block unless an explicit schema is supplied. Its [25.0.1 release notes](https://arrow.apache.org/release/25.0.1.html) do not change this assessment. Add pyarrow only when an actual Parquet or Arrow interchange requirement is shown.

**Inference:** DuckDB plus the Python standard library is enough for the first normalized JSON lines inputs. This does not establish that DuckDB is fastest or that it accepts every raw transcript variant. #108 owns private snapshot normalization, and #107 owns a synthetic runnable compatibility test. Private raw files remain in the main clone's `.holding/` and are read by worktrees through an absolute path. This research did not read, copy, or modify their contents.

## Research and documentation checks

| Command | Result | Meaning |
| --- | --- | --- |
| `gh api repos/tbhb/agent-orchestration-poc/issues/104 --jq .body` | exit 0 | Issue specification read |
| `gh api repos/tbhb/agent-orchestration-poc/issues/104/comments --paginate` | exit 0 | Review history read |
| `mise trust` | exit 0 | Worktree configuration already trusted |
| `mise run vale:sync` | exit 0 | Pinned prose styles synced once |
| `mise exec -- quarto --version` | exit 0, `1.10.18` | Host Quarto version observed, project pin remains #107 work |
| `mise run fmt` | exit 0 | Formatters made no unrelated tracked edits |
| `mise run check` | exit 0 | Repository aggregate, including Vale, Markdown, code, and secrets checks |
| `mise run check:mutation` | exit 0 | Existing Go and Python core mutation gates passed |
| `mise run build` | exit 0 | `agentd` and `agentctl` built |
| `mise run docs:build` | exit 0 | New guide and decision pages rendered |
| `mise run docs:check-links` | exit 1 | Three pre-existing links in `index.md`, `project/history.md`, and `workflow/tooling.md` failed validation. Chromium also logged a sandbox Mach registration denial. None of the invalid links is in a changed file |
| `mise exec -- vale research/gates/data-analysis/*.md` | exit 0 | New research Markdown had zero alerts |
| `mise exec -- gitleaks dir --redact --no-banner research/gates/data-analysis` | exit 0 | New research evidence had no detected leak |

The `docs:check-links` failure is outside issue #104's allowed paths. It remains a baseline failure to resolve in its owning work item. The ordinary site build still succeeded. Runtime notebook rendering and synthetic analysis belong to #107.
