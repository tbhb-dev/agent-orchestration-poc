# Skipscan review evidence for #300

The round 4 regressions for #300 reproduced nine failures on reviewed commit `6466a3f` with `mise run check:pytest -- tests/test_skipscan.py -q`: comment and ordinary-string triple markers, a marker 20 lines before executable code, three lines mixing code patterns with prose, and three mixed-clause negations. The uncertain quote-state and repeated-word regressions were added while fixing those cases.

At the current worktree state for #300, `mise run check:pytest -- tests/test_skipscan.py -q` passed 151 scanner tests. `mise run check` passed, including 1,021 standard tests, 1,146 coverage tests, Python core line coverage 97.67%, and Python core branch coverage 94.36%. `mise run check:mutation` passed: Go core 97.32% (145 killed of 149) and Python core 90.01% (11,763 killed of 13,068). `mise run build` passed.

The runnable workflow and CI probe for #300 remain in stacked PR #315; this file records the pure scanner review fixes in PR #312.
