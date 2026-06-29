import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { hasLocale } from "next-intl";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
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
      languages: {
        en: "/en/business",
        fr: "/fr/business",
      },
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
    <div className={`business-theme ${inter.variable} font-[family-name:var(--font-inter)]`}>
      {children}
    </div>
  );
}
