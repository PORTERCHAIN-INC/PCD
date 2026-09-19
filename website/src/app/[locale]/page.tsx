import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import SiteShell from "@/components/layout/SiteShell";
import HomeChooser from "@/components/home/HomeChooser";
import HomeDeliverySchema from "@/components/seo/HomeDeliverySchema";
import { routing } from "@/i18n/routing";
import { buildPageMetadata } from "@/lib/seo/page-helpers";

type Props = {
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.home" });
  return buildPageMetadata(locale, "", t("title"), t("description"));
}

export default async function HomePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <SiteShell>
      <HomeDeliverySchema />
      <HomeChooser />
    </SiteShell>
  );
}
