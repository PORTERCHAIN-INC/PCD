import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { getTranslations } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import VehiclePartnerLandingView from "@/components/vehicle-partner/VehiclePartnerLandingView";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "vehiclePartner" });
  return buildPageMetadata(locale, "vehicle-partner", t("meta.title"), t("meta.description"));
}

export default async function VehiclePartnerPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <CorporateShell>
      <VehiclePartnerLandingView locale={locale as Locale} />
    </CorporateShell>
  );
}
