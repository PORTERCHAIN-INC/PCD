import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import { Inter } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { routing } from "@/i18n/routing";
import { publicEnv } from "@/lib/env";
import AppClerkProvider from "@/components/providers/AppClerkProvider";
import DeferredSiteIntegrations from "@/components/integrations/DeferredSiteIntegrations";
import AttributionCapture from "@/components/seo/AttributionCapture";
import { JsonLd } from "@/components/seo";
import { siteConfig } from "@/lib/seo/config";
import { buildOrganizationSchema } from "@/lib/seo/schema";
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

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0a1628",
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "metadata" });

  const alternateLocale = locale === "en" ? "fr" : "en";
  const googleVerification = publicEnv.googleSiteVerification;
  const keywords = t.raw("keywords") as string[];

  return {
    title: t("title"),
    description: t("description"),
    metadataBase: new URL(siteConfig.baseUrl),
    ...(googleVerification ? { verification: { google: googleVerification } } : {}),
    keywords,
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
        <JsonLd data={buildOrganizationSchema()} />
        <AppClerkProvider>
          <NextIntlClientProvider messages={messages}>{children}</NextIntlClientProvider>
        </AppClerkProvider>
        <DeferredSiteIntegrations />
        <Suspense fallback={null}>
          <AttributionCapture />
        </Suspense>
      </body>
    </html>
  );
}
