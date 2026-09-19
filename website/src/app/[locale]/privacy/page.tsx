import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import LegalDocument from "@/components/corporate/sections/LegalDocument";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "legal.privacy.metadata" });
  return buildPageMetadata(locale, "privacy", t("title"), t("description"));
}

export default async function PrivacyPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <CorporateShell>
      <LegalDocument pageId="privacy" />
    </CorporateShell>
  );
}
