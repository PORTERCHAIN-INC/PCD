import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import HeroSection from "@/components/corporate/sections/HeroSection";
import CardGridSection from "@/components/corporate/sections/CardGridSection";
import CustomersPageCloser from "@/components/customers/CustomersPageCloser";
import { collectCardItems } from "@/lib/corporate-content";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.customers" });
  return buildPageMetadata(locale, "customers", t("title"), t("description"));
}

export default async function CustomersPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("corporate.customers");
  const tBc = await getTranslations("corporate.breadcrumbs");

  return (
    <CorporateShell>
      <PageBreadcrumbs items={[{ label: tBc("home"), href: "/" }, { label: tBc("customers") }]} />
      <HeroSection
        badge={t("hero.badge")}
        title={t("hero.title")}
        subtitle={t("hero.subtitle")}
        primaryCta={t("hero.primaryCta")}
        primaryHref="/sign-up?intent=quote&from=business"
        secondaryCta={t("hero.secondaryCta")}
        secondaryHref="/business#fleet"
        variant="light-centered"
      />
      <CardGridSection
        label={t("metrics.label")}
        title={t("metrics.title")}
        items={collectCardItems(t, "metrics.items", 3)}
        variant="mosaic"
        className="bg-gray-bg"
      />
      <CustomersPageCloser />
    </CorporateShell>
  );
}
