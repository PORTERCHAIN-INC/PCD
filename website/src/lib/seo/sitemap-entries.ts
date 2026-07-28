import type { MetadataRoute } from "next";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { siteConfig } from "./config";
import { localePath } from "./routes";
import { getNicheMessageKey, NICHE_SLUGS } from "./niche-landing";
import { getServiceAreaMessageKey, SERVICE_AREA_SLUGS, isCoreServiceArea } from "./service-areas";
import { CAMPAIGN_SLUGS } from "./campaign-landing";
import { FAQ_CLUSTERS } from "./content/faq-clusters";
import { AUTHORITY_PAGES } from "./content/authority-pages";
import { COMPARISON_PAGES } from "./content/comparison-pages";
import {
  ONBOARDING_EDUCATION_PAGES,
  getAllOnboardingEducationSlugs,
} from "./content/onboarding-education";
import {
  INTEGRATIONS_EDUCATION_PAGES,
  getAllIntegrationsEducationSlugs,
} from "./content/integrations-education";
import { SUCCESS_STORIES } from "./content/success-stories";
import { DEVELOPER_DOC_SLUGS } from "@/lib/developer-docs";
import { getAllCitySegmentPairs } from "./city-segment-seo";
import { isPublishableCitySegment } from "./city-segment-publication";
import { INDEXABLE_VEHICLE_SEGMENTS, shouldIndexVehicleRoute } from "./vehicle-publication";
import { getAllPostSlugs, getAllPostSlugsSync, getAllPosts } from "@/lib/blog";
import { SOLUTION_VERTICAL_SLUGS, solutionVerticalPathSegment } from "@/lib/solutions-verticals";
import { BLOG_CATEGORIES } from "@/data/blog-categories";
import { isPublishableNiche } from "./landing-content";
import { isDraftNicheSlug } from "./content/draft-expansions";
import { isPublishableServiceArea, type ServiceAreaMessageContent } from "./service-area-content";
import type { NicheLandingContent } from "@/components/seo/IndustryLandingView";
import frMessages from "../../../messages/fr.json";
import frProgrammatic from "../../../messages/seo-programmatic-fr.json";
import enMessages from "../../../messages/en.json";

export type SitemapPartitionId =
  | "static"
  | "industry"
  | "service"
  | "vehicle"
  | "location"
  | "resource"
  | "article"
  | "case-study"
  | "developer";

export const SITEMAP_PARTITION_IDS: SitemapPartitionId[] = [
  "static",
  "industry",
  "service",
  "vehicle",
  "location",
  "resource",
  "article",
  "case-study",
  "developer",
];

type SitemapEntry = MetadataRoute.Sitemap[number];

const frNicheLanding = frMessages.nicheLanding as Record<string, Partial<NicheLandingContent>>;
const frServiceAreaLanding = frMessages.serviceAreaLanding as unknown as Record<
  string,
  ServiceAreaMessageContent
>;

const EN_ONLY_STATIC_SEGMENTS = new Set([
  "how-porterchain-works",
  "onboarding-education",
  "integrations-education",
]);

const STATIC_PATHS: {
  segment: string;
  priority: number;
  freq?: SitemapEntry["changeFrequency"];
}[] = [
  { segment: "", priority: 1, freq: "weekly" },
  { segment: "business", priority: 0.95 },
  { segment: "contact", priority: 0.9 },
  { segment: "company", priority: 0.85 },
  { segment: "careers", priority: 0.8 },
  { segment: "developers", priority: 0.75 },
  { segment: "blog", priority: 0.85, freq: "weekly" },
  { segment: "track", priority: 0.8 },
  { segment: "vehicle-partner", priority: 0.85 },
  { segment: "drive", priority: 0.8 },
  { segment: "platform", priority: 0.8, freq: "weekly" },
  { segment: "integrations", priority: 0.85 },
  { segment: "enterprise", priority: 0.85 },
  { segment: "solutions", priority: 0.9 },
  { segment: "construction", priority: 0.85 },
  { segment: "vehicles", priority: 0.9 },
  { segment: "service-areas", priority: 0.85 },
  { segment: "faq", priority: 0.85 },
  { segment: "guides", priority: 0.85 },
  { segment: "compare", priority: 0.8 },
  { segment: "success-stories", priority: 0.8 },
  { segment: "campaigns", priority: 0.75 },
  { segment: "privacy", priority: 0.3 },
  { segment: "terms", priority: 0.3 },
  { segment: "cookies", priority: 0.3 },
  { segment: "trust", priority: 0.4 },
];

function skipFrenchEnOnlyContent(locale: Locale): boolean {
  return locale === "fr";
}

function hasFrProgrammaticSlug(
  namespace: "compare" | "faq" | "guides" | "successStories",
  slug: string
): boolean {
  const ns = frProgrammatic[namespace];
  return typeof ns === "object" && ns !== null && slug in ns;
}

function push(
  entries: SitemapEntry[],
  locale: Locale,
  pathSegment: string,
  priority: number,
  changeFrequency: SitemapEntry["changeFrequency"] = "monthly",
  lastModified?: Date
): void {
  const base = siteConfig.baseUrl.replace(/\/$/, "");
  const entry: SitemapEntry = {
    url: `${base}${localePath(locale, pathSegment)}`,
    changeFrequency,
    priority,
  };
  if (lastModified) entry.lastModified = lastModified;
  entries.push(entry);
}

function parseIsoDate(iso?: string): Date | undefined {
  if (!iso) return undefined;
  const ms = Date.parse(iso);
  return Number.isNaN(ms) ? undefined : new Date(ms);
}

export function buildStaticSitemapEntries(): SitemapEntry[] {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    for (const { segment, priority, freq } of STATIC_PATHS) {
      if (locale === "fr" && segment === "service-areas") continue;
      if (locale === "fr" && EN_ONLY_STATIC_SEGMENTS.has(segment)) continue;
      push(entries, locale, segment, priority, freq);
    }
    push(entries, locale, "how-porterchain-works", 0.9);
    push(entries, locale, "solutions", 0.9, "weekly");
    for (const vertical of SOLUTION_VERTICAL_SLUGS) {
      push(entries, locale, solutionVerticalPathSegment(vertical), 0.85);
    }
    for (const slug of CAMPAIGN_SLUGS) {
      push(entries, locale, `campaigns/${slug}`, 0.75);
    }
  }
  entries.push({
    url: `${siteConfig.baseUrl.replace(/\/$/, "")}/ravi`,
    changeFrequency: "monthly",
    priority: 0.5,
  });
  return entries;
}

export function buildIndustrySitemapEntries(): SitemapEntry[] {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    for (const slug of NICHE_SLUGS) {
      if (isDraftNicheSlug(slug)) continue;
      if (locale === "fr" && !isPublishableNiche(frNicheLanding[getNicheMessageKey(slug) ?? ""])) {
        continue;
      }
      push(entries, locale, `industry/${slug}`, 0.8);
    }
  }
  return entries;
}

export function buildServiceSitemapEntries(): SitemapEntry[] {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    push(entries, locale, "local-delivery", 0.9);
  }
  return entries;
}

export function buildVehicleSitemapEntries(): SitemapEntry[] {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    for (const segment of INDEXABLE_VEHICLE_SEGMENTS) {
      const messages = locale === "en" ? enMessages : frMessages;
      if (!shouldIndexVehicleRoute(segment, messages)) continue;
      push(entries, locale, segment, 0.75);
    }
  }
  return entries;
}

export function buildLocationSitemapEntries(): SitemapEntry[] {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    for (const slug of SERVICE_AREA_SLUGS) {
      if (!isCoreServiceArea(slug)) continue;
      if (
        locale === "fr" &&
        !isPublishableServiceArea(frServiceAreaLanding[getServiceAreaMessageKey(slug) ?? ""])
      ) {
        continue;
      }
      push(entries, locale, `service-areas/${slug}`, 0.8);
    }
    for (const { city, segmentSlug } of getAllCitySegmentPairs()) {
      const messages = locale === "en" ? enMessages : frMessages;
      if (!isPublishableCitySegment(locale, city, segmentSlug, messages)) continue;
      push(entries, locale, `${city}/${segmentSlug}`, 0.65);
    }
  }
  return entries;
}

export function buildResourceSitemapEntries(): SitemapEntry[] {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    for (const cluster of FAQ_CLUSTERS) {
      if (locale === "fr" && !hasFrProgrammaticSlug("faq", cluster.slug)) continue;
      push(entries, locale, `faq/${cluster.slug}`, 0.7);
    }
    for (const page of AUTHORITY_PAGES) {
      if (page.slug === "how-porterchain-works") continue;
      if (locale === "fr" && !hasFrProgrammaticSlug("guides", page.slug)) continue;
      push(entries, locale, `guides/${page.slug}`, 0.75);
    }
    for (const page of COMPARISON_PAGES) {
      if (locale === "fr" && !hasFrProgrammaticSlug("compare", page.slug)) continue;
      push(entries, locale, `compare/${page.slug}`, 0.7);
    }
    for (const slug of getAllOnboardingEducationSlugs()) {
      if (skipFrenchEnOnlyContent(locale)) continue;
      push(entries, locale, `onboarding-education/${slug}`, 0.75);
    }
    for (const slug of getAllIntegrationsEducationSlugs()) {
      if (skipFrenchEnOnlyContent(locale)) continue;
      push(entries, locale, `integrations-education/${slug}`, 0.75);
    }
    for (const category of BLOG_CATEGORIES) {
      push(entries, locale, `blog/category/${category}`, 0.65);
    }
  }
  return entries;
}

export async function buildArticleSitemapEntries(): Promise<SitemapEntry[]> {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    const posts = await getAllPosts(locale);
    const slugs = [...(await getAllPostSlugs(locale)), ...getAllPostSlugsSync(locale)].filter(
      (slug, index, arr) => arr.indexOf(slug) === index
    );
    const dateBySlug = new Map(posts.map((p) => [p.slug, p.date]));
    for (const slug of slugs) {
      const lastModified = parseIsoDate(dateBySlug.get(slug));
      push(entries, locale, `blog/${slug}`, 0.7, "weekly", lastModified);
    }
  }
  return entries;
}

export function buildCaseStudySitemapEntries(): SitemapEntry[] {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    for (const story of SUCCESS_STORIES) {
      if (locale === "fr" && !hasFrProgrammaticSlug("successStories", story.slug)) continue;
      push(entries, locale, `success-stories/${story.slug}`, 0.75);
    }
  }
  return entries;
}

export function buildDeveloperSitemapEntries(): SitemapEntry[] {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    push(entries, locale, "developers/docs", 0.7);
    for (const slug of DEVELOPER_DOC_SLUGS) {
      push(entries, locale, `developers/docs/${slug}`, 0.65);
    }
  }
  return entries;
}

export function buildSitemapPartition(
  id: SitemapPartitionId
): SitemapEntry[] | Promise<SitemapEntry[]> {
  switch (id) {
    case "static":
      return buildStaticSitemapEntries();
    case "industry":
      return buildIndustrySitemapEntries();
    case "service":
      return buildServiceSitemapEntries();
    case "vehicle":
      return buildVehicleSitemapEntries();
    case "location":
      return buildLocationSitemapEntries();
    case "resource":
      return buildResourceSitemapEntries();
    case "article":
      return buildArticleSitemapEntries();
    case "case-study":
      return buildCaseStudySitemapEntries();
    case "developer":
      return buildDeveloperSitemapEntries();
    default:
      return [];
  }
}

/** Combined sitemap (all partitions) — used for validation and backwards compatibility. */
export async function buildSitemap(): Promise<MetadataRoute.Sitemap> {
  const article = await buildArticleSitemapEntries();
  const parts = SITEMAP_PARTITION_IDS.filter((id) => id !== "article").flatMap((id) => {
    const result = buildSitemapPartition(id);
    return result instanceof Promise ? [] : result;
  });
  return [...parts, ...article];
}

void ONBOARDING_EDUCATION_PAGES;
void INTEGRATIONS_EDUCATION_PAGES;
