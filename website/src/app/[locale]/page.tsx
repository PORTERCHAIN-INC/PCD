import { setRequestLocale } from "next-intl/server";
import SiteShell from "@/components/layout/SiteShell";
import Hero from "@/components/sections/Hero";
import DeliveryTypes from "@/components/sections/DeliveryTypes";
import GtaFramedSection from "@/components/sections/GtaFramedSection";
import Industries from "@/components/sections/Industries";
import Vehicles from "@/components/sections/Vehicles";
import WhoCanUse from "@/components/sections/WhoCanUse";
import HowItWorks from "@/components/sections/HowItWorks";
import LiveMap from "@/components/sections/LiveMap";
import WhyPorterchain from "@/components/sections/WhyPorterchain";
import MobileApp from "@/components/sections/MobileApp";
import Features from "@/components/sections/Features";
import Trust from "@/components/sections/Trust";
import FAQ from "@/components/sections/FAQ";
import HomePageShell from "@/components/home/HomePageShell";
import { routing } from "@/i18n/routing";

type Props = {
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function HomePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <HomePageShell>
      <SiteShell>
        <Hero />
        <DeliveryTypes />
        <GtaFramedSection />
        <Industries />
        <Vehicles />
        <WhoCanUse />
        <HowItWorks />
        <LiveMap />
        <WhyPorterchain />
        <MobileApp />
        <Features />
        <Trust />
        <FAQ />
      </SiteShell>
    </HomePageShell>
  );
}
