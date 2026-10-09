import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["en", "fr"],
  defaultLocale: "en",
  localePrefix: "always",
  // hreflang comes from page metadata (<link rel="alternate">, fr-CA). The middleware's
  // Link header used plain "fr" and per-locale roots only — inconsistent signals.
  alternateLinks: false,
});

export type Locale = (typeof routing.locales)[number];
