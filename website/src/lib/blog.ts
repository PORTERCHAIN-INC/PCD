import "server-only";

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

/** Matches API MAX_LIST_LIMIT. A full page means the oldest rows were cut. */
export const BLOG_LIST_LIMIT = 500;

/** Image build has no Caddy and must not call the public site. Runtime fetches do. */
function catalogSkippedDuringImageBuild(): boolean {
  return process.env.NEXT_PHASE === "phase-production-build";
}

const MEDIA_SRC = /\]\((\/v1\/public\/blog\/media\/[a-zA-Z0-9._-]+)\)/g;

/** Prefer CDN when set; else API origin (local disk via public media route). */
export function getBlogMediaBase(): string {
  const cdn = process.env.NEXT_PUBLIC_BLOG_MEDIA_CDN?.trim().replace(/\/$/, "");
  if (cdn) return cdn;
  return getPorterchainApiBase();
}

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
  reading_minutes?: number;
  body_md?: string;
};

function readingMinutesFor(content: string, fromApi?: number): number {
  if (typeof fromApi === "number" && fromApi >= 1) return Math.floor(fromApi);
  return Math.max(1, Math.ceil(readingTime(content).minutes));
}

function rewriteBodyMedia(body: string): string {
  const base = getBlogMediaBase();
  return body.replace(MEDIA_SRC, (_match, path: string) => `](${base}${path})`);
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
    readingMinutes: readingMinutesFor(body, row.reading_minutes),
  };
}

function apiRowToPost(row: ApiBlogRow): BlogPost {
  const meta = apiRowToMeta(row);
  return { ...meta, content: rewriteBodyMedia(row.body_md ?? "") };
}

async function fetchApiPosts(
  locale: Locale,
  opts: {
    category?: BlogCategory;
    search?: string;
    featured?: boolean;
    trending?: boolean;
    caseStudy?: boolean;
    limit?: number;
    offset?: number;
  } = {}
): Promise<BlogPostMeta[]> {
  if (catalogSkippedDuringImageBuild()) return [];
  const base = getPorterchainApiBase();
  const params = new URLSearchParams({
    locale,
    limit: String(opts.limit ?? BLOG_LIST_LIMIT),
  });
  if (opts.offset && opts.offset > 0) params.set("offset", String(opts.offset));
  if (opts.category) params.set("category", opts.category);
  if (opts.search?.trim()) params.set("search", opts.search.trim());
  if (opts.featured != null) params.set("featured", String(opts.featured));
  if (opts.trending != null) params.set("trending", String(opts.trending));
  if (opts.caseStudy != null) params.set("case_study", String(opts.caseStudy));
  const res = await fetch(`${base}/v1/public/blog/posts?${params}`, {
    next: { revalidate: 3600, tags: ["blog", `blog:${locale}`] },
  });
  if (!res.ok) {
    throw new Error(`blog_catalog_unavailable:${res.status}`);
  }
  const rows = (await res.json()) as ApiBlogRow[];
  const limit = opts.limit ?? BLOG_LIST_LIMIT;
  if (rows.length === limit && limit >= BLOG_LIST_LIMIT) {
    throw new Error("blog_catalog_truncated");
  }
  return rows.map(apiRowToMeta);
}

async function fetchApiPost(locale: Locale, slug: string): Promise<BlogPost | null> {
  if (catalogSkippedDuringImageBuild()) return null;
  const base = getPorterchainApiBase();
  const res = await fetch(`${base}/v1/public/blog/posts/${slug}?locale=${locale}`, {
    next: { revalidate: 3600, tags: ["blog", `blog:${locale}`] },
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`blog_catalog_unavailable:${res.status}`);
  }
  const row = (await res.json()) as ApiBlogRow;
  return apiRowToPost(row);
}

export async function getAllPostSlugs(locale: Locale): Promise<string[]> {
  const posts = await getAllPosts(locale);
  return posts.map((p) => p.slug);
}

export async function getAllPosts(locale: Locale): Promise<BlogPostMeta[]> {
  return fetchApiPosts(locale);
}

export async function getPost(locale: Locale, slug: string): Promise<BlogPost | null> {
  return fetchApiPost(locale, slug);
}

export async function getCaseStudyPosts(locale: Locale): Promise<BlogPostMeta[]> {
  return fetchApiPosts(locale, { caseStudy: true, limit: 100 });
}

export async function getFeaturedPost(locale: Locale): Promise<BlogPostMeta | null> {
  const featured = await fetchApiPosts(locale, { featured: true, limit: 1 });
  if (featured[0]) return featured[0];
  const posts = await getAllPosts(locale);
  return posts[0] ?? null;
}

export async function getTrendingPosts(locale: Locale, limit = 5): Promise<BlogPostMeta[]> {
  const trending = await fetchApiPosts(locale, { trending: true, limit });
  if (trending.length >= limit) return trending.slice(0, limit);
  const posts = await getAllPosts(locale);
  return [...trending, ...posts.filter((p) => !p.trending)].slice(0, limit);
}

export async function getPostsByCategory(
  locale: Locale,
  category: BlogCategory
): Promise<BlogPostMeta[]> {
  return fetchApiPosts(locale, { category, limit: BLOG_LIST_LIMIT });
}

export async function getRelatedPosts(
  locale: Locale,
  post: BlogPostMeta,
  limit = 3
): Promise<BlogPostMeta[]> {
  const sameCategory = await fetchApiPosts(locale, {
    category: post.category,
    limit: limit + 5,
  });
  return sameCategory
    .filter((p) => p.slug !== post.slug)
    .sort((a, b) => {
      const aScore = (a.category === post.category ? 2 : 0) + (a.trending ? 1 : 0);
      const bScore = (b.category === post.category ? 2 : 0) + (b.trending ? 1 : 0);
      return bScore - aScore || new Date(b.date).getTime() - new Date(a.date).getTime();
    })
    .slice(0, limit);
}

export async function searchPosts(locale: Locale, query: string): Promise<BlogPostMeta[]> {
  const q = query.trim();
  if (!q) return getAllPosts(locale);
  return fetchApiPosts(locale, { search: q, limit: BLOG_LIST_LIMIT });
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
