# Docs stack research gate versions

Every package version and clone read for issue #8 on 2026-09-26. Versions come from `mise exec -- npm view <pkg> version peerDependencies` run from this worktree; clone SHAs come from `git rev-parse HEAD` in each clone.

## Runtime and tools in this checkout

| Tool | Version | How obtained |
| --- | --- | --- |
| Node | v24.21.0 | `mise exec -- node --version` (`node = "lts"` in `mise.toml`) |
| pnpm (global, not pinned) | 10.32.1 | `mise exec -- pnpm --version` resolves `/Users/tony/Library/pnpm/pnpm` |
| pnpm (npx) | 12.6.0 | `mise exec -- npx --yes pnpm --version` |
| pnpm available to mise | 12.5.1, 12.6.0, 12.7.0 | `mise ls-remote pnpm` (last three) |
| mise | 2026.8.6 macos-arm64 | printed by mise in an error message |
| guard-markdown | on PATH | `which guard-markdown` gives `/Users/tony/go/bin/guard-markdown` |

## npm package versions

| Package | Version | Peer dependencies | Notes |
| --- | --- | --- | --- |
| `astro` | 7.3.5 | `@astrojs/markdown-remark ^7.3.0` | engines `node >=22.12.0`; modified 2026-09-24 |
| `@astrojs/starlight` | 0.42.4 | `astro ^7.2.10`, `@astrojs/markdown-remark ^7.3.0` (optional) | modified 2026-09-24 |
| `@astrojs/mdx` | 8.0.2 | `astro ^7.2.10`, `@astrojs/markdown-remark ^7.3.0`, `@astrojs/markdown-satteri ^0.4.0` | |
| `@astrojs/markdown-satteri` | 0.4.2 | none | default processor in Astro 7 |
| `@astrojs/markdown-remark` | 7.3.1 | none | needed for `unified()` and rehype plugins |
| `satteri` | 0.10.5 | none | |
| `astro-expressive-code` | 0.44.2 | `astro ^3.3.0 || ^4 || ^5 || ^6 || ^7.0.0` | Starlight dependency |
| `@astrojs/check` | 0.9.10 | `typescript ^5.0.0 || ^6.0.0` | |
| `typescript` | 7.0.2 latest; 6.0.3 newest 6.x | none | pin 6.x for `@astrojs/check` |
| `sharp` | 0.35.4 | none | in the Starlight template; build script denied in Starlight's own workspace |
| `starlight-blog` | 0.30.0 | `@astrojs/starlight >=0.42.0` | modified 2026-09-21 |
| `starlight-links-validator` | 0.26.0 | `@astrojs/starlight >=0.42.0`, `astro >=7.2.10` | modified 2026-09-02 |
| `rehype-mermaid` | 3.0.0 | `playwright 1` (optional) | modified 2026-01-28 |
| `mermaid-isomorphic` | 3.1.0 | `playwright 1` | modified 2026-02-19 |
| `remark-mermaidjs` | 7.0.0 | `playwright 1` | modified 2025-03-24; not recommended |
| `playwright` | 1.63.0 | none | modified 2026-09-26 |
| `mermaid` | 12.0.0 | none | engines `node >=22.12.0`; published 2026-09-10 |
| `@mermaid-js/mermaid-cli` | 12.0.0 | `puppeteer ^25.0.0` | engines `node >=22.13.0`; modified 2026-09-24 |
| `astro-mermaid` | 2.1.0 | `astro >=4`, `mermaid ^10.0.0 || ^11.0.0`, `@mermaid-js/layout-elk ^0.2.0` | modified 2026-06-24; no Mermaid 12 support |
| `@biomejs/biome` | 2.5.14 | none | modified 2026-09-16 |
| `pnpm` | 12.6.0 (`latest` dist-tag); 12.7.0 published | none | engines `node >=18.*`; 12.6.0 published 2026-09-22, 12.7.0 on 2026-09-25 |

## Clones read

| Repository | Path | HEAD SHA | Commit date | Tag or version at HEAD | Clone shape |
| --- | --- | --- | --- | --- | --- |
| `withastro/starlight` | `~/Code/github.com/withastro/starlight` | `3ec633b8c50d3e1a6d67cae7dc4c50f80101ea41` | 2026-09-24 | `@astrojs/starlight@0.42.4` | full; pre-existing, as recorded in `experiments/00-system-assessment/dependency-clones.md` |
| `withastro/astro` | `~/Code/github.com/withastro/astro` | `7a698ca6e70d778343786cbf8fedd5f49d169ea4` | 2026-09-12 | after `astro@7.3.2` (CHANGELOG head is 7.3.2) | full; pre-existing; `git fetch` run, `origin/main` unchanged |
| `withastro/docs` | `~/Code/github.com/withastro/docs` | `99dba9d030986f3febba953185b8c5c8b9049c89` | 2026-09-12 | none | full; pre-existing; `git fetch` run, `origin/main` unchanged |
| `HiDeoo/starlight-blog` | `~/Code/github.com/HiDeoo/starlight-blog` | `19e78329c0bcff80354d09fdf5ab5a1953aeb3fb` | 2026-09-21 | `starlight-blog@0.30.0` | `--filter=blob:none`, cloned 2026-09-26 |
| `HiDeoo/starlight-links-validator` | `~/Code/github.com/HiDeoo/starlight-links-validator` | `b725855d95f02048ec60220021c650934a269ba5` | 2026-09-15 | `starlight-links-validator@0.26.0` plus one commit | `--filter=blob:none`, cloned 2026-09-26 |
| `remcohaszing/rehype-mermaid` | `~/Code/github.com/remcohaszing/rehype-mermaid` | `cab7b87c9da3d397677d3887cbd90c18620d9ea5` | 2026-04-27 | `v3.0.0` plus 13 commits | `--filter=blob:none`, cloned 2026-09-26 |
| `mermaid-js/mermaid` | `~/Code/github.com/mermaid-js/mermaid` | `69778e6e995cd72c6cb524449d8e08ee3d231628` | 2026-09-21 | `packages/mermaid/package.json` version 12.0.0 | `--filter=blob:none --sparse`, no-cone patterns `packages/mermaid/package.json`, `packages/mermaid/CHANGELOG.md`, `packages/mermaid/src/docs/config/`, `README.md`; cloned 2026-09-26 |
| `pnpm/pnpm.io` | `~/Code/github.com/pnpm/pnpm.io` | `e7dc3d418a4c141b491dd08cf7e6489d43e277cc` | 2026-09-26 | none | `--filter=blob:none --sparse`, cone `docs/`; cloned 2026-09-26 |
| `biomejs/biome` | `~/Code/github.com/biomejs/biome` | `088164f398f5edcf4c1c763514d4916d46c37119` | 2026-09-26 | `@biomejs/biome@2.5.14` plus 75 commits | full; pre-existing (dependency-clones.md) |
| `jdx/mise` | `~/Code/github.com/jdx/mise` | `fdfa0efe7f94d9a7c06b477666cc82929959b2a7` | 2026-09-26 | `v2026.9.14` | full; pre-existing (dependency-clones.md) |

## Documents read, by clone

- `withastro/starlight`: `docs/src/content/docs/getting-started.mdx`, `manual-setup.mdx`, `guides/sidebar.mdx`, `guides/project-structure.mdx`, `reference/configuration.mdx`, `reference/frontmatter.md`, `resources/plugins.mdx` (Mermaid and blog entries), `packages/starlight/CHANGELOG.md` (0.40.0 to 0.42.4), `packages/starlight/package.json`, `packages/starlight/src/index.ts`, `src/integrations/markdown-plugins.ts`, `src/integrations/satteri.ts`, `src/integrations/remark-rehype.ts`, `src/integrations/expressive-code/index.ts`, `src/style/props.css`, `src/style/util.css`, `examples/basics/*`, `docs/astro.config.mjs`, `pnpm-workspace.yaml`, `package.json`.
- `withastro/astro`: `packages/astro/CHANGELOG.md` (7.3.2 head; entries for PRs #16966, #16462, #16877, #17010).
- `withastro/docs`: `src/content/docs/en/guides/markdown-content.mdx`, `guides/content-collections.mdx`, `guides/typescript.mdx`, `guides/upgrade-to/v6.mdx`, `guides/upgrade-to/v7.mdx`, `reference/cli-reference.mdx`, `reference/configuration-reference.mdx` (`outDir`).
- `HiDeoo/starlight-blog`: `README.md`, `packages/starlight-blog/package.json`, `packages/starlight-blog/CHANGELOG.md` (0.26.1 to 0.30.0), `packages/starlight-blog/libs/content.ts`, `docs/src/content/docs/getting-started.mdx`, `configuration.md`, `guides/frontmatter.md`, `guides/authors.md`, `guides/multiple-instances.mdx`, `docs/astro.config.ts`, `pnpm-workspace.yaml`, `package.json`.
- `HiDeoo/starlight-links-validator`: `packages/starlight-links-validator/package.json`, `docs/src/content/docs/getting-started.mdx`, `configuration.md` (headings).
- `remcohaszing/rehype-mermaid`: `README.md`, `package.json`, `src/rehype-mermaid.ts` (the `<picture>` rendering).
- `mermaid-js/mermaid`: `packages/mermaid/package.json`, `packages/mermaid/CHANGELOG.md` (12.0.0), `packages/mermaid/src/docs/config/usage.md`.
- `pnpm/pnpm.io`: `docs/installation.md`, `docs/workspaces.md`, `docs/continuous-integration.md`, `docs/cli/install.md`, `docs/package_json.md`, `docs/settings/build.md`.
- `biomejs/biome`: `packages/@biomejs/biome/configuration_schema.json`, `CHANGELOG.md` (PR #7359 and Astro entries), `crates/biome_service/src/file_handlers/astro.rs`, `crates/biome_service/src/file_handlers/mod.rs`.
- `jdx/mise`: `registry/pnpm.toml`, `registry/biome.toml`, `docs/lang/node.md`, `docs/dev-tools/backends/npm.md`.

## GitHub reads through `gh query`

- `withastro/starlight` discussion 1259 (comments 8038967, 8515492, 9300105, 9309061) and issue 1682: the Mermaid integration recipes.
- `joesaby/astro-mermaid` issues 74 and 75, releases (v2.1.0 on 2026-06-24), and `package.json` on `main` (version 1.4.0 in the repository, 2.1.0 on npm).
- `pnpm/pnpm` releases: v12.7.0 and v11.28.0 on 2026-09-25.
