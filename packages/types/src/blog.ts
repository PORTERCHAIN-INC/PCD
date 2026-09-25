/**
 * Shared blog CMS contract — categories/locales/statuses + public/admin shapes.
 * Python BlogService closed sets must stay in sync (scripts/verify_blog_cms.py).
 */
import { z } from "zod";

export const BLOG_STATUSES = ["draft", "published", "archived"] as const;
export const BLOG_LOCALES = ["en", "fr"] as const;
export const BLOG_CATEGORIES = [
  "logistics",
  "technology",
  "business",
  "route-optimization",
  "supply-chain",
  "same-day-delivery",
  "wholesale",
  "construction",
  "medical",
  "retail",
  "coffee",
] as const;

export type BlogStatus = (typeof BLOG_STATUSES)[number];
export type BlogLocale = (typeof BLOG_LOCALES)[number];
export type BlogCategory = (typeof BLOG_CATEGORIES)[number];

export const publicBlogPostMetaSchema = z.object({
  id: z.string(),
  slug: z.string(),
  locale: z.string(),
  title: z.string(),
  description: z.string(),
  category: z.string(),
  author_id: z.string(),
  status: z.string(),
  featured: z.boolean().default(false),
  trending: z.boolean().default(false),
  case_study: z.boolean().default(false),
  on_time_percent: z.string().nullable().optional(),
  cost_delta_percent: z.string().nullable().optional(),
  volume_metric: z.string().nullable().optional(),
  tags: z.array(z.string()).default([]),
  cover_image_url: z.string().nullable().optional(),
  published_at: z.string().nullable().optional(),
  reading_minutes: z.number().int().positive().default(1),
  created_at: z.string(),
  updated_at: z.string(),
});

export const publicBlogPostItemSchema = publicBlogPostMetaSchema.extend({
  body_md: z.string().default(""),
});

export const adminBlogPostSchema = publicBlogPostItemSchema.extend({
  created_by: z.string().nullable().optional(),
});

export type PublicBlogPostMeta = z.infer<typeof publicBlogPostMetaSchema>;
export type PublicBlogPostItem = z.infer<typeof publicBlogPostItemSchema>;
export type AdminBlogPost = z.infer<typeof adminBlogPostSchema>;

export function isBlogCategory(value: string): value is BlogCategory {
  return (BLOG_CATEGORIES as readonly string[]).includes(value);
}
