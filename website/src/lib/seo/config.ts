import { publicEnv } from "@/lib/env";
import { routing, type Locale } from "@/i18n/routing";

export const siteConfig = {
  name: "Porterchain",
  tagline: "Commercial Logistics — GTA Delivery",
  description:
    "Book same-day deliveries across the GTA. Loose parcels, LTL freight, medical courier, food distribution and more. Instant quotes, real-time tracking, proof of delivery.",
  baseUrl: publicEnv.siteUrl,
} as const;

export type { Locale };

export const locales = routing.locales;
export const defaultLocale = routing.defaultLocale;

export function isValidLocale(locale: string): locale is Locale {
  return (routing.locales as readonly string[]).includes(locale);
}

export function getValidLocales(): Locale[] {
  return [...routing.locales];
}
