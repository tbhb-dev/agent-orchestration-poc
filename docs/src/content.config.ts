import { defineCollection } from "astro:content";
import { docsLoader } from "@astrojs/starlight/loaders";
import { docsSchema } from "@astrojs/starlight/schema";
import { z } from "astro/zod";
import { blogSchema } from "starlight-blog/schema";

export const collections = {
  docs: defineCollection({
    loader: docsLoader(),
    schema: docsSchema({
      // Devlog entries carry the plan's `phase` field alongside the starlight-blog fields.
      extend: (context) =>
        blogSchema(context).extend({ phase: z.number().int().optional() }),
    }),
  }),
};
