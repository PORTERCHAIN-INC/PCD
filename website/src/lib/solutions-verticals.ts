import type { NicheSlug } from "@/lib/seo/niche-landing";

export const CONSTRUCTION_INDUSTRY_SLUGS = [
  "construction-materials",
  "electrical-distribution",
  "plumbing-supply",
] as const;

export type ConstructionIndustrySlug = (typeof CONSTRUCTION_INDUSTRY_SLUGS)[number];

export const CONSTRUCTION_PROGRAM_KEYS = ["materials", "electrical", "plumbing"] as const;

export type ConstructionProgramKey = (typeof CONSTRUCTION_PROGRAM_KEYS)[number];

export const SOLUTION_VERTICAL_SLUGS = [
  "wholesale",
  "medical",
  "food-beverage",
  "construction",
  "3pl",
  "fleet-overflow",
] as const;

export type SolutionVerticalSlug = (typeof SOLUTION_VERTICAL_SLUGS)[number];

const VERTICAL_INDUSTRY: Record<SolutionVerticalSlug, NicheSlug> = {
  wholesale: "ecommerce",
  medical: "pharmacy-medical",
  "food-beverage": "coffee-roasters",
  construction: "construction-materials",
  "3pl": "ecommerce",
  "fleet-overflow": "construction-materials",
};

const VERTICAL_CARD_INDEX: Record<SolutionVerticalSlug, number> = {
  wholesale: 0,
  medical: 1,
  "food-beverage": 2,
  construction: 3,
  "3pl": 4,
  "fleet-overflow": 5,
};

export function isValidSolutionVertical(slug: string): slug is SolutionVerticalSlug {
  return SOLUTION_VERTICAL_SLUGS.includes(slug as SolutionVerticalSlug);
}

/**
 * Where each former /solutions vertical now lives (footer consolidation, Oct 2026: the
 * /solutions pages 301 to these /delivery industry hubs — see lib/seo/redirects.ts).
 */
const SOLUTION_VERTICAL_DESTINATION: Record<SolutionVerticalSlug, string> = {
  construction: "delivery/construction",
  wholesale: "delivery/warehouses",
  medical: "delivery/pharmacy",
  "food-beverage": "delivery",
  "3pl": "delivery/warehouses",
  "fleet-overflow": "business",
};

/** Public path for a former solutions vertical (its live /delivery or /business page). */
export function solutionVerticalPath(vertical: SolutionVerticalSlug): string {
  return `/${SOLUTION_VERTICAL_DESTINATION[vertical]}`;
}

/** Path segment without leading slash. */
export function solutionVerticalPathSegment(vertical: SolutionVerticalSlug): string {
  return SOLUTION_VERTICAL_DESTINATION[vertical];
}
