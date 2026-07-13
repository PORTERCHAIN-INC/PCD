import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { COMPARISON_PAGES } from "@/lib/seo/content/comparison-pages";
import {
  getLocalizedComparison,
  getProgrammaticHubCopy,
  listLocalizedComparisonSlugs,
} from "@/lib/seo/programmatic-content";
import { localeStaticParams, buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import { compareSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

const EN_HUB = {
  title: "Compare delivery options",
  description:
    "See how managed delivery with Porterchain compares to common alternatives — without the hype.",
};

const EN_META = {
  title: "Compare delivery options | Porterchain",
  description:
    "Compare Porterchain with in-house delivery, ad hoc couriers, and spreadsheet dispatch.",
};

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const hub = await getProgrammaticHubCopy(locale as Locale, "compare", EN_META);
  return buildProgrammaticPageMetadata(
    locale,
    "compare",
    hub.title,
    hub.description,
    locale === "fr"
  );
}

export default async function CompareHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;
  const slugs = new Set(await listLocalizedComparisonSlugs(loc));
  const hub = await getProgrammaticHubCopy(loc, "compare", EN_HUB);

  const pages = COMPARISON_PAGES.filter((p) => slugs.has(p.slug));
  const items = await Promise.all(
    pages.map(async (p) => {
      const page = (await getLocalizedComparison(loc, p.slug))!;
      return {
        href: compareSlug(loc, p.slug),
        title: page.title,
        description: page.description,
      };
    })
  );

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title={hub.title}
        description={hub.description}
        items={items}
        ctaSource="compare"
      />
    </CorporateShell>
  );
}
