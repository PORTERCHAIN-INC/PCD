import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import { getAuthorityPageBySlug } from "@/lib/seo/content/authority-pages";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

const SLUG = "how-porterchain-works";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const page = getAuthorityPageBySlug(SLUG);
  if (!page) return {};
  return buildPageMetadata(locale, SLUG, page.title, page.description);
}

export default async function HowPorterchainWorksPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const page = getAuthorityPageBySlug(SLUG);
  if (!page) notFound();

  return (
    <CorporateShell>
      <ContentClusterView
        locale={locale as Locale}
        ctaSource={SLUG}
        data={{
          title: page.title,
          description: page.description,
          intro: page.intro,
          sections: page.sections,
        }}
      />
    </CorporateShell>
  );
}
