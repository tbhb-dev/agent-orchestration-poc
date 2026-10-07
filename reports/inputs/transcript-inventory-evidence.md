# Session inventory evidence for issue #108

## Scope and input

This is a partial delivery. The source inventory and keyed snapshot manifest cover the private snapshot, while normalized events cover native Codex sessions belonging to this repository. Claude native normalization and captured-run reconciliation remain deferred. Issue #108 stays open. The local-day event window is 2026-09-26T04:00:00Z inclusive through 2026-09-27T04:00:00Z exclusive.

Measured size: scc 4.1.0 classified 518 changed Python code lines in `normalize.py` and `tests/test_transcript_retro.py`. The three added notebook and documentation files contribute 281 nonblank prose lines. Total counted size is 799 units. Fixtures, `reports/inputs/`, and experiment evidence files are excluded by the workflow reference. The complete four-format estimate exceeded 800 units, so this PR holds the native Codex slice and leaves the other formats for separately refined work.

Observed: The read-only snapshot contains 19,381 files and 535,697,753 bytes. The source inventory has 112 included Codex native sessions, 43 Codex native sessions excluded for no repository `cwd` marker, 38 deferred Claude native sources, one Claude native source excluded for no repository `cwd` marker, 279 deferred captured run files, and 18,908 excluded webhook files outside the session-event population. The JSONL inventory has 1,427 records with missing or unparseable timestamps, including metadata records for which timestamps are not supplied. No source read failed in this run. The command was the notebook's `inventory-and-events` cell with the private root and HMAC key supplied through environment variables.

Observed: The normalized native Codex table has 17,372 retained rows: 4,321 calls, 4,315 outputs, 4,315 measured call-to-output waits, 4,421 response usage records, and zero explicit turn aborts. Five rows were duplicate native keys and all five had conflicting compared metadata. The exported rows contain 78 blank effort fields and no blank model fields. Among output rows, 4,159 have blank `output_bytes` because the native output value is not a string. These blanks remain unknown, not zero. See `experiments/18-transcript-retro/evidence/claims.csv` for claim IDs N-01 through N-07 and `events.csv` for the supporting opaque rows.

The snapshot manifest has four HMAC-SHA-256 group digests. Each group digest covers sorted private relative paths and keyed content digests. Its file counts are 155 Codex native, 39 Claude native, 279 captured run, and 18,908 webhook files. The key and the source-to-path map are local files outside git. The operator must retain the key and share it with an authorized reviewer through the approved private channel.

## Independent calculation and sample

Verified: The notebook's second calculation reopened the native JSONL files, counted distinct native IDs independently of `normalize.py`, and obtained 4,321 calls, 4,315 outputs, 4,315 waits, 4,421 usage records, and zero explicit turn aborts. It reread ten sampled raw positions and checked their timestamps, event kinds, and applicable numeric metadata. The sample was selected by sorting SHA-256 of `108|event_id`, then the opaque event ID.

The sampled opaque IDs in selection order were `a9b6e828441993e07d959f16`, `32d3f1a5be66229d3e309c69`, `932cb41d30d58a94a1a53724`, `b62116086018a5ea2969dadc`, `2db951720e4f7ed81ad2c1c6`, `917e3b3920ca772a8fc9b6bb`, `e99ffb0413fe44ee9ac558de`, `ff56f73c7341d5bea7b48494`, `38be30ab7284490dfdd93bb5`, and `7369fadbaa60a4c50164984e`.

Verified: A second-model reviewer using Codex gpt-6-astra at medium effort ran a separate Python 3.14.6 calculation that imported no normalizer functions. `mise exec -- python /private/tmp/issue108-independent.py` exited 0 before and after the cross-midnight repair. It verified the four grouped HMACs and every exported column in all 17,372 retained rows, plus five conflicting duplicate keys. The reviewer found zero discrepancies. `mise exec -- uv run pytest -q tests/test_transcript_retro.py -k cross_midnight` exited 0 with one passing case. The independent script is a local review tool under `/private/tmp` and is not committed because it names private input locations. The committed notebook retains its independent calculation and sample assertions.

## Commands and limits

- `mise run vale:sync`: exit 0.
- `mise run notebooks:lint`: exit 0.
- `mise run check:pytest -- tests/test_transcript_retro.py`: exit 0 with 26 synthetic tests before the final cross-midnight case was added.
- `mise run notebooks:render -- experiments/18-transcript-retro/inventory.qmd`: exit 1 before notebook execution. Quarto attempted to write `jupyter-kernel.log` under the user's application-support directory, which the sandbox denied.
- `mise run notebooks:verify -- experiments/18-transcript-retro/inventory.qmd`: exit 1 after notebook lint passed, for the same Quarto log write denial. No sandbox escape or host change was attempted.
- The notebook's three Python cells were executed directly with `mise exec -- python` from the experiment directory and with the private root and key supplied through environment variables. Exit 0. The cells produced the committed tables and checked the independent counts and sample. The direct execution does not establish that Quarto rendering works.
- `mise run scc:version`: exit 0, scc 4.1.0.
- `mise exec go:github.com/boyter/scc/v4@4.1.0 -- scc --by-file --format json --gen --min --no-config --no-cocomo --no-complexity experiments/18-transcript-retro/normalize.py tests/test_transcript_retro.py`: exit 0. The `Code` count was 518. A Python nonblank-line count over the notebook, README, and versions file gave 281.
- The first `mise run check` exited 3 because Vulture could not see notebook uses of functions loaded dynamically from `normalize.py`. The parser now declares its public exports in `__all__`, and `mise run check:deadcode` exited 0. The full `mise run check` rerun exited 0 after 325.78 seconds.
- The first `mise run check:mutation` passed the Go core at 97.32 percent test efficacy and 100 percent mutator coverage, then failed while collecting the new test under Mutmut's copied tree because that tree omits the experiment parser. The test now resolves the parser in the original checkout when run from Mutmut's copied tree. The full mutation gate rerun exited 0, with the Go core at 97.32 percent test efficacy and 100 percent mutator coverage, and the Python core at 90.26 percent, 8,387 killed of 9,292 mutants.
- `mise run build`: exit 0.
- `mise exec -- gitleaks dir --redact --no-banner experiments/18-transcript-retro tests/fixtures/transcript_retro tests/test_transcript_retro.py reports/inputs/transcript-inventory-evidence.md`: exit 0 with no leaks found.
- A private-output scan using `privacy_findings` over the four committed evidence files exited 0 and found no raw-record field, planted token signature, or original home path.

The direct execution used this exact code after the operator-supplied environment variables were set. Their values are withheld from the committed report:

```sh
mise exec -- python - <<'PY'
import os
from pathlib import Path
notebook = Path('experiments/18-transcript-retro/inventory.qmd').resolve()
os.chdir(notebook.parent)
namespace = {}
for index, cell in enumerate(notebook.read_text().split('```{python}\n')[1:], 1):
    code = cell.split('\n```', 1)[0]
    code = '\n'.join(line for line in code.splitlines() if not line.startswith('#|'))
    exec(compile(code, f'{notebook.name}:cell-{index}', 'exec'), namespace)
PY
```

The executable local verifier in `README.md` recomputes the HMAC groups from the same authorized snapshot without displaying a path, key, or raw record. The initial source inventory includes deferred formats with explicit states, so the event counts are only for included Codex native sessions. The five ambiguous native matches retain the first sorted source representation and are disclosed rather than promoted into additional events.
