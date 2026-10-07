# Gate change evidence for issue 88

Recorded 2026-10-07 UTC in `tooling/88-gate-weakenings` with Codex CLI 0.157.1 and `gpt-6-sol` at high. The comparison base is `d32e4f4052323d10d25a354a5e0e9a13fc4c4d44`. The pinned tools include Python 3.14.6, uv 0.12.10, Ruff 0.16.9, mutmut 3.8, and jscpd 5.3.2.

## Source basis

Documented: The local gate implementation and check contracts were read at base commit `d32e4f4052323d10d25a354a5e0e9a13fc4c4d44`, including `mise.toml`, `.github/workflows/check.yml`, the supported lint configurations, `research/gates/testing/versions.md`, and `research/gates/quality-gates/versions.md`. CPython source was read at `c63aec69bd59c55314c06c23f4c22c03de76fe45` for tokenized Python comment handling. GitHub's [pull request event documentation](https://docs.github.com/en/actions/reference/events-that-trigger-workflows#pull_request) describes `edited`, and its [context documentation](https://docs.github.com/en/actions/reference/contexts-reference#runner-context) describes `runner.temp`.

## Local checks

Verified: `mise run check:pytest -- tests/test_gate_changes.py --run-integration` exited 0 with 76 passed cases after the latest test additions. The case table and passing and failing PR bodies are in `tests/fixtures/gate_changes/`.

Verified: `mise run check:gate-changes -- --base d32e4f4052323d10d25a354a5e0e9a13fc4c4d44 --head 91e5c52 --body-file tests/fixtures/gate_changes/pr-body-pass.txt` exited 0 and reported the workflow and `mise.toml` selector IDs. The same command with `pr-body-fail.txt` exited 1, reporting a missing reason for `mise.toml` and a partial reason for the workflow.

Observed: An earlier `mise run check:coverage` could not write `~/Library/Application Support/quarto/logs/jupyter-kernel.log` under the sandbox. A full `mise run check` retry exited 0 without a change to the sandbox. It reported Python core lines 97.25%, branches 93.86%, shell lines 74.20%, Go core statements 96.43%, branches 94.74%, and shell statements 74.58%. The final post-change runs are recorded below.

Observed: An intermediate `mise run check:mutation` exited 1 with Go 145/149 killed (97.32%) and Python 9123/10175 killed (89.66%). The Python score was 35 kills below its 90% floor. Focused tests were added for the surviving gate comparison branches before the final run.

## Open PR audit

Observed: A single REST list of open PRs and fetched head refs was compared against the base on 2026-10-07 UTC. The sanitized IDs and diagnostic labels are in `tests/fixtures/gate_changes/open-pr-audit.txt`. Nine open PR heads were inspected. Three had missing gate reasons and six had no findings or justification diagnostics. No PR body or credential was retained in the fixture.

## Final verification

To be completed after the final commit and PR body edit probe.
