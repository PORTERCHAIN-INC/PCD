/**
 * City-level vehicle and delivery-intent page content.
 * Template substitution for bilingual city×segment SEO pages.
 */

import { getServiceAreaConfig } from "./seo-content/service-areas";
import { isValidServiceAreaSlug } from "./service-areas";
import { getServiceAreaMessageKey } from "./service-areas";
import type { CityIndustryContent } from "./city-industry-delivery";

type SegmentLabels = {
  segmentLabel: string;
  cityLabel: string;
  region: string;
};

type LocalSegmentMessages = {
  cityLocalSegment?: {
    vehicleLabels?: Record<string, string>;
    intentLabels?: Record<string, string>;
    vehicle?: SegmentTemplateBlock;
    intent?: SegmentTemplateBlock;
    coverage?: { titlePattern?: string; descriptionPattern?: string };
    inquiry?: { headingPattern?: string };
    cta?: { primary?: string; secondary?: string };
    operationalFit?: {
      title?: string;
      description?: string;
      step1Title?: string;
      step1Description?: string;
      step2Title?: string;
      step2Description?: string;
      step3Title?: string;
      step3Description?: string;
    };
  };
  vehicleDelivery?: Record<
    string,
    {
      useCases?: string;
      whoFor?: string;
      volumeSuitability?: string;
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

type SegmentTemplateBlock = {
  meta?: { titlePattern?: string; descriptionPattern?: string };
  hero?: { titlePattern?: string; subtitlePattern?: string };
  localChallenges?: {
    titlePattern?: string;
    item1?: string;
    item2?: string;
    item3?: string;
  };
  localIntro?: { paragraph1?: string; paragraph2?: string };
  industryRelevance?: {
    titlePattern?: string;
    descriptionPattern?: string;
    bullet1?: string;
    bullet2?: string;
    bullet3?: string;
  };
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
  cta?: { titlePattern?: string; descriptionPattern?: string };
};

const PLACEHOLDERS = ["segmentLabel", "cityLabel", "region"] as const;

function substitute(template: string | undefined, labels: SegmentLabels): string {
  if (!template) return "";
  let out = template;
  for (const key of PLACEHOLDERS) {
    out = out.replace(new RegExp(`\\{${key}\\}`, "g"), labels[key] ?? "");
  }
  return out;
}

function buildFromTemplate(
  block: SegmentTemplateBlock | undefined,
  labels: SegmentLabels,
  vehicleDetail: { useCases?: string; whoFor?: string; volumeSuitability?: string } | undefined,
  onboarding:
    | {
        title?: string;
        description?: string;
        step1Title?: string;
        step1Description?: string;
        step2Title?: string;
        step2Description?: string;
        step3Title?: string;
        step3Description?: string;
      }
    | undefined,
  globalCta: { primary?: string; secondary?: string } | undefined,
  operationalFit: LocalSegmentMessages["cityLocalSegment"] | undefined,
  coverageTemplates: LocalSegmentMessages["cityLocalSegment"] | undefined,
  areaCoverage: { title?: string; description?: string } | undefined
): CityIndustryContent | null {
  if (!block?.meta?.titlePattern || !block?.hero?.titlePattern) return null;

  const bullets = [
    block.industryRelevance?.bullet1 ? substitute(block.industryRelevance.bullet1, labels) : "",
    block.industryRelevance?.bullet2 ? substitute(block.industryRelevance.bullet2, labels) : "",
    block.industryRelevance?.bullet3 ? substitute(block.industryRelevance.bullet3, labels) : "",
  ].filter(Boolean);

  const fit = operationalFit?.operationalFit;

  return {
    meta: {
      title: substitute(block.meta.titlePattern, labels),
      description: substitute(block.meta.descriptionPattern, labels),
    },
    hero: {
      title: substitute(block.hero.titlePattern, labels),
      subtitle: substitute(block.hero.subtitlePattern, labels),
    },
    localChallenges: {
      title: substitute(block.localChallenges?.titlePattern, labels),
      items: [
        substitute(block.localChallenges?.item1, labels),
        substitute(block.localChallenges?.item2, labels),
        substitute(block.localChallenges?.item3, labels),
      ].filter(Boolean),
    },
    localIntro: {
      paragraph1: substitute(block.localIntro?.paragraph1, labels),
      paragraph2: block.localIntro?.paragraph2
        ? substitute(block.localIntro.paragraph2, labels)
        : undefined,
    },
    industryRelevance: {
      title: substitute(block.industryRelevance?.titlePattern, labels),
      description: substitute(block.industryRelevance?.descriptionPattern, labels),
      bullets:
        bullets.length > 0
          ? bullets
          : [
              vehicleDetail?.useCases,
              vehicleDetail?.whoFor,
              vehicleDetail?.volumeSuitability,
            ].filter((b): b is string => Boolean(b)),
    },
    operationalFit: {
      title: fit?.title ? substitute(fit.title, labels) : "",
      description: fit?.description ? substitute(fit.description, labels) : undefined,
      steps: [
        {
          title: fit?.step1Title
            ? substitute(fit.step1Title, labels)
            : (onboarding?.step1Title ?? ""),
          description: fit?.step1Description
            ? substitute(fit.step1Description, labels)
            : (onboarding?.step1Description ?? ""),
        },
        {
          title: fit?.step2Title
            ? substitute(fit.step2Title, labels)
            : (onboarding?.step2Title ?? ""),
          description: fit?.step2Description
            ? substitute(fit.step2Description, labels)
            : (onboarding?.step2Description ?? ""),
        },
        {
          title: fit?.step3Title
            ? substitute(fit.step3Title, labels)
            : (onboarding?.step3Title ?? ""),
          description: fit?.step3Description
            ? substitute(fit.step3Description, labels)
            : (onboarding?.step3Description ?? ""),
        },
      ],
    },
    coverage: {
      title: areaCoverage?.title
        ? substitute(areaCoverage.title, labels)
        : substitute(coverageTemplates?.coverage?.titlePattern, labels),
      description: areaCoverage?.description
        ? substitute(areaCoverage.description, labels)
        : substitute(coverageTemplates?.coverage?.descriptionPattern, labels),
    },
    onboarding: {
      title: onboarding?.title ?? "",
      description: onboarding?.description ?? "",
      steps: [
        {
          title: onboarding?.step1Title ?? "",
          description: onboarding?.step1Description ?? "",
        },
        {
          title: onboarding?.step2Title ?? "",
          description: onboarding?.step2Description ?? "",
        },
        {
          title: onboarding?.step3Title ?? "",
          description: onboarding?.step3Description ?? "",
        },
      ],
    },
    faq: {
      title: substitute(block.faq?.titlePattern, labels) || "",
      items: [
        { question: substitute(block.faq?.q1, labels), answer: substitute(block.faq?.a1, labels) },
        { question: substitute(block.faq?.q2, labels), answer: substitute(block.faq?.a2, labels) },
        { question: substitute(block.faq?.q3, labels), answer: substitute(block.faq?.a3, labels) },
        ...(block.faq?.q4 && block.faq?.a4
          ? [
              {
                question: substitute(block.faq.q4, labels),
                answer: substitute(block.faq.a4, labels),
              },
            ]
          : []),
      ].filter((item) => item.question && item.answer),
    },
    cta: {
      title: substitute(block.cta?.titlePattern, labels),
      description: substitute(block.cta?.descriptionPattern, labels),
      primary: globalCta?.primary ?? "",
      secondary: globalCta?.secondary ?? "",
    },
    inquiry: {
      heading: substitute(coverageTemplates?.inquiry?.headingPattern, labels),
    },
  };
}

export function getCityLocalSegmentContent(
  segmentType: "vehicle" | "delivery-intent",
  segmentMessageKey: string,
  serviceAreaSlug: string,
  messages: LocalSegmentMessages
): CityIndustryContent | null {
  if (!isValidServiceAreaSlug(serviceAreaSlug)) return null;

  const areaConfig = getServiceAreaConfig(serviceAreaSlug);
  if (!areaConfig) return null;

  const areaKey = getServiceAreaMessageKey(serviceAreaSlug)!;
  const t = messages.cityLocalSegment;
  if (!t) return null;

  const segmentLabel =
    segmentType === "vehicle"
      ? (t.vehicleLabels?.[segmentMessageKey] ?? segmentMessageKey)
      : (t.intentLabels?.[segmentMessageKey] ?? segmentMessageKey);

  const areaLabels = messages as {
    cityIndustryDelivery?: { areaLabels?: Record<string, string> };
  };
  const cityLabel =
    areaLabels.cityIndustryDelivery?.areaLabels?.[areaKey.replace(/-/g, "")] ?? areaConfig.label;

  const labels: SegmentLabels = {
    segmentLabel,
    cityLabel,
    region: areaConfig.region ?? areaConfig.label,
  };

  const block = segmentType === "vehicle" ? t.vehicle : t.intent;
  const vehicleDetail =
    segmentType === "vehicle" ? messages.vehicleDelivery?.[segmentMessageKey] : undefined;
  const areaContent = messages.serviceAreaLanding?.[areaKey];
  const defaultArea = messages.serviceAreaLanding?.default;
  const onboarding = areaContent?.onboarding ?? defaultArea?.onboarding;
  const areaCoverage = areaContent?.coverage ?? defaultArea?.coverage;

  if (
    !block?.meta?.titlePattern ||
    !block?.hero?.titlePattern ||
    !t.coverage?.titlePattern ||
    !t.coverage?.descriptionPattern ||
    !t.inquiry?.headingPattern ||
    !t.cta?.primary ||
    !t.cta?.secondary ||
    !t.operationalFit?.title ||
    !onboarding?.title
  ) {
    return null;
  }

  return buildFromTemplate(block, labels, vehicleDetail, onboarding, t.cta, t, t, areaCoverage);
}
