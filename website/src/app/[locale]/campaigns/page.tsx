import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import HubIndexView from "@/components/seo/HubIndexView";
import { CAMPAIGN_SLUGS } from "@/lib/seo/campaign-landing";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { campaignSlug } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "campaigns",
    "Campaign landing pages | Porterchain",
    "Focused landing pages for recurring delivery, coffee roasters, pharmacy, and cosmetics campaigns."
  );
}

export default async function CampaignsHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;

  return (
    <CorporateShell>
      <HubIndexView
        locale={loc}
        title="Campaigns"
        description="Conversion-focused pages for outbound, ads, and niche merchant campaigns."
        items={CAMPAIGN_SLUGS.map((slug) => ({
          href: campaignSlug(loc, slug),
          title: slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
          description: `Learn how Porterchain supports ${slug.replace(/-/g, " ")} delivery.`,
        }))}
        ctaSource="campaigns"
      />
    </CorporateShell>
  );
}
