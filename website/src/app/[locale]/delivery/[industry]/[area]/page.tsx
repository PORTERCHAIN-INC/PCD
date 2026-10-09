import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import { JsonLd } from "@/components/seo";
import {
  BulletList,
  DeliverySection,
  FaqList,
  IncludedList,
  LinkGrid,
  VehicleCards,
} from "@/components/marketing/delivery/DeliveryBlocks";
import DeliveryCta from "@/components/marketing/delivery/DeliveryCta";
import DeliveryHero from "@/components/marketing/delivery/DeliveryHero";
import { VEHICLE_PHOTOS } from "@/components/marketing/delivery/vertical-visuals";
import CtaBand from "@/components/marketing/ui/CtaBand";
import HeroVariantTitle from "@/components/marketing/delivery/HeroVariantTitle";
import { routing } from "@/i18n/routing";
import { siteConfig } from "@/lib/seo/config";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import {
  buildDeliveryBreadcrumbJsonLd,
  buildDeliveryFaqJsonLd,
  buildDeliveryPageContent,
  buildDeliveryServiceJsonLd,
  deliveryBreadcrumbs,
  deliveryPagePath,
  getDeliveryArea,
  getDeliveryVertical,
  indexability,
  isFitCombination,
  listDeliveryPages,
} from "@/lib/seo/delivery-programmatic";

type Props = { params: Promise<{ locale: string; industry: string; area: string }> };

export function generateStaticParams() {
  return routing.locales.flatMap((locale) =>
    listDeliveryPages().map((p) => ({ locale, industry: p.vertical, area: p.area }))
  );
}

function resolve(industry: string, area: string) {
  const vertical = getDeliveryVertical(industry);
  const place = getDeliveryArea(area);
  if (!vertical || !place || !isFitCombination(vertical, place)) return null;
  return { vertical, place };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, industry, area } = await params;
  const found = resolve(industry, area);
  if (!found) return {};
  const content = buildDeliveryPageContent(found.vertical, found.place);
  // English copy only: FR URLs exist for hreflang parity but stay noindex.
  const index = locale === "en" && indexability(found.vertical, found.place).index;
  return buildPageMetadata(
    locale,
    deliveryPagePath(industry, area),
    content.metaTitle,
    content.metaDescription,
    { index }
  );
}

export default async function DeliveryIndustryAreaPage({ params }: Props) {
  const { locale, industry, area } = await params;
  setRequestLocale(locale);
  const found = resolve(industry, area);
  if (!found) notFound();
  const { vertical, place } = found;
  const content = buildDeliveryPageContent(vertical, place);
  const crumbs = deliveryBreadcrumbs(locale, vertical, place);
  const from = deliveryPagePath(vertical.slug, place.slug);

  const related = [
    ...(vertical.industryPageSlug
      ? [
          {
            href: `/industry/${vertical.industryPageSlug}`,
            label: `${vertical.name} overview`,
            note: "How the service works for your industry",
          },
        ]
      : []),
    ...(place.serviceAreaSlug
      ? [
          {
            href: `/service-areas/${place.serviceAreaSlug}`,
            label: `${place.locality} service area`,
            note: "Coverage, neighbourhoods and postal codes",
          },
        ]
      : []),
    { href: `/${deliveryPagePath(vertical.slug)}`, label: `${vertical.name} — all GTA areas` },
    { href: "/facts", label: "PorterChain facts", note: "Coverage, hours, vehicles, pricing" },
  ];

  return (
    <CorporateShell>
      <JsonLd
        data={[
          buildDeliveryServiceJsonLd(vertical, place, { baseUrl: siteConfig.baseUrl, locale }),
          buildDeliveryFaqJsonLd(content.faqs),
          buildDeliveryBreadcrumbJsonLd(crumbs, siteConfig.baseUrl),
        ]}
      />
      <DeliveryHero
        locale={locale}
        crumbs={crumbs.map((c, i) => ({
          label: c.name,
          href: i < crumbs.length - 1 ? c.path.replace(`/${locale}`, "") || "/" : undefined,
        }))}
        eyebrow={`${vertical.name} · ${place.name}`}
        title={
          <HeroVariantTitle
            control={vertical.hero.control}
            variantB={vertical.hero.variantB}
            suffix={`in ${place.name}`}
            className="max-w-4xl text-balance text-[2rem] font-semibold leading-[1.08] tracking-tight text-white sm:text-5xl"
          />
        }
        answer={content.answer}
        actions={
          <DeliveryCta
            label={vertical.cta.label}
            pitch={vertical.cta.pitch}
            industry={vertical.slug}
            area={place.slug}
            pickupFsa={place.fsas[0]}
            from={from}
            tone="dark"
          />
        }
        facts={content.quickFacts}
      />

      <DeliverySection id="area" title={`Delivering in ${place.name}`} tone="soft">
        <p className="max-w-3xl text-base leading-relaxed text-primary/90 sm:text-lg">
          {content.areaSummary}
        </p>
        <p className="mt-4 text-sm text-muted">
          Postal areas covered:{" "}
          <span className="font-medium text-primary">{place.fsas.join(" · ")}</span>
        </p>
      </DeliverySection>

      <DeliverySection id="how" title={`How ${vertical.noun} delivery works`}>
        <BulletList items={content.serviceDetails} />
      </DeliverySection>

      {vertical.hub ? (
        <DeliverySection
          id="service-details"
          title={vertical.hub.serviceDetails.title}
          lead={vertical.hub.serviceDetails.lead}
          tone="soft"
        >
          <IncludedList
            included={vertical.hub.serviceDetails.included}
            notIncluded={vertical.hub.serviceDetails.notIncluded}
          />
        </DeliverySection>
      ) : null}

      <DeliverySection
        id="vehicles"
        title="Vehicles for this work"
        tone={vertical.hub ? "white" : "soft"}
      >
        <VehicleCards
          vehicles={content.vehicles.map((v) => ({ ...v, photo: VEHICLE_PHOTOS[v.id] }))}
        />
      </DeliverySection>

      <DeliverySection
        id="promise"
        title="Cut-off and delivery promise"
        tone={vertical.hub ? "soft" : "white"}
      >
        <p className="max-w-3xl text-base leading-relaxed text-primary/90 sm:text-lg">
          {content.promise}
        </p>
      </DeliverySection>

      <DeliverySection id="faq" title="Questions" tone={vertical.hub ? "white" : "soft"}>
        <FaqList items={content.faqs} />
      </DeliverySection>

      <DeliverySection
        id="nearby"
        title={`${vertical.name} near ${place.name}`}
        tone={vertical.hub ? "soft" : "white"}
      >
        <LinkGrid
          links={content.nearby.map((n) => ({
            href: `/${deliveryPagePath(vertical.slug, n.slug)}`,
            label: `${vertical.name} in ${n.name}`,
            note: `≈ ${n.kmApart} km away`,
          }))}
        />
      </DeliverySection>

      <DeliverySection id="related" title="Related" tone={vertical.hub ? "white" : "soft"}>
        <LinkGrid links={related} />
      </DeliverySection>

      <CtaBand
        id="area-final-heading"
        title={vertical.cta.label}
        body={`${vertical.cta.pitch} Pickup or drop-off in ${place.name}.`}
        primary={{
          href: `/delivery-cost-calculator?from=${encodeURIComponent(from)}&industry=${vertical.slug}&pickup=${place.fsas[0]}`,
          label: "Get a price",
        }}
        secondary={{
          href: `/sign-up?intent=merchant&from=${encodeURIComponent(from)}`,
          label: "Open a business account",
        }}
      />
    </CorporateShell>
  );
}
