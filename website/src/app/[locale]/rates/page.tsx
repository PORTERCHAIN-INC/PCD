import type { Metadata } from "next";
import Link from "next/link";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/marketing/corporate/layout/CorporateShell";
import Container from "@/components/ui/Container";
import { siteConfig } from "@/lib/seo/config";
import { buildPageMetadata, localeStaticParams } from "@/lib/seo/page-helpers";
import { SCHEDULE_CSS, SCHEDULE_HTML } from "./schedule-html";

type Props = { params: Promise<{ locale: string }> };

const TITLE = "Porterchain — Same-day delivery across the GTA";
const DESCRIPTION =
  "Business delivery rates for the GTA: van from $30 / stop, compact sedan or SUV from $6 / stop. Live tracking included. All prices in CAD. 13% HST extra.";
const PHONE_DISPLAY = "+1 (647) 619-7951";
const PHONE_TEL = "+16476197951";
const EMAIL = "enterprise@porterchain.com";

export function generateStaticParams() {
  return localeStaticParams();
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  // noindex: this commercial rate sheet overlaps the site's indexed pricing pages
  // (calculator / business pricing), so it is a share link, not a search landing page.
  const base = buildPageMetadata(locale, "rates", TITLE, DESCRIPTION, { index: false });
  const url = `${siteConfig.baseUrl}/${locale}/rates`;
  const image = {
    url: `${siteConfig.baseUrl}/og/rates.png`,
    width: 1200,
    height: 630,
    alt: "Porterchain: same-day delivery across the GTA. Sedan, SUV, van and box truck.",
  };
  return {
    ...base,
    title: { absolute: TITLE },
    description: DESCRIPTION,
    alternates: { ...base.alternates, canonical: url },
    openGraph: {
      ...base.openGraph,
      title: TITLE,
      description: DESCRIPTION,
      url,
      siteName: "Porterchain",
      type: "website",
      images: [image],
    },
    twitter: {
      card: "summary_large_image",
      title: TITLE,
      description: DESCRIPTION,
      images: [image.url],
    },
    robots: { index: false, follow: true },
  };
}

const STEPS = [
  {
    n: "01",
    t: "Book",
    d: "Get a quote online, send orders by API or email, or call us. You see the rate before you commit.",
  },
  {
    n: "02",
    t: "We pick up",
    d: "A driver collects from your location. Pickup waiting of 45 minutes is included.",
  },
  {
    n: "03",
    t: "Delivered and tracked",
    d: "Live tracking and recipient notices are included on every delivery.",
  },
];

const AUDIENCE = [
  { t: "Warehouses", d: "Outbound runs to customers and job sites across the GTA." },
  { t: "Suppliers & distributors", d: "Regular routes to trade accounts, priced per stop." },
  { t: "Traders", d: "Ad-hoc and bulk deliveries with clear handling tiers." },
  { t: "Merchants", d: "Local delivery for retail orders without running your own fleet." },
  { t: "Shopify stores", d: "Order assignment by API integration, with no API setup charge." },
];

const VEHICLES = [
  {
    t: "Sedan or SUV",
    tag: "Small parcels",
    d: 'Packed parcels up to 10" × 10", up to 3 parcels per stop, in the compact territory. From $6 / stop.',
  },
  {
    t: "Cargo van",
    tag: "Bulk & heavier items",
    d: "Multi-stop routes, standard parcels up to 100 lb, with handling tiers above that. From $30 / stop.",
  },
  {
    t: "Box truck (16 ft)",
    tag: "Large loads",
    d: "Larger or bulky loads by custom quotation. No liftgate: pieces are hand-unloaded from the back of the truck.",
  },
];

const FAQ = [
  {
    q: "Where do you deliver?",
    a: "Across the GTA and up to about 150 km from Toronto, checked by postal code (FSA). Destinations beyond 150 km get a custom quotation.",
  },
  {
    q: "How fast is delivery?",
    a: "Same day or next day. Order by 11:00 for same-day delivery between 14:00 and 21:00, Monday to Saturday; later orders go out the next operating day. Capacity allowing — not a guaranteed window.",
  },
  {
    q: "How do businesses pay?",
    a: "Businesses pay by Interac e-Transfer for each billing cycle.",
  },
  {
    q: "Are deliveries covered?",
    a: "$2,500 goods insurance is included. Enhanced coverage up to $25,000 is optional at +$10 per stop and replaces the included cover. Claims must be notified in writing within 5 business days.",
  },
  { q: "Are taxes included?", a: "All prices in CAD. 13% HST extra." },
  { q: "Is tracking included?", a: "Yes. Live tracking and recipient notices are included." },
];

function Cta({ locale, light = false }: { locale: string; light?: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Link
        href={`/${locale}/quote`}
        className="inline-flex h-12 items-center rounded-full bg-[#2563eb] px-7 font-semibold text-white transition hover:bg-[#1d4ed8]"
      >
        Get a quote →
      </Link>
      <a
        href={`tel:${PHONE_TEL}`}
        className={`inline-flex h-12 items-center rounded-full border px-6 font-semibold transition ${
          light
            ? "border-[#0b1220]/15 text-[#0b1220] hover:bg-[#0b1220]/5"
            : "border-white/25 text-white hover:bg-white/10"
        }`}
      >
        Call {PHONE_DISPLAY}
      </a>
    </div>
  );
}

export default async function RatesPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <CorporateShell>
      <div className="font-sans text-[#0b1220]">
        {/* Hero */}
        <section className="relative overflow-hidden bg-[#0b1220] text-white">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(60% 80% at 85% 10%, rgba(37,99,235,.55), transparent 60%), radial-gradient(50% 60% at 0% 100%, rgba(29,78,216,.35), transparent 60%), linear-gradient(180deg,#0b1220 0%,#0a1628 100%)",
            }}
          />
          <Container className="relative py-16 md:py-24">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-sm font-medium">
              <span className="h-2 w-2 rounded-full bg-[#60a5fa]" /> Booking now · Mon–Sat
            </p>
            <h1 className="max-w-4xl text-4xl font-extrabold leading-[1.08] tracking-tight md:text-6xl">
              Same-day delivery across the <span className="text-[#60a5fa]">GTA</span>, priced per
              stop.
            </h1>
            <p className="mt-5 max-w-2xl text-lg text-white/80 md:text-xl">
              Van delivery from <b className="text-white">$30 / stop</b>. Compact sedan or SUV
              delivery from <b className="text-white">$6 / stop</b>. Live tracking included. All
              prices in CAD. 13% HST extra.
            </p>
            <p className="mt-2 text-white/60">Sedan · SUV · Van · Box truck</p>
            <div className="mt-8">
              <Cta locale={locale} />
            </div>
          </Container>
        </section>

        {/* How it works */}
        <section className="bg-white py-14 md:py-20">
          <Container>
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">How it works</h2>
            <ol className="mt-8 grid gap-5 md:grid-cols-3">
              {STEPS.map((s) => (
                <li key={s.n} className="rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-6">
                  <span className="text-sm font-bold text-[#2563eb]">{s.n}</span>
                  <h3 className="mt-2 text-xl font-semibold">{s.t}</h3>
                  <p className="mt-2 text-[#64748b]">{s.d}</p>
                </li>
              ))}
            </ol>
          </Container>
        </section>

        {/* Who it's for */}
        <section className="bg-[#f8fafc] py-14 md:py-20">
          <Container>
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Who it&apos;s for</h2>
            <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              {AUDIENCE.map((a) => (
                <li key={a.t} className="rounded-2xl border border-[#e2e8f0] bg-white p-5">
                  <h3 className="font-semibold">{a.t}</h3>
                  <p className="mt-1 text-sm text-[#64748b]">{a.d}</p>
                </li>
              ))}
            </ul>
          </Container>
        </section>

        {/* Vehicle guide */}
        <section className="bg-white py-14 md:py-20">
          <Container>
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Pick your vehicle</h2>
            <div className="mt-8 grid gap-5 md:grid-cols-3">
              {VEHICLES.map((v) => (
                <div key={v.t} className="rounded-2xl border border-[#e2e8f0] p-6">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#2563eb]">
                    {v.tag}
                  </span>
                  <h3 className="mt-2 text-xl font-semibold">{v.t}</h3>
                  <p className="mt-2 text-[#64748b]">{v.d}</p>
                </div>
              ))}
            </div>
          </Container>
        </section>

        {/* Full schedule (identical rates to the merchant quote) */}
        <section className="bg-[#e2e8f0] py-10 md:py-14" id="schedule">
          <Container>
            <h2 className="mb-6 text-3xl font-bold tracking-tight md:text-4xl">
              Schedule of rates and conditions
            </h2>
            <style dangerouslySetInnerHTML={{ __html: SCHEDULE_CSS }} />
            <div
              className="pc-rates overflow-x-auto rounded-2xl bg-white shadow-sm"
              dangerouslySetInnerHTML={{ __html: SCHEDULE_HTML }}
            />
          </Container>
        </section>

        {/* FAQ */}
        <section className="bg-white py-14 md:py-20">
          <Container size="narrow">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Questions</h2>
            <div className="mt-6 divide-y divide-[#e2e8f0] border-y border-[#e2e8f0]">
              {FAQ.map((f) => (
                <details key={f.q} className="group py-4">
                  <summary className="cursor-pointer list-none text-lg font-semibold">
                    {f.q}
                  </summary>
                  <p className="mt-2 text-[#64748b]">{f.a}</p>
                </details>
              ))}
            </div>
          </Container>
        </section>

        {/* Closing CTA */}
        <section className="bg-[#0b1220] py-14 text-white md:py-20">
          <Container>
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Ready to ship today?</h2>
            <p className="mt-3 max-w-2xl text-white/75">
              Get a quote online, call us, or email{" "}
              <a className="text-[#60a5fa] underline" href={`mailto:${EMAIL}`}>
                {EMAIL}
              </a>
              . Office hours Mon–Fri 8 AM–6 PM, Sat 9 AM–2 PM (Toronto time).
            </p>
            <div className="mt-7">
              <Cta locale={locale} />
            </div>
            <p className="mt-8 text-sm text-white/50">
              Porterchain Inc. · Ontario, Canada · CAD, HST extra.
            </p>
          </Container>
        </section>
      </div>
    </CorporateShell>
  );
}
