import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import IndustryHubView from "@/components/seo/IndustryHubView";
import { JsonLd } from "@/components/seo";
import { buildServiceSchema } from "@/lib/seo/schema";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "corporate.industriesIndex" });
  return buildPageMetadata(locale, "industry", t("meta.title"), t("meta.description"));
}

export default async function IndustryHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "corporate.industriesIndex" });

  return (
    <CorporateShell>
      <JsonLd
        data={buildServiceSchema({
          name: t("meta.title"),
          description: t("meta.description"),
        })}
      />
      <IndustryHubView locale={locale as Locale} />
    </CorporateShell>
  );
}
