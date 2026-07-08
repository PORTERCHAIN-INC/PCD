import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { AUTHORITY_PAGES } from "@/lib/seo/content/authority-pages";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { guideSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "guides",
    "Local delivery guides | Porterchain",
    "Practical guides on how Porterchain works, onboarding, tracking, and support for GTA merchants."
  );
}

export default async function GuidesHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title="Guides"
        description="Educational guides that build trust and explain how local logistics works with Porterchain."
        items={AUTHORITY_PAGES.map((p) => ({
          href: guideSlug(loc, p.slug),
          title: p.title,
          description: p.description,
        }))}
        ctaSource="guides"
      />
    </CorporateShell>
  );
}
