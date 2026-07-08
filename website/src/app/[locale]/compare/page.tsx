import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { COMPARISON_PAGES } from "@/lib/seo/content/comparison-pages";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { compareSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "compare",
    "Compare delivery options | Porterchain",
    "Compare Porterchain with in-house delivery, ad hoc couriers, and spreadsheet dispatch."
  );
}

export default async function CompareHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title="Compare delivery options"
        description="See how managed delivery with Porterchain compares to common alternatives — without the hype."
        items={COMPARISON_PAGES.map((p) => ({
          href: compareSlug(loc, p.slug),
          title: p.title,
          description: p.description,
        }))}
        ctaSource="compare"
      />
    </CorporateShell>
  );
}
