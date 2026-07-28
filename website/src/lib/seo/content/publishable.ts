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

export function isPublished(content: Pick<PublishableContent, "status" | "index">): boolean {
  return content.status === "published" && content.index;
}

export function parseContentDate(iso?: string): Date | undefined {
  if (!iso) return undefined;
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return undefined;
  return new Date(parsed);
}
