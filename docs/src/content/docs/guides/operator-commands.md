---
title: Operator commands
description: Fixture-only timeline commands and the coordinator digest handoff.
---

## Intake on the owner item

The coordinator posts one active `Operator ask` comment on the issue or pull request that the answer governs, or uses a dedicated issue when neither exists. The ask specifies one of the six `operator/*` attention kinds and numbers each approval line or option. It states the recommendation, effects, and work it unblocks. It also gives a deadline or `none` and links redacted evidence. The coordinator applies `needs-operator` and exactly one kind label. A command cannot authorize a sensitive host or credential action without the separate authenticated approval gate in [issue #134](https://github.com/tbhb-dev/agent-orchestration-poc/issues/134).

Write a Markdown heading such as `### Operator ask: exact plan`. Put numbered approval lines below `Approval lines:` and numbered choices below `Options:`. Each number starts a line, with `1. Text` for approval lines and `Option 1: Text` for options. Keep one active ask per item. The workflow reads all issue comment pages and uses the latest ask comment. Multiple matching headings or repeated numbers make an ask ambiguous and block approval. A later edit after the answer was posted invalidates that answer for automation.

## Commands

The entire trimmed comment must be one case-sensitive line. The exact forms are `/approve all`, `/approve lines=1,3`, `/reject lines=2`, `/choose option=2`, `/answer text=<nonempty answer>`, `/question text=<nonempty clarification question>`, `/defer reason=<nonempty reason>`, and `/withdraw`. Line lists are unique, ascending, comma separated, and must name numbers in the current ask. Ranges and unknown options are invalid. `/approve all` selects every numbered approval line in that revision only. `/reject` requires explicit lines, and `/choose` selects one option.

Use an answer to supply a fact or a question to request clarification. Deferral pauses until the coordinator records a resumption condition. Withdrawal retracts the latest unexecuted answer. It cannot undo an action already performed. Plain replies remain for the coordinator to interpret manually. A reaction acknowledges processing and does not execute the decision.

## Workflow and labels

The `issue_comment` `created` workflow fetches the source comment, open item, and all ask comment pages through REST. It accepts only `tbhb` as both fetched author and event actor, with `OWNER` or `MEMBER` in the fetched `author_association`. The item must be open and have `needs-operator` plus exactly one kind label. Account login alone cannot establish who is at the keyboard. The coordinator checks authority before acting. The workflow ignores edits, other authors, unrelated text, closed items, and items outside the two fixture numbers. A malformed slash command from the accepted account receives `confused` without a label change.

A valid command adds only `operator/replied` with the additive label endpoint and receives `+1` on its source comment. Repeated delivery does not add another label or reaction. The coordinator records the verbatim answer and removes `operator/replied` afterward. It removes attention labels only after resolution or explicit deferral, retaining them while another ask is active. The workflow uses only `GITHUB_TOKEN` with `contents: read` and `issues: write`.

## Fixture gate and activation

This workflow remains restricted to one reviewed disposable issue number and one reviewed disposable pull request number. The event item's `pull_request` marker selects the matching number. The gate must be replaced with the two recorded IDs before a fixture run, and removing it for ordinary items needs a later reviewed pull request. Read back the actual `tbhb` association, issue and pull request labels, and reactions before proposing broad activation. The coordinator's digest fixture result is a separate prerequisite.

## Coordinator digest handoff

The coordinator's external digest script listens for `issue_comment created` and `issues labeled`. Webhook text only wakes targeted REST reads of `GET /repos/tbhb-dev/agent-orchestration-poc/issues/comments/{comment_id}` and `GET /repos/tbhb-dev/agent-orchestration-poc/issues/{number}/labels`. It never authorizes dispatch. On a verified command, emit `ask:#<number>:<outcome>:comment=<id>`, including a selection when needed, as in `ask:#200:approved:lines=1,3:comment=12345`. Invalid commands emit `ask:#200:invalid:comment=12345`. Pull requests use the same number form.

When the `operator/replied` label has not arrived, retain the pending comment ID by item. A later `issues labeled` webhook supplies the item number, and the pending record supplies the comment ID for the same targeted reads. Deduplicate emitted events and coordinator processing by comment ID. After readback, the coordinator records the source comment and time verbatim. It checks the effect against the current ask before any later action or dispatch. Its external script and fixture verification are maintained by the coordinator.
