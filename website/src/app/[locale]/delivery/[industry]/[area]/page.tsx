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
  FaqList,
  LinkGrid,
  QuickFacts,
} from "@/components/marketing/delivery/DeliveryBlocks";
import DeliveryCta from "@/components/marketing/delivery/DeliveryCta";
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
      <PageBreadcrumbs
        items={crumbs.map((c, i) => ({
          label: c.name,
          href: i < crumbs.length - 1 ? c.path.replace(`/${locale}`, "") || "/" : undefined,
        }))}
      />
      <section className="bg-white pb-10 pt-8 sm:pt-12">
        <Container>
          <p className="text-sm font-semibold uppercase tracking-wide text-secondary">
            {vertical.name} · {place.name}
          </p>
          <HeroVariantTitle
            control={vertical.hero.control}
            variantB={vertical.hero.variantB}
            suffix={`in ${place.name}`}
            className="mt-3 max-w-4xl text-3xl font-bold tracking-tight text-primary sm:text-5xl"
          />
          <div className="mt-6">
            <AnswerFirst text={content.answer} />
          </div>
          <div className="mt-8">
            <DeliveryCta
              label={vertical.cta.label}
              pitch={vertical.cta.pitch}
              industry={vertical.slug}
              area={place.slug}
              pickupFsa={place.fsas[0]}
              from={from}
            />
          </div>
          <div className="mt-10">
            <QuickFacts items={content.quickFacts} />
          </div>
        </Container>
      </section>

      <DeliverySection title={`Delivering in ${place.name}`} tone="soft">
        <p className="max-w-3xl text-base leading-relaxed text-primary/90">{content.areaSummary}</p>
        <p className="mt-4 text-sm text-muted">
          Postal areas covered:{" "}
          <span className="font-medium text-primary">{place.fsas.join(" · ")}</span>
        </p>
      </DeliverySection>

      <DeliverySection title={`How ${vertical.noun} delivery works`}>
        <BulletList items={content.serviceDetails} />
      </DeliverySection>

      <DeliverySection title="Vehicles for this work" tone="soft">
        <ul className="grid gap-3 sm:grid-cols-3">
          {content.vehicles.map((v) => (
            <li key={v.id} className="rounded-xl border border-primary/10 bg-white p-4">
              <p className="font-semibold text-primary">{v.label}</p>
              <p className="mt-1 text-sm text-muted">Capacity: {v.capacity}.</p>
              <p className="mt-1 text-sm text-muted">Best for {v.bestFor}.</p>
              <p className="mt-1 text-xs text-muted">Driven on a standard Ontario G licence.</p>
            </li>
          ))}
        </ul>
      </DeliverySection>

      <DeliverySection title="Cut-off and delivery promise">
        <p className="max-w-3xl text-base leading-relaxed text-primary/90">{content.promise}</p>
      </DeliverySection>

      <DeliverySection title="Questions" tone="soft">
        <FaqList items={content.faqs} />
      </DeliverySection>

      <DeliverySection title={`${vertical.name} near ${place.name}`}>
        <LinkGrid
          links={content.nearby.map((n) => ({
            href: `/${deliveryPagePath(vertical.slug, n.slug)}`,
            label: `${vertical.name} in ${n.name}`,
            note: `≈ ${n.kmApart} km away`,
          }))}
        />
      </DeliverySection>

      <DeliverySection title="Related" tone="soft">
        <LinkGrid links={related} />
      </DeliverySection>
    </CorporateShell>
  );
}
