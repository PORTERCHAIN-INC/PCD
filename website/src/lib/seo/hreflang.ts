import type { Metadata } from "next";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { siteConfig } from "./config";
import { localePath } from "./routes";

export const HREFLANG_LOCALE_MAP: Record<Locale, string> = {
  en: "en",
  fr: "fr-CA",
};

export function buildCanonicalPath(locale: Locale, pathSegment: string = ""): string {
  return localePath(locale, pathSegment);
}

export function buildAlternateLanguages(
  locale: Locale,
  pathSegment: string = ""
): Record<string, string> {
  const base = siteConfig.baseUrl.replace(/\/$/, "");
  const out: Record<string, string> = {};
  for (const loc of routing.locales) {
    out[HREFLANG_LOCALE_MAP[loc]] = `${base}${localePath(loc, pathSegment)}`;
  }
  out["x-default"] = `${base}${localePath("en", pathSegment)}`;
  return out;
}

export function buildSeoMetadata(params: {
  locale: Locale;
  pathSegment: string;
  title: string;
  description: string;
  openGraphType?: "website" | "article";
  index?: boolean;
}): Metadata {
  const {
    locale,
    pathSegment,
    title,
    description,
    openGraphType = "website",
    index = true,
  } = params;
  return {
    title,
    description,
    alternates: {
      canonical: buildCanonicalPath(locale, pathSegment),
      languages: buildAlternateLanguages(locale, pathSegment),
    },
    openGraph: {
      title,
      description,
      type: openGraphType,
      locale: locale === "fr" ? "fr_CA" : "en_CA",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
    robots: { index, follow: true },
  };
}
