# Skipscan review evidence for #318

## PR 327 review round 1

Verified for #318: `git fetch origin && git merge origin/main` reported the branch already current with main at `0e579b756195fefd1ff6bd24af477463ed001db3`.

Verified for #318: with the scanner restored to reviewed commit `59587d9`, `mise run check:pytest -- tests/core/test_skipscan_suppressions.py -k hunk_starting_inside_docstring -q` failed all four cases. The property compiles each complete new module, builds a normal three-context-line unified diff, and compares the finding with the independent added indicator. It covers both triple-quote styles, executable and prose indicators, and docstrings with 3 through 30 padding lines.

The #318 fix grants Python string exemptions only when the visible hunk begins at file line 1. Later hunks lack a proven incoming lexical state and report string contents conservatively. The scanner remains a pure transformation of the supplied diff; it does not read the complete file. Existing tests retain coverage for complete strings in hunks beginning at line 1.

Verified for #318: `mise run check:pytest -- tests/core/test_skipscan_suppressions.py tests/test_skipscan.py -q` passed all 226 tests after restoring the fix. `mise run fmt` and `mise run build` passed.

Verified for #318: `mise run check` passed 1,138 standard tests and all 1,279 coverage tests. The standard suite excludes 141 integration tests that the coverage run includes. Python core coverage reached 97.74 percent of lines and 94.61 percent of branches. Check-generated chart changes were restored before committing.

Verified for #318: `mise run check:mutation` passed. Python core scored 90.22 percent (11,821 killed of 13,102 mutants, with two further mutants classified as timeouts); Go core scored 97.32 percent (145 killed of 149). No thresholds or mutation scope changed.

Documented for #318: CPython 3.14.6 `Doc/library/tokenize.rst` at `c63aec69bd59c55314c06c23f4c22c03de76fe45` describes complete-source tokenization and warns that invalid Python input has undefined behavior. The coordinator supplied this document at `/private/tmp/task-833-tokenize.rst` after unblocking its retrieval. Tests ran with the repository pins: Python 3.14.6, pytest 9.1.1, and Hypothesis 6.168.1.
