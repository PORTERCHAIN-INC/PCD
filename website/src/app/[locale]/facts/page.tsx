import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import { JsonLd } from "@/components/seo";
import { DeliverySection, LinkGrid } from "@/components/marketing/delivery/DeliveryBlocks";
import { siteConfig } from "@/lib/seo/config";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";
import { buildLocalBusinessSchema } from "@/lib/seo/schema";
import {
  DELIVERY_AREAS,
  ENTITY_FACTS,
  buildDeliveryBreadcrumbJsonLd,
} from "@/lib/seo/delivery-programmatic";

type Props = { params: Promise<{ locale: string }> };

export function generateStaticParams() {
  return localeStaticParams();
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "facts",
    "PorterChain at a glance — coverage, hours, vehicles, pricing",
    `Plain facts about PorterChain: same-day GTA business delivery, ${ENTITY_FACTS.coverageFsaCount} postal areas, sedan to 16 ft box truck on a G licence, distance-and-vehicle pricing with HST shown.`,
    { index: locale === "en" }
  );
}

export default async function FactsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const rows: Array<[string, string]> = [
    ["What PorterChain does", ENTITY_FACTS.what],
    ["Company", `${ENTITY_FACTS.name} (${ENTITY_FACTS.legalName})`],
    ["Hub", ENTITY_FACTS.hub],
    [
      "Coverage",
      `${ENTITY_FACTS.coverage} ${ENTITY_FACTS.coverageFsaCount} postal areas (FSAs) in the pricing registry.`,
    ],
    ["Hours", ENTITY_FACTS.hours],
    ["Same-day cut-off", ENTITY_FACTS.promise],
    ["Vehicles", ENTITY_FACTS.vehicles.join("; ")],
    ["Licence", ENTITY_FACTS.licence],
    ["Pricing approach", ENTITY_FACTS.pricing],
    ["Industries", ENTITY_FACTS.verticals.join(", ")],
    ["Privacy & consent", ENTITY_FACTS.privacy],
  ];
  return (
    <CorporateShell>
      <JsonLd
        data={[
          buildLocalBusinessSchema(),
          buildDeliveryBreadcrumbJsonLd(
            [
              { name: "Home", path: `/${locale}` },
              { name: "Facts", path: `/${locale}/facts` },
            ],
            siteConfig.baseUrl
          ),
        ]}
      />
      <PageBreadcrumbs items={[{ label: "Home", href: "/" }, { label: "Facts" }]} />
      <section className="bg-white pb-6 pt-8 sm:pt-12">
        <Container size="narrow">
          <h1 className="text-3xl font-bold tracking-tight text-primary sm:text-4xl">
            PorterChain at a glance
          </h1>
          <p className="mt-4 text-base leading-relaxed text-primary/90">
            {ENTITY_FACTS.what} This page lists the facts we stand behind, in plain language.
          </p>
          <dl className="mt-8 divide-y divide-primary/10 rounded-2xl border border-primary/10">
            {rows.map(([label, value]) => (
              <div key={label} className="grid gap-1 p-4 sm:grid-cols-3 sm:gap-4">
                <dt className="text-sm font-semibold text-primary">{label}</dt>
                <dd className="text-sm leading-relaxed text-primary/90 sm:col-span-2">{value}</dd>
              </div>
            ))}
          </dl>
        </Container>
      </section>
      <DeliverySection title="Areas we serve" tone="soft">
        <p className="text-sm text-muted">
          {DELIVERY_AREAS.map((a) => `${a.name} (${a.fsas.length})`).join(" · ")}
        </p>
      </DeliverySection>
      <DeliverySection title="Next steps">
        <LinkGrid
          links={[
            { href: "/delivery-cost-calculator", label: "Get an instant price" },
            { href: "/delivery", label: "Same-day delivery by industry and area" },
            { href: "/contact", label: "Contact the team" },
          ]}
        />
      </DeliverySection>
    </CorporateShell>
  );
}
