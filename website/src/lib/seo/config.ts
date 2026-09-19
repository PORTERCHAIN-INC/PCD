import { publicEnv } from "@/lib/env";
import { routing, type Locale } from "@/i18n/routing";

export const siteConfig = {
  name: "Porterchain",
  tagline: "Moving Commerce On-Chain",
  description:
    "Reliable vehicle-and-driver capacity for Ontario businesses — overflow, urgent delivery, and recurring distribution with tracking and proof.",
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
