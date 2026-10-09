import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import { JsonLd } from "@/components/seo";
import {
  AnswerFirst,
  DeliverySection,
  LinkGrid,
  QuickFacts,
} from "@/components/marketing/delivery/DeliveryBlocks";
import DeliveryCta from "@/components/marketing/delivery/DeliveryCta";
import { siteConfig } from "@/lib/seo/config";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";
import { buildLocalBusinessSchema } from "@/lib/seo/schema";
import {
  DELIVERY_AREAS,
  DELIVERY_VERTICALS,
  ENTITY_FACTS,
  areasForVertical,
  buildDeliveryBreadcrumbJsonLd,
  deliveryBreadcrumbs,
  deliveryPagePath,
  listDeliveryPages,
  promiseSentence,
} from "@/lib/seo/delivery-programmatic";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return localeStaticParams();
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "delivery",
    "Same-day business delivery across the GTA | PorterChain",
    "Same-day delivery for Shopify stores, pharmacies, labs, warehouses, wholesalers, construction and trade suppliers in 18 GTA areas. Live prices by postal code.",
    { index: locale === "en" }
  );
}

export default async function DeliveryHubPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const crumbs = deliveryBreadcrumbs(locale);
  const pages = listDeliveryPages();

  return (
    <CorporateShell>
      <JsonLd
        data={[
          buildLocalBusinessSchema(),
          buildDeliveryBreadcrumbJsonLd(crumbs, siteConfig.baseUrl),
        ]}
      />
      <PageBreadcrumbs items={[{ label: "Home", href: "/" }, { label: "Same-day delivery" }]} />
      <section className="bg-white pb-10 pt-8 sm:pt-12">
        <Container>
          <h1 className="max-w-4xl text-3xl font-bold tracking-tight text-primary sm:text-5xl">
            Same-day business delivery across the GTA
          </h1>
          <div className="mt-6">
            <AnswerFirst text={`${ENTITY_FACTS.what} ${promiseSentence()}`} />
          </div>
          <div className="mt-8">
            <DeliveryCta
              label="Get an instant price"
              pitch="Two postal codes and a vehicle — no sign-up."
              from="delivery"
            />
          </div>
          <div className="mt-10">
            <QuickFacts
              items={[
                { label: "Industries", value: String(DELIVERY_VERTICALS.length) },
                { label: "GTA areas", value: String(DELIVERY_AREAS.length) },
                { label: "Postal areas", value: `${ENTITY_FACTS.coverageFsaCount} FSAs` },
                { label: "Area guides", value: String(pages.length) },
              ]}
            />
          </div>
        </Container>
      </section>
      <DeliverySection title="By industry" tone="soft">
        <LinkGrid
          links={DELIVERY_VERTICALS.map((v) => ({
            href: `/${deliveryPagePath(v.slug)}`,
            label: v.name,
            note: `${areasForVertical(v).length} areas · ${v.audience}`,
          }))}
        />
      </DeliverySection>
      <DeliverySection title="By area">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {DELIVERY_AREAS.map((area) => (
            <div key={area.slug} className="rounded-2xl border border-primary/10 p-4">
              <h3 className="font-semibold text-primary">{area.name}</h3>
              <p className="mt-1 text-xs text-muted">
                {area.fsas.length} postal areas · ≈ {area.distanceKm} km from downtown
              </p>
              <ul className="mt-3 space-y-1 text-sm">
                {pages
                  .filter((p) => p.area === area.slug)
                  .map((p) => {
                    const v = DELIVERY_VERTICALS.find((x) => x.slug === p.vertical);
                    return (
                      <li key={p.path}>
                        <Link href={`/${p.path}`} className="text-secondary hover:underline">
                          {v?.name}
                        </Link>
                      </li>
                    );
                  })}
              </ul>
            </div>
          ))}
        </div>
      </DeliverySection>
    </CorporateShell>
  );
}
