// @ts-check
import { unified } from "@astrojs/markdown-remark";
import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";
import rehypeMermaid from "rehype-mermaid";
import starlightBlog from "starlight-blog";
import starlightLinksValidator from "starlight-links-validator";

// starlight-links-validator invalidates the content-layer cache on every run, so it is enabled
// only for the CI build (mise run docs:check-links) and stays off for local development.
const checkLinks = process.env.CHECK_LINKS === "1";

export default defineConfig({
  markdown: {
    // Astro 7 defaults to Sätteri; rehype-mermaid is a unified plugin and needs this processor.
    processor: unified({
      rehypePlugins: [
        [
          rehypeMermaid,
          { strategy: "inline-svg", mermaidConfig: { theme: "neutral" } },
        ],
      ],
    }),
  },
  integrations: [
    starlight({
      title: "Agent orchestration PoC",
      plugins: [
        starlightBlog({
          title: "Devlog",
          prefix: "devlog",
          navigation: "none",
          authors: { codex: { name: "Codex" } },
        }),
        ...(checkLinks ? [starlightLinksValidator()] : []),
      ],
      sidebar: [
        {
          label: "Project",
          items: [{ autogenerate: { directory: "project" } }],
        },
        {
          label: "Workflow",
          items: [{ autogenerate: { directory: "workflow" } }],
        },
        {
          label: "Research",
          items: [{ autogenerate: { directory: "research" } }],
        },
        {
          label: "Experiments",
          items: [{ autogenerate: { directory: "experiments" } }],
        },
        { label: "Design", items: [{ autogenerate: { directory: "design" } }] },
        {
          label: "Decisions",
          items: [{ autogenerate: { directory: "decisions" } }],
        },
        { label: "Guides", items: [{ autogenerate: { directory: "guides" } }] },
        { label: "Retros", items: [{ autogenerate: { directory: "retros" } }] },
        { label: "Devlog", link: "/devlog/" },
      ],
    }),
  ],
});
