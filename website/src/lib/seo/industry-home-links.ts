/**
 * Maps homepage industry card IDs to SEO industry slugs where a dedicated landing exists.
 */
export const HOME_INDUSTRY_TO_NICHE_SLUG: Record<string, string> = {
  construction: "construction-materials",
  electrical: "electrical-distribution",
  plumbing: "plumbing-supply",
  coffee: "coffee-roasters",
  medical: "pharmacy-medical",
  pharmacy: "pharmacy-medical",
  laboratories: "lab-sample-delivery",
  ecommerce: "ecommerce",
  retail: "ecommerce",
  wholesale: "construction-materials",
};

/** Campaign message key → niche slug for campaign landing industry links. */
export const CAMPAIGN_KEY_TO_NICHE_SLUG: Record<string, string> = {
  constructionMaterials: "construction-materials",
  electricalDistribution: "electrical-distribution",
  plumbingSupply: "plumbing-supply",
  coffeeRoasters: "coffee-roasters",
  pharmacyMedical: "pharmacy-medical",
  cosmetics: "cosmetics",
};
