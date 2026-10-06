import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import { buildFaqClusterInternalLinks } from "@/lib/seo/content/faq-clusters";
import {
  getLocalizedFaqCluster,
  hasProgrammaticLocale,
  listLocalizedFaqSlugs,
} from "@/lib/seo/programmatic-content";
import { ensureStaticParams } from "@/lib/seo/ensure-static-params";
import { buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export async function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    const slugs = await listLocalizedFaqSlugs(locale as Locale);
    for (const slug of slugs) {
      params.push({ locale, slug });
    }
  }
  return ensureStaticParams(params, { locale: routing.locales[0]!, slug: "__build__" });
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const cluster = await getLocalizedFaqCluster(locale as Locale, slug);
  if (!cluster) return {};
  const localized = await hasProgrammaticLocale(locale, "faq", slug);
  return buildProgrammaticPageMetadata(
    locale,
    `faq/${slug}`,
    cluster.title,
    cluster.description,
    localized
  );
}

export default async function FaqClusterPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const cluster = await getLocalizedFaqCluster(locale as Locale, slug);
  if (!cluster) notFound();

  const loc = locale as Locale;
  const links = buildFaqClusterInternalLinks(loc, cluster);
  const relatedLinks = [...links.industry, ...links.serviceAreas, ...links.extra];

  return (
    <CorporateShell>
      <ContentClusterView
        locale={loc}
        ctaSource={`faq/${slug}`}
        data={{
          title: cluster.title,
          description: cluster.description,
          intro: cluster.intro,
          items: cluster.items,
          relatedLinks,
          relatedTitle: "Related industries and service areas",
        }}
      />
    </CorporateShell>
  );
}
