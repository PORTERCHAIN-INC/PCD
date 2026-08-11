import dynamic from "next/dynamic";
import { getTranslations } from "next-intl/server";
import type { Locale } from "@/i18n/routing";
import BusinessHero from "@/components/business/sections/BusinessHero";
import BusinessHubFacade from "@/components/business/sections/BusinessHubFacade";
import BusinessFleet from "@/components/business/sections/BusinessFleet";
import BusinessAnswerSection from "@/components/business/sections/BusinessAnswerSection";
import BrandMergeBand from "@/components/brand/BrandMergeBand";
import FinalCta from "@/components/business/sections/FinalCta";
import BusinessIntentGuides from "@/components/business/sections/BusinessIntentGuides";
import HubTrustStrip from "@/components/hub/HubTrustStrip";
import HubShell from "@/components/hub/HubShell";
import CapacityProductTrust from "@/components/marketing/CapacityProductTrust";
import { siteImages } from "@/data/site-images";

const BusinessSolutions = dynamic(() => import("@/components/business/sections/BusinessSolutions"));
const BusinessChallenges = dynamic(
  () => import("@/components/business/sections/BusinessChallenges")
);
const BusinessIndustries = dynamic(
  () => import("@/components/business/sections/BusinessIndustries")
);
const WhyChooseBusiness = dynamic(() => import("@/components/business/sections/WhyChooseBusiness"));
const TrustedBy = dynamic(() => import("@/components/business/sections/TrustedBy"));
const BillingOptions = dynamic(() => import("@/components/business/sections/BillingOptions"));
const BusinessFAQ = dynamic(() => import("@/components/business/sections/BusinessFAQ"));

type Props = {
  locale: Locale;
};

/**
 * /business story (one job per band):
 * 1. Hero — capacity partner + quote
 * 2. Facade — how capacity shows up
 * 3. Fleet — vehicle classes
 * 4. Answer + challenges — pain → fit
 * 5. Solutions + industries — who / when
 * 6. Product UI — tech included (once)
 * 7. Why + proof + brand
 * 8. Pricing → guides → FAQ → final CTA
 */
export default async function BusinessPageSections({ locale }: Props) {
  const tBrand = await getTranslations("businessPage.brandBand");
  const tTrust = await getTranslations("businessPage.trustStrip");

  return (
    <HubShell className="pb-24 lg:pb-0">
      <BusinessHero />
      <BusinessHubFacade locale={locale} />
      <BusinessFleet />
      <BusinessAnswerSection locale={locale} />
      <div className="perf-defer-section">
        <BusinessChallenges />
        <BusinessSolutions />
        <BusinessIndustries />
      </div>
      <CapacityProductTrust from="business" tone="light" />
      <div className="perf-defer-section">
        <WhyChooseBusiness />
        <TrustedBy />
      </div>
      <HubTrustStrip
        eyebrow={tTrust("eyebrow")}
        title={tTrust("title")}
        body={tTrust("body")}
        companyLabel={tTrust("company")}
        trustLabel={tTrust("trust")}
        contactLabel={tTrust("contact")}
      />
      <BrandMergeBand
        eyebrow={tBrand("eyebrow")}
        title={tBrand("title")}
        body={tBrand("body")}
        imageSide="right"
        image={siteImages.brand.loading}
        objectPosition="center 45%"
      />
      <div className="perf-defer-section">
        <BillingOptions />
        <BusinessIntentGuides locale={locale} />
        <BusinessFAQ />
        <FinalCta />
      </div>
    </HubShell>
  );
}
