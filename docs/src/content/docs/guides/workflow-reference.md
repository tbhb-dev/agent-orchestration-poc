---
title: Workflow reference
description: Proposed agent provenance contract for workflow artifacts.
---

## Agent provenance

[Decision 0131](/decisions/0131-assisted-by-provenance/) defines the proposed provenance contract for issue #131. It remains inactive until [#134](https://github.com/tbhb/agent-orchestration-poc/issues/134). Current hooks still prohibit attribution trailers. This page publishes the provenance section reserved by #131. The other reference sections remain owned by #84/PR #137. When that generator is merged, it must preserve this section or render it from its source. A generated-page overwrite would lose this integration.

Use this exact line format after cutover:

```text
Assisted-by: <harness>/<version> model=<model> effort=<effort> agent=<agent>
```

The [admitted combinations](/decisions/0131-assisted-by-provenance/#admitted-combinations) define the complete catalog by exact harness/version and the Cartesian product of each row's model and effort lists. The [reference values](/decisions/0131-assisted-by-provenance/#reference-values) show literal examples for Codex Sol and Astra, Claude Fable and Sonnet, and agy. Catalog lookup rejects unknown tuples, including every use of `unavailable`, while launch permission and runtime verification remain separate requirements.

Use one line per contributing agent ID, freeze that ID's configuration, sort complete lines by ASCII bytes, and reject duplicates within each artifact. The PR body contains the exact set union of its selected commits' lines. Preserve that union when deriving the squash body. Reviews, inline comments, implementer replies, issue bodies, and coordinator notes each carry their own contributors. Project draft bodies include trailers. Typed field edits use the separate provenance record defined in the decision.

After cutover, ordinary agent communication and Project edits use `tbhbagent`, and reviews use `tbhbbot`. The coordinator is subject to the same rule. Attribution is separate from operator authority, account verification, and signing. The decision records the #132/#134/#135 coordinator clarifications and keeps today's `tbhb` implementer workflow intact.

Keep `Refs:` as issue references. Closing keywords, if selected by #124, belong before the final trailer block and apply only to completed issues. The proposed cases in `research/gates/assisted-by/examples.md` cover both #124 options, completed-issue-only and multiple-reference bodies, an issue that remains open, and squash propagation. Policy selection remains with #124. Closure behavior remains inactive here.
