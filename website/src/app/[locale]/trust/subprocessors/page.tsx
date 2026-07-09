import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HeroSection from "@/components/corporate/sections/HeroSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import { localeStaticParams } from "@/lib/seo/page-helpers";
import { Cloud, CreditCard, KeyRound, Mail, Map, BarChart3 } from "lucide-react";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.subprocessors" });
  return {
    title: t("title"),
    description: t("description"),
    openGraph: { title: t("ogTitle"), description: t("ogDescription") },
  };
}

export default async function SubprocessorsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.trust.subprocessors");
  const tBc = await getTranslations("corporate.breadcrumbs");

  const icons = [KeyRound, CreditCard, Cloud, Mail, Map, BarChart3] as const;
  const items = icons.map((icon, i) => ({
    title: t(`list.items.${i}.title`),
    description: t(`list.items.${i}.description`),
    icon,
  }));

  return (
    <CorporateShell>
      <PageBreadcrumbs
        items={[
          { label: tBc("home"), href: "/" },
          { label: tBc("trust"), href: "/trust" },
          { label: t("hero.badge") },
        ]}
      />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("cta.primary")}
        primaryHref="mailto:security@porterchain.com"
        secondaryCta={t("cta.secondary")}
        secondaryHref="/trust"
        variant="light-centered"
      />
      <FeatureSection
        label={t("list.label")}
        title={t("list.title")}
        items={items}
        variant="grid"
        className="bg-gray-bg"
      />
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="mailto:security@porterchain.com"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/trust"
        variant="gradient"
      />
    </CorporateShell>
  );
}
