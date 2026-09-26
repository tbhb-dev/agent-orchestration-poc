// Validate every fenced ```mermaid block in the Markdown files given as arguments.
// mermaid.parse() only needs a DOM for its text sanitizer, so jsdom stands in for a
// browser; mermaid-cli would pull in puppeteer and a Chromium download for the same check.
import { readFile } from "node:fs/promises";
import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body></body></html>");
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const { default: mermaid } = await import("mermaid");

const files = process.argv.slice(2);
const fence = /^(\s*)(`{3,}|~{3,})\s*mermaid\b[^\n]*\n([\s\S]*?)\n\1\2\s*$/gm;
let blocks = 0;
let failures = 0;

for (const file of files) {
  const text = await readFile(file, "utf8");
  for (const match of text.matchAll(fence)) {
    blocks += 1;
    const line = text.slice(0, match.index).split("\n").length;
    try {
      await mermaid.parse(match[3]);
    } catch (error) {
      failures += 1;
      const message = String(error.message ?? error).split("\n")[0];
      console.error(`${file}:${line}: invalid mermaid block: ${message}`);
    }
  }
}

console.log(
  `mermaid: ${blocks} block(s) in ${files.length} file(s), ${failures} invalid`,
);
process.exit(failures === 0 ? 0 : 1);
