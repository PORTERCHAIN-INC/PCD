import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import { ArrowRight } from "lucide-react";
import { JsonLd } from "@/components/seo";
import { DeliverySection } from "@/components/marketing/delivery/DeliveryBlocks";
import DeliveryCta from "@/components/marketing/delivery/DeliveryCta";
import DeliveryHero from "@/components/marketing/delivery/DeliveryHero";
import { VERTICAL_ICONS } from "@/components/marketing/delivery/vertical-visuals";
import CtaBand from "@/components/marketing/ui/CtaBand";
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
    `Same-day delivery for Shopify stores, pharmacies, labs, warehouses, wholesalers, construction, trade suppliers and furniture retailers in ${DELIVERY_AREAS.length} GTA areas. Live prices by postal code.`,
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
      <DeliveryHero
        locale={locale}
        crumbs={[{ label: "Home", href: "/" }, { label: "Same-day delivery" }]}
        eyebrow="Industries"
        title={
          <h1 className="max-w-4xl text-balance text-[2rem] font-semibold leading-[1.08] tracking-tight text-white sm:text-5xl">
            Same-day business delivery across the GTA
          </h1>
        }
        answer={`${ENTITY_FACTS.what} ${promiseSentence()}`}
        actions={
          <DeliveryCta
            label="Get an instant price"
            pitch="Two postal codes and a vehicle — no sign-up."
            from="delivery"
            tone="dark"
          />
        }
        facts={[
          { label: "Industries", value: String(DELIVERY_VERTICALS.length) },
          { label: "GTA areas", value: String(DELIVERY_AREAS.length) },
          { label: "Postal areas", value: `${ENTITY_FACTS.coverageFsaCount} FSAs` },
          { label: "Area guides", value: String(pages.length) },
        ]}
      />
      <DeliverySection
        id="by-industry"
        eyebrow="By industry"
        title="Pick your industry"
        tone="soft"
      >
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {DELIVERY_VERTICALS.map((v) => {
            const Icon = VERTICAL_ICONS[v.slug];
            return (
              <li key={v.slug}>
                <Link
                  href={`/${deliveryPagePath(v.slug)}`}
                  className="group flex h-full flex-col rounded-2xl border border-primary/8 bg-white p-5 transition-[border-color,box-shadow,transform] duration-200 hover:border-secondary/40 hover:shadow-xl hover:shadow-primary/8 motion-safe:hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
                >
                  {Icon ? (
                    <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary/10 text-secondary">
                      <Icon className="h-5 w-5" aria-hidden />
                    </span>
                  ) : null}
                  <span className="mt-4 flex items-center gap-1.5 font-semibold text-primary">
                    {v.name}
                    <ArrowRight
                      className="h-4 w-4 text-secondary transition-transform motion-safe:group-hover:translate-x-1"
                      aria-hidden
                    />
                  </span>
                  <span className="mt-1 text-xs leading-relaxed text-muted">
                    {areasForVertical(v).length} areas · {v.audience}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </DeliverySection>
      <DeliverySection id="by-area" eyebrow="By area" title="Area guides">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {DELIVERY_AREAS.map((area) => (
            <div key={area.slug} className="rounded-2xl border border-primary/8 bg-white p-5">
              <h3 className="font-semibold text-primary">{area.name}</h3>
              <p className="mt-1 text-xs text-muted">
                {area.fsas.length} postal areas · ≈ {area.distanceKm} km from downtown
              </p>
              <ul className="mt-3 space-y-1.5 text-sm">
                {pages
                  .filter((p) => p.area === area.slug)
                  .map((p) => {
                    const v = DELIVERY_VERTICALS.find((x) => x.slug === p.vertical);
                    return (
                      <li key={p.path}>
                        <Link
                          href={`/${p.path}`}
                          className="inline-flex min-h-6 items-center rounded py-0.5 text-secondary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
                        >
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
      <CtaBand
        id="delivery-final-heading"
        title="Price your next delivery."
        body="Two postal codes and a vehicle. The price includes HST and needs no sign-up."
        primary={{ href: "/delivery-cost-calculator?from=delivery", label: "Get a price" }}
        secondary={{
          href: "/sign-up?intent=merchant&from=delivery",
          label: "Open a business account",
        }}
      />
    </CorporateShell>
  );
}
