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

## Approved final revision copied for the second slice

[Verified] The five operator-approved source files under `/Users/tony/Code/github.com/tbhb/agent-orchestration-poc/.holding/reorg/` were read at source checkout `6448b1175dbc2c8f22f68fa126b5b344db9b74b0`. The files are untracked holding inputs, so their SHA-256 digests below define the revision. The supplied `verify.txt` reports `RESULT: PASS` for the final review edits. Its `verify.py` checks earlier round-four source hashes and generated final content, so its `SOURCE_HASHES` are not hashes of these final files.

| Final source suffix | Source SHA-256 | Committed copy SHA-256 |
| --- | --- | --- |
| `.md` | `481ec7a76c802bfaba639e17cb157b42dfbd0dd16e6ed6095b223b92a2b0d6ed` | `481ec7a76c802bfaba639e17cb157b42dfbd0dd16e6ed6095b223b92a2b0d6ed` |
| `.tsv` | `a06c4a16a9301d309c23f4c804222497dee20f7113e60f1be32109d0810b8f31` | `9ae24b7f1f5d871adf6ee57b7dd0b6e8d702a168fea9790dddc6510b549e38d6` |
| `-parents.tsv` | `36393c7ee940f3aa4281ff3ad43d6105ebcb58ee09fe7c54f8c42784b4b61453` | `36393c7ee940f3aa4281ff3ad43d6105ebcb58ee09fe7c54f8c42784b4b61453` |
| `-edges.tsv` | `475e4378833d0af755ab147bb169fee7f09cfb9440d96a54c7e367d0f3d35d98` | `964c3fc89a679da2eff88ba051743c6a16d09f189442a909e0f28563fc7896ec` |
| `-changes.md` | `7d630e091bb7b9804d56b16f2ccd1d3ff50a2ed5248f6a0a53c44e6e9a8bf9fe` | Sanitized copy has digest `2cd3cbba70f9cc6699c5e040ee90b313f5e1559697893f0502a2b155f5750f0e` |

[Verified] The repository copy of `-changes.md` redacts eight embedded issue-body values and includes three whitespace fixes required by rumdl. The exact source remains in the operator's holding directory at the source digest above and is not committed. The assignment and edge copies quote 121 and 34 terminal empty cells, respectively, to satisfy the commit whitespace hook. A `csv.DictReader` comparison found every parsed row equal to its source row. The work model Markdown and parent TSV match their holding inputs byte for byte. `mise exec -- gitleaks dir --redact --no-banner --log-level error reports/inputs/work-model-tables` exited 0.

[Observed] A bounded read-only REST list at 2026-09-27 19:52 UTC returned 161 issues across pages of 74, 71, and 16. The new Project item list returned 169 items across pages of 100 and 69. These counts match the final model's conditional CP1 scenario, but the reads did not collect every field, body, parent, blocker, label, and page receipt. They are not CP1. The approved tables parse to 191 assignment rows, 22 parent rows, and 387 edge audit rows, with 161 numbered assignments and 30 unnumbered assignments.

| Approved title or number | Project item ID | Content ID |
| --- | --- | --- |
| #214 `exp(workers): detect idle and finished turns of interactive workers` | 256084757 | 5604913608 |
| #215 `chore(github): update account and owner names after the move` | 256084793 | 5604914475 |
| `tooling(docs): move diagrams from Mermaid to D2` | 256030903 | 47024878 |
| `tooling(workers): report worker completion without process exit` | 256082915 | 47027486 |
| `process(workers): run every worker as an interactive tmux session` | 256082939 | 47027489 |
| `research(testing): verify the Go branch coverage stall` | 256082970 | 47027493 |
| `docs(github): fix the monitor startup vault reference` | 256085205 | 47027545 |
| `tooling(workflow): reject closing keywords outside the Closes line` | 256085226 | 47027546 |
| `tooling(workflow): add a handoff hook after compaction` | 256085253 | 47027547 |
| `feat(github): gate events on the agent_orchestrated property` | 256085273 | 47027548 |

[Observed] Issue #155 already has the proposed part B title in a read-only REST response. The Project item count is consistent with the final table scenario, but a complete number-to-item reconciliation remains for CP1. The five final files and `-changes.md` record the reviewed deltas from the earlier snapshot. The separate runner must save each current value and its reviewed disposition before a write. No new title-to-created-ID mapping exists because parent, draft, and incident creation has not run.
