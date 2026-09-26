# Documentation brief sample

## Assignment

Document the coordinator preflight tasks for issues #70 through #73 on the workflow and tooling pages. Use the [phase 1 retrospective](/retros/2026-09-26-phase-1/) as the source for each task's trigger.

## Writing rules

Write one source line per paragraph and capitalize only the first word and proper names in headings. Separate citations with commas or separate sentences. Do not use semicolon citation lists.

## Verification

Run `mise run check:vale -- docs/src/content/docs/workflow/index.md docs/src/content/docs/workflow/tooling.md` and resolve alerts. Run `mise run check:rumdl` and `mise run check:guard-markdown` before reporting the page paths and check results.
