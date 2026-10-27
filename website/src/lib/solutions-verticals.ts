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
