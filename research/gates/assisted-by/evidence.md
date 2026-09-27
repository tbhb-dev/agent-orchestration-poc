# Assisted-by convention evidence

## Scope and sources

Research date: 2026-09-27 UTC, following the operator's 2026-09-26 direction. The harness is Codex CLI 0.157.1. Model: `gpt-6-astra`, medium effort. Repository baseline: `cc1f59c7f7a932f7f9dba7073e1e63789d1328e5`. The proposed contract awaits verifier development and cutover.

[Documented] [Issue #131](https://github.com/tbhb/agent-orchestration-poc/issues/131) quotes the operator asking for “a common, consistent way like this to trace provenance.” Its body directs one Linux kernel style trailer per contributing agent, the union in PR bodies, and trailers on reviews. The [ready review](https://github.com/tbhb/agent-orchestration-poc/issues/131#issuecomment-5852268421) also requires a published-branch update example and serial integration with #84 and #124.

[Documented] Linux source commit `fd179f8a05be3ccae366b9b96e176b51fbe54aab`, dated 2026-09-26T11:14:35-07:00, was read on 2026-09-27. The exact attribution format in [Documentation/process/coding-assistants.rst](https://github.com/torvalds/linux/blob/fd179f8a05be3ccae366b9b96e176b51fbe54aab/Documentation/process/coding-assistants.rst#L49) is:

```text
Assisted-by: LLM [TOOL1] [TOOL2]
```

The same section says: “Basic development tools (git, gcc, make, editors) should not be listed.” The bracketed slots permit optional specialized analysis tools, while the source leaves harness names and versions unspecified. It also omits model, effort, and per-agent identifiers. Those fields below are project choices, not a transcription of the kernel format. The kernel also reserves DCO certification for humans.

[Documented] Git v2.51.0, commit `c44beea485f0f2feaf460e2ac87fdd5608d63cf0`, was read on 2026-09-27. [Documentation/git-interpret-trailers.adoc](https://github.com/git/git/blob/c44beea485f0f2feaf460e2ac87fdd5608d63cf0/Documentation/git-interpret-trailers.adoc) describes trailer parsing and states: “the trimmed <key> and <value> will be separated by `': '` (one colon followed by one space).” Git permits whitespace, folded values, and configurable duplicate handling. This project chooses stricter bytes and rejects duplicates within an artifact. Git parsing alone would not establish compliance.

[Documented] The [project plan at the baseline](https://github.com/tbhb/agent-orchestration-poc/blob/cc1f59c7f7a932f7f9dba7073e1e63789d1328e5/docs/src/content/docs/project/plan.md#commits), [PR #81](https://github.com/tbhb/agent-orchestration-poc/pull/81), and `scripts/check-pr-body.sh` prohibit attribution in commits and PR bodies. [PR #113](https://github.com/tbhb/agent-orchestration-poc/pull/113) records review identity separately. Those rules remain active until #134.

[Observed in prior repository evidence] `experiments/00-system-assessment/model-inventory.md` at the baseline records Codex CLI 0.157.1, Claude Code 2.1.283, and agy 1.2.11. It records resolved Claude model IDs, Codex model-list values, and agy requested model arguments. Claude effort values are help-text evidence. The agy flag versus model-tier interaction is untested, and its output does not identify the resolved model. This decision uses the retained inventory without making model calls or reading credentials.

## Collection commands

All successful reads below exited 0. The reads preserved accounts and live issue bodies. The explicit worker brief requested REST through `gh api`.

| Command | Purpose |
| --- | --- |
| `gh api repos/tbhb/agent-orchestration-poc/issues/131 --jq .body` | Binding specification |
| `gh api repos/tbhb/agent-orchestration-poc/issues/131/comments` | Refinement review |
| `gh api repos/tbhb/agent-orchestration-poc/issues/81 --jq .body` | Prior prohibition |
| `gh api repos/tbhb/agent-orchestration-poc/issues/83 --jq .body` | Account and review contract |
| `gh api repos/tbhb/agent-orchestration-poc/issues/84 --jq .body` | Reference ownership and size contract |
| `gh api repos/tbhb/agent-orchestration-poc/issues/90 --jq .body` | Issue review contract |
| `gh api repos/tbhb/agent-orchestration-poc/issues/120 --jq .body` | Coordinator merge contract |
| `gh api repos/tbhb/agent-orchestration-poc/issues/124 --jq .body` | Linking decision scope |
| `gh api repos/tbhb/agent-orchestration-poc/issues/124/comments --jq '.[].body'` | Linking review history |
| `gh api repos/tbhb/agent-orchestration-poc/issues/113 --jq .body` | Existing reviewer behavior |
| `gh api repos/tbhb/agent-orchestration-poc/pulls/137 --jq '{state,merged,head:.head.ref,body}'` | Reference integration status |
| `gh api repos/torvalds/linux/commits/master --jq .sha` | Pin kernel source |
| `gh api 'repos/torvalds/linux/contents/Documentation/process/coding-assistants.rst?ref=fd179f8a05be3ccae366b9b96e176b51fbe54aab' -H 'Accept: application/vnd.github.raw+json'` | Read exact kernel source |
| `git clone --depth 1 --filter=blob:none --sparse https://github.com/torvalds/linux.git /private/tmp/issue-131-linux` | Source checkout in permitted temporary storage |
| `git -C /private/tmp/issue-131-linux sparse-checkout set Documentation/process` | Read process source locally |
| `git -C /private/tmp/issue-131-linux rev-parse HEAD` | Confirm recorded kernel commit |
| `git clone --depth 1 --branch v2.51.0 --filter=blob:none --sparse https://github.com/git/git.git /private/tmp/issue-131-git` | Versioned Git documentation |

The first kernel REST command omitted quotes around the query string. zsh rejected its glob before making a request, exit 1. The quoted command above succeeded. A read of the guessed `decision/124-pr-issue-linkage` ref returned HTTP 404, exit 1. The linking decision remains unavailable. The source clones use `/private/tmp` because the declared sandbox writable roots exclude new clones under `~/Code/github.com`.

## Candidate formats

| Candidate | Decision | Reason |
| --- | --- | --- |
| `Assisted-by: LLM` | Reject for this project | Matches current kernel precedent but loses all requested provenance fields |
| `Assisted-by: Codex CLI 0.157.1 (gpt-6-astra, medium)` | Reject | Human-readable but cannot distinguish two agents using the same configuration |
| `Assisted-by: codex-cli/0.157.1 model=gpt-6-astra effort=medium agent=docs-131` | Select | Fixed field order, explicit version and effort, distinct agent identity |
| Co-author name and email for an agent | Reject | Confuses agent provenance with Git author identity and needs invented addresses |

## Proposed examples

[Untested] `examples.md` contains exact synthetic values and expected verdicts for the future verifier. The verifier has not run these specification fixtures. They include commit sets, reviews, comments, squash propagation, and both possible open-PR cutover answers. The examples use synthetic IDs without account secrets.

## Original integration status

At the baseline, the workflow reference page is absent. PR #137 is open and generates the entire page from `config/workflow-reference.toml`. Editing its future provenance section needs agreement with #84's owner about preservation by the generator. Issue #124 is ready for research. Finalizing the closing-line examples requires its selected contract. Shared index and reference edits are pending the coordinator's reservation response.

## Validation

| Command | Exit | Result |
| --- | --- | --- |
| `mise run vale:sync` | 0 | Pinned styles synchronized |
| `mise run fmt` | 0 | Formatters passed, changes reviewed |
| `mise run check` (first run) | 123 | Vale rejected draft prose, corrected afterward |
| `mise run check` (second run) | 0 | Aggregate passed after prose fixes |
| `mise run check:mutation` (first run) | 2 | gremlins v0.6.0 panicked in `mutantExecutor.Start` while obtaining a working directory |
| `mise run check:mutation` (second run) | 0 | Go killed 89 of 89 mutants. Python killed 454 of 467, scoring 97.22 percent |
| `mise run docs:build` | 0 | 46 pages built |
| `mise run docs:check-links` | 1 | Chromium Mach port registration denied by the sandbox on existing Mermaid pages |
| `mise exec -- vale docs/src/content/docs/decisions/0131-assisted-by-provenance.md` | 0 | Decision prose clean |
| `mise exec -- vale --ext=.md --path=docs/assisted-evidence.md < research/gates/assisted-by/evidence.md` | 0 | Research prose checked despite the repository-wide research exemption |
| `mise exec -- vale --ext=.md --path=docs/assisted-examples.md < research/gates/assisted-by/examples.md` | 0 | Example prose clean |
| `mise exec -- gitleaks dir research/gates/assisted-by --redact --no-banner` | 0 | No leaks found |
| `mise exec -- gitleaks dir docs/src/content/docs/decisions --redact --no-banner` | 0 | No leaks found |
| `git diff --check` | 0 | No whitespace errors |

[Observed] Chromium reported `bootstrap_check_in` with `Permission denied (1100)` while rendering existing workflow and monitor diagrams. The link checker then reported links into those unavailable pages. The new decision's links were not reported. A process inventory for diagnosing the stalled checks was also denied by the sandbox (`ps`, exit 1). No sandbox bypass was attempted.

[Inference] The first mutation attempt overlapped tasks that generated files. A second run started after those tasks finished and passed both mutation gates. The tool discards the underlying working-directory error, so the first result alone does not establish a sandbox denial or prove the cause.

The first decision commit passed the normal hooks, including staged secret scanning and the existing attribution prohibition. The proposed trailers appear only in documentation examples.

## Review revision on 2026-09-27

[Observed] Latest changes-requested review `5328728403` by `tbhbbot` at `c06fa9ac3cb7828fdb2f3cab57c27bcb88e3c722` has two inline blockers: `4113989750` (catalog admission) and `4113989752` (reference and linking examples). The body repeats those findings. The base is `main`, not a stacked PR. `git fetch origin && git merge origin/main` fetched successfully but exited 128 because local merge configuration requires fast-forward. `git merge --no-ff origin/main` with a Conventional Commit message and `Refs: #131` succeeded without conflicts, producing `01993eee9ad9e32a73e4cba270a298d5a12c2b33` over target `734985cf312c3fa1002e33595bec3c1633f9bf6e`.

[Verified] Before edits, a document-presence probe exited 1. Its four named checks all failed, as listed in the probe below. The same probe after edits exited 0 with all four passing. It checks document completeness only. Runtime verifier behavior remains untested and assigned to #133. The probe was run through `mise exec -- python`:

```python
from pathlib import Path

p = Path("docs/src/content/docs/decisions/0131-assisted-by-provenance.md").read_text()
e = Path("research/gates/assisted-by/examples.md").read_text()
checks = {
    "explicit admission catalog": "### Admitted combinations" in p,
    "Sol medium passing fixture": "model=gpt-6-sol effort=medium" in e,
    "workflow provenance reference": Path(
        "docs/src/content/docs/guides/workflow-reference.md"
    ).exists(),
    "completed issue linking fixtures": "Closes #131" in e,
}
for name, ok in checks.items():
    print(f"{name}: {'PASS' if ok else 'FAIL'}")
raise SystemExit(not all(checks.values()))
```

[Verified] Re-read the complete kernel file from the existing source checkout with `git -C /private/tmp/issue-131-linux show fd179f8a05be3ccae366b9b96e176b51fbe54aab:Documentation/process/coding-assistants.rst` (exit 0). Lines 31 through 41 reserve DCO certification for humans. Lines 43 through 58 define generic `LLM` attribution, optional specialized analyzers, and exclusion of basic development tools. They do not specify harness, version, model, effort, run ID, PR unions, Project records, or review trailers. All such rules here are project choices. Re-read Git's trailer passage with `git -C /private/tmp/issue-131-git show c44beea485f0f2feaf460e2ac87fdd5608d63cf0:Documentation/git-interpret-trailers.adoc` (exit 0). The reads left dependency sources and host configuration unchanged.

[Documented] Read `gh pr view 144 --comments`, `gh query repos/tbhb/agent-orchestration-poc/pulls/144/reviews`, and `gh query repos/tbhb/agent-orchestration-poc/pulls/144/comments` (all exit 0). Read `gh issue view N --json body,comments` for N = 131, 124, 132, 134, 135 (all exit 0), including all coordinator clarifications. The newest #132 note selects `tbhbagent` as default at cutover. Earlier notes in #132/#134/#135 require agent-account comments and Project edits, API authorship checks, and configuration-only use by the `tbhb` agent. The later token-retention note supersedes removal as a prerequisite and requires wrappers plus detection. This revision records those distinctions without activating them.

[Documented] Catalog rows now define exactly 124 admitted tuples from the retained inventory at `cc1f59c7f7a932f7f9dba7073e1e63789d1328e5`. Exact harness and version matching selects a row whose model/effort Cartesian product defines admission. Sol-medium and the plan's Claude Opus assignments are included. The retained inventory limits claims about per-pair runtime behavior.

The reserved workflow page now publishes the provenance section and links to the authoritative decision catalog. The decisions index also links to the record. `git show origin/tooling/84-conventions-reference:docs/src/content/docs/guides/workflow-reference.md` confirms #84's unmerged generator produces the future full page. Its integration must preserve or generate this section. Importing that unrelated forms/validator branch into this decision would exceed the assigned scope.

Issue #124 still has no selected decision in the inspected records. The examples spell out both candidates, with completed-issue-only and multiple-reference cases, a related issue left open, failure cases, and squash propagation. They cannot claim conformance to a selected #124 policy until that selection exists. The worker requested clarification and proceeded with conditional examples while preserving #124's decision ownership, as instructed not to wait for another PR to merge.

## Revision validation

Results below supersede the original validation table for this revision. Local rendered-link validation remains limited by Chromium's sandbox denial. This documentation change preserves the existing functional core and imperative shell boundaries.

| Command | Exit | Revision result |
| --- | --- | --- |
| `mise run vale:sync` | 0 | Pinned styles synchronized |
| `mise run fmt` | 0 | Formatting passed and diff inspected |
| Document-presence probe above | 1 before, 0 after | Reproduced and repaired missing artifacts |
| Catalog expansion through `mise exec -- python` | 0 | 124 unique tuples, Sol-medium and Opus-high admitted, Luna-ultra refused |
| `mise run check` (post-merge and post-edit runs) | 130 | Interrupted after prolonged silence in coverage. Completed lint and test stages passed, but local aggregate completion is unverified |
| `mise run check:mutation` | 0 | Go killed 145 of 149 mutants, none uncovered. Python killed 454 of 467 (97.22 percent) |
| `mise run build` | 0 | Both Go binaries built |
| `mise run docs:build` | 0 | 48 pages built |
| `mise run docs:check-links` | 1 | Existing Mermaid rendering blocked by Chromium Mach port permission denial |
| Rendered target probe through `mise exec -- python` | 0 | New `agent-provenance`, `admitted-combinations`, and `reference-values` anchors exist in built HTML |
| `mise exec -- rumdl check` on the five changed Markdown files | 0 | No issues |
| `mise exec -- vale` on the decision, reference, and index | 0 | No alerts |
| `mise exec -- vale --ext=.md --path=docs/assisted-evidence.md < research/gates/assisted-by/evidence.md` | 0 | Evidence prose clean |
| `mise exec -- vale --ext=.md --path=docs/assisted-examples.md < research/gates/assisted-by/examples.md` | 0 | Example prose clean |
| `mise exec -- gitleaks dir research/gates/assisted-by --redact --no-banner` | 0 | No leaks |
| `mise exec -- gitleaks dir docs/src/content/docs/decisions --redact --no-banner` | 0 | No leaks |
| `git diff --check` | 0 | No whitespace errors |

[Observed] `ps` process inspection was denied by the sandbox. The worker used task logs and session completion results instead. The Chromium denial was `bootstrap_check_in ... Permission denied (1100)`. The worker kept the sandbox restrictions in place.

[Verified in CI] At commit `dcece1f`, all five required jobs passed: `check`, `docs`, `pr-body`, `imported-research`, and `mutation`. Job `108546389448` ran `mise run check` successfully from 03:59:02 through 04:02:06 UTC on 2026-09-27. The worker confirmed the result through `gh query repos/tbhb/agent-orchestration-poc/actions/jobs/108546389448`. Local coverage stopped producing output in both aggregate runs, which were interrupted with exit 130. Their cause is undiagnosed. The separate mutation run completed successfully. Final-head CI is checked again after this evidence commit.
