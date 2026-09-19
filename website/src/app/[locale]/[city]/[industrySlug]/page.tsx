import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import CityIndustryLandingView from "@/components/seo/CityIndustryLandingView";
import { getCityIndustryContent } from "@/lib/seo/city-industry-delivery";
import { getCityLocalSegmentContent } from "@/lib/seo/city-local-segment-content";
import { getAllCitySegmentPairs, resolveCitySegment } from "@/lib/seo/city-segment-seo";
import { CITY_SEO_TO_SERVICE_AREA } from "@/lib/seo/city-industry-seo";
import {
  buildIndustryPageLinksForCityPage,
  buildVehicleLinksForCityPage,
} from "@/lib/seo/internal-linking";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { isPublishableCitySegment } from "@/lib/seo/city-segment-publication";
import { routing, type Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string; city: string; industrySlug: string }> };

export function generateStaticParams() {
  const pairs = getAllCitySegmentPairs();
  const params: { locale: string; city: string; industrySlug: string }[] = [];
  for (const locale of routing.locales) {
    for (const { city, segmentSlug } of pairs) {
      params.push({ locale, city, industrySlug: segmentSlug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, city, industrySlug } = await params;
  const resolved = resolveCitySegment(city, industrySlug);
  if (!resolved) return {};

  const messages = await getMessages({ locale });
  let content;
  let usesEnglishFallback = false;
  if (resolved.type === "industry") {
    content = getCityIndustryContent(
      resolved.nicheSlug,
      resolved.serviceAreaSlug,
      messages as never
    );
  } else {
    const segmentKey = resolved.type === "vehicle" ? resolved.vehicleKey : resolved.intentKey;
    content = getCityLocalSegmentContent(
      resolved.type,
      segmentKey,
      resolved.serviceAreaSlug,
      messages as never
    );
    if (!content && locale !== "en") {
      const enMessages = await getMessages({ locale: "en" });
      content = getCityLocalSegmentContent(
        resolved.type,
        segmentKey,
        resolved.serviceAreaSlug,
        enMessages as never
      );
      usesEnglishFallback = Boolean(content);
    }
  }
  if (!content) return {};

  const publishable =
    isPublishableCitySegment(locale as Locale, city, industrySlug, messages as never) &&
    !usesEnglishFallback;

  return buildPageMetadata(
    locale,
    `${city}/${industrySlug}`,
    content.meta.title,
    content.meta.description,
    { index: publishable }
  );
}

export default async function CitySegmentPage({ params }: Props) {
  const { locale, city, industrySlug } = await params;
  setRequestLocale(locale);

  const resolved = resolveCitySegment(city, industrySlug);
  if (!resolved) notFound();

  const messages = await getMessages({ locale });
  let content;
  if (resolved.type === "industry") {
    content = getCityIndustryContent(
      resolved.nicheSlug,
      resolved.serviceAreaSlug,
      messages as never
    );
  } else {
    const segmentKey = resolved.type === "vehicle" ? resolved.vehicleKey : resolved.intentKey;
    content = getCityLocalSegmentContent(
      resolved.type,
      segmentKey,
      resolved.serviceAreaSlug,
      messages as never
    );
    if (!content && locale !== "en") {
      const enMessages = await getMessages({ locale: "en" });
      content = getCityLocalSegmentContent(
        resolved.type,
        segmentKey,
        resolved.serviceAreaSlug,
        enMessages as never
      );
    }
  }
  if (!content) notFound();

  const loc = locale as Locale;
  const tBc = await getTranslations("corporate.breadcrumbs");
  const cityLabel = city
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  const relatedLinks =
    resolved.type === "vehicle"
      ? buildVehicleLinksForCityPage(loc, city)
      : buildIndustryPageLinksForCityPage(loc);

  const serviceAreaSlug =
    CITY_SEO_TO_SERVICE_AREA[city as keyof typeof CITY_SEO_TO_SERVICE_AREA] ?? city;
  const tSeo = await getTranslations("corporate.seo.sectionLabels");

  return (
    <CorporateShell>
      <CityIndustryLandingView
        locale={loc}
        city={city}
        industrySlug={industrySlug}
        serviceAreaSlug={serviceAreaSlug}
        content={content}
        industryLinks={relatedLinks}
        relatedTitle={
          resolved.type === "vehicle" ? tSeo("otherVehicles") : tSeo("exploreByIndustry")
        }
        sectionLabels={{
          localDelivery: tSeo("localDelivery"),
          localChallenges: tSeo("localChallenges"),
          industryFit: tSeo("industryFit"),
          howItWorks: tSeo("howItWorks"),
          onboarding: tSeo("onboarding"),
          capacitySolutions: tSeo("capacitySolutions"),
          intentGuides: tSeo("intentGuides"),
          relatedPages: tSeo("relatedPages"),
        }}
        trackSource={`${city}/${industrySlug}`}
        breadcrumbs={[
          { label: tBc("home"), href: "/" },
          { label: cityLabel, href: `/service-areas/${serviceAreaSlug}` },
          { label: content.hero.title },
        ]}
      />
    </CorporateShell>
  );
}
