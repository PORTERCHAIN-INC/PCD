import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import { JsonLd } from "@/components/seo";
import {
  AnswerFirst,
  BulletList,
  DeliverySection,
  LinkGrid,
} from "@/components/marketing/delivery/DeliveryBlocks";
import DeliveryCta from "@/components/marketing/delivery/DeliveryCta";
import HeroVariantTitle from "@/components/marketing/delivery/HeroVariantTitle";
import { routing } from "@/i18n/routing";
import { siteConfig } from "@/lib/seo/config";
import { buildPageMetadata } from "@/lib/seo/page-helpers";
import {
  DELIVERY_VEHICLES,
  areasForVertical,
  buildDeliveryBreadcrumbJsonLd,
  buildQuoteOffer,
  deliveryBreadcrumbs,
  deliveryPagePath,
  distanceBand,
  getDeliveryVertical,
  indexability,
  DELIVERY_VERTICALS,
  promiseSentence,
} from "@/lib/seo/delivery-programmatic";

type Props = { params: Promise<{ locale: string; industry: string }> };

export function generateStaticParams() {
  return routing.locales.flatMap((locale) =>
    DELIVERY_VERTICALS.map((v) => ({ locale, industry: v.slug }))
  );
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, industry } = await params;
  const vertical = getDeliveryVertical(industry);
  if (!vertical) return {};
  return buildPageMetadata(
    locale,
    deliveryPagePath(industry),
    `${vertical.hero.control} across the GTA | PorterChain`,
    `Same-day ${vertical.noun} delivery in ${areasForVertical(vertical).length} GTA areas by ${vertical.vehicles
      .map((v) => DELIVERY_VEHICLES[v].label.toLowerCase())
      .join(", ")}. Live prices, order by 11:00.`,
    { index: locale === "en" }
  );
}

const BAND_LABEL = { core: "Toronto core", inner: "Inner GTA", outer: "Outer GTA" } as const;

export default async function DeliveryIndustryHubPage({ params }: Props) {
  const { locale, industry } = await params;
  setRequestLocale(locale);
  const vertical = getDeliveryVertical(industry);
  if (!vertical) notFound();
  const areas = areasForVertical(vertical);
  const crumbs = deliveryBreadcrumbs(locale, vertical);
  const groups = (["core", "inner", "outer"] as const).map((band) => ({
    band,
    areas: areas.filter((a) => distanceBand(a.distanceKm) === band),
  }));
  const base = siteConfig.baseUrl.replace(/\/$/, "");

  return (
    <CorporateShell>
      <JsonLd
        data={[
          {
            "@context": "https://schema.org",
            "@type": "Service",
            name: `${vertical.hero.control} across the GTA`,
            serviceType: `${vertical.name} delivery`,
            provider: { "@id": `${base}/#organization` },
            areaServed: areas.map((a) => ({ "@type": "Place", name: `${a.name}, Ontario` })),
            offers: buildQuoteOffer(base, locale),
          },
          buildDeliveryBreadcrumbJsonLd(crumbs, siteConfig.baseUrl),
        ]}
      />
      <PageBreadcrumbs
        items={crumbs.map((c, i) => ({
          label: c.name,
          href: i < crumbs.length - 1 ? c.path.replace(`/${locale}`, "") || "/" : undefined,
        }))}
      />
      <section className="bg-white pb-10 pt-8 sm:pt-12">
        <Container>
          <HeroVariantTitle
            control={vertical.hero.control}
            variantB={vertical.hero.variantB}
            suffix="across the GTA"
            className="max-w-4xl text-3xl font-bold tracking-tight text-primary sm:text-5xl"
          />
          <div className="mt-6">
            <AnswerFirst
              text={`PorterChain delivers ${vertical.goods} for ${vertical.audience} in ${areas.length} GTA areas. ${promiseSentence()}`}
            />
          </div>
          <div className="mt-8">
            <DeliveryCta
              label={vertical.cta.label}
              pitch={vertical.cta.pitch}
              industry={vertical.slug}
              from={deliveryPagePath(vertical.slug)}
            />
          </div>
        </Container>
      </section>
      <DeliverySection title="What you get" tone="soft">
        <BulletList items={[...vertical.handling, vertical.compliance]} />
      </DeliverySection>
      {groups
        .filter((g) => g.areas.length)
        .map((g) => (
          <DeliverySection key={g.band} title={BAND_LABEL[g.band]}>
            <LinkGrid
              links={g.areas.map((a) => ({
                href: `/${deliveryPagePath(vertical.slug, a.slug)}`,
                label: `${vertical.name} in ${a.name}`,
                note: `${a.fsas.length} postal areas · ≈ ${a.distanceKm} km${
                  indexability(vertical, a).index ? "" : " · by confirmation"
                }`,
              }))}
            />
          </DeliverySection>
        ))}
      <DeliverySection title="Other industries" tone="soft">
        <LinkGrid
          links={DELIVERY_VERTICALS.filter((v) => v.slug !== vertical.slug).map((v) => ({
            href: `/${deliveryPagePath(v.slug)}`,
            label: v.name,
          }))}
        />
      </DeliverySection>
    </CorporateShell>
  );
}
