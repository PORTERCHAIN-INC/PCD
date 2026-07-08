import type { MetadataRoute } from "next";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { siteConfig } from "./config";
import { localePath } from "./routes";
import { NICHE_SLUGS } from "./niche-landing";
import { SERVICE_AREA_SLUGS } from "./service-areas";
import { CAMPAIGN_SLUGS } from "./campaign-landing";
import { getCityIndustrySeoPairs } from "./city-industry-seo";
import { getCityVehicleSeoPairs, getCityDeliveryIntentSeoPairs } from "./city-segment-seo";
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
import { getAllPostSlugs } from "@/lib/blog";
import { BLOG_CATEGORIES } from "@/data/blog-categories";

type SitemapEntry = MetadataRoute.Sitemap[number];

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
  { segment: "integrations", priority: 0.85 },
  { segment: "enterprise", priority: 0.85 },
  { segment: "industry", priority: 0.9 },
  { segment: "service-areas", priority: 0.85 },
  { segment: "faq", priority: 0.85 },
  { segment: "guides", priority: 0.85 },
  { segment: "compare", priority: 0.8 },
  { segment: "onboarding-education", priority: 0.85 },
  { segment: "integrations-education", priority: 0.85 },
  { segment: "success-stories", priority: 0.8 },
  { segment: "campaigns", priority: 0.75 },
  { segment: "sedan-delivery", priority: 0.75 },
  { segment: "suv-delivery", priority: 0.75 },
  { segment: "van-delivery", priority: 0.75 },
  { segment: "medium-truck", priority: 0.75 },
  { segment: "pickup-truck-delivery", priority: 0.75 },
  { segment: "cargo-van-delivery", priority: 0.75 },
  { segment: "privacy", priority: 0.3 },
  { segment: "terms", priority: 0.3 },
  { segment: "cookies", priority: 0.3 },
];

export function buildSitemap(): MetadataRoute.Sitemap {
  const entries: SitemapEntry[] = [];

  for (const locale of routing.locales) {
    for (const { segment, priority, freq } of STATIC_PATHS) {
      push(entries, locale, segment, priority, freq);
    }

    for (const slug of NICHE_SLUGS) {
      push(entries, locale, `industry/${slug}`, 0.8);
    }
    for (const slug of SERVICE_AREA_SLUGS) {
      push(entries, locale, `service-areas/${slug}`, 0.8);
    }
    for (const { city, industrySlug } of getCityIndustrySeoPairs()) {
      push(entries, locale, `${city}/${industrySlug}`, 0.75);
    }
    for (const { city, segmentSlug } of getCityVehicleSeoPairs()) {
      push(entries, locale, `${city}/${segmentSlug}`, 0.72);
    }
    for (const { city, segmentSlug } of getCityDeliveryIntentSeoPairs()) {
      push(entries, locale, `${city}/${segmentSlug}`, 0.72);
    }
    for (const cluster of FAQ_CLUSTERS) {
      push(entries, locale, `faq/${cluster.slug}`, 0.7);
    }
    for (const page of AUTHORITY_PAGES) {
      push(entries, locale, `guides/${page.slug}`, 0.75);
    }
    for (const page of COMPARISON_PAGES) {
      push(entries, locale, `compare/${page.slug}`, 0.7);
    }
    for (const slug of getAllOnboardingEducationSlugs()) {
      push(entries, locale, `onboarding-education/${slug}`, 0.75);
    }
    for (const slug of getAllIntegrationsEducationSlugs()) {
      push(entries, locale, `integrations-education/${slug}`, 0.75);
    }
    for (const story of SUCCESS_STORIES) {
      push(entries, locale, `success-stories/${story.slug}`, 0.75);
    }
    for (const slug of CAMPAIGN_SLUGS) {
      push(entries, locale, `campaigns/${slug}`, 0.75);
    }
    for (const slug of getAllPostSlugs(locale)) {
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
