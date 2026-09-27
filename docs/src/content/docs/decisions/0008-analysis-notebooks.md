---
title: "0008: analysis notebooks use Quarto text"
description: Notebook format and Python execution engine for reproducible analyses with private inputs.
---

## Status

Accepted 2026-09-26 for issue #104. Issue #107 activates the chosen tools and checks.

## Context

Each analysis needs prose, executable Python, a readable source diff, repeatable rendering, and a private-input path that cannot become a committed output. The source inventory at `research/gates/data-analysis/versions.md` records Quarto 1.10.18, nbformat 5.11.1, and Jupytext 1.19.5 with source commits and release notes. The repository pins Python 3.14.6. The current prose gates check Markdown files, so #107 must extend their coverage to the chosen notebook format.

| Candidate | Source diff and lint | Execution and output control | Decision |
| --- | --- | --- | --- |
| Quarto `.qmd` | Plain-text Markdown keeps prose, code, and review diffs together. Vale and Markdown gates can parse the source with work in #107 | Explicit Jupyter engine, Python interpreter selection, single-file rerender, and cache controls | Choose |
| Jupyter `.ipynb` | JSON cells, metadata, execution counters, and outputs make ordinary diffs harder to inspect. Prose extraction needs another gate | Native interactive workflow, but Quarto does not execute `.ipynb` on render by default | Reject as the committed source |
| Jupytext paired `.py` or `.md` | Text source is readable. Pairing adds synchronization state and a second representation when `.ipynb` is kept | CLI conversion and execution add a conversion step to the gate | Reject for the first gate |

## Decision

Commit one plain-text Quarto `.qmd` notebook for each analysis. Use Quarto 1.10.18's Jupyter engine with an `ipykernel` Python kernel in the pinned Python 3.14.6 environment. #107's mise task sets `QUARTO_PYTHON` to that environment's interpreter. Keep reusable decisions and transformations in typed pure modules under `agent_orchestration_poc.core.analysis`. Keep file access, process execution, and private-input loading in `agent_orchestration_poc.shell.analysis` or the notebook's thin experiment shell. An analysis notebook calls core functions with values and presents their results.

Render one notebook in the locked environment with cache disabled and execution required. Store source, approved aggregate tables, claims, and sanitized figures in git. Treat Jupyter cache, Quarto `_freeze`, intermediate `.ipynb`, HTML, and any output containing raw private rows as local artifacts that are neither source evidence nor committable output. Do not use frozen or cached results to satisfy verification. A site summary consumes reviewed aggregate tables and figures, not private inputs. The reproducible render task and exclusion rules belong to #107.

## Consequences

**Documented** Quarto binds a Python code block in `.qmd` to Jupyter and can use `QUARTO_PYTHON` to select the interpreter. A single-file render executes even when a project freeze is configured. Its [execution guide](https://quarto.org/docs/computations/execution-options.html), [Python guide](https://quarto.org/docs/computations/python.html), and [project execution guide](https://quarto.org/docs/projects/code-execution.html) describe those controls. The [nbformat schema](https://github.com/jupyter/nbformat/blob/75f819f5b60bc6ffc72145c364132efe5b3c4b35/nbformat/v4/nbformat.v4.5.schema.json) requires code-cell outputs and execution counts, which explains the diff and private-output risk. [Jupytext's paired notebook guide](https://github.com/jupytext/jupytext/blob/3132c6c1cc6738b355c711e07de4666413c42878/website/src/content/docs/using/paired-notebooks.md) describes the synchronization model.

**Inference** Plain-text `.qmd` gives this repository the shortest review path because its existing prose checks can be extended. It uses one committed representation. This is not a runtime proof of Python 3.14.6 kernel compatibility. #107 tests that in a clean, pinned environment. Revisit the format if #107 cannot lint code and prose reliably or a measured analysis requires an interactive notebook capability that `.qmd` cannot preserve.

## Evidence

The research notes, source versions, and verification protocol under `research/gates/data-analysis/` record the comparison and contract. #107 supplies executable proof.
