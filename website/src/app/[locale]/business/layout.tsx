import type { Metadata } from "next";
import { Carlito } from "next/font/google";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { hasLocale } from "next-intl";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";
import { buildAlternateLanguages } from "@/lib/seo/hreflang";

const brand = Carlito({
  subsets: ["latin"],
  weight: ["400", "700"],
  display: "swap",
  variable: "--font-brand",
});

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "businessPage.metadata" });

  return {
    title: t("title"),
    description: t("description"),
    openGraph: {
      title: t("ogTitle"),
      description: t("ogDescription"),
      type: "website",
      locale: locale === "fr" ? "fr_CA" : "en_CA",
    },
    alternates: {
      canonical: `/${locale}/business`,
      // Same hreflang set as every other page (en, fr-CA, x-default) — audit #14.
      languages: buildAlternateLanguages(locale as (typeof routing.locales)[number], "business"),
    },
    robots: { index: true, follow: true },
  };
}

export default async function BusinessLayout({ children, params }: Props) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <div className={`business-theme ${brand.variable} font-[family-name:var(--font-brand)]`}>
      {children}
    </div>
  );
}
