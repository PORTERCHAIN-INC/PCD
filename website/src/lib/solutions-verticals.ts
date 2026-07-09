import type { NicheSlug } from "@/lib/seo/niche-landing";

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
