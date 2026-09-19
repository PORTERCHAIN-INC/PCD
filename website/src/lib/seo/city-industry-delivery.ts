/**
 * City-industry delivery page content resolution.
 * Composes niche (industry) + service area content with template substitution
 * for local intro, FAQ, and CTA. Keeps pages substantive and bilingual-safe.
 */

import { getIndustryConfig, INDUSTRY_CONFIGS } from "./seo-content/industries";
import { getServiceAreaConfig, SERVICE_AREA_CONFIGS } from "./seo-content/service-areas";
import { isValidNicheSlug } from "./niche-landing";
import { isValidServiceAreaSlug } from "./service-areas";
import { getServiceAreaMessageKey } from "./service-areas";
import { getNicheMessageKey } from "./niche-landing";

export type CityIndustryLabels = {
  industryLabel: string;
  cityLabel: string;
  region: string;
};

export type CityIndustryContent = {
  meta: { title: string; description: string };
  hero: { title: string; subtitle: string };
  localChallenges: { title: string; items: string[] };
  localIntro: { paragraph1: string; paragraph2?: string };
  industryRelevance: {
    title: string;
    description: string;
    bullets: string[];
  };
  operationalFit: {
    title: string;
    description?: string;
    steps: { title: string; description: string }[];
  };
  coverage: { title: string; description?: string };
  onboarding: {
    title: string;
    description: string;
    steps: { title: string; description: string }[];
  };
  faq: { title: string; items: { question: string; answer: string }[] };
  cta: {
    title: string;
    description: string;
    primary: string;
    secondary: string;
  };
  inquiry: { heading: string; subheadline?: string };
};

type CityIndustryOverride = {
  meta?: { title?: string; description?: string };
  hero?: { title?: string; subtitle?: string };
  localChallenges?: { title?: string; item1?: string; item2?: string; item3?: string };
  localIntro?: { paragraph1?: string; paragraph2?: string };
  faq?: {
    title?: string;
    q1?: string;
    a1?: string;
    q2?: string;
    a2?: string;
    q3?: string;
    a3?: string;
    q4?: string;
    a4?: string;
  };
  cta?: { title?: string; description?: string; primary?: string; secondary?: string };
  inquiry?: { heading?: string; subheadline?: string };
};

type MessagesShape = {
  cityIndustryDelivery?: {
    industryLabels?: Record<string, string>;
    areaLabels?: Record<string, string>;
    overrides?: Record<string, CityIndustryOverride>;
    meta?: { titlePattern?: string; descriptionPattern?: string };
    hero?: { titlePattern?: string; subtitlePattern?: string };
    localChallenges?: {
      titlePattern?: string;
      item1?: string;
      item2?: string;
      item3?: string;
    };
    localIntro?: { paragraph1?: string; paragraph2?: string };
    faq?: {
      titlePattern?: string;
      q1?: string;
      a1?: string;
      q2?: string;
      a2?: string;
      q3?: string;
      a3?: string;
      q4?: string;
      a4?: string;
    };
    cta?: {
      titlePattern?: string;
      descriptionPattern?: string;
      primary?: string;
      secondary?: string;
    };
    inquiry?: { headingPattern?: string; subheadlinePattern?: string };
  };
  nicheLanding?: Record<
    string,
    {
      solution?: {
        title?: string;
        description?: string;
        bullet1?: string;
        bullet2?: string;
        bullet3?: string;
      };
      workflow?: {
        title?: string;
        description?: string;
        step1Title?: string;
        step1Description?: string;
        step2Title?: string;
        step2Description?: string;
        step3Title?: string;
        step3Description?: string;
      };
    }
  >;
  serviceAreaLanding?: Record<
    string,
    {
      coverage?: { title?: string; description?: string };
      onboarding?: {
        title?: string;
        description?: string;
        step1Title?: string;
        step1Description?: string;
        step2Title?: string;
        step2Description?: string;
        step3Title?: string;
        step3Description?: string;
      };
    }
  >;
};

const PLACEHOLDERS = ["industryLabel", "cityLabel", "region"] as const;

function substitute(template: string | undefined, labels: CityIndustryLabels): string {
  if (!template) return "";
  let out = template;
  for (const key of PLACEHOLDERS) {
    const value = labels[key] ?? "";
    out = out.replace(new RegExp(`\\{${key}\\}`, "g"), value);
  }
  return out;
}

/**
 * Resolve full content for a city-industry delivery page.
 * Validates slugs and returns null if invalid or messages lack required blocks.
 */
export function getCityIndustryContent(
  industrySlug: string,
  serviceAreaSlug: string,
  messages: MessagesShape
): CityIndustryContent | null {
  if (!isValidNicheSlug(industrySlug) || !isValidServiceAreaSlug(serviceAreaSlug)) return null;

  const industryConfig = getIndustryConfig(industrySlug);
  const areaConfig = getServiceAreaConfig(serviceAreaSlug);
  if (!industryConfig || !areaConfig) return null;

  const industryKey = getNicheMessageKey(industrySlug)!;
  const areaKey = getServiceAreaMessageKey(serviceAreaSlug)!;
  const t = messages.cityIndustryDelivery;
  const labels: CityIndustryLabels = {
    industryLabel: t?.industryLabels?.[industryKey] ?? industryConfig.label,
    cityLabel: t?.areaLabels?.[areaKey] ?? areaConfig.label,
    region: areaConfig.region ?? areaConfig.label,
  };
  const niche = messages.nicheLanding?.[industryKey];
  const areaContent = messages.serviceAreaLanding?.[areaKey];
  const defaultArea = messages.serviceAreaLanding?.default;

  const coverage = areaContent?.coverage ?? defaultArea?.coverage;
  const onboarding = areaContent?.onboarding ?? defaultArea?.onboarding;
  if (!t?.meta?.titlePattern || !t?.hero?.titlePattern || !niche?.solution || !niche?.workflow)
    return null;
  if (!coverage?.title || !onboarding?.title) return null;
  const localChallengesTitle = t?.localChallenges?.titlePattern
    ? substitute(t.localChallenges.titlePattern, labels)
    : "";
  const localChallengesItems = [
    t?.localChallenges?.item1 ? substitute(t.localChallenges.item1, labels) : "",
    t?.localChallenges?.item2 ? substitute(t.localChallenges.item2, labels) : "",
    t?.localChallenges?.item3 ? substitute(t.localChallenges.item3, labels) : "",
  ].filter(Boolean);

  const workflowSteps = [
    {
      title: niche.workflow.step1Title ?? "",
      description: niche.workflow.step1Description ?? "",
    },
    {
      title: niche.workflow.step2Title ?? "",
      description: niche.workflow.step2Description ?? "",
    },
    {
      title: niche.workflow.step3Title ?? "",
      description: niche.workflow.step3Description ?? "",
    },
  ];
  const onboardingSteps = [
    {
      title: onboarding.step1Title ?? "",
      description: onboarding.step1Description ?? "",
    },
    {
      title: onboarding.step2Title ?? "",
      description: onboarding.step2Description ?? "",
    },
    {
      title: onboarding.step3Title ?? "",
      description: onboarding.step3Description ?? "",
    },
  ];
  const solutionBullets = [
    niche.solution.bullet1,
    niche.solution.bullet2,
    niche.solution.bullet3,
  ].filter((b): b is string => Boolean(b));

  const faqItems = [
    { question: substitute(t.faq?.q1, labels), answer: substitute(t.faq?.a1, labels) },
    { question: substitute(t.faq?.q2, labels), answer: substitute(t.faq?.a2, labels) },
    { question: substitute(t.faq?.q3, labels), answer: substitute(t.faq?.a3, labels) },
    ...(t.faq?.q4 && t.faq?.a4
      ? [{ question: substitute(t.faq.q4, labels), answer: substitute(t.faq.a4, labels) }]
      : []),
  ].filter((item) => item.question && item.answer);

  const overrideKey = `${industryKey}_${areaKey}`;
  const ov = t?.overrides?.[overrideKey];

  const content: CityIndustryContent = {
    meta: {
      title: substitute(t.meta.titlePattern, labels),
      description: substitute(t.meta.descriptionPattern, labels),
    },
    hero: {
      title: substitute(t.hero.titlePattern, labels),
      subtitle: substitute(t.hero.subtitlePattern, labels),
    },
    localChallenges: {
      title: localChallengesTitle,
      items: localChallengesItems,
    },
    localIntro: {
      paragraph1: substitute(t.localIntro?.paragraph1, labels),
      paragraph2: t.localIntro?.paragraph2
        ? substitute(t.localIntro.paragraph2, labels)
        : undefined,
    },
    industryRelevance: {
      title: niche.solution.title ?? "",
      description: niche.solution.description ?? "",
      bullets: solutionBullets,
    },
    operationalFit: {
      title: niche.workflow.title ?? "",
      description: niche.workflow.description,
      steps: workflowSteps,
    },
    coverage: {
      title: coverage.title,
      description: coverage.description,
    },
    onboarding: {
      title: onboarding.title,
      description: onboarding.description ?? "",
      steps: onboardingSteps,
    },
    faq: {
      title: substitute(t.faq?.titlePattern, labels),
      items: faqItems,
    },
    cta: {
      title: substitute(t.cta?.titlePattern, labels),
      description: substitute(t.cta?.descriptionPattern, labels),
      primary: t.cta?.primary ?? "Talk to us",
      secondary: t.cta?.secondary ?? "Contact",
    },
    inquiry: {
      heading: substitute(t.inquiry?.headingPattern, labels),
      subheadline: t.inquiry?.subheadlinePattern
        ? substitute(t.inquiry.subheadlinePattern, labels)
        : undefined,
    },
  };

  if (ov) {
    if (ov.meta?.title) content.meta.title = ov.meta.title;
    if (ov.meta?.description) content.meta.description = ov.meta.description;
    if (ov.hero?.title) content.hero.title = ov.hero.title;
    if (ov.hero?.subtitle) content.hero.subtitle = ov.hero.subtitle;
    if (ov.localChallenges?.title) content.localChallenges.title = ov.localChallenges.title;
    const ovItems = [
      ov.localChallenges?.item1,
      ov.localChallenges?.item2,
      ov.localChallenges?.item3,
    ].filter((x): x is string => Boolean(x));
    if (ovItems.length > 0) content.localChallenges.items = ovItems;
    if (ov.localIntro?.paragraph1) content.localIntro.paragraph1 = ov.localIntro.paragraph1;
    if (ov.localIntro?.paragraph2) content.localIntro.paragraph2 = ov.localIntro.paragraph2;
    if (ov.faq) {
      if (ov.faq.title) content.faq.title = ov.faq.title;
      const ovFaqItems = [
        ov.faq.q1 != null && ov.faq.a1 != null ? { question: ov.faq.q1, answer: ov.faq.a1 } : null,
        ov.faq.q2 != null && ov.faq.a2 != null ? { question: ov.faq.q2, answer: ov.faq.a2 } : null,
        ov.faq.q3 != null && ov.faq.a3 != null ? { question: ov.faq.q3, answer: ov.faq.a3 } : null,
        ov.faq.q4 != null && ov.faq.a4 != null ? { question: ov.faq.q4, answer: ov.faq.a4 } : null,
      ].filter((x): x is { question: string; answer: string } => x != null);
      if (ovFaqItems.length > 0) content.faq.items = ovFaqItems;
    }
    if (ov.cta?.title) content.cta.title = ov.cta.title;
    if (ov.cta?.description) content.cta.description = ov.cta.description;
    if (ov.cta?.primary) content.cta.primary = ov.cta.primary;
    if (ov.cta?.secondary) content.cta.secondary = ov.cta.secondary;
    if (ov.inquiry?.heading) content.inquiry.heading = ov.inquiry.heading;
    if (ov.inquiry?.subheadline) content.inquiry.subheadline = ov.inquiry.subheadline;
  }

  return content;
}

/** All valid (industrySlug, serviceAreaSlug) pairs for static generation. */
export function getCityIndustrySlugPairs(): { industrySlug: string; serviceAreaSlug: string }[] {
  const pairs: { industrySlug: string; serviceAreaSlug: string }[] = [];
  for (const ind of INDUSTRY_CONFIGS) {
    for (const area of SERVICE_AREA_CONFIGS) {
      pairs.push({ industrySlug: ind.slug, serviceAreaSlug: area.slug });
    }
  }
  return pairs;
}
