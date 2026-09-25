import {
  BLOG_CATEGORIES,
  BLOG_LOCALES,
  BLOG_STATUSES,
  adminBlogPostSchema,
  type AdminBlogPost,
} from "@porterchain/types";
import { adminFetch } from "@/lib/api";

export { BLOG_CATEGORIES, BLOG_LOCALES, BLOG_STATUSES };
export type BlogPost = AdminBlogPost;
export type BlogPostInput = {
  slug: string;
  locale: string;
  title: string;
  description: string;
  body_md: string;
  category: string;
  author_id: string;
  status: string;
  featured: boolean;
  trending: boolean;
  case_study: boolean;
  on_time_percent?: string | null;
  cost_delta_percent?: string | null;
  volume_metric?: string | null;
  tags: string[];
  cover_image_url?: string | null;
  published_at?: string | null;
};

export type BlogFilters = {
  locale?: string;
  status?: string;
  category?: string;
  search?: string;
};

function qs(filters: BlogFilters): string {
  const params = new URLSearchParams();
  if (filters.locale) params.set("locale", filters.locale);
  if (filters.status) params.set("status", filters.status);
  if (filters.category) params.set("category", filters.category);
  if (filters.search) params.set("search", filters.search);
  params.set("limit", "500");
  return `?${params.toString()}`;
}

export const blogApi = {
  async list(token: string, filters: BlogFilters = {}): Promise<BlogPost[]> {
    const rows = await adminFetch<unknown[]>(`/v1/admin/blog/posts${qs(filters)}`, token);
    return adminBlogPostSchema.array().parse(rows);
  },

  async detail(token: string, id: string): Promise<BlogPost> {
    const row = await adminFetch<unknown>(`/v1/admin/blog/posts/${id}`, token);
    return adminBlogPostSchema.parse(row);
  },

  async create(token: string, body: BlogPostInput): Promise<BlogPost> {
    const row = await adminFetch<unknown>("/v1/admin/blog/posts", token, {
      method: "POST",
      body: JSON.stringify(body),
    });
    return adminBlogPostSchema.parse(row);
  },

  async update(token: string, id: string, patch: Partial<BlogPostInput>): Promise<BlogPost> {
    const row = await adminFetch<unknown>(`/v1/admin/blog/posts/${id}`, token, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
    return adminBlogPostSchema.parse(row);
  },

  async remove(token: string, id: string): Promise<void> {
    await adminFetch<void>(`/v1/admin/blog/posts/${id}`, token, { method: "DELETE" });
  },

  async uploadMedia(token: string, file: File): Promise<{ url: string }> {
    const { isLocalDev } = await import("@/lib/env");
    const form = new FormData();
    form.append("file", file);
    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
      ...(isLocalDev() ? { "X-Admin-Role": "admin" } : {}),
    };
    const res = await fetch(`/api/porterchain/v1/admin/blog/media`, {
      method: "POST",
      credentials: "include",
      headers,
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const detail = (body as { detail?: string }).detail;
      throw new Error(typeof detail === "string" ? detail : `Upload failed (${res.status})`);
    }
    return res.json() as Promise<{ url: string }>;
  },
};

export const STATUS_TONES: Record<string, string> = {
  draft: "slate",
  published: "green",
  archived: "amber",
};

export function slugifyTitle(title: string): string {
  return title
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120);
}
