# Mermaid check lodash-es alert evidence

## Scope and versions

This report concerns only `scripts/mermaid-check`. [High alert #2](https://github.com/tbhb/agent-orchestration-poc/security/dependabot/2) covers `_.template` imports key names and [medium alert #1](https://github.com/tbhb/agent-orchestration-poc/security/dependabot/1) covers `_.unset` and `_.omit`. Both list 4.18.0 as the first patched `lodash-es` version. The direct pins remain `mermaid@12.0.0` and `jsdom@30.1.1`. Commands used pnpm 12.7.0 and Node 24.21.0 through mise. The repository head before this change was `1856e7b4ba68916bfb582767aedb8fb133b5e599`.

The versioned source inspected was [Mermaid tag `mermaid@12.0.0`](https://github.com/mermaid-js/mermaid/tree/98a0945418c76238f15df2afaddbba4272656c3b) at commit `98a0945418c76238f15df2afaddbba4272656c3b` and [Chevrotain tag `v11.1.2`](https://github.com/Chevrotain/chevrotain/tree/3a0ee6abc9ef3b22448cc72ec54ec4987e44ab9b) at commit `3a0ee6abc9ef3b22448cc72ec54ec4987e44ab9b`. The clones used for inspection are `/tmp/issue-102-mermaid` and `/tmp/issue-102-chevrotain`. The [Mermaid 12.0.0 use case syntax](https://mermaid.js.org/syntax/usecase.html) and [pnpm 12.x override settings](https://pnpm.io/settings/dependency-resolution#overrides) were also read. The source and documentation versions bound the conclusions below.

## Dependency graph and resolution

**Verified:** `mermaid@12.0.0` declares `chevrotain: ~11.1.2` in `packages/mermaid/package.json`. At the Chevrotain commit, `packages/chevrotain/package.json`, `packages/gast/package.json`, and `packages/cst-dts-gen/package.json` each declare `lodash-es: 4.17.23` exactly. `jsdom@30.1.1` is absent from the `pnpm why` paths. Before the change, `mise exec -- pnpm --dir scripts/mermaid-check why lodash-es` exited 0 with this exact output:

```text
lodash-es@4.17.23
├─┬ @chevrotain/cst-dts-gen@11.1.2
│ └─┬ chevrotain@11.1.2
│   └─┬ mermaid@12.0.0
│     └── mermaid-check (dependencies)
├─┬ @chevrotain/gast@11.1.2
│ ├── @chevrotain/cst-dts-gen@11.1.2 [deduped]
│ └── chevrotain@11.1.2 [deduped]
└── chevrotain@11.1.2 [deduped]

lodash-es@4.18.1
└─┬ dagre-d3-es@7.0.14
  └─┬ mermaid@12.0.0
    └── mermaid-check (dependencies)

Found 2 versions of lodash-es
```

**Observed:** `mise exec -- pnpm --dir scripts/mermaid-check update lodash-es@4.18.1 --lockfile-only --no-save` exited 1 with `ERR_PNPM_UPDATE_VERSION_ON_INDIRECT_DEP` because `lodash-es` is transitive. A trial `pnpm.overrides` field in this package's `package.json` was ignored by pnpm 12.7.0 with the warning `The "pnpm" field in package.json is no longer read by pnpm`; the trial field was removed. The pnpm 12.x documentation locates overrides in `pnpm-workspace.yaml`, outside this issue's allowed paths. The registry query `mise exec -- pnpm view mermaid version dependencies.chevrotain` reported `12.0.0` and `~11.1.2`, so no newer stable direct Mermaid pin was available during this run.

**Verified:** The reviewed lockfile change replaces three Chevrotain snapshot references to 4.17.23 with 4.18.1 and deletes the 4.17.23 package and snapshot entries. The 4.18.1 package and integrity were already in this lockfile through `dagre-d3-es@7.0.14`. `rg -n '4\.17\.23' scripts/mermaid-check/pnpm-lock.yaml` exited 1 with no matches. `mise exec -- pnpm install --frozen-lockfile --dir scripts/mermaid-check` exited 0, verified 154 supply chain entries, and installed the updated graph. `mise exec -- pnpm install --lockfile-only --dir scripts/mermaid-check` then exited 0 with `Already up to date`, leaving the lockfile unchanged. A future fresh resolution could restore Chevrotain's exact 4.17.23 request, so the lockfile should be checked when it is regenerated.

The lockfile diff removes the `lodash-es@4.17.23` package resolution and empty snapshot, and makes these three replacements:

```text
@chevrotain/cst-dts-gen@11.1.2: lodash-es 4.17.23 -> 4.18.1
@chevrotain/gast@11.1.2:        lodash-es 4.17.23 -> 4.18.1
chevrotain@11.1.2:              lodash-es 4.17.23 -> 4.18.1
```

After the frozen install, `mise exec -- pnpm --dir scripts/mermaid-check why lodash-es` exited 0 with this exact output:

```text
lodash-es@4.18.1
├─┬ @chevrotain/cst-dts-gen@11.1.2
│ └─┬ chevrotain@11.1.2
│   └─┬ mermaid@12.0.0
│     └── mermaid-check (dependencies)
├─┬ @chevrotain/gast@11.1.2
│ ├── @chevrotain/cst-dts-gen@11.1.2 [deduped]
│ └── chevrotain@11.1.2 [deduped]
├── chevrotain@11.1.2 [deduped]
└─┬ dagre-d3-es@7.0.14
  └── mermaid@12.0.0 [deduped]

Found 1 version of lodash-es
```

## Parse reachability

**Verified:** `scripts/mermaid-check/check.mjs` passes each fenced block body to `mermaid.parse`. In Mermaid 12.0.0 source, `packages/mermaid/src/mermaidAPI.ts` calls `Diagram.fromText`, and `packages/mermaid/src/Diagram.ts` calls the selected diagram parser. The `usecase-beta` detector in `packages/mermaid/src/diagrams/usecase/usecaseDetector.ts` selects `packages/mermaid/src/diagrams/usecase/parser/usecase.chevrotain.ts`, which calls `runChevrotainParse`. That helper tokenizes with the Chevrotain lexer, enters the Chevrotain parser, and visits the CST. Attacker-controlled Mermaid block content can therefore reach Chevrotain and its Lodash imports through a use case diagram.

**Verified within the inspected source:** A search of all TypeScript source files under Chevrotain's `packages/chevrotain/src`, `packages/gast/src`, and `packages/cst-dts-gen/src` found 31 imports from `lodash-es`. None imports or calls `template`, `unset`, or `omit`. The only `template` text match was a comment about template strings in `parse/errors_public.ts`. This supports the narrower inference that those three vulnerable functions are not called by the inspected Chevrotain source on this parse path. It is not a whole-dependency-graph proof or a claim about other applications using Lodash.

**Observed:** Explicit checks of `tests/fixtures/mermaid_check/valid.txt` and `probe.txt` each exited 0 with `mermaid: 1 block(s) in 1 file(s), 0 invalid`. The probe puts `__proto__ constructor template unset omit` in a use case label and exercises the Chevrotain parse path. `tests/fixtures/mermaid_check/invalid.txt` exited 1 with `invalid mermaid block: Error parsing usecase diagram: Expecting: one of these possible Token sequences:` and `mermaid: 1 block(s) in 1 file(s), 1 invalid`. The clean probe result shows accepted input only and does not establish function nonreachability.

## Dependabot result and validation

**Observed:** [Dependabot run 36283746753](https://github.com/tbhb/agent-orchestration-poc/actions/runs/36283746753) concluded failure. Its redacted error named `security_update_not_possible`, `latest-resolvable-version: 4.17.23`, and `lowest-non-vulnerable-version: 4.18.1`, with an empty conflicting dependencies list. The run attempted `pnpm update lodash-es@4.18.1 --lockfile-only --no-save -r`. This was Dependabot's resolver result, separate from the local frozen installation and lockfile-only resolution reported above. The full job log remained in `/tmp/issue-102-dependabot.log` and was not committed because it includes job metadata.

`mise run check:mermaid` exited 0 with `mermaid: 7 block(s) in 101 file(s), 0 invalid`. The intentionally invalid fixture has a `.txt` extension so the default Markdown inventory does not parse it. `mise run fmt` exited 0 and changed no additional tracked files. `mise run check` exited 0 with `52 passed, 2 skipped in 4.30s` from pytest, successful Go race tests, and `Finished in 17.56s` for the aggregate. The two skipped Python tests require `--run-integration` and are unrelated to this dependency change. `mise run build` exited 0. `mise run check:mutation` exited 0 with 85 of 85 Go mutants killed, 100 percent Python core line coverage, and a Python core mutation score of 83.33 percent (200 of 240 killed).

The first commit attempt failed because prek could not open its default cache log under the sandbox. The normal hooks passed with prek's documented `PREK_HOME` set to `/tmp/issue-102-prek`, an allowed temporary location. No sandbox permission change was requested.

## Post-merge alert status

**Untested:** Alert closure requires the repaired lockfile to merge into `main` and Dependabot to rescan it. The coordinator can query alerts #1 and #2 after merge and link the result on issue #102. Both alerts were open before this PR.
