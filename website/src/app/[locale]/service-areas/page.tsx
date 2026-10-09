import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import ServiceAreasHubView from "@/components/seo/ServiceAreasHubView";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "serviceAreasIndex" });
  // FR hub is fully translated and lists the published FR area pages — index both locales.
  return buildPageMetadata(locale, "service-areas", t("meta.title"), t("meta.description"));
}

export default async function ServiceAreasHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <CorporateShell>
      <ServiceAreasHubView locale={locale as Locale} />
    </CorporateShell>
  );
}
