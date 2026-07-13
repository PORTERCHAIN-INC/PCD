import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import { buildComparisonInternalLinks } from "@/lib/seo/content/comparison-pages";
import {
  getLocalizedComparison,
  hasProgrammaticLocale,
  listLocalizedComparisonSlugs,
} from "@/lib/seo/programmatic-content";
import { buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export async function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    const slugs = await listLocalizedComparisonSlugs(locale as Locale);
    for (const slug of slugs) {
      params.push({ locale, slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const page = await getLocalizedComparison(locale as Locale, slug);
  if (!page) return {};
  const localized = await hasProgrammaticLocale(locale, "compare", slug);
  return buildProgrammaticPageMetadata(
    locale,
    `compare/${slug}`,
    page.title,
    page.description,
    localized
  );
}

export default async function ComparePage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const page = await getLocalizedComparison(locale as Locale, slug);
  if (!page) notFound();

  const loc = locale as Locale;
  const links = buildComparisonInternalLinks(loc, page);

  return (
    <CorporateShell>
      <ContentClusterView
        locale={loc}
        ctaSource={`compare/${slug}`}
        data={{
          title: page.title,
          description: page.description,
          intro: page.intro,
          alternativeLabel: page.alternativeLabel,
          comparisonRows: page.comparisonRows,
          relatedLinks: [...links.industry, ...links.serviceAreas, ...links.extra],
        }}
      />
    </CorporateShell>
  );
}
