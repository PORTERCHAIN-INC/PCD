import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { routing } from "@/i18n/routing";
import { publicEnv } from "@/lib/env";
import AppClerkProvider from "@/components/providers/AppClerkProvider";
import ZohoSalesIQ from "@/components/integrations/ZohoSalesIQ";
import AttributionCapture from "@/components/seo/AttributionCapture";
import GoogleAnalytics from "@/components/seo/GoogleAnalytics";
import { JsonLd } from "@/components/seo";
import { siteConfig } from "@/lib/seo/config";
import { buildOrganizationSchema, buildLocalBusinessSchema } from "@/lib/seo/schema";
import "../globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
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
  const t = await getTranslations({ locale, namespace: "metadata" });

  const alternateLocale = locale === "en" ? "fr" : "en";
  const googleVerification = publicEnv.googleSiteVerification;

  return {
    title: t("title"),
    description: t("description"),
    metadataBase: new URL(siteConfig.baseUrl),
    ...(googleVerification ? { verification: { google: googleVerification } } : {}),
    keywords: [
      "Construction Material Delivery GTA",
      "Jobsite Delivery Toronto",
      "Electrical Distributor Delivery",
      "Plumbing Supply Delivery Ontario",
      "Building Supply Courier",
      "Livraison matériaux construction",
      "Livraison chantier Toronto",
      "Local Delivery GTA",
      "Same Day Delivery Toronto",
      "Porterchain",
    ],
    openGraph: {
      title: t("ogTitle"),
      description: t("ogDescription"),
      type: "website",
      locale: locale === "fr" ? "fr_CA" : "en_CA",
      alternateLocale: [alternateLocale === "fr" ? "fr_CA" : "en_CA"],
    },
    alternates: {
      canonical: `/${locale}`,
      languages: {
        en: "/en",
        fr: "/fr",
      },
    },
    robots: {
      index: true,
      follow: true,
    },
  };
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <html lang={locale} className={`${inter.variable} scroll-smooth`}>
      <body className="min-h-screen bg-white font-sans antialiased">
        <JsonLd data={[buildOrganizationSchema(), buildLocalBusinessSchema()]} />
        <AppClerkProvider>
          <NextIntlClientProvider messages={messages}>{children}</NextIntlClientProvider>
          <ZohoSalesIQ />
          <GoogleAnalytics />
          <AttributionCapture />
        </AppClerkProvider>
      </body>
    </html>
  );
}
