import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getMessages, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import IndustryLandingView from "@/components/seo/IndustryLandingView";
import { NICHE_SLUGS, getNicheMessageKey, isValidNicheSlug } from "@/lib/seo/niche-landing";
import { getLandingContent } from "@/lib/seo/landing-content";
import {
  buildCityDeliveryLinksForIndustryPage,
  buildLocalDeliveryCityLinks,
} from "@/lib/seo/internal-linking";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; slug: string }> };

export function generateStaticParams() {
  const params: { locale: string; slug: string }[] = [];
  for (const locale of routing.locales) {
    for (const slug of NICHE_SLUGS) {
      params.push({ locale, slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!isValidNicheSlug(slug)) return {};
  const niche = await getLandingContent(locale, "nicheLanding", getNicheMessageKey(slug) ?? "");
  if (!niche?.meta) return {};
  return buildPageMetadata(
    locale,
    `industry/${slug}`,
    niche.meta.title ?? "Industry delivery",
    niche.meta.description ?? ""
  );
}

export default async function IndustrySlugPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  if (!isValidNicheSlug(slug)) notFound();

  const key = getNicheMessageKey(slug);
  if (!key) notFound();

  const niche = await getLandingContent(locale, "nicheLanding", key);
  if (!niche) notFound();

  const messages = await getMessages({ locale });
  const loc = locale as Locale;
  const cityLinks = buildCityDeliveryLinksForIndustryPage(loc, slug, messages as never);
  const localCityLinks = buildLocalDeliveryCityLinks(loc);

  return (
    <CorporateShell>
      <IndustryLandingView
        locale={loc}
        slug={slug}
        niche={niche}
        cityLinks={cityLinks}
        localCityLinks={localCityLinks}
      />
    </CorporateShell>
  );
}
