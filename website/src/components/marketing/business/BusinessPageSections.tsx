import dynamic from "next/dynamic";
import Container from "@/components/ui/Container";
import CoreFaqList from "@/components/marketing/faq/CoreFaqList";
import { getTranslations } from "next-intl/server";
import type { Locale } from "@/i18n/routing";
import BusinessQuoteHero from "@/components/marketing/business/sections/BusinessHero";
import BusinessHubFacade from "@/components/marketing/business/sections/BusinessHubFacade";
import BusinessFleet from "@/components/marketing/business/sections/BusinessFleet";
import BusinessAnswerSection from "@/components/marketing/business/sections/BusinessAnswerSection";
import BrandMergeBand from "@/components/marketing/brand/BrandMergeBand";
import BusinessQuoteCloser from "@/components/marketing/business/sections/FinalCta";
import BusinessIntentGuides from "@/components/marketing/business/sections/BusinessIntentGuides";
import {
  HubTrustStrip,
  ProductTrust as CapacityProductTrust,
} from "@/components/marketing/MarketingProof";
import HubShell from "@/components/marketing/hub/HubShell";
import { siteImages } from "@/data/site-images";

const BusinessSolutions = dynamic(
  () => import("@/components/marketing/business/sections/BusinessSolutions")
);
const BusinessChallenges = dynamic(
  () => import("@/components/marketing/business/sections/BusinessChallenges")
);
const BusinessIndustries = dynamic(
  () => import("@/components/marketing/business/sections/BusinessIndustries")
);
const WhyChooseBusiness = dynamic(() =>
  import("@/components/marketing/MarketingProof").then((m) => m.WhyChoose)
);
const TrustedBy = dynamic(() =>
  import("@/components/marketing/MarketingProof").then((m) => m.TrustedBy)
);
const BillingOptions = dynamic(
  () => import("@/components/marketing/business/sections/BillingOptions")
);

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
      <BusinessQuoteHero />
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
        <section className="bg-white" aria-labelledby="business-faq-heading">
          <Container size="narrow" className="py-16 sm:py-24">
            <h2
              id="business-faq-heading"
              className="text-3xl font-semibold tracking-tight text-primary sm:text-4xl"
            >
              {locale === "fr" ? "Questions fréquentes" : "Questions buyers ask"}
            </h2>
            <div className="mt-8">
              <CoreFaqList locale={locale} grouped schema={false} />
            </div>
          </Container>
        </section>
        <BusinessQuoteCloser />
      </div>
    </HubShell>
  );
}
