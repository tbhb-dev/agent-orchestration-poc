# Codex lifecycle experiment evidence

These artifacts support [CODEX_SESSION_MANAGEMENT.md](../../CODEX_SESSION_MANAGEMENT.md), especially its E1–E16 results. They record experiments performed on September 26, 2026 with local Codex 0.157.1 and an isolated migration from 0.156.1. All model-backed runs used the account's discovered default model, `gpt-6-astra`, with low reasoning effort in the test configuration.

## Files

- [results.jsonl](results.jsonl): 160 timestamped, sanitized evidence records. Each has `at`, `test`, and `data`; report references identify the `test` label. Repeated labels retain earlier attempts as well as corrected runs.
- [verification.json](verification.json): 16 checks against those records, covering every original experiment category. A true result means the measured scenario matched the stated finding, including findings such as a process surviving interruption; it does not mean all product behavior was desirable.
- [schema_diff.json](schema_diff.json): structural comparison of generated experimental schemas, excluding description/title changes.
- [cleanup.json](cleanup.json): temporary authentication-link removal and test-process checks.
- [probes/](probes/): investigation scripts preserved for audit and reproduction. These are scratch probes, not a production client or a portable automated test suite.

## Execution notes

`lab.py` provides the small WebSocket client, standalone-server control, JSONL recording, and initial marker turn. Its configuration and paths are deliberately specific to this workspace and scratch directory. It uses an existing authenticated Codex installation through a temporary auth-file link; credentials themselves are not included here. Running these probes performs actual model requests and creates or changes disposable session state.

The successful sequence was `lab.py`, `phase2.py`, corrected `phase3b.py`, corrected `phase4.py`, `phase5.py`, `phase6.py`, and `final_checks.py`. The `upgrade.py` and `daemon_compare.py` scripts use separate test homes. `inventory2.py` performs read-only aggregate reconciliation against the normal daemon; it does not record unrelated conversation text. The original `phase3.py` is retained to explain the active-revert/steering interference, not as a successful complete test.

Some scripts were corrected during execution. The preserved versions include the final corrections; the report documents prior failures. In particular, early connection-wide answer/event collections could include concurrently drained queue messages or child output. Use native thread/turn IDs and final turn objects to attribute results. The usage reconciliation uses thread-scoped persisted response records.

The first archive/ephemeral inventory calls used `sourceKinds:["appServer"]`, but these test threads were recorded as `vscode`; those empty lists are not evidence of absence. Later explicit broad-source and ancestor queries, path checks, and direct logical-row checks resolved the relevant questions.

The compaction test added one synthetic 600-line input item. It did not simulate 600 completed turns, exhaust the full context window, or establish preservation of every fact. The upgrade test used the two already-installed binaries and did not alter an installed version or the normal session store.

## Cleanup

All explicitly started test servers were stopped in cleanup handlers. The separate managed daemon reported `notRunning` after its final stop. The bounded shell commands that survived turn interruption were terminated explicitly. Four temporary authentication links were removed; a process check found no remaining executable paths under the isolated test roots. Synthetic session data remains in scratch storage for inspection; it contains no copied login file.

## Rechecking the artifacts

Validate Markdown with `guard-markdown CODEX_SESSION_MANAGEMENT.md session_experiments/codex/README.md`. Parse `results.jsonl` one JSON object per line. The scripts can be syntax-checked without running model calls by passing their source to Python's `compile()` built-in.

To reproduce protocol schemas, run the selected version's `codex app-server generate-json-schema --experimental --out <scratch-directory>`. Record both the shell CLI version and the runtime handshake version; they need not be the same in another installation.
