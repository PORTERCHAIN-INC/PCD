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

/** Map blog post category/tags to industry slugs for internal linking. */
export function getIndustrySlugsForPost(post: PostSeoInput): string[] {
  const tags = post.tags ?? [];

  if (
    tags.includes("electrical") ||
    (post.category === "construction" && tags.includes("electrical"))
  ) {
    return ["electrical-distribution", "construction-materials"];
  }
  if (tags.includes("plumbing")) {
    return ["plumbing-supply", "construction-materials"];
  }
  if (post.category === "construction" || tags.some((t) => t.includes("construction"))) {
    return [...CONSTRUCTION_SLUGS];
  }
  if (post.category === "coffee" || tags.includes("coffee")) {
    return ["coffee-roasters"];
  }
  if (post.category === "medical" || tags.includes("medical")) {
    return ["pharmacy-medical"];
  }
  if (post.category === "wholesale") {
    return ["construction-materials", "electrical-distribution", "plumbing-supply"];
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
