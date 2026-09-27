# Work model reference review checks

## Parent title regression

Observed: On Python 3.14.6 and pytest 9.1.1, `mise exec -- uv run pytest tests/test_workflow_forms.py -k 'parent_title_contract or parent_rejects_generated_leading_keys' -q` exited 1 before the validator fix with 4 failed and 7 passed. The old pattern accepted a Roman ordinal and rejected `epic: GitHub monitor` and `initiative: Codex integration`. Other keyed examples already failed because their leading character was uppercase; the new cases retain those boundaries.

Verified: The same command exited 0 after the initial fix with 13 passed and 80 deselected. The table covers initiative and epic keys, numeric and Roman ordinals, empty summaries, ordinary summaries, and proper nouns. The property check varies the leading key and number. A final row also rejects `1st` as a leading ordinal.

## Integrated checks

Verified: After merging `origin/main` at `d3a8bf9`, `mise run fmt` and `git diff --check` exited 0. The final `mise run check` exited 0, after an earlier run stopped when the Go checker scanned a changing pnpm install directory. Standalone `mise run check:go` exited 0 between those runs. The final workflow form gate reported 94 passed and matching generated files; the integrated Python coverage run reported 295 passed. Coverage floors reported Python core lines 99.75%, Python core branches 97.30%, Python shell lines 85.13%, Go core statements 96.43%, Go shell statements 74.58%, and Go core branches 94.74%.

Verified: `mise run check:mutation` exited 0. Go killed 145 of 149 mutants (97.32%), and Python killed 1414 of 1553 (91.05%).

The generated workflow reference already states that parent titles have no key or ordinal, so this fix requires no change to its sentence or generated files.
