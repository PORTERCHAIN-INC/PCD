import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import IndustryLandingView from "@/components/seo/IndustryLandingView";
import ContentViewBeacon from "@/components/seo/ContentViewBeacon";
import { NICHE_SLUGS, getNicheMessageKey, isValidNicheSlug } from "@/lib/seo/niche-landing";
import { getLandingContent, resolveLandingContent } from "@/lib/seo/landing-content";
import {
  buildCityDeliveryLinksForIndustryPage,
  buildLocalDeliveryCityLinks,
} from "@/lib/seo/internal-linking";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { isDraftNicheSlug } from "@/lib/seo/content/draft-expansions";
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
  const messageKey = getNicheMessageKey(slug) ?? "";
  const { content: niche, indexable } = await resolveLandingContent(
    locale,
    "nicheLanding",
    messageKey
  );
  if (!niche?.meta) return {};
  const allowIndex = indexable && !isDraftNicheSlug(slug);
  return buildPageMetadata(
    locale,
    `industry/${slug}`,
    niche.meta.title ?? "Industry delivery",
    niche.meta.description ?? "",
    { index: allowIndex }
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
  const tBc = await getTranslations("corporate.breadcrumbs");
  const tSeo = await getTranslations("corporate.seo.sectionLabels");
  const cityLinks = buildCityDeliveryLinksForIndustryPage(loc, slug, messages as never);
  const localCityLinks = buildLocalDeliveryCityLinks(loc);

  return (
    <CorporateShell>
      <ContentViewBeacon kind="industry" slug={slug} source={`industry/${slug}`} />
      <IndustryLandingView
        locale={loc}
        slug={slug}
        niche={niche}
        cityLinks={cityLinks}
        localCityLinks={localCityLinks}
        sectionLabels={{
          industries: tSeo("industries"),
          challenges: tSeo("challenges"),
          solution: tSeo("solution"),
          workflow: tSeo("workflow"),
          onboarding: tSeo("onboarding"),
          deliveryInCity: tSeo("deliveryInCity"),
          localDeliveryByCity: tSeo("localDeliveryByCity"),
          capacitySolutions: tSeo("capacitySolutions"),
          serviceAreas: tSeo("serviceAreas"),
          industryDeliveryInArea: tSeo("industryDeliveryInArea"),
          exploreByIndustry: tSeo("exploreByIndustry"),
          localDelivery: tSeo("localDelivery"),
          localChallenges: tSeo("localChallenges"),
          industryFit: tSeo("industryFit"),
          howItWorks: tSeo("howItWorks"),
          otherVehicles: tSeo("otherVehicles"),
          vehicles: tSeo("vehicles"),
          painPoints: tSeo("painPoints"),
          intentGuides: tSeo("intentGuides"),
          relatedPages: tSeo("relatedPages"),
        }}
        breadcrumbs={[
          { label: tBc("home"), href: "/" },
          { label: tBc("industry"), href: "/business#industries" },
          { label: niche.hero.title },
        ]}
      />
    </CorporateShell>
  );
}
