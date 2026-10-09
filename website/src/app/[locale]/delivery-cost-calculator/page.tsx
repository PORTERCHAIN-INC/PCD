import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import PageBreadcrumbs from "@/components/seo/PageBreadcrumbs";
import { JsonLd } from "@/components/seo";
import {
  AnswerFirst,
  DeliverySection,
  FaqList,
} from "@/components/marketing/delivery/DeliveryBlocks";
import PriceCalculator from "@/components/marketing/calculator/PriceCalculator";
import { siteConfig } from "@/lib/seo/config";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";
import {
  buildDeliveryBreadcrumbJsonLd,
  buildDeliveryFaqJsonLd,
  buildQuoteOffer,
} from "@/lib/seo/delivery-programmatic";

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
      <PageBreadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Same-day delivery", href: "/delivery" },
          { label: "Cost calculator" },
        ]}
      />
      <section className="bg-white pb-6 pt-8 sm:pt-12">
        <Container>
          <h1 className="max-w-4xl text-3xl font-bold tracking-tight text-primary sm:text-5xl">
            Same-day delivery cost calculator
          </h1>
          <div className="mt-6">
            <AnswerFirst text="Enter two GTA postal codes and pick a vehicle to see the live same-day price, HST included. No account or contact details needed." />
          </div>
        </Container>
      </section>
      <section className="bg-slate-50 py-10 sm:py-14">
        <Container>
          <PriceCalculator />
        </Container>
      </section>
      <DeliverySection title="About these prices">
        <FaqList items={FAQS} />
      </DeliverySection>
    </CorporateShell>
  );
}
