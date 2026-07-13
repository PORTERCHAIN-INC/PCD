import "server-only";

import fs from "fs";
import path from "path";
import matter from "gray-matter";
import readingTime from "reading-time";
import { getAuthor } from "@/data/blog-authors";
import { BLOG_CATEGORIES, isBlogCategory, type BlogCategory } from "@/data/blog-categories";
import { getPorterchainApiBase } from "@/lib/api-base";
import type { Locale } from "@/i18n/routing";
import {
  POSTS_PER_PAGE,
  type BlogPost,
  type BlogPostMeta,
  resolveBlogCover,
} from "@/lib/blog-meta";

export type { BlogPost, BlogPostMeta };
export { POSTS_PER_PAGE, resolveBlogCover };

type ApiBlogRow = {
  slug: string;
  title: string;
  description: string;
  category: string;
  author_id: string;
  featured?: boolean;
  trending?: boolean;
  case_study?: boolean;
  on_time_percent?: string | null;
  cost_delta_percent?: string | null;
  volume_metric?: string | null;
  tags?: string[];
  cover_image_url?: string | null;
  published_at?: string | null;
  body_md?: string;
};

function blogDir(locale: Locale): string {
  return path.join(process.cwd(), "content/blog", locale);
}

function readingMinutesFor(content: string): number {
  return Math.max(1, Math.ceil(readingTime(content).minutes));
}

function parsePost(slug: string, raw: string): BlogPost {
  const { data, content } = matter(raw);
  const category = isBlogCategory(data.category) ? data.category : "logistics";

  return {
    slug,
    title: data.title ?? slug,
    description: data.description ?? "",
    date: data.date ?? new Date().toISOString().slice(0, 10),
    category,
    authorId: data.author ?? "porterchain",
    featured: Boolean(data.featured),
    trending: Boolean(data.trending),
    caseStudy: Boolean(data.caseStudy),
    onTimePercent: typeof data.onTimePercent === "string" ? data.onTimePercent : undefined,
    costDeltaPercent: typeof data.costDeltaPercent === "string" ? data.costDeltaPercent : undefined,
    volumeMetric: typeof data.volumeMetric === "string" ? data.volumeMetric : undefined,
    tags: Array.isArray(data.tags) ? data.tags : [],
    readingMinutes: readingMinutesFor(content),
    content,
    source: "file",
  };
}

function apiRowToMeta(row: ApiBlogRow): BlogPostMeta {
  const category = isBlogCategory(row.category) ? row.category : "logistics";
  const body = row.body_md ?? "";
  return {
    slug: row.slug,
    title: row.title,
    description: row.description,
    date: row.published_at ?? new Date().toISOString().slice(0, 10),
    category,
    authorId: row.author_id ?? "porterchain",
    featured: Boolean(row.featured),
    trending: Boolean(row.trending),
    caseStudy: Boolean(row.case_study),
    onTimePercent: row.on_time_percent ?? undefined,
    costDeltaPercent: row.cost_delta_percent ?? undefined,
    volumeMetric: row.volume_metric ?? undefined,
    tags: row.tags ?? [],
    coverImageUrl: row.cover_image_url ?? undefined,
    readingMinutes: readingMinutesFor(body),
    source: "api",
  };
}

function apiRowToPost(row: ApiBlogRow): BlogPost {
  const meta = apiRowToMeta(row);
  return { ...meta, content: row.body_md ?? "" };
}

async function fetchApiPosts(locale: Locale): Promise<BlogPostMeta[]> {
  try {
    const base = getPorterchainApiBase();
    const res = await fetch(`${base}/v1/public/blog/posts?locale=${locale}&limit=500`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return [];
    const rows = (await res.json()) as ApiBlogRow[];
    return rows.map(apiRowToMeta);
  } catch {
    return [];
  }
}

async function fetchApiPost(locale: Locale, slug: string): Promise<BlogPost | null> {
  try {
    const base = getPorterchainApiBase();
    const res = await fetch(`${base}/v1/public/blog/posts/${slug}?locale=${locale}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    const row = (await res.json()) as ApiBlogRow;
    return apiRowToPost(row);
  } catch {
    return null;
  }
}

function getFilePostSlugs(locale: Locale): string[] {
  const dir = blogDir(locale);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .map((f) => f.replace(/\.md$/, ""));
}

function getFilePostsMeta(locale: Locale): BlogPostMeta[] {
  return getFilePostSlugs(locale)
    .map((slug) => {
      const raw = fs.readFileSync(path.join(blogDir(locale), `${slug}.md`), "utf8");
      const post = parsePost(slug, raw);
      const { content: _, ...meta } = post;
      return meta;
    })
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}

function getFilePost(locale: Locale, slug: string): BlogPost | null {
  const file = path.join(blogDir(locale), `${slug}.md`);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf8");
  return parsePost(slug, raw);
}

async function mergePostsMeta(locale: Locale): Promise<BlogPostMeta[]> {
  const apiPosts = await fetchApiPosts(locale);
  const apiSlugs = new Set(apiPosts.map((p) => p.slug));
  const filePosts = getFilePostsMeta(locale).filter((p) => !apiSlugs.has(p.slug));
  return [...apiPosts, ...filePosts].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );
}

export async function getAllPostSlugs(locale: Locale): Promise<string[]> {
  const posts = await mergePostsMeta(locale);
  return posts.map((p) => p.slug);
}

/** @deprecated Use getAllPostSlugs — kept for sync sitemap fallback */
export function getAllPostSlugsSync(locale: Locale): string[] {
  return getFilePostSlugs(locale);
}

export async function getAllPosts(locale: Locale): Promise<BlogPostMeta[]> {
  return mergePostsMeta(locale);
}

export async function getPost(locale: Locale, slug: string): Promise<BlogPost | null> {
  const apiPost = await fetchApiPost(locale, slug);
  if (apiPost) return apiPost;
  return getFilePost(locale, slug);
}

export async function getCaseStudyPosts(locale: Locale): Promise<BlogPostMeta[]> {
  return (await getAllPosts(locale)).filter((p) => p.caseStudy);
}

export async function getFeaturedPost(locale: Locale): Promise<BlogPostMeta | null> {
  const posts = await getAllPosts(locale);
  return posts.find((p) => p.featured) ?? posts[0] ?? null;
}

export async function getTrendingPosts(locale: Locale, limit = 5): Promise<BlogPostMeta[]> {
  const posts = await getAllPosts(locale);
  const trending = posts.filter((p) => p.trending);
  if (trending.length >= limit) return trending.slice(0, limit);
  return [...trending, ...posts.filter((p) => !p.trending)].slice(0, limit);
}

export async function getPostsByCategory(
  locale: Locale,
  category: BlogCategory
): Promise<BlogPostMeta[]> {
  return (await getAllPosts(locale)).filter((p) => p.category === category);
}

export async function getRelatedPosts(
  locale: Locale,
  post: BlogPostMeta,
  limit = 3
): Promise<BlogPostMeta[]> {
  return (await getAllPosts(locale))
    .filter((p) => p.slug !== post.slug)
    .sort((a, b) => {
      const aScore = (a.category === post.category ? 2 : 0) + (a.trending ? 1 : 0);
      const bScore = (b.category === post.category ? 2 : 0) + (b.trending ? 1 : 0);
      return bScore - aScore || new Date(b.date).getTime() - new Date(a.date).getTime();
    })
    .slice(0, limit);
}

export async function searchPosts(locale: Locale, query: string): Promise<BlogPostMeta[]> {
  const q = query.trim().toLowerCase();
  const posts = await getAllPosts(locale);
  if (!q) return posts;
  return posts.filter(
    (p) =>
      p.title.toLowerCase().includes(q) ||
      p.description.toLowerCase().includes(q) ||
      p.tags?.some((t) => t.toLowerCase().includes(q)) ||
      p.category.includes(q)
  );
}

export function paginatePosts<T>(posts: T[], page: number, perPage = POSTS_PER_PAGE) {
  const totalPages = Math.max(1, Math.ceil(posts.length / perPage));
  const currentPage = Math.min(Math.max(1, page), totalPages);
  const start = (currentPage - 1) * perPage;
  return {
    items: posts.slice(start, start + perPage),
    currentPage,
    totalPages,
    total: posts.length,
  };
}

export async function getCategoryPostCounts(locale: Locale): Promise<Record<BlogCategory, number>> {
  const counts = Object.fromEntries(BLOG_CATEGORIES.map((c) => [c, 0])) as Record<
    BlogCategory,
    number
  >;
  for (const post of await getAllPosts(locale)) {
    counts[post.category]++;
  }
  return counts;
}

export function getAuthorForPost(authorId: string) {
  return getAuthor(authorId);
}
