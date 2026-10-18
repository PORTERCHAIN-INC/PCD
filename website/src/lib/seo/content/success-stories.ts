import type { PublishableContent } from "./publishable";

export type SuccessStoryMerchantType =
  | "construction-materials"
  | "electrical-distribution"
  | "plumbing-supply"
  | "coffee-roasters"
  | "pharmacy-medical"
  | "cosmetics";

export type SuccessStory = PublishableContent & {
  title: string;
  description: string;
  merchantType: SuccessStoryMerchantType;
  industrySlug: string;
  headline: string;
  challenge: string;
  solution: string;
  outcome: string;
  quote?: string;
  quoteAttribution?: string;
  outcomeMetric?: string;
  /** Ops author for E-E-A-T (blogAuthors id) */
  authorId?: string;
  /** Only show metric + Review schema when true (permissioned narrative) */
  permissioned?: boolean;
  /** Customer approval on file before naming or indexing */
  customerApproved?: boolean;
  /** Evidence notes for procurement / editorial review */
  evidenceNotes?: string;
};

/**
 * Oct 2026: the earlier stories had invented quotes and numbers and are removed. Add a story
 * only with the customer's written approval of the wording, name and figures.
 */
export const SUCCESS_STORIES: SuccessStory[] = [];

export function getSuccessStoryBySlug(slug: string): SuccessStory | null {
  return SUCCESS_STORIES.find((s) => s.slug === slug) ?? null;
}

/** Public hub + sitemap + SSG — permissioned, indexed, published only. */
export function isPublicSuccessStory(story: SuccessStory): boolean {
  return (
    story.status === "published" &&
    story.index === true &&
    story.permissioned === true &&
    story.customerApproved === true
  );
}

export function listPublicSuccessStories(): SuccessStory[] {
  return SUCCESS_STORIES.filter(isPublicSuccessStory);
}
