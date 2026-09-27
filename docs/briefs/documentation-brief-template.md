# Documentation brief template

Copy this brief into the coordinator's dispatch for Codex documentation work.

## Assignment

State the issue, target pages, source inputs, and expected reader action.

## Writing rules

Write each Markdown paragraph on one source line. Use sentence case headings. Keep citation lists free of semicolons. Give site pages `title` and `description` frontmatter, with no body H1.

## Verification

Run `mise run check:vale -- <changed-markdown-paths>` with the repository's pinned Vale 3.22.0 and `ai-tells` style. Fix every new alert before reporting completion. Run `mise run check:rumdl` and `mise run check:guard-markdown` for the full Markdown inventory.

## Report

List the changed pages, the commands and outcomes, and any source claim that remains untested.
