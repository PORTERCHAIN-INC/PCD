/**
 * Shared publishable content fields for website content models.
 * Wire `index` → buildProgrammaticPageMetadata and sitemap inclusion.
 */

export type ContentStatus = "draft" | "review" | "published";

export type PublishableContent = {
  slug: string;
  status: ContentStatus;
  index: boolean;
  authorId?: string;
  reviewerId?: string;
  publishedAt?: string;
  updatedAt?: string;
  schemaType?: string;
  sources?: string[];
  canonicalSlug?: string;
};
