# Pull request

## What

Describe the change.

## Why

Explain why this work is needed.

## Evidence

Link the recorded checks and output. Feature and experiment changes need a link.

## Docs

List the updated pages or link the follow-up issue.

## Size justification

If the PR exceeds 800 measured units, explain why the work cannot split.

## Gate justifications

Run `mise run check:gate-changes -- --base <base-sha> --head <head-sha> --body-file <body-file>` and list each reported ID with a nonempty reason. Use one line per finding in the form `- gate:<kind>:<path>:<key-or-location>:<change>: <reason>`. State `None.` if the list is empty. Reviewers judge whether each reason warrants the change. Unknown syntax must be registered and reviewed before the check can pass.

## Checklist

- [ ] CI is green.
- [ ] Docs are updated or a follow-up issue is filed.
- [ ] No secrets are included.
- [ ] Evidence is committed.

Refs: #<n>
