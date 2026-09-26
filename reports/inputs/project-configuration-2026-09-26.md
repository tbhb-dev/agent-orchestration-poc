# Project configuration evidence

Recorded 2026-09-26 by the worker for issue #12 (a coordinator subagent on `claude-fable-5-1`, high) against the user project <https://github.com/users/tbhb/projects/9> (node id `PVT_kwHOARFd7s4BkxtJ`) and the repository `tbhb/agent-orchestration-poc`, with gh 2.100.0. This file is the raw material for the Project section of the workflow page (#11). Every id below was read back from the API after the mutation that created it. No secrets were involved.

## Fields

The six custom fields were created with `gh project field-create 9 --owner tbhb --name <name> --data-type <type> [--single-select-options <list>] --format json`, one call per field. The output of each call is the row below.

| Field | Type | Field id | Options (name: option id) |
| --- | --- | --- | --- |
| Phase | single select | `PVTSSF_lAHOARFd7s4BkxtJzhjiK2U` | 0: `232c591e`, 1: `2d972c47`, 2: `76935507`, 3: `343c13e7`, 4: `05bbbd5e`, 5: `c1531479`, 6: `1e9fcdb4` |
| Area | single select | `PVTSSF_lAHOARFd7s4BkxtJzhjiK2Y` | bus: `0ea118c9`, daemon: `273fb316`, containers: `b34c51df`, terminal: `f271fce2`, ui: `ba05528d`, desktop: `f0f907f1`, remote: `7fab7f7f`, docs: `54ba47b0`, tooling: `fd4dec09`, experiment: `1a9d263d`, research: `4b4e434e`, workflow: `e0bcfae9`, security: `c7be6f9f` |
| Harness | single select | `PVTSSF_lAHOARFd7s4BkxtJzhjiK2w` | claude: `d29a9c68`, codex: `98cfa3b1`, agy: `9d589f32`, any: `547f4229` |
| Priority | single select | `PVTSSF_lAHOARFd7s4BkxtJzhjiK20` | P0: `832786fe`, P1: `34051a2f`, P2: `b257ab13` |
| Size | single select | `PVTSSF_lAHOARFd7s4BkxtJzhjiK3w` | S: `87655ba0`, M: `cb414a3b`, L: `0492571b` |
| Worker | text | `PVTF_lAHOARFd7s4BkxtJzhjiK30` | none |

## Status options

The built-in Status field (`PVTSSF_lAHOARFd7s4BkxtJzhjhD-Q`) accepted `updateProjectV2Field`, which the research had left unverified. The three existing option ids were kept so the built-in workflows and the sixteen existing items kept their targets: Todo became Backlog, In Progress became In progress, and Done stayed Done. The call and its result:

```text
$ gh api graphql -f query='mutation { updateProjectV2Field(input:{ fieldId:"PVTSSF_lAHOARFd7s4BkxtJzhjhD-Q", singleSelectOptions:[ {id:"f75ad846", name:"Backlog", color:GRAY, description:"Filed, not yet ready to dispatch"}, {name:"Ready", color:BLUE, description:"Unblocked and ready to dispatch"}, {id:"47fc9ee4", name:"In progress", color:YELLOW, description:"A worker is on it"}, {name:"In review", color:PURPLE, description:"PR open, awaiting review"}, {name:"Blocked", color:RED, description:"Waiting on another item or a finding"}, {id:"98236657", name:"Done", color:GREEN, description:"Merged or closed"} ] }){ projectV2Field { ... on ProjectV2SingleSelectField { id name options { id name color } } } } }'
{"data":{"updateProjectV2Field":{"projectV2Field":{"id":"PVTSSF_lAHOARFd7s4BkxtJzhjhD-Q","name":"Status","options":[{"id":"f75ad846","name":"Backlog","color":"GRAY"},{"id":"f3296da9","name":"Ready","color":"BLUE"},{"id":"47fc9ee4","name":"In progress","color":"YELLOW"},{"id":"3cc427c7","name":"In review","color":"PURPLE"},{"id":"8e90dd53","name":"Blocked","color":"RED"},{"id":"98236657","name":"Done","color":"GREEN"}]}}}}
```

## Views

The existing board `View 1` was renamed to Default with `updateProjectV2View`. The four tables were created with `createProjectV2View` (name, `TABLE_LAYOUT`, and the ordered visible fields Title, Status, Phase, Area, Harness, Priority, Size, Worker, Labels, Linked pull requests) and then given their filter with a second `updateProjectV2View` call, because the create input has no filter argument. The read-back after the calls:

| Number | Name | View id | Layout | Filter | Board column field | Group by | Sort by |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Default | `PVTV_lAHOARFd7s4BkxtJzgLzxVw` | board | none | Status (the board default, already set) | none | none |
| 2 | Phase | `PVTV_lAHOARFd7s4BkxtJzgLz5lk` | table | none | not applicable | none (needs the UI) | none |
| 3 | Ready to dispatch | `PVTV_lAHOARFd7s4BkxtJzgLz5lo` | table | `status:Ready` | not applicable | none | none (needs the UI) |
| 4 | Blocked | `PVTV_lAHOARFd7s4BkxtJzgLz5ls` | table | `status:Blocked` | not applicable | none | none |
| 5 | Experiments | `PVTV_lAHOARFd7s4BkxtJzgLz5lw` | table | `area:experiment` | not applicable | none | none |

The schema was re-checked before the calls: `ProjectV2ViewConfigurationInput` still has only `visibleFieldIds`, and neither view input accepts group-by, sort-by, or a column field, so the two settings the plan asks for that the API cannot set are the Phase view's grouping and the Ready to dispatch view's sort.

## What the operator still has to do in the UI

1. Open the Phase view, choose Group by, and pick Phase.
2. Open the Ready to dispatch view, choose Sort by, and pick Priority ascending.
3. Optionally check the Default board's columns show all six Status options; the API read-back reports Status as the column field, so this should already be the case.
4. Check the Workflows page: the item-closed and pull-request-merged workflows still target the Done option (its id was preserved), and the item-added workflow targets what was Todo and is now Backlog. Change the item-added target to Backlog explicitly if the UI shows it as unset.

## Issues filed

Twenty-nine issues, #26 to #54, filed with `gh issue create --title <title> --label <labels> --blocked-by <numbers> --body <body>` in dependency order so each blocked-by referred to an issue that already existed. Phase 2 is items 1 to 7 plus 4a of `PLAN.md` (#26 to #33). Phase 3 is the research synthesis (#34), the seventeen experiments in the critical-path and important lists of `design-sketch/12-experiments-and-open-questions.md` (#35 to #51, plan order), and the three decisions `PLAN.md` says phase 3 makes with evidence: daemon language, protocol schema format, and Tailscale integration (#52 to #54). The three bootstrap-specific experiments (18, 19, 20) were not filed separately because phase 2 items 5 and 6 (#31 and #32) cover them. The auto-add workflow put every new issue in the Project without a call from this worker.

| Issue | Title | Labels |
| --- | --- | --- |
| #26 | feat(bus): embed the NATS server in agentd with JetStream, per-group accounts, and per-agent credentials | area/bus, type/feature, phase/2, harness/claude |
| #27 | feat(bus): agentctl join, send, receive, ack, status, and roster | area/bus, type/feature, phase/2, harness/codex |
| #28 | feat(daemon): the SQLite registry and the host-tmux backend | area/daemon, type/feature, phase/2, harness/claude |
| #29 | feat(bus): shared context buckets and the memory tiers | area/bus, type/feature, phase/2, harness/codex |
| #30 | research(shell): shell-scripting conventions gate for hooks and agent-image scripts | area/research, type/research, phase/2, harness/claude |
| #31 | feat(tooling): hooks per harness for status and inbox checks | area/tooling, type/feature, phase/2, harness/claude, needs-operator |
| #32 | exp(bootstrap): host loopback, initial prompts, and waiter semantics per harness | area/experiment, type/experiment, phase/2, harness/claude |
| #33 | feat(bus): the coordinator on the bus with a background receive | area/bus, type/feature, phase/2, harness/claude |
| #34 | docs(research): synthesize the imported research into the Research section | area/research, type/docs, phase/3, harness/codex |
| #35 | exp(containers): harnesses on Linux arm64 inside an Apple Containers VM | area/experiment, type/experiment, phase/3, harness/claude, needs-operator |
| #36 | exp(security): shared authentication per harness across sessions and VMs | area/experiment, type/experiment, phase/3, harness/claude |
| #37 | exp(terminal): container exec -it fidelity for each harness TUI | area/experiment, type/experiment, phase/3, harness/claude |
| #38 | exp(terminal): shpool in the guest | area/experiment, type/experiment, phase/3, harness/claude |
| #39 | exp(containers): worktree mounts and permissions inside the VM | area/experiment, type/experiment, phase/3, harness/claude |
| #40 | exp(bus): embedded NATS semantics as the bus | area/experiment, type/experiment, phase/3, harness/claude |
| #41 | exp(bus): NATS topology and reachability from a VM | area/experiment, type/experiment, phase/3, harness/claude |
| #42 | exp(security): NATS credentials and agent identity | area/experiment, type/experiment, phase/3, harness/claude |
| #43 | exp(bus): waiter semantics across compaction and restart inside the VM | area/experiment, type/experiment, phase/3, harness/claude |
| #44 | exp(bus): bus wake mechanisms per harness inside the VM | area/experiment, type/experiment, phase/3, harness/claude |
| #45 | exp(containers): host file watching on virtiofs writes | area/experiment, type/experiment, phase/3, harness/any |
| #46 | exp(security): egress control through internal networks and the host proxy | area/experiment, type/experiment, phase/3, harness/any |
| #47 | exp(containers): memory per group VM with three harnesses running | area/experiment, type/experiment, phase/3, harness/any |
| #48 | exp(terminal): terminal fidelity end to end through shpool, exec, the daemon, and xterm.js | area/experiment, type/experiment, phase/3, harness/any |
| #49 | exp(remote): Tailscale integration with tsnet or tailscale serve | area/experiment, type/experiment, phase/3, harness/any |
| #50 | exp(ui): WebGL context limits for xterm.js in WKWebView, Safari, and Chrome | area/experiment, type/experiment, phase/3, harness/any |
| #51 | exp(daemon): harness-native control surfaces inside a VM | area/experiment, type/experiment, phase/3, harness/any |
| #52 | decision(daemon): choose the daemon language | area/daemon, type/decision, phase/3, harness/any |
| #53 | decision(daemon): choose the protocol schema format and code generation | area/daemon, type/decision, phase/3, harness/any |
| #54 | decision(remote): choose the Tailscale integration | area/remote, type/decision, phase/3, harness/any |

Blocked-by links set at creation, read back with `gh issue view`:

| Issue | Blocked by |
| --- | --- |
| #27 | #26 |
| #28 | #27 |
| #29 | #26 |
| #31 | #27, #30 |
| #32 | #26 |
| #33 | #27 |
| #36 | #35 |
| #37 | #35 |
| #38 | #37 |
| #39 | #35 |
| #40 | #26 |
| #41 | #40, #35 |
| #42 | #40 |
| #43 | #40, #32 |
| #44 | #35, #40 |
| #45 | #35 |
| #46 | #35 |
| #47 | #35 |
| #48 | #38 |
| #51 | #35 |
| #52 | #41, #40 |
| #54 | #49 |

## Field values on every item

The item ids came from one GraphQL read of `projectV2(number:9).items(first:100)`. Each item then got one `gh api graphql` mutation carrying six aliased `updateProjectV2ItemFieldValue` calls (Status, Phase, Area, Harness, Priority, Size by option id), which avoided the one-field-per-call limit of `gh project item-edit`. All forty-five calls returned the item id and no errors, and a final read of every item's six values matched this table. Issues #7, #8, and #10 closed while the run was in progress, so their Status is Done (the item-closed workflow set #7, and a second call set #8 and #10). Status Blocked follows the `blocked` label on #6, #9, and #11. Phase 2 and 3 items start in Backlog because neither phase has been opened. The Worker field is left empty for the coordinator to fill at dispatch.

| Issue | Status | Phase | Area | Harness | Priority | Size |
| --- | --- | --- | --- | --- | --- | --- |
| #3 | Done | 1 | tooling | claude | P1 | L |
| #4 | Done | 1 | research | claude | P1 | M |
| #5 | In progress | 1 | research | claude | P1 | M |
| #6 | Blocked | 1 | tooling | claude | P1 | M |
| #7 | Done | 1 | workflow | claude | P1 | M |
| #8 | Done | 1 | docs | claude | P1 | M |
| #9 | Blocked | 1 | docs | claude | P1 | L |
| #10 | Done | 1 | research | claude | P1 | M |
| #11 | Blocked | 1 | docs | codex | P1 | L |
| #12 | In progress | 1 | workflow | claude | P1 | M |
| #13 | Done | 1 | workflow | codex | P1 | S |
| #14 | Done | 1 | tooling | any | P1 | S |
| #15 | Ready | 1 | tooling | claude | P1 | S |
| #16 | Ready | 1 | tooling | claude | P1 | S |
| #17 | Ready | 1 | workflow | claude | P1 | S |
| #18 | Ready | 2 | workflow | any | P1 | M |
| #26 | Backlog | 2 | bus | claude | P0 | L |
| #27 | Backlog | 2 | bus | codex | P0 | M |
| #28 | Backlog | 2 | daemon | claude | P1 | L |
| #29 | Backlog | 2 | bus | codex | P0 | M |
| #30 | Backlog | 2 | research | claude | P1 | S |
| #31 | Backlog | 2 | tooling | claude | P1 | M |
| #32 | Backlog | 2 | experiment | claude | P1 | M |
| #33 | Backlog | 2 | bus | claude | P0 | S |
| #34 | Backlog | 3 | research | codex | P2 | L |
| #35 | Backlog | 3 | experiment | claude | P0 | L |
| #36 | Backlog | 3 | experiment | claude | P0 | L |
| #37 | Backlog | 3 | experiment | claude | P0 | M |
| #38 | Backlog | 3 | experiment | claude | P0 | M |
| #39 | Backlog | 3 | experiment | claude | P0 | M |
| #40 | Backlog | 3 | experiment | claude | P0 | M |
| #41 | Backlog | 3 | experiment | claude | P0 | M |
| #42 | Backlog | 3 | experiment | claude | P0 | M |
| #43 | Backlog | 3 | experiment | claude | P0 | S |
| #44 | Backlog | 3 | experiment | claude | P0 | M |
| #45 | Backlog | 3 | experiment | any | P2 | S |
| #46 | Backlog | 3 | experiment | any | P2 | M |
| #47 | Backlog | 3 | experiment | any | P2 | S |
| #48 | Backlog | 3 | experiment | any | P2 | M |
| #49 | Backlog | 3 | experiment | any | P2 | M |
| #50 | Backlog | 3 | experiment | any | P2 | S |
| #51 | Backlog | 3 | experiment | any | P2 | M |
| #52 | Backlog | 3 | daemon | any | P2 | S |
| #53 | Backlog | 3 | daemon | any | P2 | S |
| #54 | Backlog | 3 | remote | any | P2 | S |
