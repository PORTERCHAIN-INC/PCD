import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { NICHE_SLUGS } from "@/lib/seo/niche-landing";
import { INDUSTRY_PAGE_LABELS } from "@/lib/seo/internal-linking";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { industrySlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "industry",
    "Construction, electrical & plumbing delivery | Porterchain Ontario",
    "Jobsite and distributor delivery for construction materials, electrical wholesalers, and plumbing supply — plus specialized delivery across Ontario."
  );
}

export default async function IndustryHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title="Industries we serve"
        description="Construction materials, electrical distribution, and plumbing supply are our primary focus — plus recurring delivery for coffee, pharmacy, cosmetics, and lab samples across Ontario."
        items={NICHE_SLUGS.map((slug) => ({
          href: industrySlug(loc, slug),
          title: INDUSTRY_PAGE_LABELS[slug] ?? slug,
          description: `Local delivery for ${INDUSTRY_PAGE_LABELS[slug] ?? slug} across the GTA and Ontario.`,
        }))}
        ctaSource="industry"
      />
    </CorporateShell>
  );
}
