export const BLOG_CATEGORIES = [
  "logistics",
  "technology",
  "business",
  "route-optimization",
  "supply-chain",
  "same-day-delivery",
  "wholesale",
  "construction",
  "medical",
  "retail",
  "coffee",
] as const;

export type BlogCategory = (typeof BLOG_CATEGORIES)[number];

export function isBlogCategory(value: string): value is BlogCategory {
  return (BLOG_CATEGORIES as readonly string[]).includes(value);
}
