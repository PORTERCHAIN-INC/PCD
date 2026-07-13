import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import SiteShell from "@/components/layout/SiteShell";
import Hero from "@/components/sections/Hero";
import HomeGtaMarquee from "@/components/home/HomeGtaMarquee";
import HomePlatformBody from "@/components/home/HomePlatformBody";
import HomeDeliverySchema from "@/components/seo/HomeDeliverySchema";
import { routing } from "@/i18n/routing";

type Props = {
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.metadata.home" });
  return {
    title: t("title"),
    description: t("description"),
    openGraph: { title: t("ogTitle"), description: t("ogDescription") },
  };
}

export default async function HomePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <SiteShell>
      <HomeDeliverySchema />
      <Hero locale={locale} />
      <HomeGtaMarquee />
      <HomePlatformBody />
    </SiteShell>
  );
}
