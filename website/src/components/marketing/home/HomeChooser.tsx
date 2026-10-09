import { getTranslations } from "next-intl/server";
import { ArrowRight, Clock3, ShoppingBag } from "lucide-react";
import { Link } from "@/i18n/navigation";
import Container from "@/components/ui/Container";
import LinkButton from "@/components/marketing/corporate/ui/LinkButton";
import HomeHeroImage from "@/components/marketing/home/HomeHeroImage";
import HomePriceCalculator from "@/components/marketing/home/HomePriceCalculator";
import HomeTrustStrip from "@/components/marketing/home/sections/HomeTrustStrip";
import HomeIndustries from "@/components/marketing/home/sections/HomeIndustries";
import HomeHowItWorks from "@/components/marketing/home/sections/HomeHowItWorks";
import HomeTrackingDemo from "@/components/marketing/home/sections/HomeTrackingDemo";
import HomeFaq from "@/components/marketing/home/sections/HomeFaq";
import HomeWhy from "@/components/marketing/home/sections/HomeWhy";
import HomeCaseStudy from "@/components/marketing/home/sections/HomeCaseStudy";
import CtaBand from "@/components/marketing/ui/CtaBand";
import TrustBadges from "@/components/marketing/ui/TrustBadges";
import { HUB_FROM } from "@/lib/marketing/config";
import { HOME_PRICE_ANCHOR_ID } from "@/lib/marketing/price-bar";
import { DELIVERY_PROMISE_DEFAULT } from "@/lib/seo/delivery-programmatic";

/** "11:00" → "11 AM" (en) / "11 h" (fr). */
function clock(value: string, locale: string): string {
  const [h, m] = value.split(":").map(Number);
  if (locale === "fr") return m ? `${h} h ${String(m).padStart(2, "0")}` : `${h} h`;
  const suffix = h >= 12 ? "PM" : "AM";
  const hour = h % 12 === 0 ? 12 : h % 12;
  return m ? `${hour}:${String(m).padStart(2, "0")} ${suffix}` : `${hour} ${suffix}`;
}

/** "14:00"–"21:00" → "2–9 PM" (en, same meridiem collapses) / "14 h et 21 h" handled in FR copy. */
function clockRange(start: string, end: string, locale: string): string {
  const a = clock(start, locale);
  const b = clock(end, locale);
  if (locale !== "fr" && a.slice(-2) === b.slice(-2)) return `${a.slice(0, -3)}–${b}`;
  return `${a}–${b}`;
}

/** Connect Shopify → public Shopify-merchants page until the app has a public App Store listing. */
const SHOPIFY_HREF = "/delivery/shopify-merchants";

/**
 * Homepage (website Phase 1, Oct 2026) — conversion-first, server-rendered.
 * Only the hero calculator is a client island; everything else is static HTML (no framer-motion,
 * no inline chat) so the first paint is the content.
 *
 * Promise line approved by Ravi 2026-10-09: "Order by 11 AM. Delivered 2–9 PM same day, Mon–Sat."
 * It is built from DELIVERY_PROMISE_DEFAULT (the same values the /delivery pages and the
 * pricing-engine `delivery_promise` default use).
 */
export default async function HomeChooser({ locale }: { locale: string }) {
  const t = await getTranslations({ locale, namespace: "homePage" });
  const quoteHref = `/sign-up?intent=quote&from=${HUB_FROM.chooser}`;
  const p = DELIVERY_PROMISE_DEFAULT;
  const promise = t("hero.promise", {
    cutoff: clock(p.cutoff, locale),
    window: clockRange(p.windowStart, p.windowEnd, locale),
    windowStart: clock(p.windowStart, locale),
    windowEnd: clock(p.windowEnd, locale),
    days: t("hero.promiseDays"),
  });

  const shopifyBadge = (
    <Link
      href={SHOPIFY_HREF}
      className="group inline-flex min-h-[var(--touch-min)] items-center gap-2.5 rounded-full border border-white/15 bg-white/5 py-1.5 pl-1.5 pr-4 text-sm text-white/85 transition-colors hover:border-white/35 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#95bf47] text-[#0b1f0b]">
        <ShoppingBag className="h-4 w-4" aria-hidden />
      </span>
      <span>
        <span className="font-semibold text-white">{t("hero.shopifyBadge")}</span>
        <span className="text-white/70"> · {t("hero.shopifyBadgeHint")}</span>
      </span>
    </Link>
  );

  return (
    <>
      {/* 1 — Hero: promise + instant price above the fold */}
      <section
        className="relative isolate overflow-hidden bg-primary text-white"
        aria-labelledby="home-hero-heading"
      >
        <div className="absolute inset-y-0 right-0 -z-10 hidden w-[62%] lg:block" aria-hidden>
          <HomeHeroImage />
          <div className="absolute inset-0 bg-gradient-to-r from-primary via-primary/40 to-transparent" />
        </div>
        <div
          className="pointer-events-none absolute -left-40 -top-40 -z-10 h-[32rem] w-[32rem] rounded-full bg-secondary/25 blur-3xl"
          aria-hidden
        />

        <Container className="grid gap-6 pb-10 pt-[calc(var(--nav-height)+1.25rem)] lg:min-h-[min(48rem,100dvh)] lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)] lg:items-center lg:gap-14 lg:pb-20 lg:pt-[calc(var(--nav-height)+3.5rem)]">
          <div className="max-w-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#93c5fd] sm:text-sm">
              {t("hero.eyebrow")}
            </p>
            <h1
              id="home-hero-heading"
              className="mt-3 text-balance text-[2.125rem] font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-[3.75rem]"
            >
              {t("hero.headline")}{" "}
              <span className="text-[#93c5fd]">{t("hero.headlineAccent")}</span>
            </h1>
            <p className="mt-4 inline-flex items-start gap-2.5 rounded-2xl border border-white/12 bg-white/[0.06] px-3.5 py-2.5 text-base font-medium leading-snug text-white sm:text-lg">
              <Clock3 className="mt-0.5 h-5 w-5 shrink-0 text-[#86efac]" aria-hidden />
              <span data-testid="home-promise">{promise}</span>
            </p>
            <p className="mt-4 hidden max-w-lg text-base leading-relaxed text-white/75 sm:block sm:text-lg">
              {t("hero.subtitle")}
            </p>
            <div className="mt-7 hidden flex-wrap items-center gap-3 lg:flex">
              <LinkButton href={quoteHref} size="lg" trackSource="home-hero" trackLabel="book_now">
                {t("hero.bookNow")}
              </LinkButton>
              <LinkButton
                href={SHOPIFY_HREF}
                size="lg"
                variant="outlineOnDark"
                trackSource="home-hero"
                trackLabel="connect_shopify"
              >
                {t("hero.connectShopify")}
              </LinkButton>
            </div>
            <div className="mt-8 hidden lg:block">
              <TrustBadges locale={locale} tone="dark" />
              <div className="mt-5">{shopifyBadge}</div>
            </div>
          </div>

          <HomePriceCalculator />

          <div className="space-y-5 lg:hidden">
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm font-semibold">
              <Link
                href={quoteHref}
                className="inline-flex min-h-[2.75rem] items-center gap-1.5 text-white underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
              >
                {t("hero.bookNow")}
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
              <Link
                href={SHOPIFY_HREF}
                className="inline-flex min-h-[2.75rem] items-center gap-1.5 text-white/85 underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
              >
                {t("hero.connectShopify")}
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </div>
            <TrustBadges locale={locale} tone="dark" />
          </div>
        </Container>
      </section>

      {/* 2 — Credibility: coverage facts from data + brand (no customer logos, reviews hidden) */}
      <HomeTrustStrip locale={locale} />

      {/* 3 — Industries */}
      <HomeIndustries locale={locale} />

      {/* 4 — How it works */}
      <HomeHowItWorks locale={locale} />

      {/* 5 — Why PorterChain (factual comparison) */}
      <HomeWhy locale={locale} promise={promise} />

      {/* 6 — Live tracking (static sample) */}
      <HomeTrackingDemo locale={locale} />

      {/* 7 — Case study slot (hidden until the customer gives permission) */}
      <HomeCaseStudy />

      {/* 8 — FAQ (+ FAQPage schema) */}
      <HomeFaq locale={locale} />

      {/* 9 — Final CTA band */}
      <CtaBand
        id="home-final-heading"
        title={t("final.title")}
        body={t("final.body")}
        primary={{ href: `#${HOME_PRICE_ANCHOR_ID}`, label: t("final.primary") }}
        secondary={{ href: quoteHref, label: t("final.secondary") }}
      >
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <Link
            href="/business"
            className="inline-flex min-h-[var(--touch-min)] items-center text-sm font-semibold text-white/85 underline underline-offset-4 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
          >
            {t("hero.businessAccounts")}
          </Link>
        </div>
      </CtaBand>
    </>
  );
}
