# Session inventory evidence for issue #108

## Scope and input

This is a partial delivery. The source inventory and keyed snapshot manifest cover the private snapshot, while normalized events cover native Codex sessions belonging to this repository. Claude native normalization and captured-run reconciliation remain deferred. Issue #108 stays open. The local-day event window is 2026-09-26T04:00:00Z inclusive through 2026-09-27T04:00:00Z exclusive.

The initial slice was measured at 799 units before review. The review fix moves the normalizer to the functional core and adds private-map protection and compressed evidence. Remeasurement gives 867 scc-classified Python code lines and 276 nonblank notebook and documentation lines, or 1143 units. This exceeds the 800-unit limit and needs a coordinator disposition. The complete four-format estimate exceeded 800 units, so this PR still holds only the native Codex slice. Issue #108's allowed-path list was updated for the core, shell, and compressed evidence paths without changing its acceptance criteria.

Observed: The read-only snapshot contains 19,381 files and 535,697,753 bytes. The source inventory has 112 included Codex native sessions, 43 Codex native sessions excluded for no repository `cwd` marker, 38 deferred Claude native sources, one Claude native source excluded for no repository `cwd` marker, 279 deferred captured run files, and 18,908 excluded webhook files outside the session-event population. The JSONL inventory has 1,427 records with missing or unparseable timestamps, including metadata records for which timestamps are not supplied. No source read failed in this run. The command was the notebook's `inventory-and-events` cell with the private root and HMAC key supplied through environment variables.

Observed: The normalized native Codex table has 17,372 retained rows: 4,321 calls, 4,315 outputs, 4,315 measured call-to-output waits, 4,421 response usage records, and zero explicit turn aborts. Five rows were duplicate native keys and all five had conflicting compared metadata. The exported rows contain 78 blank effort fields and no blank model fields. Among output rows, 4,159 have blank `output_bytes` because the native output value is not a string. These blanks remain unknown, not zero. See `experiments/18-transcript-retro/evidence/claims.csv` for claim IDs N-01 through N-07 and `events.csv.gz` for the supporting opaque rows.

The snapshot manifest has four HMAC-SHA-256 group digests. Each group digest covers sorted private relative paths and keyed content digests. Its file counts are 155 Codex native, 39 Claude native, 279 captured run, and 18,908 webhook files. The key and the source-to-path map are local files outside git. The operator must retain the key and share it with an authorized reviewer through the approved private channel.

## Independent calculation and sample

Verified: The notebook's second calculation reopened the native JSONL files, counted distinct native IDs independently of the core normalizer, and obtained 4,321 calls, 4,315 outputs, 4,315 waits, 4,421 usage records, and zero explicit turn aborts. It reread ten sampled raw positions and checked their timestamps, event kinds, and applicable numeric metadata. The sample was selected by sorting SHA-256 of `108|event_id`, then the opaque event ID.

The sampled opaque IDs in selection order were `a9b6e828441993e07d959f16`, `32d3f1a5be66229d3e309c69`, `932cb41d30d58a94a1a53724`, `b62116086018a5ea2969dadc`, `2db951720e4f7ed81ad2c1c6`, `917e3b3920ca772a8fc9b6bb`, `e99ffb0413fe44ee9ac558de`, `ff56f73c7341d5bea7b48494`, `38be30ab7284490dfdd93bb5`, and `7369fadbaa60a4c50164984e`.

Verified: A second-model reviewer using Codex gpt-6-astra at medium effort ran a separate Python 3.14.6 calculation that imported no normalizer functions. `mise exec -- python /private/tmp/issue108-independent.py` exited 0 before and after the cross-midnight repair. It verified the four grouped HMACs and every exported column in all 17,372 retained rows, plus five conflicting duplicate keys. The reviewer found zero discrepancies. `mise exec -- uv run pytest -q tests/test_transcript_retro.py -k cross_midnight` exited 0 with one passing case. The independent script is a local review tool under `/private/tmp` and is not committed because it names private input locations. The committed notebook retains its independent calculation and sample assertions.

## Commands and limits

- `mise run vale:sync`: exit 0.
- `mise run notebooks:lint`: exit 0.
- Review-fix `mise run check:pytest -- tests/test_transcript_retro.py --run-integration`: exit 0, 30 passed, including repository-boundary and private-map tests.
- `mise run check:pytest -- tests/test_transcript_retro.py`: exit 0 with 26 synthetic tests before the final cross-midnight case was added.
- `mise run notebooks:render -- experiments/18-transcript-retro/inventory.qmd`: exit 1 before notebook execution. Quarto attempted to write `jupyter-kernel.log` under the user's application-support directory, which the sandbox denied.
- `mise run notebooks:verify -- experiments/18-transcript-retro/inventory.qmd`: exit 1 after notebook lint passed, for the same Quarto log write denial. No sandbox escape or host change was attempted.
- Review-fix rerun of both pinned notebook tasks with `JUPYTER_RUNTIME_DIR` under `/private/tmp`: each exited 1 before notebook execution because pinned Quarto 1.10.18 still writes its kernel log under macOS Application Support. Installed `bin/quarto.js` lines 28673-28681 and 36531-36538 show this data path comes from the process home directory. The sandbox denied that write. The runtime-dir override did not change it.
- Review-fix direct execution of all three notebook cells with the same snapshot and key: exit 0. It reproduced all 19,381 source states, all 17,372 event rows, the five conflicting duplicate keys, the independent counts and ten-row sample. Deterministic compressed tables retained SHA-256 `0f4d2ec727617202fdb44334463f1a76e3b2651a3bc1625dee532171a7843824` for `events.csv.gz` and `4721cb4e0c30091de5583eeb5e2d3ebb8111ae1e71dc36fa4dcc7e0b80711411` for `inventory.csv.gz` before and after the rerun. Their sizes are 484,252 and 354,066 bytes, respectively, below the hook's 500 KB limit.
- `PREK_HOME=/private/tmp/agent-orchestration-poc-prek mise exec -- prek run check-added-large-files --files experiments/18-transcript-retro/evidence/events.csv.gz experiments/18-transcript-retro/evidence/inventory.csv.gz`: exit 0. The final commit also runs this hook without bypass.
- The notebook's three Python cells were executed directly with `mise exec -- python` from the experiment directory and with the private root and key supplied through environment variables. Exit 0. The cells produced the committed tables and checked the independent counts and sample. The direct execution does not establish that Quarto rendering works.
- `mise run scc:version`: exit 0, scc 4.1.0.
- `mise exec go:github.com/boyter/scc/v4@4.1.0 -- scc --by-file --format json --gen --min --no-config --no-cocomo --no-complexity src/agent_orchestration_poc/core/analysis/transcript_retro.py src/agent_orchestration_poc/shell/analysis/transcript_retro.py tests/test_transcript_retro.py`: exit 0. The `Code` count is 867. A Python nonblank-line count over the notebook, README, and versions file gives 276. The review-fix total is 1143 units.
- The initial `mise run check` exited 0 before the review fix, after Vulture's `__all__` declaration was added for the experiment parser. The review fix imports the normalizer from the functional core; its current check results are recorded below.
- Review-fix `mise run check`: exit 1 at `check:coverage`. The other completed tasks passed, including import contracts, Ruff, dead-code, Vale, 655 ordinary tests, and the Go checks. The coverage suite passed 749 tests and failed only `test_render_synthetic_notebook` when pinned Quarto attempted the same sandbox-denied Jupyter log write. The generated coverage report put Python core lines at 97.25 percent, core branches at 93.42 percent, and shell lines at 74.45 percent, above their floors; the full coverage gate still failed before Go branch scoring.
- The initial `mise run check:mutation` exited 0 before the review fix, with the Go core at 97.32 percent test efficacy and 100 percent mutator coverage, and the Python core at 90.26 percent, 8,387 killed of 9,292 mutants. That run did not include the normalizer, which was then outside the gated core. The review-fix mutation result is recorded below.
- The first review-fix `mise run check:mutation` passed the Go core, then failed at Python test collection because Mutmut copies only the core package and the new test imported the shell module at module scope. The shell test now imports its adapter inside an integration-marked test. The full mutation gate was rerun after this correction.
- That full rerun passed the Go core at 97.32 percent test efficacy and 100 percent mutator coverage but failed the Python core score at 87.67 percent, with 8,902 killed of 10,154 mutants. Surviving mutants clustered in the newly moved transcript core's metadata and event fields. Three exact-value tests for those fields and three more for calls, outputs, fallbacks, and aborts raised the targeted transcript-core survivor count from 342 to 95. `mise run check:pytest -- tests/test_transcript_retro.py --run-integration` then exited 0 with 36 passing tests. `mise run check:mutation:python` exited 0 at 90.10 percent, with 9,149 killed of 10,154 mutants. The final aggregate `mise run check:mutation` exited 0: Go core 97.32 percent efficacy and full mutator coverage. Python core 90.08 percent, with 9,147 killed of 10,154 mutants and three timeouts in the slower rerun.
- `mise run build`: exit 0.
- `mise exec -- gitleaks dir --redact --no-banner experiments/18-transcript-retro tests/fixtures/transcript_retro tests/test_transcript_retro.py reports/inputs/transcript-inventory-evidence.md`: exit 0 with no leaks found.
- A review-fix private-output scan decompressed both gzip tables and applied `privacy_findings` to all four committed evidence files. Exit 0: 17,372 event rows, 19,381 inventory rows, and zero privacy findings. This supplements the staged secret scan because generic secret scanners may not inspect gzip members.

The review-fix direct execution used this code from the experiment directory after the operator-supplied environment variables were set. Their values are withheld from the committed report:

```sh
mise exec -- uv run --group analysis python - <<'PY'
from pathlib import Path
from agent_orchestration_poc.core.analysis.notebooks import split_qmd
source = Path('inventory.qmd').read_text()
_, code = split_qmd(source)
exec(compile(code, 'inventory.qmd', 'exec'))
PY
```

The executable local verifier in `README.md` recomputes the HMAC groups from the same authorized snapshot without displaying a path, key, or raw record. The initial source inventory includes deferred formats with explicit states, so the event counts are only for included Codex native sessions. The five ambiguous native matches retain the first sorted source representation and are disclosed rather than promoted into additional events.
