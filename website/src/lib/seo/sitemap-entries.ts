import type { MetadataRoute } from "next";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { siteConfig } from "./config";
import { localePath } from "./routes";
import { getNicheMessageKey, NICHE_SLUGS } from "./niche-landing";
import { getServiceAreaMessageKey, SERVICE_AREA_SLUGS, isCoreServiceArea } from "./service-areas";
import { CAMPAIGN_SLUGS, getCampaignMessageKey } from "./campaign-landing";
import { AUTHORITY_PAGES } from "./content/authority-pages";
import { COMPARISON_PAGES } from "./content/comparison-pages";
import {
  ONBOARDING_EDUCATION_PAGES,
  getAllOnboardingEducationSlugs,
} from "./content/onboarding-education";
import { INTEGRATIONS_EDUCATION_PAGES } from "./content/integrations-education";
import { DEVELOPER_DOC_SLUGS, getDeveloperDoc } from "@/lib/developer-docs";
import { getAllCitySegmentPairs } from "./city-segment-seo";
import { DELIVERY_VERTICALS, deliveryPagePath, listDeliveryPages } from "./delivery-programmatic";
import { isPublishableCitySegment } from "./city-segment-publication";
import { INDEXABLE_VEHICLE_SEGMENTS, shouldIndexVehicleRoute } from "./vehicle-publication";
import { getAllPosts, listBlogAuthors } from "@/lib/blog";
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
  "vehicle",
  "location",
  "resource",
  "article",
  "case-study",
  "developer",
  "delivery",
];

type SitemapEntry = MetadataRoute.Sitemap[number];

/** Oct 2026 focus: no campaign pages in the index (kept as code for paid landing tests). */
const INDEXED_CAMPAIGN_SLUGS: readonly (typeof CAMPAIGN_SLUGS)[number][] = [];

const INDEX_CITY_SEGMENT_PAGES = false;

/** Only real authors get an indexed profile page. */
const INDEXED_AUTHOR_IDS = new Set(["porterchain"]);

const frNicheLanding = frMessages.nicheLanding as Record<string, Partial<NicheLandingContent>>;
const frCampaignLanding = (frMessages as unknown as Record<string, unknown>).campaignLanding as
  Record<string, Partial<NicheLandingContent>> | undefined;
const frServiceAreaLanding = frMessages.serviceAreaLanding as unknown as Record<
  string,
  ServiceAreaMessageContent
>;

const EN_ONLY_STATIC_SEGMENTS = new Set(["onboarding-education"]);

const STATIC_PATHS: {
  segment: string;
  priority: number;
  freq?: SitemapEntry["changeFrequency"];
}[] = [
  { segment: "", priority: 1, freq: "weekly" },
  { segment: "business", priority: 0.95 },
  { segment: "contact", priority: 0.9 },
  { segment: "company", priority: 0.85 },
  { segment: "developers", priority: 0.75 },
  { segment: "blog", priority: 0.85, freq: "weekly" },
  { segment: "track", priority: 0.8 },
  { segment: "vehicle-partner", priority: 0.85 },
  // "drive" omitted: it 308-redirects to /vehicle-partner (sitemaps must list final URLs).
  { segment: "vehicles", priority: 0.9 },
  { segment: "service-areas", priority: 0.85 },
  { segment: "faq", priority: 0.85 },
  { segment: "privacy", priority: 0.3 },
  { segment: "terms", priority: 0.3 },
  { segment: "cookies", priority: 0.3 },
  { segment: "trust", priority: 0.4 },
  { segment: "trust/claims", priority: 0.55 },
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
    // Campaign pages duplicate the industry pages (Oct 2026 focus): not indexed; url-policy
    // 301s them to the industry page.
    for (const slug of INDEXED_CAMPAIGN_SLUGS) {
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
    // City × industry / city × vehicle pages are not indexed (Oct 2026 focus: no doorway
    // pages). url-policy 301s them to the city's service-area page.
    if (INDEX_CITY_SEGMENT_PAGES) {
      for (const { city, segmentSlug } of getAllCitySegmentPairs()) {
        const messages = locale === "en" ? enMessages : frMessages;
        if (!isPublishableCitySegment(locale, city, segmentSlug, messages)) continue;
        push(entries, locale, `${city}/${segmentSlug}`, 0.65);
      }
    }
  }
  return entries;
}

export async function buildResourceSitemapEntries(): Promise<SitemapEntry[]> {
  const entries: SitemapEntry[] = [];
  const authors = await listBlogAuthors();
  const authorIds = authors.map((a) => a.id);
  for (const locale of routing.locales) {
    // Guides, comparison and onboarding-education pages are not indexed (Oct 2026 focus):
    // their answers live in /faq and the money pages; url-policy 301s them there.
    void AUTHORITY_PAGES;
    void COMPARISON_PAGES;
    void getAllOnboardingEducationSlugs;
    void hasFrProgrammaticSlug;
    void skipFrenchEnOnlyContent;
    for (const id of authorIds) {
      if (!INDEXED_AUTHOR_IDS.has(id)) continue;
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
    // Category hubs only when they list at least one post (empty hubs are noindex).
    const used = new Set(posts.map((p) => p.category));
    for (const category of BLOG_CATEGORIES) {
      if (used.has(category)) push(entries, locale, `blog/category/${category}`, 0.65);
    }
  }
  return entries;
}

/** Case studies were merged into the industry hubs (Oct 2026); kept as an empty child sitemap. */
export async function buildCaseStudySitemapEntries(): Promise<SitemapEntry[]> {
  const entries: SitemapEntry[] = [];
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
  // Industry × area pages are not indexed (Oct 2026 focus: one strong page per industry).
  void listDeliveryPages;
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
