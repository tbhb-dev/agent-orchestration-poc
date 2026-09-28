# Proposed provenance verifier cases

These are synthetic specification cases for issue #133, labeled untested. Expected results apply after activation under decision 0131. They do not describe the current hook, which rejects attribution. Each named value below is a complete literal line. Lists in the case table denote those exact lines in that order, not literal abbreviations to put in artifacts.

## Exact values

A:

```text
Assisted-by: codex-cli/0.157.1 model=gpt-6-astra effort=medium agent=docs-131
```

B:

```text
Assisted-by: codex-cli/0.157.1 model=gpt-6-sol effort=high agent=impl-131
```

C:

```text
Assisted-by: claude-code/2.1.283 model=claude-fable-5-1 effort=high agent=coord-131
```

D, a different run with A's configuration:

```text
Assisted-by: codex-cli/0.157.1 model=gpt-6-astra effort=medium agent=docs-132
```

R:

```text
Assisted-by: claude-code/2.1.283 model=claude-sonnet-5 effort=medium agent=review-131
```

## Complete artifact examples

Passing single-contributor commit:

```text
decision(workflow): define provenance examples

Record the convention for later verification.

Assisted-by: codex-cli/0.157.1 model=gpt-6-astra effort=medium agent=docs-131
Refs: #131
```

Passing several-contributor commit, with canonical byte order:

```text
decision(workflow): define provenance examples

Record the coordinator's decision and the worker's document.

Assisted-by: claude-code/2.1.283 model=claude-fable-5-1 effort=high agent=coord-131
Assisted-by: codex-cli/0.157.1 model=gpt-6-astra effort=medium agent=docs-131
Refs: #131
```

Passing review verdict after cutover, preserving the existing first-line identity:

```text
Reviewer: Claude Code 2.1.283, claude-sonnet-5, medium effort.

The revised cases meet the convention.

Assisted-by: claude-code/2.1.283 model=claude-sonnet-5 effort=medium agent=review-131
```

Passing inline comment, independently attributed:

```text
Keep the inherited target commits outside the PR union.

Assisted-by: claude-code/2.1.283 model=claude-sonnet-5 effort=medium agent=review-131
```

Passing author role comment:

```text
Author reply, round 2.

I added the published-branch update case.

Assisted-by: codex-cli/0.157.1 model=gpt-6-astra effort=medium agent=docs-131
```

An issue body uses its required form sections followed by the same author block. Issue-review fixtures must retain #90's exact verdict line and a correct body digest before the reviewer block. These examples specify attribution only and cannot replace full form, digest, account, or authorization tests.

## Acceptance cases

| Case | Input | Expected result |
| --- | --- | --- |
| One agent | Commit contributors A, trailer block A | Pass |
| Several agents | Commit contributors A and B, block A then B | Pass |
| Same configuration, two runs | Contributors A and D, block A then D | Pass, two distinct IDs |
| Missing contributor | Contributors A and B, block A | Fail, B missing |
| No agent contribution | Human-only commit, no attribution | Pass attribution check |
| Duplicate | Block A then A | Fail, repeated identical line |
| Wrong order | Block A then C | Fail, C sorts before A |
| Unknown harness | Replace `codex-cli` in A with `mystery` | Fail, unknown harness |
| Unknown model | Replace `gpt-6-astra` in A with `gpt-unknown` | Fail, unknown model |
| Unknown version | Replace `0.157.1` in A with `999.0.0` | Fail until version evidence admits it |
| Missing version | Replace `codex-cli/0.157.1` in A with `codex-cli` | Fail |
| Missing effort | Remove the `effort=medium` field and its preceding space from A | Fail |
| Unknown effort | Replace `medium` in A with `default` | Fail |
| False unavailable | Replace `medium` in A with `unavailable` | Fail, control exists |
| Future unavailable control | New catalog entry with documented absence and literal `effort=unavailable` | Pass only after catalog admission |
| Configuration change | Reuse A's agent ID after changing its model | Fail, allocate a new ID and retain both contributors |
| Missing run ID | Remove the `agent=docs-131` field and its preceding space from A | Fail |
| Noncanonical bytes | Indent A or add a trailing space or fold it | Fail |
| Wrong field order | Move `agent=docs-131` before `effort=medium` | Fail |
| Tool suffix | Append a space and `git` or `sparse` to A | Fail |
| Exact union | Commits contain A and B, PR block A then B | Pass |
| Repeated across commits | Commit X and commit Y each contain A, PR contains A once | Pass |
| Missing union member | Commits A and B, PR block A | Fail |
| Extra union member | Commits A and B, PR block C then A then B | Fail |
| Coordinator prose | Commits A and B plus new empty provenance commit C, PR block C then A then B | Pass |
| Unrecorded coordinator prose | Coordinator materially changes body, no C commit, PR adds C | Fail exact union |
| Review verdict | Agent R writes verdict and supplies R block | Pass attribution check |
| Missing review attribution | Agent R writes verdict without R block | Fail |
| Inline independence | Review has R, inline comment has no trailer | Fail inline comment |
| Inline reply | Implementer A replies with A block | Pass |
| Wrong review attribution | R writes review, block A | Fail against contribution record |
| Issue author | A authors issue body with A block | Pass |
| Role comment | Coordinator C writes dispatch comment with C block | Pass |
| Missing role attribution | C writes role comment without C | Fail |
| Exact arbitration today | Append C to existing exact arbitration command | Fail existing protocol, cutover parser migration required |
| Squash propagation | PR title and body retained with A then B, squash contains same union | Pass |
| Squash replacement | PR has A then B, squash replaces them with C | Fail |
| Squash omission | PR has A then B, squash drops B | Fail |
| Reference independence | PR retains `Refs: #131` and `Refs: #124` beside A | Attribution set is only A, neither reference closes an issue by itself |
| Linking options | Completed-issue and closing-line examples below | Conditional on #124 selection; not an activation claim |

## Published branch update

Let target T contain inherited commits with contributor R. The feature branch contains commit X with A and commit Y with B. A new merge-main commit M is authored by coordinator C while integrating T. At head M with target T, the selected commit set is X, Y, M. The expected PR block is C, A, B. R is excluded because its commit is already reachable from T. Including R fails exact union. Omitting C fails when M records C's integration contribution. A purely mechanical M with no agent contribution contributes an empty set instead. No original commit is amended or force pushed.

After any target or head update, recompute reachability and the union. A failed or incomplete collection is indeterminate, never an empty successful union.

## Open-PR cutover alternatives

Use synthetic cutover `2026-10-01T00:00:00Z` and an open PR created one second earlier with no agent trailers despite known agent contributions. If the operator chooses enforcement on existing PRs, expect a blocking migration finding. If the operator chooses prospective enforcement, expect a nonblocking legacy report. A PR created exactly at cutover, including one from an older branch, is enforced under either answer. Missing PR creation time or missing operator choice is indeterminate. No fixture implies permission to rewrite published history.

## Catalog regression cases

Passing Sol-medium contribution, absent from the original five examples:

```text
Assisted-by: codex-cli/0.157.1 model=gpt-6-sol effort=medium agent=routine-docs-131
```

| Tuple change | Expected result |
| --- | --- |
| Use `claude-code/2.1.283 model=claude-opus-5-5 effort=high` with a fresh agent ID | Pass catalog lookup, including the plan's coordinator review assignment |
| Use `codex-cli/0.157.1 model=gpt-6-luna effort=ultra` | Fail, effort is absent from that model's row despite valid grammar |
| Use `claude-code/2.1.283 model=gpt-6-sol effort=medium` | Fail, model belongs to another harness |
| Use `agy/1.2.11 model=gemini-3.8-flash-high effort=medium` | Pass provenance lookup; interaction between flag and tier remains untested |
| Use `codex-cli/0.157.2 model=gpt-6-sol effort=medium` | Fail until a catalog is extended with evidence |

## Issue linking alongside provenance

Issue #124 has not selected a policy in the inspected issue body or comments. These fixtures specify both candidates without claiming either is active. They retain the current `Refs:` requirement and use synthetic completed issue #131 and related issue #124. These examples leave live issues unchanged.

Option A, completed-issue-only body ending, passes if #124 selects closing keywords beside `Refs:`:

```text
Closes #131

Assisted-by: codex-cli/0.157.1 model=gpt-6-sol effort=medium agent=routine-docs-131
Refs: #131
```

Option A, multiple-reference body ending, passes for completed #131 and related #124 that remains open:

```text
Closes #131

Assisted-by: codex-cli/0.157.1 model=gpt-6-sol effort=medium agent=routine-docs-131
Refs: #131
Refs: #124
```

Option B, the same completed and related issues, passes only if #124 selects explicit closure automation and the merge evidence separately identifies #131 as completed:

```text
Assisted-by: codex-cli/0.157.1 model=gpt-6-sol effort=medium agent=routine-docs-131
Refs: #131
Refs: #124
```

| Case | Expected result |
| --- | --- |
| Option A removes `Refs: #131` from completed-issue-only example | Fail current reference requirement; closing text is not a replacement |
| Option A omits `Closes #131` | Fail the candidate linking contract, even though provenance passes |
| Option A adds `Closes #124` when #124 must remain open | Fail completion scope; valid trailers cannot authorize closure |
| Option B infers completed issues from every `Refs:` line | Fail; reference membership is not a completion record |
| Either option preserves body in squash | Pass propagation; the exact attribution union and separate issue lines survive |
| Squash retains closing line but drops the agent trailer | Fail provenance propagation |
| Either option counts `Refs:` or `Closes` as a contributor | Fail attribution set computation |

These specification verdicts require future tests of GitHub linking, closure, and Project transitions. Issue #124 owns those evidence claims and the final selection. #84/#92 own any reference-validator migration and #120 or its scoped successor supplies the closure code.

## Agent-account and Project cases

All rows below assume the recorded #134 cutover has occurred unless stated otherwise.

| Case | Expected result |
| --- | --- |
| Coordinator C posts an issue note as `tbhbagent`, ending with C | Pass provenance and role checks. It is not human operator approval |
| Implementer A replies as `tbhbagent`, ending with A | Pass |
| Reviewer R posts a verdict as `tbhbbot`, ending with R | Pass |
| Agent posts a role comment as `tbhb`, even with a valid trailer | Fail account policy and report the write |
| Before cutover, a `tbhb` comment claims operator authority by authorship alone | Fail authority inference; old agent comments used that account |
| Draft Project item authored by C as `tbhbagent`, body ends with C | Pass |
| Project status edit by C as `tbhbagent`, separate record binds Project/item/field IDs, before/after values, timestamp, API actor, mutation result, readback, and C | Pass |
| Project status edit lacks its provenance record or readback | Fail verification; do not silently treat it as human-only |
| Project status value has C appended to it | Fail typed-field contract |
| Configuration agent posts a coordinator note or Project edit as `tbhb` | Fail endpoint/role restriction; configuration access does not authorize communication |
