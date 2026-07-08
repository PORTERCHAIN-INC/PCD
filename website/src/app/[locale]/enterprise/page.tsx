import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import CtaSection from "@/components/corporate/sections/CtaSection";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { siteImages } from "@/data/site-images";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";
import { business, contact } from "@/lib/seo/routes";
import type { Locale } from "@/i18n/routing";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "enterprise",
    "Enterprise delivery | Porterchain",
    "Structured delivery operations for larger merchants — dedicated capacity, reporting, and onboarding support."
  );
}

export default async function EnterprisePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const loc = locale as Locale;

  return (
    <CorporateShell>
      <HeroSection
        badge="Enterprise"
        title="Enterprise delivery operations"
        subtitle="For merchants with structured routes, multiple locations, and reporting requirements — one partner for recurring and same-day across Ontario."
        primaryCta="Talk to us"
        primaryHref={business(loc, { from: "enterprise" })}
        secondaryCta="Contact"
        secondaryHref={contact(loc, { from: "enterprise" })}
        variant="light-centered"
        illustration={<HeroPhoto image={siteImages.hero.logistics} />}
      />
      <CtaSection
        title="Let's design your delivery program"
        subtitle="Share your volume, service areas, and SLAs. We'll map a program that fits."
        primaryLabel="Get started"
        primaryHref={business(loc, { from: "enterprise" })}
        secondaryLabel="Contact sales"
        secondaryHref={contact(loc, { from: "enterprise" })}
        variant="gradient"
      />
    </CorporateShell>
  );
}
