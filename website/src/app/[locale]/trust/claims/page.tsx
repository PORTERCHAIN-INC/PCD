import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import MarketingHero from "@/components/marketing/MarketingHero";
import FeatureSection from "@/components/marketing/corporate/sections/FeatureSection";
import MarketingCloser from "@/components/marketing/MarketingCloser";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";
import type { FeatureIconName } from "@/components/marketing/corporate/icons/feature-icons";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.claims" });
  return buildPageMetadata(locale, "trust/claims", t("title"), t("description"));
}

export default async function ClaimsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.trust.claims");
  const tCta = await getTranslations("common.cta");
  const tBc = await getTranslations("corporate.breadcrumbs");

  const icons = [
    "fileCheck",
    "map",
    "refreshCw",
    "shieldCheck",
  ] as const satisfies FeatureIconName[];
  const items = icons.map((icon, i) => ({
    title: t(`bands.items.${i}.title`),
    description: t(`bands.items.${i}.description`),
    icon,
  }));

  return (
    <CorporateShell>
      <PageBreadcrumbs
        items={[
          { label: tBc("home"), href: "/" },
          { label: tBc("trust"), href: "/trust" },
          { label: tBc("claims") },
        ]}
      />
      <MarketingHero
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={tCta("quote")}
        primaryHref="/sign-up?intent=quote&from=trust-claims"
        secondaryCta={t("cta.secondary")}
        secondaryHref="/trust"
        variant="light-centered"
      />
      <FeatureSection
        label={t("bands.label")}
        title={t("bands.title")}
        subtitle={t("bands.subtitle")}
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
      <MarketingCloser
        title={t("cta.title")}
        subtitle={t("cta.subtitle")}
        primaryLabel={tCta("quote")}
        primaryHref="/sign-up?intent=quote&from=trust-claims"
        secondaryLabel={t("cta.secondary")}
        secondaryHref="/trust"
        variant="gradient"
      />
    </CorporateShell>
  );
}
