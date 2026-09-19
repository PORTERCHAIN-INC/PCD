import { routing, type Locale } from "@/i18n/routing";
import { buildSeoMetadata } from "@/lib/seo/hreflang";

export function localeStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export function buildPageMetadata(
  locale: string,
  pathSegment: string,
  title: string,
  description: string,
  options?: { index?: boolean }
) {
  return buildSeoMetadata({
    locale: locale as Locale,
    pathSegment,
    title,
    description,
    index: options?.index !== false,
  });
}

/** Index when localized body exists for the locale (EN always; FR when seo-programmatic-fr has slug). */
export function buildProgrammaticPageMetadata(
  locale: string,
  pathSegment: string,
  title: string,
  description: string,
  localized: boolean
) {
  return buildPageMetadata(locale, pathSegment, title, description, {
    index: locale === "en" || localized,
  });
}

/** @deprecated Use buildProgrammaticPageMetadata with localized flag */
export function buildEnglishOnlyPageMetadata(
  locale: string,
  pathSegment: string,
  title: string,
  description: string
) {
  return buildPageMetadata(locale, pathSegment, title, description, {
    index: locale === "en",
  });
}
