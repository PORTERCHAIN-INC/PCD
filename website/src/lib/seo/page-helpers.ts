import { routing, type Locale } from "@/i18n/routing";
import { buildSeoMetadata } from "@/lib/seo/hreflang";

export function localeStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export function buildPageMetadata(
  locale: string,
  pathSegment: string,
  title: string,
  description: string
) {
  return buildSeoMetadata({
    locale: locale as Locale,
    pathSegment,
    title,
    description,
  });
}
