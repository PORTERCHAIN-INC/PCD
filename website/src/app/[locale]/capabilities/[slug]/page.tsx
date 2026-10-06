import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import ContentViewBeacon from "@/components/seo/ContentViewBeacon";
import { JsonLd } from "@/components/seo";
import { buildCapabilityInternalLinks } from "@/lib/seo/content/capabilities";
import { buildArticleSchema } from "@/lib/seo/schema";
import { siteConfig } from "@/lib/seo/config";
import {
  getLocalizedCapability,
  hasProgrammaticLocale,
  listLocalizedCapabilitySlugs,
} from "@/lib/seo/programmatic-content";
import { ensureStaticParams } from "@/lib/seo/ensure-static-params";
import { buildProgrammaticPageMetadata } from "@/lib/seo/page-helpers";
import { capabilitySlug } from "@/lib/seo/routes";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export async function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    const slugs = await listLocalizedCapabilitySlugs(locale as Locale);
    for (const slug of slugs) {
      params.push({ locale, slug });
    }
  }
  return ensureStaticParams(params, { locale: routing.locales[0]!, slug: "__build__" });
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const page = await getLocalizedCapability(locale as Locale, slug);
  if (!page) return {};
  const localized = await hasProgrammaticLocale(locale, "capabilities", slug);
  return buildProgrammaticPageMetadata(
    locale,
    `capabilities/${slug}`,
    page.title,
    page.description,
    localized
  );
}

export default async function CapabilityPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const page = await getLocalizedCapability(locale as Locale, slug);
  if (!page) notFound();

  const loc = locale as Locale;
  const links = buildCapabilityInternalLinks(loc, page, capabilitySlug);
  const url = `${siteConfig.baseUrl.replace(/\/$/, "")}/${loc}/capabilities/${slug}`;

  return (
    <CorporateShell>
      <ContentViewBeacon kind="guide" slug={slug} source={`capabilities/${slug}`} />
      <JsonLd
        data={buildArticleSchema({
          headline: page.title,
          description: page.description,
          url,
          authorPerson: {
            name: "PorterChain Operations",
            jobTitle: "Network Operations",
          },
        })}
      />
      <ContentClusterView
        locale={loc}
        ctaSource={`capabilities/${slug}`}
        data={{
          title: page.title,
          description: page.description,
          intro: page.intro,
          sections: page.sections,
          relatedLinks: [
            ...links.industry,
            ...links.serviceAreas,
            ...links.extra,
            ...links.cluster,
          ],
        }}
      />
    </CorporateShell>
  );
}
