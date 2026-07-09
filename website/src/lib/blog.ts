import fs from "fs";
import path from "path";
import matter from "gray-matter";
import readingTime from "reading-time";
import { getAuthor } from "@/data/blog-authors";
import { BLOG_CATEGORIES, isBlogCategory, type BlogCategory } from "@/data/blog-categories";
import type { Locale } from "@/i18n/routing";

export const POSTS_PER_PAGE = 9;

export interface BlogPostMeta {
  slug: string;
  title: string;
  description: string;
  date: string;
  category: BlogCategory;
  authorId: string;
  featured?: boolean;
  trending?: boolean;
  caseStudy?: boolean;
  onTimePercent?: string;
  costDeltaPercent?: string;
  volumeMetric?: string;
  tags?: string[];
  readingMinutes: number;
}

export interface BlogPost extends BlogPostMeta {
  content: string;
}

function blogDir(locale: Locale): string {
  return path.join(process.cwd(), "content/blog", locale);
}

function parsePost(slug: string, raw: string): BlogPost {
  const { data, content } = matter(raw);
  const category = isBlogCategory(data.category) ? data.category : "logistics";
  const stats = readingTime(content);

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
    readingMinutes: Math.max(1, Math.ceil(stats.minutes)),
    content,
  };
}

export function getAllPostSlugs(locale: Locale): string[] {
  const dir = blogDir(locale);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .map((f) => f.replace(/\.md$/, ""));
}

export function getAllPosts(locale: Locale): BlogPostMeta[] {
  return getAllPostSlugs(locale)
    .map((slug) => {
      const raw = fs.readFileSync(path.join(blogDir(locale), `${slug}.md`), "utf8");
      const post = parsePost(slug, raw);
      const { content: _, ...meta } = post;
      return meta;
    })
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}

export function getPost(locale: Locale, slug: string): BlogPost | null {
  const file = path.join(blogDir(locale), `${slug}.md`);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf8");
  return parsePost(slug, raw);
}

export function getCaseStudyPosts(locale: Locale): BlogPostMeta[] {
  return getAllPosts(locale).filter((p) => p.caseStudy);
}

export function getFeaturedPost(locale: Locale): BlogPostMeta | null {
  const posts = getAllPosts(locale);
  return posts.find((p) => p.featured) ?? posts[0] ?? null;
}

export function getTrendingPosts(locale: Locale, limit = 5): BlogPostMeta[] {
  const posts = getAllPosts(locale);
  const trending = posts.filter((p) => p.trending);
  if (trending.length >= limit) return trending.slice(0, limit);
  return [...trending, ...posts.filter((p) => !p.trending)].slice(0, limit);
}

export function getPostsByCategory(locale: Locale, category: BlogCategory): BlogPostMeta[] {
  return getAllPosts(locale).filter((p) => p.category === category);
}

export function getRelatedPosts(locale: Locale, post: BlogPostMeta, limit = 3): BlogPostMeta[] {
  return getAllPosts(locale)
    .filter((p) => p.slug !== post.slug)
    .sort((a, b) => {
      const aScore = (a.category === post.category ? 2 : 0) + (a.trending ? 1 : 0);
      const bScore = (b.category === post.category ? 2 : 0) + (b.trending ? 1 : 0);
      return bScore - aScore || new Date(b.date).getTime() - new Date(a.date).getTime();
    })
    .slice(0, limit);
}

export function searchPosts(locale: Locale, query: string): BlogPostMeta[] {
  const q = query.trim().toLowerCase();
  if (!q) return getAllPosts(locale);
  return getAllPosts(locale).filter(
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

export function getCategoryPostCounts(locale: Locale): Record<BlogCategory, number> {
  const counts = Object.fromEntries(BLOG_CATEGORIES.map((c) => [c, 0])) as Record<
    BlogCategory,
    number
  >;
  for (const post of getAllPosts(locale)) {
    counts[post.category]++;
  }
  return counts;
}

export function getAuthorForPost(authorId: string) {
  return getAuthor(authorId);
}
