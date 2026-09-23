import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { buildVehicleMetadata } from "@/lib/seo/vehicle-page";
import { routing } from "@/i18n/routing";

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
  redirect(`/${locale}/sedan-delivery`);
}
