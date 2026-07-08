/**
 * Reusable niche landing page framework.
 * Valid slugs and mapping to message keys. SEO-friendly static params.
 * Construction trades are listed first — primary marketing vertical.
 */

export const CONSTRUCTION_NICHE_SLUGS = [
  "construction-materials",
  "electrical-distribution",
  "plumbing-supply",
] as const;

export type ConstructionNicheSlug = (typeof CONSTRUCTION_NICHE_SLUGS)[number];

export const NICHE_SLUGS = [
  ...CONSTRUCTION_NICHE_SLUGS,
  "coffee-roasters",
  "pharmacy-medical",
  "cosmetics",
  "chocolate",
  "lab-sample-delivery",
  "ecommerce",
] as const;

export type NicheSlug = (typeof NICHE_SLUGS)[number];

/** Message key per slug for nicheLanding.* in messages */
export const NICHE_MESSAGE_KEYS: Record<NicheSlug, string> = {
  "construction-materials": "constructionMaterials",
  "electrical-distribution": "electricalDistribution",
  "plumbing-supply": "plumbingSupply",
  "coffee-roasters": "coffeeRoasters",
  "pharmacy-medical": "pharmacyMedical",
  cosmetics: "cosmetics",
  chocolate: "chocolate",
  "lab-sample-delivery": "labSampleDelivery",
  ecommerce: "ecommerce",
};

export function getNicheMessageKey(slug: string): string | null {
  if (NICHE_SLUGS.includes(slug as NicheSlug)) {
    return NICHE_MESSAGE_KEYS[slug as NicheSlug];
  }
  return null;
}

export function isValidNicheSlug(slug: string): slug is NicheSlug {
  return NICHE_SLUGS.includes(slug as NicheSlug);
}
