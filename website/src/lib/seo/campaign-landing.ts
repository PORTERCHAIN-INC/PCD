/**
 * Campaign landing page framework for outbound sales, ads, and niche campaigns.
 * Construction campaigns listed first — primary marketing vertical.
 */

export const CONSTRUCTION_CAMPAIGN_SLUGS = [
  "construction-materials",
  "electrical-distribution",
  "plumbing-supply",
] as const;

export const CAMPAIGN_SLUGS = [
  ...CONSTRUCTION_CAMPAIGN_SLUGS,
  "recurring-delivery",
  "coffee-roasters",
  "pharmacy-medical",
  "cosmetics",
] as const;

export type CampaignSlug = (typeof CAMPAIGN_SLUGS)[number];

/** Message key per slug for campaignLanding.* in messages (camelCase). */
export const CAMPAIGN_MESSAGE_KEYS: Record<CampaignSlug, string> = {
  "construction-materials": "constructionMaterials",
  "electrical-distribution": "electricalDistribution",
  "plumbing-supply": "plumbingSupply",
  "recurring-delivery": "recurringDelivery",
  "coffee-roasters": "coffeeRoasters",
  "pharmacy-medical": "pharmacyMedical",
  cosmetics: "cosmetics",
};

export function getCampaignMessageKey(slug: string): string | null {
  if (CAMPAIGN_SLUGS.includes(slug as CampaignSlug)) {
    return CAMPAIGN_MESSAGE_KEYS[slug as CampaignSlug];
  }
  return null;
}

export function isValidCampaignSlug(slug: string): slug is CampaignSlug {
  return CAMPAIGN_SLUGS.includes(slug as CampaignSlug);
}
