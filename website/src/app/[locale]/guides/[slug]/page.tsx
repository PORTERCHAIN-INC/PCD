import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import {
  AUTHORITY_PAGES,
  getAuthorityPageBySlug,
  buildAuthorityInternalLinks,
} from "@/lib/seo/content/authority-pages";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    for (const page of AUTHORITY_PAGES) {
      params.push({ locale, slug: page.slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const page = getAuthorityPageBySlug(slug);
  if (!page) return {};
  return buildPageMetadata(locale, `guides/${slug}`, page.title, page.description);
}

export default async function GuidePage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const page = getAuthorityPageBySlug(slug);
  if (!page) notFound();

  const loc = locale as Locale;
  const links = buildAuthorityInternalLinks(loc, page);

  return (
    <CorporateShell>
      <ContentClusterView
        locale={loc}
        ctaSource={`guides/${slug}`}
        data={{
          title: page.title,
          description: page.description,
          intro: page.intro,
          sections: page.sections,
          relatedLinks: [...links.industry, ...links.serviceAreas, ...links.extra],
        }}
      />
    </CorporateShell>
  );
}
