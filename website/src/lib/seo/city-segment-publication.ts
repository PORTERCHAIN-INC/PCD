/**
 * W6 publication gate for city×segment SEO matrix (playbook §7).
 * Phase 1: core metros × six P0 industry templates.
 * Phase 2 (W6b): vehicle + delivery-intent segments when localized templates exist.
 */

import type { Locale } from "@/i18n/routing";
import type { NicheLandingContent } from "@/components/seo/IndustryLandingView";
import {
  CITY_SEO_TO_SERVICE_AREA,
  INDUSTRY_SEO_TO_NICHE,
  type CitySeoSlug,
  type IndustrySeoSlug,
} from "./city-industry-seo";
import { getCityIndustryContent } from "./city-industry-delivery";
import { getCityLocalSegmentContent } from "./city-local-segment-content";
import { isPublishableNiche } from "./landing-content";
import { isPublishableServiceArea, type ServiceAreaContent } from "./service-area-content";
import { getNicheMessageKey } from "./niche-landing";
import { getServiceAreaMessageKey, isCoreServiceArea } from "./service-areas";
import { resolveCitySegment, type ResolvedCitySegment } from "./city-segment-seo";

/** Core metros mapped to city URL slugs (playbook §4.5). */
export const W6_PUBLISHABLE_CITY_SEO_SLUGS = [
  "toronto",
  "mississauga",
  "brampton",
  "vaughan",
  "oakville",
  "kitchener",
  "hamilton",
] as const;

/** Six P0 industry templates (playbook W3). */
export const W6_PUBLISHABLE_INDUSTRY_SEO_SLUGS = [
  "construction-materials-delivery",
  "electrical-delivery",
  "plumbing-supply-delivery",
  "coffee-roaster-delivery",
  "pharmacy-delivery",
  "cosmetics-delivery",
] as const;

/** W6b second-wave industries — publish when niche copy passes gate. */
export const W6B_PUBLISHABLE_INDUSTRY_SEO_SLUGS = [
  "chocolate-delivery",
  "lab-sample-delivery",
  "ecommerce-delivery",
] as const;

/** Buyer-facing vehicle routes for W6b. */
export const W6_PUBLISHABLE_VEHICLE_SEO_SLUGS = [
  "trade-van-delivery",
  "box-truck-delivery",
  "cargo-van-delivery",
  "pickup-truck-delivery",
  "sedan-delivery",
  "suv-delivery",
] as const;

/** High-intent delivery patterns for W6b. */
export const W6_PUBLISHABLE_INTENT_SEO_SLUGS = [
  "same-day-delivery",
  "b2b-delivery",
  "recurring-delivery",
  "on-demand-delivery",
  "local-courier",
  "last-mile-delivery",
] as const;

type PublicationMessages = {
  cityIndustryDelivery?: Parameters<typeof getCityIndustryContent>[2]["cityIndustryDelivery"];
  cityLocalSegment?: Parameters<typeof getCityLocalSegmentContent>[3]["cityLocalSegment"];
  vehicleDelivery?: Parameters<typeof getCityLocalSegmentContent>[3]["vehicleDelivery"];
  serviceAreaLanding?: Record<string, Partial<ServiceAreaContent>>;
  nicheLanding?: Record<string, Partial<NicheLandingContent>>;
};

export function isW6PublishableCitySlug(city: string): boolean {
  return (W6_PUBLISHABLE_CITY_SEO_SLUGS as readonly string[]).includes(city);
}

/** W7 extended metros — publish when service-area copy passes gate (playbook §4.5 expansion). */
export const W7_EXTENDED_CITY_SEO_SLUGS = ["oshawa", "london", "st-catharines", "niagara"] as const;

export function isW7PublishableCitySlug(city: string): boolean {
  return (W7_EXTENDED_CITY_SEO_SLUGS as readonly string[]).includes(city);
}

function cityPassesPublicationGate(
  cityUrlSlug: CitySeoSlug,
  messages: PublicationMessages
): boolean {
  const serviceAreaSlug = CITY_SEO_TO_SERVICE_AREA[cityUrlSlug];
  if (isW6PublishableCitySlug(cityUrlSlug)) {
    return isCoreServiceArea(serviceAreaSlug);
  }
  if (!isW7PublishableCitySlug(cityUrlSlug)) return false;

  const areaKey = getServiceAreaMessageKey(serviceAreaSlug);
  if (!areaKey) return false;
  return isPublishableServiceArea(messages.serviceAreaLanding?.[areaKey]);
}

export function isW6PublishableIndustrySlug(slug: string): boolean {
  return (
    (W6_PUBLISHABLE_INDUSTRY_SEO_SLUGS as readonly string[]).includes(slug) ||
    (W6B_PUBLISHABLE_INDUSTRY_SEO_SLUGS as readonly string[]).includes(slug)
  );
}

export function isW6PublishableVehicleSlug(slug: string): boolean {
  return (W6_PUBLISHABLE_VEHICLE_SEO_SLUGS as readonly string[]).includes(slug);
}

export function isW6PublishableIntentSlug(slug: string): boolean {
  return (W6_PUBLISHABLE_INTENT_SEO_SLUGS as readonly string[]).includes(slug);
}

function isPublishableCityLocalSegment(
  locale: Locale,
  cityUrlSlug: CitySeoSlug,
  resolved: Extract<ResolvedCitySegment, { type: "vehicle" | "delivery-intent" }>,
  messages: PublicationMessages
): boolean {
  if (!cityPassesPublicationGate(cityUrlSlug, messages)) return false;
  if (resolved.type === "vehicle" && !isW6PublishableVehicleSlug(resolved.segmentSlug)) {
    return false;
  }
  if (resolved.type === "delivery-intent" && !isW6PublishableIntentSlug(resolved.segmentSlug)) {
    return false;
  }

  const segmentKey = resolved.type === "vehicle" ? resolved.vehicleKey : resolved.intentKey;
  const content = getCityLocalSegmentContent(
    resolved.type,
    segmentKey,
    resolved.serviceAreaSlug,
    messages
  );
  if (!content) return false;

  if (locale === "en") return true;

  const block =
    resolved.type === "vehicle"
      ? messages.cityLocalSegment?.vehicle
      : messages.cityLocalSegment?.intent;
  const areaKey = getServiceAreaMessageKey(resolved.serviceAreaSlug);
  const areaContent = areaKey ? messages.serviceAreaLanding?.[areaKey] : undefined;

  return Boolean(
    block?.meta?.titlePattern &&
    block.hero?.titlePattern &&
    messages.cityLocalSegment?.cta?.primary &&
    messages.cityLocalSegment?.coverage?.titlePattern &&
    messages.cityLocalSegment?.inquiry?.headingPattern &&
    (areaContent?.onboarding?.title || messages.serviceAreaLanding?.default?.onboarding?.title)
  );
}

export function isPublishableCityIndustrySegment(
  locale: Locale,
  cityUrlSlug: CitySeoSlug,
  industryUrlSlug: IndustrySeoSlug,
  messages: PublicationMessages
): boolean {
  if (!isW6PublishableIndustrySlug(industryUrlSlug)) {
    return false;
  }
  if (!cityPassesPublicationGate(cityUrlSlug, messages)) {
    return false;
  }

  const serviceAreaSlug = CITY_SEO_TO_SERVICE_AREA[cityUrlSlug];
  const nicheSlug = INDUSTRY_SEO_TO_NICHE[industryUrlSlug];

  const content = getCityIndustryContent(nicheSlug, serviceAreaSlug, messages);
  if (!content) return false;

  if (locale === "en") return true;

  const nicheKey = getNicheMessageKey(nicheSlug);
  const areaKey = getServiceAreaMessageKey(serviceAreaSlug);
  if (!nicheKey || !areaKey) return false;

  return (
    isPublishableNiche(messages.nicheLanding?.[nicheKey]) &&
    isPublishableServiceArea(messages.serviceAreaLanding?.[areaKey])
  );
}

/** True when a city×segment URL may be indexed and listed in sitemap. */
export function isPublishableCitySegment(
  locale: Locale,
  city: string,
  segmentSlug: string,
  messages: PublicationMessages
): boolean {
  const resolved = resolveCitySegment(city, segmentSlug);
  if (!resolved) return false;

  if (resolved.type === "industry") {
    return isPublishableCityIndustrySegment(
      locale,
      city as CitySeoSlug,
      segmentSlug as IndustrySeoSlug,
      messages
    );
  }

  return isPublishableCityLocalSegment(
    locale,
    city as CitySeoSlug,
    resolved as Extract<ResolvedCitySegment, { type: "vehicle" | "delivery-intent" }>,
    messages
  );
}
