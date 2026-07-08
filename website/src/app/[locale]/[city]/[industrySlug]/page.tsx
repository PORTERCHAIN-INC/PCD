import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getMessages, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import CityIndustryLandingView from "@/components/seo/CityIndustryLandingView";
import { getCityIndustryContent } from "@/lib/seo/city-industry-delivery";
import { getCityLocalSegmentContent } from "@/lib/seo/city-local-segment-content";
import { getAllCitySegmentPairs, resolveCitySegment } from "@/lib/seo/city-segment-seo";
import {
  buildIndustryPageLinksForCityPage,
  buildVehicleLinksForCityPage,
} from "@/lib/seo/internal-linking";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
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
  if (!content) return {};
  return buildPageMetadata(
    locale,
    `${city}/${industrySlug}`,
    content.meta.title,
    content.meta.description
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
  const relatedLinks =
    resolved.type === "vehicle"
      ? buildVehicleLinksForCityPage(loc, city)
      : buildIndustryPageLinksForCityPage(loc);

  return (
    <CorporateShell>
      <CityIndustryLandingView
        locale={loc}
        city={city}
        industrySlug={industrySlug}
        content={content}
        industryLinks={relatedLinks}
        relatedTitle={resolved.type === "vehicle" ? "Other vehicles" : "Explore by industry"}
        trackSource={`${city}/${industrySlug}`}
      />
    </CorporateShell>
  );
}
