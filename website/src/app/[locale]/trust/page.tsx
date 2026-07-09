import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HeroSection from "@/components/corporate/sections/HeroSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";
import { localeStaticParams } from "@/lib/seo/page-helpers";
import TrustDocumentsSection from "@/components/corporate/sections/TrustDocumentsSection";
import { FileCheck, Lock, Server, Shield, Siren, Stamp } from "lucide-react";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.trust" });
  return {
    title: t("title"),
    description: t("description"),
    openGraph: { title: t("ogTitle"), description: t("ogDescription") },
  };
}

export default async function TrustPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.trust");
  const tBc = await getTranslations("corporate.breadcrumbs");

  const featureItems = [
    {
      title: t("features.items.0.title"),
      description: t("features.items.0.description"),
      icon: Shield,
    },
    {
      title: t("features.items.1.title"),
      description: t("features.items.1.description"),
      icon: Lock,
    },
    {
      title: t("features.items.2.title"),
      description: t("features.items.2.description"),
      icon: FileCheck,
    },
    {
      title: t("features.items.3.title"),
      description: t("features.items.3.description"),
      icon: Server,
    },
    {
      title: t("features.items.4.title"),
      description: t("features.items.4.description"),
      icon: Stamp,
    },
    {
      title: t("features.items.5.title"),
      description: t("features.items.5.description"),
      icon: Siren,
    },
  ];

  return (
    <CorporateShell>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: tBc("trust") }]} />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="mailto:security@porterchain.com"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/trust/sla"
        variant="light-centered"
      />
      <section className="site-section bg-gray-bg">
        <Container>
          <SectionHeader
            label={t("summary.label")}
            title={t("summary.title")}
            subtitle={t("summary.subtitle")}
          />
        </Container>
      </section>
      <FeatureSection
        label={t("features.label")}
        title={t("features.title")}
        items={featureItems}
        variant="grid"
      />
      <TrustDocumentsSection />
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="mailto:security@porterchain.com"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/contact?intent=quote"
        variant="gradient"
      />
    </CorporateShell>
  );
}
