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
import { getAllCitySegmentPairs } from "./city-segment-seo";
import { isPublishableCitySegment } from "./city-segment-publication";
import { INDEXABLE_VEHICLE_SEGMENTS, shouldIndexVehicleRoute } from "./vehicle-publication";
import { getAllPostSlugs, getAllPostSlugsSync } from "@/lib/blog";
import { SOLUTION_VERTICAL_SLUGS } from "@/lib/solutions-verticals";
import { BLOG_CATEGORIES } from "@/data/blog-categories";
import { isPublishableNiche } from "./landing-content";
import { isPublishableServiceArea, type ServiceAreaContent } from "./service-area-content";
import type { NicheLandingContent } from "@/components/seo/IndustryLandingView";
import frMessages from "../../../messages/fr.json";
import frProgrammatic from "../../../messages/seo-programmatic-fr.json";
import enMessages from "../../../messages/en.json";

type SitemapEntry = MetadataRoute.Sitemap[number];
const frNicheLanding = frMessages.nicheLanding as Record<string, Partial<NicheLandingContent>>;
const frServiceAreaLanding = frMessages.serviceAreaLanding as Record<
  string,
  Partial<ServiceAreaContent>
>;

const EN_ONLY_STATIC_SEGMENTS = new Set([
  "how-porterchain-works",
  "onboarding-education",
  "integrations-education",
]);

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
  changeFrequency: SitemapEntry["changeFrequency"] = "monthly"
): void {
  const base = siteConfig.baseUrl.replace(/\/$/, "");
  entries.push({
    url: `${base}${localePath(locale, pathSegment)}`,
    lastModified: new Date(),
    changeFrequency,
    priority,
  });
}

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
  { segment: "local-delivery", priority: 0.9 },
  { segment: "how-porterchain-works", priority: 0.9 },
  { segment: "pricing", priority: 0.85 },
  { segment: "platform", priority: 0.8, freq: "weekly" },
  { segment: "solutions", priority: 0.9, freq: "weekly" },
  { segment: "integrations", priority: 0.85 },
  { segment: "enterprise", priority: 0.85 },
  { segment: "industry", priority: 0.9 },
  { segment: "service-areas", priority: 0.85 },
  { segment: "faq", priority: 0.85 },
  { segment: "guides", priority: 0.85 },
  { segment: "compare", priority: 0.8 },
  { segment: "success-stories", priority: 0.8 },
  { segment: "campaigns", priority: 0.75 },
  { segment: "privacy", priority: 0.3 },
  { segment: "terms", priority: 0.3 },
  { segment: "cookies", priority: 0.3 },
];

export async function buildSitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: SitemapEntry[] = [];

  for (const locale of routing.locales) {
    for (const { segment, priority, freq } of STATIC_PATHS) {
      if (locale === "fr" && segment === "service-areas") continue;
      if (locale === "fr" && EN_ONLY_STATIC_SEGMENTS.has(segment)) continue;
      push(entries, locale, segment, priority, freq);
    }

    for (const vertical of SOLUTION_VERTICAL_SLUGS) {
      push(entries, locale, `solutions/${vertical}`, 0.85);
    }

    for (const slug of NICHE_SLUGS) {
      if (
        locale === "fr" &&
        // Message keys are centralized; avoid publishing translated stubs.
        !isPublishableNiche(frNicheLanding[getNicheMessageKey(slug) ?? ""])
      ) {
        continue;
      }
      push(entries, locale, `industry/${slug}`, 0.8);
    }
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
    // W6 gate: index only core metro × P0 industry pairs with complete localized copy.
    for (const { city, segmentSlug } of getAllCitySegmentPairs()) {
      const messages = locale === "en" ? enMessages : frMessages;
      if (!isPublishableCitySegment(locale, city, segmentSlug, messages)) continue;
      push(entries, locale, `${city}/${segmentSlug}`, 0.65);
    }
    for (const segment of INDEXABLE_VEHICLE_SEGMENTS) {
      const messages = locale === "en" ? enMessages : frMessages;
      if (!shouldIndexVehicleRoute(segment, messages)) continue;
      push(entries, locale, segment, 0.75);
    }
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
    for (const story of SUCCESS_STORIES) {
      if (locale === "fr" && !hasFrProgrammaticSlug("successStories", story.slug)) continue;
      push(entries, locale, `success-stories/${story.slug}`, 0.75);
    }
    for (const slug of CAMPAIGN_SLUGS) {
      push(entries, locale, `campaigns/${slug}`, 0.75);
    }
    for (const slug of [...(await getAllPostSlugs(locale)), ...getAllPostSlugsSync(locale)].filter(
      (slug, index, arr) => arr.indexOf(slug) === index
    )) {
      push(entries, locale, `blog/${slug}`, 0.7, "weekly");
    }
    for (const category of BLOG_CATEGORIES) {
      push(entries, locale, `blog/category/${category}`, 0.65);
    }
  }

  entries.push({
    url: `${siteConfig.baseUrl.replace(/\/$/, "")}/ravi`,
    lastModified: new Date(),
    changeFrequency: "monthly",
    priority: 0.5,
  });

  return entries;
}

// silence unused import warnings for hub-only exports
void ONBOARDING_EDUCATION_PAGES;
void INTEGRATIONS_EDUCATION_PAGES;
