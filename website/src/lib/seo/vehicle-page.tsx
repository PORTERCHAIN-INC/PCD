import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getMessages, setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import ContentClusterView from "@/components/seo/ContentClusterView";
import { localePath } from "@/lib/seo/routes";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import { buildVehicleConstructionLinks } from "@/lib/seo/vehicle-construction-links";
import { isIndexableVehicleSegment, shouldIndexVehicleRoute } from "@/lib/seo/vehicle-publication";
import { routing, type Locale } from "@/i18n/routing";

const VEHICLE_CONFIG = {
  "sedan-delivery": "sedan",
  "suv-delivery": "suv",
  "trade-van-delivery": "van",
  "pickup-truck-delivery": "pickupTruck",
  "cargo-van-delivery": "cargoVan",
  "box-truck-delivery": "mediumTruck",
} as const;

type VehicleSegment = keyof typeof VEHICLE_CONFIG;

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return routing.locales.flatMap((locale) =>
    (Object.keys(VEHICLE_CONFIG) as VehicleSegment[]).map((segment) => ({
      locale,
      // segment is passed via folder name in parent - see individual page files
    }))
  );
}

export async function buildVehicleMetadata(
  locale: string,
  segment: VehicleSegment
): Promise<Metadata> {
  const messages = await getMessages({ locale });
  const key = VEHICLE_CONFIG[segment];
  const v = (
    messages as { vehicleDelivery?: Record<string, { pageTitle?: string; description?: string }> }
  ).vehicleDelivery?.[key];
  const index =
    isIndexableVehicleSegment(segment) &&
    shouldIndexVehicleRoute(segment, messages as { vehicleDelivery?: Record<string, VehicleCopy> });
  return buildPageMetadata(locale, segment, v?.pageTitle ?? segment, v?.description ?? "", {
    index,
  });
}

type VehicleCopy = {
  pageTitle?: string;
  description?: string;
  intro?: string;
  headline?: string;
  subheadline?: string;
  whenYouNeedTitle?: string;
  whenYouNeed?: string;
  faqPricingQ?: string;
  faqPricingA?: string;
  useCasesTitle?: string;
  useCases?: string;
  volumeTitle?: string;
  volumeSuitability?: string;
  whoForTitle?: string;
  whoFor?: string;
  serviceAreaTitle?: string;
  serviceAreaRelevance?: string;
  sections?: { heading: string; body: string }[];
};

function buildVehicleSections(v: VehicleCopy): { heading: string; body: string }[] {
  if (v.sections?.length) return v.sections;

  const sections: { heading: string; body: string }[] = [];
  if (v.whenYouNeedTitle && v.whenYouNeed) {
    sections.push({ heading: v.whenYouNeedTitle, body: v.whenYouNeed });
  }
  const pairs: [string | undefined, string | undefined][] = [
    [v.useCasesTitle, v.useCases],
    [v.volumeTitle, v.volumeSuitability],
    [v.whoForTitle, v.whoFor],
    [v.serviceAreaTitle, v.serviceAreaRelevance],
  ];
  for (const [heading, body] of pairs) {
    if (heading && body) sections.push({ heading, body });
  }
  return sections;
}

export async function VehicleDeliveryPageContent({
  locale,
  segment,
}: {
  locale: Locale;
  segment: VehicleSegment;
}) {
  const messages = await getMessages({ locale });
  const key = VEHICLE_CONFIG[segment];
  const v = (messages as { vehicleDelivery?: Record<string, VehicleCopy> }).vehicleDelivery?.[key];
  if (!v) notFound();

  const relatedLinks = [
    ...buildVehicleConstructionLinks(locale, key),
    ...(key === "van"
      ? [
          {
            href: localePath(locale, "cargo-van-delivery"),
            label: "Cargo van delivery (e-commerce & wholesale)",
          },
        ]
      : []),
    ...(key === "cargoVan"
      ? [
          {
            href: localePath(locale, "trade-van-delivery"),
            label: "Trade van delivery (construction & plumbing)",
          },
        ]
      : []),
    ...(key === "mediumTruck"
      ? [{ href: localePath(locale, "trade-van-delivery"), label: "Trade van delivery" }]
      : []),
  ];
  const intro = v.intro ?? v.subheadline ?? v.description ?? "";
  const items =
    v.faqPricingQ && v.faqPricingA
      ? [{ question: v.faqPricingQ, answer: v.faqPricingA }]
      : undefined;

  return (
    <ContentClusterView
      locale={locale}
      ctaSource={segment}
      data={{
        title: v.pageTitle ?? v.headline ?? segment,
        description: v.description ?? "",
        intro,
        items,
        sections: buildVehicleSections(v),
        relatedLinks,
        relatedTitle: "Construction & trades delivery",
      }}
    />
  );
}
