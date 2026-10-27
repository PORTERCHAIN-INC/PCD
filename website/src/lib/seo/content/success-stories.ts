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
