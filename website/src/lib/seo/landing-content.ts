import { getMessages } from "next-intl/server";
import type { Locale } from "@/i18n/routing";
import type { NicheLandingContent } from "@/components/seo/IndustryLandingView";

function isCompleteNiche(content: Partial<NicheLandingContent> | undefined): boolean {
  return Boolean(
    content?.hero?.title &&
    content?.hero?.subtitle &&
    content?.painPoints?.title &&
    content?.painPoints?.item1
  );
}

function withLandingDefaults(content: Partial<NicheLandingContent>): NicheLandingContent {
  return {
    ...content,
    hero: content.hero!,
    painPoints: content.painPoints!,
    cta: content.cta ?? {
      title: "Ready to simplify your delivery?",
      description: "Tell us your volume and routes. We'll show you how Porterchain fits.",
      primary: "Talk to us",
      secondary: "Contact us",
    },
  };
}

/** Load niche/campaign landing copy with EN fallback when FR content is partial. */
export async function getLandingContent(
  locale: string,
  namespace: "nicheLanding" | "campaignLanding",
  messageKey: string
): Promise<NicheLandingContent | null> {
  const messages = await getMessages({ locale });
  const bucket = (messages as Record<string, Record<string, NicheLandingContent>>)[namespace];
  const localized = bucket?.[messageKey];

  if (isCompleteNiche(localized)) return withLandingDefaults(localized);

  if (locale !== "en") {
    const enMessages = (await import("../../../messages/en.json")).default as {
      nicheLanding?: Record<string, Partial<NicheLandingContent>>;
      campaignLanding?: Record<string, Partial<NicheLandingContent>>;
    };
    const fallback = enMessages[namespace]?.[messageKey];
    if (fallback && isCompleteNiche(fallback)) return withLandingDefaults(fallback);
  }

  return localized && isCompleteNiche(localized) ? withLandingDefaults(localized) : null;
}

export type { Locale };
