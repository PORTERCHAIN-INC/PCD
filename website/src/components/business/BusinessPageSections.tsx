import dynamic from "next/dynamic";
import { getTranslations } from "next-intl/server";
import type { Locale } from "@/i18n/routing";
import BusinessHero from "@/components/business/sections/BusinessHero";
import BusinessFleet from "@/components/business/sections/BusinessFleet";
import BrandMergeBand from "@/components/brand/BrandMergeBand";
import FinalCta from "@/components/business/sections/FinalCta";
import BusinessIntentGuides from "@/components/business/sections/BusinessIntentGuides";
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

/** Below-fold sections code-split to protect INP on /business (Wave 10 w10-1). */
export default async function BusinessPageSections({ locale }: Props) {
  const tBrand = await getTranslations("businessPage.brandBand");

  return (
    <div className="pb-24 lg:pb-0">
      <BusinessHero />
      <BusinessFleet />
      <BrandMergeBand
        eyebrow={tBrand("eyebrow")}
        title={tBrand("title")}
        body={tBrand("body")}
        imageSide="right"
        image={siteImages.brand.loading}
        objectPosition="center 45%"
      />
      <div className="perf-defer-section">
        <BusinessSolutions />
        <BusinessChallenges />
        <BusinessIndustries />
        <WhyChooseBusiness />
        <TrustedBy />
        <BillingOptions />
        <BusinessIntentGuides locale={locale} />
        <BusinessFAQ />
        <FinalCta />
      </div>
    </div>
  );
}
