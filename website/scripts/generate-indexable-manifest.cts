/**
 * Build-time manifest of every indexable, sitemap-listed path (except API-backed blog
 * articles). Middleware uses it to send gated/unknown programmatic URLs to their nearest
 * indexable parent in ONE 301 instead of serving soft-404 / noindex pages.
 *
 * Also bundles website/content/blog/{en,fr}/*.md into src/generated/blog-repo-posts.json:
 * repo posts are served when the CMS has no row for that slug (the production CMS was never
 * seeded after the markdown → CMS migration, so every historical post had become a soft 404).
 *
 * Run: pnpm --filter @porterchain/website seo:manifest   (also runs as `prebuild`).
 * Output: src/generated/{indexable-paths,blog-repo-posts}.json (committed; CI checks sync).
 */
/* eslint-disable @typescript-eslint/no-require-imports */
const Module = require("module");
const fs = require("fs");
const path = require("path");

const originalLoad = Module._load;
Module._load = function (request: string, ...rest: unknown[]) {
  // The sitemap builders are plain data code; stub the Next/React-server-only runtime bits.
  if (request === "server-only") return {};
  if (request === "next/cache") {
    return {
      cacheLife() {},
      cacheTag() {},
      unstable_cache: (fn: unknown) => fn,
      revalidateTag() {},
      revalidatePath() {},
    };
  }
  return originalLoad.call(this, request, ...rest);
};

type RepoPost = {
  locale: "en" | "fr";
  slug: string;
  title: string;
  description: string;
  date: string;
  category: string;
  authorId: string;
  featured: boolean;
  trending: boolean;
  caseStudy: boolean;
  tags: string[];
  content: string;
};

/** Same frontmatter subset as scripts/import_blog_markdown.py (keep in sync). */
function parseFrontmatter(raw: string): { data: Record<string, unknown>; body: string } {
  const match = raw.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (!match) return { data: {}, body: raw };
  const data: Record<string, unknown> = {};
  for (const line of match[1].split("\n")) {
    const idx = line.indexOf(":");
    if (idx < 0) continue;
    const key = line.slice(0, idx).trim();
    const value = line
      .slice(idx + 1)
      .trim()
      .replace(/^["']|["']$/g, "");
    if (value.startsWith("[") && value.endsWith("]")) {
      data[key] = value
        .slice(1, -1)
        .split(",")
        .map((v) => v.trim().replace(/^["']|["']$/g, ""))
        .filter(Boolean);
    } else if (value.toLowerCase() === "true" || value.toLowerCase() === "false") {
      data[key] = value.toLowerCase() === "true";
    } else {
      data[key] = value;
    }
  }
  return { data, body: raw.slice(match[0].length) };
}

function buildRepoBlogPosts(): RepoPost[] {
  const root = path.join(__dirname, "../content/blog");
  const posts: RepoPost[] = [];
  for (const locale of ["en", "fr"] as const) {
    const dir = path.join(root, locale);
    if (!fs.existsSync(dir)) continue;
    for (const file of fs.readdirSync(dir).sort()) {
      if (!file.endsWith(".md")) continue;
      const { data, body } = parseFrontmatter(fs.readFileSync(path.join(dir, file), "utf8"));
      posts.push({
        locale,
        slug: file.replace(/\.md$/, ""),
        title: String(data.title ?? file),
        description: String(data.description ?? ""),
        date: String(data.date ?? "2026-01-01"),
        category: String(data.category ?? "logistics"),
        authorId: String(data.author ?? "porterchain"),
        featured: data.featured === true,
        trending: data.trending === true,
        caseStudy: data.caseStudy === true,
        tags: Array.isArray(data.tags) ? (data.tags as string[]) : [],
        content: body.replace(/<!--[\s\S]*?-->/g, "").trim(),
      });
    }
  }
  return posts;
}

function writeOrCheck(out: string, body: string, label: string): boolean {
  if (process.argv.includes("--check")) {
    const current = fs.existsSync(out) ? fs.readFileSync(out, "utf8") : "";
    if (current !== body) {
      console.error(`${label} is stale — run \`pnpm --filter @porterchain/website seo:manifest\``);
      return false;
    }
    console.log(`${label} in sync`);
    return true;
  }
  fs.writeFileSync(out, body);
  console.log(`wrote ${label}`);
  return true;
}

async function main() {
  const entries = require("../src/lib/seo/sitemap-entries");
  const paths = new Set<string>();
  for (const id of entries.SITEMAP_PARTITION_IDS as string[]) {
    if (id === "article") continue; // blog posts are CMS-backed; validated at request time
    const rows = (await entries.buildSitemapPartition(id)) as Array<{ url: string }>;
    for (const row of rows) paths.add(new URL(row.url).pathname.replace(/\/+$/, "") || "/");
  }
  const sorted = [...paths].sort();
  const pathsBody = JSON.stringify(sorted, null, 0).replace(/","/g, '",\n"') + "\n";
  const posts = buildRepoBlogPosts();
  const postsBody = JSON.stringify(posts, null, 1) + "\n";
  const gen = path.join(__dirname, "../src/generated");
  const ok =
    writeOrCheck(
      path.join(gen, "indexable-paths.json"),
      pathsBody,
      `indexable-paths.json (${sorted.length})`
    ) &&
    writeOrCheck(
      path.join(gen, "blog-repo-posts.json"),
      postsBody,
      `blog-repo-posts.json (${posts.length})`
    );
  if (!ok) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
