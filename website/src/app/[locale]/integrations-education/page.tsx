import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { INTEGRATIONS_EDUCATION_PAGES } from "@/lib/seo/content/integrations-education";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { integrationsEducationSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "integrations-education",
    "Integrations education | Porterchain",
    "CSV uploads, API order ingestion, EDI-ready workflows, and operational setup for merchants."
  );
}

export default async function IntegrationsEducationHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title="Integrations education"
        description="Connect your order flow to Porterchain — CSV, API, and operational setup guides."
        items={INTEGRATIONS_EDUCATION_PAGES.map((p) => ({
          href: integrationsEducationSlug(loc, p.slug),
          title: p.title,
          description: p.description,
        }))}
        ctaSource="integrations-education"
      />
    </CorporateShell>
  );
}
