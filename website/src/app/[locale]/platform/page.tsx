import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import TimelineSection from "@/components/corporate/sections/TimelineSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CardGridSection from "@/components/corporate/sections/CardGridSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import { RelatedResourcesSection } from "@/components/corporate/sections/CardGridSection";
import { siteImages } from "@/data/site-images";
import {
  collectCardItems,
  collectFaqItems,
  collectResourceItems,
  collectTimelineSteps,
} from "@/lib/corporate-content";
import { Layers, Map, Radio, Truck } from "lucide-react";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.platform" });
  return {
    title: t("title"),
    description: t("description"),
    openGraph: { title: t("ogTitle"), description: t("ogDescription") },
  };
}

export default async function PlatformPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.platform");

  const featureItems = [
    {
      title: t("features.items.0.title"),
      description: t("features.items.0.description"),
      icon: Layers,
    },
    {
      title: t("features.items.1.title"),
      description: t("features.items.1.description"),
      icon: Map,
    },
    {
      title: t("features.items.2.title"),
      description: t("features.items.2.description"),
      icon: Radio,
    },
    {
      title: t("features.items.3.title"),
      description: t("features.items.3.description"),
      icon: Truck,
    },
  ];

  return (
    <CorporateShell>
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="/contact"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/integrations"
        variant="light-centered"
        illustration={<HeroPhoto image={siteImages.hero.logistics} />}
      />
      <TimelineSection
        label={t("timeline.label")}
        title={t("timeline.title")}
        subtitle={t("timeline.subtitle")}
        steps={collectTimelineSteps(t, "timeline.steps", 4)}
        variant="horizontal"
        className="bg-white"
      />
      <FeatureSection
        label={t("features.label")}
        title={t("features.title")}
        items={featureItems}
        variant="grid"
      />
      <CardGridSection
        label={t("cards.label")}
        title={t("cards.title")}
        subtitle={t("cards.subtitle")}
        items={collectCardItems(t, "cards.items", 4)}
        variant="mosaic"
        className="bg-gray-bg"
      />
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="/contact"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/contact"
        variant="gradient"
      />
      <FaqSection
        label={t("faq.label")}
        title={t("faq.title")}
        items={collectFaqItems(t, "faq.items", 4)}
      />
      <RelatedResourcesSection
        label={t("resources.label")}
        title={t("resources.title")}
        items={collectResourceItems(t, "resources.items", 3)}
      />
    </CorporateShell>
  );
}
