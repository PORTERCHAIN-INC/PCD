/**
 * Centralized public route builders for SEO pages and internal linking.
 * All paths are locale-prefixed: /en/industry/coffee-roasters
 */
import type { Locale } from "@/i18n/routing";

export const PATHS = {
  HOME: "",
  BUSINESS: "business",
  CONTACT: "contact",
  BLOG: "blog",
  INDUSTRY: "industry",
  SERVICE_AREAS: "service-areas",
  CAMPAIGNS: "campaigns",
  FAQ: "faq",
  COMPARE: "compare",
  GUIDES: "guides",
  ONBOARDING_EDUCATION: "onboarding-education",
  INTEGRATIONS_EDUCATION: "integrations-education",
  SUCCESS_STORIES: "success-stories",
  LOCAL_DELIVERY: "local-delivery",
  HOW_PORTERCHAIN_WORKS: "how-porterchain-works",
  PRICING: "pricing",
  INTEGRATIONS: "integrations",
  ENTERPRISE: "enterprise",
  DRIVE: "drive",
  TRACK: "track",
  SEDAN_DELIVERY: "sedan-delivery",
  SUV_DELIVERY: "suv-delivery",
  VAN_DELIVERY: "van-delivery",
  MEDIUM_TRUCK: "medium-truck",
} as const;

export type RouteQuery = Record<string, string>;

export function localePath(locale: Locale, pathSegment: string = ""): string {
  const segment = pathSegment.replace(/^\//, "");
  return segment ? `/${locale}/${segment}` : `/${locale}`;
}

function withQuery(base: string, query?: RouteQuery): string {
  if (!query || Object.keys(query).length === 0) return base;
  return `${base}?${new URLSearchParams(query).toString()}`;
}

export function home(locale: Locale): string {
  return localePath(locale);
}

export function business(locale: Locale, query?: RouteQuery): string {
  return withQuery(localePath(locale, PATHS.BUSINESS), query);
}

export function contact(locale: Locale, query?: RouteQuery): string {
  return withQuery(localePath(locale, PATHS.CONTACT), query);
}

export function blog(locale: Locale): string {
  return localePath(locale, PATHS.BLOG);
}

export function industry(locale: Locale): string {
  return localePath(locale, PATHS.INDUSTRY);
}

export function industrySlug(locale: Locale, slug: string): string {
  return localePath(locale, `${PATHS.INDUSTRY}/${encodeURIComponent(slug)}`);
}

export function serviceAreas(locale: Locale): string {
  return localePath(locale, PATHS.SERVICE_AREAS);
}

export function serviceAreaSlug(locale: Locale, slug: string): string {
  return localePath(locale, `${PATHS.SERVICE_AREAS}/${encodeURIComponent(slug)}`);
}

export function campaigns(locale: Locale): string {
  return localePath(locale, PATHS.CAMPAIGNS);
}

export function campaignSlug(locale: Locale, slug: string): string {
  return localePath(locale, `${PATHS.CAMPAIGNS}/${encodeURIComponent(slug)}`);
}

export function faq(locale: Locale): string {
  return localePath(locale, PATHS.FAQ);
}

export function faqSlug(locale: Locale, slug: string): string {
  return localePath(locale, `${PATHS.FAQ}/${encodeURIComponent(slug)}`);
}

export function compare(locale: Locale): string {
  return localePath(locale, PATHS.COMPARE);
}

export function compareSlug(locale: Locale, slug: string): string {
  return localePath(locale, `${PATHS.COMPARE}/${encodeURIComponent(slug)}`);
}

export function guides(locale: Locale): string {
  return localePath(locale, PATHS.GUIDES);
}

export function guideSlug(locale: Locale, slug: string): string {
  return localePath(locale, `${PATHS.GUIDES}/${encodeURIComponent(slug)}`);
}

export function onboardingEducation(locale: Locale): string {
  return localePath(locale, PATHS.ONBOARDING_EDUCATION);
}

export function onboardingEducationSlug(locale: Locale, slug: string): string {
  return localePath(locale, `${PATHS.ONBOARDING_EDUCATION}/${encodeURIComponent(slug)}`);
}

export function integrationsEducation(locale: Locale): string {
  return localePath(locale, PATHS.INTEGRATIONS_EDUCATION);
}

export function integrationsEducationSlug(locale: Locale, slug: string): string {
  return localePath(locale, `${PATHS.INTEGRATIONS_EDUCATION}/${encodeURIComponent(slug)}`);
}

export function successStories(locale: Locale): string {
  return localePath(locale, PATHS.SUCCESS_STORIES);
}

export function successStorySlug(locale: Locale, slug: string): string {
  return localePath(locale, `${PATHS.SUCCESS_STORIES}/${encodeURIComponent(slug)}`);
}

export function localDelivery(locale: Locale): string {
  return localePath(locale, PATHS.LOCAL_DELIVERY);
}

export function howPorterchainWorks(locale: Locale): string {
  return localePath(locale, PATHS.HOW_PORTERCHAIN_WORKS);
}

export function pricing(locale: Locale): string {
  return localePath(locale, PATHS.PRICING);
}

export function integrations(locale: Locale): string {
  return localePath(locale, PATHS.INTEGRATIONS);
}

export function enterprise(locale: Locale): string {
  return localePath(locale, PATHS.ENTERPRISE);
}

export function drive(locale: Locale, query?: RouteQuery): string {
  return withQuery(localePath(locale, PATHS.DRIVE), query);
}

export function track(locale: Locale): string {
  return localePath(locale, PATHS.TRACK);
}

export function cityIndustrySeo(
  locale: Locale,
  cityUrlSlug: string,
  industryUrlSlug: string
): string {
  return localePath(
    locale,
    `${encodeURIComponent(cityUrlSlug)}/${encodeURIComponent(industryUrlSlug)}`
  );
}

export function vehicleDeliveryPath(
  locale: Locale,
  segment:
    | "sedan-delivery"
    | "suv-delivery"
    | "van-delivery"
    | "pickup-truck-delivery"
    | "cargo-van-delivery"
    | "medium-truck"
): string {
  return localePath(locale, segment);
}
