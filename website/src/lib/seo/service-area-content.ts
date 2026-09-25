import { getMessages } from "next-intl/server";
import { quoteCtaLabel } from "@/lib/cta";

export type ServiceAreaContent = {
  meta?: { title?: string; description?: string };
  hero: { title: string; subtitle: string };
  painPoints?: { title: string; item1: string; item2: string; item3: string };
  solution?: {
    title: string;
    description: string;
    bullet1?: string;
    bullet2?: string;
    bullet3?: string;
  };
  workflow?: {
    title: string;
    description: string;
    step1Title: string;
    step1Description: string;
    step2Title: string;
    step2Description: string;
    step3Title: string;
    step3Description: string;
  };
  vehicles?: { title: string; description: string };
  coverage: { title: string; description: string };
  onboarding: {
    title: string;
    description: string;
    step1Title: string;
    step1Description: string;
    step2Title: string;
    step2Description: string;
    step3Title: string;
    step3Description: string;
  };
  faq: {
    title: string;
    q1: string;
    a1: string;
    q2: string;
    a2: string;
    q3: string;
    a3: string;
    q4?: string;
    a4?: string;
    q5?: string;
    a5?: string;
    q6?: string;
    a6?: string;
    q7?: string;
    a7?: string;
  };
  cta: { title: string; description: string; primary: string; secondary: string };
};

/** Message JSON may omit bodies that fall through to SERVICE_AREA_DEFAULT_COPY. */
export type ServiceAreaMessageContent = Omit<
  Partial<ServiceAreaContent>,
  "onboarding" | "faq" | "cta" | "coverage" | "hero"
> & {
  hero?: Partial<ServiceAreaContent["hero"]>;
  coverage?: Partial<ServiceAreaContent["coverage"]>;
  onboarding?: Partial<ServiceAreaContent["onboarding"]>;
  faq?: Partial<ServiceAreaContent["faq"]>;
  cta?: Partial<ServiceAreaContent["cta"]>;
};

/** Shared FAQ/onboarding bodies — omit matching keys from city JSON to avoid duplication. */
export const SERVICE_AREA_DEFAULT_COPY = {
  onboarding: {
    title: "Simple onboarding",
    description: "Get set up for local delivery without the fleet headache.",
    step1Title: "Connect",
    step1Description:
      "Share your volume and service areas. We align capacity and service expectations.",
    step2Title: "We deliver",
    step2Description:
      "Our drivers pick up and deliver across your zones. Live tracking and one dashboard for every shipment.",
    step3Title: "You stay in control",
    step3Description: "Track every parcel, see ETAs, and get clear reporting.",
  },
  faq: {
    a2: "Share your volume and routes. We align capacity and can have you shipping within days, not weeks.",
    a3: "Every shipment gets a tracking link. Share it so customers see status and ETA in real time.",
  },
} as const;

function withServiceAreaDefaults(content: ServiceAreaMessageContent): ServiceAreaContent | null {
  if (!content.hero?.title || !content.hero?.subtitle) return null;

  const areaLabel = content.hero.title.replace(/^Delivery in /i, "").replace(/^Livraison à /i, "");
  const d = SERVICE_AREA_DEFAULT_COPY;

  return {
    ...content,
    meta: content.meta,
    hero: { title: content.hero.title, subtitle: content.hero.subtitle },
    coverage: {
      title: content.coverage?.title ?? `Coverage — ${areaLabel}`,
      description:
        content.coverage?.description ??
        `We deliver across ${areaLabel} with the same reliability and local operations for your business.`,
    },
    onboarding: {
      title: content.onboarding?.title ?? d.onboarding.title,
      description: content.onboarding?.description ?? d.onboarding.description,
      step1Title: content.onboarding?.step1Title ?? d.onboarding.step1Title,
      step1Description: content.onboarding?.step1Description ?? d.onboarding.step1Description,
      step2Title: content.onboarding?.step2Title ?? d.onboarding.step2Title,
      step2Description: content.onboarding?.step2Description ?? d.onboarding.step2Description,
      step3Title: content.onboarding?.step3Title ?? d.onboarding.step3Title,
      step3Description: content.onboarding?.step3Description ?? d.onboarding.step3Description,
    },
    faq: {
      title: content.faq?.title ?? `Frequently asked questions — ${areaLabel}`,
      q1: content.faq?.q1 ?? `Do you deliver across ${areaLabel}?`,
      a1:
        content.faq?.a1 ??
        "Yes. Share your zones or postal codes and we'll confirm coverage and capacity.",
      q2: content.faq?.q2 ?? "How quickly can we get started?",
      a2: content.faq?.a2 ?? d.faq.a2,
      q3: content.faq?.q3 ?? "Can my customers track their delivery?",
      a3: content.faq?.a3 ?? d.faq.a3,
      ...(content.faq?.q4 ? { q4: content.faq.q4, a4: content.faq.a4 } : {}),
      ...(content.faq?.q5 ? { q5: content.faq.q5, a5: content.faq.a5 } : {}),
      ...(content.faq?.q6 ? { q6: content.faq.q6, a6: content.faq.a6 } : {}),
      ...(content.faq?.q7 ? { q7: content.faq.q7, a7: content.faq.a7 } : {}),
    },
    cta: {
      title: content.cta?.title ?? `Ready for reliable delivery in ${areaLabel}?`,
      description:
        content.cta?.description ??
        "Tell us your volume and routes. We'll show you how we can run your recurring delivery.",
      primary: content.cta?.primary || quoteCtaLabel("en"),
      secondary: content.cta?.secondary ?? "Contact us",
    },
  };
}

/**
 * Publication gate for localized service-area pages.
 * City-specific meta/hero/coverage/FAQ questions stay required in JSON;
 * duplicated FAQ/onboarding bodies may fall through to defaults.
 */
export function isPublishableServiceArea(content: ServiceAreaMessageContent | undefined): boolean {
  if (!content?.meta?.title || !content.meta.description) return false;
  if (!content.hero?.title || !content.hero.subtitle) return false;
  if (!content.coverage?.title || !content.coverage.description) return false;
  if (!content.onboarding?.title || !content.onboarding.description) return false;
  if (
    !content.onboarding.step1Title ||
    !content.onboarding.step2Title ||
    !content.onboarding.step3Title
  ) {
    return false;
  }
  if (!content.faq?.title || !content.faq.q1 || !content.faq.a1 || !content.faq.q2) return false;
  if (!content.cta?.title || !content.cta.description || !content.cta.primary) return false;

  const resolved = withServiceAreaDefaults(content);
  return Boolean(
    resolved?.onboarding.step1Description &&
    resolved.onboarding.step2Description &&
    resolved.onboarding.step3Description &&
    resolved.faq.a2
  );
}

function mergeServiceArea(
  base: ServiceAreaMessageContent | undefined,
  override: ServiceAreaMessageContent | undefined
): ServiceAreaMessageContent {
  if (!base) return override ?? {};
  if (!override) return base;
  return {
    ...base,
    ...override,
    meta: { ...base.meta, ...override.meta },
    hero: override.hero?.title ? override.hero : base.hero,
    painPoints: override.painPoints ?? base.painPoints,
    solution: override.solution ?? base.solution,
    workflow: override.workflow ?? base.workflow,
    vehicles: override.vehicles ?? base.vehicles,
    coverage: override.coverage ?? base.coverage,
    onboarding:
      base.onboarding || override.onboarding
        ? { ...base.onboarding, ...override.onboarding }
        : undefined,
    faq: base.faq || override.faq ? { ...base.faq, ...override.faq } : undefined,
    cta: override.cta ?? base.cta,
  };
}

/** Load service area copy with EN fallback and defaults for partial FR translations. */
export async function getServiceAreaContent(
  locale: string,
  messageKey: string
): Promise<ServiceAreaContent | null> {
  const messages = await getMessages({ locale });
  const localized = (messages as { serviceAreaLanding?: Record<string, ServiceAreaMessageContent> })
    .serviceAreaLanding?.[messageKey];

  let merged: ServiceAreaMessageContent = localized ?? {};
  if (locale !== "en") {
    const enMessages = (await import("../../../messages/en.json")).default as unknown as {
      serviceAreaLanding?: Record<string, ServiceAreaMessageContent>;
    };
    const enContent = enMessages.serviceAreaLanding?.[messageKey];
    merged = mergeServiceArea(enContent, localized);
  }

  return withServiceAreaDefaults(merged);
}
