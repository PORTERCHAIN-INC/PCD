import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HeroSection from "@/components/corporate/sections/HeroSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { siteImages } from "@/data/site-images";
import { localeStaticParams } from "@/lib/seo/page-helpers";
import { Headphones, KeyRound, Plug, ShieldCheck, Target, Users } from "lucide-react";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.enterprise" });
  return {
    title: t("title"),
    description: t("description"),
    openGraph: { title: t("ogTitle"), description: t("ogDescription") },
  };
}

export default async function EnterprisePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.enterprise");
  const tBc = await getTranslations("corporate.breadcrumbs");

  const featureItems = [
    {
      title: t("features.items.0.title"),
      description: t("features.items.0.description"),
      icon: KeyRound,
    },
    {
      title: t("features.items.1.title"),
      description: t("features.items.1.description"),
      icon: Headphones,
    },
    {
      title: t("features.items.2.title"),
      description: t("features.items.2.description"),
      icon: Target,
    },
    {
      title: t("features.items.3.title"),
      description: t("features.items.3.description"),
      icon: Users,
    },
    {
      title: t("features.items.4.title"),
      description: t("features.items.4.description"),
      icon: ShieldCheck,
    },
    {
      title: t("features.items.5.title"),
      description: t("features.items.5.description"),
      icon: Plug,
    },
  ];

  return (
    <CorporateShell>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: tBc("enterprise") }]} />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="/contact?intent=quote&from=enterprise"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/trust"
        variant="light-centered"
        illustration={<HeroPhoto image={siteImages.hero.logistics} />}
      />
      <FeatureSection
        label={t("features.label")}
        title={t("features.title")}
        items={featureItems}
        variant="grid"
        className="bg-gray-bg"
      />
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="/contact?intent=quote&from=enterprise"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/compare"
        variant="gradient"
      />
    </CorporateShell>
  );
}
