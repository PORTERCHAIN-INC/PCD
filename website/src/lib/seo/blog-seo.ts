/**
 * Map blog post category/tags → industry niche slugs for internal linking.
 * Keep in sync with seo-content/industries.ts KEYWORDS niches.
 */
import type { Locale } from "@/i18n/routing";
import type { BlogCategory } from "@/data/blog-categories";
import { buildInternalLinksForArticle } from "./internal-linking";
import { business, cityIndustrySeo, industrySlug } from "./routes";

type PostSeoInput = {
  category: BlogCategory;
  tags?: string[];
};

const CONSTRUCTION_SLUGS = [
  "construction-materials",
  "electrical-distribution",
  "plumbing-supply",
] as const;

function tagHas(tags: string[], ...needles: string[]): boolean {
  return tags.some((t) => needles.some((n) => t.toLowerCase().includes(n)));
}

/** Map blog post category/tags to industry slugs for internal linking. */
export function getIndustrySlugsForPost(post: PostSeoInput): string[] {
  const tags = post.tags ?? [];

  if (
    tagHas(tags, "electrical") ||
    (post.category === "construction" && tagHas(tags, "electrical"))
  ) {
    return ["electrical-distribution", "construction-materials"];
  }
  if (tagHas(tags, "plumbing", "pipe", "fixture")) {
    return ["plumbing-supply", "construction-materials"];
  }
  if (
    post.category === "construction" ||
    tagHas(tags, "construction", "jobsite", "lumber", "drywall")
  ) {
    return [...CONSTRUCTION_SLUGS];
  }
  if (post.category === "coffee" || tagHas(tags, "coffee", "roaster", "café", "cafe")) {
    return ["coffee-roasters"];
  }
  if (
    post.category === "medical" ||
    tagHas(tags, "medical", "pharmacy", "clinic", "lab", "specimen")
  ) {
    return ["pharmacy-medical", "lab-sample-delivery"];
  }
  if (post.category === "retail" || tagHas(tags, "retail", "replenishment", "store")) {
    return ["retail-replenishment", "ecommerce"];
  }
  if (tagHas(tags, "cosmetic", "beauty", "salon")) {
    return ["cosmetics"];
  }
  if (tagHas(tags, "chocolate", "confection", "candy")) {
    return ["chocolate"];
  }
  if (tagHas(tags, "ecommerce", "e-commerce", "d2c", "parcel", "last-mile", "last mile")) {
    return ["ecommerce"];
  }
  if (tagHas(tags, "hvac", "mechanical", "furnace")) {
    return ["hvac-mechanical"];
  }
  if (tagHas(tags, "auto", "automotive", "parts")) {
    return ["automotive-parts"];
  }
  if (tagHas(tags, "manufactur", "plant", "industrial")) {
    return ["manufacturing"];
  }
  if (tagHas(tags, "food", "cold-chain", "grocery")) {
    return ["food-distribution"];
  }
  if (post.category === "wholesale" || tagHas(tags, "wholesale", "distributor")) {
    return ["construction-materials", "electrical-distribution", "plumbing-supply"];
  }
  if (
    post.category === "same-day-delivery" ||
    post.category === "logistics" ||
    post.category === "supply-chain"
  ) {
    return ["ecommerce", "construction-materials"];
  }
  if (
    post.category === "route-optimization" ||
    post.category === "technology" ||
    post.category === "business"
  ) {
    return ["ecommerce", "construction-materials", "coffee-roasters"];
  }

  return ["construction-materials", "electrical-distribution", "coffee-roasters"];
}

export function buildBlogInternalLinks(locale: Locale, post: PostSeoInput) {
  const industrySlugs = getIndustrySlugsForPost(post);
  const links = buildInternalLinksForArticle(locale, {
    industrySlugs,
    maxLinks: 8,
  });

  if (post.category === "construction" || industrySlugs.includes("construction-materials")) {
    links.unshift({
      href: cityIndustrySeo(locale, "toronto", "construction-materials-delivery"),
      label: "Construction materials delivery Toronto",
    });
  }

  links.push({
    href: business(locale, { from: "blog" }),
    label: "Business delivery",
  });

  return links.slice(0, 10);
}

export function getFeaturedIndustrySlug(post: PostSeoInput): string | null {
  const slugs = getIndustrySlugsForPost(post);
  return slugs[0] ?? null;
}

export { industrySlug };
