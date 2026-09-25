import { getMessages } from "next-intl/server";
import type { Locale } from "@/i18n/routing";
import type { NicheLandingContent } from "@/components/seo/IndustryLandingView";
import { quoteCtaLabel } from "@/lib/cta";

function isCompleteNiche(content: Partial<NicheLandingContent> | undefined): boolean {
  return Boolean(
    content?.hero?.title &&
    content?.hero?.subtitle &&
    content?.painPoints?.title &&
    content?.painPoints?.item1
  );
}

/** Publication gate for localized industry pages; partial copy may render but must not be indexed. */
export function isPublishableNiche(content: Partial<NicheLandingContent> | undefined): boolean {
  if (
    !isCompleteNiche(content) ||
    !content?.meta?.title ||
    !content.meta.description ||
    !content.painPoints?.item2 ||
    !content.painPoints.item3 ||
    !content.solution?.title ||
    !content.solution.description ||
    !content.vehicleFit?.title ||
    !content.vehicleFit.description ||
    !content.workflow?.title ||
    !content.workflow.description ||
    !content.workflow.step1Title ||
    !content.workflow.step1Description ||
    !content.workflow.step2Title ||
    !content.workflow.step2Description ||
    !content.workflow.step3Title ||
    !content.workflow.step3Description ||
    !content.coverage?.title ||
    !content.coverage.description ||
    !content.onboarding?.title ||
    !content.onboarding.description ||
    !content.faq?.title ||
    !content.faq.q1 ||
    !content.faq.a1 ||
    !content.faq.q2 ||
    !content.faq.a2 ||
    !content.cta?.title ||
    !content.cta.description ||
    !content.cta.primary
  ) {
    return false;
  }

  const resolved = withLandingDefaults(content);
  return Boolean(resolved.onboarding?.step2Description && resolved.faq?.a3 !== undefined);
}

function mergeLandingContent(
  base: Partial<NicheLandingContent> | undefined,
  override: Partial<NicheLandingContent> | undefined
): Partial<NicheLandingContent> {
  if (!base) return override ?? {};
  if (!override) return base;
  return {
    ...base,
    ...override,
    meta: { ...base.meta, ...override.meta },
    hero: override.hero?.title ? override.hero : base.hero,
    painPoints: override.painPoints?.title ? override.painPoints : base.painPoints,
    solution: override.solution?.title ? override.solution : base.solution,
    vehicleFit: override.vehicleFit ?? base.vehicleFit,
    serviceAreaRelevance: override.serviceAreaRelevance ?? base.serviceAreaRelevance,
    workflow: override.workflow ?? base.workflow,
    coverage: override.coverage ?? base.coverage,
    onboarding: override.onboarding ?? base.onboarding,
    faq: override.faq ?? base.faq,
    cta: override.cta ?? base.cta,
    personas: override.personas ?? base.personas,
  };
}

/** Shared niche bodies — omit matching keys from niche JSON to avoid duplication. */
export const NICHE_DEFAULT_COPY = {
  onboardingStep2Description:
    "Our drivers pick up and deliver. You get live tracking and one dashboard for every shipment.",
  faqA3:
    "Every shipment gets a tracking link. You can share it so customers see status and ETA in real time.",
} as const;

function withLandingDefaults(content: Partial<NicheLandingContent>): NicheLandingContent {
  const onboarding = content.onboarding
    ? {
        ...content.onboarding,
        step2Description:
          content.onboarding.step2Description ?? NICHE_DEFAULT_COPY.onboardingStep2Description,
      }
    : content.onboarding;
  const faq = content.faq
    ? {
        ...content.faq,
        a3: content.faq.a3 ?? NICHE_DEFAULT_COPY.faqA3,
      }
    : content.faq;

  return {
    ...content,
    hero: content.hero!,
    painPoints: content.painPoints!,
    onboarding,
    faq,
    cta: content.cta ?? {
      title: "Ready to simplify your delivery?",
      description: "Tell us your volume and routes. We'll show you how Porterchain fits.",
      primary: quoteCtaLabel("en"),
      secondary: "Contact us",
    },
  };
}

export type LandingContentResult = {
  content: NicheLandingContent | null;
  indexable: boolean;
};

type MessageBucket = Record<string, Partial<NicheLandingContent>>;

function resolveFromBucket(
  locale: string,
  namespace: "nicheLanding" | "campaignLanding",
  messageKey: string,
  bucket: MessageBucket | undefined
): LandingContentResult {
  const localized = bucket?.[messageKey];
  let merged = localized;
  if (namespace === "campaignLanding") {
    merged = mergeLandingContent(bucket?.default, localized);
  }

  if (isCompleteNiche(merged)) {
    return {
      content: withLandingDefaults(merged!),
      indexable: locale === "en" || isPublishableNiche(localized ?? merged),
    };
  }

  if (locale !== "en") {
    return { content: null, indexable: false };
  }

  return { content: null, indexable: false };
}

/** Load niche/campaign landing copy with EN fallback when FR content is partial. */
export async function resolveLandingContent(
  locale: string,
  namespace: "nicheLanding" | "campaignLanding",
  messageKey: string
): Promise<LandingContentResult> {
  const messages = await getMessages({ locale });
  const bucket = (messages as Record<string, MessageBucket>)[namespace];
  const localizedResult = resolveFromBucket(locale, namespace, messageKey, bucket);
  if (localizedResult.content) return localizedResult;

  if (locale !== "en") {
    const enMessages = (await import("../../../messages/en.json")).default as unknown as Record<
      string,
      MessageBucket
    >;
    const enBucket = enMessages[namespace];
    const enResult = resolveFromBucket("en", namespace, messageKey, enBucket);
    if (enResult.content) {
      return { content: enResult.content, indexable: false };
    }
  }

  const localized = bucket?.[messageKey];
  if (localized && isCompleteNiche(localized)) {
    return {
      content: withLandingDefaults(localized),
      indexable: locale === "en",
    };
  }

  return { content: null, indexable: false };
}

export async function getLandingContent(
  locale: string,
  namespace: "nicheLanding" | "campaignLanding",
  messageKey: string
): Promise<NicheLandingContent | null> {
  const { content } = await resolveLandingContent(locale, namespace, messageKey);
  return content;
}

export type { Locale };
