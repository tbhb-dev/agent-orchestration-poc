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

## Integration status

At the baseline, the workflow reference page is absent. PR #137 is open and generates the entire page from `config/workflow-reference.toml`. Editing its future provenance section needs agreement with #84's owner about preservation by the generator. Issue #124 is ready for research. Finalizing the closing-line examples requires its selected contract. Shared index and reference edits are pending the coordinator's reservation response.

## Validation

| Command | Exit | Result |
| --- | --- | --- |
| `mise run vale:sync` | 0 | Pinned styles synchronized |
| `mise run fmt` | 0 | Formatters passed, changes reviewed |
| `mise run check` (first run) | 123 | Vale rejected draft prose, corrected afterward |
| `mise run check` (second run) | Pending | Aggregate still running at this evidence commit |
| `mise run check:mutation` | 2 | gremlins v0.6.0 panicked in `mutantExecutor.Start` while obtaining a working directory |
| `mise run docs:build` | 0 | 46 pages built |
| `mise run docs:check-links` | 1 | Chromium Mach port registration denied by the sandbox on existing Mermaid pages |
| `mise exec -- vale docs/src/content/docs/decisions/0131-assisted-by-provenance.md` | 0 | Decision prose clean |
| `mise exec -- vale --ext=.md --path=docs/assisted-evidence.md < research/gates/assisted-by/evidence.md` | 0 | Research prose checked despite the repository-wide research exemption |
| `mise exec -- vale --ext=.md --path=docs/assisted-examples.md < research/gates/assisted-by/examples.md` | 0 | Example prose clean |
| `mise exec -- gitleaks dir research/gates/assisted-by --redact --no-banner` | 0 | No leaks found |
| `mise exec -- gitleaks dir docs/src/content/docs/decisions --redact --no-banner` | 0 | No leaks found |
| `git diff --check` | 0 | No whitespace errors |

[Observed] Chromium reported `bootstrap_check_in` with `Permission denied (1100)` while rendering existing workflow and monitor diagrams. The link checker then reported links into those unavailable pages. The new decision's links were not reported. A process inventory for diagnosing the stalled checks was also denied by the sandbox (`ps`, exit 1). No sandbox bypass was attempted.

[Inference] The first mutation attempt overlapped aggregate checks that instrument Go source. A separate rerun after the aggregate finishes will distinguish a transient workspace-copy failure from a persistent problem. The tool discards the underlying working-directory error in its panic, so this result alone does not establish a sandbox denial.

The first decision commit passed the normal hooks, including staged secret scanning and the existing attribution prohibition. The proposed trailers appear only in documentation examples.
