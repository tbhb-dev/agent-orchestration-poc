# Inventory versions and source evidence

Observed: native Claude records identify Claude Code 2.1.283 in the private snapshot. Native Codex session metadata identifies CLI 0.157.1, 0.156.1, and 0.148.0-alpha.9. The inventory reads the frozen snapshot and does not infer missing model or effort values from these versions.

Documented: OpenAI Codex protocol source at commit `1c7c43cd856a1ef451cb7ff9dc1b701ac7942c9d` defines `SessionMeta`, `TurnContextItem`, and `TokenUsageRecord` in `codex-rs/protocol/src/protocol.rs`, and call and output item variants in `codex-rs/protocol/src/models.rs`. This source was read on 2026-10-07. The source checkout may differ from the snapshot CLI releases. The parser follows observed record shapes in the snapshot and reports unsupported values as unknown.

Observed: the Claude Code source checkout at commit `7779afb12e3635f46f56ec823979d68350ae000b` does not provide a versioned native JSONL schema for these private records in its README. Claude records are inventoried from their observed fields and await a format-specific normalization slice.

Documented: the repository pins Python 3.14.6, pytest 9.1.1, Hypothesis 6.168.1, Quarto 1.10.18, Ruff 0.16.9, and the analysis environment in `mise.toml` and `pyproject.toml`. The [data analysis conventions](../../docs/src/content/docs/guides/data-analysis-conventions.md) and [verification protocol](../../research/gates/data-analysis/verification-protocol.md) set the method for this notebook.
