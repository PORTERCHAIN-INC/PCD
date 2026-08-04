import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import TimelineSection from "@/components/corporate/sections/TimelineSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CardGridSection from "@/components/corporate/sections/CardGridSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import FaqSection from "@/components/corporate/sections/FaqSection";
import { siteImages } from "@/data/site-images";
import { collectCardItems, collectFaqItems, collectTimelineSteps } from "@/lib/corporate-content";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.platform" });
  return buildPageMetadata(locale, "platform", t("title"), t("description"));
}

export default async function PlatformPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.platform");
  const tBc = await getTranslations("corporate.breadcrumbs");

  const featureItems = [
    {
      title: t("features.items.0.title"),
      description: t("features.items.0.description"),
      icon: "layers" as const,
    },
    {
      title: t("features.items.1.title"),
      description: t("features.items.1.description"),
      icon: "map" as const,
    },
    {
      title: t("features.items.2.title"),
      description: t("features.items.2.description"),
      icon: "radio" as const,
    },
    {
      title: t("features.items.3.title"),
      description: t("features.items.3.description"),
      icon: "truck" as const,
    },
  ];

  return (
    <CorporateShell>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: tBc("platform") }]} />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="/business?from=platform#inquiry"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/business#fleet"
        variant="light-centered"
        illustration={<HeroPhoto image={siteImages.brand.dockPair} />}
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
        primaryHref="/business?from=platform#inquiry"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/compare"
        variant="gradient"
      />
      <FaqSection
        label={t("faq.label")}
        title={t("faq.title")}
        items={collectFaqItems(t, "faq.items", 4)}
      />
    </CorporateShell>
  );
}
