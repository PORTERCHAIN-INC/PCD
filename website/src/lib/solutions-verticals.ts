import type { NicheSlug } from "@/lib/seo/niche-landing";

export const CONSTRUCTION_INDUSTRY_SLUGS = [
  "construction-materials",
  "electrical-distribution",
  "plumbing-supply",
] as const;

export type ConstructionIndustrySlug = (typeof CONSTRUCTION_INDUSTRY_SLUGS)[number];

export const CONSTRUCTION_PROGRAM_KEYS = ["materials", "electrical", "plumbing"] as const;

export type ConstructionProgramKey = (typeof CONSTRUCTION_PROGRAM_KEYS)[number];

export const CONSTRUCTION_PROGRAM_TO_INDUSTRY: Record<
  ConstructionProgramKey,
  ConstructionIndustrySlug
> = {
  materials: "construction-materials",
  electrical: "electrical-distribution",
  plumbing: "plumbing-supply",
};

export const SOLUTION_VERTICAL_SLUGS = [
  "wholesale",
  "medical",
  "food-beverage",
  "construction",
] as const;

export type SolutionVerticalSlug = (typeof SOLUTION_VERTICAL_SLUGS)[number];

const VERTICAL_INDUSTRY: Record<SolutionVerticalSlug, NicheSlug> = {
  wholesale: "ecommerce",
  medical: "pharmacy-medical",
  "food-beverage": "coffee-roasters",
  construction: "construction-materials",
};

const VERTICAL_CARD_INDEX: Record<SolutionVerticalSlug, number> = {
  wholesale: 0,
  medical: 1,
  "food-beverage": 2,
  construction: 3,
};

export function isValidSolutionVertical(slug: string): slug is SolutionVerticalSlug {
  return SOLUTION_VERTICAL_SLUGS.includes(slug as SolutionVerticalSlug);
}

export function industrySlugForVertical(slug: SolutionVerticalSlug): NicheSlug {
  return VERTICAL_INDUSTRY[slug];
}

export function cardIndexForVertical(slug: SolutionVerticalSlug): number {
  return VERTICAL_CARD_INDEX[slug];
}

/** Public path for a solutions vertical (construction uses a short top-level URL). */
export function solutionVerticalPath(vertical: SolutionVerticalSlug): string {
  if (vertical === "construction") return "/construction";
  return `/solutions/${vertical}`;
}

/** Metadata / sitemap path segment without leading slash. */
export function solutionVerticalPathSegment(vertical: SolutionVerticalSlug): string {
  if (vertical === "construction") return "construction";
  return `solutions/${vertical}`;
}
