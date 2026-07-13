import { getMessages } from "next-intl/server";

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

/** Publication gate for localized service-area pages; fallback copy remains usable but noindex. */
export function isPublishableServiceArea(
  content: Partial<ServiceAreaContent> | undefined
): boolean {
  return Boolean(
    content?.meta?.title &&
    content.meta.description &&
    content.hero?.title &&
    content.hero.subtitle &&
    content.coverage?.title &&
    content.coverage.description &&
    content.onboarding?.title &&
    content.onboarding.description &&
    content.onboarding.step1Title &&
    content.onboarding.step1Description &&
    content.onboarding.step2Title &&
    content.onboarding.step2Description &&
    content.onboarding.step3Title &&
    content.onboarding.step3Description &&
    content.faq?.title &&
    content.faq.q1 &&
    content.faq.a1 &&
    content.faq.q2 &&
    content.faq.a2 &&
    content.cta?.title &&
    content.cta.description &&
    content.cta.primary
  );
}

function withServiceAreaDefaults(content: Partial<ServiceAreaContent>): ServiceAreaContent | null {
  if (!content.hero?.title || !content.hero?.subtitle) return null;

  const areaLabel = content.hero.title.replace(/^Delivery in /i, "").replace(/^Livraison à /i, "");

  return {
    meta: content.meta,
    hero: content.hero,
    coverage: content.coverage ?? {
      title: `Coverage — ${areaLabel}`,
      description: `We deliver across ${areaLabel} with the same reliability and local operations for your business.`,
    },
    onboarding: content.onboarding ?? {
      title: "Simple onboarding",
      description: "Get set up for local delivery without the fleet headache.",
      step1Title: "Connect",
      step1Description:
        "Share your volume and service areas. We align capacity and service expectations.",
      step2Title: "We deliver",
      step2Description:
        "Our drivers pick up and deliver across your zones. Live tracking in one dashboard.",
      step3Title: "You stay in control",
      step3Description: "Track every parcel, see ETAs, and get clear reporting.",
    },
    faq: content.faq ?? {
      title: `Frequently asked questions — ${areaLabel}`,
      q1: `Do you deliver across ${areaLabel}?`,
      a1: "Yes. Share your zones or postal codes and we'll confirm coverage and capacity.",
      q2: "How quickly can we get started?",
      a2: "Share your volume and routes. We align capacity and can have you shipping within days.",
      q3: "Can my customers track their delivery?",
      a3: "Every shipment gets a tracking link with real-time status and ETA.",
    },
    cta: content.cta ?? {
      title: `Ready for reliable delivery in ${areaLabel}?`,
      description:
        "Tell us your volume and routes. We'll show you how we can run your recurring delivery.",
      primary: "Get a quote",
      secondary: "Contact us",
    },
  };
}

function mergeServiceArea(
  base: Partial<ServiceAreaContent> | undefined,
  override: Partial<ServiceAreaContent> | undefined
): Partial<ServiceAreaContent> {
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
    onboarding: override.onboarding ?? base.onboarding,
    faq: override.faq ?? base.faq,
    cta: override.cta ?? base.cta,
  };
}

/** Load service area copy with EN fallback and defaults for partial FR translations. */
export async function getServiceAreaContent(
  locale: string,
  messageKey: string
): Promise<ServiceAreaContent | null> {
  const messages = await getMessages({ locale });
  const localized = (
    messages as { serviceAreaLanding?: Record<string, Partial<ServiceAreaContent>> }
  ).serviceAreaLanding?.[messageKey];

  let merged = localized ?? {};
  if (locale !== "en") {
    const enMessages = (await import("../../../messages/en.json")).default as {
      serviceAreaLanding?: Record<string, Partial<ServiceAreaContent>>;
    };
    const enContent = enMessages.serviceAreaLanding?.[messageKey];
    merged = mergeServiceArea(enContent, localized);
  }

  return withServiceAreaDefaults(merged);
}
