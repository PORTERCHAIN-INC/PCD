import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import { buildVehicleMetadata, VehicleDeliveryPageContent } from "@/lib/seo/vehicle-page";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildVehicleMetadata(locale, "suv-delivery");
}

export default async function SuvDeliveryPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <CorporateShell>
      <VehicleDeliveryPageContent locale={locale as Locale} segment="suv-delivery" />
    </CorporateShell>
  );
}
