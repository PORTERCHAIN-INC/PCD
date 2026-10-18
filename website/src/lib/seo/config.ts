import { publicEnv } from "@/lib/env";
import { routing, type Locale } from "@/i18n/routing";

export const siteConfig = {
  name: "PorterChain",
  legalName: "Porterchain Inc.",
  tagline: "Same-day courier for the GTA",
  description:
    "Same-day and next-day business courier across Toronto and the GTA by sedan, SUV, van or 16 ft box truck. Instant price, live tracking, photo proof.",
  baseUrl: publicEnv.siteUrl,
} as const;

export type { Locale };

export const locales = routing.locales;
export const defaultLocale = routing.defaultLocale;
