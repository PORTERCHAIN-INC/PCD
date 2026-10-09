import type { MetadataRoute } from "next";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { siteConfig } from "./config";
import { localePath } from "./routes";
import { getNicheMessageKey, NICHE_SLUGS } from "./niche-landing";
import { getServiceAreaMessageKey, SERVICE_AREA_SLUGS, isCoreServiceArea } from "./service-areas";
import { CAMPAIGN_SLUGS, getCampaignMessageKey } from "./campaign-landing";
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
import { CAPABILITY_PAGES } from "./content/capabilities";
import { DEVELOPER_DOC_SLUGS, getDeveloperDoc } from "@/lib/developer-docs";
import { getAllCitySegmentPairs } from "./city-segment-seo";
import { DELIVERY_VERTICALS, deliveryPagePath, listDeliveryPages } from "./delivery-programmatic";
import { isPublishableCitySegment } from "./city-segment-publication";
import { INDEXABLE_VEHICLE_SEGMENTS, shouldIndexVehicleRoute } from "./vehicle-publication";
import { getAllPosts, listBlogAuthors } from "@/lib/blog";
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
  | "developer"
  | "delivery";

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
  "delivery",
];

type SitemapEntry = MetadataRoute.Sitemap[number];

const frNicheLanding = frMessages.nicheLanding as Record<string, Partial<NicheLandingContent>>;
const frCampaignLanding = (frMessages as unknown as Record<string, unknown>).campaignLanding as
  Record<string, Partial<NicheLandingContent>> | undefined;
const frServiceAreaLanding = frMessages.serviceAreaLanding as unknown as Record<
  string,
  ServiceAreaMessageContent
>;

const EN_ONLY_STATIC_SEGMENTS = new Set([
  // FR hub is noindex until the FR area pages are complete (service-areas/page.tsx).
  "service-areas",
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
  { segment: "authors", priority: 0.7, freq: "monthly" },
  { segment: "track", priority: 0.8 },
  { segment: "vehicle-partner", priority: 0.85 },
  // "solutions" and "construction" are pushed with the solution verticals below.
  // "drive" omitted: it 308-redirects to /vehicle-partner (sitemaps must list final URLs).
  { segment: "platform", priority: 0.8, freq: "weekly" },
  { segment: "capabilities", priority: 0.85, freq: "weekly" },
  { segment: "integrations", priority: 0.85 },
  { segment: "enterprise", priority: 0.85 },
  { segment: "vehicles", priority: 0.9 },
  { segment: "service-areas", priority: 0.85 },
  { segment: "faq", priority: 0.85 },
  { segment: "guides", priority: 0.85, freq: "weekly" },
  { segment: "compare", priority: 0.8 },
  { segment: "campaigns", priority: 0.75 },
  { segment: "privacy", priority: 0.3 },
  { segment: "terms", priority: 0.3 },
  { segment: "cookies", priority: 0.3 },
  { segment: "trust", priority: 0.4 },
  { segment: "trust/claims", priority: 0.55 },
  { segment: "trust/sla", priority: 0.45 },
];

function skipFrenchEnOnlyContent(locale: Locale): boolean {
  return locale === "fr";
}

function hasFrProgrammaticSlug(
  namespace: "compare" | "faq" | "guides" | "successStories" | "capabilities",
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
      if (locale === "fr" && EN_ONLY_STATIC_SEGMENTS.has(segment)) continue;
      push(entries, locale, segment, priority, freq);
    }
    push(entries, locale, "how-porterchain-works", 0.9);
    push(entries, locale, "solutions", 0.9, "weekly");
    for (const vertical of SOLUTION_VERTICAL_SLUGS) {
      push(entries, locale, solutionVerticalPathSegment(vertical), 0.85);
    }
    for (const slug of CAMPAIGN_SLUGS) {
      // FR campaigns without a full translation render the EN copy with noindex — keep them out.
      if (
        locale === "fr" &&
        !isPublishableNiche(frCampaignLanding?.[getCampaignMessageKey(slug) ?? ""])
      ) {
        continue;
      }
      push(entries, locale, `campaigns/${slug}`, 0.75);
    }
  }
  // Intentional: founder personal contact card at /ravi (non-locale, public).
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

export async function buildResourceSitemapEntries(): Promise<SitemapEntry[]> {
  const entries: SitemapEntry[] = [];
  const authors = await listBlogAuthors();
  const authorIds = authors.map((a) => a.id);
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
    for (const page of CAPABILITY_PAGES) {
      if (locale === "fr" && !hasFrProgrammaticSlug("capabilities", page.slug)) continue;
      push(entries, locale, `capabilities/${page.slug}`, 0.8);
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
    for (const id of authorIds) {
      push(entries, locale, `authors/${id}`, 0.55, "monthly");
    }
  }
  return entries;
}

export async function buildArticleSitemapEntries(): Promise<SitemapEntry[]> {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    const posts = await getAllPosts(locale);
    for (const post of posts) {
      push(entries, locale, `blog/${post.slug}`, 0.7, "weekly", parseIsoDate(post.date));
    }
  }
  return entries;
}

export async function buildCaseStudySitemapEntries(): Promise<SitemapEntry[]> {
  const entries: SitemapEntry[] = [];
  const { listPublicSuccessStories } = await import("./content/success-stories");
  const { listLocalizedSuccessStorySlugs } = await import("./programmatic-content");
  const publicSlugs = new Set(listPublicSuccessStories().map((s) => s.slug));
  for (const locale of routing.locales) {
    if (publicSlugs.size > 0) {
      push(entries, locale, "success-stories", 0.7, "monthly");
    }
    const localized = await listLocalizedSuccessStorySlugs(locale);
    for (const slug of localized) {
      if (!publicSlugs.has(slug)) continue;
      push(entries, locale, `success-stories/${slug}`, 0.65, "monthly");
    }
  }
  return entries;
}

export function buildDeveloperSitemapEntries(): SitemapEntry[] {
  const entries: SitemapEntry[] = [];
  for (const locale of routing.locales) {
    push(entries, locale, "developers/docs", 0.7);
    for (const slug of DEVELOPER_DOC_SLUGS) {
      // Docs are read from the API docs folder; a missing file renders not-found (soft 404).
      if (!getDeveloperDoc(slug)) continue;
      push(entries, locale, `developers/docs/${slug}`, 0.65);
    }
  }
  return entries;
}

/** Programmatic /delivery pages — English copy only; noindex (weak) pages are left out. */
export function buildDeliverySitemapEntries(): SitemapEntry[] {
  const entries: SitemapEntry[] = [];
  const locale: Locale = "en";
  push(entries, locale, "delivery", 0.85, "weekly");
  push(entries, locale, "delivery-cost-calculator", 0.85);
  push(entries, locale, "facts", 0.7);
  for (const vertical of DELIVERY_VERTICALS) {
    push(entries, locale, deliveryPagePath(vertical.slug), 0.8);
  }
  for (const page of listDeliveryPages()) {
    if (page.index) push(entries, locale, page.path, 0.7);
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
    case "delivery":
      return buildDeliverySitemapEntries();
    default:
      return [];
  }
}

void ONBOARDING_EDUCATION_PAGES;
void INTEGRATIONS_EDUCATION_PAGES;
