import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import { Building2, MapPinned, Receipt, Truck } from "lucide-react";
import Container from "@/components/ui/Container";
import { JsonLd } from "@/components/seo";
import { DeliverySection, FaqList } from "@/components/marketing/delivery/DeliveryBlocks";
import DeliveryHero from "@/components/marketing/delivery/DeliveryHero";
import CtaBand from "@/components/marketing/ui/CtaBand";
import PriceCalculator from "@/components/marketing/calculator/PriceCalculator";
import { siteConfig } from "@/lib/seo/config";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";
import {
  DELIVERY_PROMISE_DEFAULT,
  ENTITY_FACTS,
  buildDeliveryBreadcrumbJsonLd,
  buildDeliveryFaqJsonLd,
  buildQuoteOffer,
} from "@/lib/seo/delivery-programmatic";

/** How the price is built — each line restates the pricing FAQ / ENTITY_FACTS (no new claims). */
const PRICE_PARTS = [
  {
    Icon: MapPinned,
    title: "Driving distance",
    body: "Measured between the two postal-area centres; a base price covers the first kilometres, then a per-kilometre rate.",
  },
  {
    Icon: Truck,
    title: "Vehicle",
    body: "Sedan / SUV, cargo van or 16 ft box truck — pick the smallest one that fits the load.",
  },
  {
    Icon: Building2,
    title: "Downtown surcharge",
    body: "Applies to downtown Toronto postal areas where relevant, as part of the same live price.",
  },
  {
    Icon: Receipt,
    title: "HST included",
    body: "The total shows 13% HST. Your exact addresses are confirmed before you pay.",
  },
] as const;

type Props = { params: Promise<{ locale: string }> };

const FAQS = [
  {
    question: "How is the price calculated?",
    answer:
      "From the driving distance between the two postal areas and the vehicle you pick: a base price covers the first kilometres, then a per-kilometre rate; a downtown Toronto surcharge applies where relevant. The total shown includes 13% HST.",
  },
  {
    question: "Is this the price I will pay?",
    answer:
      "It is the same pricing engine used at checkout, measured between postal-area centres. Your exact addresses can move the distance a little, so the final price is confirmed before you pay.",
  },
  {
    question: "Do I have to share my contact details to see a price?",
    answer:
      "No. The price shows with just two postal codes. The call-back form is optional, and marketing email needs its own tick box.",
  },
];

export function generateStaticParams() {
  return localeStaticParams();
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "delivery-cost-calculator",
    "Same-day delivery cost calculator (GTA) | PorterChain",
    "Instant same-day delivery price between any two GTA postal codes for a sedan, cargo van or box truck. Live pricing, HST included, no sign-up.",
    { index: locale === "en" }
  );
}

export default async function DeliveryCostCalculatorPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const crumbs = [
    { name: "Home", path: `/${locale}` },
    { name: "Same-day delivery", path: `/${locale}/delivery` },
    { name: "Cost calculator", path: `/${locale}/delivery-cost-calculator` },
  ];
  const base = siteConfig.baseUrl.replace(/\/$/, "");
  return (
    <CorporateShell>
      <JsonLd
        data={[
          {
            "@context": "https://schema.org",
            "@type": "WebApplication",
            name: "PorterChain delivery cost calculator",
            applicationCategory: "BusinessApplication",
            operatingSystem: "Any",
            url: `${base}/${locale}/delivery-cost-calculator`,
            provider: { "@id": `${base}/#organization` },
            offers: buildQuoteOffer(base, locale),
          },
          buildDeliveryFaqJsonLd(FAQS),
          buildDeliveryBreadcrumbJsonLd(crumbs, siteConfig.baseUrl),
        ]}
      />
      <DeliveryHero
        locale={locale}
        crumbs={[
          { label: "Home", href: "/" },
          { label: "Same-day delivery", href: "/delivery" },
          { label: "Cost calculator" },
        ]}
        eyebrow="Instant price · GTA"
        title={
          <h1 className="max-w-4xl text-balance text-[2rem] font-semibold leading-[1.08] tracking-tight text-white sm:text-5xl">
            Same-day delivery cost calculator
          </h1>
        }
        answer="Enter two GTA postal codes and pick a vehicle to see the live same-day price, HST included. No account or contact details needed."
        facts={[
          {
            label: "Same-day cut-off",
            value: `${DELIVERY_PROMISE_DEFAULT.cutoff} → ${DELIVERY_PROMISE_DEFAULT.windowStart}–${DELIVERY_PROMISE_DEFAULT.windowEnd}`,
          },
          { label: "Days", value: DELIVERY_PROMISE_DEFAULT.daysShort },
          { label: "Postal areas", value: `${ENTITY_FACTS.coverageFsaCount} FSAs` },
          { label: "Vehicles", value: "Sedan · Van · Box truck" },
        ]}
      />
      <section className="bg-gray-bg pb-14 pt-10 sm:pb-20 sm:pt-14" aria-label="Price calculator">
        <Container>
          <PriceCalculator />
        </Container>
      </section>
      <DeliverySection
        id="price-parts"
        eyebrow="Transparent pricing"
        title="How the price is built"
      >
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PRICE_PARTS.map(({ Icon, title, body }) => (
            <li key={title} className="rounded-2xl border border-primary/8 bg-gray-bg p-6">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary/10 text-secondary">
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <h3 className="mt-4 text-lg font-semibold text-primary">{title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{body}</p>
            </li>
          ))}
        </ul>
      </DeliverySection>
      <DeliverySection id="about-prices" title="About these prices" tone="soft">
        <FaqList items={FAQS} />
      </DeliverySection>
      <CtaBand
        id="calculator-final-heading"
        title="Ready to book?"
        body="Open an account to book this delivery, track it live and get photo proof of delivery."
        primary={{ href: "/sign-up?intent=quote&from=delivery-cost-calculator", label: "Book now" }}
        secondary={{ href: "/business", label: "Business accounts" }}
      />
    </CorporateShell>
  );
}
