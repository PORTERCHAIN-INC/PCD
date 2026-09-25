import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import MarketingHero from "@/components/marketing/MarketingHero";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import SectionHeader from "@/components/ui/SectionHeader";
import Container from "@/components/ui/Container";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";
import TrustDocumentsSection from "@/components/corporate/sections/TrustDocumentsSection";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.trust" });
  return buildPageMetadata(locale, "trust", t("title"), t("description"));
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
      icon: "shield" as const,
    },
    {
      title: t("features.items.1.title"),
      description: t("features.items.1.description"),
      icon: "lock" as const,
    },
    {
      title: t("features.items.2.title"),
      description: t("features.items.2.description"),
      icon: "fileCheck" as const,
    },
    {
      title: t("features.items.3.title"),
      description: t("features.items.3.description"),
      icon: "server" as const,
    },
    {
      title: t("features.items.4.title"),
      description: t("features.items.4.description"),
      icon: "stamp" as const,
    },
    {
      title: t("features.items.5.title"),
      description: t("features.items.5.description"),
      icon: "siren" as const,
    },
  ];

  return (
    <CorporateShell>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: tBc("trust") }]} />
      <MarketingHero
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="mailto:enterprise@porterchain.com"
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
        secondaryHref="/sign-up?intent=quote&from=business"
        variant="gradient"
      />
    </CorporateShell>
  );
}
