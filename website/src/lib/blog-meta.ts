/**
 * Client-safe blog types and helpers (no Node fs / gray-matter).
 * Server loaders live in `@/lib/blog`.
 */
import type { BlogCategory } from "@/data/blog-categories";
import type { SiteImageRef } from "@/data/site-images";
import { getBlogCoverImage } from "@/data/site-images";
import { getPorterchainApiBase } from "@/lib/api-base";

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
  coverImageUrl?: string;
  readingMinutes: number;
}

export interface BlogPost extends BlogPostMeta {
  content: string;
}

function blogMediaOrigin(): string {
  const cdn = process.env.NEXT_PUBLIC_BLOG_MEDIA_CDN?.trim().replace(/\/$/, "");
  if (cdn) return cdn;
  return getPorterchainApiBase();
}

/** Cover for cards/hero — CMS upload when set, else category stock image. */
export function resolveBlogCover(
  post: Pick<BlogPostMeta, "title" | "category" | "coverImageUrl">
): SiteImageRef {
  if (post.coverImageUrl) {
    const url = post.coverImageUrl;
    const src =
      url.startsWith("http://") || url.startsWith("https://")
        ? url
        : `${blogMediaOrigin()}${url.startsWith("/") ? url : `/${url}`}`;
    return { src, alt: post.title, width: 1200, height: 630 };
  }
  return getBlogCoverImage(post.category);
}
