# Mutation evidence for #314

## Scope and versions

The #314 tests cover scanner behavior without changing the production core, mutation selection, or the 90 percent score floor. The baseline is `0e579b756195fefd1ff6bd24af477463ed001db3`. The original 105-row issue audit, including its 67 unproven entries, describes scanner source at `a384875`. Later #312 review fixes changed mutant numbering and replaced eleven of those mutations' statements.

Source read for #314: `src/agent_orchestration_poc/core/skipscan.py`, `scripts/check-mutation-score.py`, the scanner tests and fixtures, the #300 evidence report, issues #299, #300, and #314, and PRs #312 and #315 with their reviews. No API or scanner behavior changes are included.

Tools: CPython 3.14.6, pytest 9.1.1, Hypothesis 6.168.1, mutmut 3.8.0, and uv 0.12.10. Mutmut source and `README.rst` were read at `14a7230049a5c8abd90c2bb0f7438e30da6471f5` in `/Users/tony/Code/github.com/boxed/mutmut`. Harness: Codex CLI 0.157.1, model `gpt-6-astra`, medium effort.

The shared CPython checkout denied lazy-fetch writes to its `.git/objects/pack` directory under the sandbox for #314. The brief explicitly permits a temporary source clone in this situation. The replacement clone is `/tmp/skipscan-314-cpython`, tag `v3.14.6`, commit `c63aec69bd59c55314c06c23f4c22c03de76fe45`. Read `Lib/tokenize.py` and `Python/Python-tokenize.c`, especially the ERRORTOKEN branch at lines 252 to 258, for the tokenizer equivalence proof below. No host permissions or installations changed.

## Baseline

Verified for #314 before test edits: `mise run check:mutation:python` exited 0. Its final output was:

```text
13155/13155  killed 11853  no tests 0  timeout 2  suspicious 0  survived 1300  skipped 0  type-check killed 0
22.32 mutations/second
Saved CI/CD stats to mutants/mutmut-cicd-stats.json
Python core mutation score: 90.10% (11853 killed of 13155)
```

The progress glyphs are written as labels above. `mise exec -- uv run mutmut results` reported these 128 scanner survivors at the baseline for #314:

```text
agent_orchestration_poc.core.skipscan.x_event_pr_number__mutmut_27: survived
agent_orchestration_poc.core.skipscan.x_redacted_lines__mutmut_2: survived
agent_orchestration_poc.core.skipscan.x_redacted_lines__mutmut_23: survived
agent_orchestration_poc.core.skipscan.x_excerpt__mutmut_1: survived
agent_orchestration_poc.core.skipscan.x_excerpt__mutmut_2: survived
agent_orchestration_poc.core.skipscan.x_excerpt__mutmut_11: survived
agent_orchestration_poc.core.skipscan.x__blocks__mutmut_15: survived
agent_orchestration_poc.core.skipscan.x__blocks__mutmut_18: survived
agent_orchestration_poc.core.skipscan.x__blocks__mutmut_19: survived
agent_orchestration_poc.core.skipscan.x__inline_code__mutmut_8: survived
agent_orchestration_poc.core.skipscan.x__python_string__mutmut_5: survived
agent_orchestration_poc.core.skipscan.x__python_string__mutmut_14: survived
agent_orchestration_poc.core.skipscan.x__python_string__mutmut_15: survived
agent_orchestration_poc.core.skipscan.x__python_string__mutmut_17: survived
agent_orchestration_poc.core.skipscan.x__inert_triple_markers__mutmut_5: survived
agent_orchestration_poc.core.skipscan.x__inert_triple_markers__mutmut_9: survived
agent_orchestration_poc.core.skipscan.x__inert_triple_markers__mutmut_12: survived
agent_orchestration_poc.core.skipscan.x__inert_triple_markers__mutmut_13: survived
agent_orchestration_poc.core.skipscan.x__inert_triple_markers__mutmut_16: survived
agent_orchestration_poc.core.skipscan.x__inert_triple_markers__mutmut_33: survived
agent_orchestration_poc.core.skipscan.x__triple_spans__mutmut_4: survived
agent_orchestration_poc.core.skipscan.x__triple_spans__mutmut_16: survived
agent_orchestration_poc.core.skipscan.x__triple_spans__mutmut_19: survived
agent_orchestration_poc.core.skipscan.x__triple_spans__mutmut_20: survived
agent_orchestration_poc.core.skipscan.x__triple_spans__mutmut_21: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_3: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_5: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_15: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_17: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_18: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_21: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_22: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_23: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_24: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_36: survived
agent_orchestration_poc.core.skipscan.x__threshold__mutmut_37: survived
agent_orchestration_poc.core.skipscan.x__tracked__mutmut_7: survived
agent_orchestration_poc.core.skipscan.x__tracked__mutmut_9: survived
agent_orchestration_poc.core.skipscan.x__tracked__mutmut_18: survived
agent_orchestration_poc.core.skipscan.x__tracked__mutmut_20: survived
agent_orchestration_poc.core.skipscan.x__tracked__mutmut_21: survived
agent_orchestration_poc.core.skipscan.x__tracked__mutmut_27: survived
agent_orchestration_poc.core.skipscan.x__tracked__mutmut_37: survived
agent_orchestration_poc.core.skipscan.x__tracked__mutmut_44: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_8: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_10: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_11: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_18: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_38: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_40: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_57: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_62: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_63: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_64: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_69: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_70: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_80: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_100: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_114: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_116: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_128: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_130: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_144: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_150: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_156: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_157: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_158: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_159: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_165: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_166: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_167: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_195: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_196: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_198: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_199: survived
agent_orchestration_poc.core.skipscan.x_scan_text__mutmut_206: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_2: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_3: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_4: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_5: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_6: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_7: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_11: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_12: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_39: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_42: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_52: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_56: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_90: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_110: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_164: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_165: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_168: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_169: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_171: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_183: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_186: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_195: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_198: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_204: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_210: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_221: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_222: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_225: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_228: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_230: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_233: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_237: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_242: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_259: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_260: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_296: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_314: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_336: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_338: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_363: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_364: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_366: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_367: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_371: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_374: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_383: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_392: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_399: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_402: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_406: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_407: survived
agent_orchestration_poc.core.skipscan.x_scan_diff__mutmut_408: survived
```

## Result

Verified for #314 in the focused mutation pass: `mise exec -- uv run mutmut run 'agent_orchestration_poc.core.skipscan.*'` reduced the scanner's 128 survivors to 46. All 82 additional outcomes are killed, and every remaining scanner mutant has an equivalence reason below. The focused scanner and event suite passes 236 tests with `mise run check:pytest -- tests/test_skipscan.py tests/test_skipscan_events.py -q`.

Verified for #314: `mise run check` passed 1,126 standard tests and 1,267 tests in the coverage run, including integration tests. Python core line coverage is 97.75 percent and branch coverage is 94.59 percent. `mise run fmt`, `mise run build`, and the report's historical reproduction command passed. The fresh full mutation run is being recorded before publication.

## Original 67-mutant audit

Each ID in this table has the prefix `agent_orchestration_poc.core.skipscan.`. The current-ID mapping was obtained by regenerating mutations with mutmut 3.8.0 and comparing the changed source expressions, with call-site disambiguation where expressions repeat. For #314, 52 current mutations are killed, eleven historical mutations are killed by the same plain-value expectations on the historical original, and four are equivalent. The historical check is separate from the current score and changes no production file.

| Original audit ID | Classification | Evidence or reason |
| --- | --- | --- |
| `x__blocks__mutmut_15` | Killed | `x__blocks__mutmut_15` in the current mutation run. |
| `x__blocks__mutmut_18` | Killed | `x__blocks__mutmut_18` in the current mutation run. |
| `x__blocks__mutmut_19` | Killed | `x__blocks__mutmut_19` in the current mutation run. |
| `x__inline_code__mutmut_8` | Killed | `x__inline_code__mutmut_8` in the current mutation run. |
| `x__python_string__mutmut_5` | Equivalent | Current `x__python_string__mutmut_5`. For the single physical line supplied by the scanner, appending `XX` before and after the synthetic newline cannot introduce a closing quote. Every complete first-line STRING token and its columns stay the same. An incomplete string still raises, and a suffix without a string still returns false. |
| `x__python_string__mutmut_14` | Killed | `x__python_string__mutmut_14` in the current mutation run. |
| `x__python_string__mutmut_15` | Killed | `x__python_string__mutmut_15` in the current mutation run. |
| `x__python_string__mutmut_17` | Killed | `x__python_string__mutmut_17` in the current mutation run. |
| `x__tracked__mutmut_9` | Killed | `x__tracked__mutmut_7` in the current mutation run. |
| `x__tracked__mutmut_11` | Killed | `x__tracked__mutmut_9` in the current mutation run. |
| `x__tracked__mutmut_20` | Killed | `x__tracked__mutmut_18` in the current mutation run. |
| `x__tracked__mutmut_23` | Killed | `x__tracked__mutmut_21` in the current mutation run. |
| `x__tracked__mutmut_29` | Killed | `x__tracked__mutmut_27` in the current mutation run. |
| `x__tracked__mutmut_46` | Killed | `x__tracked__mutmut_44` in the current mutation run. |
| `x_scan_text__mutmut_55` | Equivalent | Current `x_scan_text__mutmut_69`. The negation regular expression ends in `skipped$`. A clause ending at a `skip` match can never satisfy it, so removing `skip` from the preceding membership test has no effect. |
| `x_scan_text__mutmut_56` | Equivalent | Current `x_scan_text__mutmut_70`. The negation regular expression ends in `skipped$`. A clause ending at a `skip` match can never satisfy it, so removing `skip` from the preceding membership test has no effect. |
| `x_scan_text__mutmut_100` | Killed | `x_scan_text__mutmut_114` in the current mutation run. |
| `x_scan_text__mutmut_114` | Killed | `x_scan_text__mutmut_128` in the current mutation run. |
| `x_scan_text__mutmut_136` | Killed | `x_scan_text__mutmut_150` in the current mutation run. |
| `x_scan_text__mutmut_142` | Killed | `x_scan_text__mutmut_156` in the current mutation run. |
| `x_scan_text__mutmut_143` | Killed | `x_scan_text__mutmut_157` in the current mutation run. |
| `x_scan_text__mutmut_145` | Killed | `x_scan_text__mutmut_159` in the current mutation run. |
| `x_scan_text__mutmut_151` | Killed | `x_scan_text__mutmut_165` in the current mutation run. |
| `x_scan_text__mutmut_152` | Killed | `x_scan_text__mutmut_166` in the current mutation run. |
| `x_scan_text__mutmut_181` | Killed | `x_scan_text__mutmut_195` in the current mutation run. |
| `x_scan_text__mutmut_182` | Killed | `x_scan_text__mutmut_196` in the current mutation run. |
| `x_scan_text__mutmut_184` | Killed | `x_scan_text__mutmut_198` in the current mutation run. |
| `x_scan_text__mutmut_185` | Equivalent | Current `x_scan_text__mutmut_199`. Every PROSE match is at most 16 characters. Thus `end + 100` is at most `start + 116`. For start at least 90, `left + 240` is `start + 150`, and for smaller starts it is 240. The window is always determined by `left + 240`, even when end defaults to zero. |
| `x_scan_text__mutmut_192` | Killed | `x_scan_text__mutmut_206` in the current mutation run. |
| `x_scan_diff__mutmut_39` | Killed | `x_scan_diff__mutmut_39` in the current mutation run. |
| `x_scan_diff__mutmut_42` | Killed | `x_scan_diff__mutmut_42` in the current mutation run. |
| `x_scan_diff__mutmut_52` | Killed | `x_scan_diff__mutmut_52`, `x_scan_diff__mutmut_237` in the current mutation run. |
| `x_scan_diff__mutmut_56` | Killed | `x_scan_diff__mutmut_56` in the current mutation run. |
| `x_scan_diff__mutmut_90` | Killed | `x_scan_diff__mutmut_90` in the current mutation run. |
| `x_scan_diff__mutmut_110` | Killed | `x_scan_diff__mutmut_110` in the current mutation run. |
| `x_scan_diff__mutmut_159` | Killed | `x_scan_diff__mutmut_164` in the current mutation run. |
| `x_scan_diff__mutmut_160` | Killed | `x_scan_diff__mutmut_165` in the current mutation run. |
| `x_scan_diff__mutmut_163` | Killed | `x_scan_diff__mutmut_168` in the current mutation run. |
| `x_scan_diff__mutmut_199` | Killed | `x_scan_diff__mutmut_204` in the current mutation run. |
| `x_scan_diff__mutmut_221` | Historical mutation killed | `diffs.tsv:50` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_224` | Historical mutation killed | `diffs.tsv:49` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_227` | Killed | `x_scan_diff__mutmut_221` in the current mutation run. |
| `x_scan_diff__mutmut_228` | Killed | `x_scan_diff__mutmut_222` in the current mutation run. |
| `x_scan_diff__mutmut_233` | Historical mutation killed | `diffs.tsv:35` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_234` | Historical mutation killed | `diffs.tsv:35` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_239` | Killed | `x_scan_diff__mutmut_225` in the current mutation run. |
| `x_scan_diff__mutmut_242` | Killed | `x_scan_diff__mutmut_228` in the current mutation run. |
| `x_scan_diff__mutmut_244` | Killed | `x_scan_diff__mutmut_230` in the current mutation run. |
| `x_scan_diff__mutmut_247` | Killed | `x_scan_diff__mutmut_233` in the current mutation run. |
| `x_scan_diff__mutmut_251` | Historical mutation killed | `test_diff_propagates_pending_runs[build.sh]` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_255` | Historical mutation killed | `test_diff_propagates_pending_runs[build.sh]` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_260` | Historical mutation killed | `diffs.tsv:48` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_336` | Killed | `x_scan_diff__mutmut_336` in the current mutation run. |
| `x_scan_diff__mutmut_363` | Killed | `x_scan_diff__mutmut_363` in the current mutation run. |
| `x_scan_diff__mutmut_364` | Killed | `x_scan_diff__mutmut_364` in the current mutation run. |
| `x_scan_diff__mutmut_366` | Killed | `x_scan_diff__mutmut_366` in the current mutation run. |
| `x_scan_diff__mutmut_367` | Killed | `x_scan_diff__mutmut_367` in the current mutation run. |
| `x_scan_diff__mutmut_371` | Killed | `x_scan_diff__mutmut_371` in the current mutation run. |
| `x_scan_diff__mutmut_374` | Killed | `x_scan_diff__mutmut_374` in the current mutation run. |
| `x_scan_diff__mutmut_392` | Killed | `x_scan_diff__mutmut_392` in the current mutation run. |
| `x_scan_diff__mutmut_402` | Historical mutation killed | `diffs.tsv:35` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_404` | Historical mutation killed | `diffs.tsv:36` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_406` | Historical mutation killed | `diffs.tsv:36` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_409` | Historical mutation killed | `diffs.tsv:51` passes the historical original and produces a different result with this mutation. |
| `x_scan_diff__mutmut_414` | Killed | `x_scan_diff__mutmut_406` in the current mutation run. |
| `x_scan_diff__mutmut_415` | Killed | `x_scan_diff__mutmut_407` in the current mutation run. |
| `x_scan_diff__mutmut_416` | Killed | `x_scan_diff__mutmut_408` in the current mutation run. |

The older audit classified `x_excerpt__mutmut_11` as equivalent. The #314 test `test_exact_excerpt_limit_does_not_crop_at_match_offset` disproves that classification: an exactly 240-character line with start 120 must remain intact. The changed comparison crops it. This mutation is now killed.

## Remaining equivalent mutants

These are source-level equivalence arguments under the scanner's input domain for #314, not claims that tests distinguish identical behavior. Text helpers receive individual physical lines. Diff helpers receive complete unified diffs with file and hunk headers. All mutants remain included in the score denominator.

| Current mutant ID | Reason |
| --- | --- |
| `x_redacted_lines__mutmut_2` | The PEM state is read for truthiness only. Both `None` and `False` mean outside a PEM block, and the next opening marker replaces the state. |
| `x_redacted_lines__mutmut_23` | The PEM state is read for truthiness only. Both `None` and `False` mean outside a PEM block, and the next opening marker replaces the state. |
| `x_excerpt__mutmut_1` | The omitted start becomes 1 instead of 0. Both yield `left = 0`, so the same right endpoint and excerpt result follow. |
| `x_excerpt__mutmut_2` | The omitted end becomes 1 instead of 0. Both `end + 100` values are below `left + 240`, so neither changes the right endpoint. |
| `x__python_string__mutmut_5` | For the single physical line supplied by the scanner, appending `XX` before and after the synthetic newline cannot introduce a closing quote. Every complete first-line STRING token and its columns stay the same. An incomplete string still raises, and a suffix without a string still returns false. |
| `x__inert_triple_markers__mutmut_9` | The scanner supplies one physical line. Once the tokenizer emits a token on a subsequent line, no later token starts on line 1. Ending iteration instead of continuing cannot add a first-line span. |
| `x__inert_triple_markers__mutmut_12` | Unreachable with pinned CPython 3.14.6. `Python/Python-tokenize.c` handles ERRORTOKEN by setting an exception and exiting before constructing a yielded token. `Lib/tokenize.py` converts SyntaxError into TokenError, so this ERRORTOKEN body never executes. No synthetic tokenizer or mock is used to reach it. |
| `x__inert_triple_markers__mutmut_13` | Unreachable with pinned CPython 3.14.6. `Python/Python-tokenize.c` handles ERRORTOKEN by setting an exception and exiting before constructing a yielded token. `Lib/tokenize.py` converts SyntaxError into TokenError, so this ERRORTOKEN body never executes. No synthetic tokenizer or mock is used to reach it. |
| `x__tracked__mutmut_20` | Only letters in the regular expression change case. `re.IGNORECASE` remains active, so the matching language is unchanged. |
| `x__tracked__mutmut_37` | Only letters in the regular expression change case. `re.IGNORECASE` remains active, so the matching language is unchanged. |
| `x_scan_text__mutmut_8` | The fence state is checked for truthiness until an opening marker assigns its delimiter. Both `None` and the empty string mean no active fence. |
| `x_scan_text__mutmut_10` | The initial ignore-fence state is read only with an active fence. Opening a fence always assigns this state before that read, so the changed initial value is overwritten. |
| `x_scan_text__mutmut_11` | The initial ignore-fence state is read only with an active fence. Opening a fence always assigns this state before that read, so the changed initial value is overwritten. |
| `x_scan_text__mutmut_18` | FENCE_RE captures exactly three delimiter characters. Slicing that capture at 3 or 4 returns the same delimiter. |
| `x_scan_text__mutmut_38` | FENCE_RE captures exactly three delimiter characters. Slicing that capture at 3 or 4 returns the same delimiter. |
| `x_scan_text__mutmut_40` | The fence state is checked for truthiness until an opening marker assigns its delimiter. Both `None` and the empty string mean no active fence. |
| `x_scan_text__mutmut_57` | Python string search treats a `None` start as the beginning, the same as start 0. |
| `x_scan_text__mutmut_63` | The change can only omit a punctuation mark at column 0. If there is a subsequent delimiter it determines the same clause. Otherwise the clause gains one leading punctuation character, which cannot alter either unanchored negation regular expression. |
| `x_scan_text__mutmut_69` | The negation regular expression ends in `skipped$`. A clause ending at a `skip` match can never satisfy it, so removing `skip` from the preceding membership test has no effect. |
| `x_scan_text__mutmut_70` | The negation regular expression ends in `skipped$`. A clause ending at a `skip` match can never satisfy it, so removing `skip` from the preceding membership test has no effect. |
| `x_scan_text__mutmut_80` | Only regex letter case changes. `re.IGNORECASE` remains active, including the phrase appended to the negation expression. |
| `x_scan_text__mutmut_100` | Only regex letter case changes. `re.IGNORECASE` remains active, including the phrase appended to the negation expression. |
| `x_scan_text__mutmut_116` | Only regex letter case changes. `re.IGNORECASE` remains active, including the phrase appended to the negation expression. |
| `x_scan_text__mutmut_130` | Only regex letter case changes. `re.IGNORECASE` remains active, including the phrase appended to the negation expression. |
| `x_scan_text__mutmut_144` | Only regex letter case changes. `re.IGNORECASE` remains active, including the phrase appended to the negation expression. |
| `x_scan_text__mutmut_158` | Only regex letter case changes. `re.IGNORECASE` remains active, including the phrase appended to the negation expression. |
| `x_scan_text__mutmut_167` | Only regex letter case changes. `re.IGNORECASE` remains active, including the phrase appended to the negation expression. |
| `x_scan_text__mutmut_199` | Every PROSE match is at most 16 characters. Thus `end + 100` is at most `start + 116`. For start at least 90, `left + 240` is `start + 150`, and for smaller starts it is 240. The window is always determined by `left + 240`, even when end defaults to zero. |
| `x_scan_diff__mutmut_2` | For the supported complete unified diff, a file header and hunk header assign the path, both line counters, and triple-quote state before content uses them. The initial flush has no collected lines, so the changed initial value cannot produce a finding. |
| `x_scan_diff__mutmut_3` | For the supported complete unified diff, a file header and hunk header assign the path, both line counters, and triple-quote state before content uses them. The initial flush has no collected lines, so the changed initial value cannot produce a finding. |
| `x_scan_diff__mutmut_4` | For the supported complete unified diff, a file header and hunk header assign the path, both line counters, and triple-quote state before content uses them. The initial flush has no collected lines, so the changed initial value cannot produce a finding. |
| `x_scan_diff__mutmut_5` | For the supported complete unified diff, a file header and hunk header assign the path, both line counters, and triple-quote state before content uses them. The initial flush has no collected lines, so the changed initial value cannot produce a finding. |
| `x_scan_diff__mutmut_6` | For the supported complete unified diff, a file header and hunk header assign the path, both line counters, and triple-quote state before content uses them. The initial flush has no collected lines, so the changed initial value cannot produce a finding. |
| `x_scan_diff__mutmut_7` | For the supported complete unified diff, a file header and hunk header assign the path, both line counters, and triple-quote state before content uses them. The initial flush has no collected lines, so the changed initial value cannot produce a finding. |
| `x_scan_diff__mutmut_11` | For the supported complete unified diff, a file header and hunk header assign the path, both line counters, and triple-quote state before content uses them. The initial flush has no collected lines, so the changed initial value cannot produce a finding. |
| `x_scan_diff__mutmut_12` | For the supported complete unified diff, a file header and hunk header assign the path, both line counters, and triple-quote state before content uses them. The initial flush has no collected lines, so the changed initial value cannot produce a finding. |
| `x_scan_diff__mutmut_169` | A valid `diff --git` header has the `b/` separator. Splitting once yields two elements, so indexes -1 and +1 select the same destination element. This changes the index, not the split limit as the older audit stated. |
| `x_scan_diff__mutmut_171` | Both the empty string and `None` are falsey when passed as initial quote state. The first marker assigns a real delimiter, and the quote scanner never exposes this internal initial value in a finding. |
| `x_scan_diff__mutmut_183` | A valid unified hunk header contains both numeric line positions. The match always exists, so the changed fallback or forced truthy condition selects the same integer. |
| `x_scan_diff__mutmut_186` | A valid unified hunk header contains both numeric line positions. The match always exists, so the changed fallback or forced truthy condition selects the same integer. |
| `x_scan_diff__mutmut_195` | A valid unified hunk header contains both numeric line positions. The match always exists, so the changed fallback or forced truthy condition selects the same integer. |
| `x_scan_diff__mutmut_198` | A valid unified hunk header contains both numeric line positions. The match always exists, so the changed fallback or forced truthy condition selects the same integer. |
| `x_scan_diff__mutmut_210` | The initial spans value is used only on Python paths, where `_triple_spans` replaces it before either containment test. Other paths short-circuit those containment tests. |
| `x_scan_diff__mutmut_314` | Only regex letter case changes while `re.IGNORECASE` remains active. |
| `x_scan_diff__mutmut_338` | Only regex letter case changes while `re.IGNORECASE` remains active. |
| `x_scan_diff__mutmut_383` | A standard old-file header is before the first hunk. Treating it as a removed line cannot report a CI step, and no added threshold exists at that point. The hunk header clears it before content comparisons. |

## Historical reproduction

For the eleven replaced statements under #314, the regenerated original mutant is evaluated against the historical original using the fixture's expected path, line, phrase, tracking flag, and excerpt. Every reported fixture passes the original and differs under the mutation. The pending-run case uses the inputs from `test_diff_propagates_pending_runs[build.sh]`. The check does not mock tokenization or replace any current core function.

Run this historical probe from the repository root for #314:

```sh
git show a384875:src/agent_orchestration_poc/core/skipscan.py > /tmp/skipscan-314-original.py
mise exec -- uv run python - <<'PY'
import ast
import io
import json
from pathlib import Path
from mutmut.__main__ import write_all_mutants_to_file

source = Path('/tmp/skipscan-314-original.py').read_text()
output = io.StringIO()
write_all_mutants_to_file(
    out=output, source=source,
    filename=Path('src/agent_orchestration_poc/core/skipscan.py'),
)
mutated = output.getvalue()
lines = mutated.splitlines()
nodes = {
    node.name: node for node in ast.parse(mutated).body
    if isinstance(node, ast.FunctionDef)
}
cases = []
fixture = Path('tests/fixtures/skipscan/diffs.tsv')
for number, row in enumerate(fixture.read_text().splitlines(), 1):
    diff, expected, _ = row.split('\t')
    cases.append((f'diffs.tsv:{number}', json.loads(diff), set(), json.loads(expected)))
cases.append((
    'test_diff_propagates_pending_runs[build.sh]',
    'diff --git a/build.sh b/build.sh\n@@ -1 +1 @@\n+# Deferred RFC-12/34\n',
    {'RFC-12/34'},
    [['build.sh', 1, 'Deferred', True, 'Deferred RFC-12/34']],
))
for number in [221, 224, 233, 234, 251, 255, 260, 402, 404, 406, 409]:
    name = f'x_scan_diff__mutmut_{number}'
    original, variant = {}, {}
    exec(compile(source, 'original', 'exec'), original)
    exec(compile(source, 'original', 'exec'), variant)
    node = nodes[name]
    body = '\n'.join(lines[node.lineno - 1:node.end_lineno])
    body = body.replace(f'def {name}(', 'def scan_diff(', 1)
    exec(compile(body, name, 'exec'), variant)
    for label, diff, pending, expected in cases:
        before = original['scan_diff'](diff, 'PR #300', pending)
        actual = [
            [hit['source'].removeprefix('PR #300:'), hit['line'],
             hit['phrase'], hit['tracked'], hit['excerpt']]
            for hit in before
        ]
        if actual != expected:
            continue
        try:
            after = variant['scan_diff'](diff, 'PR #300', pending)
        except Exception as error:
            after = type(error).__name__
        if before != after:
            print(name, label)
            break
    else:
        raise AssertionError(name)
PY
```

Observed historical probe output for #314:

```text
x_scan_diff__mutmut_221 diffs.tsv:50
x_scan_diff__mutmut_224 diffs.tsv:49
x_scan_diff__mutmut_233 diffs.tsv:35
x_scan_diff__mutmut_234 diffs.tsv:35
x_scan_diff__mutmut_251 test_diff_propagates_pending_runs[build.sh]
x_scan_diff__mutmut_255 test_diff_propagates_pending_runs[build.sh]
x_scan_diff__mutmut_260 diffs.tsv:48
x_scan_diff__mutmut_402 diffs.tsv:35
x_scan_diff__mutmut_404 diffs.tsv:36
x_scan_diff__mutmut_406 diffs.tsv:36
x_scan_diff__mutmut_409 diffs.tsv:51
```
