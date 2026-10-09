import Container from "@/components/ui/Container";
import AreaSelector from "@/components/marketing/delivery/AreaSelector";
import ServicesStrip from "@/components/marketing/delivery/ServicesStrip";
import ContactBar from "@/components/marketing/delivery/ContactBar";
import { groupByRegion } from "@/lib/seo/area-regions";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import { JsonLd } from "@/components/seo";
import {
  BulletList,
  CardGrid,
  DeliverySection,
  FaqList,
  IncludedList,
  VehicleCards,
} from "@/components/marketing/delivery/DeliveryBlocks";
import DeliveryCta from "@/components/marketing/delivery/DeliveryCta";
import DeliveryHero from "@/components/marketing/delivery/DeliveryHero";
import HeroVariantTitle from "@/components/marketing/delivery/HeroVariantTitle";
import {
  VEHICLE_PHOTOS,
  VERTICAL_ICONS,
  VERTICAL_PHOTOS,
} from "@/components/marketing/delivery/vertical-visuals";
import CtaBand from "@/components/marketing/ui/CtaBand";
import { routing } from "@/i18n/routing";
import { siteConfig } from "@/lib/seo/config";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import {
  DELIVERY_PROMISE_DEFAULT,
  DELIVERY_VEHICLES,
  ENTITY_FACTS,
  areasForVertical,
  buildDeliveryBreadcrumbJsonLd,
  buildDeliveryFaqJsonLd,
  buildQuoteOffer,
  deliveryBreadcrumbs,
  deliveryPagePath,
  getDeliveryVertical,
  indexability,
  DELIVERY_VERTICALS,
  promiseSentence,
  type DeliveryFaq,
  type DeliveryVertical,
} from "@/lib/seo/delivery-programmatic";

type Props = { params: Promise<{ locale: string; industry: string }> };

export function generateStaticParams() {
  return routing.locales.flatMap((locale) =>
    DELIVERY_VERTICALS.map((v) => ({ locale, industry: v.slug }))
  );
}

function vehicleList(vertical: DeliveryVertical): string {
  return vertical.vehicles.map((v) => DELIVERY_VEHICLES[v].label.toLowerCase()).join(", ");
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, industry } = await params;
  const vertical = getDeliveryVertical(industry);
  if (!vertical) return {};
  return buildPageMetadata(
    locale,
    deliveryPagePath(industry),
    `${vertical.hero.control} across the GTA | PorterChain`,
    `Same-day ${vertical.noun} delivery in ${areasForVertical(vertical).length} GTA areas by ${vehicleList(
      vertical
    )}. Live prices, order by ${DELIVERY_PROMISE_DEFAULT.cutoff}.`,
    { index: locale === "en" }
  );
}

/** Hubs without long-form content still get a short, factual FAQ (and FAQPage schema). */
function hubFaqs(vertical: DeliveryVertical, areaCount: number): DeliveryFaq[] {
  if (vertical.hub) return vertical.hub.faqs;
  return [
    {
      question: `Do you offer same-day ${vertical.noun} delivery across the GTA?`,
      answer: `Yes, in ${areaCount} GTA areas. ${promiseSentence()}`,
    },
    {
      question: `Which vehicles can I book for ${vertical.noun}s?`,
      answer: vertical.vehicles
        .map((v) => `${DELIVERY_VEHICLES[v].label}: ${DELIVERY_VEHICLES[v].capacity}.`)
        .join(" "),
    },
    {
      question: `How much does ${vertical.noun} delivery cost?`,
      answer:
        "Price depends on the driving distance and the vehicle. The calculator uses the same pricing engine as checkout and shows the total including HST before you share any contact details.",
    },
    vertical.specialistFaq,
  ];
}

export default async function DeliveryIndustryHubPage({ params }: Props) {
  const { locale, industry } = await params;
  setRequestLocale(locale);
  const vertical = getDeliveryVertical(industry);
  if (!vertical) notFound();
  const areas = areasForVertical(vertical);
  const crumbs = deliveryBreadcrumbs(locale, vertical);
  const base = siteConfig.baseUrl.replace(/\/$/, "");
  const faqs = hubFaqs(vertical, areas.length);
  const hub = vertical.hub;
  const p = DELIVERY_PROMISE_DEFAULT;
  const from = deliveryPagePath(vertical.slug);
  const calculatorHref = `/delivery-cost-calculator?from=${encodeURIComponent(from)}&industry=${vertical.slug}`;
  const Icon = VERTICAL_ICONS[vertical.slug];
  /** Hubs with their own vehicle cards (with photos) skip the generic vehicle section. */
  const hubHasVehicles = Boolean(hub?.sections.some((sec) => sec.blocks.some((b) => b.vehicle)));

  return (
    <CorporateShell>
      <JsonLd
        data={[
          {
            "@context": "https://schema.org",
            "@type": "Service",
            name: `${vertical.hero.control} across the GTA`,
            serviceType: `${vertical.name} delivery`,
            description:
              hub?.intro ??
              `Same-day ${vertical.noun} delivery across the GTA by ${vehicleList(vertical)}.`,
            url: `${base}/${locale}/${from}`,
            provider: { "@id": `${base}/#organization` },
            areaServed: areas.map((a) => ({ "@type": "Place", name: `${a.name}, Ontario` })),
            offers: buildQuoteOffer(base, locale),
          },
          buildDeliveryFaqJsonLd(faqs),
          buildDeliveryBreadcrumbJsonLd(crumbs, siteConfig.baseUrl),
        ].filter(Boolean)}
      />
      <DeliveryHero
        locale={locale}
        crumbs={crumbs.map((c, i) => ({
          label: c.name,
          href: i < crumbs.length - 1 ? c.path.replace(`/${locale}`, "") || "/" : undefined,
        }))}
        eyebrow={vertical.name}
        title={
          <div className="flex items-start gap-4">
            {Icon ? (
              <span className="mt-1 hidden h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/10 text-[#93c5fd] sm:flex">
                <Icon className="h-6 w-6" aria-hidden />
              </span>
            ) : null}
            <HeroVariantTitle
              control={vertical.hero.control}
              variantB={vertical.hero.variantB}
              suffix="across the GTA"
              className="max-w-3xl text-balance text-[2rem] font-semibold leading-[1.08] tracking-tight text-white sm:text-5xl"
            />
          </div>
        }
        answer={
          hub?.intro ??
          `PorterChain delivers ${vertical.goods} for ${vertical.audience} in ${areas.length} GTA areas. ${promiseSentence()}`
        }
        actions={
          <DeliveryCta
            label={vertical.cta.label}
            pitch={vertical.cta.pitch}
            industry={vertical.slug}
            from={from}
            tone="dark"
          />
        }
        facts={[
          { label: "Same-day cut-off", value: `${p.cutoff} → ${p.windowStart}–${p.windowEnd}` },
          { label: "Days", value: p.daysShort },
          { label: "GTA areas", value: String(areas.length) },
          { label: "Postal areas", value: `${ENTITY_FACTS.coverageFsaCount} FSAs` },
        ]}
        image={VERTICAL_PHOTOS[vertical.slug]}
      />

      {hub ? (
        hub.sections.map((section, index) => (
          <DeliverySection
            key={section.id}
            id={`hub-${section.id}`}
            title={section.title}
            lead={section.lead}
            tone={index % 2 === 0 ? "soft" : "white"}
          >
            <CardGrid
              numbered={section.numbered}
              items={section.blocks.map((b) => ({
                ...b,
                photo: b.vehicle ? { ...VEHICLE_PHOTOS[b.vehicle], alt: "" } : undefined,
              }))}
            />
          </DeliverySection>
        ))
      ) : (
        <DeliverySection id="hub-what" title="What you get" tone="soft">
          <BulletList items={[...vertical.handling, vertical.compliance]} />
        </DeliverySection>
      )}

      {hub ? (
        <DeliverySection
          id="service-details"
          title={hub.serviceDetails.title}
          lead={hub.serviceDetails.lead}
          tone={hub.sections.length % 2 === 0 ? "soft" : "white"}
        >
          <IncludedList
            included={hub.serviceDetails.included}
            notIncluded={hub.serviceDetails.notIncluded}
          />
        </DeliverySection>
      ) : null}

      {hubHasVehicles ? null : (
        <DeliverySection
          id="hub-vehicles"
          title="Vehicles for this work"
          lead="Every class is driven on a standard Ontario G licence and priced live by distance."
          tone={hub ? "soft" : "white"}
        >
          <VehicleCards
            vehicles={vertical.vehicles.map((id) => ({
              ...DELIVERY_VEHICLES[id],
              photo: VEHICLE_PHOTOS[id],
            }))}
          />
        </DeliverySection>
      )}

      <section aria-label="Areas" className="bg-white">
        <Container className="py-10 sm:py-12">
          <AreaSelector
            title={`${vertical.name} by area`}
            groups={groupByRegion(
              areas.map((a) => ({
                slug: a.slug,
                href: `/${deliveryPagePath(vertical.slug, a.slug)}`,
                label: a.name,
                note: `${a.fsas.length} postal areas · ≈ ${a.distanceKm} km${
                  indexability(vertical, a).index ? "" : " · by confirmation"
                }`,
              }))
            )}
          />
        </Container>
      </section>

      <DeliverySection id="hub-faq" title="Questions" tone="soft">
        <FaqList items={faqs} />
      </DeliverySection>

      <ServicesStrip current={vertical.slug} />
      <ContactBar />

      <CtaBand
        id="hub-final-heading"
        title={vertical.cta.label}
        body={`${vertical.cta.pitch} ${promiseSentence().split(". ")[0]}.`}
        primary={{ href: calculatorHref, label: "Get a price" }}
        secondary={{
          href: `/sign-up?intent=merchant&from=${encodeURIComponent(from)}`,
          label: "Open a business account",
        }}
      />
    </CorporateShell>
  );
}
