import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import ContentViewBeacon from "@/components/seo/ContentViewBeacon";
import { JsonLd } from "@/components/seo";
import { buildAuthorityInternalLinks } from "@/lib/seo/content/authority-pages";
import { buildArticleSchema, buildHowToSchema } from "@/lib/seo/schema";
import { siteConfig } from "@/lib/seo/config";
import {
  getLocalizedAuthorityPage,
  hasProgrammaticLocale,
  listLocalizedGuideSlugs,
} from "@/lib/seo/programmatic-content";
import { buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };
const CANONICAL_HOW_IT_WORKS_SLUG = "how-porterchain-works";

export async function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    const slugs = await listLocalizedGuideSlugs(locale as Locale);
    for (const slug of slugs) {
      params.push({ locale, slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const page = await getLocalizedAuthorityPage(locale as Locale, slug);
  if (!page) return {};
  const localized = await hasProgrammaticLocale(locale, "guides", slug);
  return buildProgrammaticPageMetadata(
    locale,
    `guides/${slug}`,
    page.title,
    page.description,
    localized
  );
}

export default async function GuidePage({ params }: Props) {
  const { locale, slug } = await params;
  if (slug === CANONICAL_HOW_IT_WORKS_SLUG) {
    redirect(`/${locale}/${CANONICAL_HOW_IT_WORKS_SLUG}`);
  }
  setRequestLocale(locale);
  const page = await getLocalizedAuthorityPage(locale as Locale, slug);
  if (!page) notFound();

  const loc = locale as Locale;
  const links = buildAuthorityInternalLinks(loc, page);
  const guideUrl = `${siteConfig.baseUrl.replace(/\/$/, "")}/${loc}/guides/${slug}`;
  const howTo =
    page.sections?.length >= 2
      ? buildHowToSchema({
          name: page.title,
          description: page.description,
          steps: page.sections.map((s) => ({ name: s.heading, text: s.body })),
        })
      : null;

  return (
    <CorporateShell>
      <ContentViewBeacon kind="guide" slug={slug} source={`guides/${slug}`} />
      <JsonLd
        data={[
          buildArticleSchema({
            headline: page.title,
            description: page.description,
            url: guideUrl,
            authorPerson: {
              name: "PorterChain Operations",
              jobTitle: "Network Operations",
            },
          }),
          howTo,
        ].filter(Boolean)}
      />
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
