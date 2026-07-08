import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import IndustryLandingView from "@/components/seo/IndustryLandingView";
import {
  CAMPAIGN_SLUGS,
  getCampaignMessageKey,
  isValidCampaignSlug,
} from "@/lib/seo/campaign-landing";
import { getLandingContent } from "@/lib/seo/landing-content";
import { buildLocalDeliveryCityLinks } from "@/lib/seo/internal-linking";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { CAMPAIGN_KEY_TO_NICHE_SLUG } from "@/lib/seo/industry-home-links";
import { industrySlug } from "@/lib/seo/routes";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    for (const slug of CAMPAIGN_SLUGS) {
      params.push({ locale, slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!isValidCampaignSlug(slug)) return {};
  const key = getCampaignMessageKey(slug);
  const campaign = await getLandingContent(locale, "campaignLanding", key ?? "");
  if (!campaign?.meta) return {};
  return buildPageMetadata(
    locale,
    `campaigns/${slug}`,
    campaign.meta.title ?? "",
    campaign.meta.description ?? ""
  );
}

export default async function CampaignPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  if (!isValidCampaignSlug(slug)) notFound();

  const key = getCampaignMessageKey(slug);
  if (!key) notFound();

  const campaign = await getLandingContent(locale, "campaignLanding", key);
  if (!campaign) notFound();

  const loc = locale as Locale;
  const industryNiche = CAMPAIGN_KEY_TO_NICHE_SLUG[key];
  const cityLinks = industryNiche
    ? [{ href: industrySlug(loc, industryNiche), label: "Industry page" }]
    : [];

  return (
    <CorporateShell>
      <IndustryLandingView
        locale={loc}
        slug={`campaigns/${slug}`}
        niche={campaign}
        cityLinks={cityLinks}
        localCityLinks={buildLocalDeliveryCityLinks(loc)}
      />
    </CorporateShell>
  );
}
