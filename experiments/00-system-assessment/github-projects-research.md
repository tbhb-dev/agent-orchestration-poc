# GitHub Projects v2 automation research

Scope: what a worker can script against the user project <https://github.com/users/tbhb/projects/9> (owner `tbhb`, number 9) and the repository `tbhb/agent-orchestration-poc`, using gh 2.100.0 (released 2026-09-03) and the GitHub GraphQL and REST APIs. All checks were read-only. Date of research: 2026-09-26. Every fact is labelled [help-text], [schema] (live GraphQL introspection through `gh query graphql`), [vendor-docs] (docs.github.com or github.blog, fetched 2026-09-26), or [observed] (a read-only API call against the live project or repository).

Authentication context: `gh auth status` shows the active account `tbhb` with token scopes `gist`, `project`, `read:org`, `repo`, `workflow` [observed]. The `project` scope is the one every `gh project` command and every Projects mutation needs: "The minimum required scope for the token is: `project`" [help-text, `gh project --help`], and the docs say to use "a token that has the `read:project` scope (for queries) or `project` scope (for queries and mutations)" [vendor-docs, https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects].

## 1. Fields

### Creating fields with gh

`gh project field-create` supports four data types and single-select options in one call. The help reads: `--data-type string  DataType of the new field.: {TEXT|SINGLE_SELECT|DATE|NUMBER}` and `--single-select-options strings  Options for SINGLE_SELECT data type`, with the example `gh project field-create 1 --owner monalisa --name "new field" --data-type "SINGLE_SELECT" --single-select-options "one,two,three"` [help-text, `gh project field-create --help`]. The manual page lists the same four values and no ITERATION [vendor-docs, https://cli.github.com/manual/gh_project_field-create].

So `gh` cannot create iteration fields, and it cannot set option colors or descriptions. Both are available through the raw mutation instead.

### Creating fields with GraphQL

`createProjectV2Field` takes `CreateProjectV2FieldInput` with `projectId: ID!`, `dataType: ProjectV2CustomFieldType!`, `name: String!`, `singleSelectOptions: [ProjectV2SingleSelectFieldOptionInput!]` ("At least one value is required if data_type is SINGLE_SELECT"), `multiSelectOptions: [ProjectV2MultiSelectFieldOptionInput!]`, and `iterationConfiguration: ProjectV2IterationFieldConfigurationInput` [schema].

`ProjectV2CustomFieldType` has six values: `TEXT`, `SINGLE_SELECT`, `MULTI_SELECT`, `NUMBER`, `DATE`, `ITERATION` [schema]. Multi-select is new: the GraphQL changelog entry for 2026-07-27 records `MULTI_SELECT` being added to `ProjectV2CustomFieldType` and `multiSelectOptions` being added to `UpdateProjectV2FieldInput` [vendor-docs, https://docs.github.com/en/graphql/overview/changelog/2026]. `gh project item-edit` has no multi-select flag, so multi-select values can only be set through `updateProjectV2ItemFieldValue` with `multiSelectOptionIds` [help-text, schema].

`ProjectV2IterationFieldConfigurationInput` has `startDate: Date!`, `duration: Int!` (days), and `iterations: [ProjectV2Iteration!]!` where each `ProjectV2Iteration` input is `startDate: Date!`, `duration: Int!`, `title: String!` [schema]. That is the only way to create an iteration field; it is not exposed in `gh`.

### Editing existing fields, including single-select options

`updateProjectV2Field` exists (added to the schema on 2024-12-04 per the GraphQL changelog for 2024; `iterationConfiguration` added 2025-02-14 per the 2025 changelog) [vendor-docs, https://docs.github.com/en/graphql/overview/changelog/2024 and /2025]. Its input `UpdateProjectV2FieldInput` has [schema]:

- `fieldId: ID!` ("The ID of the field to update.")
- `name: String` ("The name to update.")
- `singleSelectOptions: [ProjectV2SingleSelectFieldOptionInput!]` ("Options for a field of type SINGLE_SELECT. Empty input is ignored, provided values overwrite existing options, and existing options should be fetched for partial updates.")
- `multiSelectOptions: [ProjectV2MultiSelectFieldOptionInput!]` (same wording for MULTI_SELECT)
- `iterationConfiguration: ProjectV2IterationFieldConfigurationInput` ("provided values overwrite the existing configuration")

`ProjectV2SingleSelectFieldOptionInput` has four input fields [schema]:

- `id: String` ("The ID of an existing single select option. Include this to preserve the option's identity during updates, preventing item field values from being cleared.")
- `name: String!` ("The name of the option")
- `color: ProjectV2SingleSelectFieldOptionColor!` (enum: `GRAY`, `BLUE`, `GREEN`, `YELLOW`, `ORANGE`, `RED`, `PINK`, `PURPLE`)
- `description: String!` ("The description text of the option")

Practical consequence: adding or renaming options is a full replace. To add one option, fetch the current options (id, name, color, description), resend all of them with their `id` values plus the new option without an `id`. To rename, resend the same `id` with the new `name`. Omitting an existing option from the list deletes it and clears that value on every item. `color` and `description` are non-null on the input, so the worker must send them for every option even when unchanged (an empty string is a valid `description`). Single-select fields are limited to 50 options [vendor-docs, https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-single-select-fields].

There is no `gh` subcommand for editing a field. `gh project field-delete --id <field-id>` deletes one [help-text].

## 2. Views

Views are now scriptable, and this is recent. The live schema contains three view mutations [schema, introspection of `Mutation` filtered on `ProjectV2`]:

- `createProjectV2View`: "Creates a new view in a project." Input `CreateProjectV2ViewInput`: `projectId: ID!`, `name: String!`, `layout: ProjectV2ViewLayout!`, `configuration: ProjectV2ViewConfigurationInput`.
- `updateProjectV2View`: "Updates an existing view in a project." Input `UpdateProjectV2ViewInput`: `viewId: ID!`, `name: String`, `layout: ProjectV2ViewLayout`, `filter: String` ("The new filter for the view."), `configuration: ProjectV2ViewConfigurationInput`.
- `deleteProjectV2View`: "Deletes a view from a project." Input: `viewId: ID!`.

`ProjectV2ViewLayout` has exactly `BOARD_LAYOUT`, `TABLE_LAYOUT`, `ROADMAP_LAYOUT` [schema]. `ProjectV2ViewConfigurationInput` has exactly one input field: `visibleFieldIds: [ID!]` ("The ordered IDs of the fields visible in the view.") [schema]. The matching output type `ProjectV2ViewConfiguration` has one field, `visibleFields` [schema].

The GraphQL changelog dates these: the three mutations and their input types were added on 2026-07-28 (`CreateProjectV2ViewInput` initially with `projectId`, `name`, `layout`; `UpdateProjectV2ViewInput` with `viewId`, `name`, `layout`, `filter`), and `ProjectV2ViewConfigurationInput` with `visibleFieldIds` plus the `configuration` argument on both inputs were added on 2026-07-30 [vendor-docs, https://docs.github.com/en/graphql/overview/changelog/2026, sections "Schema changes for 2026-07-28" and "2026-07-30"]. A community discussion opened 2026-05-01 asking for exactly these mutations had no staff reply and predates the ship [vendor-docs, https://github.com/orgs/community/discussions/194509]. The projects API guide page does not mention the view mutations yet [vendor-docs, using-the-api-to-manage-projects page fetched 2026-09-26].

What the API can and cannot configure on a view, as of this schema [schema]:

- Can: create, rename, delete, change layout, set the filter string (update only; `createProjectV2View` has no `filter` input, so create then update), and set the ordered list of visible fields.
- Cannot: set grouping, vertical grouping (board columns), sorting, slicing, column field for boards, roadmap date fields or zoom, or field sums. The read side exposes `groupByFields`, `sortByFields`, `verticalGroupByFields` on `ProjectV2View`, but no input accepts them.

So a worker can script the existence, name, layout, filter, and visible columns of every view, but the operator must open each board view in the UI to pick the column field if it should be anything other than the default (a new board view groups by Status by default, see the observed view in section 7), and must set any group-by or sort-by in the UI.

`gh` has no view subcommands at all: `gh project --help` lists close, copy, create, delete, edit, field-create, field-delete, field-list, item-add, item-archive, item-create, item-delete, item-edit, item-list, link, list, mark-template, unlink, view [help-text]. Use `gh query graphql` (reads) and `gh api graphql` (mutations) for views.

## 3. Items

Adding: `gh project item-add [<number>] --owner <login> --url <issue-or-pr-url>` ("Add a pull request or an issue to a project") [help-text]. Draft issues: `gh project item-create <number> --owner <login> --title ... --body ...` [help-text]. Adding an issue to a project from `gh issue create -p <project title>` also works but "requires authorization with the `project` scope" [help-text, `gh issue create --help`]; the token already has it [observed].

Editing field values: `gh project item-edit` supports two addressing modes. By name: `--owner`, project number, `--url <issue-or-pr-url>`, `--field <name>`, `--value <value>`, where "For single-select fields, `--value` is the option name." By node id: `--id <item-id> --field-id <field-id> --project-id <project-id>` plus one typed value flag: `--text string`, `--number float`, `--date string` (YYYY-MM-DD), `--single-select-option-id string`, `--iteration-id string`. `--clear` removes a value. "For non-draft issues, only a single field value can be updated per invocation." Draft issues additionally accept `--title` and `--body` [help-text, `gh project item-edit --help`]. Example from the help: `gh project item-edit 1 --owner monalisa --url https://github.com/monalisa/myproject/issues/23 --field "Status" --value "In Progress"`.

The underlying mutation `updateProjectV2ItemFieldValue` takes `projectId`, `itemId`, `fieldId`, and `value: ProjectV2FieldValue!` where `ProjectV2FieldValue` is one of `text`, `number`, `date`, `singleSelectOptionId`, `multiSelectOptionIds`, `iterationId` [schema]. Its description says "Currently only single-select, multi-select, text, number, date, and iteration fields are supported" [schema], so Assignees, Labels, Milestone, and Repository are set on the issue itself, not through the project.

Listing item ids: `gh project item-list <number> --owner <login> --format json -L <n> [--query "<projects filter syntax>"]` [help-text].

Archiving and deleting: `gh project item-archive <number> --owner <login> --id <item-id>` with `--undo` to unarchive; `gh project item-delete <number> --owner <login> --id <item-id>` [help-text]. GraphQL equivalents `archiveProjectV2Item`, `unarchiveProjectV2Item`, `deleteProjectV2Item` exist [schema].

## 4. Status field and built-in workflows

The built-in `Status` field on project 9 is an ordinary `ProjectV2SingleSelectField` with id `PVTSSF_lAHOARFd7s4BkxtJzhjhD-Q` and three options: `Todo` (`f75ad846`), `In Progress` (`47fc9ee4`), `Done` (`98236657`) [observed, `gh project field-list 9 --owner tbhb --format json`]. Its id has the same `PVTSSF_` prefix as any custom single-select field.

`updateProjectV2Field` takes any `fieldId` and its `singleSelectOptions` argument replaces the option set [schema]. Nothing in the schema distinguishes Status from a custom single-select field, so replacing or extending Status options should work with the same fetch-then-resend procedure described in section 1. This was not verified by mutation because the task is read-only. A 2023 community thread complained that Status could not be edited via API; that predates `updateProjectV2Field` (added 2024-12-04) and has no later resolution comment [vendor-docs, https://github.com/orgs/community/discussions/44265]. Recommendation: the phase 1 worker should try the mutation on Status first and fall back to the UI only if it errors. Keep the existing three option ids in the payload so the built-in workflows that reference Todo and Done keep their targets.

Built-in workflows are UI-only for configuration. The project already has seven workflows, all enabled [observed, GraphQL `workflows(first:20)`]:

| Number | Name | Id |
| --- | --- | --- |
| 1 | Item closed | `PWF_lAHOARFd7s4BkxtJzgcbObQ` |
| 2 | Pull request merged | `PWF_lAHOARFd7s4BkxtJzgcbObU` |
| 3 | Auto-close issue | `PWF_lAHOARFd7s4BkxtJzgcbObY` |
| 4 | Auto-add sub-issues to project | `PWF_lAHOARFd7s4BkxtJzgcbObc` |
| 5 | Pull request linked to issue | `PWF_lAHOARFd7s4BkxtJzgcbObg` |
| 6 | Item added to project | `PWF_lAHOARFd7s4BkxtJzgcbObk` |
| 7 | Auto-add to project | `PWF_lAHOARFd7s4BkxtJzgcbOd4` |

The only workflow mutation in the schema is `deleteProjectV2Workflow` (input `workflowId: ID!`) [schema]. There is no create, update, enable, or configure mutation, and the `ProjectV2Workflow` type exposes only `id`, `name`, `number`, `enabled`, timestamps, and `project` [schema]. The docs describe workflow configuration only as UI steps ("Workflows", "Edit", "Save and turn on workflow") and mention no API [vendor-docs, https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations]. The docs also state the defaults: "When issues or pull requests in your project are closed, their status is set to Done, and when pull requests in your project are merged, their status is set to Done" [vendor-docs, same page].

Auto-add is plan-limited: "The auto-add workflow is limited per plan" with a table of GitHub Free 1, GitHub Pro 5, GitHub Team 5, GitHub Enterprise Cloud 20, GitHub Enterprise Server 20 [vendor-docs, https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/adding-items-automatically]. Each auto-add workflow targets one repository plus a filter, configured in the UI only [vendor-docs, same page]. Auto-archive accepts `is:`, `reason:`, and `updated:` filters and is also UI-only [vendor-docs, https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/archiving-items-automatically].

Alternative to auto-add that a worker can script: the auto-add workflow number 7 above is enabled but its target repository and filter are not readable through the API. If the operator does not configure it in the UI, the worker can add items itself with `gh project item-add`, or via issue forms with a `projects:` key (section 5), or by passing `--project "agent-orchestration-poc"` to `gh issue create`.

## 5. Issue types, sub-issues, and issue templates

### Issue types

Organization-only. The docs page is titled "Managing issue types in an organization" and its permission callout reads "Who can use this feature? Organization owners can modify issue types." and "You can create up to 25 issue types that your organization members can apply to issues" [vendor-docs, https://docs.github.com/en/issues/tracking-your-work-with-issues/configuring-issues/managing-issue-types-in-an-organization]. The `createIssueType` mutation's `ownerId` is described as "The ID for the organization on which the issue type is created" [schema]. A GitHub staff reply dated 2025-10-05 states the features are "available only for organizations... not for personal repositories, even on paid personal plans" [vendor-docs, https://github.com/orgs/community/discussions/175785].

Observed on this repository: `gh query repos/tbhb/agent-orchestration-poc/issue-types` returns Task, Bug, and Feature with `is_enabled: true`, but GraphQL `repository.issueTypes` returns `null` for the same repository, and a search across 85 issues on `tbhb` personal repositories found none with an `issueType` set [observed]. Treat issue types as unavailable here. `gh issue create --type <name>` and `gh issue edit --type` exist [help-text] but have no types to target on a user repo. Use labels or a single-select project field instead.

### Sub-issues

Available on this account's personal repositories. Docs: "People with at least triage permissions for a repository can add sub-issues", "You can add up to 100 sub-issues per parent issue", "up to eight levels of nested sub-issues" [vendor-docs, https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues]. Observed: the personal repository `tbhb/typing-graph.internal` has issues 15, 25, and 35 with sub-issue totals of 9, 6, and 1, and sixteen issues carrying a `parent`, so the staff statement in the discussion above about sub-issues on personal repos does not match current behaviour on this account [observed, GraphQL search `user:tbhb is:issue`].

CLI support [help-text, `gh issue create --help` and `gh issue edit --help`]: `gh issue create --parent <number-or-url>`, `gh issue create --blocked-by <numbers> --blocking <numbers>`, `gh issue edit <parent> --add-sub-issue 123,124`, `--remove-sub-issue`, `gh issue edit <child> --parent <n>` and `--remove-parent`, `--add-blocked-by`, `--remove-blocked-by`. GraphQL: `addSubIssue`, `removeSubIssue`, `reprioritizeSubIssue`, and `CreateIssueInput.parentIssueId` [schema]. REST: `POST /repos/{owner}/{repo}/issues/{issue_number}/sub_issues` with body `{"sub_issue_id": <issue database id>, "replace_parent": <bool>}`, plus GET `.../sub_issues`, GET `.../parent`, DELETE `.../sub_issue`, PATCH `.../sub_issues/priority` [vendor-docs, https://docs.github.com/en/rest/issues/sub-issues]. The project already has "Parent issue" and "Sub-issues progress" fields and an "Auto-add sub-issues to project" workflow [observed].

### Issue forms

YAML issue forms live in `/.github/ISSUE_TEMPLATE` and are "currently in public preview and subject to change" [vendor-docs, https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms]. Required top-level keys are `name`, `description`, `body`; optional keys are `title`, `labels`, `assignees`, `type`, `projects` [vendor-docs, same page]. The `projects` key takes `PROJECT-OWNER/PROJECT-NUMBER` (here `tbhb/9`) with the note "The person opening the issue must have write permissions for the specified projects. If you don't expect people using this template to have write access, consider enabling your project's auto-add workflow" [vendor-docs, same page]. The `type` key needs organization issue types and is useless here. The repository currently has no `.github` directory [observed].

### gh issue create in one go

`gh issue create` accepts `-T, --template name` ("Template name to use as starting body text"), `-p, --project title` ("Add the issue to projects by title"), `-l --label`, `-m --milestone`, `-a --assignee`, `--parent`, `--blocked-by`, `--blocking`, `--type` [help-text]. It has no flag for project field values (Status, custom single-selects, and so on). Setting those is a second step with `gh project item-edit` or `updateProjectV2ItemFieldValue`. The GraphQL `createIssue` mutation matches: `projectV2Ids`, `issueTemplate`, `parentIssueId`, `labelIds`, `milestoneId`, `issueTypeId`, `issueFields`, no project field values [schema].

## 6. Labels and branch protection

### Labels

`gh label create <name> [-c color] [-d description] [-f]`: "Create a new label on GitHub, or update an existing one with `--force`." The color is a six-character hex value and is random when omitted [help-text, `gh label create --help`]. The repository currently has the ten GitHub default labels: accessibility, bug, documentation, duplicate, enhancement, good first issue, help wanted, invalid, question, wontfix [observed, `gh label list`]. Idempotent scripting is `gh label create <name> --color <hex> --description "<text>" --force`.

### Repository facts

`tbhb/agent-orchestration-poc` is owned by a `User`, is `private`, default branch `main`, no rulesets (`GET repos/.../rulesets` returns `[]`, `gh ruleset check main` reports "0 rules apply"), and `main` is not protected (`GET repos/.../branches/main/protection` returns 404 "Branch not protected") [observed]. The plan could not be read: `gh query user` returns `plan: null` with the current scopes [observed].

### Availability by plan

Rulesets: "Rulesets are available in public repositories with GitHub Free and GitHub Free for organizations, and in public and private repositories with GitHub Pro, GitHub Team, and GitHub Enterprise Cloud." [vendor-docs, https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets]. Protected branches: "Protected branches are available in public repositories with GitHub Free and GitHub Free for organizations. Protected branches are also available in public and private repositories with GitHub Pro, GitHub Team, GitHub Enterprise Cloud, and GitHub Enterprise Server." [vendor-docs, https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches]. Both features therefore need GitHub Pro on this private user-owned repository; neither is available on GitHub Free for a private repo. One weak signal that the account has Pro: the protection GET returned "Branch not protected" rather than a plan-upgrade error, but confirm by checking <https://github.com/settings/billing> in the UI before relying on it.

Recommendation: use a ruleset, not classic branch protection. Docs list the advantages: several rulesets apply at once where "only a single branch protection rule can apply at a time", enforcement can be set to `evaluate` or `disabled` without deleting the rules, and read-access users can see the rules [vendor-docs, about-rulesets and about-protected-branches pages]. Rulesets also apply to the repository admin unless a bypass actor is added, which is the right default for a solo repo that wants agents and the operator to go through pull requests. `gh ruleset` is read-only (`check`, `list`, `view`) [help-text, `gh ruleset --help`], so creation goes through `gh api`.

### Ruleset endpoint and body (not run)

Endpoint: `POST /repos/tbhb/agent-orchestration-poc/rulesets` with `Accept: application/vnd.github+json` [vendor-docs, https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset]. Top-level fields: `name` (required), `target` (`branch`), `enforcement` (`active`, `evaluate`, `disabled`), `bypass_actors`, `conditions.ref_name.include/exclude`, `rules` [vendor-docs, same page]. Rule shapes from the same page: `pull_request` with `required_approving_review_count`, `dismiss_stale_reviews_on_push`, `require_code_owner_review`, `require_last_push_approval`, `required_review_thread_resolution`, `allowed_merge_methods`; `required_status_checks` with `required_status_checks: [{context, integration_id}]`, `strict_required_status_checks_policy`, `do_not_enforce_on_create`; `non_fast_forward` (blocks force pushes) and `deletion` take no parameters. For `bypass_actors`, `actor_type` may be `Integration`, `OrganizationAdmin`, `RepositoryRole`, `Team`, `DeployKey`, `User`; `OrganizationAdmin` "is not applicable for personal repositories"; repository role ids are admin 5, maintain 2, write 4; `bypass_mode` is `always`, `pull_request`, or `exempt` [vendor-docs, same page]. The `context` is "The status check context name that must be present on the commit", which for GitHub Actions is the job name (or the job's `name:` if set), and `integration_id` 15368 pins it to GitHub Actions [vendor-docs, same page].

```bash
gh api -X POST repos/tbhb/agent-orchestration-poc/rulesets \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true,
        "allowed_merge_methods": ["squash"] } },
    { "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "<job name from ci.yml>", "integration_id": 15368 }
        ] } }
  ]
}
JSON
```

Notes on that body: `required_approving_review_count` 0 still requires a pull request but lets a solo owner merge without a second account; raise it if review by another account is wanted. To let the owner bypass in emergencies add `{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}` to `bypass_actors`. `~DEFAULT_BRANCH` is the documented ref pattern for the default branch; `refs/heads/main` also works. The status check context must match a job that actually runs on pull requests, otherwise merges block forever, so create the workflow first and copy the job name exactly.

Classic alternative, also not run: `PUT /repos/tbhb/agent-orchestration-poc/branches/main/protection` where `required_status_checks`, `enforce_admins`, `required_pull_request_reviews`, and `restrictions` are all required keys (nullable), with `required_status_checks: {strict, contexts, checks: [{context, app_id}]}`, `required_pull_request_reviews: {dismiss_stale_reviews, require_code_owner_reviews, required_approving_review_count, require_last_push_approval}`, and optional `allow_force_pushes`, `allow_deletions`, `required_linear_history`, `required_conversation_resolution`, `lock_branch` [vendor-docs, https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection]. `restrictions` must be `null` on a user-owned repository since push restrictions are organization-only [vendor-docs, about-protected-branches page].

## 7. Current project state (read-only snapshot, 2026-09-26)

Project node id `PVT_kwHOARFd7s4BkxtJ`, title `agent-orchestration-poc`, url <https://github.com/users/tbhb/projects/9>, private, open, empty readme and description, 0 items [observed, `gh project view 9 --owner tbhb --format json` and GraphQL]. Repository node id `R_kgDOUtKbtw` [observed].

Fields (13 total) [observed, `gh project field-list 9 --owner tbhb --format json`]:

| Field | Type | Id | Options |
| --- | --- | --- | --- |
| Title | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-I` | |
| Assignees | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-M` | |
| Status | ProjectV2SingleSelectField | `PVTSSF_lAHOARFd7s4BkxtJzhjhD-Q` | Todo `f75ad846`, In Progress `47fc9ee4`, Done `98236657` |
| Labels | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-U` | |
| Linked pull requests | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-Y` | |
| Milestone | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-c` | |
| Repository | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-g` | |
| Reviewers | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-o` | |
| Parent issue | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-s` | |
| Sub-issues progress | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-w` | |
| Created | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-0` | |
| Updated | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-4` | |
| Closed | ProjectV2Field | `PVTF_lAHOARFd7s4BkxtJzhjhD-8` | |

No custom fields exist yet. `field-list` does not report option colors or descriptions; fetch them with GraphQL (`... on ProjectV2SingleSelectField { options { id name color description } }`) before any `updateProjectV2Field` call.

Views (1 total) [observed, GraphQL `views(first:20)`]:

| Number | Name | Id | Layout | Filter | Visible fields | Vertical group (columns) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | View 1 | `PVTV_lAHOARFd7s4BkxtJzgLzxVw` | `BOARD_LAYOUT` | empty | Title, Assignees, Status, Linked pull requests, Sub-issues progress | Status |

The view has no group-by or sort-by set. It was created 2026-09-26T16:46:12Z.

Workflows: the seven listed in section 4, all enabled. Their targets and filters are not readable through the API.

Repository: private, user-owned, default branch `main`, no rulesets, no branch protection, ten default labels, no `.github` directory, one issue-or-PR returned by the issues endpoint (issue 1 does not resolve as an Issue, so it is a pull request) [observed].

## Implications for automating the project setup

What a worker can script, in dependency order:

- Labels: `gh label create ... --force` for each label, idempotent.
- Custom fields: `gh project field-create 9 --owner tbhb` for text, number, date, and single-select fields (names only); `gh api graphql` with `createProjectV2Field` when option colors, descriptions, an iteration field, or a multi-select field are wanted.
- Status options: `updateProjectV2Field` with the full option list, keeping the three existing ids. Unverified on the built-in field; try it first and report the error if GitHub refuses.
- Views: `createProjectV2View` (name, layout) then `updateProjectV2View` (filter, visibleFieldIds), and `deleteProjectV2View` or a rename for the default "View 1". Filter strings use the same syntax as the UI filter bar.
- Issue forms: commit YAML under `.github/ISSUE_TEMPLATE/` with `labels:` and `projects: ["tbhb/9"]`; no `type:` key.
- Issues and hierarchy: `gh issue create --template ... --label ... --project agent-orchestration-poc --parent N`, then `gh project item-edit` per field value (one field per call for real issues). `gh project item-list --format json` yields item ids.
- Branch protection: one `gh api -X POST repos/tbhb/agent-orchestration-poc/rulesets` call with the body above, after the CI workflow exists so the job name is known. Needs GitHub Pro for this private repo.
- Linking the project to the repository: `gh project link 9 --owner tbhb --repo agent-orchestration-poc` (or `linkProjectV2ToRepository`), so the project appears in the repository's Projects tab and in the issue sidebar.

What the operator must do in the UI:

- Board column field, group-by, sort-by, slice-by, roadmap date fields, and field sums on every view. The API only sets name, layout, filter, and visible fields.
- Auto-add workflow target repository and filter (one workflow on GitHub Free, five on Pro), auto-archive filter, and any change to which Status option the item-closed, PR-merged, and item-added workflows set. The API can list and delete workflows only.
- Confirm the plan on the billing page before the ruleset call, and fall back to making the repo public or upgrading if the call returns a plan error.
- Issue types: not available on a personal repository; do not plan around them.
