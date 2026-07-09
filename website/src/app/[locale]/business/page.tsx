import { setRequestLocale } from "next-intl/server";
import SiteShell from "@/components/layout/SiteShell";
import StickyCta from "@/components/business/StickyCta";
import BusinessHero from "@/components/business/sections/BusinessHero";
import TrustedBy from "@/components/business/sections/TrustedBy";
import BusinessChallenges from "@/components/business/sections/BusinessChallenges";
import BusinessSolutions from "@/components/business/sections/BusinessSolutions";
import BusinessIndustries from "@/components/business/sections/BusinessIndustries";
import WhyChooseBusiness from "@/components/business/sections/WhyChooseBusiness";
import BusinessFleet from "@/components/business/sections/BusinessFleet";
import EnterpriseOnboarding from "@/components/business/sections/EnterpriseOnboarding";
import DashboardPreview from "@/components/business/sections/DashboardPreview";
import Technology from "@/components/business/sections/Technology";
import BillingOptions from "@/components/business/sections/BillingOptions";
import CustomerSuccess from "@/components/business/sections/CustomerSuccess";
import BusinessFAQ from "@/components/business/sections/BusinessFAQ";
import FinalCta from "@/components/business/sections/FinalCta";
import { routing } from "@/i18n/routing";

type Props = {
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function BusinessPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <>
      <SiteShell>
        <div className="pb-24 lg:pb-0">
          <BusinessHero />
          <BusinessFleet />
          <TrustedBy />
          <BusinessChallenges />
          <BusinessSolutions />
          <BusinessIndustries />
          <WhyChooseBusiness />
          <EnterpriseOnboarding />
          <DashboardPreview />
          <Technology />
          <BillingOptions />
          <CustomerSuccess />
          <BusinessFAQ />
          <FinalCta />
        </div>
      </SiteShell>
      <StickyCta />
    </>
  );
}
