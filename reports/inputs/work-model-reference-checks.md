# Work model reference review checks

## Parent title regression

Observed: On Python 3.14.6 and pytest 9.1.1, `mise exec -- uv run pytest tests/test_workflow_forms.py -k 'parent_title_contract or parent_rejects_generated_leading_keys' -q` exited 1 before the validator fix with 4 failed and 7 passed. The old pattern accepted a Roman ordinal and rejected `epic: GitHub monitor` and `initiative: Codex integration`. Other keyed examples already failed because their leading character was uppercase; the new cases retain those boundaries.

Verified: The same command exited 0 after the initial fix with 13 passed and 80 deselected. The table covered initiative and epic keys, numeric and Roman ordinals, empty summaries, ordinary summaries, and proper nouns. The property check varied the leading key and number. Round two narrows those earlier ordinal expectations to the operator's exact rule.

## Round-two parent title boundary

Observed: On Python 3.14.6 and pytest 9.1.1, `mise exec -- uv run pytest tests/test_workflow_forms.py -k 'parent_title_contract or parent_rejects_generated_leading_keys or parent_accepts_ordinary_lowercase_words' -q` exited 1 before the second validator fix with 15 failed, 14 passed, and 80 deselected. The failing rows included `civil infrastructure`, `CLI tooling`, `CI quality gates`, `mix process`, `DIM review`, and `MIDI support`; Hypothesis shrank an ordinary lowercase summary to `c`.

Observed: Before the fix, direct `validate_issue` probes returned `('parent summary needs text without a leading key or ordinal',)` for `epic: civil infrastructure`, `epic: CLI tooling`, and `epic: CI quality gates`. The same result for `epic: I2-E3 quality gates` and `epic: II: quality gates` was correct, while `epic: GitHub monitor` returned `()`.

Verified: After the fix, the same focused pytest command exited 0 with 29 passed and 80 deselected. The same direct probes returned `()` for `civil infrastructure`, `CLI tooling`, `CI quality gates`, and `GitHub monitor`, and retained the parent-title finding for `I2-E3 quality gates` and `II: quality gates`. The table also covers uppercase single-letter keys, numeric and Roman ordinals with punctuation, `IV -`, numbered phase, part, and step prefixes, ordinary lowercase words, acronyms, and proper nouns. The lowercase-word property test checks that such summaries are never rejected for a key or ordinal.

## Integrated checks

Verified: After merging `origin/main` at `d3a8bf9`, `mise run fmt` and `git diff --check` exited 0. The final `mise run check` exited 0, after an earlier run stopped when the Go checker scanned a changing pnpm install directory. Standalone `mise run check:go` exited 0 between those runs. The final workflow form gate reported 94 passed and matching generated files; the integrated Python coverage run reported 295 passed. Coverage floors reported Python core lines 99.75%, Python core branches 97.30%, Python shell lines 85.13%, Go core statements 96.43%, Go shell statements 74.58%, and Go core branches 94.74%.

Verified: `mise run check:mutation` exited 0. Go killed 145 of 149 mutants (97.32%), and Python killed 1414 of 1553 (91.05%).

The generated workflow reference already states that parent titles have no key or ordinal, so this fix requires no change to its sentence or generated files.

Verified: For the round-two fix, `mise run --jobs=1 check` exited 0 after two default parallel runs stopped when the Go checker scanned a changing Mermaid pnpm directory. The serial aggregate reported 109 passed workflow-form tests, 310 passed integrated Python tests, Python core lines 99.75%, core branches 97.30%, shell lines 85.13%, Go core statements 96.43%, core branches 94.74%, and shell statements 74.58%. Its import contracts and Ruff checks passed. One first serial run exposed a stale assertion for bare `1 quality gates`; the final run passed after changing that assertion to the punctuated ordinal `1. quality gates`.

Verified: For round two, `mise run check:mutation` exited 0. Go killed 145 of 149 mutants (97.32%), and Python killed 1418 of 1557 mutants (91.07%). `mise run build` exited 0.
