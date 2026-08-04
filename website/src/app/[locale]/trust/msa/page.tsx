import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HeroSection from "@/components/corporate/sections/HeroSection";
import FeatureSection from "@/components/corporate/sections/FeatureSection";
import CtaSection from "@/components/corporate/sections/CtaSection";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";
import type { FeatureIconName } from "@/components/corporate/icons/feature-icons";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.msa" });
  return buildPageMetadata(locale, "trust/msa", t("title"), t("description"));
}

export default async function MsaPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.trust.msa");
  const tBc = await getTranslations("corporate.breadcrumbs");

  const icons = ["handshake", "layers", "scale", "fileCheck"] as const satisfies FeatureIconName[];
  const items = icons.map((icon, i) => ({
    title: t(`sections.items.${i}.title`),
    description: t(`sections.items.${i}.description`),
    icon,
  }));

  return (
    <CorporateShell>
      <PageBreadcrumbs
        items={[
          { label: tBc("home"), href: "/" },
          { label: tBc("trust"), href: "/trust" },
          { label: tBc("msa") },
        ]}
      />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("cta.primary")}
        primaryHref="mailto:enterprise@porterchain.com?subject=MSA%20request"
        secondaryCta={t("cta.secondary")}
        secondaryHref="/trust"
        variant="light-centered"
      />
      <FeatureSection
        label={t("sections.label")}
        title={t("sections.title")}
        subtitle={t("sections.subtitle")}
        items={items}
        variant="grid"
        className="bg-gray-bg"
      />
      <section className="site-section bg-white">
        <Container className="max-w-3xl">
          <SectionHeader title={t("note.title")} />
          <p className="mt-4 text-muted leading-relaxed">{t("note.body")}</p>
        </Container>
      </section>
      <CtaSection
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={t("cta.primary")}
        primaryHref="/business?from=trust-msa#inquiry"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/trust"
        variant="gradient"
      />
    </CorporateShell>
  );
}
