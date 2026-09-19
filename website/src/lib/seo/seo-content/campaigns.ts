/**
 * Campaign segment config for SEO content expansion.
 * Single source of truth for campaign slugs, message keys, and optional industry link.
 * Aligns with lib/campaign-landing.ts and messages.campaignLanding.*
 */

import type { CampaignSegmentConfig } from "./types";
import { CAMPAIGN_SLUGS, CAMPAIGN_MESSAGE_KEYS } from "../campaign-landing";
import type { CampaignSlug } from "../campaign-landing";

/** Display label and optional industry slug for campaigns that mirror an industry. */
const SEGMENT_META: Record<CampaignSlug, { label: string; industrySlug?: string }> = {
  "construction-materials": {
    label: "Construction materials",
    industrySlug: "construction-materials",
  },
  "electrical-distribution": {
    label: "Electrical distribution",
    industrySlug: "electrical-distribution",
  },
  "plumbing-supply": {
    label: "Plumbing supply",
    industrySlug: "plumbing-supply",
  },
  "recurring-delivery": { label: "Recurring delivery" },
  "coffee-roasters": {
    label: "Coffee roasters",
    industrySlug: "coffee-roasters",
  },
  "pharmacy-medical": {
    label: "Pharmacy & medical",
    industrySlug: "pharmacy-medical",
  },
  cosmetics: { label: "Cosmetics & beauty", industrySlug: "cosmetics" },
};

/** Campaign segment configs. Used for campaign pages and ad/landing generation. */
export const CAMPAIGN_SEGMENT_CONFIGS: CampaignSegmentConfig[] = CAMPAIGN_SLUGS.map((slug) => {
  const meta = SEGMENT_META[slug];
  return {
    id: `campaign-${slug}`,
    slug,
    messageKey: CAMPAIGN_MESSAGE_KEYS[slug],
    label: meta.label,
    industrySlug: meta.industrySlug,
    generationHints: {
      keywords:
        slug === "recurring-delivery"
          ? ["recurring", "last-mile", "merchants", "parcel"]
          : undefined,
    },
  };
});

export function getCampaignSegmentConfig(slug: string): CampaignSegmentConfig | null {
  const found = CAMPAIGN_SEGMENT_CONFIGS.find((c) => c.slug === slug);
  return found ?? null;
}

export function getCampaignSegmentConfigByMessageKey(
  messageKey: string
): CampaignSegmentConfig | null {
  const found = CAMPAIGN_SEGMENT_CONFIGS.find((c) => c.messageKey === messageKey);
  return found ?? null;
}
