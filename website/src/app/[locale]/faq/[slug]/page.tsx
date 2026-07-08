import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import {
  FAQ_CLUSTERS,
  getFaqClusterBySlug,
  buildFaqClusterInternalLinks,
} from "@/lib/seo/content/faq-clusters";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    for (const cluster of FAQ_CLUSTERS) {
      params.push({ locale, slug: cluster.slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const cluster = getFaqClusterBySlug(slug);
  if (!cluster) return {};
  return buildPageMetadata(locale, `faq/${slug}`, cluster.title, cluster.description);
}

export default async function FaqClusterPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const cluster = getFaqClusterBySlug(slug);
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
