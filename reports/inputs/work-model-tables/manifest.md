# Work model table provenance

[Observed] The only version 3 files available to this worker on 2026-09-27 at 14:11 EDT were round-three review candidates under `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/reorg/`. The round-three review says part A needs another author round, so this directory contains no copy labeled approved. The source checkout was at `cfb74707dd57c70288b250c739c480bad4258770` when read. The digest identifies each uncommitted candidate file exactly.

| Candidate source path | SHA-256 |
| --- | --- |
| `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/reorg/2026-09-27-work-model-v3-r3.tsv` | `4959fb80dfb52ebd203831da16742e15130b7e701bd3208d39add73b00b7b54b` |
| `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/reorg/2026-09-27-work-model-v3-r3-parents.tsv` | `e5cafb9fee3146dde4e3f6dcc2ac88a031bd94fdd7eac33d0432744067eb4278` |
| `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/reorg/2026-09-27-work-model-v3-r3-edges.tsv` | `b17a64a6b3946bdd876329e232c68cd336597b24593e587e87fa6da46ffc9782` |

[Verified] `parse_tables` read the three round-three candidate files by supplied paths under Python 3.14.6 and returned 186 assignments, 22 parents, and 387 edge audit rows. `cycle_nodes` returned an empty cycle. These are properties of the candidate digest above, not constants in the implementation or an approval verdict.

## Live baseline and mapping

[Observed] One read-only `gh api 'repos/tbhb-dev/agent-orchestration-poc/issues?state=all&per_page=100' --paginate` returned 161 non-pull-request issues across three pages. One read-only `gh api 'orgs/tbhb-dev/projectsV2/1/items?per_page=100'` returned the following ten items. The read did not collect the complete CP1 field, parent, blocker, body, order, and nested pagination values. These identities require another complete read before any backfill mutation.

| Title | Project item ID | Content kind | Content ID |
| --- | --- | --- | --- |
| `tooling(docs): move diagrams from Mermaid to D2` | 256030903 | DraftIssue | 47024878 |
| `tooling(workers): report worker completion without process exit` | 256082915 | DraftIssue | 47027486 |
| `process(workers): run every worker as an interactive tmux session` | 256082939 | DraftIssue | 47027489 |
| `research(testing): verify the Go branch coverage stall` | 256082970 | DraftIssue | 47027493 |
| `exp(workers): detect idle and finished turns of interactive workers` | 256084757 | Issue | 5604913608 |
| `chore(github): update account and owner names after the move` | 256084793 | Issue | 5604914475 |
| `docs(github): fix the monitor startup vault reference` | 256085205 | DraftIssue | 47027545 |
| `tooling(workflow): reject closing keywords outside the Closes line` | 256085226 | DraftIssue | 47027546 |
| `tooling(workflow): add a handoff hook after compaction` | 256085253 | DraftIssue | 47027547 |
| `feat(github): gate events on the agent_orchestrated property` | 256085273 | DraftIssue | 47027548 |

[Observed] The round-three review identifies four of those drafts as missing from the candidate assignments and calls for another author round. It also finds the draft field model changed after a 400 response to a Project item field write trial, a newly decided `agentgw` program and other operator decisions, and a stale target Status for #199. The next snapshot must compare all current Project items, including held drafts, against the newly approved rows and record reviewed differences before producing a plan.

[Observed] Round-four candidate files appeared under the same source directory during implementation. A path-supplied read of `2026-09-27-work-model-v3-r4.tsv`, `2026-09-27-work-model-v3-r4-parents.tsv`, and `2026-09-27-work-model-v3-r4-edges.tsv` returned 191 assignments, 22 parents, 387 edge audit rows, and no accepted cycle. This candidate was not substituted for an approved input or copied into the repository.

[Untested] No live CP1 or CP13 was collected, no title-to-created-ID mapping exists, and no mutation was attempted. The separate REST runner will capture those values after approved input files exist.
