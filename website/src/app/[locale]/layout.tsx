import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { routing } from "@/i18n/routing";
import { publicEnv } from "@/lib/env";
import DeferredSiteIntegrations from "@/components/integrations/DeferredSiteIntegrations";
import AttributionCapture from "@/components/seo/AttributionCapture";
import HtmlLang from "@/components/i18n/HtmlLang";
import { JsonLd } from "@/components/seo";
import { buildOrganizationSchema, buildWebSiteSchema } from "@/lib/seo/schema";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { pickMessages } from "@/i18n/client-messages";

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0a1628",
  colorScheme: "light",
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "metadata" });
  const googleVerification = publicEnv.googleSiteVerification;
  const keywords = t.raw("keywords") as string[];
  const otherVerify: Record<string, string> = {};
  if (publicEnv.bingSiteVerification) {
    otherVerify["msvalidate.01"] = publicEnv.bingSiteVerification;
  }
  if (publicEnv.yandexSiteVerification) {
    otherVerify["yandex-verification"] = publicEnv.yandexSiteVerification;
  }
  return {
    ...buildPageMetadata(locale, "", t("title"), t("description")),
    keywords,
    ...(googleVerification || Object.keys(otherVerify).length
      ? {
          verification: {
            ...(googleVerification ? { google: googleVerification } : {}),
            ...(Object.keys(otherVerify).length ? { other: otherVerify } : {}),
          },
        }
      : {}),
  };
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);
  // Only namespaces client components use are serialised into the page (see client-messages.ts).
  const messages = pickMessages(await getMessages());

  return (
    <>
      <HtmlLang locale={locale} />
      <JsonLd data={buildOrganizationSchema()} />
      <JsonLd data={buildWebSiteSchema()} />
      {/* Server-rendered language for assistive tech + crawlers (root <html lang> is static "en"). */}
      <div lang={locale} style={{ display: "contents" }}>
        <NextIntlClientProvider messages={messages}>
          {children}
          <DeferredSiteIntegrations />
        </NextIntlClientProvider>
      </div>
      <Suspense fallback={null}>
        <AttributionCapture />
      </Suspense>
    </>
  );
}
