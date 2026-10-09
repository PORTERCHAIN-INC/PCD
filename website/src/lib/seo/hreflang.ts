import type { Metadata } from "next";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { siteConfig } from "./config";
import { localePath } from "./routes";
import { isIndexablePath } from "./url-policy";

export const HREFLANG_LOCALE_MAP: Record<Locale, string> = {
  en: "en",
  fr: "fr-CA",
};

/** Hubs with dedicated `opengraph-image.tsx` under `app/[locale]/<hub>/`. */
const HUB_OPENGRAPH_SEGMENTS = new Set(["business", "blog", "vehicle-partner", "trust"]);

/** Default Open Graph image — hub route when available, else site root. */
export function defaultOpenGraphImages(
  title: string,
  pathSegment: string = "",
  locale: Locale = "en"
) {
  const base = siteConfig.baseUrl.replace(/\/$/, "");
  const first = (pathSegment.split("/")[0] || "").trim();
  const ogPath =
    first && HUB_OPENGRAPH_SEGMENTS.has(first)
      ? `${localePath(locale, first)}/opengraph-image`
      : "/opengraph-image";
  return [
    {
      url: `${base}${ogPath}`,
      width: 1200,
      height: 630,
      alt: title,
    },
  ];
}

export function buildCanonicalPath(locale: Locale, pathSegment: string = ""): string {
  return localePath(locale, pathSegment);
}

export function buildAlternateLanguages(
  locale: Locale,
  pathSegment: string = ""
): Record<string, string> {
  const base = siteConfig.baseUrl.replace(/\/$/, "");
  const out: Record<string, string> = {};
  // Sitemap-managed paths (build-time manifest): only advertise locales that actually serve
  // an indexable page — an EN-only page must not point hreflang at a FR URL that 301s away.
  const indexable = routing.locales.filter((loc) => isIndexablePath(localePath(loc, pathSegment)));
  const managed = indexable.length > 0;
  const locales = managed ? indexable : [...routing.locales];
  if (managed && !locales.includes(locale)) locales.push(locale);
  for (const loc of locales) {
    out[HREFLANG_LOCALE_MAP[loc]] = `${base}${localePath(loc, pathSegment)}`;
  }
  const xDefault = locales.includes("en") ? "en" : locale;
  out["x-default"] = `${base}${localePath(xDefault, pathSegment)}`;
  return out;
}

function shouldIndexInEnvironment(requestedIndex: boolean): boolean {
  if (!requestedIndex) return false;
  const env = process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV;
  if (env === "staging" || env === "preview") return false;
  return true;
}

/** Collapse stray/duplicate separators so no title renders as "… |" or "| …" (audit #14). */
export function cleanSeoTitle(raw: string): string {
  return raw
    .replace(/\s+/g, " ")
    .replace(/(\s*\|\s*){2,}/g, " | ")
    .replace(/^\s*[|·–—-]\s*/, "")
    .replace(/\s*[|·–—-]\s*$/, "")
    .trim();
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
    title: rawTitle,
    description,
    openGraphType = "website",
    index = true,
  } = params;
  const title = cleanSeoTitle(rawTitle);
  const allowIndex = shouldIndexInEnvironment(index);
  const ogImages = defaultOpenGraphImages(title, pathSegment, locale);
  return {
    metadataBase: new URL(siteConfig.baseUrl),
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
      images: ogImages,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: ogImages.map((img) => img.url),
    },
    robots: { index: allowIndex, follow: true },
  };
}
