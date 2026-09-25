import "server-only";

import {
  publicBlogPostItemSchema,
  publicBlogPostMetaSchema,
  blogAuthorSchema,
  type BlogAuthor,
  type PublicBlogPostItem,
  type PublicBlogPostMeta,
  BLOG_AUTHORS,
  getBlogAuthor,
} from "@porterchain/types";
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

/** Matches API MAX_LIST_LIMIT — hard ceiling, not the default page size. */
export const BLOG_LIST_LIMIT = 500;

/** Matches API DEFAULT_LIST_LIMIT — preferred page size for catalog fetches. */
export const BLOG_PAGE_SIZE = 100;

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

function readingMinutesFor(content: string, fromApi?: number): number {
  if (typeof fromApi === "number" && fromApi >= 1) return Math.floor(fromApi);
  return Math.max(1, Math.ceil(readingTime(content).minutes));
}

function rewriteBodyMedia(body: string): string {
  const base = getBlogMediaBase();
  return body.replace(MEDIA_SRC, (_match, path: string) => `](${base}${path})`);
}

function metaFromApi(row: PublicBlogPostMeta): BlogPostMeta {
  const category = isBlogCategory(row.category) ? row.category : "logistics";
  return {
    slug: row.slug,
    title: row.title,
    description: row.description,
    date: row.published_at ?? new Date().toISOString().slice(0, 10),
    category,
    authorId: row.author_id || "porterchain",
    featured: Boolean(row.featured),
    trending: Boolean(row.trending),
    caseStudy: Boolean(row.case_study),
    onTimePercent: row.on_time_percent ?? undefined,
    costDeltaPercent: row.cost_delta_percent ?? undefined,
    volumeMetric: row.volume_metric ?? undefined,
    tags: row.tags ?? [],
    coverImageUrl: row.cover_image_url ?? undefined,
    readingMinutes: readingMinutesFor("", row.reading_minutes),
  };
}

function postFromApi(row: PublicBlogPostItem): BlogPost {
  const meta = metaFromApi(row);
  const body = row.body_md ?? "";
  return {
    ...meta,
    readingMinutes: readingMinutesFor(body, row.reading_minutes),
    content: rewriteBodyMedia(body),
  };
}

type ListOpts = {
  category?: BlogCategory;
  search?: string;
  featured?: boolean;
  trending?: boolean;
  caseStudy?: boolean;
  limit?: number;
  offset?: number;
};

async function fetchApiPostsPage(locale: Locale, opts: ListOpts = {}): Promise<BlogPostMeta[]> {
  if (catalogSkippedDuringImageBuild()) return [];
  const base = getPorterchainApiBase();
  const limit = Math.min(opts.limit ?? BLOG_PAGE_SIZE, BLOG_LIST_LIMIT);
  const params = new URLSearchParams({
    locale,
    limit: String(limit),
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
  const raw: unknown = await res.json();
  const rows = publicBlogPostMetaSchema.array().parse(raw);
  return rows.map(metaFromApi);
}

/** Page through the public catalog until exhausted or the API ceiling. */
async function fetchAllApiPosts(
  locale: Locale,
  opts: Omit<ListOpts, "limit" | "offset"> = {}
): Promise<BlogPostMeta[]> {
  const all: BlogPostMeta[] = [];
  let offset = 0;
  while (offset < BLOG_LIST_LIMIT) {
    const page = await fetchApiPostsPage(locale, {
      ...opts,
      limit: BLOG_PAGE_SIZE,
      offset,
    });
    all.push(...page);
    if (page.length < BLOG_PAGE_SIZE) break;
    offset += BLOG_PAGE_SIZE;
  }
  if (all.length >= BLOG_LIST_LIMIT) {
    throw new Error("blog_catalog_truncated");
  }
  return all;
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
  const raw: unknown = await res.json();
  return postFromApi(publicBlogPostItemSchema.parse(raw));
}

/** Signed draft/archive preview — never cached; requires admin token query. */
export async function getPreviewPost(
  locale: Locale,
  slug: string,
  token: string
): Promise<BlogPost | null> {
  if (catalogSkippedDuringImageBuild()) return null;
  const base = getPorterchainApiBase();
  const params = new URLSearchParams({ locale, token });
  const res = await fetch(
    `${base}/v1/public/blog/posts/${encodeURIComponent(slug)}/preview?${params}`,
    {
      cache: "no-store",
    }
  );
  if (res.status === 401 || res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`blog_preview_unavailable:${res.status}`);
  }
  const raw: unknown = await res.json();
  return postFromApi(publicBlogPostItemSchema.parse(raw));
}

export async function getAllPostSlugs(locale: Locale): Promise<string[]> {
  const posts = await getAllPosts(locale);
  return posts.map((p) => p.slug);
}

export async function getAllPosts(locale: Locale): Promise<BlogPostMeta[]> {
  return fetchAllApiPosts(locale);
}

export async function getPost(locale: Locale, slug: string): Promise<BlogPost | null> {
  return fetchApiPost(locale, slug);
}

export async function getCaseStudyPosts(locale: Locale): Promise<BlogPostMeta[]> {
  return fetchApiPostsPage(locale, { caseStudy: true, limit: BLOG_PAGE_SIZE });
}

export async function getFeaturedPost(locale: Locale): Promise<BlogPostMeta | null> {
  const featured = await fetchApiPostsPage(locale, { featured: true, limit: 1 });
  if (featured[0]) return featured[0];
  const posts = await getAllPosts(locale);
  return posts[0] ?? null;
}

export async function getTrendingPosts(locale: Locale, limit = 5): Promise<BlogPostMeta[]> {
  const trending = await fetchApiPostsPage(locale, { trending: true, limit });
  if (trending.length >= limit) return trending.slice(0, limit);
  const posts = await getAllPosts(locale);
  return [...trending, ...posts.filter((p) => !p.trending)].slice(0, limit);
}

export async function getPostsByCategory(
  locale: Locale,
  category: BlogCategory
): Promise<BlogPostMeta[]> {
  return fetchAllApiPosts(locale, { category });
}

export async function getRelatedPosts(
  locale: Locale,
  post: BlogPostMeta,
  limit = 3
): Promise<BlogPostMeta[]> {
  const sameCategory = await fetchApiPostsPage(locale, {
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
  return fetchAllApiPosts(locale, { search: q });
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

/** CMS authors with static fallback for image build / API down. */
export async function listBlogAuthors(): Promise<BlogAuthor[]> {
  if (catalogSkippedDuringImageBuild()) {
    return Object.values(BLOG_AUTHORS);
  }
  try {
    const res = await fetch(`${getPorterchainApiBase()}/v1/public/blog/authors`, {
      next: { revalidate: 300, tags: ["blog-authors"] },
    });
    if (!res.ok) return Object.values(BLOG_AUTHORS);
    const rows = blogAuthorSchema.array().parse(await res.json());
    return rows.length > 0
      ? rows.map((r) => ({ id: r.id, name: r.name, role: r.role, bio: r.bio }))
      : Object.values(BLOG_AUTHORS);
  } catch {
    return Object.values(BLOG_AUTHORS);
  }
}

export async function getBlogAuthorRemote(id: string): Promise<BlogAuthor> {
  if (catalogSkippedDuringImageBuild()) {
    return getBlogAuthor(id);
  }
  try {
    const res = await fetch(
      `${getPorterchainApiBase()}/v1/public/blog/authors/${encodeURIComponent(id)}`,
      { next: { revalidate: 300, tags: ["blog-authors"] } }
    );
    if (!res.ok) return getBlogAuthor(id);
    const row = blogAuthorSchema.parse(await res.json());
    return { id: row.id, name: row.name, role: row.role, bio: row.bio };
  } catch {
    return getBlogAuthor(id);
  }
}
