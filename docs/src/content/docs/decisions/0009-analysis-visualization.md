---
title: "0009: analysis charts use Matplotlib SVG"
description: Static chart library, reproducible output, and accessible chart review rules.
---

## Status

Accepted 2026-09-26 for issue #104. Issue #107 pins and validates the library.

## Context

The docs site currently supports Mermaid and Excalidraw for diagrams. Analysis charts need numeric marks tied to a reviewed data table. They must be readable on light and dark backgrounds and produce useful source diffs. Static output avoids an interactive JavaScript runtime. The source inventory at `research/gates/data-analysis/versions.md` records Matplotlib 3.11.2, Altair 6.3.0, and Plotly.py 7.1.0.

| Candidate | Static output and typing | Additional render surface | Decision |
| --- | --- | --- | --- |
| Matplotlib | Native SVG output, configurable face colors, fixed SVG hash salt, and bundled `.pyi` stubs plus `py.typed` | Python renderer already required for notebooks | Choose |
| Altair | Declarative chart specifications and SVG export | Static image export needs `vl-convert-python` | Reject for the first gate |
| Plotly.py | Static SVG and interactive figures | Static export uses Kaleido and a Chrome or Chromium installation | Reject for the first gate |

## Decision

Use one visualization library, Matplotlib 3.11.2, to generate static SVG charts from committed aggregate source tables. Render separate light and dark SVG variants with explicit background, text, grid, and mark colors. Set figure size, fonts, `svg.hashsalt`, and SVG metadata so two runs in the pinned environment can be compared. Do not rely on color alone. Label axes, units, series, and relevant values, and provide a text alternative plus an adjacent source table. Use a distinguishable palette in both variants and check contrast during review.

Chart-producing Python is source code in the notebook or a typed analysis module. A chart has a stable ID, an input table path and row IDs, two SVG paths, and a claims-table link. The reviewer checks the SVG marks and labels against every row used by the chart. #107 adds the executable diff and docs-site rendering checks. This decision does not add a new library or chart asset.

## Consequences

**Documented** Matplotlib's [tagged configuration](https://github.com/matplotlib/matplotlib/blob/d3ca9172e392048ec242b90e8423e88d1a3000b2/lib/matplotlib/mpl-data/matplotlibrc) defines the face colors for figures, SVG font behavior, and `svg.hashsalt`. The same tag includes [type stubs](https://github.com/matplotlib/matplotlib/blob/d3ca9172e392048ec242b90e8423e88d1a3000b2/lib/matplotlib/figure.pyi) and [`py.typed`](https://github.com/matplotlib/matplotlib/blob/d3ca9172e392048ec242b90e8423e88d1a3000b2/lib/matplotlib/py.typed). Altair's [static export guide](https://altair-viz.github.io/user_guide/saving_charts.html) requires `vl-convert-python`. Plotly's [static export guide](https://plotly.com/python/static-image-export/) requires Kaleido and Chrome or Chromium.

**Inference** Matplotlib needs fewer rendering dependencies for these static reports. Fixed settings make source diffs useful, but byte-for-byte equality across different operating systems or font stacks is untested. #107 tests repeatability inside its pinned CI image. Revisit this choice if accessible SVG output or typed usage fails the gate, or if later work has a documented need for interaction.

## Evidence

The research notes, source versions, and verification protocol under `research/gates/data-analysis/` record the comparison, source commits, and chart review rule.
