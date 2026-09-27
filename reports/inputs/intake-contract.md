# Intake contract evidence

## Sources and status

- [Documented] The approved local work model, section 7, at `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/reorg/2026-09-27-work-model.md` with SHA-256 `3bb23a032bf9f922555bf6333d73834716120a1476d7c1c9d23bf7ebdceda87d`, defines sole-writer intake, Backlog drafts, and conversion at the move to Refinement. Its section 10 makes the contract merge precede the step 1 snapshot comparison. The repository baseline read was `7b67be6`.
- [Documented] GitHub REST API version `2026-03-10` describes [organization draft creation](https://docs.github.com/en/rest/projects/drafts?apiVersion=2026-03-10), [Project item reads and updates](https://docs.github.com/en/rest/projects/items?apiVersion=2026-03-10), [sub-issues](https://docs.github.com/en/rest/issues/sub-issues?apiVersion=2026-03-10), and [issue dependencies](https://docs.github.com/en/rest/issues/issue-dependencies?apiVersion=2026-03-10). The [GraphQL Project schema](https://docs.github.com/en/graphql/reference/projects#updateprojectv2draftissue) defines the draft title and body edit mutation. Documentation and schema do not prove this account can make those writes.
- [Help-text] `mise exec -- codex exec --help` on Codex CLI 0.157.1 accepts `-` to read instructions from stdin, `-m` for model, `-C` for worktree, and `-c` for configuration. [Official OpenAI documentation](https://developers.openai.com/learn/codex) supplies the product context. The local help is the command evidence.
- [Observed] `gh api user --jq .login` returned `tbhb-agent`. `GET orgs/tbhb-dev/projectsV2/1/items/256030903` and `GET users/tbhb/projectsV2/9/items/255815053` returned matching D2 drafts. The organization Project field list had Status, Priority P0/P1/P2, and Size, but no Type, Work type, Severity, Validation, or Validation detail. New draft creation and conversion remain [Untested] until the live acceptance.

## Launcher examples

The coordinator prepares a request file containing only the request, then supplies the brief before that file on stdin. This is the invocation contract, not an activation command:

```sh
{ cat docs/briefs/intake-brief.md; printf '\n\n## Intake request\n\n'; cat "$request_file"; } | mise exec -- codex exec -m gpt-6-sol -c model_reasoning_effort=high -C "$PWD" -
```

The coordinator may invoke the Claude agent with `@intake` and the same request after activation. The `.claude/agents/intake.md` definition tells it to read the shared brief and template. No wrapper is needed for this invocation. agy submits a request through the coordinator and does not run intake.

## Sanitized fixture

The first stub's title is `tooling(docs): move diagrams from Mermaid to D2`. Its class is chore, epic is none, plan reference or origin is the operator's 2026-09-27 decision, Type is chore, Priority is Intangible, Work type is Planned, Severity is none, and estimated Size is L. Validation is Invalid while required Project fields and the shared checker are absent. Its blockers and related issues are none, its source is operator, and its requester is Claude Code, Fable 5.1. The what and why preserve the prior draft's D2 rationale and the question about Excalidraw. The old item id is `255815053` on the former user Project and its matching organization item id is `256030903`. Neither is converted by this PR.

[Observed] `gh api graphql` used `updateProjectV2DraftIssue` with the draft node ids and the same title and body for both items. REST read-back of both titles succeeded. The local body file and both API bodies had SHA-256 `c886a3104929df9f90aeab978bb0f1b50d17821b427a9caa7ea6ab9ef2c7b56a`. The body has no credential or token. The rewrite did not set Project fields, so Validation remains a declared Invalid value in the body, not a Project field value.

Example reply after a complete search finds the existing draft: `duplicate | item URL: https://api.github.com/orgs/tbhb-dev/projectsV2/1/items/256030903 | Title: tooling(docs): move diagrams from Mermaid to D2 | Class: chore | Epic: none | Type: chore | Priority: Intangible | Work type: Planned | Severity: none | Size: L | Validation: Invalid | Blockers: none | search terms: Mermaid D2 diagrams, docs browser rendering`. This is a fixture, not an observed intake response.

The first issue comment after a later conversion uses `Stub Project item id`, `Stub URL`, `Decision-maker`, `Decision time UTC`, `Old Project item id`, and `New Project item id` exactly as the brief specifies. The coordinator's #198 activation comment records the UTC activation instant, `policy version: 1`, and `policy location: docs/briefs/intake-brief.md@<merged SHA>`. [Untested] Live creation, read-back, rank replacement, deletion, and conversion wait for #206 and #201.

## Later evidence and limits

After #200 commits the step 1 snapshot, compare every row with the approved version 2 assignment table and record each difference and its disposition here. Do not create a stub for the classification pass. The coordinator posts the sanitized activation and single live draft and conversion acceptance record on #198 after #206 integrates the shared checker. The live record is also consumed by #206 and includes Vale on the draft body. The 31 pre-existing Backlog issues are a separate inventory, not new draft violations.

No Project fields were edited for this contract. The absent organization fields and options make current live readiness impossible. Any field creation or option change belongs to the operator and #200. The draft rewrite used the GraphQL title and body mutation because the REST draft API does not expose an update endpoint.

## Validation and size

- [Verified] `mise run vale:sync`, `mise run fmt`, `mise run check`, and `mise run check:mutation` exited 0. The first full check found seven Vale alerts in the new brief. Those were corrected before the passing full check. The Go core mutation score was 97.32 percent and the Python core score was 91.07 percent.
- [Verified] The staged `git diff --check` and staged gitleaks hook exited 0. The Project title and body read-backs matched the local SHA-256 above.
- [Verified] The three contract Markdown files add 46 nonblank prose lines under the workflow reference's size unit. The evidence file is excluded by `reports/inputs/**`. No code line is added, so the measured PR size is 46 units against the 400-unit target and 800-unit limit.
