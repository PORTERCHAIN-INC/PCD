/**
 * Quote CTA SSOT for non-i18n content modules (SEO sheets, defaults).
 * React surfaces should use getTranslations/useTranslations("common.cta").
 * Keep in sync with website/messages/{en,fr}.json → common.cta.
 */
export const QUOTE_CTA = {
  en: "Get a quote",
  fr: "Obtenir une soumission",
} as const;

export const REQUEST_CAPACITY_CTA = {
  en: "Request capacity",
  fr: "Demander de la capacité",
} as const;

export function quoteCtaLabel(locale: string = "en"): string {
  return locale === "fr" ? QUOTE_CTA.fr : QUOTE_CTA.en;
}

export function requestCapacityCtaLabel(locale: string = "en"): string {
  return locale === "fr" ? REQUEST_CAPACITY_CTA.fr : REQUEST_CAPACITY_CTA.en;
}
