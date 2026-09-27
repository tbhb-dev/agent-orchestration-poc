---
title: Data analysis conventions
description: Notebook, module, evidence, verification, privacy, and chart rules for repository analyses.
---

## Decisions and locations

Use [decision 0008](/decisions/0008-analysis-notebooks/) for plain-text Quarto `.qmd` notebooks with the Jupyter Python engine and [decision 0009](/decisions/0009-analysis-visualization/) for Matplotlib SVG charts. Keep a notebook beside its research or experiment evidence, such as `research/gates/document-size/measure.qmd` or `experiments/18-transcript-retro/retro.qmd`. Keep reusable typed transformations under `src/agent_orchestration_poc/core/analysis/` and I/O adapters under `src/agent_orchestration_poc/shell/analysis/`. Experiment notebooks and scripts are the thin shell for one analysis.

The functional core takes values and returns values. It does not open files, write charts, spawn processes, read environment variables, or receive a writer or connection that can perform I/O. The shell reads private and committed inputs, calls the core, then writes approved aggregate tables and chart files. Test core functions with plain values, table cases, and properties without mocks. Test shell I/O separately. The import boundary and mutation gates in [decision 0003](/decisions/0003-functional-core-imperative-shell/) and [decision 0005](/decisions/0005-property-and-mutation-testing/) apply to analysis modules.

## Evidence and claims

Follow the [verification protocol](https://github.com/tbhb/agent-orchestration-poc/blob/main/research/gates/data-analysis/verification-protocol.md). Commit a query or script for each number and a claims row pointing to its result-table row. Also commit the approved aggregate table and a review artifact from a different model. A second method separately recomputes every numerical result cited in a conclusion and at least ten deterministically selected supporting rows, or all rows when fewer than ten exist. Compare every chart row with its source table. Retain the exact commands, versions, source IDs, row IDs, differences, and resolutions in the review artifact.

Use the `AGENTS.md` evidence labels precisely. A `verified` claim has a targeted check at recorded versions. An `observed` claim describes one run and its conditions. A `documented` claim cites versioned documentation. An `inference` names its premises and uncertainty. `help-text`, `schema`, and `untested` do not establish runtime behavior. In a summary, cite the claim ID, committed query, result row, source version, and limitation near the statement. Never convert an unknown field into zero without a documented rule.

## Notebook execution and private inputs

Issue #107 adds the analysis dependency group, project Quarto pin, prose and code lint, `mise run notebooks:lint`, `mise run notebooks:render -- <path>`, `mise run notebooks:verify -- <path>`, CI, and a keyless synthetic example. Those commands are the intended rerun interface after #107 is merged. Run `mise run check` and `mise run docs:build` for the repository and site checks. Private analysis starts after #107 passes its runnable gate. Issues #100 and #103 wait for that activation.

Run notebooks in the pinned Python environment through Quarto's Jupyter engine. Rerun one notebook with execution enabled and cache disabled. Do not satisfy verification from a Jupyter cache, Quarto `_freeze`, or a previously rendered `.ipynb` or HTML file. Record input version or hash, command, environment versions, and exit code. Commit only reviewed source, claims, aggregate tables, short redacted examples when authorized, and static figures. Generated notebook output stays outside git unless #107 names a synthetic artifact for its gate.

Raw private inputs live under `.holding/` in the main clone. Worktrees read them by absolute path with authorization and never write there. Do not commit private inputs, raw rows, input-to-opaque-ID mappings, notebook outputs that include raw records, caches, credentials, tokens, or keys. Scan evidence before committing. #107 adds `.holding/` exclusions to the repository and all relevant checkers and proves the keyless privacy gate. A docs summary uses only reviewed aggregate tables and figures. The site build reads those committed outputs.

## Charts and docs site

For each chart, commit its producing notebook or typed source, sanitized source table, stable row IDs, and `-light.svg` and `-dark.svg` files. Set explicit figure size, palette, background, text and grid colors, font, SVG hash salt, and metadata. Use labels, units, and a text alternative that states the main values. Put the source table next to the chart in the summary or link to it. Review visual marks and labels against every source-table row in both variants. The docs build checks that the static assets render and links resolve, while the review artifact records numeric and visual agreement.

Publish an analysis summary as a site page with `title` and `description` frontmatter and no body H1. State the question, population, method, measured findings, documented context, inferences, limitations, claim IDs, chart tables, and exact rerun commands. Use one line per paragraph and sentence case headings. Keep a chart's source table and summary free of private raw records. #107 validates a synthetic summary and chart rendering before real measurements begin.
