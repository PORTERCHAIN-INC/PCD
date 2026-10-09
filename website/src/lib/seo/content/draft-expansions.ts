/**
 * Gated content expansion — draft niches and service areas stay noindex until copy + ops verified.
 * See docs/DEFERRED_AND_OWNER_INPUT_REQUIRED.md.
 */

export const DRAFT_NICHE_SLUGS = [
  "hvac-mechanical",
  "automotive-parts",
  "manufacturing",
  "retail-replenishment",
  "food-distribution",
] as const;

export type DraftNicheSlug = (typeof DRAFT_NICHE_SLUGS)[number];

export const DRAFT_NICHE_MESSAGE_KEYS: Record<DraftNicheSlug, string> = {
  "hvac-mechanical": "hvacMechanical",
  "automotive-parts": "automotiveParts",
  manufacturing: "manufacturing",
  "retail-replenishment": "retailReplenishment",
  "food-distribution": "foodDistribution",
};

/** GTA boroughs / cities with local copy pending — not in CORE_SERVICE_AREA_SLUGS. */
export const DRAFT_SERVICE_AREA_SLUGS = [
  "richmond-hill",
  "scarborough",
  "etobicoke",
  "north-york",
  "milton",
  "whitby",
] as const;

export type DraftServiceAreaSlug = (typeof DRAFT_SERVICE_AREA_SLUGS)[number];

export const DRAFT_SERVICE_AREA_MESSAGE_KEYS: Record<DraftServiceAreaSlug, string> = {
  "richmond-hill": "richmondHill",
  scarborough: "scarborough",
  etobicoke: "etobicoke",
  "north-york": "northYork",
  milton: "milton",
  whitby: "whitby",
};

export function isDraftNicheSlug(slug: string): slug is DraftNicheSlug {
  return (DRAFT_NICHE_SLUGS as readonly string[]).includes(slug);
}
