import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { SUCCESS_STORIES } from "@/lib/seo/content/success-stories";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { successStorySlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "success-stories",
    "Merchant success stories | Porterchain",
    "How coffee roasters, pharmacies, and beauty brands scale delivery with Porterchain."
  );
}

export default async function SuccessStoriesHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title="Success stories"
        description="Real outcomes from merchants who partnered with Porterchain for local delivery."
        items={SUCCESS_STORIES.map((s) => ({
          href: successStorySlug(loc, s.slug),
          title: s.title,
          description: s.description,
        }))}
        ctaSource="success-stories"
      />
    </CorporateShell>
  );
}
