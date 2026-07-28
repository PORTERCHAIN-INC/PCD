import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import CorporateShell from "@/components/corporate/layout/CorporateShell";
import GuestTrackLookup from "@/components/portal/GuestTrackLookup";
import HeroSection from "@/components/corporate/sections/HeroSection";
import HeroPhoto from "@/components/ui/HeroPhoto";
import { siteImages } from "@/data/site-images";
import { localeStaticParams, buildPageMetadata } from "@/lib/seo/page-helpers";

type Props = { params: Promise<{ locale: string }> };

export const generateStaticParams = localeStaticParams;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(
    locale,
    "track",
    "Track your delivery | Porterchain",
    "Look up shipment status and proof of delivery with your Porterchain tracking number."
  );
}

export default async function TrackPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <CorporateShell>
      <HeroSection
        badge="Tracking"
        title="Track your shipment"
        subtitle="Enter your tracking number to see live status, ETA, and delivery confirmation."
        primaryCta="Get a quote"
        primaryHref="/business#pricing"
        variant="light-centered"
        clearNav
        illustration={<HeroPhoto image={siteImages.sections.howItWorks} />}
      />
      <section className="site-section bg-white pb-16">
        <div className="site-container max-w-xl mx-auto px-4">
          <GuestTrackLookup />
        </div>
      </section>
    </CorporateShell>
  );
}
